import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'curvas_recon' / 'sulfide_inputs.py'
SPEC = importlib.util.spec_from_file_location('staged_sulfide_inputs', MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def anchor():
    return {'SULFUROS': {'net_cu_target_t': 1069.137402}}


def test_captured_case_identity_and_daily_inputs_are_returned():
    loaded = module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor())
    assert loaded['source_ids']['solver_run_id'] == 10082
    assert loaded['source_ids']['allocation_profile_run_id'] == 2348
    assert loaded['source_ids']['fixture_sha256'] == module._FIXTURE_SHA256
    assert loaded['target_period_start'] == '2026-09-01'
    assert loaded['target_net_t'] == pytest.approx(1069.137402)
    assert any(row['date'] == '2026-08-31' for row in loaded['rows'])
    case_rows = [row for row in loaded['rows'] if row['date'] >= '2026-09-01']
    assert case_rows and all('q_riego_m3h' in row for row in case_rows)
    assert all('not measured' in row['drainage_profile_source'].lower() for row in case_rows)


@pytest.mark.parametrize('case_id,start,end', [
    (10013, '2026-09-01', '2026-09-07'),
    (10009, '2026-09-02', '2026-09-07'),
    (10009, '2026-09-01', '2026-09-08'),
])
def test_unsupported_case_or_window_fails_closed(case_id, start, end):
    with pytest.raises(module.SulfideInputError):
        module.load_sulfide_inputs(start, end, case_id, anchor())


def test_missing_anchor_or_mismatched_target_fails_closed():
    with pytest.raises(module.SulfideInputError, match='anchor'):
        module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, {})
    with pytest.raises(module.SulfideInputError, match='does not match'):
        module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009,
                                   {'net_cu_target_t': 999.})


def test_injected_provider_must_prove_run_identity_and_complete_coverage():
    fixture = json.loads((ROOT / 'test_fixtures' / 'caso10009_sulfuros_net_inputs.json')
                         .read_text(encoding='utf-8'))
    meta = fixture['metadata']
    payload = {
        'rows': fixture['rows'], 'target_net_t': fixture['target_net_t'],
        'target_period_start': '2026-09-01',
        'source_ids': {'case_id': meta['case_id'], 'solver_run_id': meta['solver_run_id'],
                       'allocation_profile_run_id': meta['allocation_profile_run_id']},
    }
    seen = {}

    def provider(**kwargs):
        seen.update(kwargs)
        return payload

    loaded = module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009,
                                        anchor(), source_provider=provider)
    assert loaded['rows'] == fixture['rows']
    assert seen['case_id'] == 10009
    assert seen['week_start'].isoformat() == '2026-09-01'

    stale = dict(payload, source_ids=dict(payload['source_ids'], allocation_profile_run_id=2349))
    with pytest.raises(module.SulfideInputError, match='allocation_profile_run_id'):
        module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor(),
                                   source_provider=lambda **_: stale)

    incomplete_rows = [row for row in fixture['rows'] if row['date'] != '2026-09-03']
    incomplete = dict(payload, rows=incomplete_rows)
    with pytest.raises(module.SulfideInputError, match='complete Case coverage'):
        module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor(),
                                   source_provider=lambda **_: incomplete)


def test_fixture_tamper_fails_hash_check(tmp_path):
    bad = tmp_path / 'tampered.json'
    bad.write_text('{}', encoding='utf-8')
    with pytest.raises(module.SulfideInputError, match='hash mismatch'):
        module.load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor(),
                                   fixture_path=bad)
