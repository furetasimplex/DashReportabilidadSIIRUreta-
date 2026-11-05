"""Offline regression of the active direct-recovery path; SQL is forbidden."""
from copy import deepcopy
from io import BytesIO
import sys
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon import recon_engine as engine, pad_dashboard as dashboard
from curvas_recon.sulfide_inputs import load_sulfide_inputs
from curvas_recon.sulfide_presentation import direct_series, direct_member, solution_figures, trial_bars, trial_workbook


@pytest.fixture
def result(monkeypatch):
    forbidden = Mock(side_effect=AssertionError('SQL persistence/read forbidden'))
    monkeypatch.setattr(engine, 'reconcile_week_flowsheet_db', forbidden)
    monkeypatch.setattr(dashboard, 'connect', forbidden)
    anchor = {'SULFUROS': {'net_cu_target_t': 1069.137402}}
    inputs = load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor)
    joint = engine.reconcile_week_flowsheet_dash(
        '2026-09-01', {'SULFUROS': {'sulfide_inputs': inputs}}, None, None,
        week_end='2026-09-07', anchor=anchor, caso_id=10009)
    assert not forbidden.called
    return joint


def test_real_case_closes_without_modifying_mature_recovery(result):
    res = result['res']
    assert res['sulfide_audit']['lambda'] == pytest.approx(.7214427195956585)
    assert res['daily_net_cu_t'] == pytest.approx(1069.137402)
    assert len(result['materials']['SULFUROS']['ss']) == 16
    assert set(result['materials']['SULFUROS']['transient']) == {'P24', 'P25'}
    for r in res['recovery_rows']:
        if r['recovery_source'] == 'observed':
            assert r['reconciled_pct'] == r['observed_pct']
        if r['date'] < '2026-09-01':
            assert r['reconciled_pct'] == r['official_pct']
    for p in res['piles']:
        if p['parcela'] not in ('P24', 'P25'):
            assert all(d['q_pls_final'] is None for d in p['daily'])
    assert result['_phase_seconds']['persist'] == 0


def test_direct_charts_groups_and_workbook_keep_values_and_unknown_drainage(result, monkeypatch):
    res = result['res']
    series = direct_series(res, 'SULFUROS', 7)
    raw = {'res': res}
    assert dashboard._reconstructed_campaign_series('SULFUROS', 7, '2026-09-01', '2026-09-07', raw=raw) == series
    group = dashboard._combined_member_series('rsu-P07', raw, pd.Timestamp('2026-09-01'), pd.Timestamp('2026-09-07'))
    assert group['cu_tf_t'] == series['cu_tf']
    assert group['reconciled_series']['ys'] == [v for d,v in zip(series['xs'],series['ys']) if d >= pd.Timestamp('2026-09-01')]
    flow, concentrations = solution_figures(res, 'SULFUROS', 7)
    assert all(v is None for v in flow.data[1].y)
    assert any(v is not None for v in concentrations.data[1].y)
    for tab in ('tab-rec', 'tab-flujo', 'tab-cus'):
        assert len(trial_bars(res, tab).data) == 2
    wb = pd.read_excel(BytesIO(trial_workbook(res, {'id': 10009, 'run_id': 10082})), sheet_name=None)
    table = wb['Recuperacion Sulfuros']
    mature = table[table['recovery_source'] == 'observed']
    assert (mature['reconciled_pct'] == mature['observed_pct']).all()
    assert 'Fuentes y alcance' in wb
    assert len(res['recovery_rows']) == 640
    assert sum(r['date'] < '2026-09-01' for r in res['recovery_rows']) == 514


def test_actual_group_builder_and_older_campaign_context(result, monkeypatch):
    raw = {'res': result['res']}
    data = {'local_direct_recovery': True}
    ws, we = pd.Timestamp('2026-09-01'), pd.Timestamp('2026-09-07')
    monkeypatch.setattr(dashboard, '_FULL_DATA_READY', True)
    monkeypatch.setattr(dashboard, '_store_matches_case', lambda *args: True)
    monkeypatch.setattr(dashboard, '_get_group_raw', lambda *args: raw)
    monkeypatch.setattr(dashboard, '_store_window', lambda *args: (ws, we, 7))
    cycles = [{'dates': [pd.Timestamp('2026-07-25')], 'values': [60.123]}]
    monkeypatch.setattr(dashboard, '_measured_cycles', lambda *args: cycles)
    fig, message = dashboard._build_combined_recovery_chart(
        {'members': ['rsu-P07', 'rsu-P08'], 'name': 'Prueba grupo'}, data, 10009)
    assert fig.data
    assert any(pd.Timestamp('2026-07-25') in trace.x for trace in fig.data)
    series = dashboard._reconstructed_campaign_series('SULFUROS', 7, ws, we, raw=raw)
    assert series['ys'][0] == 60.123
    assert series['sources'][0] == 'Historico medido (contexto de campana)'


def test_sql_entrypoint_rejects_direct_payload_before_save(result, monkeypatch):
    from curvas_recon import db_pipeline
    forbidden = Mock(side_effect=AssertionError('SQL write forbidden'))
    monkeypatch.setattr(db_pipeline, 'save_run', forbidden)
    # Restore the unpatched implementation from the module source via fixture's
    # monkeypatch context would be unnecessary; the public DB method is tested
    # in a separate test below with a fresh import binding.
    import importlib.util
    spec = importlib.util.spec_from_file_location('curvas_recon._engine_guard_test', engine.__file__)
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    with pytest.raises(RuntimeError, match='persistencia SQL'):
        independent.reconcile_week_flowsheet_db('2026-09-01', {}, None,
            week_end='2026-09-07', res=result['res'])
    forbidden.assert_not_called()


def test_compute_callback_connects_validated_inputs_and_serializes_local_result(monkeypatch):
    import json
    case = dict(id=10009, run_id=10082, nombre='1-7 septiembre',
                fecha_inicio='2026-09-01', fecha_fin='2026-09-07',
                modelo_codigo='hidrometalurgia_125_v2', modelo_version='v2', total_flujos=125)
    monkeypatch.setattr(dashboard, '_refresh_case_catalog', lambda: None)
    monkeypatch.setattr(dashboard, '_caso_by_id', lambda _: case)
    monkeypatch.setattr(dashboard, 'load_caso_anchor', lambda *args: {'SULFUROS': {'net_cu_target_t': 1069.137402}})
    monkeypatch.setattr(dashboard, 'diagnose_caso_anchor', lambda _: [])
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda: None)
    monkeypatch.setattr(dashboard, '_refresh_primary_recovery_curves', lambda: None)
    monkeypatch.setattr(dashboard, 'WIP_META', {'SULFUROS': {}, 'OXIDOS': {}})
    monkeypatch.setattr(dashboard, 'REC_META', {'SULFUROS': ({}, {}, {}), 'OXIDOS': ({}, {}, {})})
    monkeypatch.setattr(dashboard, 'prepare_recon_inputs', lambda *args, **kw: ({'SULFUROS': {'riego': None, 'cu_riego': None, 'drena_cu': None}}, {}))
    monkeypatch.setattr(dashboard, 'compute_wz_week', lambda *args, **kw: {})
    monkeypatch.setattr(dashboard, 'connect', Mock())
    # The generic loader is SELECT-only SQL; here the frozen Case 10009 bundle stands in for it.
    monkeypatch.setattr(dashboard, '_load_net_trial_inputs',
                        lambda ws, we, caso, anchor, label: (
                            load_sulfide_inputs(ws, we, caso['id'], anchor) if label == 'SULFUROS' else None))
    monkeypatch.setattr(dashboard, '_save_recon_raw', lambda *args: 'offline-test-token')
    forbid = Mock(side_effect=AssertionError('SQL persistence forbidden'))
    monkeypatch.setattr(engine, 'reconcile_week_flowsheet_db', forbid)
    data, modal, _ = dashboard.compute_recon(1, 10009)
    assert modal is False
    assert data['local_direct_recovery']
    assert data['sulfide_audit']['source_ids']['solver_run_id'] == 10082
    assert len(data['SULFUROS']['ss']) == 16
    json.dumps(data, allow_nan=False)
    forbid.assert_not_called()


def test_case10009_regression_through_generic_core_and_report_interface(result):
    """Caso 10009 congelado: mismas cifras de la auditoria con el nucleo generico."""
    from curvas_recon.maduras_nuevas import direct_recovery_series, reconcile_pad
    res = result['res']
    audit = res['sulfide_audit']
    assert audit['lambda'] == pytest.approx(0.7214427195956585, rel=1e-12)
    assert audit['curve_net_t'] == pytest.approx(1069.137402, abs=1e-6)
    assert abs(audit['net_residual_t']) < 1e-6
    assert res['maduras_audit']['SULFUROS']['lambda'] == audit['lambda']
    series = direct_recovery_series(res)
    assert set(series) == {('SULFUROS', n) for n in [7, 8] + list(range(10, 26))}
    end = pd.Timestamp('2026-09-07')
    assert series[('SULFUROS', 24)][end] == pytest.approx(15.847805, abs=5e-7)
    assert series[('SULFUROS', 25)][end] == pytest.approx(5.480463, abs=5e-7)
    for r in res['recovery_rows']:
        if r['recovery_source'] == 'observed':
            assert series[('SULFUROS', int(r['pile'][1:]))][pd.Timestamp(r['date'])] == r['observed_pct']
    # El nucleo generico y el contrato historico entregan lo mismo.
    inputs = load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, {'SULFUROS': {'net_cu_target_t': 1069.137402}})
    _, direct = reconcile_pad(inputs['rows'], '2026-09-01', '2026-09-07', 1069.137402, pad='SULFUROS')
    assert direct['lambda'] == audit['lambda']
