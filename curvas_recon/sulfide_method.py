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


def reconcile_sulfides(rows, case_start, case_end, target_net_t):
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
    if not young:
        if abs(float(target_net_t) - held_net) > 1e-6:
            raise ValueError('infeasible target without young cohorts')
        factor = None
    else:
        if young_drain <= 0 or required < 0:
            raise ValueError('infeasible young drainage target')
        factor = required / young_drain
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
            pct += 100 * .024 * (qd * float(row['cu_drenaje_gL']) - float(row['q_riego_m3h']) * float(row['cu_riego_gL'])) / cu_tf
            if not isfinite(pct):
                raise ValueError('nonfinite recovery')
            output[idx]['reconciled_pct'] = pct
            output[idx]['fitted_q_drenaje_m3h'] = qd
        water['irrigation_minus_fitted_m3'] = water['irrigation_m3'] - water['fitted_drainage_m3']
        water['fitted_minus_profile_m3'] = water['fitted_drainage_m3'] - water['profile_drainage_m3']
        water_by_young[key] = water
    delivered = held_net + (factor * young_drain if factor is not None else 0.0) - young_in
    curve_net = sum(float(group[end][1]['cu_apilado_t']) * (float(output[group[end][0]]['reconciled_pct']) - float(group[previous][1]['official_pct'])) / 100 for key, group in groups.items() if str(key[0]).strip().upper() in {'SU', 'SULFUROS', 'SULFURO'})
    if abs(curve_net - float(target_net_t)) > 1e-6:
        raise ValueError('recovery curve net does not match target')
    return output, {'lambda': factor, 'target_net_t': float(target_net_t), 'delivered_net_t': delivered,
                    'net_residual_t': float(target_net_t)-delivered, 'curve_net_t': curve_net, 'young': young,
                    'mature': mature, 'protected_history': history,
                    'water_by_young': water_by_young,
                    'water_qualification': 'Diferencia incluye almacenamiento y otras entradas o perdidas; no es almacenamiento medido.',
                    'method': 'offline net-only conditional profile fit'}
