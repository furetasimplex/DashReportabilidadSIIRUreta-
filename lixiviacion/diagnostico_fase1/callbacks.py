"""Callbacks de presentación. NULL permanece ausente, nunca se recalcula V2."""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import logging
from math import ceil
from dash import Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from . import db

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
        return [{k: serial(v) for k, v in r.items()} for r in rows], ceil(total/25), page, None, f'{total} filas · 25 por página'
    except Exception as exc:
        return [], 0, 0, alert(exc), ''


@callback(Output('lix-label-kpi-delta', 'children'), Input('lix-aplicado', 'data'))
def delta_label(applied):
    return 'ΔCu promedio [g/L]' if applied and applied.get('parcela') is not None else 'ΔCu promedio parcelas [g/L]'
