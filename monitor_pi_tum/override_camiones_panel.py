"""Control manual del factor aplicado; no recalcula ni publica resultados."""
from datetime import date
import logging
from uuid import uuid4

from flask import has_request_context, session
from dash import Input, Output, State, callback, ctx, dcc, html, no_update
import dash_bootstrap_components as dbc

from . import db
from .limites_camiones_panel import fecha, tabla

PREFIX = 'pitum-override-'
SESSION_KEY = 'pitum_override_confirmacion'
log = logging.getLogger(__name__)


def usuario():
    value = session.get('user') if has_request_context() else None
    return value.strip() if isinstance(value,str) and value.strip() else None


def layout():
    return html.Div([
        html.H5('Control manual del factor aplicado'),
        html.P('Permite definir 1,0000 como factor operativo para los reportes del rango seleccionado, conservando sin cambios el factor calculado para trazabilidad.', className='text-muted small'),
        dbc.Row([
            dbc.Col([dbc.Label('Desde'),dcc.DatePickerSingle(id=PREFIX+'desde',date=date.today().isoformat(),display_format='DD-MM-YYYY')],md=6),
            dbc.Col([dbc.Label('Hasta'),dcc.DatePickerSingle(id=PREFIX+'hasta',date=date.today().isoformat(),display_format='DD-MM-YYYY')],md=6),
        ],className='mb-2'),
        dbc.Label('Motivo'),dbc.Textarea(id=PREFIX+'motivo',maxLength=1000),
        html.Div(id=PREFIX+'usuario',className='small my-2'),
        dbc.Button('Forzar factor = 1',id=PREFIX+'forzar',color='secondary',outline=True,className='me-2'),
        dbc.Button('Restaurar automático',id=PREFIX+'automatico',color='secondary',outline=True),
        dcc.Store(id=PREFIX+'version',data=0),dcc.Store(id=PREFIX+'token'),
        html.Div(id=PREFIX+'resultado',className='mt-2'),
        html.Details([html.Summary('Historial de controles manuales'),html.Div(id=PREFIX+'historial')],className='mt-2'),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Confirmar control del factor aplicado'),close_button=False),
            dbc.ModalBody([html.Div(id=PREFIX+'resumen'),dbc.Checkbox(id=PREFIX+'retro-check',value=False,
                label='Confirmo que entiendo que el cambio afecta fechas históricas.')]),
            dbc.ModalFooter([dbc.Button('Cancelar',id=PREFIX+'cancelar',color='secondary'),
                             dbc.Button('Confirmar',id=PREFIX+'confirmar',color='primary',disabled=True)]),
        ],id=PREFIX+'confirmacion',is_open=False,backdrop='static',keyboard=False),
    ],className='border-top mt-3 pt-3')


@callback(Output(PREFIX+'historial','children'),Output(PREFIX+'usuario','children'),Input(PREFIX+'version','data'))
def refrescar_historial(_version):
    identity='Usuario autenticado: '+usuario() if usuario() else 'Se requiere una sesión autenticada para registrar.'
    try:
        history=db.obtener_historial_override_factor()
        if history.empty:
            return html.P('Sin controles manuales registrados.',className='text-muted small'),identity
        return tabla(['ID','Desde','Hasta','Modo','Motivo','Usuario','Fecha registro'],[
            [r['id_override'],fecha(r['fecha_desde']),fecha(r['fecha_hasta']),r['modo'],r['motivo'],r['usuario'],fecha(r['fecha_registro'],True)]
            for r in history.to_dict('records')]),identity
    except Exception:
        log.exception('Error leyendo historial de control manual')
        return dbc.Alert('No fue posible consultar el historial de controles manuales.',color='warning'),identity


def preparar_confirmacion(desde,hasta,modo,motivo):
    if has_request_context():
        session.pop(SESSION_KEY,None)
    payload=db.validar_override_factor(desde,hasta,modo,motivo,usuario())
    version=db.obtener_version_override_rango(payload['fecha_desde'],payload['fecha_hasta'])
    retro=payload['fecha_desde']<date.today()
    label='CAMBIO RETROACTIVO' if retro else 'CAMBIO PROGRAMADO' if payload['fecha_desde']>date.today() else 'CAMBIO VIGENTE DESDE HOY'
    description=html.Div([
        dbc.Alert(label,color='warning' if retro else 'info'),
        tabla(['Dato','Valor'],[
            ['Acción','Forzar factor = 1' if modo=='FORZADO_1' else 'Restaurar automático'],
            ['Desde',fecha(payload['fecha_desde'])],['Hasta',fecha(payload['fecha_hasta'])],
            ['Cantidad de días',(payload['fecha_hasta']-payload['fecha_desde']).days+1],
            ['Motivo',payload['motivo']],['Usuario',payload['usuario']],
        ]),
        html.P(
            'El factor forzado será el factor operativo utilizado por los reportes para este rango. '
            'Esta acción solo registra el cambio; no reprocesará automáticamente resultados históricos ya materializados ni publicará reportes.'
            if modo=='FORZADO_1' else
            'El factor automático volverá a ser el factor operativo utilizado por los reportes para este rango. '
            'Esta acción solo registra el cambio; no reprocesará automáticamente resultados históricos ya materializados ni publicará reportes.'),
        html.P(
            'El factor calculado se conservará para trazabilidad. Durante FORZADO_1, el factor aplicado a reportes será 1,0000.'
            if modo=='FORZADO_1' else
            'El factor calculado se conservará para trazabilidad y el factor aplicado volverá al valor automático.'),
        html.P('El rango incluye ambas fechas.'),
    ])
    token=uuid4().hex
    session[SESSION_KEY]={**payload,'fecha_desde':payload['fecha_desde'].isoformat(),
                          'fecha_hasta':payload['fecha_hasta'].isoformat(),'version_esperada':version,'token':token}
    return token,description,retro


def presentar_resultado(result):
    affected=bool(result['Afecta_Fechas_Materializadas'])
    return dbc.Alert([
        html.Strong('Control registrado. '+('PENDIENTE DE REPROCESO' if affected else 'PROGRAMADO')),
        html.P(f"{result['Modo']}: {fecha(result['Fecha_Desde'])} → {fecha(result['Fecha_Hasta'])}."),
        html.P('Rango potencialmente afectado: '+fecha(result['Fecha_Inicio_Materializada_Afectada'])+' → '+fecha(result['Fecha_Fin_Materializada_Afectada']))
            if affected else html.P('No existen actualmente fechas materializadas afectadas.'),
        html.P(
            'Control registrado. El factor aplicado a reportes para el rango seleccionado pasa a 1,0000. '
            'Los resultados históricos ya materializados NO fueron reprocesados automáticamente.'
            if result['Modo']=='FORZADO_1' else
            'Control registrado. El factor aplicado a reportes para el rango seleccionado vuelve al valor automático. '
            'Los resultados históricos ya materializados NO fueron reprocesados automáticamente.'),
    ],color='warning' if affected else 'success')


def confirmar_registro(token,ack):
    pending=session.get(SESSION_KEY) if has_request_context() else None
    if not pending or pending.get('token')!=token or pending.get('usuario')!=usuario() or not usuario():
        raise ValueError('La confirmación no está vigente. Revise nuevamente la solicitud.')
    if date.fromisoformat(pending['fecha_desde'])<date.today() and ack is not True:
        raise ValueError('Debe confirmar expresamente que el cambio afecta fechas históricas.')
    try:
        return db.registrar_override_factor(**{k:v for k,v in pending.items() if k!='token'})
    finally:
        session.pop(SESSION_KEY,None)


def mensaje_error(exc):
    if isinstance(exc,ValueError):
        return str(exc)
    for code,message in [('53100','Seleccione fechas válidas.'),('53101','Hasta no puede ser anterior a Desde.'),
                         ('53102','Modo de aplicación inválido.'),('53103','El motivo es obligatorio.'),
                         ('53104','El motivo excede 1000 caracteres.'),('53105','Se requiere usuario autenticado.'),
                         ('53106','El usuario excede 128 caracteres.')]:
        if code in str(exc):
            return message
    return 'No fue posible registrar el control. Revise la conexión DEV y el historial antes de volver a intentarlo.'


@callback(Output(PREFIX+'confirmacion','is_open'),Output(PREFIX+'resumen','children'),
          Output(PREFIX+'token','data'),Output(PREFIX+'retro-check','value'),
          Output(PREFIX+'resultado','children'),Output(PREFIX+'version','data'),
          Input(PREFIX+'forzar','n_clicks'),Input(PREFIX+'automatico','n_clicks'),
          Input(PREFIX+'cancelar','n_clicks'),Input(PREFIX+'confirmar','n_clicks'),
          State(PREFIX+'desde','date'),State(PREFIX+'hasta','date'),State(PREFIX+'motivo','value'),
          State(PREFIX+'token','data'),State(PREFIX+'retro-check','value'),State(PREFIX+'version','data'),prevent_initial_call=True)
def gestionar(_force,_auto,_cancel,_confirm,desde,hasta,motivo,token,ack,version):
    try:
        action=ctx.triggered_id
        if action==PREFIX+'cancelar':
            session.pop(SESSION_KEY,None)
            return False,'',None,False,no_update,no_update
        if action in (PREFIX+'forzar',PREFIX+'automatico'):
            mode='FORZADO_1' if action==PREFIX+'forzar' else 'AUTOMATICO'
            challenge,description,_=preparar_confirmacion(desde,hasta,mode,motivo)
            return True,description,challenge,False,no_update,no_update
        if action==PREFIX+'confirmar':
            result=confirmar_registro(token,ack)
            return False,'',None,False,presentar_resultado(result),(version or 0)+1
    except Exception as exc:
        log.exception('No se completó el control manual del factor')
        if has_request_context():
            session.pop(SESSION_KEY,None)
        return False,'',None,False,dbc.Alert(mensaje_error(exc),color='danger'),no_update
    return (no_update,)*6


@callback(Output(PREFIX+'confirmar','disabled'),Output(PREFIX+'retro-check','style'),
          Input(PREFIX+'token','data'),Input(PREFIX+'retro-check','value'))
def habilitar_confirmacion(token,ack):
    pending=session.get(SESSION_KEY) if has_request_context() else None
    valid=bool(pending and usuario() and pending.get('token')==token and pending.get('usuario')==usuario())
    retro=valid and date.fromisoformat(pending['fecha_desde'])<date.today()
    return not valid or (retro and ack is not True), {'display':'block' if retro else 'none'}
