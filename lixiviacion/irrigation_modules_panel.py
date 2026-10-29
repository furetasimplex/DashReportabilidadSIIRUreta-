"""Presentacion y acciones modulares propias; no modifica fase ni mapa principal."""
import json
import uuid
from datetime import date
from dash import html,dcc,callback,Input,Output,State,ctx,no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from . import irrigation_modules_db as db, irrigation_modules_model as model, phase_flags

LABELS={'SELECCION_CONOCIDA':'Selección conocida','NINGUN_MODULO':'Ningún módulo','SIN_INFORMACION':'Sin información'}


def _chips(names):
    return html.Div([html.Span(name,className='imr-chip') for name in names],className='imr-chips')


def _reference(snapshot):
    reference=snapshot.get('referencia')
    if not reference:
        return None
    valid=reference['estado_referencia']=='VALIDA' and reference.get('estructura_actual',True)
    names=[x['nombre_visible'] for x in reference.get('sugeridos') or []]
    count=reference['cantidad_modulos_referencia']
    denominator=reference.get('total_modulos_snapshot',snapshot['roster']['total'])
    quantity='Sin información' if count is None else f'{count} de {denominator if denominator is not None else "?"} módulos'
    return html.Div([html.H6('REFERENCIA OPERACIONAL'),
        html.Div([html.Span('Fuente: ',className='imr-muted'),reference['fuente']]),
        html.Div([html.Span('Cantidad: ',className='imr-muted'),html.Strong(quantity)]),
        html.Div('Sugerencia:',className='imr-label'),
        _chips(names) if valid and names else html.Div('Sin módulos sugeridos.' if valid and count==0 else 'Sin autosugerencia.',className='imr-muted'),
        html.Small('Referencia no confirmada; no equivale a una confirmación modular.'),
        html.Small(reference.get('observacion') or ('' if valid else 'Referencia ambigua, inconsistente o de otra estructura.'))],className='imr-reference')


def _effective_date(value):
    try:return date.fromisoformat(str(value)[:10]).strftime('%d-%m-%Y')
    except ValueError:return str(value or 'No disponible')


def _documentary_notes(row):
    return [html.Div(label+str(row[key])) for key,label in (
        ('observacion','Observación: '),('evidencia_usuario','Evidencia registrada: ')) if row.get(key)]


def detail(snapshot):
    active=snapshot.get('vigente');total=active.get('total_modulos_snapshot',snapshot['roster']['total']) if active else snapshot['roster']['total']
    if active:
        state=active['estado_modular'];count=active['cantidad_confirmada']
        main=(f'{count} de {total} módulos en riego' if state!='SIN_INFORMACION' else 'Sin información de módulos en riego.')
        names=[x['nombre_modulo_snapshot'] or str(x['modulo_id']) for x in snapshot.get('seleccion',[])]
        confirmation=html.Div([html.H6('CONFIRMACIÓN MODULAR'),
            html.Div([html.Span('Estado: ',className='imr-muted'),LABELS[state]]),
            html.Strong(main,className='imr-summary'),
            html.Div('Ningún módulo confirmado en riego.') if state=='NINGUN_MODULO' else
                html.Div([html.Div('Confirmado:',className='imr-label'),_chips(names)]) if state=='SELECCION_CONOCIDA' else None,
            html.Small('Origen: Confirmación operacional'),
            html.Div('Usuario: '+str(active.get('usuario') or 'No disponible')),
            html.Div('Vigente desde: '+_effective_date(active.get('fecha_efectiva') or snapshot['roster'].get('fecha'))),
            html.Div('Fecha consultada: '+_effective_date(snapshot['roster'].get('fecha'))),
            html.Div('Versión: '+str(active['version'])) if active.get('version') is not None else None,
            html.Div('Motivo / fuente: '+str(active.get('justificacion') or 'No disponible')),
            *_documentary_notes(active),
        ],className='imr-confirmation')
    else:
        confirmation=html.Div([html.H6('CONFIRMACIÓN MODULAR'),html.Div('Sin confirmación modular',className='imr-muted')],className='imr-confirmation')
    unknown=not active
    return html.Section([html.H6('MÓDULOS EN RIEGO'),
        html.Div(model.INCOMPATIBLE_MESSAGE,className='imr-warning') if snapshot.get('temporal',{}).get('aplicabilidad')=='ROSTER_INCOMPATIBLE' else None,
        html.Div('Confirmación modular cerrada desde '+_effective_date(snapshot['temporal']['cierre']),className='imr-muted') if snapshot.get('temporal',{}).get('aplicabilidad')=='CERRADA' else None,
        html.Strong('Sin información de módulos en riego.',className='imr-summary') if unknown else None,
        html.Div([confirmation,_reference(snapshot)],className='imr-info-blocks'),
        html.Div([html.Div('Módulos disponibles en la parcela:',className='imr-label'),
            _chips([m['nombre_visible'] or f'Módulo SQL {m["modulo_id"]}' for m in snapshot['roster']['miembros']])
                if snapshot['roster']['miembros'] else html.Div('Roster estructural no resuelto.',className='imr-muted')],className='imr-available'),
    ],className='lix-detail-section imr-shell')


def load_detail(row):
    if not phase_flags.is_dev():return None
    try:return detail(db.modular_snapshot(str(row['fecha'])[:10],int(row['pad_id']),int(row['parcela_id'])))
    except Exception:
        return html.Section([html.H6('MÓDULOS EN RIEGO'),html.P('Información modular no disponible. Actualice el detalle.')],className='lix-detail-section imr-shell')


def history_cards(history):
    if not history:return html.P('Sin confirmaciones modulares para esta fecha.',className='imr-muted')
    result=[]
    latest={};groups={}
    for row in history:
        key=(row.get('campana_id'),str(row['fecha_efectiva'])[:10])
        latest[key]=max(latest.get(key,0),row['version'])
    for row in history:
        names=' · '.join(d['nombre_modulo_snapshot'] or str(d['modulo_id']) for d in row.get('detalle',[]) if d['seleccionado'])
        closed=any(e['tipo_evento']=='CERRAR' for e in row.get('eventos',[]))
        reference=json.loads(row['referencia_snapshot_json']) if row.get('referencia_snapshot_json') else {}
        card=html.Div([
            html.Strong(f'Versión {row["version"]} · {LABELS[row["estado_modular"]]} · '+row.get('situacion_temporal',
                'Cerrada' if closed else 'Supersedida' if row['version']<latest[(row.get('campana_id'),str(row['fecha_efectiva'])[:10])] else 'Vigente')),
            html.Small('Hasta (exclusivo): '+_effective_date(row['vigencia_hasta']),className='d-block') if row.get('vigencia_hasta') else None,
            html.Div(names or ('Ningún módulo' if row['estado_modular']=='NINGUN_MODULO' else 'Sin información')),
            html.Small(f'Fecha efectiva: {row["fecha_efectiva"]} · Cantidad: {row["cantidad_confirmada"] if row["cantidad_confirmada"] is not None else "desconocida"}'),
            html.Div(f'Usuario: {row["usuario"]} · Registro: {row["created_at"]}'),
            html.Div(f'Motivo / fuente: {row["justificacion"]}'),
            html.Div([
                html.Strong('ANULADO'),
                html.Div('Anulado por: '+str(row['anulacion']['actor'])),
                html.Div('Fecha anulación: '+str(row['anulacion'].get('created_at') or row['anulacion'].get('fecha_registro') or 'No disponible')),
                html.Div('Motivo anulación: '+row['anulacion']['motivo']),
                html.Div('Comentario: '+str(json.loads(row['anulacion']['payload_json']).get('observacion') or '')),
            ],className='imr-warning') if row.get('anulacion') else None,
            *_documentary_notes(row),
            html.Small('Referencia: '+str(reference['fuente'])) if reference.get('fuente') else None,
        ],className='imr-history-item')
        key=(row.get('campana_id'),str(row['fecha_efectiva'])[:10])
        if key not in groups:
            groups[key]=html.Section([html.H6('Punto desde '+_effective_date(row['fecha_efectiva']))],className='imr-history-point')
            result.append(groups[key])
        groups[key].children.append(card)
    return result


def editor(snapshot,can_write,history):
    roster=snapshot['roster'];active=snapshot.get('vigente');ref=snapshot.get('referencia')
    suggested=(ref.get('sugeridos') or []) if ref and ref['estado_referencia']=='VALIDA' and ref.get('estructura_actual',True) else []
    ids=[x['modulo_id'] for x in snapshot.get('seleccion',[])] if active else [x['modulo_id'] for x in suggested]
    state=active['estado_modular'] if active else 'SELECCION_CONOCIDA' if ids else None
    editable=can_write and roster['campana_id'] is not None and roster['total'] is not None
    if not can_write:
        return html.Div([detail(snapshot),
            html.Small('Solo lectura',className='imr-readonly-label'),
            html.H6('Historial modular',className='mt-3'),html.Div(history_cards(history)),
        ],className='imr-readonly-view')
    return html.Div([
        detail(snapshot),
        html.Small('El orden es ambiguo: no se genera una sugerencia automática.',className='imr-warning') if not roster['orden_confiable'] else None,
        html.Div([
        html.H6('Editar decisión modular'),
        html.P('Registra una nueva configuración vigente desde esta fecha. Rectificar corrige únicamente el punto de su fecha efectiva original.',className='imr-muted'),
        dbc.Label('Estado modular'),
        dcc.RadioItems(id='imr-state',options=[{'label':v,'value':k,'disabled':not editable} for k,v in LABELS.items()],value=state,className='imr-states'),
        html.Div('Módulos',className='imr-label'),
        dcc.Checklist(id='imr-selection',options=[dict(label=m['nombre_visible'] or f'Módulo SQL {m["modulo_id"]}',value=m['modulo_id'],disabled=not editable) for m in roster['miembros']],value=ids,className='imr-options'),
        html.Div(id='imr-count',className='imr-count'),
        dbc.Label('Motivo / fuente (obligatorio)'),dbc.Textarea(id='imr-motive',maxLength=1000,value='',disabled=not editable,placeholder='Indique la fuente o motivo de la decisión. Ej.: Balance Diario de Pilas 19-10-2026.'),
        html.Div([dbc.Button(label,id='imr-'+key,n_clicks=0,disabled=True,color=color) for key,label,color in (
            ('confirm','Registrar cambio desde '+_effective_date(roster['fecha']) if snapshot.get('temporal',{}).get('heredada') else 'Confirmar módulos','primary'),('rectify','Rectificar módulos','secondary'),('close','Cerrar confirmación modular','secondary'))],className='imr-actions'),
        ],id='imr-form',className='imr-form'),
        dbc.Button('Anular decisión modular',id='imr-annul',n_clicks=0,color='secondary',outline=True,size='sm',
            style={} if snapshot.get('punto_fecha') and not snapshot.get('revision',{}).get('anulada') and not snapshot.get('revision',{}).get('cerrada') else {'display':'none'}),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle('Anular decisión modular')),
            dbc.ModalBody([
                html.P('Esta acción retirará este punto de la línea temporal, pero conservará toda su información para auditoría. Las fechas afectadas volverán a resolverse usando el punto válido anterior, si existe.'),
                dbc.Label('Motivo de anulación (obligatorio)'),
                dcc.Dropdown(id='imr-annul-reason',options=['Registro duplicado','Fecha ingresada por error','No correspondía a un cambio operacional','Otro'],clearable=True,placeholder='Seleccione un motivo'),
                dbc.Label('Comentario adicional'),dbc.Textarea(id='imr-annul-comment',maxLength=2000),
                html.Div(id='imr-annul-feedback'),
            ]),
            dbc.ModalFooter([dbc.Button('Cancelar',id='imr-annul-cancel',n_clicks=0,color='secondary',outline=True),
                dbc.Button('Confirmar anulación',id='imr-annul-confirm',n_clicks=0,color='danger')]),
        ],id='imr-annul-modal',is_open=False),
        html.H6('Historial modular',className='mt-3'),html.Div(history_cards(history)),
    ],className='imr-editor')


def layout():
    return html.Div([html.H5('MÓDULOS EN RIEGO'),
        html.P('Vigencia por puntos de cambio, independiente de la confirmación de fase.',className='imr-muted'),
        dcc.Store(id='imr-preview'),dcc.Store(id='imr-key'),dcc.Store(id='imr-refresh',data=0),
        html.Div(id='imr-editor'),html.Div(id='imr-result',className='mt-2'),
    ],id='imr-shell',className='imr-shell',style={'display':'none'})


@callback(Output('imr-shell','style'),Output('imr-preview','data'),Output('imr-key','data'),Output('imr-editor','children'),
          Input('lix-phase-selected','data'),Input('lix-phase-effective','date'),Input('imr-refresh','data'))
def preview(selected,day,refresh=0):
    if not selected or not day or not phase_flags.is_dev():return {'display':'none'},None,None,None
    try:
        snapshot=db.modular_snapshot(str(day)[:10],int(selected['pad_id']),int(selected['parcela_id']))
        history=db.modular_history(str(day)[:10],int(selected['pad_id']),int(selected['parcela_id']))
        try:db.phase_db._actor();allowed=True
        except (PermissionError,ValueError):allowed=False
        store=json.loads(model.dump(dict(snapshot=snapshot,can_write=allowed)))
        return {},store,str(uuid.uuid4()),editor(snapshot,allowed,history)
    except Exception:
        return {},None,None,dbc.Alert('No se pudo consultar la dimensión modular. Actualice el detalle.',color='warning')


@callback(Output('imr-count','children'),Output('imr-confirm','disabled'),Output('imr-rectify','disabled'),Output('imr-close','disabled'),
          Input('imr-state','value'),Input('imr-selection','value'),Input('imr-motive','value'),State('imr-preview','data'))
def availability(state,ids,motive,preview):
    if not preview:return '',True,True,True
    snapshot=preview['snapshot'];total=snapshot['roster']['total'];allowed=preview['can_write']
    text_count=('Roster estructural no resuelto.' if total is None else
        'Sin información (no equivale a cero).' if state=='SIN_INFORMACION' else
        f'0 de {total} módulos en riego · decisión del formulario, pendiente de guardar.' if state=='NINGUN_MODULO' else
        f'{len(ids or [])} de {total} módulos seleccionados' if state=='SELECCION_CONOCIDA' and allowed else
        'Seleccione un estado modular para editar; todavía no hay una decisión.')
    valid=False
    try:model.selection(snapshot['roster'],state,ids or []);valid=True
    except ValueError:pass
    ready=bool(allowed and motive and str(motive).strip())
    active=snapshot.get('vigente') is not None
    exact=snapshot.get('punto_fecha',snapshot.get('vigente')) is not None
    closed=snapshot.get('revision',{}).get('cerrada',False) or snapshot.get('revision',{}).get('anulada',False)
    temporal=snapshot.get('temporal',{})
    same_cut=temporal.get('aplicabilidad')=='CERRADA' and str(snapshot['roster']['fecha'])<=temporal['cierre']
    return text_count,not(ready and valid and not exact and not same_cut),not(ready and valid and exact and not closed),not(ready and active and not temporal.get('cierre'))


@callback(Output('imr-selection','value'),
          Input('imr-state','value'),State('imr-selection','value'),prevent_initial_call=True)
def reset_selection(state,ids):
    return [] if state in ('NINGUN_MODULO','SIN_INFORMACION') else no_update


@callback(Output('imr-annul-modal','is_open'),Output('imr-annul-feedback','children'),
          Output('imr-result','children',allow_duplicate=True),Output('imr-refresh','data',allow_duplicate=True),
          Input('imr-annul','n_clicks'),Input('imr-annul-cancel','n_clicks'),Input('imr-annul-confirm','n_clicks'),
          State('imr-annul-reason','value'),State('imr-annul-comment','value'),
          State('imr-preview','data'),State('imr-key','data'),State('imr-refresh','data'),prevent_initial_call=True)
def annul_action(open_click,cancel_click,confirm_click,reason,comment,preview,key,refresh):
    if not any((open_click,cancel_click,confirm_click)) or not preview:raise PreventUpdate
    if ctx.triggered_id=='imr-annul-cancel':return False,'',no_update,no_update
    snapshot=preview['snapshot'];revision=snapshot.get('revision',{})
    if not preview.get('can_write') or not snapshot.get('punto_fecha') or revision.get('anulada') or revision.get('cerrada'):
        return False,'',dbc.Alert('Anular requiere un punto propio, no cerrado ni anulado, y autorización operacional.',color='warning'),no_update
    if ctx.triggered_id=='imr-annul':return True,'',no_update,no_update
    if reason not in ('Registro duplicado','Fecha ingresada por error','No correspondía a un cambio operacional','Otro'):
        return True,dbc.Alert('Indique un motivo de anulación.',color='warning'),no_update,no_update
    if reason=='Otro' and not str(comment or '').strip():
        return True,dbc.Alert('Detalle el motivo en el comentario.',color='warning'),no_update,no_update
    roster=snapshot['roster']
    payload=dict(fecha=roster['fecha'],pad_id=roster['pad_id'],parcela_id=roster['parcela_id'],
        motivo=reason,observacion=comment or '',context_token=snapshot['context_token'],idempotency_key=key)
    try:
        db.annul_modules(payload)
        return False,'',dbc.Alert('Punto modular anulado; toda su información permanece en auditoría.',color='success'),(refresh or 0)+1
    except model.StaleContextError:
        return True,dbc.Alert(model.STALE_MESSAGE,color='warning'),no_update,no_update
    except (PermissionError,ValueError) as exc:
        return True,dbc.Alert(str(exc),color='warning'),no_update,no_update
    except Exception:
        return True,dbc.Alert('No se pudo anular. Actualice el detalle antes de reintentar.',color='danger'),no_update,no_update


@callback(Output('imr-selection','options'),Input('imr-state','value'),State('imr-preview','data'))
def selection_options(state,preview):
    if not preview:return []
    disabled=not preview.get('can_write') or state!='SELECCION_CONOCIDA'
    return [dict(label=m['nombre_visible'] or f'Módulo SQL {m["modulo_id"]}',value=m['modulo_id'],disabled=disabled)
            for m in preview['snapshot']['roster']['miembros']]


@callback(Output('imr-result','children'),Output('imr-refresh','data'),
          Input('imr-confirm','n_clicks'),Input('imr-rectify','n_clicks'),Input('imr-close','n_clicks'),
          State('imr-preview','data'),State('imr-key','data'),State('imr-state','value'),State('imr-selection','value'),
          State('imr-motive','value'),State('imr-refresh','data'),prevent_initial_call=True)
def submit(confirm,rectify,close,preview,key,state,ids,motive,refresh):
    if not any((confirm,rectify,close)) or not preview:raise PreventUpdate
    snapshot=preview['snapshot'];roster=snapshot['roster']
    payload=dict(fecha=roster['fecha'],pad_id=roster['pad_id'],parcela_id=roster['parcela_id'],
        estado=state,seleccion=ids or [],motivo=motive,context_token=snapshot['context_token'],idempotency_key=key)
    try:
        actions={'imr-confirm':db.confirm_modules,'imr-rectify':db.rectify_modules,'imr-close':db.close_modules}
        result=actions[ctx.triggered_id](payload)
        return dbc.Alert(f'Decisión modular registrada: {result["id_confirmacion"]}.',color='success'),(refresh or 0)+1
    except model.StaleContextError:
        return dbc.Alert(model.STALE_MESSAGE,color='warning'),no_update
    except (PermissionError,ValueError) as exc:
        return dbc.Alert(str(exc),color='warning'),no_update
    except Exception:
        return dbc.Alert('No se pudo guardar. No reenvíe una selección diferente sin actualizar el detalle.',color='danger'),no_update
