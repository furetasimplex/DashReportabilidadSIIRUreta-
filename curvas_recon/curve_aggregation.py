"""Pure helpers for local, weighted recovery curve groups."""
from __future__ import annotations

import math
import uuid

import pandas as pd


def save_local_group(groups, group_id, name, members, active_members):
    """Validate and upsert a browser-local group without touching data sources."""
    groups = list(groups or [])
    clean_name = str(name or '').strip()
    clean_members = list(dict.fromkeys(members or []))
    active = set(active_members or [])
    if not clean_name:
        return groups, 'Escribe un nombre para el grupo.'
    if len(clean_members) < 2 or any(member not in active for member in clean_members):
        return groups, 'Selecciona al menos dos pilas activas del Caso actual.'
    identifier = group_id or uuid.uuid4().hex
    group = {'id': identifier, 'name': clean_name, 'members': clean_members}
    if identifier in [item.get('id') for item in groups]:
        groups = [group if item.get('id') == identifier else item for item in groups]
    else:
        groups.append(group)
    return groups, 'Grupo guardado en este navegador.'


def delete_local_group(groups, group_id):
    return [item for item in (groups or []) if item.get('id') != group_id]


def restore_local_groups():
    return []


def combine_recovery_series(members):
    """Combine campaign curves by exact calendar day and Cu stacked.

    Each member has ``id``, ``cu_tf_t`` and ``series`` with ``xs``, ``ys`` and
    optional ``sources``. A point is emitted only when every member has a
    finite point on that date; gaps are never filled or carried forward.
    """
    if not members:
        return {'xs': [], 'ys': [], 'sources': [], 'cu_tf_t': [],
                'recovered_cu_t': [], 'member_ids': []}
    weights = []
    indexed = []
    for member in members:
        try:
            weight = float(member.get('cu_tf_t'))
        except (TypeError, ValueError):
            return {'xs': [], 'ys': [], 'sources': [], 'cu_tf_t': [],
                    'recovered_cu_t': [], 'member_ids': []}
        if not math.isfinite(weight) or weight <= 0:
            return {'xs': [], 'ys': [], 'sources': [], 'cu_tf_t': [],
                    'recovered_cu_t': [], 'member_ids': []}
        weights.append(weight)
        series = member.get('series') or {}
        points = {}
        for i, (day, pct) in enumerate(zip(series.get('xs') or [], series.get('ys') or [])):
            try:
                stamp = pd.Timestamp(day).normalize()
                if pd.isna(stamp):
                    continue
                key = stamp.date()
            except (TypeError, ValueError):
                continue
            try:
                val = float(pct)
            except (TypeError, ValueError):
                val = float('nan')
            sources = series.get('sources') or []
            points[key] = (val if math.isfinite(val) else None,
                           sources[i] if i < len(sources) else 'Medido')
        indexed.append(points)

    present = set().union(*(set(p) for p in indexed))
    if not present:
        dates = []
    else:
        dates = list(pd.date_range(min(present), max(present), freq='D').date)
    total_cu_tf = sum(weights)
    xs, ys, sources, recovered = [], [], [], []
    for day in dates:
        # Missing dates and explicit gaps stay missing; no partial-member mean.
        complete = all(day in points and points[day][0] is not None
                       for points in indexed)
        recovered_t = (sum(points[day][0] * weight / 100.0
                           for points, weight in zip(indexed, weights))
                       if complete else None)
        xs.append(day)
        recovered.append(recovered_t)
        ys.append(recovered_t / total_cu_tf * 100.0 if complete else None)
        point_sources = [points[day][1] for points in indexed if day in points]
        if not complete or not point_sources:
            source = 'Medido'
        elif all(source == 'Histórico reconciliado' for source in point_sources):
            source = 'Histórico reconciliado'
        elif all(source == 'Reconciliado del Caso' for source in point_sources):
            source = 'Reconciliado del Caso'
        elif any(source in ('Reconciliado del Caso', 'Histórico reconciliado')
                 for source in point_sources):
            source = 'Mixto (medido/reconciliado)'
        else:
            source = 'Medido'
        sources.append(source)
    return {'xs': xs, 'ys': ys, 'sources': sources,
            'cu_tf_t': [total_cu_tf] * len(xs), 'recovered_cu_t': recovered,
            'member_ids': [m.get('id') for m in members]}
