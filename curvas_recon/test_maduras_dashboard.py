"""Ensayo neto local para Oxidos y Sulfuros de un Caso generico (SQL simulado)."""
import json
from datetime import date
from unittest.mock import Mock

import pandas as pd
import pytest

from curvas_recon import pad_dashboard as dashboard, recon_engine as engine
from curvas_recon.maduras_inputs import load_pad_inputs
from curvas_recon.maduras_nuevas import direct_recovery_series
from curvas_recon.sulfide_presentation import direct_series, trial_workbook
from curvas_recon.test_maduras_inputs import (
    CASE, END, FakeDB, FakeEngine, H, S, SOLVER_RUN, START,
)

FLOW = {'OXIDOS': 'F25', 'SULFUROS': 'F29'}


def anchors(db):
    return {pad: {'net_cu_target_t': db.targets[flow], 'net_cu_target_flow': flow}
            for pad, flow in FLOW.items()}


def sql_loader(db):
    def load(ws, we, caso, anchor, label):
        return load_pad_inputs(ws, we, caso['id'], label, anchor, expected_run_id=caso['run_id'],
                               engine=FakeEngine(db), schema=S, hidro_schema=H)
    return load


@pytest.fixture
def joint(monkeypatch):
    forbidden = Mock(side_effect=AssertionError('SQL persistence forbidden'))
    monkeypatch.setattr(engine, 'reconcile_week_flowsheet_db', forbidden)
    db = FakeDB()
    anchor = anchors(db)
    load = sql_loader(db)
    case = dict(id=CASE, run_id=SOLVER_RUN)
    materials = {pad: {'maduras_inputs': load(pd.Timestamp(START), pd.Timestamp(END), case, anchor, pad)}
                 for pad in ('SULFUROS', 'OXIDOS')}
    result = engine.reconcile_week_flowsheet_dash(
        START.isoformat(), materials, None, None, week_end=END.isoformat(), anchor=anchor, caso_id=CASE)
    assert not forbidden.called
    return db, result


def test_both_pads_close_their_own_net_target_locally(joint):
    db, result = joint
    res = result['res']
    assert res['local_direct_recovery'] and result['_phase_seconds']['persist'] == 0
    audits = res['maduras_audit']
    assert set(audits) == {'SULFUROS', 'OXIDOS'}
    assert audits['SULFUROS']['lambda'] == pytest.approx(0.75)
    assert audits['OXIDOS']['lambda'] == pytest.approx(0.65)      # lambda propio por PAD
    for pad, flow in FLOW.items():
        assert audits[pad]['curve_net_t'] == pytest.approx(db.targets[flow], abs=1e-9)
        assert res['net_cu_by_label'][pad]['target_t'] == pytest.approx(db.targets[flow])
        assert abs(res['net_cu_by_label'][pad]['residual_t']) < 1e-9
        sub = result['materials'][pad]
        assert set(sub['transient']) == {'P05', 'P06'}
        assert set(sub['ss']) == {'P01', 'P02'} and sub['fixed_transient'] == ['P04']
    assert res['sulfide_audit'] is not None


def test_direct_recovery_series_serves_both_pads_for_the_report(joint):
    _, result = joint
    series = direct_recovery_series(result['res'])
    assert {pad for pad, _ in series} == {'SULFUROS', 'OXIDOS'}
    assert ('OXIDOS', 6) in series and ('SULFUROS', 1) in series
    ox5 = series[('OXIDOS', 5)]
    assert ox5.index.min() < pd.Timestamp(START) and ox5.index.max() == pd.Timestamp(END)
    old = direct_series(result['res'], 'OXIDOS', 5)
    assert list(ox5.values) == pytest.approx(old['ys'])           # misma serie que pinta la UI
    # Mature: conserva exacto lo observado en la ventana.
    rows = [r for r in result['res']['recovery_rows'] if r['pad'] == 'OXIDOS' and r['pile'] == 'P01'
            and START.isoformat() <= r['date'] <= END.isoformat()]
    assert rows and all(r['reconciled_pct'] == r['observed_pct'] for r in rows)
    # La pila que nace en la ventana no tiene puntos anteriores a su nacimiento.
    assert series[('SULFUROS', 6)].index.min() == pd.Timestamp('2026-09-04')


def test_workbook_exports_each_pad(joint):
    _, result = joint
    from io import BytesIO
    wb = pd.read_excel(BytesIO(trial_workbook(result['res'], {'id': CASE, 'run_id': SOLVER_RUN})), sheet_name=None)
    assert {'Recuperacion Sulfuros', 'Recuperacion Oxidos', 'Flujos', 'Fuentes y alcance'} <= set(wb)
    assert set(wb['Recuperacion Oxidos']['pad']) == {'OXIDOS'}


def _compute(monkeypatch, db, anchor):
    case = dict(id=CASE, run_id=SOLVER_RUN, nombre='Caso generico', fecha_inicio=START.isoformat(),
                fecha_fin=END.isoformat(), modelo_codigo='hidrometalurgia_125_v2',
                modelo_version='v2', total_flujos=125)
    monkeypatch.setattr(dashboard, '_refresh_case_catalog', lambda: None)
    monkeypatch.setattr(dashboard, '_caso_by_id', lambda _: case)
    monkeypatch.setattr(dashboard, 'load_caso_anchor', lambda *args: anchor)
    monkeypatch.setattr(dashboard, 'diagnose_caso_anchor', lambda _: [])
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda: None)
    monkeypatch.setattr(dashboard, '_refresh_primary_recovery_curves', lambda: None)
    monkeypatch.setattr(dashboard, 'WIP_META', {'SULFUROS': {}, 'OXIDOS': {}})
    monkeypatch.setattr(dashboard, 'REC_META', {'SULFUROS': ({}, {}, {}), 'OXIDOS': ({}, {}, {})})
    monkeypatch.setattr(dashboard, 'prepare_recon_inputs', lambda *a, **k: (
        {pad: {'riego': None, 'cu_riego': None, 'drena_cu': None} for pad in ('SULFUROS', 'OXIDOS')}, {}))
    monkeypatch.setattr(dashboard, 'compute_wz_week', lambda *a, **k: {})
    monkeypatch.setattr(dashboard, 'connect', Mock())
    monkeypatch.setattr(dashboard, '_save_recon_raw', lambda *a: 'offline-test-token')
    monkeypatch.setattr(dashboard, '_load_net_trial_inputs', sql_loader(db))
    monkeypatch.setattr(engine, 'reconcile_week_flowsheet_db',
                        Mock(side_effect=AssertionError('SQL persistence forbidden')))
    return dashboard.compute_recon(1, CASE)


def test_compute_recon_runs_any_case_for_both_pads_without_writes(monkeypatch):
    db = FakeDB()
    data, modal, _ = _compute(monkeypatch, db, anchors(db))
    assert modal is False
    assert data['local_direct_recovery'] and data['sulfide_policy'] == 'net_trial'
    assert '10009' not in json.dumps(data) and 'Sulfuros:' not in data['method']
    assert set(data['maduras_audit']) == {'SULFUROS', 'OXIDOS'}
    assert len(data['OXIDOS']['ss']) == 2 and len(data['SULFUROS']['transient']) == 2
    json.dumps(data, allow_nan=False)
    assert all(sql.lstrip().upper().startswith(('SELECT', 'WITH')) for sql, _ in db.statements)


def test_compute_recon_infeasible_target_is_reported_not_replaced(monkeypatch):
    db = FakeDB()
    db.flows['F25'] = db.targets['F25'] = db.targets['F25'] + 500.0       # inalcanzable con las nuevas
    data, modal, body = _compute(monkeypatch, db, anchors(db))
    assert modal is True and data is dashboard.dash.no_update
    assert 'inalcanzable' in str(body)


def test_compute_recon_source_failure_is_reported_not_replaced(monkeypatch):
    db = FakeDB()
    db.runs = []
    data, modal, body = _compute(monkeypatch, db, anchors(db))
    assert modal is True and 'run de asignacion' in str(body)


def test_policy_ui_text_is_generic():
    text = str(dashboard._build_content_layout())
    assert '10009' not in text and 'Metodologia de curvas' in text
    assert 'Oxidos y Sulfuros' in text
