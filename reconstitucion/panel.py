"""Sección SIIR. Montaje/import seguro; SQL únicamente al pulsar Cargar datos."""
from threading import RLock
from uuid import uuid4
from io import BytesIO
import base64

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, dcc, html, no_update

from . import engine as e, db_source as dbs, validacion as val, informe_modulos as im, movi_detalle as mov, detalle_reconstituido as det
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
    """Reconstituted intervals, split for click detail, with shift measurement cuts."""
    fig=go.Figure()
    pieces=_itinerary_frame(res)
    if pieces.empty:
        fig.update_layout(title='Sin horario disponible para esta seleccion')
        return fig
    pieces=pieces.loc[pieces.start.notna() & pieces.end.notna()].copy()
    pieces=pieces.loc[pieces.end.gt(pieces.start)]
    if pieces.empty:
        fig.update_layout(title='Sin horario disponible para esta seleccion')
        return fig
    def lane(pad,camp,mod):return f'P{int(pad)} / C{int(camp)} / M{int(mod)}'
    keys=pieces[['pad_id','campana','modulo']].drop_duplicates().sort_values(['pad_id','campana','modulo'])
    rows=[lane(r.pad_id,r.campana,r.modulo) for r in keys.itertuples()]
    categories=rows[::-1]
    bars={'x':[],'base':[],'y':[],'customdata':[]}
    cuts=set();limits=[]
    for seg in pieces.itertuples():
        start,end=pd.Timestamp(seg.start),pd.Timestamp(seg.end)
        label=lane(seg.pad_id,seg.campana,seg.modulo)
        bars['x'].append((end-start).total_seconds()*1000)
        bars['base'].append(start.isoformat());bars['y'].append(label)
        bars['customdata'].append([int(seg.pad_id),int(seg.campana),int(seg.modulo),seg.id,
            pd.Timestamp(seg.fecha).strftime('%Y-%m-%d'),seg.turno,timestamp_text(start),timestamp_text(end)])
        limits.extend([start,end])
        for day in pd.date_range((start-pd.Timedelta(hours=8)).normalize(),end.normalize(),freq='D'):
            for hour in (8,20):
                cut=day+pd.Timedelta(hours=hour)
                if start<=cut<=end:cuts.add((label,cut.isoformat()))
    fig.add_trace(go.Bar(**bars,name='Reconstituido',orientation='h',width=.65,
        marker_color=C['shift2'],hovertemplate='P%{customdata[0]} / C%{customdata[1]} / M%{customdata[2]}'
        '<br>Fecha operacional %{customdata[4]} / %{customdata[5]}'
        '<br>%{customdata[6]} a %{customdata[7]}'
        '<extra>Click: detalle del modulo y turno</extra>'))
    for i,(label,cut) in enumerate(sorted(cuts)):
        y=categories.index(label)
        fig.add_shape(type='line',xref='x',yref='y',x0=cut,x1=cut,y0=y-.29,y1=y+.29,
            line=dict(color=C['accent'],width=2,dash='dot'),
            name='Medicion / cambio de turno (08:00 y 20:00)',showlegend=i==0,legendgroup='turnos')
    fig.update_layout(template='plotly_white',paper_bgcolor=C['panel'],plot_bgcolor=C['panel'],
        font=dict(family=SANS,color=C['text'],size=12),barmode='overlay',bargap=.28,
        height=max(310,len(rows)*38+115),margin=dict(l=165,r=20,t=65,b=45),
        title='Reconstitucion por modulo y cambios de turno',
        legend=dict(orientation='h',y=1.12),clickmode='event+select',
        yaxis=dict(type='category',categoryorder='array',categoryarray=categories,showgrid=False),
        xaxis=dict(type='date',tickformat='%d-%m',gridcolor=C['grid']),
        uirevision='reconstitucion-itinerario')
    fig.update_xaxes(range=[min(limits).isoformat(),max(limits).isoformat()])
    return fig



def select_result(res, key, f0, f1):
    cache_key=(str(key or 'all'), pd.Timestamp(f0).normalize().isoformat(), pd.Timestamp(f1).normalize().isoformat())
    with _lock:
        cached=res.get('_view_cache', {}).get(cache_key)
    if cached is not None:
        return cached
    # Keep the memo outside the derived view to avoid circular references.
    clean={k:v for k,v in res.items() if k not in ('_view_cache','_movement_cache','_movement_quality_cache','_informe_modulos_por_pad','_informe_xlsx_por_pad','_informe_calidad_por_pad')}
    cropped = e.recortar_rango(clean, f0, f1)
    timeline = cropped.get('module_timeline')
    bits = [] if not key or key == 'all' else [int(x) for x in key.split('|')]
    if len(bits) == 1:
        # A PAD tab aggregates every campaign and module for that physical pad.
        pad = bits[0]
        out = dict(cropped)
        out['shift_table'] = out['shift_table'].loc[out['shift_table'].pad_id.eq(pad)].copy()
        timeline = timeline.loc[timeline.pad_id.eq(pad)] if timeline is not None else None
        out.update(daily=e.daily_shift_summary(out['shift_table']),
                   modules=e.module_summary(out['shift_table']),
                   weekly=e.weekly_summary(out['shift_table']), itinerario=timeline)
        out['avisos'] = out.get('avisos_entrada', []) + val.revisar_resultado(out)
    elif bits:
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
    with _lock:
        cache=res.setdefault('_view_cache', {})
        if len(cache)>=32:
            cache.pop(next(iter(cache)))
        out['_full_shift_table']=res.get('_full_shift_table',res['shift_table'])
        cache[cache_key]=out
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
        html.P('Barras azules: horario reconstituido. Lineas punteadas: cortes de medicion y cambios de turno (08:00 y 20:00). Haz click en una barra o fila para ver el detalle del modulo y turno.', className='reconstitucion-note'),
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


def build_layout():
    return html.Div([
        dcc.Store(id='reconstitucion-token', storage_type='memory'),
        dcc.Store(id='reconstitucion-casos', storage_type='memory'),
        dcc.Interval(id='reconstitucion-iniciar-casos', interval=50, n_intervals=0, max_intervals=1),
        html.P('Reconstitución de Módulos', className='reconstitucion-title'),
        html.Div([
            dcc.Dropdown(id='reconstitucion-caso', options=[], placeholder='Cargando casos oficiales...', clearable=False),
            html.Button('Cargar datos', id='reconstitucion-cargar', n_clicks=0, className='reconstitucion-button')], className='reconstitucion-controls reconstitucion-controls-caso'),
        html.Div(id='reconstitucion-estado-casos', className='reconstitucion-note'),
        html.Div(id='reconstitucion-estado', children='Selecciona un Caso y carga su reconstitución.'),
        dcc.Tabs(id='reconstitucion-pad-tabs', value='2', children=[
            dcc.Tab(label='\u00d3xidos', value='1'), dcc.Tab(label='Sulfuros', value='2')],
            colors={'border': C['border'], 'primary': C['accent'], 'background': C['panel']}, className='reconstitucion-pad-tabs'),
        html.Div([
            html.Button('Descargar informe de modulos (XLSX)',
                id='reconstitucion-informe-descargar', n_clicks=0, disabled=True,
                className='reconstitucion-button'),
            dcc.Download(id='reconstitucion-informe-download'),
            html.Span(id='reconstitucion-informe-estado'),
        ], className='reconstitucion-controls reconstitucion-controls-informe'),
        dcc.Loading(html.Div(id='reconstitucion-resultados'), type='circle', color=C['accent'])], className='reconstitucion-shell')


def _resolve_loader(loader=None):
    if loader is not None:
        return loader
    return lambda **kwargs: e.analyze_db(use_intraday=True, **kwargs)


def register_callbacks(app, loader=None, case_loader=None, report_quality_loader=None, movement_loader=None, report_extra_loader=None):
    """Registro idempotente; loader inyectable para pruebas y vista offline."""
    if getattr(app, '_reconstitucion_registered', False):
        return
    app._reconstitucion_registered = True
    load = _resolve_loader(loader)
    quality_loader = report_quality_loader or im.calidad_turno
    extra_loader = report_extra_loader or im.cargar_campos_extra
    movement_source = movement_loader or mov.load_movimientos

    @app.callback(Output('reconstitucion-casos', 'data'), Output('reconstitucion-caso', 'options'),
        Output('reconstitucion-caso', 'value'), Output('reconstitucion-estado-casos', 'children'),
        Input('reconstitucion-iniciar-casos', 'n_intervals'),
        State('reconstitucion-caso', 'value'), prevent_initial_call=True)
    def cargar_catalogo(n, selected=None):
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
            return cases, options, (selected if any(c['id']==selected for c in cases) else cases[0]['id'] if cases else None), (
                'Casos oficiales cargados.' if cases else 'No hay Casos oficiales disponibles.')
        except Exception:
            return None, [], None, 'No se pudieron cargar los Casos. Vuelve a abrir la seccion para reintentar.'

    def caso_actual(cases, case_id):
        return next((c for c in (cases or []) if c['id'] == case_id), None)

    @app.callback(Output('reconstitucion-token', 'data'), Output('reconstitucion-estado', 'children'),
        Input('reconstitucion-cargar', 'n_clicks'), State('reconstitucion-caso', 'value'),
        State('reconstitucion-casos', 'data'), prevent_initial_call=True,
        running=[(Output('reconstitucion-cargar', 'disabled'), True, False),
                 (Output('reconstitucion-cargar', 'children'), 'Calculando…', 'Cargar datos')])
    def cargar(n, case_id, cases):
        if not n:
            return (no_update,) * 2
        case = caso_actual(cases, case_id)
        if case is None:
            return None, 'Selecciona un Caso oficial antes de cargar.'
        try:
            kwargs = dict(fecha_min=case['fecha_inicio'], fecha_max=case['fecha_fin'], caso_id=case_id)
            if case.get('modelo_codigo'):
                kwargs['caso'] = dict(case)
            res = load(**kwargs)
            mass = res.get('masa')
            if mass is None or mass.empty or not mass['caso_id'].eq(case_id).all():
                return None, 'El Caso no tiene masa publicada validada disponible. No se usan datos de otros Casos.'
            # Identidad guardada junto al resultado: una respuesta tardía de otro
            # Caso nunca se presenta como la selección actual.
            res = dict(res, caso=dict(case))
            return remember(res), 'Carga finalizada. Los resultados identifican el Caso asociado.'
        except FlowCaseError as exc:
            return None, str(exc)
        except e.MissingCaseMassError:
            return None, 'El Caso no tiene masa publicada validada disponible. No se usan datos de otros Casos.'
        except Exception:
            return None, 'No se pudo cargar el Caso. Verifica conexión y datos del Caso; puedes reintentar.'

    def resultado_actual(token, case_id, cases):
        with _lock:
            res = _results.get(token)
        case = caso_actual(cases, case_id)
        return res if res is not None and case is not None and res.get('caso') == case else None

    @app.callback(Output('reconstitucion-informe-descargar', 'disabled'),
        Input('reconstitucion-token', 'data'), Input('reconstitucion-caso', 'value'),
        Input('reconstitucion-casos', 'data'))
    def estado_informe(token, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        return res is None or not bool(res.get('fuente_modelo'))

    @app.callback(Output('reconstitucion-informe-download', 'data'),
        Output('reconstitucion-informe-estado', 'children'),
        Input('reconstitucion-informe-descargar', 'n_clicks'),
        State('reconstitucion-token', 'data'), State('reconstitucion-pad-tabs', 'value'),
        State('reconstitucion-caso', 'value'), State('reconstitucion-casos', 'data'),
        prevent_initial_call=True,
        running=[(Output('reconstitucion-informe-descargar', 'children'),
                  'Generando informe...', 'Descargar informe de modulos (XLSX)'),
                 (Output('reconstitucion-informe-descargar', 'disabled'), True, False)])
    def descargar_informe(n, token, pad, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        try:
            pad = int(pad)
        except (TypeError, ValueError):
            pad = None
        if not n or res is None or not res.get('fuente_modelo') or pad not in dbs.PADS:
            return None, 'Carga el Caso seleccionado antes de descargar.'
        case = res['caso']
        try:
            with _lock:
                workbook = res.get('_informe_xlsx_por_pad', {}).get(pad)
                frame = res.get('_informe_modulos_por_pad', {}).get(pad)
            if frame is None:
                workbook = None
            if workbook is None and frame is None:
                has_modules = res['apilado']['pad_id'].eq(pad).any()
                quality = (quality_loader(pad, engine=dbs.get_engine(),
                    fecha_min=case['fecha_inicio'], fecha_max=case['fecha_fin'])
                    if has_modules else pd.DataFrame())
                res.setdefault('_informe_calidad_por_pad', {})[pad] = quality
                extras = extra_loader(res, pad, case, dbs.get_engine())
                frame = im.preparar_modulos_desde_resultado(res, pad, quality,
                    fecha_min=case['fecha_inicio'], fecha_max=case['fecha_fin'],
                    extras=extras)
                warning = bool("advertencias_fuentes" in frame and
                    frame["advertencias_fuentes"].fillna("").astype(str).str.strip().ne("").any())
                if not warning:
                    with _lock:
                        res.setdefault('_informe_modulos_por_pad', {})[pad] = frame
            else:
                warning = bool("advertencias_fuentes" in frame and
                    frame["advertencias_fuentes"].fillna("").astype(str).str.strip().ne("").any())
            if workbook is None:
                output = BytesIO()
                im.exportar_desde_dataframe(frame, output, pad=pad, detalle=True, caso=case)
                workbook = output.getvalue()
                if not warning:
                    with _lock:
                        res.setdefault('_informe_xlsx_por_pad', {})[pad] = workbook
        except Exception:
            return None, 'No se pudo generar el informe. Verifica la conexion de calidad y reintenta.'
        material = 'oxidos' if pad == dbs.PAD_OXIDOS else 'sulfuros'
        filename = f"informe_modulos_{material}_caso_{int(case_id)}_run_{case['run_id']}.xlsx"
        return {'content': base64.b64encode(workbook).decode('ascii'),
            'filename': filename, 'base64': True,
            'type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, (
                (f"Informe listo: {len(frame)} modulos del Caso {int(case_id)}. Hay fuentes sin consultar; ver CASO; reintenta la descarga."
                 if warning else f"Informe listo: {len(frame)} modulos del Caso {int(case_id)}."))

    @app.callback(Output('reconstitucion-resultados', 'children'),
        Input('reconstitucion-token', 'data'), Input('reconstitucion-pad-tabs', 'value'),
        Input('reconstitucion-caso', 'value'),
        Input('reconstitucion-casos', 'data'))
    def resultados(token, pad, case_id, cases):
        res = resultado_actual(token, case_id, cases)
        if res is None:
            return None
        case = res['caso']
        return html.Div([
            html.P(f"Caso #{case_id} · {case['nombre']} · {pd.Timestamp(case['fecha_inicio']):%d-%m-%Y} a "
                   f"{pd.Timestamp(case['fecha_fin']):%d-%m-%Y}.", className='reconstitucion-note'),
            render(select_result(res, str(int(pad)), case['fecha_inicio'], case['fecha_fin']))])

    @app.callback(Output('reconstitucion-tabla-popup', 'children'),
        Output('reconstitucion-tabla-cerrar', 'style'),
        Output('reconstitucion-itinerario', 'active_cell'),
        Output('reconstitucion-gantt', 'clickData'),
        Input('reconstitucion-gantt', 'clickData'), Input('reconstitucion-itinerario', 'active_cell'),
        Input('reconstitucion-tabla-cerrar', 'n_clicks'),
        Input('reconstitucion-token', 'data'), Input('reconstitucion-pad-tabs', 'value'),
        Input('reconstitucion-caso', 'value'), Input('reconstitucion-casos', 'data'),
        prevent_initial_call=True)
    def detalle_fila(click, active_cell, closed, token, pad, case_id, cases):
        from dash import ctx
        try:triggered=ctx.triggered_id
        except Exception:triggered=None
        empty=(None, {'display':'none'}, None, None)
        if triggered in ('reconstitucion-tabla-cerrar','reconstitucion-token','reconstitucion-pad-tabs',
                         'reconstitucion-caso','reconstitucion-casos'):
            return empty
        res=resultado_actual(token,case_id,cases)
        if res is None:return empty
        row_id=None
        if triggered=='reconstitucion-itinerario' or (triggered is None and active_cell):
            row_id=active_cell.get('row_id') if active_cell else None
        elif click and click.get('points'):
            data=click['points'][0].get('customdata')
            if data and len(data)>3:row_id=data[3]
        if not row_id:return empty
        case=res['caso']
        current=select_result(res,str(int(pad)),case['fecha_inicio'],case['fecha_fin'])
        itinerary=_itinerary_frame(current)
        selected=itinerary.loc[itinerary.id.eq(row_id)] if not itinerary.empty else itinerary
        if selected.empty:return empty
        record=det.resolve_itinerary_record(itinerary,row_id,caso_id=case_id)
        if record is None:return empty
        row=selected.iloc[0]
        date=pd.Timestamp(row.fecha).normalize()
        turno=str(row.turno)
        cache_key=(date.isoformat(),turno,'CH01')
        error=None
        try:
            with _lock:cached=res.get('_movement_cache',{}).get(cache_key)
            if cached is None:
                cached=movement_source(dbs.get_engine(),fecha=date,turno=turno)
                with _lock:
                    cache=res.setdefault('_movement_cache',{})
                    if len(cache)>=24:cache.pop(next(iter(cache)))
                    cache[cache_key]=cached
            frame,truncated=cached
        except Exception:
            frame=None;truncated=False
            error='No se pudieron cargar los movimientos del turno. Reintenta la consulta.'
        quality_key=(int(row.pad_id),date.isoformat())
        quality=None
        try:
            with _lock:quality=res.get('_movement_quality_cache',{}).get(quality_key)
            if quality is None:
                quality=quality_loader(int(row.pad_id),engine=dbs.get_engine(),fecha_min=date,fecha_max=date)
                with _lock:
                    cache=res.setdefault('_movement_quality_cache',{})
                    if len(cache)>=24:cache.pop(next(iter(cache)))
                    cache[quality_key]=quality
        except Exception:
            error=(error+' ' if error else '')+'No se pudo consultar el perfil de calidad del turno.'
        fields=det.consolidate_report_fields(res,record,calidad=quality,raw_mov_cam=None if truncated else frame)
        popup=det.render_detail(fields,record,movement_frame=frame,movement_truncated=truncated)
        if error:popup.children[0].children.insert(1,html.P(error))
        close={'display':'block','position':'fixed','zIndex':1101,'top':'6vh','right':'6vw',
               'background':'white','border':'1px solid #ddd','borderRadius':'6px','padding':'8px 12px','cursor':'pointer'}
        return popup,close,no_update,no_update

    @app.callback(Output('reconstitucion-modal', 'style'), Input('reconstitucion-consideraciones', 'n_clicks'),
        Input('reconstitucion-cerrar', 'n_clicks'), prevent_initial_call=True)
    def modal(opened, closed):
        from dash import ctx
        return {'display': 'flex' if ctx.triggered_id == 'reconstitucion-consideraciones' else 'none'}
