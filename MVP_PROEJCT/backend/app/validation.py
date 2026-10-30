"""순수 Python 검사 엔진. DB·화면·AI와 분리하여 동일 입력에 동일 판정을 낸다.

PASS: 합의한 기준 만족 / FAIL: 기준 위반 / NOT_TESTED: 설정·자료가 없어 검사 미실시
UNDETERMINED: 자료가 모호하여 판단 불가. 어느 경우도 임의로 PASS로 바꾸지 않는다.
"""
from collections import Counter
from datetime import datetime
from math import isfinite

ENGINE_VERSION = '1.0.1'


def parse_time(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # 시차 정보가 없는 시각을 로컬 시간으로 추정하면 장비 간 비교가 왜곡된다.
        return result if result.tzinfo is not None and result.utcoffset() is not None else None
    except (TypeError, ValueError, AttributeError):
        return None


def inspect_release(payload, profile):
    checks = []
    rows = payload['measurements']

    def add(parameter_id, rule, title, status, expected, observed, indexes=None, required=True):
        checks.append(dict(parameter_id=parameter_id, rule=rule, title=title, status=status,
                           expected=str(expected), observed=str(observed), rows=indexes or [], required=required))

    manifest = payload['manifest']
    evidence = manifest.get('tester_software_version')
    version_status = 'UNDETERMINED' if not evidence else ('PASS' if evidence == manifest['software_version'] else 'FAIL')
    add('_manifest', 'VERSION', '시험 결과의 소프트웨어 버전', version_status,
        manifest['software_version'], evidence or '시험 버전 증거 없음')

    for spec in profile['parameters']:
        pid = spec['id']
        selected = [(i + 1, row) for i, row in enumerate(rows) if row['parameter_id'] == pid]
        indexes = [i for i, _ in selected]
        data = [row for _, row in selected]
        required = spec.get('required', True)
        add(pid, 'PRESENCE', '필수 데이터와 최소 표본', 'PASS' if len(data) >= spec['min_samples'] else 'FAIL',
            f"최소 {spec['min_samples']}개", f'{len(data)}개', indexes, required)
        if not data:
            # 데이터가 없어도 검사 항목을 없애지 않는다. 정상 버전과 같은 분모를 유지한다.
            # 미실시를 통과로 취급하지 않고 필수 검사는 승인 차단 사유로 남긴다.
            for rule, title in [('UNIT', '단위 일치'), ('RANGE', '측정값과 허용 범위'),
                                ('TIME', '시각과 수집 간격'), ('RUN', '작업 번호 연결'), ('CHAMBER', '챔버 연결')]:
                is_required = required and not (rule == 'RANGE' and spec.get('minimum') is None and spec.get('maximum') is None)
                add(pid, rule, title, 'NOT_TESTED', '측정 데이터 필요', '데이터 미수신', required=is_required)
            continue

        units = {row.get('unit') for row in data}
        status = 'UNDETERMINED' if None in units or '' in units else ('PASS' if units == {spec['unit']} else 'FAIL')
        add(pid, 'UNIT', '단위 일치', status, spec['unit'], ', '.join(str(u) for u in sorted(units, key=str)), indexes)

        values = [row.get('value') for row in data]
        usable_values = [v for v in values if isinstance(v, (int, float)) and isfinite(v)]
        if len(usable_values) != len(values):
            add(pid, 'RANGE', '측정값과 허용 범위', 'UNDETERMINED', '유효한 수치', '값이 없는 표본 포함', indexes)
        elif spec.get('minimum') is None and spec.get('maximum') is None:
            add(pid, 'RANGE', '측정값과 허용 범위', 'NOT_TESTED', '허용 범위 설정', '범위 미지정', indexes, False)
        elif status != 'PASS':
            # 단위가 다른 수치를 같은 범위와 비교하면 잘못된 합격/불합격이 된다.
            add(pid, 'RANGE', '측정값과 허용 범위', 'UNDETERMINED', f"{spec.get('minimum')} ~ {spec.get('maximum')} {spec['unit']}",
                '단위 확인 전 수치 범위 판정 유보', indexes)
        else:
            low, high = spec.get('minimum'), spec.get('maximum')
            bad = [(i, r['value']) for i, r in selected if (low is not None and r['value'] < low) or (high is not None and r['value'] > high)]
            add(pid, 'RANGE', '측정값과 허용 범위', 'FAIL' if bad else 'PASS', f'{low} ~ {high}',
                f'최소 {min(values):g}, 최대 {max(values):g}', [i for i, _ in bad] if bad else indexes)

        times = [parse_time(row.get('timestamp')) for row in data]
        if any(t is None for t in times):
            add(pid, 'TIME', '시각과 수집 간격', 'UNDETERMINED', '시차를 포함한 ISO 8601 시각', '누락·잘못된 시각 또는 시차 정보 없음',
                [i for (i, _), t in zip(selected, times) if t is None])
        elif len(times) < 2:
            add(pid, 'TIME', '시각과 수집 간격', 'UNDETERMINED', '2개 이상의 표본', '간격 계산 불가', indexes)
        else:
            # 원래 수신 순서를 유지한다. 정렬하면 역전·중복 결함을 숨기게 된다.
            gaps = [(b - a).total_seconds() * 1000 for a, b in zip(times, times[1:])]
            target = spec['interval_ms']
            tolerance = spec.get('interval_tolerance', 0.2)
            good = all(g > 0 and abs(g - target) <= target * tolerance for g in gaps)
            add(pid, 'TIME', '시각과 수집 간격', 'PASS' if good else 'FAIL', f'{target}ms ±{tolerance * 100:g}%',
                '관측 간격(ms): ' + ', '.join(f'{g:g}' for g in gaps), indexes)

        for field, rule, title, allowed in [('run_id', 'RUN', '작업 번호 연결', profile['allowed_run_ids']),
                                             ('chamber', 'CHAMBER', '챔버 연결', profile['allowed_chambers'])]:
            observed = {row.get(field) for row in data}
            state = 'UNDETERMINED' if None in observed or '' in observed else ('PASS' if observed <= set(allowed) else 'FAIL')
            add(pid, rule, title, state, ', '.join(allowed), ', '.join(str(v) for v in sorted(observed, key=str)), indexes)

    known = {s['id'] for s in profile['parameters']}
    extras = sorted({r['parameter_id'] for r in rows} - known)
    if extras:
        add('_scope', 'EXTRA', '등록 범위 밖 항목', 'UNDETERMINED', '승인 항목표에 등록', ', '.join(extras))
    return checks


def summarize(checks):
    counts = Counter(c['status'] for c in checks)
    return {s: counts[s] for s in ['PASS', 'FAIL', 'NOT_TESTED', 'UNDETERMINED']}


def compare_releases(baseline, candidate, profile):
    # 다른 장비나 운전 조건을 비교하면 공정 차이를 소프트웨어 결함으로 오인한다.
    for key in ['equipment_id', 'scenario']:
        if baseline['manifest'][key] != candidate['manifest'][key]:
            raise ValueError('동일 장비와 동일 운전 시나리오만 비교할 수 있습니다.')
    if candidate['manifest']['equipment_id'] != profile['equipment_id'] or candidate['manifest']['scenario'] != profile['scenario']:
        raise ValueError('장비 또는 운전 시나리오가 선택한 검증 기준과 다릅니다.')
    checks = inspect_release(candidate, profile)
    baseline_checks = inspect_release(baseline, profile)
    counts = summarize(checks)
    blockers = lambda items: any(c['required'] and c['status'] != 'PASS' for c in items)
    baseline_usable = not blockers(baseline_checks)
    approvable = baseline_usable and not blockers(checks)
    return dict(engine_version=ENGINE_VERSION, checks=checks, summary=counts,
                baseline_checks=baseline_checks, baseline_summary=summarize(baseline_checks),
                baseline_usable=baseline_usable, approvable=approvable,
                conclusion='PASS' if approvable else ('FAIL' if counts['FAIL'] else 'UNDETERMINED'),
                scope_note='승인 항목표에 등록된 범위만 검사합니다. 센서 교정·공정 품질·고객 인수 합격을 보증하지 않습니다.')
