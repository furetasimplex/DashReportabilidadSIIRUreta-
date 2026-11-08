"""Reconciliacion a nivel de pad con la recuperacion de las maduras FIJA (propuesta, FUERA del dash).

Este modulo no lo importa el dash ni el informe: se usa para probar con datos reales.

Variables por pila (totales de la ventana): caudal de riego Q_r, fino de riego F_r = Q_r*Cu_r, caudal de
PLS Q_p y fino de PLS F_p = Q_p*Cu_p, con Q en suma diaria de m3/h y F en m3/h*g/L. El Cu neto de una pila
es K*(F_p - F_r) [t], K = 0.024.

Restricciones:
  * el Cu neto (recuperacion) de cada pila MADURA queda exacto;
  * masa de riego, masa de PLS y concentracion ponderada de riego y de PLS del pad dentro de una banda
    relativa `tolerance` (`BAND_DEFAULT` = 1 %, provisional) de los flujos globales;
  * el Cu neto del pad dentro de `net_tolerance` de F29 (lo que cierra la pila nueva);
  * drenaje <= tope * riego en cada pila (tope = 1 por defecto; ver `max_drain_ratio`) y valores positivos.
Entre las soluciones posibles se elige la que menos se aparta de lo medido (minimos cuadrados con
incertidumbre relativa `sigma` por variable). No hay ajuste de las recuperaciones de las maduras.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import linprog, minimize

K_F = 0.024
DEFAULT_SIGMA = (0.02, 0.05, 0.05, 0.03)      # Q riego, F riego, Q PLS (proxy), F PLS
# Banda de cierre del pad contra los flujos globales (masas, concentraciones ponderadas y neto F29), relativa.
# PROVISIONAL: 1 % (antes 0,1 %) por el error de masa del run 10093 de 0,83 %; revisar al actualizar el run.
BAND_DEFAULT = 0.01
# Rango fisico de los factores de cada pila respecto de lo medido (valor de partida). Provisional, no calibrado con ensayos:
#  * caudal (riego y PLS) en [0,5; 2]: una pila no duplica ni reduce a la mitad su caudal por una reconciliacion de
#    balance; el error de medicion de caudal esta en pocos % (las maduras suben ~5 % por el tope de drenaje, la nueva
#    absorbe el residuo hasta ~x1,6 en 10009).
#  * concentracion de Cu (riego y PLS) en [0; 3]: el limite inferior 0 admite un riego casi sin Cu (F72 fino reconciliado
#    cae ~86 % en 10009); el superior 3 evita fino sin respaldo en la medida.
PHYS_Q_RANGE = (0.5, 2.0)
PHYS_CONC_RANGE = (0.0, 3.0)
_PHYS_TOL = 1e-6


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


def _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance, caps=None):
    """Matrices de las restricciones lineales: A_eq x = b_eq y A_ub x <= b_ub (x = [Qr | Fr | Qp | Fp])."""
    n = len(piles)
    caps = np.ones(n) if caps is None else np.asarray(caps, dtype=float)
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
        v = np.zeros(4 * n); v[2 * n + i], v[i] = 1.0, -caps[i]       # drenaje <= tope * riego
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


def _pile_caps(piles, max_drain_ratio, measured_drain_ratio, measured_slack):
    """Tope drenaje/riego por pila y su fuente. `measured_drain_ratio` {pila: razon medida} (hoy el repo no tiene
    ninguna: no existe medicion de caudal de PLS por pila) se usa con `measured_slack` de holgura relativa; las
    pilas sin medida usan `max_drain_ratio` y quedan marcadas 'respaldo'. Sin medidas todo es 'configurado'."""
    measured = measured_drain_ratio or {}
    caps, sources = [], []
    for p in piles:
        if p['pile'] in measured:
            caps.append(float(measured[p['pile']]) * (1.0 + measured_slack)); sources.append('medido')
        else:
            caps.append(float(max_drain_ratio)); sources.append('respaldo' if measured else 'configurado')
    return np.array(caps), sources


def _feasible(n_vars, A_eq, b_eq, A_ub, b_ub, bounds):
    return linprog(np.zeros(n_vars), A_ub=A_ub if len(b_ub) else None, b_ub=b_ub if len(b_ub) else None,
                   A_eq=A_eq if len(b_eq) else None, b_eq=b_eq if len(b_eq) else None, bounds=bounds, method='highs').success


def _movement_bounds(x0, max_change):
    if max_change is None:
        return [(1e-9, None)] * len(x0)
    return [(max(1e-9, v * (1 - max_change)), v * (1 + max_change)) for v in x0]


def diagnose_infeasibility(piles, mature_nets_t, targets, net_target_t, tolerance, net_tolerance, caps, x0, max_change):
    """Causa de la infactibilidad, por etapas (cada etapa agrega restricciones a la anterior):
    1 `masa_agua`: topes de drenaje + bandas de masa de riego y de PLS del pad.
    2 `cobre`: + Cu neto exacto de las maduras + concentraciones ponderadas del pad.
    3 `neto_f29`: + neto del pad dentro de la tolerancia de F29.
    4 `limites_movimiento`: + cotas de movimiento (solo si se pidio `max_change`).
    La causa es la primera etapa infactible. Devuelve dict `causa`, `motivo`, `detalle`, `tope_comun_minimo_factible`."""
    n = len(piles)
    A_eq, b_eq, A_ub, b_ub, _ = _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance, caps)
    assert A_ub.shape[0] == n + 4 + 4 + 2, 'orden de restricciones inesperado'
    caps_rows, mass_rows, conc_rows, net_rows = (slice(0, n), slice(n, n + 4), slice(n + 4, n + 8), slice(n + 8, n + 10))
    free = [(1e-9, None)] * (4 * n)
    moved = _movement_bounds(x0, max_change)
    no_eq = (np.zeros((0, 4 * n)), np.zeros(0))
    pick = lambda *sl: (np.vstack([A_ub[s_] for s_ in sl]), np.concatenate([b_ub[s_] for s_ in sl]))
    R, P = targets['q_riego_m3h_sum'], targets['q_pls_m3h_sum']
    lo = 1 - tolerance
    # PLS maximo permitido = max sum(Qp) con Qp_i <= tope_i * Qr_i y la banda de masa de riego del pad
    c_obj = np.zeros(4 * n); c_obj[2 * n:3 * n] = -1.0
    Au, bu = pick(caps_rows, slice(n, n + 2))                     # topes + banda de riego (hi y lo)
    upper = linprog(c_obj, A_ub=Au, b_ub=bu, bounds=free, method='highs')
    pls_max = -upper.fun * 24 if upper.success else None
    detalle = dict(pls_minimo_exigido_m3=P * lo * 24, pls_maximo_permitido_m3=pls_max, pls_global_objetivo_m3=P * 24,
                   riego_global_objetivo_m3=R * 24, tope_drenaje_max=float(caps.max()), drenaje_riego_global_objetivo=P / R)
    stages = [('masa_agua', pick(caps_rows, mass_rows), no_eq),
              ('cobre', pick(caps_rows, mass_rows, conc_rows), (A_eq, b_eq)),
              ('neto_f29', pick(caps_rows, mass_rows, conc_rows, net_rows), (A_eq, b_eq))]
    causa = None
    for name, (Au_, bu_), (Ae_, be_) in stages:
        if not _feasible(4 * n, Ae_, be_, Au_, bu_, free):
            causa = name
            break
    if causa is None:
        causa = 'limites_movimiento' if max_change is not None and not _feasible(4 * n, A_eq, b_eq, A_ub, b_ub, moved) else 'indeterminada'
    texts = dict(
        masa_agua=(f'masa de agua imposible con el tope: PLS minimo exigido {detalle["pls_minimo_exigido_m3"]:.0f} m3 > '
                   f'PLS maximo permitido {pls_max:.0f} m3 (drenaje <= {caps.max():g} x riego, riego <= objetivo + banda {tolerance:.1%})'
                   if pls_max is not None else 'masa de agua imposible con el tope'),
        cobre='Cu imposible: el Cu neto exacto de las maduras y las concentraciones ponderadas del pad no son compatibles con las masas',
        neto_f29='neto del pad imposible: el cierre en F29 no es compatible con el resto de las restricciones',
        limites_movimiento=f'las cotas de movimiento (+-{max_change}) impiden la solucion que existe sin ellas',
        indeterminada='no se identifico la etapa que impide la solucion')
    out = dict(causa=causa, motivo=texts[causa], detalle=detalle)

    def feasible_with(cap):                  # tope unico para todas las pilas
        a_eq, b_eq_, a_ub, b_ub_, _ = _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance, np.full(n, cap))
        return _feasible(4 * n, a_eq, b_eq_, a_ub, b_ub_, moved)
    low, high = 0.5, 3.0
    if feasible_with(high):
        for _ in range(40):
            mid = (low + high) / 2
            low, high = (low, mid) if feasible_with(mid) else (mid, high)
        out['tope_comun_minimo_factible'] = high
    else:
        out['tope_comun_minimo_factible'] = None
    return out


YOUNG_MAX_AGE_DAYS = 30          # igual que sulfide_db_inputs.MAX_YOUNG_AGE_DAYS: edad <= 30 (incluye exactamente 30) es nueva


def previous_cases_affected(casos, open_from, window_start, current_case_id=None):
    """Casos del mismo mes cuyos dias [open_from, window_start) se ajustan: quedan INVALIDADOS (hay que recalcularlos).

    `casos`: lista de dicts con id, fecha_inicio y fecha_fin (p. ej. `db_pipeline.load_casos()`). Se invalida todo Caso
    cuyo periodo se solape con esos dias previos; sus sucesores del mismo mes (empiezan despues del primero invalidado,
    excepto el Caso actual) quedan en `sucesores_afectados`: dependen de un cierre que cambia (AGENTS.md)."""
    from datetime import date, timedelta
    day = lambda v: date.fromisoformat(str(v)[:10])
    lo, hi = day(open_from), day(window_start)
    invalid, others = [], []
    for c in casos or []:
        if current_case_id is not None and int(c['id']) == int(current_case_id):
            continue
        ini, fin = day(c['fecha_inicio']), day(c['fecha_fin'])
        if ini < hi and fin >= lo:
            n_days = (min(fin, hi - timedelta(days=1)) - max(ini, lo)).days + 1
            invalid.append(dict(caso_id=int(c['id']), fecha_inicio=ini.isoformat(), fecha_fin=fin.isoformat(), invalidado=True,
                                accion='recalcular', dias_afectados=[(max(ini, lo) + timedelta(days=i)).isoformat() for i in range(n_days)]))
        else:
            others.append(c)
    first = min((day(c['fecha_inicio']) for c in invalid), default=None)
    successors = [int(c['id']) for c in others if first is not None and day(c['fecha_inicio']) > first
                  and (day(c['fecha_inicio']).year, day(c['fecha_inicio']).month) == (hi.year, hi.month)]
    return dict(casos_invalidados=invalid, sucesores_afectados=sorted(successors))


def closed_days_check(rows, window_start, window_end, closed_before=None, casos=None, current_case_id=None):
    """Dias CERRADOS y ABIERTOS de las pilas. Todo dia anterior a `closed_before` queda intacto (ni masa ni neto se reasignan).

    `closed_before` es la primera fecha ABIERTA (ISO). Si no se da se usa el primer dia del mes calendario de
    `window_end` y la salida lo declara (`fuente`='por_defecto_mes_calendario'); el cierre nunca se deduce en silencio.
    Vida abierta: una pila NUEVA (edad al fin del Caso <= 30 dias, incluido exactamente 30) la tiene desde
    max(primer riego, cierre) hasta `window_end`, o sea tambien los dias del mismo mes previos a la ventana
    (`dias_abiertos_previos`); una MADURA solo la ventana. Esos dias previos pertenecen a un Caso anterior del mismo
    mes: con `casos` la salida lista `casos_invalidados` (recalcular) y `sucesores_afectados`.
    Si la ventana incluyera dias cerrados con riego (`ok` False), `reconcile_pad` informa infactibilidad con causa
    `dias_cerrados_en_ventana` en vez de moverlos."""
    from datetime import date, timedelta
    day = lambda v: date.fromisoformat(str(v)[:10])
    start, end = day(window_start), day(window_end)
    if closed_before is None:
        cut, source = end.replace(day=1), 'por_defecto_mes_calendario'
    else:
        cut, source = day(closed_before), 'parametro'
    births = {}
    for r in rows:
        births.setdefault(r['pile'], day(r['first_irrigation']))
    per_pile, previous_days = {}, []
    for name, birth in sorted(births.items()):
        young = (end - birth).days <= YOUNG_MAX_AGE_DAYS
        first_open = max(birth, cut)
        prev = max(0, (start - first_open).days) if young else 0
        previous_days += [first_open + timedelta(days=i) for i in range(prev)]
        per_pile[name] = dict(primer_riego=birth.isoformat(), nueva=young,
                              dias_cerrados=max(0, (min(cut, end + timedelta(days=1)) - birth).days),
                              dias_abiertos_previos=prev,
                              dias_abiertos=(prev + (end - max(start, first_open)).days + 1) if young
                              else max(0, (end - max(start, birth)).days + 1))
    in_window = sorted({r['date'] for r in rows if str(r['date'])[:10] >= start.isoformat() and day(r['date']) < cut
                        and (r.get('q_riego_m3h') or 0) > 0})
    out = dict(ok=not in_window, cierre_fecha=cut.isoformat(), fuente=source, ventana=[start.isoformat(), end.isoformat()],
               dias_cerrados_en_ventana=in_window, por_pila=per_pile)
    if previous_days:
        out['abiertos_previos_desde'] = min(previous_days).isoformat()
        out['abiertos_previos_hasta'] = (start - timedelta(days=1)).isoformat()
        if casos is not None:
            out.update(previous_cases_affected(casos, min(previous_days), start, current_case_id))
    return out


def reconcile_pad(piles, mature_nets_t, targets, net_target_t, tolerance=BAND_DEFAULT, net_tolerance=BAND_DEFAULT,
                  sigma=DEFAULT_SIGMA, max_drain_ratio=1.0, measured_drain_ratio=None, measured_slack=0.0,
                  max_change=None, cierre=None, physical_q_range=PHYS_Q_RANGE, physical_conc_range=PHYS_CONC_RANGE):
    """Resuelve el ajuste. `piles`: salida de `window_priors`; `mature_nets_t`: {pila madura: Cu neto observado [t]}.

    `tolerance` / `net_tolerance`: banda relativa de cierre de masas y concentraciones del pad / del neto F29 contra los
    globales (1 % por defecto, PROVISIONAL: error de masa del run 10093 de 0,83 %; revisar al actualizar el run).
    `max_drain_ratio`: tope drenaje/riego de cada pila (1 = no se drena mas de lo que se riega); es un supuesto,
    no una ley hidraulica. `measured_drain_ratio` {pila: razon medida} y `measured_slack` (holgura relativa que cubre
    la incertidumbre de esa medida) reemplazan el tope de las pilas con medida; hoy el repo no tiene medicion de caudal
    de PLS por pila, asi que no se usa. `max_change`: cota relativa opcional del movimiento de cada variable respecto del
    valor de partida (None = solo positividad). `cierre`: salida de `closed_days_check`; si trae dias cerrados dentro de la
    ventana el resultado es infactible (`causa`='dias_cerrados_en_ventana') y se anexa `cierre` a la salida.
    `physical_q_range` / `physical_conc_range`: rango de los factores de caudal y de concentracion de cada pila respecto
    de lo medido (`PHYS_Q_RANGE`, `PHYS_CONC_RANGE`; None = sin limite). Se imponen como restricciones (si solo ellas
    impiden cerrar, `causa`='limites_fisicos') y la solucion final se verifica: flujos negativos, concentraciones no
    finitas o factores fuera de rango la vuelven infactible con `causa`='solucion_no_fisica'.

    Devuelve dict con `status` ('ok' | 'infactible'), la solucion por pila, los totales del pad y, si no hay
    solucion, `causa` (masa_agua | cobre | neto_f29 | limites_movimiento | limites_fisicos | solucion_no_fisica), `motivo`, `detalle`,
    `tope_comun_minimo_factible` y la menor desviacion del Cu neto respecto de F29 si se puede calcular."""
    if cierre is not None and not cierre['ok']:
        return dict(status='infactible', causa='dias_cerrados_en_ventana', cierre=cierre,
                    motivo=f"la ventana incluye {len(cierre['dias_cerrados_en_ventana'])} dia(s) con riego anteriores al cierre "
                           f"{cierre['cierre_fecha']}; no se mueven dias cerrados")
    n = len(piles)
    caps, cap_sources = _pile_caps(piles, max_drain_ratio, measured_drain_ratio, measured_slack)
    x0 = np.array([p['x0'][j] for j in range(4) for p in piles])
    A_eq, b_eq, A_ub, b_ub, net = _constraints(piles, mature_nets_t, targets, tolerance, net_target_t, net_tolerance, caps)
    bounds = _movement_bounds(x0, max_change)
    bounds_free, A_ub_free, b_ub_free = bounds, A_ub, b_ub
    if physical_q_range is not None or physical_conc_range is not None:
        bounds, A_ub, b_ub = _physical_limits(piles, x0, bounds, A_ub, b_ub, physical_q_range, physical_conc_range)
    feasible = _closest_feasible(x0, A_eq, b_eq, A_ub, b_ub, bounds)
    if not feasible.success and (A_ub is not A_ub_free):
        if _closest_feasible(x0, A_eq, b_eq, A_ub_free, b_ub_free, bounds_free).success:
            return dict(status='infactible', causa='limites_fisicos',
                        motivo=f'el cierre exige factores fuera del rango fisico (caudal {physical_q_range}, concentracion {physical_conc_range} '
                               f'respecto de lo medido); sin ese rango si cierra', detalle=dict(q=physical_q_range, conc=physical_conc_range))
        bounds, A_ub, b_ub = bounds_free, A_ub_free, b_ub_free
    if not feasible.success:
        # menor desviacion del neto del pad (mismas demas restricciones): variable extra d >= |net - F29|
        goal_f = net_target_t / K_F
        c = np.zeros(4 * n + 1); c[-1] = 1.0
        keep = np.array([not (np.allclose(r, net) or np.allclose(r, -net)) for r in A_ub])
        A_ub2 = np.vstack([np.hstack([A_ub[keep], np.zeros((keep.sum(), 1))]),
                           np.append(net, -1.0)[None, :], np.append(-net, -1.0)[None, :]])
        b_ub2 = np.concatenate([b_ub[keep], [goal_f, -goal_f]])
        relax = linprog(c, A_ub=A_ub2, b_ub=b_ub2, A_eq=np.hstack([A_eq, np.zeros((len(b_eq), 1))]), b_eq=b_eq,
                        bounds=bounds + [(0, None)], method='highs')
        gap_t = K_F * relax.x[-1] if relax.success else None
        diag = diagnose_infeasibility(piles, mature_nets_t, targets, net_target_t, tolerance, net_tolerance, caps, x0, max_change)
        return dict(status='infactible', desviacion_minima_neto_t=gap_t,
                    desviacion_minima_neto_relativa=(gap_t / net_target_t if gap_t is not None else None), **diag)
    w = np.concatenate([np.full(n, 1 / sigma[j]) for j in range(4)]) / x0
    objective = lambda x: float(np.sum((w * (x - x0)) ** 2))
    gradient = lambda x: 2 * w ** 2 * (x - x0)
    constraints = [dict(type='eq', fun=lambda x: A_eq @ x - b_eq, jac=lambda x: A_eq),
                   dict(type='ineq', fun=lambda x: b_ub - A_ub @ x, jac=lambda x: -A_ub)]
    scale = np.maximum(np.abs(x0), 1.0)
    solved = minimize(lambda z: objective(z * scale), feasible.x / scale, jac=lambda z: gradient(z * scale) * scale,
                      bounds=[(lo_ / sc, (hi_ / sc if hi_ is not None else None)) for (lo_, hi_), sc in zip(bounds, scale)],
                      constraints=[dict(type='eq', fun=lambda z: (A_eq @ (z * scale) - b_eq) / scale.mean(), jac=lambda z: A_eq * scale / scale.mean()),
                                   dict(type='ineq', fun=lambda z: (b_ub - A_ub @ (z * scale)) / scale.mean(), jac=lambda z: -A_ub * scale / scale.mean())],
                      method='SLSQP', options=dict(maxiter=1000, ftol=1e-16))
    x = solved.x * scale
    if not _satisfies(x, A_eq, b_eq, A_ub, b_ub):                       # SLSQP no llego: se conserva la solucion factible del LP
        x = feasible.x
    out = _summary(piles, x, x0, targets, net_target_t, mature_nets_t, caps, cap_sources)
    bad = _plausibility_problems(out, physical_q_range, physical_conc_range)
    if bad:
        return dict(status='infactible', causa='solucion_no_fisica', motivo='la solucion no es fisica: ' + '; '.join(bad[:4]),
                    detalle=dict(problemas=bad))
    if cierre is not None:
        out['cierre'] = cierre
    return out


def _closest_feasible(x0, A_eq, b_eq, A_ub, b_ub, bounds):
    """Punto factible lo mas cercano a `x0` (LP de desviacion relativa absoluta minima). Sustituye al LP de objetivo cero,
    cuyo vertice arbitrario (varios factores en el limite, otros en ~0) degeneraba la solucion cuando SLSQP no llegaba."""
    m = len(x0)
    c = np.concatenate([np.zeros(m), 1.0 / np.abs(x0)])
    I = np.eye(m)
    A_dev = np.vstack([np.hstack([I, -I]), np.hstack([-I, -I])])
    b_dev = np.concatenate([x0, -x0])
    A2 = np.vstack([np.hstack([A_ub, np.zeros((A_ub.shape[0], m))]), A_dev])
    b2 = np.concatenate([b_ub, b_dev])
    Ae = np.hstack([A_eq, np.zeros((A_eq.shape[0], m))]) if len(b_eq) else None
    r = linprog(c, A_ub=A2, b_ub=b2, A_eq=Ae, b_eq=b_eq if len(b_eq) else None, bounds=list(bounds) + [(0, None)] * m, method='highs')
    if r.success:
        r.x = r.x[:m]
    return r


def _physical_limits(piles, x0, bounds, A_ub, b_ub, q_range, conc_range):
    """Agrega el rango fisico: cotas de caudal sobre Q_r y Q_p, y F <= hi * (F0/Q0) * Q (concentracion maxima) por pila."""
    n = len(piles)
    bounds = list(bounds)
    if q_range is not None:
        for j in (0, 2):
            for i in range(n):
                lo, hi = bounds[j * n + i]
                lo = max(lo, q_range[0] * x0[j * n + i]); hi = q_range[1] * x0[j * n + i] if hi is None else min(hi, q_range[1] * x0[j * n + i])
                bounds[j * n + i] = (lo, hi)
    extra, bx = [], []
    if conc_range is not None:
        for jq, jf in ((0, 1), (2, 3)):
            for i in range(n):
                v = np.zeros(4 * n); v[jf * n + i] = 1.0; v[jq * n + i] = -conc_range[1] * x0[jf * n + i] / x0[jq * n + i]
                extra.append(v); bx.append(0.0)
    if extra:
        A_ub = np.vstack([A_ub, np.array(extra)]); b_ub = np.concatenate([b_ub, bx])
    return bounds, A_ub, b_ub


def _plausibility_problems(out, q_range, conc_range):
    """Lista de problemas fisicos de una solucion: no finitos, negativos o factores fuera de rango."""
    bad = []
    for p in out['por_pila']:
        vals = {k: p[k] for k in ('q_riego', 'cu_riego', 'q_pls', 'cu_pls')}
        for k, v in vals.items():
            if not np.isfinite(v):
                bad.append(f"{p['pile']}: {k} no finito")
            elif v < 0:
                bad.append(f"{p['pile']}: {k} negativo ({v:.4g})")
        if bad and any(b.startswith(p['pile']) for b in bad):
            continue
        if q_range is not None:
            for k in ('d_q_riego', 'd_q_pls'):
                f = 1 + p[k]
                if not (q_range[0] - _PHYS_TOL <= f <= q_range[1] + _PHYS_TOL):
                    bad.append(f"{p['pile']}: factor {k[2:]} {f:.3g} fuera de {q_range}")
        if conc_range is not None:
            for k in ('d_cu_riego', 'd_cu_pls'):
                f = 1 + p[k]
                if not (conc_range[0] - _PHYS_TOL <= f <= conc_range[1] + _PHYS_TOL):
                    bad.append(f"{p['pile']}: factor {k[2:]} {f:.3g} fuera de {conc_range}")
    return bad


def _satisfies(x, A_eq, b_eq, A_ub, b_ub, rel=1e-9):
    scale = max(1.0, float(np.abs(x).max()))
    return bool(np.all(np.abs(A_eq @ x - b_eq) <= rel * scale * 1e3) and np.all(A_ub @ x - b_ub <= rel * scale * 1e3))


def _summary(piles, x, x0, targets, net_target_t, mature_nets_t, caps=None, cap_sources=None):
    n = len(piles)
    q_r, f_r, q_p, f_p = (x[j * n:(j + 1) * n] for j in range(4))
    p_q_r, p_f_r, p_q_p, p_f_p = (x0[j * n:(j + 1) * n] for j in range(4))
    per_pile = []
    for i, p in enumerate(piles):
        per_pile.append(dict(
            pile=p['pile'], young=p['young'], q_riego=q_r[i], cu_riego=f_r[i] / q_r[i], q_pls=q_p[i], cu_pls=f_p[i] / q_p[i],
            d_q_riego=q_r[i] / p_q_r[i] - 1, d_cu_riego=(f_r[i] / q_r[i]) / (p_f_r[i] / p_q_r[i]) - 1,
            d_q_pls=q_p[i] / p_q_p[i] - 1, d_cu_pls=(f_p[i] / q_p[i]) / (p_f_p[i] / p_q_p[i]) - 1,
            drenaje_riego=q_p[i] / q_r[i], neto_t=K_F * (f_p[i] - f_r[i]),
            tope_drenaje=(float(caps[i]) if caps is not None else 1.0),
            tope_fuente=(cap_sources[i] if cap_sources is not None else 'configurado')))
    pad = dict(masa_riego_m3=q_r.sum() * 24, masa_pls_m3=q_p.sum() * 24, cu_riego_g_l=f_r.sum() / q_r.sum(),
               cu_pls_g_l=f_p.sum() / q_p.sum(), neto_t=K_F * (f_p.sum() - f_r.sum()))
    goals = dict(masa_riego_m3=targets['q_riego_m3h_sum'] * 24, masa_pls_m3=targets['q_pls_m3h_sum'] * 24,
                 cu_riego_g_l=targets['cu_riego_g_l'], cu_pls_g_l=targets['cu_pls_g_l'], neto_t=net_target_t)
    return dict(status='ok', por_pila=per_pile, pad=pad, objetivo=goals,
                diferencia={k: pad[k] / goals[k] - 1 for k in pad})


def expand_to_days(rows, window_start, solution, observed_net_t_by_day, young_lambda, mature_ratio=0.95, closed_before=None,
                   include_previous_open=False):
    """Lleva la solucion (totales de la ventana) a cada dia, manteniendo EXACTA la recuperacion diaria de las maduras.

    Riego: caudal y Cu de riego se escalan con los factores de la pila. PLS de una madura: el caudal se escala y su
    fino diario es el Cu neto observado del dia / K mas el fino de riego del dia, de modo que el neto diario (la
    recuperacion) no cambia; el Cu de PLS diario sale de ese fino. Una pila nueva escala caudal y Cu de PLS con
    factores constantes. Devuelve filas diarias {pile, date, q_riego, cu_riego, q_pls, cu_pls, net_t}.

    `include_previous_open` (exige `closed_before`): las pilas NUEVAS aplican los mismos factores a sus dias abiertos del
    mismo mes anteriores a la ventana (filas con `previo`=True); esos dias son de un Caso anterior (ver `closed_days_check`).
    Las maduras y los dias anteriores a `closed_before` no se tocan. Si faltan los datos medidos de esos dias se levanta
    ValueError: no se inventan."""
    start = str(window_start)[:10]
    win_start = start
    if closed_before is not None:                                  # nunca emite dias cerrados
        start = max(start, str(closed_before)[:10])
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
    if include_previous_open:
        if closed_before is None:
            raise ValueError('include_previous_open exige closed_before explicito')
        cut = str(closed_before)[:10]
        for name, f in sorted(factors.items()):
            if not f['young']:
                continue
            pre = [r for r in rows if r['pile'] == name and cut <= r['date'] < win_start and (r.get('q_riego_m3h') or 0) > 0]
            bad = [r['date'] for r in pre if any(r.get(k) is None for k in ('cu_riego_gL', 'cu_drenaje_gL', 'profile_q_drenaje_m3h'))]
            if bad:
                raise ValueError(f'{name}: faltan datos medidos de dias previos abiertos {bad}; no se inventan')
            win = by_pile.get(name, [])
            q0 = sum(d['q_riego_m3h'] for d in win)
            c_r0 = sum(d['q_riego_m3h'] * d['cu_riego_gL'] for d in win) / q0
            qp0 = young_lambda * sum(d['profile_q_drenaje_m3h'] for d in win)
            cp0 = sum(young_lambda * d['profile_q_drenaje_m3h'] * d['cu_drenaje_gL'] for d in win) / qp0
            a_r, b_r = f['q_riego'] / q0, f['cu_riego'] / c_r0
            a_p, b_p = f['q_pls'] / qp0, f['cu_pls'] / cp0
            for d in sorted(pre, key=lambda r: r['date']):
                q_r, c_r = a_r * d['q_riego_m3h'], b_r * d['cu_riego_gL']
                q_p, c_p = a_p * young_lambda * d['profile_q_drenaje_m3h'], b_p * d['cu_drenaje_gL']
                out.append(dict(pile=name, date=d['date'], young=True, q_riego=q_r, cu_riego=c_r, q_pls=q_p, cu_pls=c_p,
                                net_t=K_F * (q_p * c_p - q_r * c_r), previo=True))
    return out
