"""Filas de entrada del ajuste de Sulfuros para cualquier Caso oficial.

Arma el contrato canonico de `sulfide_inputs` solo con series que el dash ya
tiene en memoria para la ventana (riego, Cu de riego, Cu de drenaje, curvas de
recuperacion medidas, Cu apilado de la campana y primer riego real). No abre
conexiones ni escribe: es una funcion pura sobre esos datos.

Supuestos explicitos:
  * Recuperacion medida y base del dia previo/cierre del mes anterior salen de
    la misma curva medida; sin dato exacto en una fecha requerida la entrada se
    rechaza, nunca se rellena.
  * El perfil de drenaje de las pilas jovenes es una forma de referencia
    (rampa por defecto del motor x riego), no una medicion; el ajuste la
    reescala con un factor comun.
  * Las pilas con mas de 30 dias no necesitan perfil de drenaje.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from .curve_recalc import cu_tf_toneladas
from .pad_cycles import split_into_cycles
from .ramp_curve import factores
from .sulfide_inputs import SulfideInputError

MAX_YOUNG_AGE_DAYS = 30
PROFILE_SOURCE = ('referencia: rampa por defecto del motor x riego; '
                  'modelado, not measured')
CURVE_SOURCE = 'curva de recuperacion medida del dashboard (sin relleno)'


def _pile_name(raw):
    try:
        return f'P{int(str(raw).lstrip("Pp")):02d}'
    except ValueError as exc:
        raise SulfideInputError(f'pila invalida: {raw}') from exc


def _as_day(value):
    return pd.Timestamp(value).date()


def _curve_lookup(curve):
    return {_as_day(d): float(v) for d, v in zip(curve.get('dates', []), curve.get('values', []))
            if v is not None and v == v}


def build_sulfide_rows(week_start, week_end, material, curves, wip, first_irrigation, *,
                       meseta=0.95):
    """Filas canonicas por pila y dia (dia previo, cierre del mes anterior y
    toda la ventana) para las pilas de Sulfuros que riegan en la ventana."""
    start, end = _as_day(week_start), _as_day(week_end)
    month_start = end.replace(day=1)
    previous, month_end = start - timedelta(days=1), month_start - timedelta(days=1)
    riego = material.get('riego')
    if riego is None or getattr(riego, 'empty', True):
        raise SulfideInputError('sin riego medido en la ventana del Caso')
    window = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    idx = pd.DatetimeIndex([pd.Timestamp(d) for d in window])
    cu_riego = material.get('cu_riego')
    drena = material.get('drena_cu')
    by_name = {_pile_name(c): c for c in riego.columns}
    ini_by_pile = {_pile_name(k): _as_day(v) for k, v in first_irrigation.items()}
    curves_by_pile = {f'P{int(k):02d}': v for k, v in curves.items()}
    rows = []
    for pile in sorted(by_name):
        series = riego[by_name[pile]].reindex(idx)
        if not (series.fillna(0) > 0).any():
            continue                                    # no riega en la ventana
        birth = ini_by_pile.get(pile)
        if birth is None:
            raise SulfideInputError(f'{pile}: sin primer riego de la campana vigente')
        info = wip.get(pile) or {}
        cu_tf = cu_tf_toneladas(info.get('CuTf'))
        if cu_tf is None:
            raise SulfideInputError(f'{pile}: sin Cu apilado de la campana')
        curve = curves_by_pile.get(pile)
        if not curve:
            raise SulfideInputError(f'{pile}: sin curva de recuperacion medida')
        measured = _curve_lookup(curve)
        cycles = split_into_cycles(list(curve['dates']), list(curve['values']), end)
        campaign = max(len(cycles), 1)
        young = (end - birth).days <= MAX_YOUNG_AGE_DAYS
        for day in dict.fromkeys([month_end, previous, *window]):  # ventana que parte el dia 1: mismo dia
            pct = measured.get(day)
            if pct is None and (day in (month_end, previous) or not young):
                raise SulfideInputError(f'{pile}: sin recuperacion medida el {day.isoformat()}')
            row = dict(pad='SULFUROS', pile=pile, campaign=campaign, date=day.isoformat(),
                       first_irrigation=birth.isoformat(), cu_apilado_t=cu_tf,
                       official_pct=pct, observed_pct=pct, observation_source=CURVE_SOURCE)
            if day >= start:
                ts = pd.Timestamp(day)
                q = series.get(ts)
                row['q_riego_m3h'] = None if q is None or q != q else float(q)
                row['cu_riego_gL'] = _daily(cu_riego, ts, None)
                row['cu_drenaje_gL'] = _daily(drena, ts, by_name[pile])
                if young:
                    for field in ('q_riego_m3h', 'cu_riego_gL', 'cu_drenaje_gL'):
                        if row[field] is None:
                            raise SulfideInputError(f'{pile}: sin {field} el {day.isoformat()}')
                    if row['q_riego_m3h'] <= 0:
                        raise SulfideInputError(f'{pile}: riego nulo el {day.isoformat()}')
                    f = factores([(day - birth).days + 1], meseta)[0]
                    row['profile_q_drenaje_m3h'] = f * row['q_riego_m3h']
                    row['drainage_profile_source'] = PROFILE_SOURCE
            rows.append(row)
    if not rows:
        raise SulfideInputError('ninguna pila de Sulfuros riega en la ventana del Caso')
    return rows


def _daily(frame, ts, column):
    if frame is None or getattr(frame, 'empty', True):
        return None
    data = frame if column is None else frame[column] if column in frame.columns else None
    if data is None:
        return None
    if hasattr(data, 'columns'):                         # serie unica del material
        data = data.iloc[:, 0]
    value = data.reindex([ts]).iloc[0]
    return None if value is None or value != value else float(value)


def make_source_provider(material, curves, wip, first_irrigation, caso):
    """Proveedor para `load_sulfide_inputs(source_provider=...)`."""
    def provider(*, week_start, week_end, case_id, anchor):
        target = None
        for key in ('SULFUROS', 'sulfuros'):
            sub = anchor.get(key) if isinstance(anchor, dict) else None
            if isinstance(sub, dict) and isinstance(sub.get('net_cu_target_t'), (int, float)):
                target = float(sub['net_cu_target_t'])
        if target is None:
            raise SulfideInputError('el ancla no trae objetivo de Cu neto de Sulfuros')
        return {
            'rows': build_sulfide_rows(week_start, week_end, material, curves, wip, first_irrigation),
            'source_ids': {'case_id': case_id, 'solver_run_id': caso['run_id']},
            'target_period_start': _as_day(week_start).isoformat(),
            'target_net_t': target,
            'metadata': {'provider': 'dashboard series', 'qualification': PROFILE_SOURCE},
        }
    return provider
