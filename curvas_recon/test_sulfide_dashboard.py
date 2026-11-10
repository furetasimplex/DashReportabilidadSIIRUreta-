"""Offline regression of the active direct-recovery path; SQL is forbidden."""
from copy import deepcopy
from io import BytesIO
import sys
from pathlib import Path
import re
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon import recon_engine as engine, pad_dashboard as dashboard
from curvas_recon.sulfide_inputs import load_sulfide_inputs
from curvas_recon.sulfide_presentation import (direct_series, direct_member, solution_figures, trial_bars,
                                               trial_workbook, recovery_figure)


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
    q_med, q_rec, pls_med, pls_rec = flow.data                 # riego medido/reconciliado y PLS medido/reconciliado
    assert list(pls_med.y) == pytest.approx([0.95 * v for v in q_med.y]) and 'medido' in pls_med.name
    assert list(pls_rec.y) == list(pls_med.y)                  # madura: sin ajuste, el reconciliado es el medido
    assert any(v is not None for v in concentrations.data[1].y)
    assert [len(trial_bars(res, tab).data) for tab in ('tab-rec', 'tab-flujo', 'tab-cus')] == [2, 4, 4]
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
    monkeypatch.setattr(dashboard, '_save_recon_raw', lambda *args: 'offline-test-token')
    monkeypatch.setattr(dashboard, 'pilas_jovenes', lambda *args, **kw: {'P24': '2026-08-15', 'P25': '2026-09-01'})
    import curvas_recon.sulfide_inputs as inputs_module
    import curvas_recon.sulfide_db_inputs as db_inputs_module
    original_loader = inputs_module.load_sulfide_inputs
    monkeypatch.setattr(inputs_module, 'load_sulfide_inputs',
                        lambda ws, we, cid, anchor, source_provider=None: original_loader(ws, we, cid, anchor))
    monkeypatch.setattr(db_inputs_module, 'make_source_provider', lambda *args, **kw: None)
    monkeypatch.setattr(db_inputs_module, 'load_saved_profile', lambda *args, **kw: {})
    monkeypatch.setattr(dashboard, 'load_cu_riego', lambda *args, **kw: None)
    monkeypatch.setattr(dashboard, 'load_drena_cu', lambda *args, **kw: None)
    monkeypatch.setattr(dashboard, 'DATA_SU', {})
    monkeypatch.setattr(dashboard, 'inicio_campana', lambda *args, **kw: {})
    forbid = Mock(side_effect=AssertionError('SQL persistence forbidden'))
    monkeypatch.setattr(engine, 'reconcile_week_flowsheet_db', forbid)
    data, modal, _ = dashboard.compute_recon(1, 10009)
    assert modal is False
    assert data['local_direct_recovery']
    assert data['sulfide_audit']['source_ids']['solver_run_id'] == 10082
    assert len(data['SULFUROS']['ss']) == 16
    json.dumps(data, allow_nan=False)
    forbid.assert_not_called()


def test_without_young_piles_falls_back_to_distribution(monkeypatch):
    """Sin curvas nuevas no se carga el paquete de ajuste: se usa la distribucion."""
    case = dict(id=7, run_id=70, nombre='sin nuevas', fecha_inicio='2026-09-01',
                fecha_fin='2026-09-07', modelo_codigo='m', modelo_version='v', total_flujos=1)
    seen = {}

    def solve(ws, materials, *args, **kwargs):
        seen['materials'] = materials
        raise RuntimeError('stop after capture')

    monkeypatch.setattr(dashboard, '_refresh_case_catalog', lambda: None)
    monkeypatch.setattr(dashboard, '_caso_by_id', lambda _: case)
    monkeypatch.setattr(dashboard, 'load_caso_anchor', lambda *a: {'SULFUROS': {}})
    monkeypatch.setattr(dashboard, 'diagnose_caso_anchor', lambda _: [])
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda: None)
    monkeypatch.setattr(dashboard, '_refresh_primary_recovery_curves', lambda: None)
    monkeypatch.setattr(dashboard, 'WIP_META', {'SULFUROS': {}, 'OXIDOS': {}})
    monkeypatch.setattr(dashboard, 'REC_META', {'SULFUROS': ({}, {}, {}), 'OXIDOS': ({}, {}, {})})
    monkeypatch.setattr(dashboard, 'pilas_jovenes', lambda *a, **kw: {})
    monkeypatch.setattr(dashboard, 'prepare_recon_inputs',
                        lambda *a, **kw: ({'SULFUROS': {}, 'OXIDOS': {}}, {}))
    monkeypatch.setattr(dashboard, 'connect', Mock())
    monkeypatch.setattr(dashboard, 'reconcile_week_flowsheet_dash', solve)
    loader = Mock(side_effect=AssertionError('ajuste neto no aplica sin curvas nuevas'))
    monkeypatch.setattr('curvas_recon.sulfide_inputs.load_sulfide_inputs', loader)
    dashboard.compute_recon(1, 7)
    assert seen['materials']['SULFUROS'] == {'sulfide_policy': 'legacy'}
    loader.assert_not_called()


def test_pilas_jovenes_uses_first_irrigation_age_at_case_end(monkeypatch):
    days = lambda *d: pd.DatetimeIndex(d)
    riego = {'P24': days('2026-09-01', '2026-09-07'), 'P23': days('2026-09-01'),
             'P20': days('2026-09-01'), 'P09': days('2026-08-01')}
    monkeypatch.setattr(engine, '_fechas_actividad', lambda label: (riego, {}))
    monkeypatch.setattr(engine, 'inicio_campana', lambda label, we: {
        'P24': pd.Timestamp('2026-08-15'), 'P23': pd.Timestamp('2026-08-08'),
        'P20': pd.Timestamp('2026-08-07'), 'P09': pd.Timestamp('2026-07-01')})
    young = engine.pilas_jovenes('SULFUROS', '2026-09-01', '2026-09-07')
    assert sorted(young) == ['P23', 'P24']   # P23 tiene exactamente 30 dias; P09 no riega en la ventana


def test_new_pile_without_measured_recovery_still_calculates_and_draws():
    """P26 en octubre: pila nueva sin lecturas medidas en la ventana (el calculo la ajusta)."""
    from curvas_recon.sulfide_db_inputs import build_sulfide_rows, make_source_provider
    from curvas_recon.test_sulfide_db_inputs import case10009_series
    fx, material, curves, wip, first, saved = case10009_series()
    curves[25] = {'dates': [d for d in curves[25]['dates'] if d <= pd.Timestamp('2026-08-31').date()],
                  'values': curves[25]['values'][:len([d for d in curves[25]['dates'] if d <= pd.Timestamp('2026-08-31').date()])]}
    provider = make_source_provider(material, curves, wip, first, {'run_id': 10082}, saved_profile=saved)
    anchor = {'SULFUROS': {'net_cu_target_t': fx['target_net_t']}}
    inputs = load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, anchor, source_provider=provider)
    assert all(r['observed_pct'] is None for r in inputs['rows'] if r['pile'] == 'P25' and r['date'] >= '2026-09-01')
    res = engine.reconcile_week_flowsheet_dash('2026-09-01', {'SULFUROS': {'sulfide_inputs': inputs}}, None, None,
                                               week_end='2026-09-07', anchor=anchor, caso_id=10009)['res']
    for tab in ('tab-rec', 'tab-flujo', 'tab-cus'):
        trial_bars(res, tab)                                    # antes: TypeError en tab-rec
    figure = trial_bars(res, 'tab-rec')
    measured = dict(zip(figure.data[0].x, figure.data[0].y))
    assert measured['SU-P25'] is not None and measured['SU-P24'] is not None   # P25 sin lectura: estimado con 0,95 x riego
    assert 'SU-P25' in figure.layout.annotations[0].text and 'sin lectura' in figure.layout.annotations[0].text
    series = direct_series(res, 'SULFUROS', 25)
    assert all(y is None for x, y in zip(series['xs'], series['measured_ys']) if x >= pd.Timestamp('2026-09-01'))
    assert all(y is not None for y in series['ys'])             # la curva reconciliada si existe
    assert trial_workbook(res, {'id': 10009, 'run_id': 10082})



def oxide_pile(label='OXIDOS', parcela='P01'):
    """Pila de Oxidos con la forma de las filas diarias del motor (medido y reconciliado)."""
    days = pd.date_range('2026-09-01', '2026-09-07')
    daily = [dict(label=label, parcela=parcela, date=d, q_riego_medido=100.0, q_pls_medido=95.0,
                  cu_riego_medido=0.4, cu_pls_medido=2.0, fino_riego_medido=40.0, fino_pls_medido=190.0,
                  q_riego_final=105.0, q_pls_final=98.0, cu_riego_recon=0.41, cu_pls_recon=2.1,
                  fino_riego_final=43.0, fino_pls_final=205.8) for d in days]
    return dict(label=label, parcela=parcela, daily=daily), daily


def test_bars_show_measured_and_reconciled_for_oxide_piles_too(result):
    res = dict(result['res'])
    pile, daily = oxide_pile()
    res['piles'] = [pile] + list(res['piles'])
    res['daily'] = daily + list(res['daily'])
    keys = {tab: dict(zip(trial_bars(res, tab).data[0].x, zip(*[t.y for t in trial_bars(res, tab).data])))
            for tab in ('tab-rec', 'tab-flujo', 'tab-cus')}
    measured, reconciled = keys['tab-rec']['OX-P01']
    assert measured == pytest.approx(0.024 * 7 * (190.0 - 40.0)) and reconciled == pytest.approx(0.024 * 7 * (205.8 - 43.0))
    assert all(v is not None for tab in keys.values() for values in tab.values() for v in values)   # ninguna barra vacia
    assert keys['tab-flujo']['OX-P01'] == pytest.approx((100 * 24 * 7, 105 * 24 * 7, 95 * 24 * 7, 98 * 24 * 7))
    assert len(keys['tab-rec']) == 19 and 'SU-P26' not in keys['tab-rec']        # Oxidos + las 18 de Sulfuros
    assert all(all(v is not None for v in values) for values in keys['tab-rec'].values())


def test_delta_cards_are_filled_for_the_sulfide_method(result):
    res = result['res']
    for key in ('q_pls_medido', 'q_pls_recon', 'cu_fino_riego_medido', 'cu_fino_riego_recon',
                'cu_fino_pls_medido', 'cu_fino_pls_recon', 'delta_recon_riego', 'delta_recon_pls',
                'delta_fino_riego', 'delta_fino_pls'):
        assert res[key] is not None, key
    assert res['delta_recon_riego'] == 0 and res['delta_fino_riego'] == 0       # riego y Cu medidos se conservan
    # El Cu neto reconciliado menos el medido es lo que el metodo agrega: 196.5 t en el Caso 10009.
    assert 0.024 * res['delta_fino_pls'] == pytest.approx(196.5, abs=0.2)
    totals = {k: res[k] for k in ('q_riego_medido', 'q_pls_medido', 'delta_recon_riego', 'delta_recon_pls',
                                  'cu_fino_riego_medido', 'delta_fino_riego', 'cu_fino_pls_medido', 'delta_fino_pls')}
    tiles = str(dashboard._build_kpis(dict(base_row={}, n_activas=18, n_nuevas=2), totals))
    assert 'N/A' not in tiles and '+0.0%' in tiles


def test_charts_show_one_official_series_before_the_window_and_both_inside(result):
    res = result['res']
    history = [dict(date=pd.Timestamp('2026-08-30') + pd.Timedelta(days=i), q=90.0 + i, q_pls=80.0 + i,
                    cu_riego=0.3, cu_drena=1.5) for i in range(2)]          # 30 y 31-ago, antes de la ventana
    flow, concentrations = solution_figures(res, 'SULFUROS', 24, history)
    for figure, row_names in ((flow, ('Riego', 'PLS')), (concentrations, ('Cu riego', 'Cu PLS'))):
        by_name = {}
        for trace in figure.data:
            by_name.setdefault(trace.name.split(' (')[0] if trace.name.startswith('Oficial') else trace.name, []).append(trace)
        official = [t for t in figure.data if t.name.startswith('Oficial')]
        assert len(official) == 2 and all(max(t.x) < pd.Timestamp('2026-09-01') for t in official)
        inside = [t for t in figure.data if not t.name.startswith('Oficial')]
        assert len(inside) == 4 and all(min(t.x) >= pd.Timestamp('2026-09-01') for t in inside)
        assert {t.name.split('(')[-1].rstrip(')').split(',')[0] for t in inside} >= {'medido', 'reconciliado'}
    # una pila joven: el PLS reconciliado (ajustado) difiere del medido
    pls_med, pls_rec = flow.data[-2], flow.data[-1]
    assert list(pls_rec.y) != list(pls_med.y)
    recovery = recovery_figure(res, 'SULFUROS', 24, ())
    names = [t.name for t in recovery.data]
    assert names == ['Oficial (histórico)', 'Medido', 'Reconciliado']
    assert max(recovery.data[0].x) < pd.Timestamp('2026-09-01') and min(recovery.data[2].x) >= pd.Timestamp('2026-08-31')


def test_progress_and_error_texts_have_no_broken_accents():
    source = Path(dashboard.__file__).read_text(encoding='utf-8')
    assert 'Reconciliación pendiente' in source and 'Reconciliaci?n' not in source
    assert 'conexión' in source and 'conexi?n' not in source
    assert not re.search(r"'[^'\n]*[A-Za-záéíóúñ]\?[A-Za-záéíóúñ][^'\n]*'", "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith('#') and 're.' not in line and '(?' not in line))


def _sulfide_result(anchor_extra, tolerance=0.001):
    """Caso 10009 por el motor, con objetivos globales de flujo opcionales en el ancla."""
    from curvas_recon.sulfide_db_inputs import make_source_provider
    from curvas_recon.test_sulfide_db_inputs import case10009_series
    fx, material, curves, wip, first, saved = case10009_series()
    provider = make_source_provider(material, curves, wip, first, {'run_id': 10082}, saved_profile=saved)
    base = {'SULFUROS': {'net_cu_target_t': fx['target_net_t']}}
    inputs = load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, base, source_provider=provider)
    anchor = {'SULFUROS': dict(base['SULFUROS'], **anchor_extra)}
    previous, engine.SULFIDE_CONC_TOLERANCE = engine.SULFIDE_CONC_TOLERANCE, tolerance    # banda de tolerancia del ajuste
    try:
        return engine.reconcile_week_flowsheet_dash('2026-09-01', {'SULFUROS': {'sulfide_inputs': inputs}}, None, None,
                                                    week_end='2026-09-07', anchor=anchor, caso_id=10009)['res']
    finally:
        engine.SULFIDE_CONC_TOLERANCE = previous


def _pad_totals(res):
    """Masas y ponderadas del pad como las entrega el agregador de grupos (PLS de maduras = 0.95 x riego)."""
    from curvas_recon.group_solution_series import aggregate_group_solution_series
    members = {}
    for entry in res['daily']:
        q, qp = entry['q_riego_final'], entry['q_pls_final']
        members.setdefault(entry['parcela'], {})[pd.Timestamp(entry['date'])] = dict(
            q_riego=q, q_pls=qp if qp is not None else 0.95 * q,
            cu_riego=entry['cu_riego_recon'], cu_pls=entry['cu_pls_recon'])
    days = aggregate_group_solution_series(members)
    q_r, q_p = sum(d['q_riego'] for d in days), sum(d['q_pls'] for d in days)
    return dict(q_riego=q_r * 24, q_pls=q_p * 24,
                cu_riego=sum(d['q_riego'] * d['cu_riego'] for d in days) / q_r,
                cu_pls=sum(d['q_pls'] * d['cu_pls'] for d in days) / q_p)


F29_TARGET = 1069.137402


def _global_flows(base, riego_mass=1.0, pls_mass=1.0, cu_pls=1.0, riego_drift=0.0, riego_exact=False):
    """Objetivos globales consistentes con F29: masa de riego y de PLS como multiplos de lo que da el pad
    sin ajuste, Cu de PLS escalado, y Cu fino de riego = PLS - F29 (mas una deriva opcional)."""
    t = _pad_totals(base)
    q_r, q_p = t['q_riego'] * riego_mass, t['q_pls'] * pls_mass
    fino_p = t['cu_pls'] * cu_pls * q_p / 1000
    fino_r = t['cu_riego'] * q_r / 1000 if riego_exact else (fino_p - F29_TARGET) * (1 + riego_drift)
    return dict(q_riego_recon=q_r, fino_riego_recon=fino_r, q_pls_recon=q_p, fino_pls_recon=fino_p)


YOUNG = {'P24', 'P25'}


def test_pad_matches_global_flows_masses_and_concentrations_changing_only_new_piles():
    base = _sulfide_result({}, tolerance=1e-12)                           # tolerancia ~0: igualdad exacta
    goal = _global_flows(base, 0.998, 1.002, 1.001)                       # diferencias de ~0,2 % contra lo medido
    res = _sulfide_result(goal, tolerance=1e-12)
    match = res['sulfide_audit']['concentration_match']
    assert match['status'] == 'aplicado' and match['con_masas']
    assert all(0.7 <= match[k] <= 1.3 for k in ('beta', 'alpha_riego', 'alpha_pls'))
    t = _pad_totals(res)
    assert t['q_riego'] == pytest.approx(goal['q_riego_recon'], rel=1e-9)                       # masa de riego global
    assert t['q_pls'] == pytest.approx(goal['q_pls_recon'], rel=1e-9)                           # masa de drenaje global
    assert t['cu_pls'] == pytest.approx(1000 * goal['fino_pls_recon'] / goal['q_pls_recon'], rel=1e-9)
    assert t['cu_riego'] == pytest.approx(match['cu_riego_pad_g_l_despues'], rel=1e-9)
    assert match['diferencia_cu_riego_relativa'] < 0.05                                          # el Cu de riego absorbe el resto
    assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)                 # F29 exacto
    assert res['q_riego_recon'] == pytest.approx(goal['q_riego_recon'] / 24, rel=1e-9) and res['delta_recon_riego'] < 0
    for new, old in zip(res['daily'], base['daily']):
        if new['parcela'] not in YOUNG:                                                         # maduras intactas
            assert (new['q_riego_final'], new['cu_riego_recon'], new['cu_pls_recon'], new['q_pls_final']) == (
                old['q_riego_final'], old['cu_riego_recon'], old['cu_pls_recon'], old['q_pls_final'])
        else:                                                                                    # el medido se conserva aparte
            assert new['q_riego_medido'] == old['q_riego_medido'] and new['cu_riego_medido'] == old['cu_riego_medido']
            assert new['q_riego_final'] != old['q_riego_final']
    rec = {(r['pile'], r['date']): r['reconciled_pct'] for r in res['recovery_rows']}
    old_rec = {(r['pile'], r['date']): r['reconciled_pct'] for r in base['recovery_rows']}
    assert all(rec[k] == old_rec[k] for k in rec if k[0] not in YOUNG)                           # recuperacion de maduras igual
    assert res['delta_fino_riego'] != 0 and res['delta_recon_pls'] != base['delta_recon_pls']


def test_inconsistency_between_global_flows_and_f29_is_absorbed_by_irrigation_concentration_and_reported():
    base = _sulfide_result({})
    ok = _sulfide_result(_global_flows(base, 1, 1, 1))['sulfide_audit']['concentration_match']
    assert ok['status'] == 'aplicado'                                    # PLS - riego global difiere de F29: se informa la diferencia
    assert 0 < ok['diferencia_cu_riego_relativa'] < 0.05
    bad = _sulfide_result(_global_flows(base, 1, 1, 1, riego_drift=0.08))['sulfide_audit']['concentration_match']
    assert bad['status'] == 'no_aplicado' and 'cierre de F29' in bad['motivo']


def test_global_flows_beyond_the_limit_are_reported_not_forced():
    base = _sulfide_result({})
    cr0, cp0 = _pad_totals(base)['cu_riego'], _pad_totals(base)['cu_pls']
    real_run_10082 = dict(q_riego_recon=716982.6, fino_riego_recon=41.232979, q_pls_recon=724392.8, fino_pls_recon=1112.4752)
    for extra in (real_run_10082, _global_flows(base, 0.99, 1.01, 1.005)):         # 1 % de masa ya exige cambiar las nuevas > 30 %
        res = _sulfide_result(extra)
        match = res['sulfide_audit']['concentration_match']
        assert match['status'] == 'no_aplicado' and match['motivo']
        assert res['sulfide_audit']['lambda'] == pytest.approx(base['sulfide_audit']['lambda'])     # sin forzar nada
        assert _pad_totals(res)['cu_riego'] == pytest.approx(cr0) and _pad_totals(res)['cu_pls'] == pytest.approx(cp0)
        assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_pad_already_matching_the_global_flows_is_left_alone():
    base = _sulfide_result({})
    res = _sulfide_result(_global_flows(base, 1.0, 1.0, 1.0, riego_exact=True))
    assert res['sulfide_audit']['concentration_match']['status'] == 'sin_cambio'
    assert res['delta_fino_riego'] == 0 and res['delta_recon_riego'] == 0


def test_concentration_only_matching_when_the_global_masses_are_not_given():
    from curvas_recon.sulfide_method import match_pad_flows
    day = lambda q, cr, cd, prof=None: dict(q_riego_m3h=q, cu_riego_gL=cr, cu_drenaje_gL=cd, profile_q_drenaje_m3h=prof)
    mature, young = [day(100.0, 0.4, 2.0)] * 5, [day(100.0, 0.4, 20.0, 50.0)] * 5
    held = 0.024 * 5 * (0.95 * 100 * 2.0 - 100 * 0.4)
    rows = dict(mature=mature, young=young)
    before = match_pad_flows(rows, held, held + 10.0, dict(cu_riego_g_l=1.0, cu_pls_g_l=1.0), 0.30, 1e-9)
    goals = dict(cu_riego_g_l=0.995 * before['cu_riego_pad_g_l_antes'], cu_pls_g_l=0.99 * before['cu_pls_pad_g_l_antes'])
    match = match_pad_flows(rows, held, held + 10.0, goals, 0.30, 1e-9)
    assert match['status'] == 'aplicado' and not match['con_masas'] and match['beta'] == 1.0
    assert match['cu_riego_pad_g_l_despues'] == pytest.approx(goals['cu_riego_g_l'])
    assert match['cu_pls_pad_g_l_despues'] == pytest.approx(goals['cu_pls_g_l'])
    assert match_pad_flows(rows, held, held + 10.0, {}, 0.30, 1e-9)['status'] == 'sin_objetivos'



def test_tolerance_band_leaves_alone_a_pad_that_is_already_inside_it():
    assert engine.SULFIDE_CONC_TOLERANCE == 0.10                      # tolerancia vigente en el dash: 10 %, no cero
    base = _sulfide_result({}, tolerance=0.10)
    for goal in (_global_flows(base, 0.998, 1.002, 1.001),            # ~0,2 %
                 _global_flows(base, 0.96, 1.04, 1.05, riego_exact=True)):   # hasta ~5 %: sigue dentro de la banda
        res = _sulfide_result(goal, tolerance=0.10)
        assert res['sulfide_audit']['concentration_match']['status'] == 'sin_cambio'
        assert res['sulfide_audit']['lambda'] == pytest.approx(base['sulfide_audit']['lambda'])
        assert _pad_totals(res) == pytest.approx(_pad_totals(base))                               # no se movio nada
        assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_pad_just_outside_the_band_is_moved_only_to_the_edge_not_to_the_exact_value():
    base = _sulfide_result({}, tolerance=0.10)
    cp0 = _pad_totals(base)['cu_pls']
    goal = _global_flows(base, 1.0, 1.0, 1 / 1.1005, riego_exact=True)   # el Cu de PLS del pad queda 10,05 % sobre el global
    res = _sulfide_result(goal, tolerance=0.10)
    match = res['sulfide_audit']['concentration_match']
    assert match['status'] == 'aplicado'
    exact = 1000 * goal['fino_pls_recon'] / goal['q_pls_recon']
    edge = exact * 1.10
    assert match['objetivo_efectivo']['cu_pls_g_l'] == pytest.approx(edge)
    assert _pad_totals(res)['cu_pls'] == pytest.approx(edge, rel=1e-9)                            # llega al borde de la banda...
    assert abs(_pad_totals(res)['cu_pls'] - exact) / exact == pytest.approx(0.10, abs=1e-9)       # ...y no a la igualdad exacta
    assert _pad_totals(res)['cu_pls'] < cp0                                                       # se movio muy poco
    assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)
