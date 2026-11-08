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


def test_engine_reparto_is_identical_to_before_and_maduras_fijas_has_the_same_output_format():
    _, _, _, targets, net = _setup()
    anchor = _anchor(targets, net)
    base = engine._reconcile_sulfide_local(WS, WE, _material(), anchor)
    explicit = engine._reconcile_sulfide_local(WS, WE, dict(_material(), sulfide_metodo=METODO_REPARTO), anchor)
    for k in ('recovery_rows', 'daily', 'piles', 'sulfide_audit'):
        assert explicit[k] == base[k]                           # regresion: el metodo 1 no cambia ningun dato
    assert base['metodo_sulfuros'] == METODO_REPARTO and base['mensajes_pad'] == []
    m2 = engine._reconcile_sulfide_local(WS, WE, dict(_material(), sulfide_metodo=METODO_MADURAS_FIJAS), anchor)
    assert set(m2) == set(base) and len(m2['piles']) == len(base['piles']) and len(m2['recovery_rows']) == len(base['recovery_rows'])
    assert m2['metodo_sulfuros'] == METODO_MADURAS_FIJAS and m2['local_direct_recovery'] and m2['mensajes_pad']
    json.dumps(m2['mensajes_pad']); json.dumps(m2['sulfide_audit'], allow_nan=False, default=str)
    # mensajes de cada metodo: avisos de tope/factores/brecha solo en maduras fijas; avisos del motor solo en reparto
    assert all(m['nivel'] in MP.NIVELES for m in m2['mensajes_pad']) and m2['mensajes_pad']
    assert not any('maduras fijas' in w.lower() for w in base['warnings'])


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


def test_option_reparto_uses_the_general_engine_for_all_sulfide_piles_even_with_new_piles(monkeypatch):
    mat, loader = _capture_solve(monkeypatch, METODO_REPARTO)
    assert mat.get('sulfide_policy') == 'legacy' and 'sulfide_inputs' not in mat and 'sulfide_metodo' not in mat and not loader.called         # sin ajuste local de nuevas: motor general, todas las pilas


def test_option_maduras_fijas_and_no_selector_keep_the_local_sulfide_package(monkeypatch):
    mat, loader = _capture_solve(monkeypatch, METODO_MADURAS_FIJAS)
    assert mat['sulfide_metodo'] == METODO_MADURAS_FIJAS and 'sulfide_inputs' in mat and loader.called
    mat, _ = _capture_solve(monkeypatch, None)                                 # llamada directa sin selector: ajuste local de siempre
    assert mat['sulfide_metodo'] == 'ajuste_local' and 'sulfide_inputs' in mat


EXCEL_10009 = ROOT / 'auditorias' / 'verificacion_metodo_pad_20261107' / 'datos_caso_10009.xlsx'
FINAL_10009 = ROOT / 'auditorias' / 'mejora_solver_redondeo_20261107' / 'final' / 'res_despues_10009_b0.0_defaults.csv'


@pytest.mark.skipif(not (EXCEL_10009.exists() and FINAL_10009.exists()), reason='Excel del Caso 10009 y resultado final del solver (locales, no versionados)')
def test_option_reparto_adjusts_mature_piles_proportionally_to_their_flow_contribution():
    """Con el Excel del Caso (sin SQL): las maduras de Sulfuros SI reciben ajuste, proporcional a su caudal."""
    import subprocess
    code = r'''
import sys, json
sys.path.insert(0, %r); sys.path.insert(0, %r)
import pandas as pd
from curvas_recon import extraccion_caso as EC
_o = EC.read_workbook
def rw(path, *a, **k):
    D = _o(path, *a, **k)
    v = pd.read_csv(%r).set_index('Codigo')
    f = D['flows'].copy(); m = f['codigo_flujo'].isin(v.index)
    f.loc[m, 'masa_reconciliada'] = f.loc[m, 'codigo_flujo'].map(v['Masa recon']); f.loc[m, 'fino_cu_reconciliado'] = f.loc[m, 'codigo_flujo'].map(v['Fino recon Cu'])
    D['flows'] = f
    return D
EC.read_workbook = rw
import dash_con_excel as X
D, caso, P = X.install(%r)
cap = {}
P._save_recon_raw = lambda res, c, w, e: cap.update(res=res) or 'tok'
P.compute_recon(1, int(caso['id']), 'reparto')
d = [x for x in cap['res']['daily'] if x['label'] == 'SULFUROS']
ratio = {}
for x in d:
    if x['dia_ciclo'] > 30 and x['q_riego_medido']:
        ratio.setdefault(x['parcela'], [0, 0]); ratio[x['parcela']][0] += x['q_riego_final']; ratio[x['parcela']][1] += x['q_riego_medido']
dq = {p: a / b - 1 for p, (a, b) in ratio.items()}
dm = {x['parcela']: sum(y['d_riego'] for y in d if y['parcela'] == x['parcela']) for x in d if x['dia_ciclo'] > 30}
print('RESULT:' + json.dumps(dict(n=len(dq), dq=dq, dm=dm, local=bool(cap['res'].get('local_direct_recovery')))))
''' % (str(ROOT), str(ROOT / 'scripts'), str(FINAL_10009), str(EXCEL_10009))
    import json as _j
    out = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=str(ROOT), env=dict(__import__('os').environ, PYTHONPATH=str(ROOT)))
    assert 'RESULT:' in out.stdout, out.stderr[-1500:]
    res = _j.loads(next(l for l in out.stdout.splitlines() if l.startswith('RESULT:'))[7:])
    assert res['n'] >= 10 and not res['local']                               # motor general, no el ajuste local
    assert any(abs(v) > 1e-4 for v in res['dq'].values())                    # las maduras SI cambian
    assert all(abs(v) > 1e-9 for v in res['dm'].values())
    # proporcional al aporte: mayor caudal => mayor ajuste absoluto (el relativo es casi uniforme)
    vals = list(res['dq'].values())
    assert max(vals) - min(vals) < 0.02
