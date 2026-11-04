"""Offline net-only conditional fit of a supplied drainage profile, not a solver."""
from copy import deepcopy
from datetime import date, datetime, timedelta
from math import isfinite
from numbers import Real


def _date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _number(row, field, positive=False):
    value = row[field]
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value) or value < 0 or (positive and value <= 0):
        raise ValueError(f'invalid {field}')
    return float(value)


FDRENA_PROXY = 0.95            # drenaje de las maduras = 0.95 x riego (no hay sensor); solo pondera concentraciones
K_F = 0.024


def match_pad_flows(rows_by_state, held_net_t, target_net_t, targets, max_change=0.30, tolerance=0.001,
                    max_relaxed_gap=0.05, mature_ratio=FDRENA_PROXY):
    """Ajusta SOLO las pilas nuevas para que el pad entregue lo que entregan los flujos globales.

    Maduras: intactas (medido). Nuevas: cuatro factores comunes --
      beta    caudal de riego,           alpha_r  Cu de riego,
      lambda  caudal de drenaje (perfil), alpha_p  Cu de PLS.
    Condiciones con la solucion cerrada: masa de riego global, masa de PLS global,
    concentracion ponderada de PLS global y cierre del Cu neto F29. El Cu de riego
    ponderado absorbe la inconsistencia propia de los flujos globales (PLS - riego no
    es exactamente F29): su diferencia se informa y debe ser <= `max_relaxed_gap`.
    Sin objetivos de masa se ajustan solo concentraciones (beta = 1): la ponderada de riego
    y la de PLS quedan exactas y lambda sale del cierre de F29.

    `targets`: cu_riego_g_l, cu_pls_g_l y, opcionales, q_riego_m3h_sum y q_pls_m3h_sum
    (masa global / 24: suma diaria de caudal en m3/h). Los factores deben estar en
    1 +/- `max_change`; nunca se fuerza una solucion fuera de ese limite. `tolerance` es
    la diferencia relativa por debajo de la cual no se ajusta nada."""
    t = targets or {}
    cr_goal, cp_goal = t.get('cu_riego_g_l'), t.get('cu_pls_g_l')
    if not (isinstance(cr_goal, Real) and isinstance(cp_goal, Real) and cr_goal > 0 and cp_goal > 0):
        return dict(status='sin_objetivos')
    r_goal, p_goal = t.get('q_riego_m3h_sum'), t.get('q_pls_m3h_sum')
    with_mass = isinstance(r_goal, Real) and isinstance(p_goal, Real) and r_goal > 0 and p_goal > 0
    mature, young = rows_by_state.get('mature', []), rows_by_state.get('young', [])
    out = dict(status='no_aplicado', max_change=max_change, tolerance=tolerance,
               objetivo_cu_riego_g_l=float(cr_goal), objetivo_cu_pls_g_l=float(cp_goal),
               con_masas=bool(with_mass))
    if with_mass:
        out.update(objetivo_q_riego_m3=float(r_goal) * 24, objetivo_q_pls_m3=float(p_goal) * 24)
    irrigated = lambda rows: [r for r in rows if r['q_riego_m3h'] > 0]
    if any(r.get('cu_riego_gL') is None or r.get('cu_drenaje_gL') is None for r in irrigated(mature + young)):
        return dict(out, motivo='faltan concentraciones medidas en dias con riego')
    if not young:
        return dict(out, motivo='sin pilas nuevas')
    M_q = sum(r['q_riego_m3h'] for r in irrigated(mature))
    M_rc = sum(r['q_riego_m3h'] * r['cu_riego_gL'] for r in irrigated(mature))
    Y_q = sum(r['q_riego_m3h'] for r in irrigated(young))
    Y_rc = sum(r['q_riego_m3h'] * r['cu_riego_gL'] for r in irrigated(young))
    Q_mp = sum(mature_ratio * r['q_riego_m3h'] for r in irrigated(mature))
    S_m = sum(mature_ratio * r['q_riego_m3h'] * r['cu_drenaje_gL'] for r in irrigated(mature))
    Y_pq = sum(r['profile_q_drenaje_m3h'] for r in irrigated(young))
    Y_pc = sum(r['profile_q_drenaje_m3h'] * r['cu_drenaje_gL'] for r in irrigated(young))
    if min(Y_q, Y_rc, Y_pq, Y_pc) <= 0 or M_q + Y_q <= 0:
        return dict(out, motivo='las pilas nuevas no tienen riego y concentraciones medidas')
    need = (target_net_t - held_net_t) / K_F                       # fino neto que deben aportar las nuevas [m3/h*g/L]
    lam0 = (need + Y_rc) / Y_pc                                    # lambda del cierre simple (todos los factores = 1)
    q_pad, p_pad = M_q + Y_q, Q_mp + lam0 * Y_pq
    out['cu_riego_pad_g_l_antes'] = (M_rc + Y_rc) / q_pad
    out['cu_pls_pad_g_l_antes'] = (S_m + lam0 * Y_pc) / p_pad if p_pad > 0 else None
    gap = lambda value, goal: abs(value - goal) / goal
    masses_ok = (not with_mass) or (gap(q_pad, r_goal) <= tolerance and gap(p_pad, p_goal) <= tolerance)
    if (masses_ok and gap(out['cu_riego_pad_g_l_antes'], cr_goal) <= tolerance
            and out['cu_pls_pad_g_l_antes'] is not None and gap(out['cu_pls_pad_g_l_antes'], cp_goal) <= tolerance):
        return dict(out, status='sin_cambio', motivo='el pad ya coincide con los flujos globales')
    if with_mass:
        beta = (r_goal - M_q) / Y_q
        lam = (p_goal - Q_mp) / Y_pq
        if not (beta > 0 and lam > 0):
            return dict(out, beta=beta, lambda_=lam, motivo='la masa global exige un caudal no positivo en las nuevas')
        alpha_p = (cp_goal * p_goal - S_m) / (lam * Y_pc)
        alpha_r = (alpha_p * lam * Y_pc - need) / (beta * Y_rc)        # el cierre de F29 fija el Cu de riego
        q_after, p_after = r_goal, p_goal
    else:
        beta = 1.0
        alpha_r = (cr_goal * q_pad - M_rc) / Y_rc
        a = (need + alpha_r * Y_rc) / Y_pc
        lam = ((S_m + a * Y_pc) / cp_goal - Q_mp) / Y_pq
        if not lam > 0:
            return dict(out, beta=beta, alpha_riego=alpha_r, lambda_=lam,
                        motivo='el caudal de PLS global exige un drenaje no positivo en las nuevas')
        alpha_p = a / lam
        q_after, p_after = q_pad, Q_mp + lam * Y_pq
    out.update(beta=beta, alpha_riego=alpha_r, alpha_pls=alpha_p, lambda_=lam)
    within = lambda x: 1 - max_change <= x <= 1 + max_change
    if not (within(alpha_r) and within(alpha_p) and within(beta)):
        return dict(out, motivo=f'requiere cambiar las pilas nuevas mas de {max_change:.0%} '
                                f'(riego x{beta:.3f}, Cu riego x{alpha_r:.3f}, Cu PLS x{alpha_p:.3f})')
    if any(lam * r['profile_q_drenaje_m3h'] > beta * r['q_riego_m3h'] + 1e-10 for r in irrigated(young)):
        return dict(out, motivo='el drenaje ajustado superaria al riego en alguna pila nueva')
    cr_after = (M_rc + alpha_r * beta * Y_rc) / (M_q + beta * Y_q)
    cp_after = (S_m + alpha_p * lam * Y_pc) / (Q_mp + lam * Y_pq)
    relaxed = gap(cr_after, cr_goal) if with_mass else 0.0
    out.update(cu_riego_pad_g_l_despues=cr_after, cu_pls_pad_g_l_despues=cp_after,
               q_riego_pad_m3_despues=(M_q + beta * Y_q) * 24, q_pls_pad_m3_despues=(Q_mp + lam * Y_pq) * 24,
               diferencia_cu_riego_relativa=relaxed)
    if relaxed > max_relaxed_gap:
        return dict(out, motivo=f'los flujos globales no son compatibles con el cierre de F29: '
                                f'el Cu de riego del pad quedaria {relaxed:.1%} fuera del global')
    return dict(out, status='aplicado')


def reconcile_sulfides(rows, case_start, case_end, target_net_t, concentration_targets=None,
                       max_concentration_change=0.30, concentration_tolerance=0.001,
                       mature_drainage_ratio=FDRENA_PROXY):
    """Fit one common drainage-profile multiplier to the net Cu target.

    Requires each sulfide cohort to have the preceding month-end and every
    daily row through case_end. Age is elapsed calendar days at case_end.
    """
    start, end = _date(case_start), _date(case_end)
    month_start = end.replace(day=1)
    previous = start - timedelta(days=1)
    if end < start or start < month_start:
        raise ValueError('case must lie within one calendar month')
    if isinstance(target_net_t, bool) or not isinstance(target_net_t, Real) or not isfinite(target_net_t):
        raise ValueError('invalid net target')
    groups = {}
    for index, row in enumerate(rows):
        key = (row['pad'], row['pile'], row['campaign'])
        day = _date(row['date'])
        group = groups.setdefault(key, {})
        if day in group:
            raise ValueError(f'duplicate row: {key} {day}')
        group[day] = (index, row)
    output = deepcopy(rows)
    young, mature, history = [], [], []
    held_net = young_in = young_drain = 0.0
    for key, group in groups.items():
        if str(key[0]).strip().upper() not in {'SU', 'SULFUROS', 'SULFURO'}:
            continue
        if previous not in group or month_start - timedelta(days=1) not in group:
            raise ValueError(f'missing prior baseline: {key}')
        base = group[previous][1]
        base_pct = _number(base, 'official_pct')
        cu_tf = _number(base, 'cu_apilado_t', positive=True)
        birth = _date(base['first_irrigation'])
        age = (end - birth).days
        if age < 0:
            raise ValueError(f'first irrigation after case end: {key}')
        expected = [start + timedelta(days=i) for i in range((end-start).days+1)]
        if any(day not in group for day in expected):
            raise ValueError(f'incomplete daily coverage: {key}')
        for day in expected:
            row = group[day][1]
            if _number(row, 'cu_apilado_t', positive=True) != cu_tf or _date(row['first_irrigation']) != birth:
                raise ValueError(f'inconsistent cohort metadata: {key}')
        history.extend((key, day) for day in group if day < month_start)
        if age > 30:
            mature.append(key)
            for day in expected:
                idx, row = group[day]
                # Solo el cierre es obligatorio; un dia intermedio sin lectura
                # queda como hueco, nunca se rellena.
                if day != end and row.get('observed_pct') is None:
                    output[idx]['reconciled_pct'] = None
                    continue
                output[idx]['reconciled_pct'] = _number(row, 'observed_pct')
            held_net += cu_tf * (_number(group[end][1], 'observed_pct') - base_pct) / 100
        else:
            young.append(key)
            for day in expected:
                row = group[day][1]
                qr = _number(row, 'q_riego_m3h')
                if qr == 0:
                    continue                  # sin riego: sin flujo ni Cu ese dia
                cr = _number(row, 'cu_riego_gL')
                cd = _number(row, 'cu_drenaje_gL')
                qd = _number(row, 'profile_q_drenaje_m3h', positive=True)
                young_in += .024 * qr * cr
                young_drain += .024 * qd * cd
    required = float(target_net_t) - held_net + young_in
    state_rows = {'mature': [], 'young': []}
    for key, group in groups.items():
        state = 'mature' if key in mature else 'young' if key in young else None
        if state:
            state_rows[state].extend(group[day][1] for day in (start + timedelta(days=i) for i in range((end-start).days+1)))
    matching = match_pad_flows(state_rows, held_net, float(target_net_t), concentration_targets,
                               max_concentration_change, concentration_tolerance, mature_ratio=mature_drainage_ratio) if young else {'status': 'sin_pilas_nuevas'}
    if not young:
        if abs(float(target_net_t) - held_net) > 1e-6:
            raise ValueError('infeasible target without young cohorts')
        factor = None
    else:
        if young_drain <= 0 or required < 0:
            raise ValueError('infeasible young drainage target')
        factor = required / young_drain
    alpha_r = alpha_p = beta = 1.0
    if matching.get('status') == 'aplicado':
        factor, alpha_r, alpha_p, beta = (matching['lambda_'], matching['alpha_riego'],
                                          matching['alpha_pls'], matching['beta'])
    water_by_young = {}
    for key in young:
        group = groups[key]
        base = group[previous][1]
        pct = float(base['official_pct'])
        cu_tf = float(base['cu_apilado_t'])
        water = {'irrigation_m3': 0.0, 'profile_drainage_m3': 0.0, 'fitted_drainage_m3': 0.0}
        for i in range((end-start).days+1):
            day = start + timedelta(days=i)
            idx, row = group[day]
            if float(row['q_riego_m3h']) == 0:
                output[idx]['reconciled_pct'] = pct
                output[idx]['fitted_q_drenaje_m3h'] = 0.0
                continue
            qd = factor * float(row['profile_q_drenaje_m3h'])
            q_eff = beta * float(row['q_riego_m3h'])
            if not isfinite(qd) or qd > q_eff + 1e-10:
                raise ValueError(f'infeasible drainage flow cap: {key} {day}')
            water['irrigation_m3'] += 24 * q_eff
            water['profile_drainage_m3'] += 24 * float(row['profile_q_drenaje_m3h'])
            water['fitted_drainage_m3'] += 24 * qd
            cd_eff, cr_eff = alpha_p * float(row['cu_drenaje_gL']), alpha_r * float(row['cu_riego_gL'])
            pct += 100 * .024 * (qd * cd_eff - q_eff * cr_eff) / cu_tf
            output[idx]['q_riego_recon_m3h'] = q_eff
            output[idx]['cu_riego_recon_gL'] = cr_eff
            output[idx]['cu_drenaje_recon_gL'] = cd_eff
            if not isfinite(pct):
                raise ValueError('nonfinite recovery')
            output[idx]['reconciled_pct'] = pct
            output[idx]['fitted_q_drenaje_m3h'] = qd
        water['irrigation_minus_fitted_m3'] = water['irrigation_m3'] - water['fitted_drainage_m3']
        water['fitted_minus_profile_m3'] = water['fitted_drainage_m3'] - water['profile_drainage_m3']
        water_by_young[key] = water
    delivered = held_net + ((factor * alpha_p * young_drain - alpha_r * beta * young_in) if factor is not None else 0.0)
    curve_net = sum(float(group[end][1]['cu_apilado_t']) * (float(output[group[end][0]]['reconciled_pct']) - float(group[previous][1]['official_pct'])) / 100 for key, group in groups.items() if str(key[0]).strip().upper() in {'SU', 'SULFUROS', 'SULFURO'})
    if abs(curve_net - float(target_net_t)) > 1e-6:
        raise ValueError('recovery curve net does not match target')
    return output, {'lambda': factor, 'target_net_t': float(target_net_t), 'delivered_net_t': delivered,
                    'net_residual_t': float(target_net_t)-delivered, 'curve_net_t': curve_net, 'young': young,
                    'mature': mature, 'protected_history': history,
                    'water_by_young': water_by_young, 'concentration_match': matching,
                    'mature_drainage_ratio': mature_drainage_ratio,
                    'water_qualification': 'Diferencia incluye almacenamiento y otras entradas o perdidas; no es almacenamiento medido.',
                    'method': 'offline net-only conditional profile fit'}
