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


def match_pad_concentrations(rows_by_state, held_net_t, target_net_t, targets, max_change=0.30, tolerance=0.001):
    """Reescala las concentraciones de las pilas NUEVAS para que las concentraciones
    ponderadas por caudal del pad (riego y PLS) coincidan con las de los flujos globales.

    Las maduras no se tocan. Con alpha_r y alpha_p (factores sobre Cu riego y Cu PLS de las
    nuevas) y lambda (factor del perfil de drenaje) hay tres incognitas y tres condiciones:
    ponderada de riego, ponderada de PLS y cierre del Cu neto; la solucion es cerrada.

    `rows_by_state`: {'mature': [...], 'young': [...]} con filas diarias (q_riego_m3h,
    cu_riego_gL, cu_drenaje_gL y, en las nuevas, profile_q_drenaje_m3h).
    `targets`: {'cu_riego_g_l', 'cu_pls_g_l'}. Devuelve un dict con `status`
    ('aplicado' | 'sin_cambio' | 'no_aplicado' | 'sin_objetivos'), los factores y las
    ponderadas antes/despues; nunca fuerza una solucion fuera del limite."""
    cr_goal, cp_goal = (targets or {}).get('cu_riego_g_l'), (targets or {}).get('cu_pls_g_l')
    if not (isinstance(cr_goal, Real) and isinstance(cp_goal, Real) and cr_goal > 0 and cp_goal > 0):
        return dict(status='sin_objetivos')
    mature, young = rows_by_state.get('mature', []), rows_by_state.get('young', [])
    pos = lambda row, field: row.get(field) is not None and row['q_riego_m3h'] > 0
    riego = [r for r in mature + young if r['q_riego_m3h'] > 0 and r.get('cu_riego_gL') is not None]
    q_all = sum(r['q_riego_m3h'] for r in riego)
    m_rc = sum(r['q_riego_m3h'] * r['cu_riego_gL'] for r in mature if r['q_riego_m3h'] > 0 and r.get('cu_riego_gL') is not None)
    y_rc = sum(r['q_riego_m3h'] * r['cu_riego_gL'] for r in young if r['q_riego_m3h'] > 0 and r.get('cu_riego_gL') is not None)
    mature_pls = [r for r in mature if r['q_riego_m3h'] > 0 and r.get('cu_drenaje_gL') is not None]
    q_m = sum(FDRENA_PROXY * r['q_riego_m3h'] for r in mature_pls)
    s_m = sum(FDRENA_PROXY * r['q_riego_m3h'] * r['cu_drenaje_gL'] for r in mature_pls)
    young_pls = [r for r in young if r['q_riego_m3h'] > 0 and r.get('cu_drenaje_gL') is not None]
    y_q = sum(r['profile_q_drenaje_m3h'] for r in young_pls)
    y_pc = sum(r['profile_q_drenaje_m3h'] * r['cu_drenaje_gL'] for r in young_pls)
    out = dict(status='no_aplicado', max_change=max_change, tolerance=tolerance,
               objetivo_cu_riego_g_l=float(cr_goal), objetivo_cu_pls_g_l=float(cp_goal))
    if not young or y_rc <= 0 or y_pc <= 0 or y_q <= 0 or q_all <= 0:
        return dict(out, motivo='sin pilas nuevas con riego y concentraciones medidas')
    out['cu_riego_pad_g_l_antes'] = (m_rc + y_rc) / q_all
    # ponderada de PLS antes del ajuste: con el lambda del cierre neto (alpha = 1)
    lam0 = ((target_net_t - held_net_t) / K_F + y_rc) / y_pc
    out['cu_pls_pad_g_l_antes'] = (s_m + lam0 * y_pc) / (q_m + lam0 * y_q) if q_m + lam0 * y_q > 0 else None
    gap = lambda value, goal: abs(value - goal) / goal
    if (gap(out['cu_riego_pad_g_l_antes'], cr_goal) <= tolerance
            and out['cu_pls_pad_g_l_antes'] is not None and gap(out['cu_pls_pad_g_l_antes'], cp_goal) <= tolerance):
        return dict(out, status='sin_cambio', motivo='las ponderadas ya coinciden con los flujos globales')
    alpha_r = (cr_goal * q_all - m_rc) / y_rc
    a = ((target_net_t - held_net_t) / K_F + alpha_r * y_rc) / y_pc          # = alpha_p * lambda
    lam = ((s_m + a * y_pc) / cp_goal - q_m) / y_q
    out.update(alpha_riego=alpha_r, lambda_=lam)
    if not (lam > 0):
        return dict(out, motivo='el caudal de PLS global exige un drenaje no positivo en las nuevas')
    alpha_p = a / lam
    out['alpha_pls'] = alpha_p
    limit = lambda x: 1 - max_change <= x <= 1 + max_change
    if not (limit(alpha_r) and limit(alpha_p)):
        return dict(out, motivo=f'requiere cambiar las concentraciones de las nuevas mas de {max_change:.0%} '
                                f'(riego x{alpha_r:.3f}, PLS x{alpha_p:.3f})')
    if any(lam * r['profile_q_drenaje_m3h'] > r['q_riego_m3h'] + 1e-10 for r in young_pls):
        return dict(out, motivo='el drenaje ajustado superaria al riego en alguna pila nueva')
    out.update(status='aplicado', cu_riego_pad_g_l_despues=(m_rc + alpha_r * y_rc) / q_all,
               cu_pls_pad_g_l_despues=(s_m + a * y_pc) / (q_m + lam * y_q))
    return out


def reconcile_sulfides(rows, case_start, case_end, target_net_t, concentration_targets=None,
                       max_concentration_change=0.30, concentration_tolerance=0.001):
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
    matching = match_pad_concentrations(state_rows, held_net, float(target_net_t), concentration_targets,
                                        max_concentration_change, concentration_tolerance) if young else {'status': 'sin_pilas_nuevas'}
    if not young:
        if abs(float(target_net_t) - held_net) > 1e-6:
            raise ValueError('infeasible target without young cohorts')
        factor = None
    else:
        if young_drain <= 0 or required < 0:
            raise ValueError('infeasible young drainage target')
        factor = required / young_drain
    alpha_r = alpha_p = 1.0
    if matching.get('status') == 'aplicado':
        factor, alpha_r, alpha_p = matching['lambda_'], matching['alpha_riego'], matching['alpha_pls']
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
            if not isfinite(qd) or qd > float(row['q_riego_m3h']) + 1e-10:
                raise ValueError(f'infeasible drainage flow cap: {key} {day}')
            water['irrigation_m3'] += 24 * float(row['q_riego_m3h'])
            water['profile_drainage_m3'] += 24 * float(row['profile_q_drenaje_m3h'])
            water['fitted_drainage_m3'] += 24 * qd
            cd_eff, cr_eff = alpha_p * float(row['cu_drenaje_gL']), alpha_r * float(row['cu_riego_gL'])
            pct += 100 * .024 * (qd * cd_eff - float(row['q_riego_m3h']) * cr_eff) / cu_tf
            output[idx]['cu_riego_recon_gL'] = cr_eff
            output[idx]['cu_drenaje_recon_gL'] = cd_eff
            if not isfinite(pct):
                raise ValueError('nonfinite recovery')
            output[idx]['reconciled_pct'] = pct
            output[idx]['fitted_q_drenaje_m3h'] = qd
        water['irrigation_minus_fitted_m3'] = water['irrigation_m3'] - water['fitted_drainage_m3']
        water['fitted_minus_profile_m3'] = water['fitted_drainage_m3'] - water['profile_drainage_m3']
        water_by_young[key] = water
    delivered = held_net + ((factor * alpha_p * young_drain - alpha_r * young_in) if factor is not None else 0.0)
    curve_net = sum(float(group[end][1]['cu_apilado_t']) * (float(output[group[end][0]]['reconciled_pct']) - float(group[previous][1]['official_pct'])) / 100 for key, group in groups.items() if str(key[0]).strip().upper() in {'SU', 'SULFUROS', 'SULFURO'})
    if abs(curve_net - float(target_net_t)) > 1e-6:
        raise ValueError('recovery curve net does not match target')
    return output, {'lambda': factor, 'target_net_t': float(target_net_t), 'delivered_net_t': delivered,
                    'net_residual_t': float(target_net_t)-delivered, 'curve_net_t': curve_net, 'young': young,
                    'mature': mature, 'protected_history': history,
                    'water_by_young': water_by_young, 'concentration_match': matching,
                    'water_qualification': 'Diferencia incluye almacenamiento y otras entradas o perdidas; no es almacenamiento medido.',
                    'method': 'offline net-only conditional profile fit'}
