"""Vista global de recuperaciones reconciliadas para todas las pilas de un Caso.

El módulo no calcula ni consulta SQL por sí mismo: las dependencias de la
reconciliación se inyectan desde pad_dashboard. El dataset se cachea por
identidad de Caso/corrida/ventana y los sliders solo cambian la figura.
"""
from __future__ import annotations

import threading
from copy import deepcopy
from .curve_aggregation import combine_recovery_series
from .curve_recalc import cu_tf_toneladas
from collections import OrderedDict

import numpy as np
import pandas as pd
import plotly.graph_objects as go

_CACHE = OrderedDict()
_LOCK = threading.RLock()
_CACHE_LIMIT = 3
COLORS = ['#2a78d6', '#008300', '#e87ba4', '#eda100', '#1baf7a', '#4a3aa7', '#e34948']


def store_identity(data, caso_id):
    """Valida un Store vigente y devuelve su identidad normalizada, o None."""
    if not isinstance(data, dict) or not caso_id:
        return None
    try:
        stored_case = int(data.get('caso_id'))
        selected_case = int(caso_id)
        run = int(data.get('caso_run_id'))
        ws, we = pd.Timestamp(data['week_start']).normalize(), pd.Timestamp(data['week_end']).normalize()
    except (TypeError, ValueError, KeyError, OverflowError):
        return None
    if stored_case != selected_case or not data.get('raw_token') or pd.isna(ws) or pd.isna(we) or we < ws:
        return None
    return (stored_case, run, str(data['raw_token']), ws.date().isoformat(), we.date().isoformat())


def _physical_piles(raw):
    """Pilas físicas reportadas por el solver, sin IDs virtuales ni duplicados."""
    found, seen = [], set()
    for row in ((raw.get('res') or {}).get('piles') or []):
        label = row.get('label')
        if label not in ('OXIDOS', 'SULFUROS'):
            continue
        n = row.get('parcela', row.get('p'))
        try:
            if isinstance(n, str):
                n = n.strip().upper().removeprefix('P')
            n = int(n)
        except (TypeError, ValueError):
            continue
        key = (label, n)
        if key not in seen:
            seen.add(key)
            found.append(key)
    return found


def _first_irrigation(label, num, material, case_start, case_end, wip_meta):
    """Edad operacional: primer Q de riego positivo en campaña disponible."""
    p = f'P{num:02d}'
    info = (wip_meta.get(label, {}).get(p) or {})
    try:
        candidate = pd.Timestamp(info.get('ini_aporte')).normalize()
    except (TypeError, ValueError):
        candidate = pd.NaT
    riego = (material or {}).get('riego')
    if isinstance(riego, pd.DataFrame) and p in riego.columns and len(riego.index):
        vals = pd.to_numeric(riego[p], errors='coerce')
        active = vals.index[vals.gt(0)]
        if pd.notna(candidate):
            active = active[pd.DatetimeIndex(active).normalize() >= candidate]
        if len(active):
            return min(pd.Timestamp(active.min()).normalize(), case_end)
    return None


def build_dataset(data, caso_id, *, get_raw, ensure_full_data, wip_meta,
                  reconstruct, load_material, cutoff=None):
    """Carga una sola vez curvas históricas+Caso reconciliadas por Caso/run/token."""
    ident = store_identity(data, caso_id)
    if ident is None:
        return None, 'El Caso cambió o el resultado guardado está vencido. Ejecuta nuevamente el cálculo.'
    raw = get_raw(data, caso_id)
    if not isinstance(raw, dict) or raw.get('caso', {}).get('run_id') != ident[1]:
        return None, 'No hay datos locales válidos para el Caso seleccionado.'
    with _LOCK:
        if ident in _CACHE:
            _CACHE.move_to_end(ident)
            return _CACHE[ident], _CACHE[ident].get('warning', '')
    ensure_full_data()
    wip_meta = wip_meta() if callable(wip_meta) else wip_meta
    cutoff = cutoff() if callable(cutoff) else cutoff
    ws, we = pd.Timestamp(data['week_start']).normalize(), pd.Timestamp(data['week_end']).normalize()
    # La edad se define al cierre oficial del Caso. La reconstrucción interna
    # ya respeta JOINT_DATA_CUTOFF y tampoco entrega puntos posteriores a we.
    end = we
    piles = _physical_piles(raw)
    if not piles:
        return None, 'El Caso no contiene pilas físicas activas.'
    # Un único rango material por PAD, desde la campaña más antigua al cierre.
    starts = {}
    for label, num in piles:
        try:
            start = pd.Timestamp((wip_meta.get(label, {}).get(f'P{num:02d}') or {}).get('ini_aporte')).normalize()
        except (TypeError, ValueError):
            start = pd.NaT
        starts[label] = min(starts.get(label, end), start) if pd.notna(start) else starts.get(label, end)
    material_by_pad = {label: load_material(label, start, end)
                       for label, start in starts.items() if start <= end}
    dataset = {'identity': ident, 'case_end': end, 'groups': {'OXIDOS': [], 'SULFUROS': []}}
    for label, num in piles:
        material = material_by_pad.get(label)
        series = reconstruct(label, num, ws, end, raw=raw,
                             history_token=data.get('raw_token'), material=material)
        age_start = _first_irrigation(label, num, material, ws, end, wip_meta)
        if age_start is None:
            continue
        xs, ys, src = [], [], []
        for day, value, source in zip(series.get('xs', []), series.get('ys', []), series.get('sources', [])):
            stamp = pd.Timestamp(day).normalize()
            # La vista contiene únicamente puntos reconciliados, sin tramos medidos.
            is_rec = str(source).startswith('Hist') or source == 'Reconciliado del Caso'
            xs.append(stamp)
            ys.append(value if is_rec else None)
            src.append(source if is_rec else '')
        dataset['groups'][label].append({'num': num, 'start': age_start,
                                         'cu_tf_t': cu_tf_toneladas(series.get('cu_tf')),
                                         'xs': xs, 'ys': ys, 'sources': src})
    with _LOCK:
        _CACHE[ident] = dataset
        _CACHE.move_to_end(ident)
        while len(_CACHE) > _CACHE_LIMIT:
            _CACHE.popitem(last=False)
    missing = len(piles) - sum(len(group) for group in dataset['groups'].values())
    warning = (f'{missing} pila(s) omitida(s): no se encontró primer riego positivo desde el inicio de campaña.'
               if missing else '')
    dataset['warning'] = warning
    return dataset, warning



def add_group_curves(dataset, groups):
    """Reuse the physical reconciled series, weighted by stacked Cu."""
    out = deepcopy(dataset)
    lookup = {f"{prefix}-P{item['num']:02d}": item
              for label, prefix in [('OXIDOS','rox'),('SULFUROS','rsu')]
              for item in dataset['groups'][label]}
    warnings = []
    for group in groups or []:
        members = group.get('members') or []
        if len(set(members)) < 2 or any(m not in lookup or not lookup[m].get('cu_tf_t') for m in members):
            warnings.append(str(group.get('name') or 'Suma sin datos'))
            continue
        items = [lookup[m] for m in members]
        summed = combine_recovery_series([dict(id=m, cu_tf_t=lookup[m]['cu_tf_t'],
            series=dict(xs=lookup[m]['xs'],ys=lookup[m]['ys'],sources=lookup[m]['sources'])) for m in members])
        pads = {m.split('-P')[0] for m in members}
        item = dict(num=group['id'], name='Σ '+group['name']+(' [OX+SU]' if len(pads)>1 else ''),
                    start=min(it['start'] for it in items), xs=[pd.Timestamp(d) for d in summed['xs']],
                    ys=summed['ys'], sources=summed['sources'])
        for prefix, label in [('rox','OXIDOS'),('rsu','SULFUROS')]:
            if prefix in pads:
                out['groups'][label].append(item)
    return out, ('Sumas sin datos completos: '+', '.join(warnings) if warnings else '')


def _bounds(group, case_end=None):
    ages = []
    for item in group:
        if pd.notna(item['start']):
            end = pd.Timestamp(case_end).normalize() if case_end is not None else (item['xs'][-1] if item['xs'] else item['start'])
            ages.append(max(0, (end.date() - item['start'].date()).days))
    return [0, max(ages, default=0)]


def make_figure(dataset, label, age_range):
    """Renderiza las curvas seleccionadas por antigüedad en días al cierre del Caso."""
    fig = go.Figure()
    items = (dataset or {}).get('groups', {}).get(label, [])
    lo, hi = age_range or _bounds(items, (dataset or {}).get('case_end'))
    lo, hi = max(0, int(lo)), max(0, int(hi))
    cutoff = (dataset or {}).get('case_end')
    for i, item in enumerate(items):
        age_end = max(0, (pd.Timestamp(cutoff).date() - item['start'].date()).days) if cutoff is not None else 0
        # El slider filtra campañas por edad al cierre, preservando el historial
        # completo de cada campaña que queda seleccionada.
        if not lo <= age_end <= hi:
            continue
        x, y, hover = [], [], []
        for day, value, source in zip(item['xs'], item['ys'], item['sources']):
            age = (day.date() - item['start'].date()).days
            include = age >= 0 and (cutoff is None or day <= cutoff)
            x.append(age if include else None)
            y.append(value if include else None)
            hover.append(f"{day:%d/%m/%Y} · Edad {age} días · {source}" if include else '')
        fig.add_trace(go.Scatter(x=x, y=y, customdata=hover, mode='lines',
            name=item.get('name') or f"P{item['num']:02d}", connectgaps=False,
            line={'color': COLORS[i % len(COLORS)], 'width': 2.2},
            hovertemplate='Día %{x}<br>Recuperación: %{y:.2f}%<br>%{customdata}<extra>%{fullData.name}</extra>'))
    fig.update_layout(title=f'{label}: recuperaciones reconciliadas',
        paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
        font={'color': '#1F2937', 'family': 'Inter, system-ui, sans-serif'},
        xaxis_title='Días desde el primer riego de campaña',
        yaxis_title='Recuperación (%)', xaxis={'gridcolor': '#E5E7EB'},
        yaxis={'gridcolor': '#E5E7EB'}, hovermode='x unified',
        legend={'title': {'text': 'Pila'}}, margin={'l': 55, 'r': 20, 't': 45, 'b': 55})
    return fig


def layout_components(dbc, dcc, html, go):
    """Retorna botón y modal; IDs estables con namespace curvas-todas-rec."""
    return [
        dbc.Button('Ver todas las recuperaciones reconciliadas', id='curvas-todas-rec-open',
                   n_clicks=0, disabled=True, color='secondary', outline=True, className='action-secondary'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Recuperaciones reconciliadas de todas las pilas')),
            dbc.ModalBody([
                html.P('Curvas reconciliadas históricas y de la ventana del Caso, hasta su fecha de cierre. El eje X muestra días desde el primer riego real de cada campaña.'),
                html.H5('Óxidos'),
                html.Div([
                    html.Label('Antigüedad máxima al cierre del Caso (días; desde 0)'),
                    dcc.Slider(id='curvas-todas-rec-ox-age', min=0, max=1, value=1,
                        step=1, marks={0: '0'}, updatemode='mouseup',
                        tooltip={'placement': 'top', 'always_visible': False}),
                ], style={'maxWidth': '520px', 'width': '100%', 'padding': '8px 12px 24px',
                          'marginBottom': '12px'}),
                dcc.Graph(id='curvas-todas-rec-ox-chart', figure=go.Figure(),
                          style={'height': '390px', 'marginBottom': '24px'}),
                html.H5('Sulfuros'),
                html.Div([
                    html.Label('Antigüedad máxima al cierre del Caso (días; desde 0)'),
                    dcc.Slider(id='curvas-todas-rec-su-age', min=0, max=1, value=1,
                        step=1, marks={0: '0'}, updatemode='mouseup',
                        tooltip={'placement': 'top', 'always_visible': False}),
                ], style={'maxWidth': '520px', 'width': '100%', 'padding': '8px 12px 24px',
                          'marginBottom': '12px'}),
                dcc.Graph(id='curvas-todas-rec-su-chart', figure=go.Figure(),
                          style={'height': '390px', 'marginBottom': '24px'}),
                html.Div(id='curvas-todas-rec-status', className='text-warning'),
            ]),
            dbc.ModalFooter(dbc.Button('Cerrar', id='curvas-todas-rec-close', n_clicks=0,
                                       className='action-primary')),
        ], id='curvas-todas-rec-modal', is_open=False, size='xl', scrollable=True,
           className='curvas-recon-shell'),
        dcc.Store(id='curvas-todas-rec-dataset', data=None),
    ]


def calculation_ready(data, caso_id, get_raw):
    """Require a usable calculated result for the selected Case, without SQL."""
    if store_identity(data, caso_id) is None:
        return False
    try:
        raw = get_raw(data, caso_id)
        return isinstance(raw, dict) and bool(_physical_piles(raw))
    except Exception:
        return False


def register_callbacks(app, *, callback, Input, Output, State, ctx, build_kwargs):
    """Registra callbacks en app directamente (no añade SQL ni modifica solver)."""
    if not hasattr(app, 'clientside_callback'):
        return

    @callback(Output('curvas-todas-rec-open', 'disabled'),
              Input('curvas-recon-store', 'data'), Input('curvas-recon-caso', 'value'))
    def disable_until_calculated(data, caso_id):
        kwargs = build_kwargs() if callable(build_kwargs) else build_kwargs
        return not calculation_ready(data, caso_id, kwargs['get_raw'])

    @callback(Output('curvas-todas-rec-modal', 'is_open'),
              Input('curvas-todas-rec-open', 'n_clicks'), Input('curvas-todas-rec-close', 'n_clicks'),
              State('curvas-todas-rec-modal', 'is_open'), prevent_initial_call=True)
    def toggle_all(_open, _close, is_open):
        return not is_open if ctx.triggered_id == 'curvas-todas-rec-open' else False

    @callback(Output('curvas-todas-rec-dataset', 'data'), Output('curvas-todas-rec-status', 'children'),
              Input('curvas-todas-rec-modal', 'is_open'), Input('curvas-recon-store', 'data'),
              Input('curvas-recon-caso', 'value'), Input('curvas-grupos-store', 'data'), prevent_initial_call=True)
    def prepare_all(is_open, data, caso_id, groups):
        if not is_open:
            return None, ''
        kwargs = build_kwargs() if callable(build_kwargs) else build_kwargs
        dataset, message = build_dataset(data, caso_id, **kwargs)
        if dataset is None:
            return None, message
        dataset, group_warning = add_group_curves(dataset, groups)
        message = ' '.join(part for part in (message, group_warning) if part)
        # Build once. Slider changes only filter these figures in the browser.
        serial = {'identity': dataset['identity'], 'pads': {}}
        for label, items in dataset['groups'].items():
            hi = _bounds(items, dataset['case_end'])[1]
            figure = make_figure(dataset, label, [0, hi])
            ages = {(item.get('name') or f"P{item['num']:02d}"): max(0, (dataset['case_end'] - item['start']).days)
                    for item in items}
            for trace in figure.data:
                trace.meta = {'age_days': ages[trace.name]}
            serial['pads'][label] = {'max_age': hi, 'figure': figure.to_plotly_json()}
        return serial, message

    if not hasattr(app, 'clientside_callback'):
        return

    app.clientside_callback(
        """function(dataset) {
            const pads = (dataset || {}).pads || {};
            const ox = (pads.OXIDOS || {}).max_age || 0;
            const su = (pads.SULFUROS || {}).max_age || 0;
            return [Math.max(1, ox), ox, Math.max(1, su), su];
        }""",
        Output('curvas-todas-rec-ox-age', 'max'), Output('curvas-todas-rec-ox-age', 'value'),
        Output('curvas-todas-rec-su-age', 'max'), Output('curvas-todas-rec-su-age', 'value'),
        Input('curvas-todas-rec-dataset', 'data'))

    for label, prefix in [('OXIDOS', 'ox'), ('SULFUROS', 'su')]:
        # Identity guards also run locally when the selected Case changes.
        js = """function(dataset, age, caseId, store) {
            const empty = {data: [], layout: {}};
            const ident = (dataset || {}).identity;
            if (!ident || !store || String(ident[0]) !== String(caseId)
                || String(ident[0]) !== String(store.caso_id)
                || String(ident[1]) !== String(store.caso_run_id)
                || ident[2] !== store.raw_token
                || ident[3] !== String(store.week_start).slice(0,10)
                || ident[4] !== String(store.week_end).slice(0,10)) return empty;
            const pad = dataset.pads['__PAD__'];
            if (!pad) return empty;
            const upper = age == null ? pad.max_age : Math.max(0, Number(age));
            return {data: pad.figure.data.filter(t => t.meta.age_days <= upper),
                    layout: Object.assign({}, pad.figure.layout)};
        }""".replace('__PAD__', label)
        app.clientside_callback(js, Output(f'curvas-todas-rec-{prefix}-chart', 'figure'),
            Input('curvas-todas-rec-dataset', 'data'),
            Input(f'curvas-todas-rec-{prefix}-age', 'value'),
            Input('curvas-recon-caso', 'value'), Input('curvas-recon-store', 'data'))


def _deserialize_dataset(dataset):
    return {'identity': dataset.get('identity'), 'case_end': pd.Timestamp(dataset['case_end']),
            'groups': {label: [{**item, 'start': pd.Timestamp(item['start']),
                'xs': [pd.Timestamp(x) for x in item['xs']]} for item in items]
                for label, items in dataset.get('groups', {}).items()}}
