"""Reconciliacion a nivel de pad con la recuperacion de las maduras FIJA (propuesta, FUERA del dash).

Este modulo no lo importa el dash ni el informe: se usa para probar con datos reales.

Variables por pila (totales de la ventana): caudal de riego Q_r, fino de riego F_r = Q_r*Cu_r, caudal de
PLS Q_p y fino de PLS F_p = Q_p*Cu_p, con Q en suma diaria de m3/h y F en m3/h*g/L. El Cu neto de una pila
es K*(F_p - F_r) [t], K = 0.024.

Restricciones:
  * el Cu neto (recuperacion) de cada pila MADURA queda exacto;
  * masa de riego, masa de PLS y concentracion ponderada de riego y de PLS del pad dentro de una banda
    relativa `tolerance` (0,1 % por defecto) de los flujos globales;
  * el Cu neto del pad dentro de `net_tolerance` de F29 (lo que cierra la pila nueva);
  * drenaje <= riego en cada pila y valores positivos.
Entre las soluciones posibles se elige la que menos se aparta de lo medido (minimos cuadrados con
incertidumbre relativa `sigma` por variable). No hay ajuste de las recuperaciones de las maduras.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog, minimize

K_F = 0.024
DEFAULT_SIGMA = (0.02, 0.05, 0.05, 0.03)      # Q riego, F riego, Q PLS (proxy), F PLS


def window_priors(rows, window_start, young_lambda, mature_ratio=0.95):
    """Valores de partida por pila (totales de la ventana) desde las filas diarias de `sulfide_db_inputs`.

    Maduras: PLS = mature_ratio x riego con el Cu de drenaje medido. Nuevas: perfil de drenaje guardado x lambda."""
    start = str(window_start)[:10]
    by_pile = {}
    for r in rows:
        if r['date'] >= start and r['q_riego_m3h'] > 0:
            by_pile.setdefault(r['pile'], []).append(r)
    piles = []
    for name, days in sorted(by_pile.items()):
        young = 'profile_q_drenaje_m3h' in days[0]
        q_r = sum(d['q_riego_m3h'] for d in days)
        f_r = sum(d['q_riego_m3h'] * d['cu_riego_gL'] for d in days)
        if young:
            q_p = young_lambda * sum(d['profile_q_drenaje_m3h'] for d in days)
            f_p = young_lambda * sum(d['profile_q_drenaje_m3h'] * d['cu_drenaje_gL'] for d in days)
        else:
            q_p = mature_ratio * q_r
            f_p = mature_ratio * sum(d['q_riego_m3h'] * d['cu_drenaje_gL'] for d in days)
        piles.append(dict(pile=name, young=young, x0=(q_r, f_r, q_p, f_p)))
    return piles


def _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance):
    """Matrices de las restricciones lineales: A_eq x = b_eq y A_ub x <= b_ub (x = [Qr | Fr | Qp | Fp])."""
    n = len(piles)
    block = lambda j: slice(j * n, (j + 1) * n)
    ones = np.ones(n)
    A_eq, b_eq, A_ub, b_ub = [], [], [], []

    def row(**parts):
        v = np.zeros(4 * n)
        for j, coeff in parts.items():
            v[block(int(j[1:]))] = coeff
        return v

    for i, p in enumerate(piles):                                     # neto exacto de cada madura
        if not p['young']:
            v = np.zeros(4 * n); v[3 * n + i], v[n + i] = 1.0, -1.0
            A_eq.append(v); b_eq.append(mature_nets_t[p['pile']] / K_F)
        v = np.zeros(4 * n); v[2 * n + i], v[i] = 1.0, -1.0           # drenaje <= riego
        A_ub.append(v); b_ub.append(0.0)
    R, P = targets['q_riego_m3h_sum'], targets['q_pls_m3h_sum']
    cr, cp = targets['cu_riego_g_l'], targets['cu_pls_g_l']
    lo, hi = 1 - tolerance, 1 + tolerance
    for j, goal in ((0, R), (2, P)):                                  # masas del pad dentro de la banda
        A_ub.append(row(**{f'j{j}': ones})); b_ub.append(goal * hi)
        A_ub.append(-row(**{f'j{j}': ones})); b_ub.append(-goal * lo)
    for jq, jf, c in ((0, 1, cr), (2, 3, cp)):                        # Cu ponderado: c*lo*Q <= F <= c*hi*Q
        A_ub.append(row(**{f'j{jf}': ones, f'j{jq}': -c * hi * ones})); b_ub.append(0.0)
        A_ub.append(row(**{f'j{jq}': c * lo * ones, f'j{jf}': -ones})); b_ub.append(0.0)
    net = row(j3=ones, j1=-ones)                                      # neto del pad
    goal_f = net_target_t / K_F
    A_ub.append(net); b_ub.append(goal_f * (1 + net_tolerance))
    A_ub.append(-net); b_ub.append(-goal_f * (1 - net_tolerance))
    return np.array(A_eq), np.array(b_eq), np.array(A_ub), np.array(b_ub), net


def reconcile_pad(piles, mature_nets_t, targets, net_target_t, tolerance=0.001, net_tolerance=0.001,
                  sigma=DEFAULT_SIGMA):
    """Resuelve el ajuste. `piles`: salida de `window_priors`; `mature_nets_t`: {pila madura: Cu neto observado [t]}.

    Devuelve dict con `status` ('ok' | 'infactible'), la solucion por pila, los totales del pad y, si no hay
    solucion, la menor desviacion del Cu neto respecto de F29 que haria factible el resto."""
    n = len(piles)
    x0 = np.array([p['x0'][j] for j in range(4) for p in piles])
    A_eq, b_eq, A_ub, b_ub, net = _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance)
    bounds = [(1e-9, None)] * (4 * n)
    feasible = linprog(np.zeros(4 * n), A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    if not feasible.success:
        # menor desviacion del neto del pad (mismas demas restricciones): variable extra d >= |net - F29|
        goal_f = net_target_t / K_F
        c = np.zeros(4 * n + 1); c[-1] = 1.0
        A2 = np.vstack([np.hstack([A_ub, np.zeros((len(b_ub), 1))])])
        keep = np.array([not (np.allclose(r, net) or np.allclose(r, -net)) for r in A_ub])
        A_ub2 = np.vstack([np.hstack([A_ub[keep], np.zeros((keep.sum(), 1))]),
                           np.append(net, -1.0)[None, :], np.append(-net, -1.0)[None, :]])
        b_ub2 = np.concatenate([b_ub[keep], [goal_f, -goal_f]])
        relax = linprog(c, A_ub=A_ub2, b_ub=b_ub2, A_eq=np.hstack([A_eq, np.zeros((len(b_eq), 1))]), b_eq=b_eq,
                        bounds=bounds + [(0, None)], method='highs')
        gap_t = K_F * relax.x[-1] if relax.success else None
        return dict(status='infactible', motivo='las restricciones no admiten solucion',
                    desviacion_minima_neto_t=gap_t,
                    desviacion_minima_neto_relativa=(gap_t / net_target_t if gap_t is not None else None))
    w = np.concatenate([np.full(n, 1 / sigma[j]) for j in range(4)]) / x0
    objective = lambda x: float(np.sum((w * (x - x0)) ** 2))
    gradient = lambda x: 2 * w ** 2 * (x - x0)
    constraints = [dict(type='eq', fun=lambda x: A_eq @ x - b_eq, jac=lambda x: A_eq),
                   dict(type='ineq', fun=lambda x: b_ub - A_ub @ x, jac=lambda x: -A_ub)]
    scale = np.maximum(np.abs(x0), 1.0)
    solved = minimize(lambda z: objective(z * scale), feasible.x / scale, jac=lambda z: gradient(z * scale) * scale,
                      bounds=[(1e-9, None)] * (4 * n),
                      constraints=[dict(type='eq', fun=lambda z: (A_eq @ (z * scale) - b_eq) / scale.mean(), jac=lambda z: A_eq * scale / scale.mean()),
                                   dict(type='ineq', fun=lambda z: (b_ub - A_ub @ (z * scale)) / scale.mean(), jac=lambda z: -A_ub * scale / scale.mean())],
                      method='SLSQP', options=dict(maxiter=1000, ftol=1e-16))
    x = solved.x * scale
    if not _satisfies(x, A_eq, b_eq, A_ub, b_ub):                       # SLSQP no llego: se conserva la solucion factible del LP
        x = feasible.x
    return _summary(piles, x, x0, targets, net_target_t, mature_nets_t)


def _satisfies(x, A_eq, b_eq, A_ub, b_ub, rel=1e-9):
    scale = max(1.0, float(np.abs(x).max()))
    return bool(np.all(np.abs(A_eq @ x - b_eq) <= rel * scale * 1e3) and np.all(A_ub @ x - b_ub <= rel * scale * 1e3))


def _summary(piles, x, x0, targets, net_target_t, mature_nets_t):
    n = len(piles)
    q_r, f_r, q_p, f_p = (x[j * n:(j + 1) * n] for j in range(4))
    p_q_r, p_f_r, p_q_p, p_f_p = (x0[j * n:(j + 1) * n] for j in range(4))
    per_pile = []
    for i, p in enumerate(piles):
        per_pile.append(dict(
            pile=p['pile'], young=p['young'], q_riego=q_r[i], cu_riego=f_r[i] / q_r[i], q_pls=q_p[i], cu_pls=f_p[i] / q_p[i],
            d_q_riego=q_r[i] / p_q_r[i] - 1, d_cu_riego=(f_r[i] / q_r[i]) / (p_f_r[i] / p_q_r[i]) - 1,
            d_q_pls=q_p[i] / p_q_p[i] - 1, d_cu_pls=(f_p[i] / q_p[i]) / (p_f_p[i] / p_q_p[i]) - 1,
            drenaje_riego=q_p[i] / q_r[i], neto_t=K_F * (f_p[i] - f_r[i])))
    pad = dict(masa_riego_m3=q_r.sum() * 24, masa_pls_m3=q_p.sum() * 24, cu_riego_g_l=f_r.sum() / q_r.sum(),
               cu_pls_g_l=f_p.sum() / q_p.sum(), neto_t=K_F * (f_p.sum() - f_r.sum()))
    goals = dict(masa_riego_m3=targets['q_riego_m3h_sum'] * 24, masa_pls_m3=targets['q_pls_m3h_sum'] * 24,
                 cu_riego_g_l=targets['cu_riego_g_l'], cu_pls_g_l=targets['cu_pls_g_l'], neto_t=net_target_t)
    return dict(status='ok', por_pila=per_pile, pad=pad, objetivo=goals,
                diferencia={k: pad[k] / goals[k] - 1 for k in pad})


def expand_to_days(rows, window_start, solution, observed_net_t_by_day, young_lambda, mature_ratio=0.95):
    """Lleva la solucion (totales de la ventana) a cada dia, manteniendo EXACTA la recuperacion diaria de las maduras.

    Riego: caudal y Cu de riego se escalan con los factores de la pila. PLS de una madura: el caudal se escala y su
    fino diario es el Cu neto observado del dia / K mas el fino de riego del dia, de modo que el neto diario (la
    recuperacion) no cambia; el Cu de PLS diario sale de ese fino. Una pila nueva escala caudal y Cu de PLS con
    factores constantes. Devuelve filas diarias {pile, date, q_riego, cu_riego, q_pls, cu_pls, net_t}."""
    start = str(window_start)[:10]
    factors = {p['pile']: p for p in solution['por_pila']}
    out = []
    by_pile = {}
    for r in rows:
        if r['date'] >= start and r['q_riego_m3h'] > 0:
            by_pile.setdefault(r['pile'], []).append(r)
    for name, days in sorted(by_pile.items()):
        f = factors[name]
        young = f['young']
        q0 = sum(d['q_riego_m3h'] for d in days)
        a_r = f['q_riego'] / q0
        c_r0 = sum(d['q_riego_m3h'] * d['cu_riego_gL'] for d in days) / q0
        b_r = f['cu_riego'] / c_r0
        if young:
            qp0 = young_lambda * sum(d['profile_q_drenaje_m3h'] for d in days)
            cp0 = sum(young_lambda * d['profile_q_drenaje_m3h'] * d['cu_drenaje_gL'] for d in days) / qp0
        else:
            qp0 = mature_ratio * q0
            cp0 = sum(d['q_riego_m3h'] * d['cu_drenaje_gL'] for d in days) / q0
        a_p, b_p = f['q_pls'] / qp0, f['cu_pls'] / cp0
        rest = None
        if not young:
            nets = observed_net_t_by_day[name]
            used = sum(nets.get(d['date'], 0.0) for d in days)
            rest = sum(nets.values()) - used                             # neto en dias sin riego: se carga al ultimo dia con riego
        for k, d in enumerate(days):
            q_r, c_r = a_r * d['q_riego_m3h'], b_r * d['cu_riego_gL']
            if young:
                q_p = a_p * young_lambda * d['profile_q_drenaje_m3h']
                c_p = b_p * d['cu_drenaje_gL']
            else:
                q_p = a_p * mature_ratio * d['q_riego_m3h']
                net = nets.get(d['date'], 0.0) + (rest if k == len(days) - 1 else 0.0)
                c_p = (net / K_F + q_r * c_r) / q_p
            out.append(dict(pile=name, date=d['date'], young=young, q_riego=q_r, cu_riego=c_r, q_pls=q_p, cu_pls=c_p,
                            net_t=K_F * (q_p * c_p - q_r * c_r)))
    return out
