"""승인에 영향을 주는 업무 경계를 검사한다. 판정의 정확성을 직접 확인한다."""
import copy
import json
import os
from pathlib import Path
import pytest
from app.validation import compare_releases, inspect_release

RAW = Path(os.getenv('RAW_DATA_DIR', Path(__file__).resolve().parents[2] / 'RAW_DATA'))


def load(name):
    return json.loads((RAW / f'{name}.json').read_text(encoding='utf-8'))


def test_healthy_is_approvable_but_unconfigured_range_is_not_tested():
    result = compare_releases(load('baseline'), load('healthy'), load('profile'))
    assert result['approvable'] is True
    assert result['summary'] == {'PASS': 30, 'FAIL': 0, 'NOT_TESTED': 1, 'UNDETERMINED': 0}
    assert any(c['parameter_id'] == 'VIBRATION' and c['status'] == 'NOT_TESTED' and not c['required'] for c in result['checks'])


def test_faulty_data_detects_known_errors_without_false_pass():
    result = compare_releases(load('baseline'), load('faulty'), load('profile'))
    by_rule = {(c['parameter_id'], c['rule']): c for c in result['checks']}
    assert not result['approvable']
    for key in [('_manifest', 'VERSION'), ('TEMP_PV', 'UNIT'), ('PRESSURE', 'TIME'), ('FLOW', 'PRESENCE'), ('POWER', 'RUN'), ('POWER', 'RANGE')]:
        assert by_rule[key]['status'] == 'FAIL'
    assert by_rule[('VIBRATION', 'TIME')]['status'] == 'UNDETERMINED'
    assert by_rule[('TEMP_PV', 'RANGE')]['status'] == 'UNDETERMINED'
    assert by_rule[('FLOW', 'UNIT')]['status'] == 'NOT_TESTED'
    assert len(result['checks']) == 31  # 결측으로 검사 분모가 줄어들지 않아야 한다.


def test_bad_baseline_cannot_authorize_healthy_candidate():
    bad = load('baseline')
    bad['measurements'][0]['run_id'] = 'WRONG'
    result = compare_releases(bad, load('healthy'), load('profile'))
    assert not result['baseline_usable']
    assert not result['approvable']
    assert result['conclusion'] == 'UNDETERMINED'


def test_other_scenario_is_rejected():
    candidate = load('healthy')
    candidate['manifest']['scenario'] = 'OTHER_RECIPE'
    with pytest.raises(ValueError):
        compare_releases(load('baseline'), candidate, load('profile'))


def test_unknown_parameter_requires_confirmation():
    candidate = load('healthy')
    extra = copy.deepcopy(candidate['measurements'][0])
    extra['parameter_id'] = 'UNREGISTERED'
    candidate['measurements'].append(extra)
    result = compare_releases(load('baseline'), candidate, load('profile'))
    assert not result['approvable']
    assert result['checks'][-1]['status'] == 'UNDETERMINED'


@pytest.mark.parametrize('timestamp', [None, 'not-a-date', '2026-10-30T00:00:00'])
def test_missing_or_naive_time_does_not_pass(timestamp):
    candidate = load('healthy')
    candidate['measurements'][0]['timestamp'] = timestamp
    result = inspect_release(candidate, load('profile'))
    assert next(c for c in result if c['parameter_id'] == 'TEMP_PV' and c['rule'] == 'TIME')['status'] == 'UNDETERMINED'
