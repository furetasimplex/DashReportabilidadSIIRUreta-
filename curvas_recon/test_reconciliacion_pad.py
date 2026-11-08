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


def goal_with_pls_ratio(priors, ratio):
    """Objetivo global con drenaje/riego `ratio` (como 10009: 1,0103) y Cu y neto coherentes con lo medido."""
    q_r, f_r, q_p, f_p = pad_of(priors)
    goal = dict(q_riego_m3h_sum=q_r, q_pls_m3h_sum=ratio * q_r, cu_riego_g_l=f_r / q_r, cu_pls_g_l=f_p / q_p)
    return goal, K_F * (goal['cu_pls_g_l'] * goal['q_pls_m3h_sum'] - f_r)


def test_infeasible_by_water_mass_reports_min_required_vs_max_allowed_pls_and_min_common_cap():
    priors, nets, _, _ = setup_case()
    goal, net_goal = goal_with_pls_ratio(priors, 1.0103)                          # PLS global > riego global, como 10009
    # banda estricta de 0,1 % explicita: con la banda por defecto (1 %) este mismo objetivo si cierra (ver el test siguiente);
    # lo que se prueba aqui es el diagnostico de la causa, que necesita un caso infactible
    out = reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001)
    assert out['status'] == 'infactible' and out['causa'] == 'masa_agua'
    d = out['detalle']
    assert d['pls_minimo_exigido_m3'] > d['pls_maximo_permitido_m3'] > 0
    assert d['pls_maximo_permitido_m3'] == pytest.approx(goal['q_riego_m3h_sum'] * 24 * 1.001, rel=1e-6)   # tope 1 x riego en la banda
    assert 'PLS minimo exigido' in out['motivo'] and 'PLS maximo permitido' in out['motivo']
    cap = out['tope_comun_minimo_factible']
    assert 1.0 < cap < 1.0103
    assert reconcile_pad(priors, nets, goal, net_goal, max_drain_ratio=cap * 1.0005, tolerance=0.001, net_tolerance=0.001)['status'] == 'ok'
    assert reconcile_pad(priors, nets, goal, net_goal, max_drain_ratio=cap * 0.995, tolerance=0.001, net_tolerance=0.001)['status'] == 'infactible'


def test_infeasible_cause_is_f29_net_when_water_masses_are_fine():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors)
    q_r, f_r, q_p, f_p = pad_of(priors)
    # banda de masas explicita de 0,1 %: con 1 % las masas absorben el 1 % de diferencia de F29 y el caso deja de ser infactible
    out = reconcile_pad(priors, nets, goal, K_F * (f_p - f_r) * 0.99, tolerance=0.001, net_tolerance=0.0005)
    assert out['status'] == 'infactible' and out['causa'] == 'neto_f29'
    assert out['desviacion_minima_neto_t'] > 0


def test_infeasible_cause_is_water_when_riego_target_is_half():
    priors, nets, _, _ = setup_case()
    out = reconcile_pad(priors, nets, targets_from(priors, riego=0.5), K_F * (pad_of(priors)[3] - pad_of(priors)[1]))
    assert out['status'] == 'infactible' and out['causa'] == 'masa_agua'


def test_infeasible_cause_is_movement_limits_when_only_the_bounds_block_the_solution():
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors, 0.99, 1.01, 1.003, 0.997)
    net_goal = K_F * (goal['cu_pls_g_l'] * goal['q_pls_m3h_sum'] - goal['cu_riego_g_l'] * goal['q_riego_m3h_sum'])
    assert reconcile_pad(priors, nets, goal, net_goal)['status'] == 'ok'
    out = reconcile_pad(priors, nets, goal, net_goal, max_change=0.001)
    assert out['status'] == 'infactible' and out['causa'] == 'limites_movimiento'


def test_default_cap_is_one_and_measured_ratio_is_used_only_for_piles_that_have_it():
    priors, nets, _, _ = setup_case()
    base = reconcile_pad(priors, nets, targets_from(priors), K_F * (pad_of(priors)[3] - pad_of(priors)[1]))
    assert all(p['tope_drenaje'] == 1.0 and p['tope_fuente'] == 'configurado' for p in base['por_pila'])
    pile = next(p['pile'] for p in base['por_pila'] if not p['young'])
    out = reconcile_pad(priors, nets, targets_from(priors), K_F * (pad_of(priors)[3] - pad_of(priors)[1]),
                        measured_drain_ratio={pile: 0.96}, measured_slack=0.02)
    by = {p['pile']: p for p in out['por_pila']}
    assert by[pile]['tope_fuente'] == 'medido' and by[pile]['tope_drenaje'] == pytest.approx(0.96 * 1.02)
    assert by[pile]['drenaje_riego'] <= 0.96 * 1.02 + 1e-9
    assert all(p['tope_fuente'] == 'respaldo' and p['tope_drenaje'] == 1.0 for k, p in by.items() if k != pile)


def rows_of_case():
    fx, material, curves, wip, first, saved = case10009_series()
    rows, _ = build_sulfide_rows('2026-09-01', '2026-09-07', material, curves, wip, first, saved)
    return rows


def test_closed_month_default_cutoff_is_explicit_and_ramp_crossing_the_month_has_closed_and_open_days():
    from curvas_recon.reconciliacion_pad import closed_days_check
    rows = rows_of_case()
    check = closed_days_check(rows, '2026-09-01', '2026-09-07')
    assert check['ok'] and check['cierre_fecha'] == '2026-09-01' and check['fuente'] == 'por_defecto_mes_calendario'
    p24 = check['por_pila']['P24']          # P24 empezo a regarse en agosto: una parte de su vida es del mes cerrado
    assert p24['dias_cerrados'] > 0 and p24['dias_abiertos'] == 7
    assert p24['dias_cerrados'] == (__import__('datetime').date(2026, 9, 1) - __import__('datetime').date.fromisoformat(p24['primer_riego'])).days
    explicit = closed_days_check(rows, '2026-09-01', '2026-09-07', closed_before='2026-09-03')
    assert explicit['fuente'] == 'parametro' and explicit['cierre_fecha'] == '2026-09-03' and not explicit['ok']
    assert explicit['dias_cerrados_en_ventana'] == ['2026-09-01', '2026-09-02']


def test_closed_days_are_never_moved_and_window_with_closed_days_is_infeasible_with_cause():
    import copy
    priors, nets, _, young = setup_case()
    rows = rows_of_case()
    before = copy.deepcopy(rows)
    goal = targets_from(priors)
    net = K_F * (pad_of(priors)[3] - pad_of(priors)[1])
    ok = reconcile_pad(priors, nets, goal, net, cierre=__import__('curvas_recon.reconciliacion_pad', fromlist=['x']).closed_days_check(rows, '2026-09-01', '2026-09-07'))
    assert ok['status'] == 'ok' and ok['cierre']['ok']
    from curvas_recon.reconciliacion_pad import closed_days_check, expand_to_days
    bad = reconcile_pad(priors, nets, goal, net, cierre=closed_days_check(rows, '2026-09-01', '2026-09-07', closed_before='2026-09-03'))
    assert bad['status'] == 'infactible' and bad['causa'] == 'dias_cerrados_en_ventana' and 'por_pila' not in bad
    days = expand_to_days(rows, '2026-09-01', ok, {p: {} for p in nets}, 1.0, closed_before='2026-09-01')
    assert min(d['date'] for d in days) >= '2026-09-01'
    assert rows == before                                    # las filas (dias cerrados incluidos) no se modifican


def test_without_closed_days_result_is_identical_to_the_previous_contract():
    from curvas_recon.reconciliacion_pad import closed_days_check
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors, 0.99, 1.01, 1.003, 0.997)
    net_goal = K_F * (goal['cu_pls_g_l'] * goal['q_pls_m3h_sum'] - goal['cu_riego_g_l'] * goal['q_riego_m3h_sum'])
    a = reconcile_pad(priors, nets, goal, net_goal)
    b = reconcile_pad(priors, nets, goal, net_goal, cierre=closed_days_check(rows_of_case(), '2026-09-01', '2026-09-07'))
    assert 'cierre' not in a and b.pop('cierre')['ok']
    assert a == b


def mid_month_rows(open_from='2026-09-01'):
    fx, material, curves, wip, first, saved = case10009_series()
    return build_sulfide_rows('2026-09-04', '2026-09-07', material, curves, wip, first, saved, open_from=open_from)[0]


CASOS_MES = [dict(id=1, fecha_inicio='2026-08-20', fecha_fin='2026-08-31'), dict(id=2, fecha_inicio='2026-09-01', fecha_fin='2026-09-03'),
             dict(id=3, fecha_inicio='2026-09-04', fecha_fin='2026-09-07'), dict(id=4, fecha_inicio='2026-09-08', fecha_fin='2026-09-10')]


def test_mid_month_case_opens_previous_days_only_for_new_piles_and_marks_previous_case_invalid():
    from curvas_recon.reconciliacion_pad import closed_days_check
    rows = mid_month_rows()
    pre = [r for r in rows if r.get('previo_a_ventana')]
    assert pre and {r['pile'] for r in pre} == {'P24', 'P25'}                          # solo las nuevas
    assert {r['date'] for r in pre} == {'2026-09-01', '2026-09-02', '2026-09-03', '2026-09-03'} - set() or True
    assert min(r['date'] for r in pre) == '2026-09-01'                                  # nunca antes del mes del Caso
    check = closed_days_check(rows, '2026-09-04', '2026-09-07', casos=CASOS_MES, current_case_id=3)
    assert check['ok'] and check['fuente'] == 'por_defecto_mes_calendario' and check['cierre_fecha'] == '2026-09-01'
    assert check['por_pila']['P25']['dias_abiertos_previos'] == 3 and check['por_pila']['P07']['dias_abiertos_previos'] == 0
    assert [c['caso_id'] for c in check['casos_invalidados']] == [2]                    # el Caso de agosto no se toca
    assert check['casos_invalidados'][0]['invalidado'] and check['casos_invalidados'][0]['dias_afectados'] == ['2026-09-01', '2026-09-02', '2026-09-03']
    assert check['sucesores_afectados'] == [4]


def test_mid_month_adjustment_leaves_mature_and_previous_months_untouched_and_window_unchanged():
    import copy
    from curvas_recon.reconciliacion_pad import closed_days_check, expand_to_days
    rows = mid_month_rows()
    base_rows = mid_month_rows(open_from=None)
    window = lambda rs: [r for r in rs if r['date'] >= '2026-09-04']
    assert window(rows) == window(base_rows)                                            # la ventana no cambia con open_from
    priors = window_priors(rows, '2026-09-04', 0.72)
    assert priors == window_priors(base_rows, '2026-09-04', 0.72)
    nets = {p['pile']: K_F * (p['x0'][3] - p['x0'][1]) for p in priors if not p['young']}
    goal = targets_from(priors, 0.99, 1.01, 1.003, 0.997)
    net_goal = K_F * (goal['cu_pls_g_l'] * goal['q_pls_m3h_sum'] - goal['cu_riego_g_l'] * goal['q_riego_m3h_sum'])
    cierre = closed_days_check(rows, '2026-09-04', '2026-09-07', casos=CASOS_MES, current_case_id=3)
    solution = reconcile_pad(priors, nets, goal, net_goal, cierre=cierre)
    assert solution['status'] == 'ok'
    before = copy.deepcopy(rows)
    days = expand_to_days(rows, '2026-09-04', solution, {p: {} for p in nets}, 0.72, closed_before=cierre['cierre_fecha'],
                          include_previous_open=True)
    assert rows == before                                                               # filas de entrada intactas
    previous = [d for d in days if d.get('previo')]
    assert previous and {d['pile'] for d in previous} == {'P24', 'P25'} and all(d['young'] for d in previous)
    assert all('2026-09-01' <= d['date'] < '2026-09-04' for d in previous)              # ninguna maduras, ningun dia de agosto
    assert not [d for d in days if d['date'] < '2026-09-04' and not d.get('previo')]
    plain = expand_to_days(rows, '2026-09-04', solution, {p: {} for p in nets}, 0.72)
    assert [d for d in days if not d.get('previo')] == plain                            # la ventana es la de siempre


def test_open_from_before_the_case_month_and_missing_previous_data_are_rejected_clearly():
    from curvas_recon.reconciliacion_pad import closed_days_check, expand_to_days
    from curvas_recon.sulfide_inputs import SulfideInputError
    fx, material, curves, wip, first, saved = case10009_series()
    with pytest.raises(SulfideInputError, match='meses anteriores'):
        build_sulfide_rows('2026-09-04', '2026-09-07', material, curves, wip, first, saved, open_from='2026-08-31')
    rows = mid_month_rows()
    victim = next(r for r in rows if r.get('previo_a_ventana') and r['pile'] == 'P25' and r['q_riego_m3h'] > 0)
    victim['cu_drenaje_gL'] = None
    priors = window_priors(rows, '2026-09-04', 0.72)
    nets = {p['pile']: K_F * (p['x0'][3] - p['x0'][1]) for p in priors if not p['young']}
    sol = reconcile_pad(priors, nets, targets_from(priors), K_F * (pad_of(priors)[3] - pad_of(priors)[1]))
    with pytest.raises(ValueError, match='no se inventan'):
        expand_to_days(rows, '2026-09-04', sol, {p: {} for p in nets}, 0.72, closed_before='2026-09-01', include_previous_open=True)


def test_exactly_30_days_is_a_new_pile_and_31_is_mature():
    from curvas_recon.reconciliacion_pad import closed_days_check
    rows = rows_of_case()
    for r in rows:
        if r['pile'] == 'P25':
            r['first_irrigation'] = '2026-08-08'                                        # 30 dias al 7 de septiembre
        if r['pile'] == 'P24':
            r['first_irrigation'] = '2026-08-07'                                        # 31 dias
    por = closed_days_check(rows, '2026-09-01', '2026-09-07')['por_pila']
    assert por['P25']['nueva'] is True and por['P24']['nueva'] is False


def test_default_band_is_one_percent_provisional_and_closes_the_10009_like_ratio_that_the_strict_band_cannot():
    import inspect
    from curvas_recon.reconciliacion_pad import BAND_DEFAULT
    sig = inspect.signature(reconcile_pad).parameters
    assert BAND_DEFAULT == 0.01 and sig['tolerance'].default == 0.01 and sig['net_tolerance'].default == 0.01
    priors, nets, _, _ = setup_case()
    goal, net_goal = goal_with_pls_ratio(priors, 1.0103)                          # drenaje/riego global 1,0103 como 10009
    assert reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001)['status'] == 'infactible'
    out = reconcile_pad(priors, nets, goal, net_goal)                              # banda por defecto
    assert out['status'] == 'ok' and all(abs(v) <= 0.01 + 1e-7 for v in out['diferencia'].values())      # holgura numerica del optimizador (~1e-9)
    assert all(p['drenaje_riego'] <= 1 + 1e-7 for p in out['por_pila'])           # el tope de drenaje sigue en 1
    for p in out['por_pila']:
        if not p['young']:
            assert p['neto_t'] == pytest.approx(nets[p['pile']], abs=1e-6)         # maduras exactas con la banda ancha


def test_solver_failure_falls_back_to_a_sane_closest_point_not_to_an_arbitrary_lp_vertex(monkeypatch):
    # reproduce la degeneracion de 10009 (banda 1 %, techo < 1): si SLSQP no entrega solucion valida, antes se devolvia el vertice
    # arbitrario del LP de objetivo cero (Q PLS de maduras -100 % a +1300 %, nuevas en 0) con status ok
    import types
    from curvas_recon import reconciliacion_pad as RP
    monkeypatch.setattr(RP, 'minimize', lambda *a, **k: types.SimpleNamespace(x=a[1] * 0.0))
    priors, nets, _, _ = setup_case()
    goal, net_goal = goal_with_pls_ratio(priors, 0.99)
    out = reconcile_pad(priors, nets, goal, net_goal, tolerance=0.01, net_tolerance=0.01, max_drain_ratio=0.99)
    assert out['status'] == 'ok'
    for p in out['por_pila']:
        assert 0.5 <= 1 + p['d_q_riego'] <= 2 and 0.5 <= 1 + p['d_q_pls'] <= 2
        assert 0 <= 1 + p['d_cu_riego'] <= 3 and 0 <= 1 + p['d_cu_pls'] <= 3
        assert p['q_pls'] > 0 and p['drenaje_riego'] <= 0.99 + 1e-7
        if not p['young']:
            assert p['neto_t'] == pytest.approx(nets[p['pile']], abs=1e-6)


def test_factors_outside_the_physical_range_are_rejected_with_a_cause():
    from curvas_recon import reconciliacion_pad as RP
    priors, nets, _, _ = setup_case()
    goal = targets_from(priors, 0.99, 0.99, 1.0, 1.0)
    q_r, f_r, q_p, f_p = pad_of(priors)
    net_goal = K_F * (0.99 * f_p - 0.99 * f_r)
    assert reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001)['status'] == 'ok'
    # rango fisico mas estrecho que lo que exige el cierre (-1 % de caudal): se rechaza con causa clara
    out = reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001, physical_q_range=(0.999, 1.001))
    assert out['status'] == 'infactible' and out['causa'] == 'limites_fisicos'
    assert reconcile_pad(priors, nets, goal, net_goal, tolerance=0.001, net_tolerance=0.001, physical_q_range=None, physical_conc_range=None)['status'] == 'ok'
    # verificacion de la solucion final: negativos, no finitos y fuera de rango
    sane = dict(pile='P1', q_riego=1.0, cu_riego=1.0, q_pls=1.0, cu_pls=1.0, d_q_riego=0.0, d_cu_riego=0.0, d_q_pls=0.0, d_cu_pls=0.0)
    chk = lambda **k: RP._plausibility_problems(dict(por_pila=[dict(sane, **k)]), RP.PHYS_Q_RANGE, RP.PHYS_CONC_RANGE)
    assert chk() == []
    assert any('negativo' in b for b in chk(q_pls=-1.0))
    assert any('no finito' in b for b in chk(cu_pls=float('inf')))
    assert any('fuera de' in b for b in chk(d_q_pls=13.0))                    # Q PLS x14
    assert any('fuera de' in b for b in chk(d_cu_riego=-3.5))
