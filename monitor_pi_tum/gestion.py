"""Gestión global PI/TUM: acciones auditadas y apilado en una transacción."""
from datetime import date
from decimal import Decimal
import logging
from uuid import uuid4
import pandas as pd
from flask import session, has_request_context
from dash import Input, Output, State, callback, ctx, dcc, html, dash_table, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from . import db

log = logging.getLogger(__name__)
DESCRIPCIONES_MOTIVO = {
    'CAIDA_PI': 'Indisponibilidad general o pérdida de datos desde PI System.',
    'MANTENCION': 'Intervención planificada o conocida que afecta la disponibilidad o confiabilidad del dato.',
    'COMUNICACIONES': 'Falla de transmisión, enlace o red entre la fuente operacional y PI.',
    'SERVIDOR': 'Falla o indisponibilidad identificada en un servidor o servicio asociado.',
    'OTRO': 'Causa distinta a las anteriores. Debe especificarse en el comentario.',
}
SIN_USUARIO = "No fue posible identificar al usuario de la sesión. La acción no fue registrada."
ESTADOS_PI = {
    'CON_VARIACION': 'Con variación',
    'SIN_CAMBIO': 'Sin cambio',
    'SIN_CAMBIO_TURNO_COMPLETO': 'Sin cambio · turno completo',
    'SIN_CAMBIO_CON_COBERTURA_PARCIAL': 'Sin cambio · cobertura parcial',
    'CON_VARIACION_COBERTURA_PARCIAL': 'Con variación · cobertura parcial',
    'SIN_PI': 'Sin PI',
}
ALERTA_TUM = ("Uno o más totalizadores no poseen Informe TUM para el período seleccionado.\n\n"
              "La contingencia puede registrarse, pero los equipos afectados quedarán pendientes de TUM "
              "hasta que la información sea cargada.")
CONFIRMAR_ACTIVAR = ("Está por declarar una contingencia de PI System.\n\n"
                    "Durante este período, las siete señales utilizarán Informe TUM como fuente operacional.")
CONFIRMAR_CERRAR = ("Desde el período seleccionado el sistema volverá a utilizar PI System como fuente "
                   "por defecto. ¿Desea continuar?")
ALERTA_SIN_INFORMACION_TUM = (
    "No existe información TUM suficiente para evaluar todas las señales en el período seleccionado.\n\n"
    "Si se registra la contingencia, los equipos sin TUM quedarán pendientes de resolución "
    "hasta que la información sea cargada.")


def _usuario():
    valor = session.get('user') if has_request_context() else None
    return valor if isinstance(valor, str) and valor.strip() else None


def layout():
    return html.Div([
        html.H4("Gestión operacional PI/TUM", className="mt-4"),
        html.P("PI System es la fuente por defecto. Informe TUM se utiliza únicamente durante una contingencia declarada."),
        dbc.Card(dbc.CardBody([
            html.H5("Estado operacional vigente"),
            dcc.Loading(html.Div(id="pitum-gestion-estado-actual")),
            html.H5("Estado en el período seleccionado"),
            dcc.Loading(html.Div(id="pitum-gestion-estado")),
            dbc.Button("Activar contingencia PI", id="pitum-gestion-activar", color="warning", disabled=True, className="me-2 mt-2"),
            dbc.Button("Cerrar contingencia", id="pitum-gestion-cerrar", color="primary", disabled=True, className="mt-2"),
        ]), className="mb-3"),
        dbc.Card(dbc.CardBody([
            html.H5("Consulta de período"),
            html.P("Seleccione una fecha y turno para consultar el estado de PI, TUM, la fuente resuelta y el apilado del período.",
                   className="text-muted small mb-2"),
            dbc.Row([
                dbc.Col([html.Label("Fecha operacional", className="d-block"),
                         dcc.DatePickerSingle(id="pitum-gestion-fecha", date=date.today().isoformat(),
                            min_date_allowed=db.CORTE.isoformat(), display_format="DD-MM-YYYY", first_day_of_week=1)], md=5),
                dbc.Col([dbc.Label("Turno", html_for="pitum-gestion-turno"),
                         dcc.Dropdown(id="pitum-gestion-turno", options=["A", "B"], value="A", clearable=False)], md=3),
                dbc.Col(dbc.Button("Actualizar", id="pitum-gestion-refrescar", className="mt-4", outline=True), md=4),
            ], className="g-3"),
            html.Small('Este selector solo consulta información. Para declarar una contingencia utilice "Activar contingencia PI".',
                       className="text-muted d-block mt-2"),
            html.Div(id="pitum-gestion-guardado", className="mt-3"),
            dcc.Store(id="pitum-gestion-version"),
        ]), className="mb-3"),
        dbc.Card(dbc.CardBody([
            html.H5("Disponibilidad de datos · siete señales"),
            html.P("Fuentes y valores del turno seleccionado.", className="text-muted small"),
            dcc.Loading(html.Div(id="pitum-gestion-preview")),
            html.H6("Apilado materializado del período", className="mt-3"),
            dcc.Loading(html.Div(id="pitum-gestion-apilado")),
        ]), className="mb-3"),
        dbc.Card(dbc.CardBody([
            html.H5("Historial de contingencias"),
            dcc.Loading(html.Div(id="pitum-gestion-historial")),
        ])),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id="pitum-gestion-titulo-modal"), close_button=False),
            dbc.ModalBody([
                html.Div([
                    html.H6('Período de contingencia'),
                    dbc.Label('Duración', className='fw-semibold'),
                    dbc.RadioItems(id='pitum-modalidad', value='ABIERTA', options=[
                        {'label':'Hasta nuevo aviso','value':'ABIERTA'},
                        {'label':'Definir período de término','value':'RANGO_CERRADO'}],
                        className='mb-3'),
                    html.P('El rango seleccionado define los turnos en los que PI no será utilizado como fuente operacional.',
                           className='text-muted small'),
                    dbc.Row([
                        dbc.Col([
                            html.Div(etiqueta, className='fw-semibold mb-1'),
                            html.Label('Fecha',className='small d-block'),
                            dcc.DatePickerSingle(id=f'pitum-rango-{extremo}',
                                min_date_allowed=db.CORTE.isoformat(), display_format='DD-MM-YYYY'),
                            dbc.Label('Turno',html_for=f'pitum-rango-turno-{extremo}',className='small mt-2'),
                            dcc.Dropdown(id=f'pitum-rango-turno-{extremo}',options=['A','B'],
                                         value='A',clearable=False,className='mt-2'),
                        ], md=6, id='pitum-rango-col-fin' if extremo == 'fin' else 'pitum-rango-col-inicio')
                        for extremo,etiqueta in [('inicio','Desde'),('fin','Hasta')]
                    ],className='g-3'),
                    html.Small('La contingencia permanecerá activa hasta que un especialista registre su cierre.',
                               id='pitum-abierta-ayuda', className='text-muted'),
                    dcc.Store(id='pitum-rango-validado'),
                ],id='pitum-rango-bloque',style={'display':'none'}),
                html.Div([
                    html.P(id='pitum-cierre-desde'),
                    html.Div('PI volverá a utilizarse desde:', className='fw-semibold'),
                    dbc.Row([
                        dbc.Col([html.Label('Fecha', className='d-block'),
                                 dcc.DatePickerSingle(id='pitum-cierre-fecha',
                                     min_date_allowed=db.CORTE.isoformat(), display_format='DD-MM-YYYY')], md=6),
                        dbc.Col([dbc.Label('Turno', html_for='pitum-cierre-turno'),
                                 dcc.Dropdown(id='pitum-cierre-turno', options=['A','B'], value='A', clearable=False)], md=6),
                    ], className='g-3'),
                ], id='pitum-cierre-bloque', style={'display':'none'}),
                dcc.Store(id='pitum-gestion-cierre-desde'),
                html.Div(id="pitum-gestion-detalle-modal"),
                html.Div(id="pitum-gestion-error-modal", role="alert"),
                html.Div([
                    dbc.Label("Motivo (obligatorio)", html_for="pitum-gestion-motivo", className="fw-semibold"),
                    dcc.Dropdown(id="pitum-gestion-motivo", options=[
                        {"label":label,"value":value} for value,label in zip(db.MOTIVOS,
                        ("Caída PI System","Mantención","Comunicaciones","Servidor","Otro"))],
                        placeholder="Seleccione el motivo", clearable=False),
                    html.Div(id="pitum-gestion-motivo-ayuda", className="small mt-2", **{'aria-live': 'polite'}),
                    html.Small("Seleccione un motivo para habilitar Confirmar.",
                               id="pitum-gestion-motivo-pendiente", className="text-muted mt-1", style={'display': 'block'}),
                    html.Small("El motivo explica por qué PI fue declarado no confiable. No determina si TUM está disponible.",
                               className="text-muted d-block mt-2"),
                ], id="pitum-gestion-motivo-bloque", className="mt-3"),
                dbc.Label("Comentario (opcional)", id="pitum-gestion-comentario-label",
                          html_for="pitum-gestion-comentario", className="mt-3 fw-semibold"),
                dbc.Textarea(id="pitum-gestion-comentario", maxLength=1000, rows=3),
                html.Small("Especifique la causa para habilitar Confirmar.",
                           id="pitum-gestion-comentario-pendiente", className="text-muted mt-1",
                           style={'display': 'none'}, **{'aria-live': 'polite'}),
                html.Div([html.Div("Usuario responsable", className="text-muted small"),
                          html.Strong(id="pitum-gestion-usuario")], className="mt-3 pt-3 border-top"),
                dcc.Loading(html.Div(id='pitum-rango-preview',className='mt-3')),
            ]),
            dbc.ModalFooter(html.Fieldset([
                dbc.Button("Cancelar", id="pitum-gestion-cancelar", color="secondary", outline=True),
                dbc.Button("Confirmar", id="pitum-gestion-guardar", color="primary", disabled=True),
            ], id="pitum-gestion-acciones", disabled=False,
               className="d-flex justify-content-end gap-2 m-0 p-0 border-0")),
        ], id="pitum-gestion-modal", is_open=False, backdrop="static", keyboard=False,
           size="lg", scrollable=True),
    ])


@callback(Output('pitum-gestion-guardar', 'disabled'),
          Input('pitum-gestion-modal', 'is_open'), Input('pitum-gestion-motivo', 'value'),
          Input('pitum-gestion-motivo-bloque', 'style'), Input('pitum-gestion-comentario', 'value'),
          Input('pitum-rango-inicio','date'), Input('pitum-rango-turno-inicio','value'),
          Input('pitum-rango-fin','date'), Input('pitum-rango-turno-fin','value'),
          Input('pitum-rango-validado','data'), Input('pitum-modalidad','value'),
          Input('pitum-cierre-fecha','date'), Input('pitum-cierre-turno','value'),
          State('pitum-gestion-cierre-desde','data'))
def confirmar_deshabilitado(abierto, motivo, motivo_style, comentario=None,
                           inicio=None, turno_inicio=None, fin=None, turno_fin=None, validado=None,
                           modalidad='RANGO_CERRADO', cierre_fecha=None, cierre_turno=None, cierre_desde=None):
    """Validación visual; el cierre conserva su comportamiento sin motivo."""
    if not abierto or not _usuario():
        return True
    es_cierre = (motivo_style or {}).get('display') == 'none'
    if es_cierre:
        try:
            fecha = db.validar_periodo(cierre_fecha, cierre_turno)
            return not cierre_desde or (fecha, cierre_turno) < (
                db.validar_periodo(cierre_desde[0], cierre_desde[1]), cierre_desde[1])
        except (ValueError, TypeError):
            return True
    if modalidad == 'ABIERTA':
        valido = isinstance(validado,dict) and validado.get('abierta') == [inicio,turno_inicio]
    elif modalidad == 'RANGO_CERRADO':
        valido = _rango_confirmado(inicio,turno_inicio,fin,turno_fin,validado)
    else:
        valido = False
    return not valido or motivo not in db.MOTIVOS or (
        motivo == 'OTRO' and (not isinstance(comentario, str) or not comentario.strip()))


@callback(Output('pitum-rango-col-fin','style'), Output('pitum-abierta-ayuda','style'),
          Output('pitum-rango-fin','date'), Output('pitum-rango-turno-fin','value'),
          Input('pitum-modalidad','value'), Input('pitum-gestion-modal','is_open'),
          State('pitum-rango-inicio','date'), State('pitum-rango-turno-inicio','value'))
def estilo_modalidad(modalidad, abierto=True, inicio=None, turno_inicio=None):
    abierta = modalidad == 'ABIERTA'
    return ({'display':'none' if abierta else 'block'},
            {'display':'block' if abierta else 'none'},
            None if abierta or not abierto else inicio,
            None if abierta or not abierto else turno_inicio)


def _rango_confirmado(inicio, turno_inicio, fin, turno_fin, validado):
    try:
        db.validar_rango(inicio,turno_inicio,fin,turno_fin)
    except ValueError:
        return False
    return isinstance(validado,dict) and validado.get('periodo') == [inicio,turno_inicio,fin,turno_fin]


def presentar_preview_rango(frame, inicio, turno_inicio, fin, turno_fin):
    periodos = db.expandir_turnos(inicio,turno_inicio,fin,turno_fin)
    datos = {}
    for row in frame.to_dict('records'):
        datos[(str(row['fecha_operacional'])[:10],row['turno'],row['equipo_codigo'])] = row
    filas, completos, faltantes, desconocidos = [], 0, 0, 0
    for fecha, turno in periodos:
        estados = [_disponibilidad_evaluada(datos.get((fecha.isoformat(),turno,e),{}).get(
            'tum_disponible_operacional')) for e in db.EQUIPOS]
        completo = all(e is True for e in estados)
        completos += int(completo)
        faltantes += int(any(e is False for e in estados))
        desconocidos += int(any(e is None for e in estados))
        fila = dict(fecha=f'{fecha:%d-%m-%Y}', turno=turno,
            resultado='TUM' if completo else 'Pendiente de TUM',
            informacion='Sin información TUM' if None in estados else 'Evaluado')
        fila.update({equipo: _disponibilidad(estado)
                     for equipo, estado in zip(db.EQUIPOS, estados)})
        filas.append(fila)
    cierre, turno_cierre = db.turno_siguiente(fin,turno_fin)
    contenido = [html.Strong(f'Período seleccionado: {periodos[0][0]:%d-%m-%Y} {turno_inicio} → {periodos[-1][0]:%d-%m-%Y} {turno_fin}'),
        html.Div(f'Turnos afectados: {len(periodos)}'),
        html.Div(f'Con TUM completo: {completos} · Con TUM faltante: {len(periodos)-completos}'),
        html.Small(f'Evaluados sin TUM: {faltantes} · Sin información TUM: {desconocidos}',className='text-muted'),
        html.Div(f'Vuelve a PI desde: {cierre:%d-%m-%Y} · Turno {turno_cierre}',className='my-2'),
        _tabla(pd.DataFrame(filas), [('fecha','Fecha'),('turno','Turno'),
            *((equipo, equipo.replace('PRINCIPAL_', '') + ' TUM') for equipo in db.EQUIPOS),
            ('resultado','Resultado esperado'),('informacion','Información')])]
    if completos != len(periodos):
        contenido.append(dbc.Alert(f'{len(periodos)-completos} de {len(periodos)} turnos no poseen TUM disponible. '
            'Esos períodos quedarán pendientes de TUM hasta que la información sea cargada. '
            'La contingencia puede registrarse.',color='warning',className='mt-2'))
    contenido.append(html.P(f'Está por declarar una contingencia PI para {len(periodos)} turnos, '
        f'desde {periodos[0][0]:%d-%m-%Y} {turno_inicio} hasta {periodos[-1][0]:%d-%m-%Y} {turno_fin}.',
        className='fw-semibold mt-3 mb-0'))
    return html.Div(contenido)


@callback(Output('pitum-rango-preview','children'), Output('pitum-rango-validado','data'),
          Input('pitum-rango-inicio','date'), Input('pitum-rango-turno-inicio','value'),
          Input('pitum-rango-fin','date'), Input('pitum-rango-turno-fin','value'),
          Input('pitum-gestion-modal','is_open'), Input('pitum-rango-bloque','style'),
          Input('pitum-modalidad','value'))
def previsualizar_rango(inicio, turno_inicio, fin, turno_fin, abierto, estilo, modalidad='RANGO_CERRADO'):
    if not abierto or (estilo or {}).get('display') == 'none':
        return '', None
    try:
        if modalidad == 'ABIERTA':
            ultimo_fecha, ultimo_turno = db.obtener_ultimo_periodo_materializable()
            if (db.validar_periodo(inicio, turno_inicio), turno_inicio) > (ultimo_fecha, ultimo_turno):
                raise ValueError('No es posible iniciar una contingencia en un período futuro o aún no materializable.')
            frame = db.obtener_preview_rango(inicio,turno_inicio,ultimo_fecha.isoformat(),ultimo_turno)
            contenido = presentar_preview_rango(frame,inicio,turno_inicio,ultimo_fecha.isoformat(),ultimo_turno)
            # El rango sirve para evaluar TUM; no implica un cierre automático.
            resumen = [html.Strong('Contingencia abierta'),
                html.Div(f'Inicio de contingencia: {db.validar_periodo(inicio,turno_inicio):%d-%m-%Y} · Turno {turno_inicio}'),
                html.Div('Estado: Hasta nuevo aviso'),
                html.Div(f'Períodos actualmente evaluables: {len(db.expandir_turnos(inicio,turno_inicio,ultimo_fecha.isoformat(),ultimo_turno))}'),
                contenido.children[2], contenido.children[3], contenido.children[5],
                html.P(f'Está por activar una contingencia PI desde {db.validar_periodo(inicio,turno_inicio):%d-%m-%Y} · Turno {turno_inicio}. '
                    'La contingencia permanecerá activa hasta que un especialista registre su cierre.',
                    className='fw-semibold mt-3')]
            if len(contenido.children) > 7:
                resumen.insert(-1, contenido.children[-2])
            return html.Div(resumen), {'abierta':[inicio,turno_inicio]}
        if modalidad != 'RANGO_CERRADO':
            raise ValueError('Seleccione una duración válida.')
        ultimo_fecha, ultimo_turno = db.obtener_ultimo_periodo_materializable()
        if (db.validar_periodo(fin,turno_fin),turno_fin) > (ultimo_fecha,ultimo_turno):
            raise ValueError('El período final no puede superar el último período materializable.')
        frame = db.obtener_preview_rango(inicio,turno_inicio,fin,turno_fin)
        return (presentar_preview_rango(frame,inicio,turno_inicio,fin,turno_fin),
                {'periodo':[inicio,turno_inicio,fin,turno_fin]})
    except ValueError as exc:
        return dbc.Alert(str(exc),color='warning'), None
    except Exception:
        log.exception('Error consultando preview del rango de contingencia')
        return dbc.Alert('No fue posible consultar el rango. Revise el período e intente nuevamente.',color='danger'), None


@callback(Output('pitum-gestion-motivo-ayuda', 'children'),
          Output('pitum-gestion-comentario-label', 'children'),
          Output('pitum-gestion-comentario', 'required'),
          Input('pitum-gestion-motivo', 'value'), Input('pitum-gestion-motivo-bloque', 'style'))
def ayuda_motivo(motivo, motivo_style):
    es_cierre = (motivo_style or {}).get('display') == 'none'
    obligatorio = not es_cierre and motivo == 'OTRO'
    descripcion = '' if es_cierre else DESCRIPCIONES_MOTIVO.get(motivo, '')
    return descripcion, 'Comentario (obligatorio)' if obligatorio else 'Comentario (opcional)', obligatorio


@callback(Output('pitum-gestion-motivo-pendiente', 'style'),
          Output('pitum-gestion-comentario-pendiente', 'style'),
          Input('pitum-gestion-motivo', 'value'), Input('pitum-gestion-motivo-bloque', 'style'),
          Input('pitum-gestion-comentario', 'value'))
def indicaciones_motivo(motivo, motivo_style, comentario):
    es_cierre = (motivo_style or {}).get('display') == 'none'
    falta_motivo = not es_cierre and motivo not in db.MOTIVOS
    falta_causa = not es_cierre and motivo == 'OTRO' and (
        not isinstance(comentario, str) or not comentario.strip())
    return ({'display': 'block' if falta_motivo else 'none'},
            {'display': 'block' if falta_causa else 'none'})


def formato_tonelaje(valor):
    """Texto de presentación; no modifica ni redondea el dato de origen."""
    if pd.isna(valor):
        return '—'
    texto = format(Decimal(str(valor)), ',f')
    if '.' in texto:
        texto = texto.rstrip('0').rstrip('.')
    return texto.translate(str.maketrans({',': '.', '.': ','})) + ' t'


def _disponibilidad_evaluada(valor):
    """Normaliza solo para presentación, conservando el tercer estado desconocido."""
    if pd.isna(valor):
        return None
    if valor == 1:
        return True
    if valor == 0:
        return False
    return None


def _disponibilidad(valor):
    return {True: 'Sí', False: 'No', None: '—'}[_disponibilidad_evaluada(valor)]


def _badge_disponibilidad(valor):
    etiqueta = _disponibilidad(valor)
    if etiqueta == '—':
        return etiqueta
    return dbc.Badge(etiqueta, color='light', text_color='success' if etiqueta == 'Sí' else 'secondary',
                     className='border fw-normal')


def _etiqueta_estado_operacional(activa):
    return html.Strong('Contingencia PI activa' if activa else 'Sin contingencia declarada',
                       title='CONTINGENCIA_PI' if activa else 'NORMAL_PI')


def _tabla_fuentes(datos, incluir_resuelto=False):
    filas = []
    grupos = {equipo: grupo for grupo, equipos in db.GRUPOS_EQUIPOS for equipo in equipos}
    grupo_anterior = None
    for row in datos.to_dict('records'):
        grupo = grupos.get(row['equipo_codigo'], 'OTROS')
        if grupo != grupo_anterior:
            filas.append(html.Tr(html.Th(grupo, colSpan=9 if incluir_resuelto else 6,
                                         scope='colgroup', className='table-secondary')))
            grupo_anterior = grupo
        codigo = row.get('estado_tecnico_pi')
        etiqueta = '—' if pd.isna(codigo) else ESTADOS_PI.get(codigo, codigo)
        celdas = [
            html.Th(row['equipo_codigo'].replace('PRINCIPAL_', ''), scope='row'),
            html.Td(html.Span(etiqueta, title=None if pd.isna(codigo) else str(codigo))),
            html.Td(formato_tonelaje(row.get('valor_pi_final')), className='text-nowrap text-end'),
            html.Td(_badge_disponibilidad(row.get('pi_disponible_operacional'))),
            html.Td(formato_tonelaje(row.get('valor_turno_tum')), className='text-nowrap text-end'),
            html.Td(_badge_disponibilidad(row.get('tum_disponible_operacional'))),
        ]
        if incluir_resuelto:
            fuente = row.get('fuente_resuelta')
            celdas.extend([
                html.Td(fuente if pd.notna(fuente) and fuente in ('PI', 'TUM') else '—'),
                html.Td(formato_tonelaje(row.get('valor_final_resuelto')), className='text-nowrap text-end'),
                html.Td({'PI': 'Resuelto', 'TUM': 'Resuelto',
                         'PENDIENTE_PI': 'Pendiente de PI',
                         'PENDIENTE_TUM': 'Pendiente de TUM'}.get(fuente, 'Sin información')
                        if pd.notna(fuente) else 'Sin información'),
            ])
        filas.append(html.Tr(celdas))
    encabezados = ['Equipo', 'Estado PI', 'PI', 'PI disponible', 'TUM', 'TUM disponible']
    if incluir_resuelto:
        encabezados.extend(['Fuente actual', 'Valor resuelto', 'Estado de resolución'])
    return dbc.Table([
        html.Thead(html.Tr([html.Th(label, scope='col') for label in encabezados]),
            className='table-light'),
        html.Tbody(filas),
    ], responsive=True, hover=True, className='align-middle small mb-0')


def _tabla(frame, columnas, tonelajes=()):
    df = frame.reindex(columns=[c for c, _ in columnas]).copy()
    for col in df.columns:
        if col in tonelajes:
            df[col] = df[col].map(formato_tonelaje)
            continue
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d %H:%M:%S.%f").str[:-3]
    records = df.astype(object).where(pd.notna(df), None).to_dict("records")
    return dash_table.DataTable(
        data=records, columns=[{"id": c, "name": label} for c, label in columnas],
        page_size=10, sort_action="native", editable=False, row_deletable=False,
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Segoe UI, Arial, sans-serif", "fontSize": 12,
                    "padding": "8px", "whiteSpace": "normal", "height": "auto", "textAlign": "left"},
        style_header={"backgroundColor": "#1F4E78", "color": "white", "fontWeight": "bold"},
    )


def presentar_preview(frame, activa, modal=False):
    # Una respuesta sin filas tampoco confirma indisponibilidad: se presenta como —.
    columnas = ['equipo_codigo', *[c for c in frame.columns if c != 'equipo_codigo']]
    datos = frame.reindex(columns=columnas).set_index('equipo_codigo').reindex(db.EQUIPOS).reset_index()
    tabla = _tabla_fuentes(datos, incluir_resuelto=not modal)
    filas_proyeccion, faltantes, sin_informacion = [], [], []
    for row in datos.to_dict('records'):
        equipo = row['equipo_codigo'].replace('PRINCIPAL_', '')
        disponible = _disponibilidad_evaluada(row.get('tum_disponible_operacional'))
        if disponible is True:
            valor = row.get('valor_turno_tum')
            estado_esperado = 'Resuelto'
        else:
            (faltantes if disponible is False else sin_informacion).append(equipo)
            valor = None
            estado_esperado = 'Pendiente de TUM' if disponible is False else 'Sin información'
        nombre = (equipo.replace('CHANCADOR_', '').replace('RIPIOS_', '')
                  .replace('SRR_', 'SRR '))
        filas_proyeccion.append(html.Tr([
            html.Th(nombre, scope='row', className='text-nowrap'),
            html.Td('TUM'),
            html.Td(formato_tonelaje(valor), className='text-nowrap text-end'),
            html.Td(estado_esperado),
        ]))
    contenido = [tabla]
    if not activa:
        contenido += [html.H6("Si activa la contingencia", className="mt-3"),
                      dbc.Table([
                          html.Thead(html.Tr([
                              html.Th(label, scope='col', className='text-end' if label == 'Valor TUM' else '')
                              for label in ('Equipo', 'Fuente si activa', 'Valor TUM', 'Estado esperado')
                          ]), className='table-light'),
                          html.Tbody(filas_proyeccion),
                      ], responsive=True, hover=True, size='sm',
                          className='align-middle small mb-0')]
        explicaciones = []
        if faltantes:
            explicaciones.append("Sin TUM disponible, el equipo quedará pendiente. "
                "Cuando el TUM sea cargado, se utilizará como fuente operacional durante la contingencia.")
        if sin_informacion:
            explicaciones.append("No existe información TUM suficiente para este período. "
                "Si se registra la contingencia, el equipo quedará pendiente hasta que la información sea cargada.")
        if not faltantes and not sin_informacion:
            explicaciones.append("Durante la contingencia, el Informe TUM se utilizará como fuente operacional.")
        contenido.extend(html.Small(texto, className="text-muted d-block mt-2") for texto in explicaciones)
    if faltantes:
        alerta = [html.Strong("Informe TUM no disponible", className='d-block mb-1'),
                  html.Div(ALERTA_TUM, style={'whiteSpace': 'pre-line'}),
                  html.Div("Sin TUM: " + ', '.join(faltantes), className='mt-2')]
        contenido.append(dbc.Alert(alerta, color='warning', className='mt-3 mb-0' if modal else 'mt-3'))
    if sin_informacion:
        contenido.append(dbc.Alert([
            html.Strong("Sin información TUM para el período seleccionado", className='d-block mb-1'),
            html.Div(ALERTA_SIN_INFORMACION_TUM, style={'whiteSpace': 'pre-line'}),
            html.Div("Sin información TUM: " + ', '.join(sin_informacion), className='mt-2'),
        ], color='warning', className='mt-3 mb-0' if modal else 'mt-3'))
    return html.Div(contenido)


@callback(Output('pitum-gestion-estado','children'), Output('pitum-gestion-preview','children'),
          Output('pitum-gestion-historial','children'), Output('pitum-gestion-apilado','children'),
          Output('pitum-gestion-activar','style'), Output('pitum-gestion-cerrar','style'),
          Output('pitum-gestion-activar','disabled'), Output('pitum-gestion-cerrar','disabled'),
          Output('pitum-gestion-estado-actual','children'),
          Input('pitum-gestion-fecha','date'), Input('pitum-gestion-turno','value'),
          Input('pitum-gestion-version','data'), Input('pitum-gestion-refrescar','n_clicks'),
          Input('pitum-tabs','active_tab'))
def cargar(fecha, turno, version, refrescar, tab):
    if tab != 'pitum-gestion':
        raise PreventUpdate
    try:
        estado = db.obtener_estado_contingencia(fecha, turno)
        actual = db.obtener_estado_actual()
        vigente_desde = actual['fecha_accion_vigente']
        if vigente_desde:
            vigente_desde = db.validar_periodo(vigente_desde, actual['turno_accion_vigente'])
        actual_bloque = dbc.Alert([
            _etiqueta_estado_operacional(actual['contingencia_pi_activa']),
            html.Div(f"Desde: {vigente_desde:%d-%m-%Y} · Turno {actual['turno_accion_vigente']}")
            if actual['contingencia_pi_activa'] else None,
            html.Div(f"Motivo: {actual['motivo_contingencia']}")
            if actual['contingencia_pi_activa'] else None,
            html.Div(f"Declarada por: {actual['usuario_estado_operacional']}")
            if actual['contingencia_pi_activa'] else None,
            html.Div('Fuente alternativa: Informe TUM' if actual['contingencia_pi_activa']
                     else 'Fuente por defecto: PI System'),
            html.Div(f"Última acción efectiva: {actual['fecha_accion_vigente']} · turno {actual['turno_accion_vigente']}")
            if actual['fecha_accion_vigente'] else html.Div('Sin contingencias declaradas.'),
        ], color='warning' if actual['contingencia_pi_activa'] else 'secondary')
        frame = db.obtener_preview_turno(fecha, turno)
        historial = db.obtener_historial_contingencias()
        apilado = db.obtener_apilado(fecha, turno)
        activa = bool(estado['contingencia_pi_activa'])
        if activa:
            bloque = dbc.Alert([
                _etiqueta_estado_operacional(True),
                html.Div(f"Desde: {estado['fecha_accion_vigente']} · turno {estado['turno_accion_vigente']}"),
                html.Div(f"Motivo: {estado['motivo_contingencia']}"),
                html.Div(f"Declarada por: {estado['usuario_estado_operacional']}"),
                html.Div(f"Fecha/hora de registro: {estado['fecha_registro_estado_operacional']}"),
                html.Div('Fuente operacional: Informe TUM'),
            ], color='warning')
        else:
            bloque = dbc.Alert([_etiqueta_estado_operacional(False),
                                html.Div('Fuente por defecto: PI System')], color='secondary')
        if not _usuario():
            bloque = html.Div([bloque, dbc.Alert(SIN_USUARIO, color='danger')])
        hist = _tabla(historial, [('fecha_operacional','Fecha operacional'), ('turno','Turno'),
            ('accion','Acción'), ('motivo','Motivo'), ('comentario','Comentario'),
            ('usuario','Usuario'), ('fecha_registro','Fecha de registro')]) if not historial.empty else dbc.Alert('Sin acciones registradas.', color='info')
        mat = _tabla(apilado, [('Fecha','Fecha'), ('CV008','CV008'), ('CV108','CV108'),
            ('Total_turno','Total turno'), ('TMH_Apilado_Total_Dia','Total día'),
            ('Fecha_Calculo','Fecha de cálculo')],
            tonelajes=('CV008','CV108','Total_turno','TMH_Apilado_Total_Dia')) if not apilado.empty else dbc.Alert('Sin apilado materializado para esta fecha.',color='info')
        vigente = bool(actual['contingencia_pi_activa'])
        return (bloque, presentar_preview(frame, activa), hist, mat,
                {'display':'none' if vigente else 'inline-block'},
                {'display':'inline-block' if vigente else 'none'}, not bool(_usuario()), not bool(_usuario()), actual_bloque)
    except ValueError as exc:
        error = dbc.Alert(str(exc), color='warning')
    except Exception:
        log.exception('Error consultando gestión de contingencias')
        error = dbc.Alert('No fue posible consultar el estado. Intente actualizar.', color='danger')
    return error, '', '', '', {'display':'none'}, {'display':'none'}, True, True, error


def _respuesta(abrir=no_update, titulo=no_update, detalle=no_update, motivo_style=no_update,
               usuario=no_update, mensaje=no_update, version=no_update, comentario=no_update, motivo=no_update,
               error_modal='', rango_style=no_update, inicio=no_update, turno_inicio=no_update,
               modalidad=no_update, cierre_style=no_update,
               cierre_fecha=no_update, cierre_turno=no_update, cierre_desde=no_update, cierre_texto=no_update):
    return (abrir, titulo, detalle, motivo_style, usuario, mensaje, version, comentario, motivo, error_modal,
            rango_style,inicio,turno_inicio,modalidad,cierre_style,cierre_fecha,cierre_turno,cierre_desde,cierre_texto)


@callback(Output('pitum-gestion-modal','is_open'), Output('pitum-gestion-titulo-modal','children'),
          Output('pitum-gestion-detalle-modal','children'), Output('pitum-gestion-motivo-bloque','style'),
          Output('pitum-gestion-usuario','children'), Output('pitum-gestion-guardado','children'),
          Output('pitum-gestion-version','data'), Output('pitum-gestion-comentario','value'),
          Output('pitum-gestion-motivo','value'),
          Output('pitum-gestion-error-modal','children'),
          Output('pitum-rango-bloque','style'), Output('pitum-rango-inicio','date'),
          Output('pitum-rango-turno-inicio','value'),
          Output('pitum-modalidad','value'), Output('pitum-cierre-bloque','style'),
          Output('pitum-cierre-fecha','date'), Output('pitum-cierre-turno','value'),
          Output('pitum-gestion-cierre-desde','data'), Output('pitum-cierre-desde','children'),
          Input('pitum-gestion-activar','n_clicks'), Input('pitum-gestion-cerrar','n_clicks'),
          Input('pitum-gestion-cancelar','n_clicks'), Input('pitum-gestion-guardar','n_clicks'),
          State('pitum-gestion-fecha','date'), State('pitum-gestion-turno','value'),
          State('pitum-gestion-motivo','value'), State('pitum-gestion-comentario','value'),
          State('pitum-rango-inicio','date'), State('pitum-rango-turno-inicio','value'),
          State('pitum-rango-fin','date'), State('pitum-rango-turno-fin','value'),
          State('pitum-rango-validado','data'),
          State('pitum-modalidad','value'), State('pitum-cierre-fecha','date'),
          State('pitum-cierre-turno','value'),
          prevent_initial_call=True,
          # El fieldset bloquea ambas acciones durante el envío, sin sobrescribir
          # el disabled del botón que depende del motivo.
          running=[(Output('pitum-gestion-acciones','disabled'),True,False)])
def gestionar(activar, cerrar, cancelar, confirmar, fecha, turno, motivo, comentario,
              inicio=None, turno_inicio=None, fin=None, turno_fin=None, validado=None,
              modalidad='RANGO_CERRADO', cierre_fecha=None, cierre_turno=None):
    trigger = ctx.triggered_id
    usuario = _usuario()
    if not usuario:
        return _respuesta(abrir=False, mensaje=dbc.Alert(SIN_USUARIO,color='danger'))
    if trigger == 'pitum-gestion-cancelar':
        session.pop('pitum_confirmacion',None)
        return _respuesta(abrir=False)
    try:
        if trigger in ('pitum-gestion-activar','pitum-gestion-cerrar'):
            actual = db.obtener_estado_actual()
            accion = 'ACTIVAR_CONTINGENCIA' if trigger.endswith('activar') else 'CERRAR_CONTINGENCIA'
            if bool(actual['contingencia_pi_activa']) != (accion=='CERRAR_CONTINGENCIA'):
                raise ValueError('El estado cambió. Actualice antes de continuar.')
            if accion == 'ACTIVAR_CONTINGENCIA':
                fecha = db.validar_periodo(fecha, turno)
                actual_fecha, actual_turno = db.obtener_ultimo_periodo_materializable()
                if (fecha, turno) > (actual_fecha, actual_turno):
                    raise ValueError('No es posible iniciar una contingencia en un período futuro o aún no materializable.')
            else:
                actual_fecha, actual_turno = db.obtener_ultimo_periodo_materializable()
                fecha, turno = actual_fecha, actual_turno
            session['pitum_confirmacion'] = dict(fecha=fecha.isoformat(),turno=turno,accion=accion,
                usuario=usuario,esperada=actual['accion_vigente_id'] or 0)
            detalle = [html.Div([
                html.Div("Período efectivo", className="text-muted small"),
                html.Strong(f"{fecha:%d-%m-%Y} · Turno {turno}"),
            ], className="mb-3"),
                html.P(CONFIRMAR_ACTIVAR if accion=='ACTIVAR_CONTINGENCIA' else CONFIRMAR_CERRAR,
                       style={'whiteSpace': 'pre-line'}, className='mb-3')]
            if accion == 'ACTIVAR_CONTINGENCIA':
                detalle = [html.P(CONFIRMAR_ACTIVAR,style={'whiteSpace':'pre-line'},className='mt-3')]
            else:
                detalle = ''
            inicio_activo = actual.get('fecha_accion_vigente')
            if hasattr(inicio_activo, 'isoformat'):
                inicio_activo = inicio_activo.isoformat()
            return _respuesta(abrir=True,titulo='Activar contingencia PI' if accion=='ACTIVAR_CONTINGENCIA' else 'Cerrar contingencia PI',
                detalle=detalle, motivo_style={'display':'block' if accion=='ACTIVAR_CONTINGENCIA' else 'none'},
                usuario=usuario,mensaje='',comentario=None,motivo=None,
                rango_style={'display':'block' if accion=='ACTIVAR_CONTINGENCIA' else 'none'},
                inicio=fecha.isoformat(),turno_inicio=turno,
                modalidad='ABIERTA',cierre_style={'display':'block' if accion=='CERRAR_CONTINGENCIA' else 'none'},
                cierre_fecha=actual_fecha.isoformat(),cierre_turno=actual_turno,
                cierre_desde=[inicio_activo,actual.get('turno_accion_vigente')] if accion=='CERRAR_CONTINGENCIA' else None,
                cierre_texto=f"La contingencia está activa desde: {inicio_activo} · Turno {actual.get('turno_accion_vigente')}" if accion=='CERRAR_CONTINGENCIA' else '')
        if trigger != 'pitum-gestion-guardar':
            raise PreventUpdate
        pendiente = session.get('pitum_confirmacion')
        if not pendiente or pendiente.get('usuario') != usuario:
            raise ValueError('Abra la confirmación de la acción antes de continuar.')
        if pendiente['accion']=='ACTIVAR_CONTINGENCIA':
            if modalidad == 'ABIERTA':
                if not isinstance(validado,dict) or validado.get('abierta') != [inicio,turno_inicio]:
                    raise ValueError('Revise el preview de la contingencia antes de confirmar.')
                resultado = db.registrar_contingencia(inicio,turno_inicio,'ACTIVAR_CONTINGENCIA',
                    motivo,comentario,usuario,pendiente['esperada'])
            elif modalidad == 'RANGO_CERRADO':
                if not _rango_confirmado(inicio,turno_inicio,fin,turno_fin,validado):
                    raise ValueError('Revise el preview del rango antes de confirmar.')
                resultado = db.registrar_contingencia_rango(inicio,turno_inicio,fin,turno_fin,motivo,comentario,usuario)
            else:
                raise ValueError('Seleccione una duración válida.')
        else:
            cierre_dia = db.validar_periodo(cierre_fecha,cierre_turno)
            vigente = db.obtener_estado_actual()
            inicio_vigente = vigente['fecha_accion_vigente']
            if (not vigente['contingencia_pi_activa'] or
                    (vigente['accion_vigente_id'] or 0) != pendiente['esperada']):
                raise ValueError('El estado cambió desde la confirmación. Actualice y revise la acción.')
            if (cierre_dia,cierre_turno) < (inicio_vigente,vigente['turno_accion_vigente']):
                raise ValueError('El cierre no puede ser anterior al inicio de la contingencia.')
            resultado = db.registrar_contingencia(cierre_dia.isoformat(),cierre_turno,pendiente['accion'],
                None, comentario,usuario,pendiente['esperada'])
        session.pop('pitum_confirmacion',None)
        if pendiente['accion']=='ACTIVAR_CONTINGENCIA' and modalidad == 'ABIERTA':
            texto = f'Contingencia PI activada desde {db.validar_periodo(inicio,turno_inicio):%d-%m-%Y} · Turno {turno_inicio}. Permanecerá activa hasta que se registre su cierre.'
        elif pendiente['accion']=='ACTIVAR_CONTINGENCIA':
            texto = 'Contingencia PI registrada correctamente.'
        else:
            texto = f'Contingencia PI cerrada correctamente. PI vuelve a utilizarse desde {cierre_dia:%d-%m-%Y} · Turno {cierre_turno}.'
        if pendiente['accion']=='ACTIVAR_CONTINGENCIA' and modalidad == 'RANGO_CERRADO' and 'fecha_cierre' in resultado:
            texto += f" Vuelve a PI desde {resultado['fecha_cierre']:%d-%m-%Y} · Turno {resultado['turno_cierre']}."
        if resultado['pendientes_tum']:
            texto += ' Existen equipos pendientes de Informe TUM: ' + ', '.join(resultado['pendientes_tum']) + '.'
        texto += f" Apilado actualizado desde {resultado['inicio']} hasta {resultado['fin']}."
        return _respuesta(abrir=False,mensaje=dbc.Alert(texto,color='warning' if resultado['pendientes_tum'] else 'success'),
                          version=uuid4().hex,comentario=None,motivo=None)
    except ValueError as exc:
        aviso = dbc.Alert(str(exc), color='warning')
        return _respuesta(mensaje=aviso, error_modal=aviso, version=uuid4().hex)
    except PreventUpdate:
        raise
    except RuntimeError as exc:
        if str(exc) == db.DEV_BLOCKED:
            session.pop('pitum_confirmacion',None)
            return _respuesta(abrir=False,mensaje=dbc.Alert(
                'La operación fue bloqueada porque no se pudo validar el ambiente DEV.',
                color='danger'),version=uuid4().hex)
        log.exception('Error registrando contingencia y reprocesando apilado')
        session.pop('pitum_confirmacion',None)
        return _respuesta(abrir=False,mensaje=dbc.Alert(
            'No fue posible confirmar la operación. Revise el historial actualizado antes de reintentar.',
            color='danger'),version=uuid4().hex)
    except Exception:
        log.exception('Error registrando contingencia y reprocesando apilado')
        session.pop('pitum_confirmacion',None)
        return _respuesta(abrir=False,mensaje=dbc.Alert('No fue posible confirmar la operación. Revise el historial actualizado antes de reintentar.',color='danger'),version=uuid4().hex)
