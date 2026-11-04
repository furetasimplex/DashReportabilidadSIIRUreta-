"""Reconciliacion del pad con la recuperacion de las maduras fija (fuera del dash); sin SQL."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curvas_recon.reconciliacion_pad import K_F, reconcile_pad, window_priors
from curvas_recon.sulfide_db_inputs import build_sulfide_rows
from curvas_recon.sulfide_method import reconcile_sulfides
from curvas_recon.test_sulfide_db_inputs import case10009_series


def setup_case():
    fx, material, curves, wip, first, saved = case10009_series()
    rows, _ = build_sulfide_rows('2026-09-01', '2026-09-07', material, curves, wip, first, saved)
    target = fx['target_net_t']
    out, audit = reconcile_sulfides(rows, '2026-09-01', '2026-09-07', target)
    young = {k[1] for k in audit['young']}
    rec = {(r['pile'], r['date']): r for r in out}
    nets = {p: wip[p]['CuTf'] * (rec[(p, '2026-09-07')]['reconciled_pct'] - rec[(p, '2026-08-31')]['official_pct']) / 100
            for p in wip if p not in young}
    priors = window_priors(rows, '2026-09-01', audit['lambda'])
    return priors, nets, target, young


def pad_of(priors):
    q_r = sum(p['x0'][0] for p in priors); f_r = sum(p['x0'][1] for p in priors)
    q_p = sum(p['x0'][2] for p in priors); f_p = sum(p['x0'][3] for p in priors)
    return q_r, f_r, q_p, f_p


def targets_from(priors, riego=1.0, pls=1.0, cu_riego=1.0, cu_pls=1.0):
    q_r, f_r, q_p, f_p = pad_of(priors)
    return dict(q_riego_m3h_sum=q_r * riego, q_pls_m3h_sum=q_p * pls, cu_riego_g_l=f_r / q_r * cu_riego, cu_pls_g_l=f_p / q_p * cu_pls)


def test_pad_reaches_global_flows_within_the_band_with_mature_recoveries_fixed():
    priors, nets, _, young = setup_case()
    goal = targets_from(priors, 0.99, 1.01, 1.003, 0.997)                       # diferencias de ~1 % contra lo medido
    f_r_goal, f_p_goal = goal['cu_riego_g_l'] * goal['q_riego_m3h_sum'], goal['cu_pls_g_l'] * goal['q_pls_m3h_sum']
    net_goal = K_F * (f_p_goal - f_r_goal)                                        # F29 consistente con los flujos globales
    solution = reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001)
    assert solution['status'] == 'ok'
    pad, diff = solution['pad'], solution['diferencia']
    assert all(abs(diff[k]) <= 0.001 + 1e-9 for k in ('masa_riego_m3', 'masa_pls_m3', 'cu_riego_g_l', 'cu_pls_g_l', 'neto_t'))
    mature = [p for p in solution['por_pila'] if not p['young']]
    assert len(mature) == len(nets) and len(solution['por_pila']) == len(priors)
    for pile in mature:                                                           # la recuperacion de las maduras no cambia
        assert pile['neto_t'] == pytest.approx(nets[pile['pile']], abs=1e-8)
    assert all(p['drenaje_riego'] <= 1 + 1e-9 and p['q_riego'] > 0 and p['q_pls'] > 0 for p in solution['por_pila'])
    assert max(abs(p[k]) for p in mature for k in ('d_q_riego', 'd_cu_riego', 'd_q_pls', 'd_cu_pls')) < 0.05      # movimientos pequenos
    assert next(p for p in solution['por_pila'] if p['young'])['pile'] in young


def test_with_the_pad_already_on_target_only_the_gap_between_proxy_and_observed_recoveries_moves():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors)
    q_r, f_r, q_p, f_p = pad_of(priors)
    solution = reconcile_pad(priors, nets, goal, K_F * (f_p - f_r), tolerance=0.001, net_tolerance=0.001)
    assert solution['status'] == 'ok'
    # las maduras deben reproducir su recuperacion OBSERVADA; el valor de partida (0,95 x riego) la reproduce solo
    # aproximadamente, y esa es la unica razon para moverse: movimientos de ~1-2 %, nunca grandes
    mature = [p for p in solution['por_pila'] if not p['young']]
    assert all(p['neto_t'] == pytest.approx(nets[p['pile']], abs=1e-8) for p in mature)
    assert max(abs(p[k]) for p in mature for k in ('d_q_riego', 'd_cu_riego', 'd_q_pls', 'd_cu_pls')) < 0.03
    assert all(abs(solution['diferencia'][k]) <= 0.001 + 1e-9 for k in ('masa_riego_m3', 'masa_pls_m3', 'cu_riego_g_l', 'cu_pls_g_l'))


def test_global_flows_inconsistent_with_f29_are_reported_with_the_minimum_net_deviation():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors)
    q_r, f_r, q_p, f_p = pad_of(priors)
    net_goal = K_F * (f_p - f_r)
    # F29 bien por debajo de lo que dan los flujos globales (como un tercer flujo de entrada de Cu): las bandas de 0,1 % no alcanzan
    solution = reconcile_pad(priors, nets, goal, net_goal * 0.99, tolerance=0.001, net_tolerance=0.0005)
    assert solution['status'] == 'infactible'
    assert solution['desviacion_minima_neto_t'] > 0
    assert solution['desviacion_minima_neto_relativa'] == pytest.approx(0.01 - 0.0005 - 0.0, abs=0.006)     # ~1 % menos lo que absorben las bandas
    # con una tolerancia de neto suficiente la misma entrada si tiene solucion
    ok = reconcile_pad(priors, nets, goal, net_goal * 0.99, tolerance=0.001, net_tolerance=0.012)
    assert ok['status'] == 'ok'


def test_targets_beyond_what_the_flows_allow_are_infeasible_not_forced():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors, riego=0.5)                                       # la mitad del riego medido: imposible con las maduras fijas
    q_r, f_r, q_p, f_p = pad_of(priors)
    assert reconcile_pad(priors, nets, goal, K_F * (f_p - f_r), tolerance=0.001)['status'] == 'infactible'
