"""Sección SIIR solo de reportes: curvas reconciliadas + reconstitución de módulos.

Une en una pestaña aparte la generación de los dos informes que hoy viven en
«Curvas y reconciliación» y «Reconstitución de Módulos», sin gráficos ni
exploración. Para un mismo Caso oficial entrega:

* ``Reporte_Recuperaciones_Metodo_Reconciliado`` (curvas): por defecto desde la
  última corrida reconciliada guardada en este servidor, sin recalcular ni
  escribir en SQL. «Reconciliar ahora» ejecuta el mismo cálculo de la pestaña
  de curvas, que sí guarda la corrida.
* Informe de módulos de Óxidos y/o Sulfuros (reconstitución), solo lectura.

Si se pide más de un informe se descarga un ZIP con un ``LEEME.txt`` que
identifica Caso, run, ventana y el estado de cada informe. El montaje no
consulta SQL: el catálogo de Casos se pide al abrir la sección.
"""
from datetime import datetime
from io import BytesIO
from threading import RLock
import base64
import zipfile

import pandas as pd
from dash import Input, Output, State, dcc, html, no_update

PREFIX = 'reportes-recon'
REPORTES = [
    ('curvas', 'Recuperaciones reconciliadas por pila (curvas)'),
    ('recon-1', 'Informe de módulos · Óxidos (reconstitución)'),
    ('recon-2', 'Informe de módulos · Sulfuros (reconstitución)'),
]
ZIP_MIME = 'application/zip'

_lock = RLock()
_recon_cache = {}  # (caso_id, run_id) -> resultado de reconstitución
MAX_CACHE = 4


def _id(name):
    return f'{PREFIX}-{name}'


def _host_casos():
    from curvas_recon.db_pipeline import load_casos
    return load_casos()


def layout():
    return html.Div([
        dcc.Store(id=_id('casos'), storage_type='memory'),
        dcc.Interval(id=_id('iniciar'), interval=50, n_intervals=0, max_intervals=1),
        html.P('Reportes de reconciliación', className='reportes-recon-title'),
        html.P('Genera en un solo paso los informes de reconciliación de curvas y de '
               'reconstitución de módulos de un Caso oficial. Esta sección no muestra '
               'gráficos: para revisarlos usa Curvas y reconciliación o Reconstitución de Módulos.',
               className='reportes-recon-note'),
        html.Div([
            html.Label('Caso oficial', htmlFor=_id('caso'), className='reportes-recon-label'),
            dcc.Dropdown(id=_id('caso'), options=[], placeholder='Cargando casos oficiales...',
                         clearable=False),
            html.Div(id=_id('estado-casos'), className='reportes-recon-note'),
        ], className='reportes-recon-card'),
        html.Div([
            html.Label('Informes', className='reportes-recon-label'),
            dcc.Checklist(id=_id('seleccion'), value=[key for key, _ in REPORTES],
                          options=[{'label': label, 'value': key} for key, label in REPORTES],
                          className='reportes-recon-checklist',
                          inputClassName='reportes-recon-check'),
        ], className='reportes-recon-card'),
        html.Div([
            html.Label('Origen de la reconciliación de curvas', className='reportes-recon-label'),
            dcc.RadioItems(id=_id('modo-curvas'), value='ultima', options=[
                {'label': 'Última corrida del Caso guardada en este servidor (no recalcula ni escribe en SQL)',
                 'value': 'ultima'},
                {'label': 'Reconciliar ahora (ejecuta el cálculo y guarda la corrida en SIIR)',
                 'value': 'calcular'},
            ], className='reportes-recon-radio', inputClassName='reportes-recon-check'),
            html.Div([
                html.Label('Metodología Sulfuros', htmlFor=_id('sulfuros'),
                           className='reportes-recon-label'),
                dcc.Dropdown(id=_id('sulfuros'), value='net_trial', clearable=False, options=[
                    {'label': 'Menores de 30 días: ensayo neto local', 'value': 'net_trial'},
                    {'label': 'Método anterior (guarda en SQL al calcular)', 'value': 'legacy'}]),
            ], id=_id('sulfuros-wrap'), style={'display': 'none'}),
            html.P('El reporte de curvas exporta las pilas individuales; las sumas de curvas '
                   '(pilas virtuales) se exportan desde Curvas y reconciliación.',
                   className='reportes-recon-note'),
        ], className='reportes-recon-card'),
        html.Div([
            html.Button('Generar reportes', id=_id('generar'), n_clicks=0,
                        className='reportes-recon-button'),
            dcc.Download(id=_id('download')),
        ], className='reportes-recon-actions'),
        dcc.Loading(html.Div(id=_id('estado')), type='circle', color='#E86D1F'),
    ], className='reportes-recon-shell')


def _caso(cases, case_id):
    return next((c for c in (cases or []) if c.get('id') == case_id), None)


def _resultado_reconstitucion(case, loader=None):
    """Carga la reconstitución del Caso una vez por worker y run oficial."""
    from reconstitucion import panel as recon_panel
    key = (case['id'], case.get('run_id'))
    with _lock:
        cached = _recon_cache.get(key)
    if cached is not None:
        return cached
    res = recon_panel.cargar_resultado_caso(case, loader)
    with _lock:
        if len(_recon_cache) >= MAX_CACHE:
            _recon_cache.pop(next(iter(_recon_cache)))
        _recon_cache[key] = res
    return res


def _download_bytes(download):
    if not download:
        return None
    content = download.get('content')
    return base64.b64decode(content) if download.get('base64') else content.encode('utf-8')


def _texto(component):
    """Texto plano de un mensaje Dash, para el LEEME del paquete."""
    if component is None:
        return ''
    if isinstance(component, (str, int, float)):
        return str(component)
    if isinstance(component, (list, tuple)):
        return ' '.join(t for t in (_texto(c) for c in component) if t)
    return _texto(getattr(component, 'children', None))


def generar_paquete(case, seleccion, modo_curvas='ultima', sulfide_policy='net_trial',
                    curvas_report=None, recon_loader=None, quality_loader=None,
                    extra_loader=None):
    """Genera los informes pedidos. Devuelve ``(archivos, filas_estado)``.

    ``archivos`` es una lista ``(nombre, bytes)``; ``filas_estado`` una lista
    ``(informe, ok, mensaje)``. Cada informe falla por separado."""
    archivos, filas = [], []
    labels = dict(REPORTES)
    if 'curvas' in seleccion:
        try:
            if curvas_report is None:
                from curvas_recon.pad_dashboard import generate_case_report as curvas_report
            estado, download = curvas_report(case['id'], reconciliar=modo_curvas == 'calcular',
                                             sulfide_policy=sulfide_policy)
            data = _download_bytes(download)
            if data:
                archivos.append((download['filename'], data))
            filas.append((labels['curvas'], bool(data), _texto(estado)))
        except Exception:
            filas.append((labels['curvas'], False,
                          'No se pudo generar el reporte de curvas. Revisa la conexión SIIR y reintenta.'))
    pads = [int(key.split('-')[1]) for key in seleccion if key.startswith('recon-')]
    if pads:
        from reconstitucion import panel as recon_panel
        from reconstitucion.modelo_flujos import FlowCaseError
        from reconstitucion import engine as recon_engine
        res, error = None, None
        try:
            res = _resultado_reconstitucion(case, recon_loader)
            if not res.get('fuente_modelo'):
                error = ('El Caso no tiene masa reconciliada del modelo de flujos; '
                         'el informe de módulos no está disponible.')
        except FlowCaseError as exc:
            error = str(exc)
        except recon_engine.MissingCaseMassError:
            error = 'El Caso no tiene masa publicada validada disponible. No se usan datos de otros Casos.'
        except Exception:
            error = 'No se pudo cargar la reconstitución del Caso. Verifica conexión y reintenta.'
        for pad in sorted(set(pads)):
            label = labels[f'recon-{pad}']
            if error:
                filas.append((label, False, error))
                continue
            try:
                informe = recon_panel.generar_informe_modulos(res, pad, quality_loader, extra_loader)
                archivos.append((informe['filename'], informe['xlsx']))
                filas.append((label, True, informe['mensaje']))
            except Exception:
                filas.append((label, False,
                              'No se pudo generar el informe. Verifica la conexión de calidad y reintenta.'))
    return archivos, filas


def empaquetar(case, archivos, filas, ahora=None):
    """Un archivo se entrega tal cual; varios van en un ZIP con LEEME.txt."""
    if len(archivos) == 1:
        return archivos[0]
    ahora = ahora or datetime.now()
    inicio, fin = pd.Timestamp(case['fecha_inicio']), pd.Timestamp(case['fecha_fin'])
    leeme = [
        'Reportes de reconciliación SIIR',
        f"Caso #{case['id']} · {case.get('nombre', '')}",
        f"Run oficial: {case.get('run_id')}",
        f'Ventana: {inicio:%d-%m-%Y} a {fin:%d-%m-%Y}',
        f'Generado: {ahora:%d-%m-%Y %H:%M}',
        '',
    ] + [f"[{'OK' if ok else 'NO GENERADO'}] {informe}: {mensaje}" for informe, ok, mensaje in filas]
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('LEEME.txt', '\n'.join(leeme) + '\n')
        for nombre, data in archivos:
            archive.writestr(nombre, data)
    return f"Reportes_Reconciliacion_Caso{case['id']}_{ahora:%Y%m%d_%H%M}.zip", buffer.getvalue()


def _estado(filas, nombre=None):
    items = [html.Li([html.Strong('Listo · ' if ok else 'No generado · '), f'{informe}: ', mensaje],
                     className='ok' if ok else 'error') for informe, ok, mensaje in filas]
    head = (html.P(f'Descarga: {nombre}', className='reportes-recon-note') if nombre
            else html.P('No se generó ningún archivo.', className='reportes-recon-note'))
    return html.Div([head, html.Ul(items, className='reportes-recon-status')])


def register_callbacks(app, case_loader=None, **report_kwargs):
    """Registro idempotente; loaders inyectables para pruebas sin SQL."""
    if getattr(app, '_reportes_recon_registered', False):
        return
    app._reportes_recon_registered = True
    load_cases = case_loader or _host_casos

    @app.callback(Output(_id('casos'), 'data'), Output(_id('caso'), 'options'),
        Output(_id('caso'), 'value'), Output(_id('estado-casos'), 'children'),
        Input(_id('iniciar'), 'n_intervals'), State(_id('caso'), 'value'),
        prevent_initial_call=True)
    def cargar_catalogo(n, selected=None):
        if not n:
            return (no_update,) * 4
        try:
            cases = [dict(c, fecha_inicio=pd.Timestamp(c['fecha_inicio']).isoformat(),
                          fecha_fin=pd.Timestamp(c['fecha_fin']).isoformat())
                     for c in load_cases() if c.get('run_id')]
        except Exception:
            return None, [], None, 'No se pudieron cargar los Casos. Vuelve a abrir la sección para reintentar.'
        options = [{'label': f"Caso #{c['id']} · {c['nombre']} · "
                    f"{pd.Timestamp(c['fecha_inicio']):%d-%m-%Y} a {pd.Timestamp(c['fecha_fin']):%d-%m-%Y}",
                    'value': c['id']} for c in cases]
        value = selected if _caso(cases, selected) else (cases[0]['id'] if cases else None)
        return cases, options, value, ('Casos oficiales cargados.' if cases
                                       else 'No hay Casos oficiales disponibles.')

    @app.callback(Output(_id('sulfuros-wrap'), 'style'), Input(_id('modo-curvas'), 'value'))
    def mostrar_metodologia(modo):
        return {'display': 'block' if modo == 'calcular' else 'none', 'marginTop': '8px'}

    @app.callback(Output(_id('generar'), 'disabled'),
        Input(_id('caso'), 'value'), Input(_id('seleccion'), 'value'))
    def habilitar(case_id, seleccion):
        return case_id is None or not seleccion

    @app.callback(Output(_id('download'), 'data'), Output(_id('estado'), 'children'),
        Input(_id('generar'), 'n_clicks'),
        State(_id('caso'), 'value'), State(_id('casos'), 'data'),
        State(_id('seleccion'), 'value'), State(_id('modo-curvas'), 'value'),
        State(_id('sulfuros'), 'value'),
        prevent_initial_call=True,
        running=[(Output(_id('generar'), 'disabled'), True, False),
                 (Output(_id('generar'), 'children'), 'Generando reportes…', 'Generar reportes')])
    def generar(n, case_id, cases, seleccion, modo, sulfide_policy):
        if not n:
            return no_update, no_update
        case = _caso(cases, case_id)
        if case is None:
            return None, html.P('Selecciona un Caso oficial.', className='reportes-recon-note')
        if not seleccion:
            return None, html.P('Selecciona al menos un informe.', className='reportes-recon-note')
        archivos, filas = generar_paquete(case, seleccion, modo, sulfide_policy, **report_kwargs)
        if not archivos:
            return None, _estado(filas)
        nombre, data = empaquetar(case, archivos, filas)
        mime = ZIP_MIME if nombre.endswith('.zip') else (
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        return ({'content': base64.b64encode(data).decode('ascii'), 'filename': nombre,
                 'base64': True, 'type': mime}, _estado(filas, nombre))
