"""가상의 장비 원시 자료를 만든다. 실제 고객·공정 데이터는 사용하지 않는다."""
import copy
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parent
PARAMETERS = [
    dict(id='TEMP_PV', name='공정 온도', unit='C', minimum=150, maximum=200, interval_ms=1000),
    dict(id='PRESSURE', name='챔버 압력', unit='Pa', minimum=90, maximum=110, interval_ms=1000),
    dict(id='FLOW', name='가스 유량', unit='sccm', minimum=45, maximum=55, interval_ms=1000),
    dict(id='POWER', name='RF 전력', unit='W', minimum=400, maximum=600, interval_ms=1000),
    dict(id='VIBRATION', name='진동 참고값', unit='mm/s', minimum=None, maximum=None, interval_ms=1000),
]


def write(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def generate():
    profile = dict(name='데모 식각 장비 출하 데이터 기준', version='1.0', equipment_id='EQ-DEMO-01',
                   scenario='NORMAL_RUN', allowed_run_ids=['RUN-001'], allowed_chambers=['CH-A'],
                   parameters=[dict(**p, required=True, min_samples=6, interval_tolerance=0.2) for p in PARAMETERS])
    start = datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc)
    base_values = {'TEMP_PV': [170, 172, 174, 175, 173, 171], 'PRESSURE': [100, 101, 99, 100, 102, 100],
                   'FLOW': [50, 51, 50, 49, 50, 51], 'POWER': [500, 505, 510, 508, 502, 500],
                   'VIBRATION': [1.2, 1.3, 1.2, 1.1, 1.2, 1.3]}
    baseline = dict(manifest=dict(equipment_id='EQ-DEMO-01', label='기준 버전 · v1.0.0', software_version='1.0.0',
                                 config_version='CFG-001', scenario='NORMAL_RUN', tester_software_version='1.0.0'), measurements=[])
    for p in PARAMETERS:
        for index, value in enumerate(base_values[p['id']]):
            baseline['measurements'].append(dict(parameter_id=p['id'], timestamp=(start + timedelta(seconds=index)).isoformat(),
                                                  value=value, unit=p['unit'], run_id='RUN-001', chamber='CH-A'))
    healthy = copy.deepcopy(baseline)
    healthy['manifest'].update(label='정상 수정 버전 · v1.1.1', software_version='1.1.1', config_version='CFG-003', tester_software_version='1.1.1')
    for row in healthy['measurements']:
        if row['parameter_id'] == 'TEMP_PV':
            row['value'] += 1
    faulty = copy.deepcopy(baseline)
    faulty['manifest'].update(label='결함 수정 버전 · v1.1.0', software_version='1.1.0', config_version='CFG-002')
    faulty['measurements'] = [r for r in faulty['measurements'] if r['parameter_id'] != 'FLOW']
    for row in faulty['measurements']:
        if row['parameter_id'] == 'TEMP_PV':
            row['unit'] = 'F'
            row['value'] = round(row['value'] * 1.8 + 32, 1)
        if row['parameter_id'] == 'POWER':
            row['run_id'] = 'RUN-999'
            row['value'] = 900
    pressure = [r for r in faulty['measurements'] if r['parameter_id'] == 'PRESSURE']
    pressure[3]['timestamp'] = pressure[2]['timestamp']
    vibration = [r for r in faulty['measurements'] if r['parameter_id'] == 'VIBRATION']
    vibration[0]['timestamp'] = '2026-10-30T00:00:00'  # 시차 정보가 없어 판단불가여야 한다.
    write('profile.json', profile)
    for name, data in [('baseline', baseline), ('faulty', faulty), ('healthy', healthy)]:
        write(name + '.json', data)
    print('데모 기준과 원시 자료 3종 생성 완료')


if __name__ == '__main__':
    generate()
