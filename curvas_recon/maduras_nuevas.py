"""Metodo "maduras fijas, nuevas moviles": nucleo puro, sin SQL ni Dash.

Contrato (vigente para Oxidos y Sulfuros; ver docs/METODO_MADURAS_NUEVAS.md):

* Edad = dias calendario desde el primer riego real de la campana hasta el
  cierre del Caso. Una clasificacion por pila para toda la ventana.
* Mayor de 30 dias (madura): conserva EXACTA la recuperacion observada.
* Menor de 30 dias (nueva): se mueve escalando su perfil de drenaje modelado
  por un factor comun ``lambda`` para cerrar el Cu neto objetivo del PAD
  (F25 Oxidos / F29 Sulfuros del run oficial). Riego y concentraciones
  observados no se tocan.
* Exactamente 30 dias: conserva la recuperacion oficial (frontera protegida).
* Historia anterior a la ventana: intacta. No se inventan caudales ni se
  rellenan mediciones.
* Resultado LOCAL: nada de aqui escribe en SQL.

Una pila que nace dentro de la ventana (primer riego posterior al inicio del
Caso) arranca en su nacimiento: no se exigen ni se inventan filas anteriores,
y su recuperacion parte de 0 % salvo que exista una fila medida el dia previo.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta
from math import isfinite
from numbers import Real

AGE_THRESHOLD_DAYS = 30
# Cotas provisionales de lambda (factor comun sobre el perfil modelado de
# drenaje). No estan calibradas con ensayos: fuera de ellas el ajuste no es
# creible y se informa el error en vez de caer a otro metodo.
LAMBDA_BOUNDS = (0.2, 5.0)
NET_TOLERANCE_T = 1e-6

PAD_ALIASES = {
    'SU': 'SULFUROS', 'SULFURO': 'SULFUROS', 'SULFUROS': 'SULFUROS',
    'OX': 'OXIDOS', 'OXIDO': 'OXIDOS', 'OXIDOS': 'OXIDOS',
}


class MadurasError(ValueError):
    """Entrada o resultado invalido del metodo."""


class CoverageError(MadurasError):
    """Faltan filas diarias o la linea base; nunca se rellenan mediciones."""


class InfeasibleError(MadurasError):
    """El objetivo neto no es alcanzable con las nuevas dentro de las cotas."""

    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details


def normalize_pad(name):
    try:
        return PAD_ALIASES[str(name).strip().upper()]
    except KeyError as exc:
        raise MadurasError(f'PAD desconocido: {name!r}') from exc


def as_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise MadurasError(f'fecha invalida: {value!r}') from exc


def _number(row, field, key=None, day=None, positive=False):
    value = row.get(field) if hasattr(row, 'get') else None
    if (value is None or isinstance(value, bool) or not isinstance(value, Real)
            or not isfinite(value) or value < 0 or (positive and value <= 0)):
        where = f' ({key[1]} c{key[2]} {day})' if key else ''
        raise MadurasError(f'invalid {field}{where}: {value!r}')
    return float(value)


def _label_key(key):
    return f'{key[1]} campana {key[2]}'


def plan_cohorts(rows, case_start, case_end, pad):
    """Agrupa filas por (pad, pila, campana) y valida cobertura y metadatos.

    Devuelve ``(plan, start, end)`` con, por cohorte: indice y fila por dia,
    nacimiento, edad al cierre, dia de arranque en la ventana, dia base,
    porcentaje base y su origen, y la clase (young/mature/boundary).
    """
    start, end = as_date(case_start), as_date(case_end)
    if end < start:
        raise MadurasError('la ventana del Caso termina antes de empezar')
    pad = normalize_pad(pad)
    groups = {}
    for index, row in enumerate(rows):
        if 'pad' not in row or normalize_pad(row['pad']) != pad:
            continue
        key = (pad, row['pile'], int(row['campaign']))
        day = as_date(row['date'])
        group = groups.setdefault(key, {})
        if day in group:
            raise MadurasError(f'duplicate row: {key} {day}')
        group[day] = (index, row)
    plan = {}
    for key, group in groups.items():
        first = next(iter(group.values()))[1]
        cu_tf = _number(first, 'cu_apilado_t', key, positive=True)
        birth = as_date(first['first_irrigation'])
        for day, (_, row) in group.items():
            if _number(row, 'cu_apilado_t', key, day, positive=True) != cu_tf or as_date(row['first_irrigation']) != birth:
                raise MadurasError(f'inconsistent cohort metadata: {key}')
        age = (end - birth).days
        if age < 0:
            raise MadurasError(f'first irrigation after case end: {key}')
        active_start = max(start, birth)
        expected = [active_start + timedelta(days=i) for i in range((end - active_start).days + 1)]
        missing = [day for day in expected if day not in group]
        if missing:
            raise CoverageError(
                f'incomplete daily coverage: {_label_key(key)} '
                f'sin fila en {len(missing)} dia(s) de {active_start}..{end} '
                f'(primero: {missing[0]}); no se rellenan mediciones')
        base_day = active_start - timedelta(days=1)
        if base_day in group:
            base_pct = _number(group[base_day][1], 'official_pct', key, base_day)
            base_source = 'row'
        elif birth >= start:
            base_pct, base_source = 0.0, 'campaign_birth_zero'
        else:
            raise CoverageError(
                f'missing prior baseline: {_label_key(key)} necesita fila oficial '
                f'del dia {base_day} (dia anterior al inicio de su ventana)')
        plan[key] = dict(
            group=group, cu_tf=cu_tf, birth=birth, age=age, active_start=active_start,
            expected=expected, base_day=base_day, base_pct=base_pct, base_source=base_source,
            born_in_window=birth >= start,
            kind='mature' if age > AGE_THRESHOLD_DAYS else 'boundary' if age == AGE_THRESHOLD_DAYS else 'young')
    return plan, start, end


def reconcile_pad(rows, case_start, case_end, target_net_t, *, pad,
                  lambda_bounds=LAMBDA_BOUNDS):
    """Aplica maduras fijas / nuevas moviles a un PAD y cierra su Cu neto.

    ``rows``: filas diarias con pad, pile, campaign, date, first_irrigation,
    cu_apilado_t, official_pct, observed_pct y, para las nuevas en la
    ventana, q_riego_m3h, cu_riego_gL, cu_drenaje_gL, profile_q_drenaje_m3h.
    No muta la entrada. Devuelve ``(filas, auditoria)``.
    """
    pad = normalize_pad(pad)
    plan, start, end = plan_cohorts(rows, case_start, case_end, pad)
    if isinstance(target_net_t, bool) or not isinstance(target_net_t, Real) or not isfinite(target_net_t):
        raise MadurasError('invalid net target')
    target = float(target_net_t)
    low, high = lambda_bounds
    output = deepcopy(rows)
    young, mature, boundary, history, born = [], [], [], [], []
    held_net = young_in = young_drain = 0.0
    lambda_cap, cap_at = None, None
    for key, info in plan.items():
        group, cu_tf, base_pct = info['group'], info['cu_tf'], info['base_pct']
        history.extend((key, day) for day in group if day < start)
        if info['born_in_window']:
            born.append(key)
        # Dias de la ventana anteriores al nacimiento: ni se mueven ni se
        # inventan; la recuperacion oficial/medida queda tal cual.
        for day, (idx, row) in group.items():
            if start <= day < info['active_start']:
                output[idx]['reconciled_pct'] = _number(row, 'official_pct', key, day)
                output[idx]['recovery_source'] = 'official'
        expected = info['expected']
        if info['kind'] in ('mature', 'boundary'):
            field, source = (('observed_pct', 'observed') if info['kind'] == 'mature'
                             else ('official_pct', 'official'))
            (mature if info['kind'] == 'mature' else boundary).append(key)
            for day in expected:
                idx, row = group[day]
                output[idx]['reconciled_pct'] = _number(row, field, key, day)
                output[idx]['recovery_source'] = source
            held_net += cu_tf * (_number(group[end][1], field, key, end) - base_pct) / 100
            continue
        young.append(key)
        for day in expected:
            row = group[day][1]
            qr = _number(row, 'q_riego_m3h', key, day)
            cr = _number(row, 'cu_riego_gL', key, day)
            cd = _number(row, 'cu_drenaje_gL', key, day)
            qd = _number(row, 'profile_q_drenaje_m3h', key, day)
            young_in += .024 * qr * cr
            young_drain += .024 * qd * cd
            if qd > 0:
                cap = qr / qd
                if lambda_cap is None or cap < lambda_cap:
                    lambda_cap, cap_at = cap, (key, day)
    required = target - held_net + young_in
    factor = None
    reach = None
    if not young:
        if abs(target - held_net) > NET_TOLERANCE_T:
            raise InfeasibleError(
                f'Objetivo neto {target:.6f} t Cu inalcanzable en {pad}: no hay pilas '
                f'nuevas (<{AGE_THRESHOLD_DAYS} d) que se muevan y las protegidas '
                f'(maduras y de frontera) ya entregan {held_net:.6f} t. '
                'Sin nuevas no se ajusta ni se cae a otro metodo.',
                target_net_t=target, held_net_t=held_net)
    else:
        top = high if lambda_cap is None else min(high, lambda_cap)
        if young_drain > 0 and top >= low:
            reach = (held_net + low * young_drain - young_in,
                     held_net + top * young_drain - young_in)
        if reach:
            reach_txt = (f' Con lambda en [{low:g}, {top:.4f}] el Cu neto alcanzable es '
                         f'{reach[0]:.3f}..{reach[1]:.3f} t.')
        elif top < low:
            reach_txt = (f' El tope Qd <= Qr limita lambda <= {top:.4f}, bajo la cota minima {low:g}: '
                         'ningun lambda admisible.')
        else:
            reach_txt = ''
        if young_drain <= 0:
            raise InfeasibleError(
                f'{pad}: el perfil de drenaje modelado de las nuevas no entrega Cu '
                '(caudal o concentracion nulos); no hay con que escalar.',
                target_net_t=target)
        factor = required / young_drain
        if required < 0 or factor < low - 1e-12:
            raise InfeasibleError(
                f'Objetivo neto {target:.6f} t Cu inalcanzable en {pad}: requiere '
                f'lambda={factor:.4f}, bajo la cota minima {low:g} (las protegidas '
                f'ya entregan {held_net:.6f} t; el riego de las nuevas aporta '
                f'{young_in:.6f} t).' + reach_txt,
                target_net_t=target, lambda_required=factor, lambda_bounds=(low, high),
                lambda_cap=lambda_cap, reachable_net_t=reach)
        if factor > high + 1e-12:
            raise InfeasibleError(
                f'Objetivo neto {target:.6f} t Cu inalcanzable en {pad}: requiere '
                f'lambda={factor:.4f}, sobre la cota maxima {high:g}.' + reach_txt,
                target_net_t=target, lambda_required=factor, lambda_bounds=(low, high),
                lambda_cap=lambda_cap, reachable_net_t=reach)
        if lambda_cap is not None and factor > lambda_cap * (1 + 1e-12):
            (cap_key, cap_day) = cap_at
            raise InfeasibleError(
                f'Objetivo neto {target:.6f} t Cu inalcanzable en {pad}: requiere '
                f'lambda={factor:.4f}, pero el caudal de drenaje no puede superar el '
                f'riego (Qd <= Qr): {_label_key(cap_key)} el {cap_day} limita '
                f'lambda <= {lambda_cap:.4f}.' + reach_txt,
                target_net_t=target, lambda_required=factor, lambda_bounds=(low, high),
                lambda_cap=lambda_cap, reachable_net_t=reach)
    water_by_young = {}
    for key in young:
        info = plan[key]
        group = info['group']
        pct = info['base_pct']
        cu_tf = info['cu_tf']
        water = {'irrigation_m3': 0.0, 'profile_drainage_m3': 0.0, 'fitted_drainage_m3': 0.0}
        for day in info['expected']:
            idx, row = group[day]
            qr = float(row['q_riego_m3h'])
            qd = factor * float(row['profile_q_drenaje_m3h'])
            if not isfinite(qd) or qd > qr + 1e-10:
                raise InfeasibleError(
                    f'Qd > Qr en {_label_key(key)} el {day}: {qd:.4f} > {qr:.4f} m3/h',
                    target_net_t=target)
            water['irrigation_m3'] += 24 * qr
            water['profile_drainage_m3'] += 24 * float(row['profile_q_drenaje_m3h'])
            water['fitted_drainage_m3'] += 24 * qd
            pct += 100 * .024 * (qd * float(row['cu_drenaje_gL']) - qr * float(row['cu_riego_gL'])) / cu_tf
            if not isfinite(pct):
                raise MadurasError('nonfinite recovery')
            output[idx]['reconciled_pct'] = pct
            output[idx]['recovery_source'] = 'net_fit'
            output[idx]['fitted_q_drenaje_m3h'] = qd
        water['irrigation_minus_fitted_m3'] = water['irrigation_m3'] - water['fitted_drainage_m3']
        water['fitted_minus_profile_m3'] = water['fitted_drainage_m3'] - water['profile_drainage_m3']
        water_by_young[key] = water
    delivered = held_net + (factor * young_drain if factor is not None else 0.0) - young_in
    curve_net = sum(
        info['cu_tf'] * (float(output[info['group'][end][0]]['reconciled_pct']) - info['base_pct']) / 100
        for info in plan.values())
    if abs(curve_net - target) > NET_TOLERANCE_T:
        raise MadurasError('recovery curve net does not match target')
    audit = {
        'pad': pad, 'lambda': factor, 'target_net_t': target, 'delivered_net_t': delivered,
        'net_residual_t': target - delivered, 'curve_net_t': curve_net, 'young': young,
        'mature': mature, 'exact_30_pending': boundary, 'protected_history': history,
        'born_in_window': born, 'water_by_young': water_by_young,
        'age_by_pile': {key: info['age'] for key, info in plan.items()},
        'baseline_by_pile': {key: {'pct': info['base_pct'], 'source': info['base_source'],
                                   'day': info['base_day'].isoformat()}
                             for key, info in plan.items()},
        'lambda_bounds': (low, high), 'lambda_cap': lambda_cap,
        'reachable_net_t': reach,
        'water_qualification': 'Diferencia incluye almacenamiento y otras entradas o perdidas; no es almacenamiento medido.',
        'method': 'offline net-only conditional profile fit',
    }
    return output, audit


def carry_previous_result(rows, previous_rows, previous_start, previous_end, *, pad):
    """Hereda como linea base la recuperacion que dejo el Caso anterior.

    Devuelve una copia de ``rows`` donde, para las fechas de la ventana del
    Caso anterior, ``official_pct`` pasa a ser el ``reconciled_pct`` de ese
    Caso (historia protegida). ``previous_rows`` es la salida de
    :func:`reconcile_pad` (o ``res['recovery_rows']``).
    """
    pad = normalize_pad(pad)
    p_start, p_end = as_date(previous_start), as_date(previous_end)
    prior = {}
    for row in previous_rows:
        if normalize_pad(row.get('pad', pad)) != pad or 'reconciled_pct' not in row:
            continue
        day = as_date(row['date'])
        if p_start <= day <= p_end:
            prior[(row['pile'], int(row['campaign']), day)] = float(row['reconciled_pct'])
    out = deepcopy(rows)
    for row in out:
        if 'pad' not in row or normalize_pad(row['pad']) != pad:
            continue
        day = as_date(row['date'])
        if p_start <= day <= p_end:
            value = prior.get((row['pile'], int(row['campaign']), day))
            if value is not None:
                row['official_pct'] = value
                row['baseline_source'] = 'previous_case_result'
    return out


def reconcile_chain(cases, *, pad, lambda_bounds=LAMBDA_BOUNDS):
    """Encadena Casos consecutivos de un PAD.

    ``cases``: lista cronologica de dicts con ``rows``, ``start``, ``end`` y
    ``target_net_t``. Cada Caso exige comenzar el dia siguiente al cierre del
    anterior, hereda su recuperacion como linea base y resuelve su propio
    lambda. Devuelve una lista de ``(filas, auditoria)``.
    """
    results, previous = [], None
    for case in cases:
        start, end = as_date(case['start']), as_date(case['end'])
        rows = case['rows']
        if previous is not None:
            p_start, p_end, p_rows = previous
            if start != p_end + timedelta(days=1):
                raise MadurasError(
                    f'Casos no consecutivos: el anterior cierra {p_end} y este inicia {start}')
            rows = carry_previous_result(rows, p_rows, p_start, p_end, pad=pad)
        out, audit = reconcile_pad(rows, start, end, case['target_net_t'], pad=pad,
                                   lambda_bounds=lambda_bounds)
        results.append((out, audit))
        previous = (start, end, out)
    return results


def direct_recovery_rows(res, *, case_only=False):
    """Filas ``recovery_rows`` del resultado local, o ``[]`` si no es local."""
    if not isinstance(res, dict) or not res.get('local_direct_recovery'):
        return []
    rows = list(res.get('recovery_rows') or [])
    if case_only:
        ws, we = as_date(res['week_start']), as_date(res['week_end'])
        rows = [r for r in rows if ws <= as_date(r['date']) <= we]
    return rows


def direct_recovery_series(res, *, with_campaign=False, case_only=False):
    """Recuperacion directa diaria por pila para consumidores del reporte.

    ``res`` es el ``res`` del motor (``joint['res']``) o el guardado en la
    corrida local; debe tener ``local_direct_recovery`` y ``recovery_rows``.
    Devuelve ``{(pad, num_pila): pandas.Series}`` con ``pad`` en
    ``'OXIDOS' | 'SULFUROS'``, ``num_pila`` entero (P07 -> 7) y una Series
    ``fecha -> recuperacion %`` ordenada, con indice ``DatetimeIndex`` llamado
    ``date``. Incluye la historia protegida anterior al Caso (usar
    ``case_only=True`` para recortar a la ventana). Valores = ``reconciled_pct``:
    observado en maduras, oficial en frontera/historia, ajustado en nuevas.

    Una pila con varias campanas en los datos es ambigua: se lanza
    ``MadurasError`` salvo ``with_campaign=True``, que usa la clave
    ``(pad, num_pila, campana)``. Cada Series lleva en ``attrs``:
    ``campaign``, ``cu_apilado_t``, ``first_irrigation`` y ``sources`` (fecha ->
    origen de cada punto). Sin recuperacion directa devuelve ``{}``.
    """
    import pandas as pd
    grouped = {}
    for row in direct_recovery_rows(res, case_only=case_only):
        pad = normalize_pad(row['pad'])
        num = int(str(row['pile']).strip().upper().removeprefix('P'))
        grouped.setdefault((pad, num, int(row['campaign'])), []).append(row)
    by_pile = {}
    for (pad, num, campaign), rows in grouped.items():
        by_pile.setdefault((pad, num), []).append(campaign)
    out = {}
    for (pad, num, campaign), rows in sorted(grouped.items()):
        if not with_campaign and len(by_pile[(pad, num)]) > 1:
            raise MadurasError(
                f'{pad} P{num:02d} tiene varias campanas {sorted(by_pile[(pad, num)])}; '
                'use with_campaign=True')
        rows = sorted(rows, key=lambda r: as_date(r['date']))
        index = pd.DatetimeIndex([pd.Timestamp(as_date(r['date'])) for r in rows], name='date')
        series = pd.Series([float(r.get('reconciled_pct', r['official_pct'])) for r in rows], index=index,
                           name=f'{pad}-P{num:02d}', dtype='float64')
        series.attrs.update(
            campaign=campaign, cu_apilado_t=float(rows[0]['cu_apilado_t']),
            first_irrigation=as_date(rows[0]['first_irrigation']).isoformat(),
            sources={ts: r.get('recovery_source', 'official') for ts, r in zip(index, rows)})
        out[(pad, num, campaign) if with_campaign else (pad, num)] = series
    return out
