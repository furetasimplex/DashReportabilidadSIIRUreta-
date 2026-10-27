"""Read-only group panels: summed flows and flow-weighted concentrations."""
from collections import OrderedDict
from threading import RLock

import pandas as pd
import plotly.graph_objects as go

from .group_solution_series import aggregate_group_solution_series

_CACHE = OrderedDict()
_LOCK = RLock()


def build_group_solution_charts(a, group, data, caso_id):
    members = list(dict.fromkeys((group or {}).get('members') or []))
    raw = a._get_group_raw(data, caso_id)
    if len(members) < 2 or not isinstance(raw, dict):
        return (a.empty_figure('Selecciona un grupo válido del Caso'),) * 2
    ws, we, _ = a._store_window(data)
    ws, we = pd.Timestamp(ws).normalize(), pd.Timestamp(we).normalize()
    active = set()
    for pile in (raw.get('res') or {}).get('piles', []):
        prefix = {'OXIDOS': 'rox', 'SULFUROS': 'rsu'}.get(pile.get('label'))
        try:
            if prefix:
                num = int(str(pile.get('parcela', pile.get('p'))).upper().removeprefix('P'))
                active.add(f'{prefix}-P{num:02d}')
        except (TypeError, ValueError):
            continue
    if any(member not in active for member in members):
        return (a.empty_figure('El grupo contiene pilas fuera del Caso actual'),) * 2
    key = (str(data.get('raw_token')), data.get('caso_run_id'), tuple(members),
           str(group.get('name')), str(ws), str(we), id(a.WIP_META))
    with _LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return tuple(go.Figure(fig) for fig in _CACHE[key])
    stack = a._rl_tms_by_pile(we, data['raw_token'])
    meta = {}
    for member in members:
        pad, number = member.split('-P')
        label, num = a._PAD_TO_LABEL[pad], int(number)
        row = stack.get((label, num))
        if not row or pd.isna(pd.Timestamp(row.get('f0'))):
            return (a.empty_figure('Falta el inicio de campaña de una pila del grupo'),) * 2
        meta[member] = (label, num, pd.Timestamp(row['f0']).normalize())
    first = min(ws, min(info[2] for info in meta.values()))
    calendar = list(pd.date_range(first, we, freq='D'))
    materials = {label: a._load_material_window(label, min(m[2] for m in meta.values() if m[0] == label), we)
                 for label in {m[0] for m in meta.values()}}
    result = raw.get('res') or {}
    rows = list(result.get('daily') or [])
    if not rows:
        rows = [dict(row, label=row.get('label', pile.get('label')),
                     parcela=row.get('parcela', row.get('p', pile.get('parcela', pile.get('p')))))
                for pile in result.get('piles', []) for row in pile.get('daily', [])]
    indexed = {}
    for row in rows:
        try:
            k = (row['label'], int(str(row.get('parcela', row.get('p'))).upper().removeprefix('P')),
                 pd.Timestamp(row['date']).normalize())
            if ws <= k[2] <= we:
                indexed[k] = row
        except (KeyError, TypeError, ValueError):
            continue
    measured, reconciled = {}, {}
    for member, (label, num, start) in meta.items():
        mat, p = materials[label], f'P{num:02d}'
        measured[member], reconciled[member] = {}, {}
        for day in calendar:
            row = indexed.get((label, num, day))
            if ws <= day <= we and (row is not None or day >= start):
                # The validated Case wins over campaign metadata at a boundary.
                row = row or {}
                measured[member][day] = dict(q_riego=row.get('q_riego_medido'), q_pls=row.get('q_pls_medido'),
                                            cu_riego=row.get('cu_riego_medido'), cu_pls=row.get('cu_pls_medido'))
                reconciled[member][day] = dict(q_riego=row.get('q_riego_final'), q_pls=row.get('q_pls_final'),
                                              cu_riego=row.get('cu_riego_recon'), cu_pls=row.get('cu_pls_recon'))
            elif day < start:
                zero = dict(q_riego=0.0, q_pls=0.0, cu_riego=None, cu_pls=None)
                measured[member][day] = zero
                if ws <= day <= we:
                    reconciled[member][day] = dict(zero)
            else:
                q = mat['riego'].at[day, p] if day in mat['riego'].index and p in mat['riego'].columns else None
                cr = mat['cu_riego'].get(day)
                cp = mat['drena_cu'].at[day, p] if day in mat['drena_cu'].index and p in mat['drena_cu'].columns else None
                # Same historical drainage proxy as the individual flow view.
                qp = float(q) * a.FDRENA_MAX if q is not None and pd.notna(q) else None
                measured[member][day] = dict(q_riego=q, q_pls=qp, cu_riego=cr, cu_pls=cp)
    aggregated = {'medido': aggregate_group_solution_series(measured),
                  'reconciliado': aggregate_group_solution_series(reconciled)}
    flows = a._stacked_figure('Caudal riego', 'Caudal PLS')
    concentrations = a._stacked_figure('Cu riego', 'Cu PLS')
    for mode, daily in aggregated.items():
        for panel, q_field, cu_field, name, color in [
                (1, 'q_riego', 'cu_riego', 'riego', '#2a78d6'),
                (2, 'q_pls', 'cu_pls', 'PLS', '#E86D1F')]:
            style = dict(color=color, width=1.5 if mode == 'medido' else 3,
                         dash='dash' if mode == 'medido' else 'solid')
            dates = [row['date'] for row in daily]
            flows.add_trace(go.Scatter(x=dates, y=[row[q_field] for row in daily], mode='lines',
                            name=f'Caudal {name} ({mode})', line=style, connectgaps=False), row=panel, col=1)
            concentrations.add_trace(go.Scatter(x=dates, y=[row[cu_field] for row in daily], mode='lines',
                                     name=f'Cu {name} ({mode})', line=style, connectgaps=False), row=panel, col=1)
    for fig, label, units in [(flows, 'Caudales sumados', ('Q riego (m³/h)', 'Q PLS (m³/h)')),
                              (concentrations, 'Concentraciones ponderadas', ('Cu riego (g/L)', 'Cu PLS (g/L)'))]:
        a._add_week_zoom_box(fig, ws, we)
        fig.update_layout(title=f"{group.get('name', 'Grupo')} — {label}",
            paper_bgcolor=a.CHART_SURFACE, plot_bgcolor=a.CHART_SURFACE,
            font=dict(color=a.CHART_INK_PRIMARY, family='Inter, system-ui, sans-serif'),
            legend=dict(bgcolor='rgba(0,0,0,0)'), hovermode='x unified',
            uirevision=f'group-solutions-{key}', margin=dict(l=50, r=30, t=60, b=40), height=640,
            xaxis=dict(type='date', gridcolor='#E5E7EB'), xaxis2=dict(type='date', gridcolor='#E5E7EB'),
            yaxis=dict(title=units[0], gridcolor='#E5E7EB'), yaxis2=dict(title=units[1], gridcolor='#E5E7EB'))
        visible = a.visible_xaxis_range([(trace.x, trace.y) for trace in fig.data])
        if visible:
            fig.update_xaxes(range=visible)
    with _LOCK:
        _CACHE[key] = (flows, concentrations)
        while len(_CACHE) > 16:
            _CACHE.popitem(last=False)
    return flows, concentrations
