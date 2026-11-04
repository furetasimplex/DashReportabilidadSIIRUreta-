"""Recuperacion medida de una pila a partir de datos medidos (logica pura).

Completa `Recuperaciones_pad` para los dias en que SIIR aun no trae lectura:
parte de la ultima lectura guardada y suma, dia a dia, el Cu neto extraido
calculado con riego y concentraciones medidos. Es la misma formula que usa
`report_metodo` entre lecturas primarias:

    ext [t Cu/dia] = 0.024 * (Q_dren * Cu_PLS - Q_riego * Cu_riego)
    Q_dren         = FDRENA_BASE * Q_riego       (no hay caudal de drenaje medido)
    d recuperacion = 100 * ext / Cu apilado [t]

Valida solo para pilas con mas de 30 dias desde el primer riego: contra las
lecturas reales de septiembre 2026 el error a 7 dias es 0.00-0.02 pp en pilas
de mas de 70 dias y 0.07 pp a los 37-43 dias; en pilas jovenes sube a 2-9 pp
(el 0.95 supone un drenaje que una pila nueva aun no tiene). Por eso una pila
con 30 dias o menos nunca se completa: su curva la ajusta el metodo de Sulfuros.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import isfinite

FDRENA_BASE = 0.95
UNIT_FACTOR = 0.024               # m3/h * g/L * 24 h / 1000 -> t Cu/dia
MIN_AGE_DAYS = 30                 # solo pilas con MAS de 30 dias
MAX_BASE_GAP_DAYS = 31            # el CLI no extiende una lectura base mas antigua que esto


def _num(value):
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def extend_recovery(last_date, last_pct, cu_tf_t, first_irrigation, until, q_riego, cu_riego, cu_drena,
                    min_age_days=MIN_AGE_DAYS, fdrena=FDRENA_BASE):
    """Dias nuevos de recuperacion medida para una pila.

    `q_riego`, `cu_riego`, `cu_drena`: {date: valor medido}, sin relleno.
    Devuelve (filas [(fecha, pct)], motivo_de_corte | None). Se detiene en el
    primer dia que no pueda calcularse y no continua despues de un hueco.
    """
    last_date, until, first_irrigation = _day(last_date), _day(until), _day(first_irrigation)
    cu_tf_t, last_pct = _num(cu_tf_t), _num(last_pct)
    if cu_tf_t is None or cu_tf_t <= 0:
        return [], 'sin Cu apilado de la campana'
    if last_pct is None:
        return [], 'sin lectura base'
    if last_date >= until:
        return [], None
    if first_irrigation > last_date:
        return [], 'campana nueva sin lecturas base'
    rows, pct = [], last_pct
    day = last_date + timedelta(days=1)
    while day <= until:
        if (day - first_irrigation).days <= min_age_days:
            return rows, f'{day.isoformat()}: pila con {(day - first_irrigation).days} dias (<= {min_age_days}); la ajusta el metodo'
        q = _num(q_riego.get(day))
        if q is None:
            return rows, f'{day.isoformat()}: sin riego medido'
        if q > 0:
            cr, cd = _num(cu_riego.get(day)), _num(cu_drena.get(day))
            if cr is None or cd is None:
                return rows, f"{day.isoformat()}: sin {'Cu de riego' if cr is None else 'Cu de drenaje'} medido"
            pct += 100.0 * UNIT_FACTOR * (fdrena * q * cd - q * cr) / cu_tf_t
        rows.append((day, pct))
        day += timedelta(days=1)
    return rows, None


def _day(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def plan_completion(base_rows, cu_tf, first_irrigation, q_riego, cu_riego, cu_drena, until,
                    window_start=None, min_age_days=MIN_AGE_DAYS, max_base_gap_days=MAX_BASE_GAP_DAYS):
    """Plan por pila para completar `Recuperaciones_pad` hasta `until`.

    `base_rows`: {pila: {'fecha', 'pct', 'ids': {...}}} con la ultima lectura de
    cada pila; `cu_tf`/`first_irrigation`: {pila: valor}; `q_riego`, `cu_riego`
    y `cu_drena`: {pila: {fecha: valor}} medidos sin relleno.
    Devuelve (filas_a_insertar, reporte_por_pila). Cada fila lleva los
    identificadores de la ultima lectura de su pila (misma campana).
    """
    until = _day(until)
    plan, report = [], []
    for pile in sorted(base_rows):
        base = base_rows[pile]
        last = _day(base['fecha'])
        info = dict(pila=pile, ultima_lectura=last.isoformat(), pct_inicial=base['pct'], filas=0,
                    pct_final=None, estado='omitida', motivo=None)
        report.append(info)
        if last >= until:
            info.update(estado='al dia', motivo='ya tiene lectura hasta la fecha pedida')
            continue
        if window_start is not None and (_day(window_start) - last).days > max_base_gap_days:
            info['motivo'] = f'ultima lectura ({last.isoformat()}) mas de {max_base_gap_days} dias antes de la ventana'
            continue
        if pile not in first_irrigation or pile not in cu_tf:
            info['motivo'] = 'sin primer riego o Cu apilado de la campana vigente'
            continue
        rows, stop = extend_recovery(
            last, base['pct'], cu_tf[pile], first_irrigation[pile], until, q_riego.get(pile, {}),
            cu_riego, cu_drena.get(pile, {}), min_age_days=min_age_days)
        for day, pct in rows:
            plan.append(dict(pila=pile, fecha=day, recuperacion_pct=pct, ids=base['ids']))
        if rows:
            info.update(filas=len(rows), pct_final=rows[-1][1], estado='completa' if stop is None else 'parcial')
        info['motivo'] = stop
    return plan, report


def compare_with_official(plan, report, official, tol_pp=0.05):
    """Compara las recuperaciones calculadas con las curvas del reporte oficial.

    Deben coincidir salvo en las pilas nuevas (no completadas). `official`:
    {pila: {'YYYY-MM-DD': pct}}. Devuelve (filas por pila, todo_igual).
    """
    calculated = {}
    for row in plan:
        calculated.setdefault(row['pila'], {})[_day(row['fecha']).isoformat()] = row['recuperacion_pct']
    out, all_equal = [], True
    for info in report:
        pile = info['pila']
        ours, theirs = calculated.get(pile), official.get(pile, {})
        record = dict(pila=pile, dias_comparados=0, max_abs_pp=None, fecha_max=None, dif_final_pp=None,
                      oficial_final_pct=None, calculada_final_pct=None, estado=None)
        if not ours:
            record['estado'] = 'no completada (joven u omitida): se ajusta con el metodo'
        else:
            diffs = {d: ours[d] - theirs[d] for d in ours if d in theirs}
            if not diffs:
                record['estado'] = 'sin curva oficial en esas fechas'
                all_equal = False
            else:
                worst = max(diffs, key=lambda d: abs(diffs[d]))
                last = max(diffs)
                record.update(dias_comparados=len(diffs), max_abs_pp=abs(diffs[worst]), fecha_max=worst,
                              dif_final_pp=diffs[last], oficial_final_pct=theirs[last], calculada_final_pct=ours[last])
                equal = abs(diffs[worst]) <= tol_pp and len(diffs) == len(ours)
                record['estado'] = 'igual' if equal else ('difiere' if abs(diffs[worst]) > tol_pp else 'faltan fechas oficiales')
                all_equal &= equal
        out.append(record)
    return out, all_equal
