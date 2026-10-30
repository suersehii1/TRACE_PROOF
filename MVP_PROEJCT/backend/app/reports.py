"""저장된 판정 스냅샷으로 보고서를 만든다. 내보낼 때 재검사하거나 판정을 바꾸지 않는다."""
import csv
import io
from html import escape

LABELS = {'PASS': '통과', 'FAIL': '실패', 'NOT_TESTED': '미실시', 'UNDETERMINED': '판단불가',
          'PENDING': '검토 대기', 'HOLD': '보류', 'APPROVED': '검토 승인'}


def safe_csv(value):
    text = str(value)
    # Excel에서 고객 입력을 수식으로 실행하지 않도록 문자열 접두어를 붙인다.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def csv_report(validation):
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['항목', '규칙', '검사', '판정', '기대 기준', '관측 결과', '원본 측정 행'])
    for c in validation.result['checks']:
        writer.writerow([safe_csv(x) for x in [c['parameter_id'], c['rule'], c['title'], LABELS[c['status']],
                                             c['expected'], c['observed'], ', '.join(map(str, c['rows']))]])
    return '\ufeff' + buffer.getvalue()


def html_report(v, baseline, candidate):
    e = lambda value: escape(str(value))
    summary = v.result['summary']
    rows = ''.join('<tr>' + ''.join(f'<td>{e(x)}</td>' for x in [c['parameter_id'], c['title'], LABELS[c['status']],
                    c['expected'], c['observed'], ', '.join(map(str, c['rows']))]) + '</tr>' for c in v.result['checks'])
    audits = ''.join(f"<li>{e(a['at'])} · {e(a['reviewer'])} · {e(LABELS[a['disposition']])}: {e(a['note'])}</li>" for a in v.reviews)
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>TraceProof 검증 보고서 #{v.id}</title><style>
    body{{font:14px/1.7 system-ui,sans-serif;color:#182b3d;max-width:1100px;margin:36px auto;padding:0 20px}}
    h1{{font-size:26px}}table{{width:100%;border-collapse:collapse;font-size:12px}}td,th{{border:1px solid #dbe3eb;padding:9px;text-align:left;word-break:break-word}}
    th{{background:#edf3f7}}.meta{{background:#f3f7fa;padding:16px}}code{{overflow-wrap:anywhere}}@media print{{body{{margin:0}}thead{{display:table-header-group}}tr{{break-inside:avoid}}}}
    </style><h1>장비 데이터 변경 검증 보고서 #{v.id}</h1>
    <p>TraceProof · 생성 {e(v.created_at.isoformat())} · 검사 엔진 {e(v.result['engine_version'])}</p>
    <div class="meta">장비: {e(candidate.equipment_id)}<br>기준: {e(baseline.label)} / {e(baseline.software_version)}<br>
    비교: {e(candidate.label)} / {e(candidate.software_version)}<br>승인 항목표: {e(v.profile_snapshot['name'])} ({e(v.profile_snapshot['version'])})<br>
    검사 결과: {e(LABELS[v.result['conclusion']])} · 검토 상태: {e(LABELS[v.review_status])}<br>
    기준 데이터 사용 가능: {'예' if v.result['baseline_usable'] else '아니오 — 기준 데이터부터 확인 필요'}<br>
    통과 {summary['PASS']} / 실패 {summary['FAIL']} / 미실시 {summary['NOT_TESTED']} / 판단불가 {summary['UNDETERMINED']}</div>
    <h2>검사 범위와 한계</h2><p>{e(v.result['scope_note'])} 표본 수신 간격은 원천 센서 측정 정확도와 다릅니다. 원본 행 번호는 JSON measurements 배열의 1부터 시작하는 번호입니다.</p>
    <h2>원본 증거</h2><p>기준 파일: {e(baseline.filename)}<br><code>SHA-256 {e(baseline.sha256)}</code><br>
    비교 파일: {e(candidate.filename)}<br><code>SHA-256 {e(candidate.sha256)}</code></p>
    <p><a href="/api/releases/{baseline.id}/raw">기준 원본 다운로드</a> · <a href="/api/releases/{candidate.id}/raw">비교 원본 다운로드</a></p>
    <h2>검사 상세</h2><table><thead><tr><th>항목</th><th>검사</th><th>판정</th><th>기대 기준</th><th>관측 결과</th><th>원본 행</th></tr></thead><tbody>{rows}</tbody></table>
    <h2>검토 이력</h2><ul>{audits or '<li>아직 검토되지 않았습니다.</li>'}</ul>
    <p>검토 승인은 위 합의 범위에 대한 담당자 확인이며 고객 인수·출하 승인이나 공인 인증이 아닙니다. 브라우저의 인쇄 메뉴에서 PDF로 저장할 수 있습니다.</p></html>'''
