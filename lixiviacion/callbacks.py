"""Callbacks de presentación. NULL permanece ausente, nunca se recalcula V2."""
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
import re
from decimal import Decimal
import logging
from math import ceil
from dash import Input, Output, State, callback, ctx, html, dcc
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from . import db
from .map_states import FASES, ESTADOS, CALIDAD, fase_visual, actividad

log = logging.getLogger(__name__)
PADS = {1: 'Óxidos', 2: 'Sulfuros'}
COLORS = {1: '#1F4E78', 2: '#1E6B3A'}


def filters(start, end, pad, campaign, parcel, state):
    return dict(desde=start, hasta=end, pad=pad, campana=campaign, parcela=parcel, estado=state)


def number(value, precision=3):
    return 'Sin dato' if value is None else f'{value:,.{precision}f}'.translate(str.maketrans(',.', '.,'))


def serial(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    if isinstance(value, Decimal):
        return float(value)
    return value


def figure(title, unit):
    fig = go.Figure()
    fig.update_layout(title=title, template='plotly_white', height=340, separators=',.',
                      margin=dict(l=60, r=20, t=55, b=45), hovermode='x unified',
                      xaxis_title='Fecha', yaxis_title=unit,
                      legend=dict(orientation='h', y=-0.3), xaxis=dict(tickformat='%d-%m-%Y'))
    return fig


def figures(rows, single_parcel=False):
    flow = figure('Flujo diario', 'Flujo [m³/d]')
    chemistry = figure('Cu drenaje vs refino · promedio por fecha/PAD', 'Cu [g/L]')
    transfer = figure('Transferencia diaria de Cu', 'Transferencia [t Cu/d]')
    for pad in sorted({r['pad_id'] for r in rows}):
        subset = [r for r in rows if r['pad_id'] == pad]
        x = [serial(r['fecha']) for r in subset]
        flow.add_trace(go.Scatter(x=x, y=[serial(r['flujo']) for r in subset],
                                 name=PADS.get(pad, str(pad)), line_color=COLORS.get(pad), connectgaps=False))
        qualifier = '' if single_parcel else ' promedio'
        for col, name, dash in [('drenaje', f'Cu drenaje{qualifier} [g/L]', 'solid'), ('refino', f'Cu refino{qualifier} [g/L]', 'dash')]:
            chemistry.add_trace(go.Scatter(x=x, y=[serial(r[col]) for r in subset],
                name=f'{PADS.get(pad, pad)} · {name}', connectgaps=False,
                line=dict(color=COLORS.get(pad), dash=dash)))
    daily = defaultdict(list)
    for r in rows:
        daily[serial(r['fecha'])].append(r['transferencia'])
    dates = sorted(daily)
    # Agregación visual: SUM ignora NULL, pero un día completamente NULL sigue NULL.
    y = []
    for day in dates:
        values = [v for v in daily[day] if v is not None]
        y.append(serial(sum(values)) if values else None)
    transfer.add_trace(go.Bar(x=dates, y=y, name='Transferencia Cu', marker_color='#1F4E78'))
    return flow, chemistry, transfer


def alert(exc):
    if isinstance(exc, ValueError):
        return dbc.Alert(str(exc), color='warning')
    log.exception('Consulta de lixiviación fallida')
    return dbc.Alert('No fue posible consultar Lixiviación. Revise la conexión y disponibilidad de V2.', color='danger')


@callback(Output('lix-campana', 'options'), Output('lix-campana', 'value'),
          Output('lix-parcela', 'options'), Output('lix-parcela', 'value'), Output('lix-opciones-error', 'children'),
          Input('subtabs-lixiviacion', 'style'), Input('lix-fechas', 'start_date'), Input('lix-fechas', 'end_date'),
          Input('lix-pad', 'value'), Input('lix-estado', 'value'), Input('lix-campana', 'value'), Input('lix-parcela', 'value'),
          Input('lix-tabs', 'active_tab'))
def options(style, start, end, pad, state, campaign, parcel, tab):
    if tab != 'lix-diagnostic-tab' or not style or style.get('display') == 'none':
        raise PreventUpdate
    try:
        f = filters(start, end, pad, campaign, parcel, state)
        db.where(f)
        campaigns, parcels = db.options(f)
        cs = [{'label': f"{PADS.get(r['pad_id'], r['pad_id'])} · Campaña {r['numero_campana']}",
               'value': r['campana_id']} for r in campaigns]
        ps = [{'label': f"{PADS.get(r['pad_id'], r['pad_id'])} · P{r['nro_parcela_pad']}",
               'value': r['parcela_id']} for r in parcels]
        return cs, campaign if campaign in [r['value'] for r in cs] else None, ps, parcel if parcel in [r['value'] for r in ps] else None, None
    except Exception as exc:
        return [], None, [], None, alert(exc)


@callback(*[Output(i, 'children') for i in ['lix-kpi-flujo', 'lix-kpi-cu', 'lix-kpi-delta', 'lix-kpi-fuera']],
          Output('lix-flujo', 'figure'), Output('lix-quimica', 'figure'), Output('lix-transferencia', 'figure'),
          Output('lix-aplicado', 'data'), Output('lix-error', 'children'), Output('lix-resumen', 'children'),
          Input('lix-consultar', 'n_clicks'), State('lix-fechas', 'start_date'), State('lix-fechas', 'end_date'),
          State('lix-pad', 'value'), State('lix-campana', 'value'), State('lix-parcela', 'value'),
          State('lix-estado', 'value'), prevent_initial_call=True)
def load(clicks, start, end, pad, campaign, parcel, state):
    try:
        f = filters(start, end, pad, campaign, parcel, state)
        totals, rows = db.overview(f)
        charts = figures(rows, single_parcel=parcel is not None)
        if parcel is not None:
            charts[1].update_layout(title='Cu drenaje vs refino · parcela seleccionada')
        message = dbc.Alert('No hay registros para los filtros seleccionados.', color='info') if not totals['registros'] else None
        return (number(totals['flujo']), number(totals['transferencia']), number(totals['delta']),
                number(totals['fuera'], 0), *charts, f, message,
                f"Consulta aplicada: {start} → {end} · {totals['registros']} registros. Cambie filtros y pulse Consultar.")
    except Exception as exc:
        return ('—', '—', '—', '—', *figures([]), None, alert(exc), '')


@callback(Output('lix-tabla', 'data'), Output('lix-tabla', 'page_count'), Output('lix-tabla', 'page_current'),
          Output('lix-tabla-error', 'children'), Output('lix-tabla-total', 'children'),
          Input('lix-aplicado', 'data'), Input('lix-tabla', 'page_current'), Input('lix-tabla', 'sort_by'),
          Input('lix-tabla', 'filter_query'), prevent_initial_call=True)
def table(applied, page, order, query):
    if not applied:
        return [], 0, 0, None, ''
    try:
        page = 0 if ctx.triggered_id in ('lix-aplicado',) or ctx.triggered_prop_ids.get('lix-tabla.filter_query') else page
        rows, total, page = db.detail(applied, page or 0, 25, order, query)
        return [{k: db.HYDRAULIC_LABELS.get(v, v) if k == 'estado' else serial(v)
                 for k, v in r.items()} for r in rows], ceil(total/25), page, None, f'{total} filas · 25 por página'
    except Exception as exc:
        return [], 0, 0, alert(exc), ''


@callback(Output('lix-label-kpi-delta', 'children'), Input('lix-aplicado', 'data'))
def delta_label(applied):
    return 'ΔCu promedio [g/L]' if applied and applied.get('parcela') is not None else 'ΔCu promedio parcelas [g/L]'


@lru_cache(maxsize=1)
def operational_colors():
    # La paleta tiene una única fuente: CSS existente del mapa. No se modifica ni duplica.
    css = (Path(__file__).resolve().parent.parent/'assets'/'lixiviacion_map.css').read_text(encoding='utf-8')
    colors = dict(re.findall(r'\.lix-operational \.(\w+)\s*\{\s*--lix-state:\s*(#[0-9a-fA-F]{6})', css))
    return {phase: colors[style] for phase, (_, style) in FASES.items()}


def operational_timeline(rows, applied):
    fig = go.Figure()
    palette = operational_colors()
    for phase, (label, _) in FASES.items():
        subset = [r for r in rows if fase_visual(r['estado_operacional']) == phase]
        if not subset:
            continue
        custom = [[r['fecha'].strftime('%d-%m-%Y'), ESTADOS[r['estado_operacional']][1], label,
                   str(r['numero_campana']) if r['numero_campana'] is not None else 'Sin dato',
                   actividad(r['tiene_dato_riego'],r['riego_activo']),
                   actividad(r['tiene_dato_drenaje'],r['drenaje_activo']),
                   CALIDAD.get(r['calidad_estado'],'Sin dato')] for r in subset]
        fig.add_trace(go.Bar(name=label, orientation='h', y=['Estado operacional']*len(subset),
            base=[r['fecha'].isoformat() for r in subset], x=[86400000]*len(subset),
            width=0.55, marker_color=palette[phase], customdata=custom,
            hovertemplate='Fecha: %{customdata[0]}<br>Estado operacional: %{customdata[1]}<br>'
            'Fase visual: %{customdata[2]}<br>Campaña operacional: %{customdata[3]}<br>'
            'Riego activo: %{customdata[4]}<br>Drenaje activo: %{customdata[5]}<br>'
            'Calidad: %{customdata[6]}<extra></extra>'))
    fig.update_layout(template='plotly_white', height=220,
        barmode='overlay', margin=dict(l=20,r=20,t=15,b=70),
        xaxis=dict(type='date',tickformat='%d-%m-%Y',range=[applied['desde'],
            (date.fromisoformat(applied['hasta'][:10])+timedelta(days=1)).isoformat()]),
        yaxis=dict(type='category',showticklabels=False),legend=dict(orientation='h',y=-0.3))
    return fig


def operational_header(row, end):
    when = date.fromisoformat(end[:10]).strftime('%d-%m-%Y')
    phase = fase_visual(row['estado_operacional'])
    fields = [('Fase operacional',FASES[phase][0]),('Condición actual',ESTADOS[row['estado_operacional']][1])] if phase == 'CICLO_HIDRAULICO' else [('Estado operacional',ESTADOS[row['estado_operacional']][1])]
    fields += [('Campaña operacional',row['numero_campana']),
               ('Calidad',CALIDAD.get(row['calidad_estado'],'Sin dato')),
               ('Asignación hidráulica',db.HYDRAULIC_LABELS.get(row['estado_asignacion'],'Sin dato')),
               ('Campaña hidráulica',row['numero_campana_hidraulica']),
               ('Riego al '+when,actividad(row['tiene_dato_riego'],row['riego_activo'])),
               ('Drenaje al '+when,actividad(row['tiene_dato_drenaje'],row['drenaje_activo']))]
    return dbc.Card(dbc.CardBody([
        html.H5('Estado operacional al '+when),
        html.Small(f"{PADS.get(row['pad_id'],row['pad_id'])} · P{row['numero_parcela']}",className='text-muted'),
        dbc.Row([dbc.Col([html.Div(label,className='small text-muted'),
                          html.Div('Sin dato' if value is None else str(value),className='fw-semibold')],
                         xs=12,sm=6,lg=3,className='mt-2') for label,value in fields]),
        html.Small('Drenaje es un indicador operacional basado en Cu positivo, no un caudal. '
                   'Fuera de ventana hidráulica no implica inactividad.',className='text-muted d-block mt-3')
    ]),className='mb-3')


@callback(Output('lix-operacional','children'), Input('lix-aplicado','data'))
def load_operational(applied):
    if not applied or applied.get('parcela') is None:
        return html.P('Seleccione una parcela para visualizar su estado operacional y evolución.',className='text-muted')
    try:
        header, rows = db.operational(applied)
        content = [operational_header(header,applied['hasta'])] if header else []
        content.append(dbc.Card(dbc.CardBody([
            html.H5('Evolución del estado operacional'),
            dcc.Graph(id='lix-timeline',figure=operational_timeline(rows,applied),
                config={'displaylogo':False,'scrollZoom':False})])) if rows else
            html.P('Sin información operacional para el período seleccionado.',className='text-muted'))
        return content
    except Exception as exc:
        log.warning('Estado operacional no disponible (%s)',type(exc).__name__)
        return dbc.Alert('No fue posible cargar el estado operacional.',color='light')
