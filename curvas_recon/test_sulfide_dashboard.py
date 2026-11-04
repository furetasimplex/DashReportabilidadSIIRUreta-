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


def _sulfide_result(anchor_extra):
    """Caso 10009 por el motor, con objetivos globales de flujo opcionales en el ancla."""
    from curvas_recon.sulfide_db_inputs import make_source_provider
    from curvas_recon.test_sulfide_db_inputs import case10009_series
    fx, material, curves, wip, first, saved = case10009_series()
    provider = make_source_provider(material, curves, wip, first, {'run_id': 10082}, saved_profile=saved)
    base = {'SULFUROS': {'net_cu_target_t': fx['target_net_t']}}
    inputs = load_sulfide_inputs('2026-09-01', '2026-09-07', 10009, base, source_provider=provider)
    anchor = {'SULFUROS': dict(base['SULFUROS'], **anchor_extra)}
    return engine.reconcile_week_flowsheet_dash('2026-09-01', {'SULFUROS': {'sulfide_inputs': inputs}}, None, None,
                                                week_end='2026-09-07', anchor=anchor, caso_id=10009)['res']


def _pad_weighted(res):
    """Ponderadas del pad como las calcula el agregador de grupos (PLS de maduras = 0.95 x riego)."""
    from curvas_recon.group_solution_series import aggregate_group_solution_series
    members = {}
    for entry in res['daily']:
        q, qp = entry['q_riego_final'], entry['q_pls_final']
        members.setdefault(entry['parcela'], {})[pd.Timestamp(entry['date'])] = dict(
            q_riego=q, q_pls=qp if qp is not None else 0.95 * q,
            cu_riego=entry['cu_riego_recon'], cu_pls=entry['cu_pls_recon'])
    days = aggregate_group_solution_series(members)
    q_r = sum(d['q_riego'] for d in days)
    q_p = sum(d['q_pls'] for d in days)
    return (sum(d['q_riego'] * d['cu_riego'] for d in days) / q_r, sum(d['q_pls'] * d['cu_pls'] for d in days) / q_p)


def test_weighted_concentrations_match_global_flows_by_changing_only_new_piles():
    cr0, cp0 = _pad_weighted(_sulfide_result({}))
    cr_goal, cp_goal = 0.995 * cr0, 1.005 * cp0                      # diferencia pequena contra los flujos globales
    res = _sulfide_result(dict(q_riego_recon=700000.0, fino_riego_recon=cr_goal * 700.0,
                               q_pls_recon=690000.0, fino_pls_recon=cp_goal * 690.0))
    match = res['sulfide_audit']['concentration_match']
    assert match['status'] == 'aplicado' and 0.7 <= match['alpha_riego'] <= 1.3 and 0.7 <= match['alpha_pls'] <= 1.3
    assert _pad_weighted(res) == pytest.approx((cr_goal, cp_goal), rel=1e-9)             # igualan al global
    assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)          # F29 sigue cerrando
    base = _sulfide_result({})
    young = {'P24', 'P25'}
    for new, old in zip(res['daily'], base['daily']):
        if new['parcela'] not in young:                                                    # maduras intactas
            assert (new['cu_riego_recon'], new['cu_pls_recon'], new['q_pls_final']) == (
                old['cu_riego_recon'], old['cu_pls_recon'], old['q_pls_final'])
        else:                                                                              # nuevas: medido se conserva aparte
            assert new['cu_riego_medido'] == old['cu_riego_medido'] and new['cu_riego_recon'] != old['cu_riego_recon']
    rec = {(r['pile'], r['date']): r['reconciled_pct'] for r in res['recovery_rows']}
    old_rec = {(r['pile'], r['date']): r['reconciled_pct'] for r in base['recovery_rows']}
    assert all(rec[k] == old_rec[k] for k in rec if k[0] not in young)                     # recuperacion de maduras igual
    assert res['delta_fino_riego'] != 0                                                    # la tarjeta ya refleja el cambio


def test_global_targets_beyond_the_limit_are_reported_not_forced():
    base = _sulfide_result({})
    cr0, cp0 = _pad_weighted(base)
    for extra in (dict(q_riego_recon=716982.6, fino_riego_recon=41.232979, q_pls_recon=724392.8, fino_pls_recon=1112.4752),  # run 10082
                  dict(q_riego_recon=700000.0, fino_riego_recon=0.981 * cr0 * 700.0,
                       q_pls_recon=690000.0, fino_pls_recon=1.02 * cp0 * 690.0)):                                        # +-2 %
        res = _sulfide_result(extra)
        match = res['sulfide_audit']['concentration_match']
        assert match['status'] == 'no_aplicado' and match['motivo']
        assert res['sulfide_audit']['lambda'] == pytest.approx(base['sulfide_audit']['lambda'])    # sin forzar nada
        assert _pad_weighted(res) == pytest.approx((cr0, cp0))
        assert res['sulfide_audit']['net_residual_t'] == pytest.approx(0, abs=1e-9)


def test_concentrations_already_matching_the_global_flows_are_left_alone():
    cr0, cp0 = _pad_weighted(_sulfide_result({}))
    res = _sulfide_result(dict(q_riego_recon=700000.0, fino_riego_recon=cr0 * 700.0 * 1.0005,
                               q_pls_recon=690000.0, fino_pls_recon=cp0 * 690.0))
    assert res['sulfide_audit']['concentration_match']['status'] == 'sin_cambio'
    assert res['delta_fino_riego'] == 0
