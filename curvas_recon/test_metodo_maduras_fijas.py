"""Metodo "Maduras fijas, nuevas absorben" y selector de metodo; sin SQL (fixtures de test_fixtures/)."""
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon import mensajes_pad as MP
from curvas_recon import pad_dashboard as dashboard
from curvas_recon import recon_engine as engine
from curvas_recon import reconciliacion_pad as RP
from curvas_recon.metodo_maduras_fijas import (METODO_DEFAULT, METODO_MADURAS_FIJAS, METODO_REPARTO, MetodoInfactible,
                                               aplicar_maduras_fijas)
from curvas_recon.sulfide_method import reconcile_sulfides

ROOT = Path(__file__).resolve().parents[1]
FX = json.loads((ROOT / 'test_fixtures/caso10009_sulfuros_net_inputs.json').read_text(encoding='utf-8'))
WS, WE, PREV = '2026-09-01', '2026-09-07', '2026-08-31'


def _setup(riego=1.0, pls=1.0, ratio=None):
    """Filas, resultado del metodo 1, objetivos globales coherentes con F29 (= target del fixture) y neto F29."""
    rows = FX['rows']
    result, audit = reconcile_sulfides(rows, WS, WE, FX['target_net_t'])
    priors = RP.window_priors(rows, WS, audit['lambda'])
    q_r = sum(p['x0'][0] for p in priors); f_r = sum(p['x0'][1] for p in priors)
    q_p = sum(p['x0'][2] for p in priors)
    net = FX['target_net_t']
    f_p_goal = f_r * riego + net / RP.K_F * 1.0             # fino de PLS que da F29 con el fino de riego del objetivo
    if ratio is not None:                                    # drenaje/riego global del objetivo
        q_p, pls = ratio * q_r * riego, 1.0
    targets = dict(q_riego_m3h_sum=q_r * riego, q_pls_m3h_sum=q_p * pls, cu_riego_g_l=f_r / q_r, cu_pls_g_l=f_p_goal / (q_p * pls))
    return rows, result, audit, targets, net


def test_default_method_in_the_selector_is_maduras_fijas_and_the_engine_default_is_unchanged():
    assert METODO_DEFAULT == METODO_MADURAS_FIJAS
    layout = dashboard._build_content_layout()
    found = [c for c in layout._traverse() if getattr(c, 'id', None) == 'curvas-recon-metodo']
    assert found and found[0].value == METODO_MADURAS_FIJAS
    assert [o['value'] for o in found[0].options] == [METODO_MADURAS_FIJAS, METODO_REPARTO]
    assert [o['label'] for o in found[0].options] == ['Maduras fijas, nuevas absorben', 'Reparto por aporte']


def test_maduras_fijas_keeps_mature_recovery_and_closed_days_and_closes_the_net_within_the_band():
    rows, result, audit, targets, net = _setup()
    out, audit2, msgs = aplicar_maduras_fijas(result, audit, rows, WS, WE, targets, net, banda=0.001)
    old, new = {(r['pile'], r['date']): r for r in result}, {(r['pile'], r['date']): r for r in out}
    mature = {k[1] for k in audit['mature']}; young = {k[1] for k in audit['young']}
    assert young == {'P24', 'P25'} and len(mature) == 16
    for (pile, d), r in new.items():
        if d < WS:                                              # dias de meses cerrados y previos: intactos
            assert r == old[(pile, d)]
        elif pile in mature:                                    # maduras: recuperacion acumulada exactamente la observada
            assert r['reconciled_pct'] == old[(pile, d)]['reconciled_pct']
    # neto diario de las maduras desde los flujos reconciliados == neto observado diario (invariante)
    for pile in mature:
        last = old[(pile, PREV)]['official_pct']; cu_tf = old[(pile, PREV)]['cu_apilado_t']
        for d in [f'2026-09-0{i}' for i in range(1, 8)]:
            r, o = new[(pile, d)], old[(pile, d)]['reconciled_pct']
            if o is None or r.get('fitted_q_drenaje_m3h') is None:
                continue
            net_flow = RP.K_F * (r['fitted_q_drenaje_m3h'] * r['cu_drenaje_recon_gL'] - r['q_riego_recon_m3h'] * r['cu_riego_recon_gL'])
            assert net_flow == pytest.approx(cu_tf * (o - last) / 100, abs=1e-6)
            last = o
    assert abs(audit2['curve_net_t'] / FX['target_net_t'] - 1) <= 0.0011
    assert audit2['metodo'] == METODO_MADURAS_FIJAS and audit2['banda'] == 0.001 and audit2['water_by_young'] == {}
    for p in young:                                             # la nueva absorbe: cambia respecto del metodo 1
        assert new[(p, WE)]['reconciled_pct'] != old[(p, WE)]['reconciled_pct']
    assert all(m['nivel'] in MP.NIVELES for m in msgs)


def test_maduras_fijas_infeasible_raises_with_operator_messages_and_unmet_anchor_blocks():
    rows, result, audit, targets, net = _setup(ratio=1.0103)
    with pytest.raises(MetodoInfactible) as e:
        aplicar_maduras_fijas(result, audit, rows, WS, WE, targets, net, banda=0.0005)
    assert e.value.mensajes and e.value.mensajes[0]['nivel'] == MP.ERROR
    with pytest.raises(MetodoInfactible) as e:
        aplicar_maduras_fijas(result, audit, rows, WS, WE, dict(targets, cu_pls_g_l=None), net)
    assert 'globales' in e.value.mensajes[0]['titulo']


def _material():
    return {'sulfide_inputs': dict(rows=deepcopy(FX['rows']), source_ids=dict(solver_run_id=1), target_period_start=WS)}


def _anchor(targets, net):
    return dict(net_cu_target_t=net, q_riego_recon=24 * targets['q_riego_m3h_sum'], q_pls_recon=24 * targets['q_pls_m3h_sum'],
                fino_riego_recon=targets['cu_riego_g_l'] * 24 * targets['q_riego_m3h_sum'] / 1000,
                fino_pls_recon=targets['cu_pls_g_l'] * 24 * targets['q_pls_m3h_sum'] / 1000)


def test_engine_default_is_unchanged_and_both_methods_have_the_same_output_format():
    _, _, _, targets, net = _setup()
    anchor = _anchor(targets, net)
    base = engine._reconcile_sulfide_local(WS, WE, _material(), anchor)
    explicit = engine._reconcile_sulfide_local(WS, WE, dict(_material(), sulfide_metodo='ajuste_local'), anchor)
    for k in ('recovery_rows', 'daily', 'piles', 'sulfide_audit'):
        assert explicit[k] == base[k]                           # regresion: sin metodo el motor no cambia ningun dato
    assert base['metodo_sulfuros'] == 'ajuste_local' and base['mensajes_pad'] == []
    for metodo in (METODO_MADURAS_FIJAS, METODO_REPARTO):
        m = engine._reconcile_sulfide_local(WS, WE, dict(_material(), sulfide_metodo=metodo), anchor)
        assert set(m) == set(base) and len(m['piles']) == len(base['piles']) and len(m['recovery_rows']) == len(base['recovery_rows'])
        assert m['metodo_sulfuros'] == metodo and m['local_direct_recovery'] and m['mensajes_pad']
        json.dumps(m['mensajes_pad']); json.dumps(m['sulfide_audit'], allow_nan=False, default=str)
        assert all(x['nivel'] in MP.NIVELES for x in m['mensajes_pad'])


def _both(band=0.001, **kw):
    rows, result, audit, targets, net = _setup(**kw)
    f2 = aplicar_maduras_fijas(result, audit, rows, WS, WE, targets, net, banda=band, fijar_maduras=True)
    f1 = aplicar_maduras_fijas(result, audit, rows, WS, WE, targets, net, banda=band, fijar_maduras=False)
    return result, audit, targets, net, f2, f1


def test_both_methods_close_against_the_same_absolute_targets_and_keep_closed_days():
    result, audit, targets, net, (r2, a2, _), (r1, a1, m1) = _both()
    for a in (a2, a1):
        d = a['concentration_match']['diferencia']
        assert all(abs(v) <= 0.001 + 1e-7 for v in d.values())                      # misma banda, mismos objetivos
        assert a['concentration_match']['objetivo'] == a2['concentration_match']['objetivo']
        assert a['tope_drenaje'] == 0.99 and all(p['drenaje_riego'] <= 0.99 + 1e-7 for p in a['por_pila'])
        assert abs(a['curve_net_t'] / net - 1) <= 0.0011
    old = {(r['pile'], r['date']): r for r in result}
    for out in (r2, r1):
        for r in out:
            if r['date'] < WS:
                assert r == old[(r['pile'], r['date'])]                              # dias de meses cerrados sin cambio
    assert a1['metodo'] == METODO_REPARTO and a2['metodo'] == METODO_MADURAS_FIJAS
    assert any(x['titulo'] == 'Las pilas maduras también se ajustan' for x in m1)


def test_method_2_keeps_mature_exact_and_method_1_moves_them_with_a_common_factor_except_where_limits_act():
    result, audit, targets, net, (r2, a2, _), (r1, a1, _) = _both()
    old = {(r['pile'], r['date']): r for r in result}
    mature = {k[1] for k in audit['mature']}
    new2 = {(r['pile'], r['date']): r for r in r2}; new1 = {(r['pile'], r['date']): r for r in r1}
    assert all(new2[(p, '2026-09-07')]['reconciled_pct'] == old[(p, '2026-09-07')]['reconciled_pct'] for p in mature)        # metodo 2: exactas
    assert any(abs(new1[(p, '2026-09-07')]['reconciled_pct'] - old[(p, '2026-09-07')]['reconciled_pct']) > 1e-6 for p in mature)   # metodo 1: se mueven
    por = {p['pile']: p for p in a1['por_pila']}
    free = [p for p in por.values() if p['drenaje_riego'] < 0.99 - 1e-6]                 # sin limite de drenaje activo
    assert len(free) >= 3
    for g in ('d_q_riego', 'd_q_pls'):
        vals = [1 + p[g] for p in free]
        assert max(vals) - min(vals) < 0.02                                              # factor comun (dentro de la tolerancia)
    assert abs(sum(p['neto_t'] for p in a1['por_pila']) / net - 1) <= 0.0011


def test_dashboard_shows_the_method_used_and_exports_it(monkeypatch):
    data = dict(metodo=METODO_MADURAS_FIJAS, metodo_etiqueta='Maduras fijas, nuevas absorben', metodo_aplicado='maduras_fijas', converged=True,
                caso_id=1, mensajes_pad=[], solver_run=dict(estado='validated'))
    from plotly.utils import PlotlyJSONEncoder
    r = json.dumps(dashboard._build_warnings(data), cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert 'Maduras fijas, nuevas absorben' in r
    from dash._callback_context import context_value
    from dash._utils import AttributeDict
    token = context_value.set(AttributeDict(**{'triggered_inputs': [{'prop_id': 'curvas-recon-store.data'}], 'inputs_list': []}))
    try:
        badge, _ = dashboard.update_status_badge(dict(data, caso_id=1), 1)
    finally:
        context_value.reset(token)
    assert 'Maduras fijas, nuevas absorben' in badge
    from curvas_recon import report_metodo
    import tempfile, os
    import pandas as pd
    assert 'meta' in report_metodo.escribir_libro.__code__.co_varnames


def test_solver_run_state_is_optional(monkeypatch):
    monkeypatch.setattr(dashboard, 'load_solver_run_meta', lambda _: (_ for _ in ()).throw(RuntimeError('sin BD')))
    assert dashboard._solver_run_or_none(10009) is None


def _capture_solve(monkeypatch, metodo):
    """compute_recon hasta la llamada al motor, con pilas nuevas en Sulfuros; devuelve los materiales que recibe el motor."""
    from unittest.mock import Mock
    case = dict(id=7, run_id=70, nombre='con nuevas', fecha_inicio='2026-09-01', fecha_fin='2026-09-07', modelo_codigo='m', modelo_version='v', total_flujos=1)
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
    monkeypatch.setattr(dashboard, 'pilas_jovenes', lambda *a, **kw: {'P24': '2026-08-15'})        # HAY pilas nuevas
    monkeypatch.setattr(dashboard, 'prepare_recon_inputs', lambda *a, **kw: ({'SULFUROS': {'riego': None, 'cu_riego': None, 'drena_cu': None}, 'OXIDOS': {}}, {}))
    monkeypatch.setattr(dashboard, 'connect', Mock())
    monkeypatch.setattr(dashboard, 'reconcile_week_flowsheet_dash', solve)
    import curvas_recon.sulfide_db_inputs as dbi, curvas_recon.sulfide_inputs as si
    loader = Mock(return_value=dict(source_ids=dict(solver_run_id=70), rows=[], target_period_start='2026-09-01'))
    monkeypatch.setattr(si, 'load_sulfide_inputs', loader)
    monkeypatch.setattr(dbi, 'make_source_provider', lambda *a, **k: None)
    monkeypatch.setattr(dbi, 'load_saved_profile', lambda *a, **k: {})
    monkeypatch.setattr(dashboard, 'load_cu_riego', lambda *a, **k: None)
    monkeypatch.setattr(dashboard, 'load_drena_cu', lambda *a, **k: None)
    monkeypatch.setattr(dashboard, 'DATA_SU', {}); monkeypatch.setattr(dashboard, 'inicio_campana', lambda *a, **k: {})
    dashboard.compute_recon(1, 7, metodo)
    return seen['materials']['SULFUROS'], loader


def test_both_selector_options_use_the_local_sulfide_package_with_their_own_flag(monkeypatch):
    for metodo in (METODO_REPARTO, METODO_MADURAS_FIJAS):
        mat, loader = _capture_solve(monkeypatch, metodo)
        assert mat['sulfide_metodo'] == metodo and 'sulfide_inputs' in mat and loader.called
    mat, _ = _capture_solve(monkeypatch, None)                                 # llamada directa sin selector: ajuste local de siempre
    assert mat['sulfide_metodo'] == 'ajuste_local' and 'sulfide_inputs' in mat

