"""Sección SIIR. Montaje/import seguro; SQL únicamente al pulsar Cargar datos."""
from threading import RLock
from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

from . import engine as e, db_source as dbs, validacion as val
from .modelo_flujos import FlowCaseError
from .presentacion import C, SANS, MONO, kpi, tabla_itinerario, tabla_detalle_modulo, panel_calidad, gantt_labels

_lock = RLock()
_results = {}  # Tokens por sesión: no serializar el histórico en el navegador.
MAX_SESSIONS = 16


def configure(engine_provider, schema="inventar_SpcHidr.inventar_SpcHidr"):
    dbs.configure(engine_provider, schema)


def remember(res):
    token = uuid4().hex
    with _lock:
        if len(_results) >= MAX_SESSIONS:
            _results.pop(next(iter(_results)))
        _results[token] = res
    return token


def fig_gantt(res):
    """Un gráfico, dos carriles distintos: ventana de levantamiento y estimación.

    Barras de medición NO representan horas efectivas. El eje/identidad incluye
    pad y campaña; los días sin volumen se omiten en el carril medido.
    """
    it = res.get('itinerario')
    fig = go.Figure()
    if it is None or it.empty:
        fig.update_layout(title='Sin módulos para esta selección')
        return fig
    it = it.sort_values(['pad_id', 'campana', 'act_ini', 'modulo']).copy()
    st = res['shift_table']
    activity = {(int(r.pad_id), int(r.campana), int(r.modulo), pd.Timestamp(r.fecha)): r
                for r in st.itertuples()}
    measured = {'x': [], 'base': [], 'y': [], 'customdata': []}
    projected = {'x': [], 'base': [], 'y': [], 'customdata': []}
    rows, limits = [], []
    for r in it.itertuples():
        key = f'P{int(r.pad_id)} · C{int(r.campana)} · M{int(r.modulo)}'
        valid_projection = pd.notna(r.proy_ini) and pd.notna(r.proy_fin)
        rows.append(key + ' | Medido')
        if valid_projection:
            rows.append(key + ' | Proyectado')
        # La presencia diaria se segmenta: no fingir actividad en días vacíos.
        for day in pd.date_range(r.real_ini, r.real_fin, freq='D'):
            if (int(r.pad_id), int(r.campana), int(r.modulo), day) not in activity:
                continue
            start = day + pd.Timedelta(hours=e.SHIFT1_START)
            end = start + pd.Timedelta(days=1)
            measured['x'].append(86400000)
            measured['base'].append(start.isoformat())
            measured['y'].append(key + ' | Medido')
            obs = activity[(int(r.pad_id), int(r.campana), int(r.modulo), day)]
            measured['customdata'].append([int(r.pad_id), int(r.campana), int(r.modulo),
                day.strftime('%d-%m-%Y'), float(obs.vol_diario),
                None if pd.isna(obs.masa_total) else float(obs.masa_total)])
            limits.extend((start, end))
        if valid_projection:
            projected['x'].append((r.proy_fin-r.proy_ini).total_seconds()*1000)
            projected['base'].append(r.proy_ini.isoformat())
            projected['y'].append(key + ' | Proyectado')
            projected['customdata'].append([int(r.pad_id), int(r.campana), int(r.modulo),
                r.proy_ini.strftime('%d-%m %H:%M'), r.proy_fin.strftime('%d-%m %H:%M'),
                float(r.rho_proy)])
            limits.extend((r.proy_ini, r.proy_fin))
    fig.add_trace(go.Bar(**measured, name='Medido · días con volumen', orientation='h',
        marker_color=C['accent'], hovertemplate='Pad %{customdata[0]} · campaña %{customdata[1]} · módulo %{customdata[2]}'
        '<br>Día operacional %{customdata[3]} · 08:00–08:00'
        '<br>Volumen del día %{customdata[4]:,.0f} m³'
        '<br>Masa asignada del día %{customdata[5]:,.0f} t<extra>Ventana de levantamientos; no horas efectivas</extra>'))
    if projected['x']:
        fig.add_trace(go.Bar(**projected, name='Proyectado · estimación', orientation='h',
            marker_color=C['shift2'], hovertemplate='Pad %{customdata[0]} · campaña %{customdata[1]} · módulo %{customdata[2]}'
            '<br>%{customdata[3]} → %{customdata[4]}'
            '<br>Densidad de proyección %{customdata[5]:.3f} t/m³<extra>Estimación, no medición</extra>'))
    fig.update_layout(template='plotly_white', paper_bgcolor=C['panel'], plot_bgcolor=C['panel'],
        font=dict(family=SANS, color=C['text'], size=12), barmode='overlay', bargap=.28,
        height=max(310, len(rows)*25+95), margin=dict(l=160, r=20, t=60, b=40),
        title='Itinerario por pad, campaña y módulo',
        legend=dict(orientation='h', y=1.12), clickmode='event+select',
        yaxis=dict(categoryorder='array', categoryarray=rows[::-1], showgrid=False),
        xaxis=dict(type='date', tickformat='%d-%m', gridcolor=C['grid']),
        uirevision='reconstitucion-itinerario')
    if limits:
        fig.update_xaxes(range=[min(limits).isoformat(), max(limits).isoformat()])
    if not projected['x']:
        fig.add_annotation(text='Proyección no disponible: falta tasa o densidad válida.',
            x=0, y=1.02, xref='paper', yref='paper', showarrow=False,
            xanchor='left', font=dict(color=C['sub'], size=11))
    return fig


def select_result(res, key, mode, f0, f1):
    cropped = e.recortar_rango(res, f0, f1)
    if key and key != 'all':
        pad, camp = (int(x) for x in key.split('|'))
        return e.analyze_group(cropped, pad, camp, proy_modo=mode)
    out = dict(cropped)
    st = out['shift_table']
    out.update(daily=e.daily_shift_summary(st), modules=e.module_summary(st),
        weekly=e.weekly_summary(st), itinerario=e.module_itinerary(out['apilado'], st, mode,
        tasa=out.get('tasa')))
    out['avisos'] = out.get('avisos_entrada', []) + val.revisar_resultado(out)
    return out


def summary(res):
    st = res['shift_table']
    balance = res.get('cuadratura')
    mass = st.masa_total.sum(min_count=1)
    pending = balance.masa_pendiente.sum(min_count=1) if balance is not None else np.nan
    cards = [kpi('Volumen', f'{st.vol_diario.sum():,.0f} m³'),
             kpi('Masa asignada', 'Sin dato' if pd.isna(mass) else f'{mass:,.0f} t'),
             kpi('Módulos', str(len(res.get('itinerario', [])))),
             kpi('Masa pendiente global', 'Sin dato' if pd.isna(pending) else f'{pending:,.0f} t', C['amber'])]
    return html.Div(cards, className='reconstitucion-kpis')


def render(res):
    st = res['shift_table']
    sources = sorted(str(x) for x in st.get('fuente_masa', pd.Series(dtype=str)).dropna().unique())
    if res.get('fuente_modelo'):
        source = res['fuente_modelo']
        flows = '/'.join(res['balance_flujos']['flujo'])
        sources = [f"Caso #{source['id']} - run #{source['run_id']} - {flows}: masa reconciliada"]
    return html.Div([
        summary(res),
        html.P('Fuente de masa: ' + (', '.join(sources) if sources else 'Oficial validada'), className='reconstitucion-note'),
        html.P('Naranja: días operacionales con volumen medido. Azul: itinerario estimado cuando existe evidencia. '
               'Los huecos indican días sin volumen; cada módulo aparece una vez por tipo de dato.', className='reconstitucion-note'),
        dcc.Graph(id='reconstitucion-gantt', figure=fig_gantt(res), config={'displaylogo': False}),
        html.Div(id='reconstitucion-detalle'),
        html.Details([html.Summary('Ver tabla de itinerario'), tabla_itinerario(res)]),
        html.Button('Consideraciones', id='reconstitucion-consideraciones', n_clicks=0, className='reconstitucion-button'),
        html.Div([html.Div([
            html.Button('Cerrar', id='reconstitucion-cerrar', n_clicks=0, className='reconstitucion-button'),
            html.H3('Consideraciones'),
            html.P('La masa conserva el total reconciliado de cada pad. '
                   'Un turno conocido en cero conserva cero. Días sin masa no se rellenan. '
                   'El pendiente global no se atribuye a módulos sin evidencia de volumen. '
                   'Los días medidos delimitan levantamientos, no horas efectivas de operación. '
                   'Las fechas proyectadas requieren tasa y densidad válidas.'),
            html.P((
                'Fuente: flujos solidos del Caso y su run oficial. La distribucion por dia y turno '
                'se deriva del perfil operativo de correas y humedad; no es un nuevo pesaje por turno. '
                'No se mezclan publicaciones de otros Casos. '
                f"Caso #{res['fuente_modelo']['id']} - run #{res['fuente_modelo']['run_id']}."
            ) if res.get('fuente_modelo') else (
                'Fuente historica: publicacion de masa validada del Caso. '
                'Publicaciones: ' + ', '.join(sorted(res['masa'].get('reporte_run_id', pd.Series(dtype=str))
                    .dropna().astype(str).unique())))),
            panel_calidad(res) or html.P('Sin observaciones adicionales.')], className='reconstitucion-dialog')],
            id='reconstitucion-modal', role='dialog', **{'aria-label': 'Consideraciones'},
            className='reconstitucion-modal', style={'display': 'none'})])


def build_layout(start_date=None, end_date=None):
    return html.Div([
        dcc.Store(id='reconstitucion-token', storage_type='memory'),
        dcc.Store(id='reconstitucion-casos', storage_type='memory'),
        html.P('Reconstitución de Módulos', className='reconstitucion-title'),
        html.Div([
            html.Button('Actualizar Casos', id='reconstitucion-actualizar-casos', n_clicks=0, className='reconstitucion-button'),
            dcc.Dropdown(id='reconstitucion-caso', options=[], placeholder='Caso oficial', clearable=False),
            html.Div(id='reconstitucion-estado-casos'),
            dcc.Dropdown(id='reconstitucion-grupo', options=[{'label': 'Todos los módulos', 'value': 'all'}], value='all', clearable=False),
            dcc.Dropdown(id='reconstitucion-modo', options=[{'label': 'Calendario de apilado', 'value': 'apilado'},
                {'label': 'Utilización de calendario', 'value': 'calendario'},
                {'label': 'Calibración por campaña', 'value': 'campana'}], value='apilado', clearable=False),
            dcc.DatePickerRange(id='reconstitucion-rango', start_date=start_date, end_date=end_date, disabled=True,
                                display_format='DD-MM-YYYY', first_day_of_week=1),
            html.Button('Cargar datos', id='reconstitucion-cargar', n_clicks=0, className='reconstitucion-button')], className='reconstitucion-controls'),
        html.Div(id='reconstitucion-estado', children='Actualiza los Casos, selecciona uno y carga su reconstitución.'),
        dcc.Loading(html.Div(id='reconstitucion-resultados'), type='circle', color=C['accent'])], className='reconstitucion-shell')


def register_callbacks(app, loader=None, case_loader=None):
    """Registro idempotente; loader inyectable para pruebas y vista offline."""
    if getattr(app, '_reconstitucion_registered', False):
        return
    app._reconstitucion_registered = True
    load = loader or e.analyze_db

    @app.callback(Output('reconstitucion-casos', 'data'), Output('reconstitucion-caso', 'options'),
        Output('reconstitucion-caso', 'value'), Output('reconstitucion-estado-casos', 'children'),
        Input('reconstitucion-actualizar-casos', 'n_clicks'), prevent_initial_call=True,
        running=[(Output('reconstitucion-actualizar-casos', 'disabled'), True, False)])
    def actualizar_casos(n):
        if not n:
            return (no_update,) * 4
        try:
            if case_loader is None:
                raise RuntimeError('Configurar catálogo oficial')
            cases = [dict(c, fecha_inicio=pd.Timestamp(c['fecha_inicio']).isoformat(),
                          fecha_fin=pd.Timestamp(c['fecha_fin']).isoformat())
                     for c in case_loader() if c.get('run_id')]
            options = [{'label': f"Caso #{c['id']} · {c['nombre']} · "
                        f"{pd.Timestamp(c['fecha_inicio']):%d-%m-%Y} a {pd.Timestamp(c['fecha_fin']):%d-%m-%Y}",
                        'value': c['id']} for c in cases]
            return cases, options, cases[0]['id'] if cases else None, (
                'Casos oficiales actualizados.' if cases else 'No hay Casos oficiales disponibles.')
        except Exception:
            return None, [], None, 'No se pudieron actualizar los Casos. Puedes reintentar.'

    def caso_actual(cases, case_id):
        return next((c for c in (cases or []) if c['id'] == case_id), None)

    @app.callback(Output('reconstitucion-rango', 'start_date'), Output('reconstitucion-rango', 'end_date'),
        Input('reconstitucion-caso', 'value'), Input('reconstitucion-casos', 'data'))
    def ventana(case_id, cases):
        case = caso_actual(cases, case_id)
        return (case['fecha_inicio'], case['fecha_fin']) if case else (None, None)

    @app.callback(Output('reconstitucion-token', 'data'), Output('reconstitucion-grupo', 'options'),
        Output('reconstitucion-grupo', 'value'), Output('reconstitucion-estado', 'children'),
        Input('reconstitucion-cargar', 'n_clicks'), State('reconstitucion-caso', 'value'),
        State('reconstitucion-casos', 'data'), prevent_initial_call=True,
        running=[(Output('reconstitucion-cargar', 'disabled'), True, False),
                 (Output('reconstitucion-cargar', 'children'), 'Calculando…', 'Cargar datos')])
    def cargar(n, case_id, cases):
        if not n:
            return (no_update,) * 4
        case = caso_actual(cases, case_id)
        if case is None:
            return None, [], 'all', 'Selecciona un Caso oficial antes de cargar.'
        try:
            kwargs = dict(fecha_min=case['fecha_inicio'], fecha_max=case['fecha_fin'], caso_id=case_id)
            if case.get('modelo_codigo'):
                kwargs['caso'] = dict(case)
            res = load(**kwargs)
            mass = res.get('masa')
            if mass is None or mass.empty or not mass['caso_id'].eq(case_id).all():
                return None, [], 'all', 'El Caso no tiene masa publicada validada disponible. No se usan datos de otros Casos.'
            # Identidad guardada junto al resultado: una respuesta tardía de otro
            # Caso nunca se presenta como la selección actual.
            res = dict(res, caso=dict(case))
            groups = res['shift_table'][['pad_id', 'campana']].drop_duplicates().sort_values(['pad_id', 'campana'])
            options = [{'label': 'Todos los módulos', 'value': 'all'}] + [
                {'label': f'Pad {int(r.pad_id)} · campaña {int(r.campana)}', 'value': f'{int(r.pad_id)}|{int(r.campana)}'}
                for r in groups.itertuples()]
            return remember(res), options, 'all', 'Carga finalizada. Los resultados identifican el Caso asociado.'
        except FlowCaseError as exc:
            return None, [], 'all', str(exc)
        except e.MissingCaseMassError:
            return None, [], 'all', 'El Caso no tiene masa publicada validada disponible. No se usan datos de otros Casos.'
        except Exception:
            return None, [], 'all', 'No se pudo cargar el Caso. Verifica conexión y datos del Caso; puedes reintentar.'

    def resultado_actual(token, case_id, cases):
        with _lock:
            res = _results.get(token)
        case = caso_actual(cases, case_id)
        return res if res is not None and case is not None and res.get('caso') == case else None

    @app.callback(Output('reconstitucion-resultados', 'children'),
        Input('reconstitucion-token', 'data'), Input('reconstitucion-grupo', 'value'),
        Input('reconstitucion-modo', 'value'), Input('reconstitucion-caso', 'value'),
        Input('reconstitucion-casos', 'data'))
    def resultados(token, group, mode, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        if res is None:
            return html.P('Carga la reconstitución del Caso seleccionado para mostrar el itinerario.')
        case = res['caso']
        return html.Div([
            html.P(f"Caso #{case_id} · {case['nombre']} · {pd.Timestamp(case['fecha_inicio']):%d-%m-%Y} a "
                   f"{pd.Timestamp(case['fecha_fin']):%d-%m-%Y}.", className='reconstitucion-note'),
            render(select_result(res, group, mode, case['fecha_inicio'], case['fecha_fin']))])

    @app.callback(Output('reconstitucion-detalle', 'children'), Input('reconstitucion-gantt', 'clickData'),
        State('reconstitucion-token', 'data'), State('reconstitucion-grupo', 'value'),
        State('reconstitucion-modo', 'value'), State('reconstitucion-caso', 'value'),
        State('reconstitucion-casos', 'data'))
    def detalle(click, token, group, mode, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        if res is None or not click or not click.get('points'):
            return None
        data = click['points'][0].get('customdata')
        if not data:
            return None
        pad, camp, mod = map(int, data[:3])
        case = res['caso']
        current = select_result(res, group, mode, case['fecha_inicio'], case['fecha_fin'])
        it = current['itinerario']
        if it is None or it.empty:
            return None
        d = it[it.pad_id.eq(pad)].sort_values(['pad_id', 'campana', 'act_ini'], ascending=[True, True, False])
        labels = dict(zip(zip(d.campana.astype(int), d.modulo.astype(int)), gantt_labels(d)))
        return tabla_detalle_modulo(current, labels.get((camp, mod)), pad=pad)

    @app.callback(Output('reconstitucion-modal', 'style'), Input('reconstitucion-consideraciones', 'n_clicks'),
        Input('reconstitucion-cerrar', 'n_clicks'), prevent_initial_call=True)
    def modal(opened, closed):
        from dash import ctx
        return {'display': 'flex' if ctx.triggered_id == 'reconstitucion-consideraciones' else 'none'}
