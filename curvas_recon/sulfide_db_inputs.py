"""Filas de entrada del ajuste de Sulfuros para cualquier Caso oficial.

Arma el contrato canonico de `sulfide_inputs` con las series del dash para la
ventana del Caso. `build_sulfide_rows` es pura; `load_saved_profile` es la
unica lectura SQL (SELECT) y no escribe nada.

Reglas verificadas contra el Caso 10009 (las filas generadas coinciden campo a
campo con el paquete congelado y, con el perfil guardado, reproducen lambda y
recuperaciones exactamente):
  * Recuperacion medida y base del dia previo/cierre del mes anterior salen de
    la curva primaria (Recuperaciones_pad), restringida a la campana vigente.
    Antes del inicio de la campana vigente la recuperacion es 0; dentro de ella
    un dato faltante se rechaza, nunca se rellena.
  * Cu de riego y de drenaje: lecturas sin ffill ni valor de respaldo.
  * Perfil de drenaje de las pilas jovenes: el perfil modelado guardado del
    Caso; si no existe completo, un perfil plano proporcional al riego. Ambos
    son modelados, no mediciones; el ajuste los reescala con un factor comun.
  * Un dia sin riego no aporta flujo ni Cu: la recuperacion no cambia.
"""
from __future__ import annotations

from datetime import timedelta

import pandas as pd

from .curve_recalc import cu_tf_toneladas
from .pad_cycles import split_into_cycles
from .sulfide_inputs import SulfideInputError

MAX_YOUNG_AGE_DAYS = 30
SAVED_PROFILE_SOURCE = 'perfil modelado guardado del Caso; not measured'
FLAT_PROFILE_SOURCE = 'perfil plano proporcional al riego; modelado, not measured'
CURVE_SOURCE = 'curva primaria Recuperaciones_pad, campana vigente (sin relleno)'


def _pile_name(raw):
    try:
        return f'P{int(str(raw).strip().lstrip("Pp")):02d}'
    except ValueError as exc:
        raise SulfideInputError(f'pila invalida: {raw}') from exc


def _as_day(value):
    return pd.Timestamp(value).date()


def _current_campaign(curve, end):
    """(inicio, {fecha: pct}, numero) de la campana vigente al cierre."""
    pairs = sorted((_as_day(d), float(v)) for d, v in zip(curve.get('dates', []), curve.get('values', []))
                   if v is not None and v == v and _as_day(d) <= end)
    if not pairs:
        return None, {}, 0
    cycles = split_into_cycles([d for d, _ in pairs], [v for _, v in pairs], end)
    last = cycles[-1]
    start = _as_day(last['start_date'])
    return start, {d: v for d, v in pairs if d >= start}, len(cycles)


def _daily(frame, ts, column):
    if frame is None or getattr(frame, 'empty', True):
        return None
    if column is None:
        data = frame.iloc[:, 0] if hasattr(frame, 'columns') else frame
    elif column in getattr(frame, 'columns', ()):
        data = frame[column]
    else:
        return None
    value = data.reindex([ts]).iloc[0]
    return None if value is None or value != value else float(value)


def build_sulfide_rows(week_start, week_end, material, curves, wip, first_irrigation,
                       saved_profile=None):
    """Filas canonicas por pila y dia (cierre del mes anterior, dia previo y
    toda la ventana) para las pilas de Sulfuros que riegan en la ventana.

    `material`: riego, cu_riego y drena_cu de la ventana SIN relleno.
    `saved_profile`: {(pila, 'YYYY-MM-DD'): q_pls_m3h} guardado para el Caso.
    Devuelve (filas, fuente_del_perfil).
    """
    start, end = _as_day(week_start), _as_day(week_end)
    month_end = end.replace(day=1) - timedelta(days=1)
    previous = start - timedelta(days=1)
    riego = material.get('riego')
    if riego is None or getattr(riego, 'empty', True):
        raise SulfideInputError('sin riego medido en la ventana del Caso')
    window = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in window])
    by_name = {_pile_name(c): c for c in riego.columns}
    births = {_pile_name(k): _as_day(v) for k, v in first_irrigation.items()}
    curves_by_pile = {_pile_name(k): v for k, v in curves.items()}
    rows = []
    missing = {}                  # fecha -> pilas sin recuperacion medida obligatoria
    last_reading = {}
    for pile in sorted(by_name):
        q_series = riego[by_name[pile]].reindex(idx)
        if not (q_series.fillna(0) > 0).any():
            continue                                    # no riega en la ventana
        birth = births.get(pile)
        if birth is None:
            raise SulfideInputError(f'{pile}: sin primer riego de la campana vigente')
        cu_tf = cu_tf_toneladas((wip.get(pile) or {}).get('CuTf'))
        if cu_tf is None:
            raise SulfideInputError(f'{pile}: sin Cu apilado de la campana')
        cycle_start, measured, campaign = _current_campaign(curves_by_pile.get(pile) or {}, end)
        young = (end - birth).days <= MAX_YOUNG_AGE_DAYS
        for day in dict.fromkeys([month_end, previous, *window]):   # ventana desde el dia 1: coinciden
            pct = measured.get(day)
            if pct is None and young and (cycle_start is None or day < cycle_start):
                pct = 0.0 if day < start else None      # campana aun sin recuperacion
            # Obligatorio: base (dias previos) y cierre de las maduras. Un dia
            # intermedio sin lectura queda como hueco.
            if pct is None and (day < start or (not young and day == end)):
                missing.setdefault(day, []).append(pile)
                last_reading[pile] = max(measured, default=None)
            row = dict(pad='SULFUROS', pile=pile, campaign=max(campaign, 1), date=day.isoformat(),
                       first_irrigation=birth.isoformat(), cu_apilado_t=cu_tf,
                       official_pct=pct, observed_pct=pct, observation_source=CURVE_SOURCE)
            if day >= start:
                ts = pd.Timestamp(day)
                q = q_series.get(ts)
                row['q_riego_m3h'] = 0.0 if q is None or q != q else float(q)
                row['cu_riego_gL'] = _daily(material.get('cu_riego'), ts, None)
                row['cu_drenaje_gL'] = _daily(material.get('drena_cu'), ts, by_name[pile])
                if young and row['q_riego_m3h'] > 0:
                    for field in ('cu_riego_gL', 'cu_drenaje_gL'):
                        if row[field] is None:
                            raise SulfideInputError(f'{pile}: sin {field} medido el {day.isoformat()}')
            rows.append(row)
    if missing:
        details = []
        for day in sorted(missing):
            known = [last_reading[p] for p in missing[day] if last_reading[p] is not None]
            tail = f' (ultima lectura disponible: {max(known).isoformat()})' if known else ''
            details.append(f"{', '.join(missing[day])}: sin recuperacion medida el {day.isoformat()}{tail}")
        raise SulfideInputError(
            '; '.join(details) + '. Recuperaciones_pad no tiene las lecturas necesarias: '
            'cargue las recuperaciones oficiales de esas fechas y reintente.')
    if not rows:
        raise SulfideInputError('ninguna pila de Sulfuros riega en la ventana del Caso')
    return _attach_profile(rows, start, end, saved_profile or {})


def _attach_profile(rows, start, end, saved):
    """Perfil guardado solo si cubre todos los dias con riego de todas las
    jovenes; si no, plano para todas (no se mezclan formas entre pilas)."""
    young = [r for r in rows if r['date'] >= start.isoformat()
             and (end - _as_day(r['first_irrigation'])).days <= MAX_YOUNG_AGE_DAYS]
    needed = [r for r in young if r['q_riego_m3h'] > 0]
    use_saved = bool(needed) and all((saved.get((r['pile'], r['date'])) or 0) > 0 for r in needed)
    source = SAVED_PROFILE_SOURCE if use_saved else FLAT_PROFILE_SOURCE
    for r in young:
        if r['q_riego_m3h'] == 0:
            r['profile_q_drenaje_m3h'] = 0.0
        else:
            r['profile_q_drenaje_m3h'] = float(saved[(r['pile'], r['date'])]) if use_saved else r['q_riego_m3h']
        r['drainage_profile_source'] = source
    return rows, source


def load_saved_profile(case_id, week_start, week_end):
    """{(pila, fecha): q_pls} del ultimo resultado guardado del Caso (SELECT)."""
    from sqlalchemy import text
    from .db_pipeline import get_engine, SCHEMA
    query = text(f"""
        WITH candidatos AS (
            SELECT d.parcela_nombre AS pila,
                   CAST(DATEADD(day, d.dia_offset, r.semana_lunes) AS date) AS fecha,
                   CAST(d.q_pls AS float) AS q_pls,
                   ROW_NUMBER() OVER (PARTITION BY d.parcela_nombre, DATEADD(day, d.dia_offset, r.semana_lunes)
                                      ORDER BY r.id DESC, d.id DESC) AS orden
            FROM {SCHEMA}.reconciliacion_detalle_dia d
            JOIN {SCHEMA}.reconciliacion_run r ON r.id = d.run_id
            WHERE r.caso_id = :caso AND d.label = 'SULFUROS'
              AND DATEADD(day, d.dia_offset, r.semana_lunes) BETWEEN :inicio AND :fin)
        SELECT pila, fecha, q_pls FROM candidatos WHERE orden = 1 AND q_pls IS NOT NULL""")
    with get_engine().connect() as conn:
        result = conn.execute(query, {'caso': int(case_id), 'inicio': _as_day(week_start),
                                      'fin': _as_day(week_end)})
        return {(_pile_name(p), _as_day(f).isoformat()): float(q) for p, f, q in result}


def make_source_provider(material, curves, wip, first_irrigation, caso, saved_profile=None):
    """Proveedor para `load_sulfide_inputs(source_provider=...)`."""
    def provider(*, week_start, week_end, case_id, anchor):
        sub = anchor.get('SULFUROS') if isinstance(anchor, dict) else None
        target = sub.get('net_cu_target_t') if isinstance(sub, dict) else None
        if not isinstance(target, (int, float)) or isinstance(target, bool):
            raise SulfideInputError('el ancla no trae objetivo de Cu neto de Sulfuros')
        rows, profile_source = build_sulfide_rows(week_start, week_end, material, curves, wip,
                                                  first_irrigation, saved_profile)
        return {
            'rows': rows,
            'source_ids': {'case_id': case_id, 'solver_run_id': caso['run_id']},
            'target_period_start': _as_day(week_start).isoformat(),
            'target_net_t': float(target),
            'metadata': {'provider': 'series del dashboard', 'drainage_profile': profile_source},
        }
    return provider
