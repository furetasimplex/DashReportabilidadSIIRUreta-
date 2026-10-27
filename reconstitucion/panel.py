"""Sección SIIR. Montaje/import seguro; SQL únicamente al pulsar Cargar datos."""
from threading import RLock
from uuid import uuid4

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

from . import engine as e, db_source as dbs, validacion as val
from .modelo_flujos import FlowCaseError
from .presentacion import C, SANS, MONO, kpi, tabla_itinerario, tabla_detalle_modulo, detalle_itinerario, _itinerary_frame, panel_calidad, gantt_labels, timestamp_text, resolution_label

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


def _optional_number(value):
    return None if pd.isna(value) else float(value)


def fig_gantt(res):
    """Reconstructed blue intervals split at TA/TB, with orange change markers."""
    timeline=res.get('module_timeline')
    fig=go.Figure()
    if timeline is None or timeline.empty:
        fig.update_layout(title='Sin modulos para esta seleccion')
        return fig
    pieces=_itinerary_frame(res)
    bars={'x':[],'base':[],'y':[],'customdata':[]}
    transitions={'x':[],'y':[],'customdata':[]}
    rows=[]; limits=[]
    def lane(pad,camp,mod,turn):
        return f'P{int(pad)} / C{int(camp)} / M{int(mod)}'
    if pieces is not None and not pieces.empty:
        for seg in pieces.itertuples():
            if pd.isna(seg.start) or pd.isna(seg.end) or pd.Timestamp(seg.end)<=pd.Timestamp(seg.start):
                continue
            start,end=pd.Timestamp(seg.start),pd.Timestamp(seg.end)
            y=lane(seg.pad_id,seg.campana,seg.modulo,seg.turno)
            if y not in rows: rows.append(y)
            bars['x'].append((end-start).total_seconds()*1000); bars['base'].append(start.isoformat()); bars['y'].append(y)
            bars['customdata'].append([int(seg.pad_id),int(seg.campana),int(seg.modulo),seg.turno,timestamp_text(start),timestamp_text(end),_optional_number(seg.masa_turno_asignada),str(seg.frontera_tipo) if hasattr(seg,'frontera_tipo') else ''])
            limits.extend((start,end))
    tl=timeline.sort_values(['pad_id','campana','start','modulo']).copy()
    for _,group in tl.groupby(['pad_id','campana'],sort=False):
        items=list(group.itertuples())
        for prev,nxt in zip(items,items[1:]):
            if int(prev.modulo)==int(nxt.modulo):
                continue
            t=pd.Timestamp(nxt.start)
            opday=(t-pd.Timedelta(hours=8)).normalize()
            turn='TA' if t < opday+pd.Timedelta(hours=20) else 'TB'
            y=lane(nxt.pad_id,nxt.campana,nxt.modulo,turn)
            if y not in rows: rows.append(y)
            transitions['x'].append(t.isoformat()); transitions['y'].append(y)
            transitions['customdata'].append([int(nxt.pad_id),int(nxt.campana),int(nxt.modulo),int(prev.modulo),timestamp_text(t),pd.Timestamp(nxt.fecha).strftime('%d-%m-%Y'),str(nxt.origen),str(nxt.resolucion)])
            limits.append(t)
    if bars['x']:
        fig.add_trace(go.Bar(**bars,name='Horario reconstruido',orientation='h',marker_color=C['shift2'],
            hovertemplate='P%{customdata[0]} / C%{customdata[1]} / M%{customdata[2]}<br>Turno %{customdata[3]}<br>Horario %{customdata[4]} a %{customdata[5]}<br>TMS asignada a este turno: %{customdata[6]:,.0f} t<br>Base de turno: %{customdata[7]}<br>Horario reconstruido; la masa humeda y la TMS diaria no se desglosan linealmente por tramo.<extra></extra>',
            hoverlabel=dict(align='left',font=dict(size=10))))
    if transitions['x']:
        fig.add_trace(go.Scatter(x=transitions['x'],y=transitions['y'],mode='markers',name='Medicion asignada al cambio reconstruido',
            marker=dict(symbol='line-ns',size=16,color=C['accent'],line=dict(color=C['accent'],width=3)),customdata=transitions['customdata'],
            hovertemplate='Medicion asignada al cambio reconstruido<br>P%{customdata[0]} / C%{customdata[1]}<br>M%{customdata[3]} -> M%{customdata[2]}<br>Hora reconstruida %{customdata[4]}<br>Fecha original %{customdata[5]}<br>No hay evento de cambio registrado.<br>%{customdata[6]}<br>%{customdata[7]}<extra></extra>',
            hoverlabel=dict(align='left',font=dict(size=10))))
    rows=sorted(rows,key=lambda label:(int(label.split('/')[0].strip()[1:]),int(label.split('/')[1].strip()[1:]),int(label.split('/')[2].split('|')[0].strip()[1:]),0))
    fig.update_layout(template='plotly_white',paper_bgcolor=C['panel'],plot_bgcolor=C['panel'],font=dict(family=SANS,color=C['text'],size=12),barmode='overlay',bargap=.28,height=max(310,len(rows)*25+95),margin=dict(l=190,r=20,t=60,b=55),title='Horario reconstruido por modulo; turnos en eje temporal',legend=dict(orientation='h',y=1.12),clickmode='event+select',yaxis=dict(categoryorder='array',categoryarray=rows[::-1],showgrid=False),xaxis=dict(type='date',gridcolor=C['grid']),uirevision='reconstitucion-itinerario')
    if limits:
        low,high=min(limits),max(limits)
        fig.update_xaxes(range=[low.isoformat(),high.isoformat()])
        ticks=[]; labels=[]
        for day in pd.date_range((low-pd.Timedelta(hours=8)).normalize(),high.normalize(),freq='D'):
            for hour,label in ((8,'TA'),(20,'TB')):
                t=day+pd.Timedelta(hours=hour)
                if low<=t<=high:
                    ticks.append(t.isoformat()); labels.append(f'{label} {hour:02d}:00<br>{t:%d-%m}')
        fig.update_xaxes(tickmode='array',tickvals=ticks,ticktext=labels,tickangle=-25)
    if not bars['x']:
        fig.add_annotation(text='Horario no disponible para los tramos de esta seleccion.',x=0,y=1.02,xref='paper',yref='paper',showarrow=False,xanchor='left',font=dict(color=C['sub'],size=11))
    elif not transitions['x']:
        fig.add_annotation(text='No hay evento de cambio registrado; se muestra el horario reconstruido.',x=0,y=1.02,xref='paper',yref='paper',showarrow=False,xanchor='left',font=dict(color=C['sub'],size=11))
    return fig


def select_result(res, key, f0, f1):
    cropped = e.recortar_rango(res, f0, f1)
    timeline = cropped.get('module_timeline')
    bits = [] if not key or key == 'all' else [int(x) for x in key.split('|')]
    if bits:
        pad, camp = bits[:2]
        out = e.analyze_group(cropped, pad, camp)
        if len(bits) == 3:
            mod = bits[2]
            out['shift_table'] = out['shift_table'].loc[out['shift_table'].modulo.eq(mod)].copy()
            out['itinerario'] = out['itinerario'].loc[out['itinerario'].modulo.eq(mod)].copy()
        timeline = timeline.loc[timeline.pad_id.eq(pad) & timeline.campana.eq(camp)] if timeline is not None else None
        if len(bits) == 3 and timeline is not None:
            timeline = timeline.loc[timeline.modulo.eq(bits[2])]
    else:
        out = dict(cropped)
        st = out['shift_table']
        out.update(daily=e.daily_shift_summary(st), modules=e.module_summary(st), weekly=e.weekly_summary(st), itinerario=timeline)
        out['avisos'] = out.get('avisos_entrada', []) + val.revisar_resultado(out)
    if timeline is not None:
        timeline = timeline.copy()
        timeline['fecha'] = pd.to_datetime(timeline.fecha).dt.normalize()
        timeline = timeline.loc[timeline.fecha.between(pd.Timestamp(f0).normalize(), pd.Timestamp(f1).normalize())]
        out['module_timeline'] = timeline
        out['itinerario'] = timeline
    return out


def summary(res):
    st = res['shift_table']
    balance = res.get('cuadratura')
    mass = st.masa_total.sum(min_count=1)
    pending = balance.masa_pendiente.sum(min_count=1) if balance is not None else np.nan
    timeline = res.get('module_timeline')
    n_modules = (timeline[['pad_id', 'campana', 'modulo']].drop_duplicates().shape[0]
                 if timeline is not None and not timeline.empty else 0)
    cards = [kpi('Volumen', f'{st.vol_diario.sum():,.0f} m³'),
             kpi('Masa asignada', 'Sin dato' if pd.isna(mass) else f'{mass:,.0f} t'),
             kpi('Modulos', str(n_modules)),
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
        html.P('Azul: horario reconstruido desde el perfil TMH y la fraccion de volumen diaria del modulo. Las lineas verticales naranjas son mediciones asignadas al cambio reconstruido; no hay evento de cambio registrado. Selecciona una fila para abrir los datos del modulo y turno disponibles en esta carga. TMS diaria es un unico total y no se replica como TMS por tramo.', className='reconstitucion-note'),
        html.Div(dcc.Graph(id='reconstitucion-gantt', figure=fig_gantt(res), config={'displaylogo': False}, style={'minWidth':'960px'}), style={'overflowX':'auto','maxWidth':'100%'}),
        html.Div(id='reconstitucion-detalle'),
        html.Div(id='reconstitucion-tabla-popup'),
        html.Button('Cerrar detalle de fila', id='reconstitucion-tabla-cerrar', n_clicks=0, style={'display':'none','position':'fixed','zIndex':1101,'top':'12%','right':'16%','background':'white','border':'1px solid #ddd','borderRadius':'6px','padding':'8px 12px','cursor':'pointer'}),
        html.Div([html.P('Selecciona una fila para abrir sus datos de modulo y turno.',className='reconstitucion-note'),tabla_itinerario(res)]),
        html.Button('Consideraciones', id='reconstitucion-consideraciones', n_clicks=0, className='reconstitucion-button'),
        html.Div([html.Div([
            html.Button('Cerrar', id='reconstitucion-cerrar', n_clicks=0, className='reconstitucion-button'),
            html.H3('Consideraciones'),
            html.P('La masa conserva el total reconciliado de cada pad. Un turno conocido en cero conserva cero; dias sin masa no se rellenan. El pendiente global no se atribuye a modulos sin evidencia. Los levantamientos diarios no son horas efectivas. Las horas son estimaciones reconstruidas desde perfil TMH y reparto por fraccion de volumen; la resolucion y el origen usados aparecen en cada intervalo. La hora no es una observacion y el fin no acredita cierre fisico.'),
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
            dcc.DatePickerRange(id='reconstitucion-rango', start_date=start_date, end_date=end_date, disabled=True,
                                display_format='DD-MM-YYYY', first_day_of_week=1),
            html.Button('Cargar datos', id='reconstitucion-cargar', n_clicks=0, className='reconstitucion-button')], className='reconstitucion-controls'),
        html.Div(id='reconstitucion-estado', children='Actualiza los Casos, selecciona uno y carga su reconstitución.'),
        dcc.Loading(html.Div(id='reconstitucion-resultados'), type='circle', color=C['accent'])], className='reconstitucion-shell')


def _resolve_loader(loader=None):
    if loader is not None:
        return loader
    return lambda **kwargs: e.analyze_db(use_intraday=True, **kwargs)


def register_callbacks(app, loader=None, case_loader=None):
    """Registro idempotente; loader inyectable para pruebas y vista offline."""
    if getattr(app, '_reconstitucion_registered', False):
        return
    app._reconstitucion_registered = True
    load = _resolve_loader(loader)

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
            options = [{'label': 'Todos los m\u00f3dulos', 'value': 'all'}] + [
                {'label': f'Pad {int(r.pad_id)} / campana {int(r.campana)} / modulo {int(r.modulo)}', 'value': f'{int(r.pad_id)}|{int(r.campana)}|{int(r.modulo)}'}
                for r in res['shift_table'][['pad_id','campana','modulo']].drop_duplicates().sort_values(['pad_id','campana','modulo']).itertuples()]
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
        Input('reconstitucion-caso', 'value'),
        Input('reconstitucion-casos', 'data'))
    def resultados(token, group, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        if res is None:
            return html.P('Carga la reconstitución del Caso seleccionado para mostrar el itinerario.')
        case = res['caso']
        return html.Div([
            html.P(f"Caso #{case_id} · {case['nombre']} · {pd.Timestamp(case['fecha_inicio']):%d-%m-%Y} a "
                   f"{pd.Timestamp(case['fecha_fin']):%d-%m-%Y}.", className='reconstitucion-note'),
            render(select_result(res, group, case['fecha_inicio'], case['fecha_fin']))])

    # Conserva el detalle del grafico y sus argumentos/guardas existentes.
    @app.callback(Output('reconstitucion-detalle', 'children'), Input('reconstitucion-gantt', 'clickData'),
        State('reconstitucion-token', 'data'), State('reconstitucion-grupo', 'value'),
        State('reconstitucion-caso', 'value'), State('reconstitucion-casos', 'data'))
    def detalle(click, token, group, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        if res is None or not click or not click.get('points'):
            return None
        data = click['points'][0].get('customdata')
        if not data:
            return None
        pad, camp, mod = map(int, data[:3])
        case = res['caso']
        current = select_result(res, group, case['fecha_inicio'], case['fecha_fin'])
        return tabla_detalle_modulo(current, (camp, mod), pad=pad)

    @app.callback(Output('reconstitucion-tabla-popup', 'children'), Output('reconstitucion-tabla-cerrar','style'), Output('reconstitucion-itinerario','active_cell'),
        Input('reconstitucion-itinerario', 'active_cell'), Input('reconstitucion-tabla-cerrar', 'n_clicks'),
        State('reconstitucion-token', 'data'), State('reconstitucion-grupo', 'value'),
        State('reconstitucion-caso', 'value'), State('reconstitucion-casos', 'data'), prevent_initial_call=True)
    def detalle_fila(active_cell, closed, token, group, case_id, cases):
        from dash import ctx
        try:
            triggered_id=ctx.triggered_id
        except Exception:
            triggered_id=None
        if triggered_id == 'reconstitucion-tabla-cerrar':
            return None, {'display':'none'}, None
        res = resultado_actual(token, case_id, cases)
        row_id = active_cell.get('row_id') if active_cell else None
        if res is None or not row_id:
            return None, {'display':'none'}, None
        case = res['caso']
        current = select_result(res, group, case['fecha_inicio'], case['fecha_fin'])
        # La clave indexa filas recreadas desde el resultado server-side; no se acepta row_data.
        detail=detalle_itinerario(current, row_id)
        style={'display':'block','position':'fixed','zIndex':1101,'top':'12%','right':'16%','background':'white','border':'1px solid #ddd','borderRadius':'6px','padding':'8px 12px','cursor':'pointer'} if detail else {'display':'none'}
        return detail, style, no_update

    @app.callback(Output('reconstitucion-modal', 'style'), Input('reconstitucion-consideraciones', 'n_clicks'),
        Input('reconstitucion-cerrar', 'n_clicks'), prevent_initial_call=True)
    def modal(opened, closed):
        from dash import ctx
        return {'display': 'flex' if ctx.triggered_id == 'reconstitucion-consideraciones' else 'none'}
