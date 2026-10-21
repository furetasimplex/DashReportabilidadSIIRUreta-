"""Ficha V2 y administrador DEV con etiquetas operacionales."""
import json,uuid,logging
from datetime import date,datetime
from zoneinfo import ZoneInfo
from flask import session,has_request_context
from dash import ALL,Input,Output,State,callback,clientside_callback,ctx,dcc,html,no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from . import phase_db,phase_flags
from .phase_model import PHASES,CONDITIONS,ALERTS,STATUSES,REASONS,EVENTS,ADMIN_PHASES,label
from .map_states import ESTADOS,FASES
log=logging.getLogger(__name__)

def when(v):
    if v is None:return 'Sin información'
    try:return date.fromisoformat(str(v)[:10]).strftime('%d-%m-%Y')
    except ValueError:return 'Sin información'
def registered(v):
    if v is None:return 'Sin confirmación'
    try:return datetime.fromisoformat(str(v).replace('Z','+00:00')).strftime('%d-%m-%Y %H:%M:%S UTC')
    except ValueError:return 'Sin información'

def number(v):
    return 'Sin información' if v is None else f'{float(v):,.3f}'.translate(str.maketrans(',.','.,'))
def legacy_label(code):
    return 'Apilado terminado (modelo anterior)' if code=='CONFORMADO' else ESTADOS.get(code,(None,'Sin información'))[1]

def legacy_phase_label(code):
    return 'Apilado terminado (modelo anterior)' if code=='CONFORMADO_PRE_RIEGO' else FASES.get(code,('Sin información',None))[0]

def review_text(row):
    if row.get('override_status')=='CONTRADICHO':
        return ('Se detectó riego posterior a la confirmación operacional. Se requiere revisión.'
                if row.get('fase_administrativa')=='DRENAJE_RESIDUAL' else
                'Se detectó riego o una nueva muestra posterior a la confirmación operacional. Se requiere revisión.')
    if row.get('fase_final')=='MIXTO':return 'Los módulos presentan situaciones diferentes. Revise su detalle.'
    if row.get('sin_cobertura'):return 'La información del día es incompleta; la fase reconocida se conserva.'
    if row.get('proxy_previo_riego'):return 'Existe una muestra anterior al primer riego reconocido; no se utiliza para iniciar Riego continuo.'
    if row.get('revision_requerida'):return 'La evidencia requiere validación operacional.'
    return None


def parcel_review_visible(row, global_missing=()):
    if not row.get('revision_requerida'):return False
    if row.get('proxy_previo_riego') or row.get('fase_final')=='MIXTO' or row.get('override_status')=='CONTRADICHO':return True
    missing={kind for kind,field in [('riego','caudal_operacional'),('quimica','cu_pp')] if row.get(field) is None}
    global_only=(row.get('campana_id') is not None and row.get('motivo_revision_modelo')=='SIN_COBERTURA'
                 and missing and missing.issubset(set(global_missing))
                 and not row.get('motivo_revision_administrativa'))
    return not global_only

def tooltip(row):
    text=[f"Parcela {row['numero_parcela']} · Campaña {row.get('numero_campana') or 'sin información'}",
          'Fase: '+label(row.get('fase_final')),'Condición: '+label(row.get('condicion_dia'),CONDITIONS),
          'Origen: '+('Confirmación operacional' if row.get('origen_fase_final')=='ADMINISTRADOR' else 'Automático')]
    if row.get('dias_sin_riego_confirmados') is not None:
        days=row['dias_sin_riego_confirmados'];text.append('1 día sin riego confirmado' if days==1 else f'{days} días sin riego confirmados')
    if row.get('nivel_alerta') not in (None,'SIN_ALERTA'):text.append(label(row['nivel_alerta'],ALERTS))
    if row.get('revision_requerida'):text+=['⚠ Revisión requerida',review_text(row)]
    return '\n'.join(x for x in text if x)

def module_table(row):
    try:modules=json.loads(row.get('detalle_modulos') or '[]')
    except (TypeError,ValueError):modules=[]
    structural={'DISPONIBLE':'Apilado terminado','NO_EVALUABLE':'Información pendiente'}
    return html.Div([html.Small('Desplace la tabla horizontalmente para consultar todas las fechas.',className='lix-v2-scroll-hint'),html.Div(html.Table([
        html.Thead(html.Tr([html.Th(x) for x in ('Módulo','Situación','Inicio apilado','Fin apilado','Inicio retiro','Fin retiro')])),
        html.Tbody([html.Tr([html.Td(m.get('nombre_modulo') or str(m.get('modulo_id'))),
            html.Td(structural.get(m.get('estado_estructural'),label(m.get('estado_estructural')))),
            *[html.Td(when(m.get(k))) for k in ('fecha_ini_carguio','fecha_fin_carguio','fecha_ini_retiro','fecha_fin_retiro')]]) for m in modules])
    ],className='table table-sm lix-v2-modules'),className='lix-v2-scroll lix-v2-module-scroll',
       role='region',tabIndex=0,**{'aria-label':'Módulos e hitos'})])

def fields(items):
    return html.Dl([html.Div([html.Dt(k),html.Dd('Sin información' if v is None else str(v))]) for k,v in items],className='lix-detail-grid')

def detail(row):
    origin='Confirmación operacional' if row.get('origen_fase_final')=='ADMINISTRADOR' else 'Automático'
    legacy=legacy_label(row.get('estado_operacional_SQL_original'))
    sections=[('Identificación',[('PAD',row['nombre_pad']),('Parcela',row['numero_parcela']),('Campaña',row.get('numero_campana')),('Fecha',when(row['fecha']))]),
              ('Fase',[('Fase calculada',label(row['fase_calculada_modelo'])),('Origen',origin)]),
              ('Condición',[('Condición diaria',label(row['condicion_dia'],CONDITIONS)),('Alerta',label(row['nivel_alerta'],ALERTS)),('Días sin riego confirmados',row.get('dias_sin_riego_confirmados'))]),
              ('Riego',[('Caudal real [m³/h]',number(row.get('caudal_operacional'))),('Último riego real',when(row.get('fecha_ultimo_riego_real'))),('Primer riego reconocido',when(row.get('fecha_primer_riego_reconocido')))]),
              ('Drenaje',[('Cu++ drenaje',number(row.get('cu_pp'))),('Último Cu++ positivo',when(row.get('fecha_ultima_ley_cu_pp'))),('Primer aporte reconocido',when(row.get('fecha_primer_cu_pp_valido')))]),
              ('Modelo anterior',[('Fase del modelo anterior',legacy_phase_label(row.get('fase_visual_legacy'))),('Estado del modelo anterior',legacy)]),
              ('Confirmación',[('Fase confirmada',label(row.get('fase_administrativa')) if row.get('fase_administrativa') else 'Sin confirmación'),('Situación',label(row.get('override_status'),STATUSES) if row.get('override_id') else 'Sin confirmación'),('Usuario',row.get('usuario_creacion')),('Fecha efectiva',when(row.get('override_desde'))),('Registro',registered(row.get('fecha_creacion'))),('Motivo',row.get('motivo_texto'))])]
    warnings=[review_text(row)]
    if row.get('proxy_previo_riego'):
        warnings.append('Existe una muestra anterior al primer riego reconocido; no se utiliza para iniciar Riego continuo.')
    if row.get('sin_cobertura'):
        warnings.append('La información del día es incompleta; la fase reconocida se conserva.')
    warnings=list(dict.fromkeys(x for x in warnings if x))
    secondary=row.get('fase_final')=='RECLAMADO' and warnings==['La información del día es incompleta; la fase reconocida se conserva.']
    return html.Div([html.Div([html.Small('Fase estructural'),html.H4(label(row['fase_final']))],className='lix-v2-phase-heading'),
        dbc.Alert([html.Div(w) for w in warnings],color='light' if secondary else 'warning',className='lix-v2-review-secondary' if secondary else '') if warnings else None,
        *[html.Section([html.H6(title),fields(items),html.P('Indicador químico de aporte/drenaje; no corresponde a caudal hidráulico medido.',className='small text-muted') if title=='Drenaje' else None],className='lix-detail-section') for title,items in sections],
        html.Section([html.H6('Módulos e hitos'),module_table(row)],className='lix-detail-section'),
        html.P('Puede revisar el historial y gestionar una confirmación debajo del mapa.',className='small text-muted')])

def confirmation_summary(row,revision):
    """Contexto de decisión; la evidencia completa permanece en el drawer."""
    notices=[]
    mixed=row.get('fase_calculada_modelo')=='MIXTO' or row.get('fase_final')=='MIXTO'
    structural=mixed or row.get('override_status')=='APARTADO_ESTRUCTURA'
    if mixed:
        try:count=len(json.loads(row.get('detalle_modulos') or '[]'))
        except (TypeError,ValueError):count=0
        notices.append(html.P(f'Módulos con situaciones diferentes: {count}' if count else 'Los módulos presentan situaciones diferentes.',className='lix-confirm-notice'))
    elif structural:
        notices.append(html.P('Confirmación apartada por situación de módulos.',className='lix-confirm-notice'))
    if row.get('override_status')=='CONTRADICHO':
        notices.append(dbc.Alert([html.Div(review_text(row)),html.Small(
            'Evidencia: último riego '+when(row.get('fecha_ultimo_riego_real'))+
            ' · última muestra positiva '+when(row.get('fecha_ultima_ley_cu_pp')))],color='warning',className='small'))
    if row.get('proxy_previo_riego'):
        notices.append(html.P('Existe una muestra anterior al primer riego reconocido; no se utiliza para iniciar Riego continuo.',className='lix-confirm-notice'))
    active=phase_db.administrative_context(row,revision)['active']
    current=html.Section([html.H6('Confirmación vigente'),fields([
        ('Fase confirmada',label(row.get('fase_administrativa'))),('Fecha efectiva',when(row.get('override_desde'))),
        ('Usuario',row.get('usuario_creacion')),('Motivo',row.get('motivo_texto')),
        ('Estado','Contradicho · '+label(row.get('override_status'),STATUSES) if row.get('override_status')=='CONTRADICHO' else label(row.get('override_status'),STATUSES))
    ])],className='lix-confirm-current') if active else None
    return html.Div([
        html.Dl([
            html.Div([html.Dt('Fase automática actual'),html.Dd(label(row.get('fase_calculada_modelo')))],className='lix-confirm-auto'),
            html.Div([html.Dt('Condición actual'),html.Dd(label(row.get('condicion_dia'),CONDITIONS))]),
            html.Div([html.Dt('Alerta'),html.Dd(label(row.get('nivel_alerta'),ALERTS))]),
            html.Div([html.Dt('Modelo anterior'),html.Dd(legacy_phase_label(row.get('fase_visual_legacy')),
                title='Estado del modelo anterior: '+legacy_label(row.get('estado_operacional_SQL_original')))]),
        ],className='lix-confirm-summary-grid'),
        *notices,
        html.Div([dbc.Button('Ver detalle operacional',id={'type':'lix-phase-open-detail','section':'overview'},n_clicks=0,color='link',size='sm'),
            dbc.Button('Ver módulos e hitos',id={'type':'lix-phase-open-detail','section':'modules'},n_clicks=0,color='link',size='sm') if structural else None],className='lix-confirm-links'),
        current,
    ],className='lix-confirm-summary')


def layout():
    return html.Div([
        dcc.Store(id='lix-phase-selected'),dcc.Store(id='lix-phase-preview'),dcc.Store(id='lix-phase-key'),dcc.Store(id='lix-phase-refresh',data=0),dcc.Store(id='lix-phase-detail-focus'),
        html.Div([
          html.H5('Confirmación operacional'),html.Div(id='lix-phase-identity'),
          html.Div(id='lix-phase-evidence'),html.Div(id='lix-phase-preview-error'),
          html.H6('Confirmación',className='lix-confirm-form-title'),
          html.Div([dbc.Row([
            dbc.Col([dbc.Label('Fase a confirmar'),dcc.Dropdown(id='lix-phase-choice',options=[{'value':x,'label':label(x)} for x in ADMIN_PHASES],value=None,placeholder='Seleccione una fase',clearable=True,disabled=True)],md=4),
            dbc.Col([dbc.Label('Fecha efectiva'),dcc.DatePickerSingle(id='lix-phase-effective',date=None,display_format='DD-MM-YYYY',max_date_allowed=datetime.now(ZoneInfo('America/Santiago')).date(),disabled=True)],md=4),
            dbc.Col([dbc.Label('Motivo'),dcc.Dropdown(id='lix-phase-reason',options=[{'value':x,'label':label(x,REASONS)} for x in REASONS],value=None,placeholder='Seleccione un motivo',clearable=True,disabled=True)],md=4),
          ],className='g-3 mb-3'),
          dbc.Label('Justificación del motivo (obligatoria)'),dbc.Textarea(id='lix-phase-motive',placeholder='Describa la confirmación o la corrección realizada.',maxLength=1000,className='mb-2',disabled=True),
          dbc.Label('Observación'),dbc.Textarea(id='lix-phase-observation',maxLength=2000,className='mb-2',disabled=True),
          dbc.Label('Evidencia o referencia (opcional)'),dbc.Input(id='lix-phase-reference',maxLength=1000,className='mb-3',disabled=True),
          html.Div(id='lix-phase-drain-reference'),
          ],id='lix-phase-form',className='lix-confirm-form is-readonly'),
          html.Div([dbc.Button(title,id='lix-phase-'+key,n_clicks=0,color=color,disabled=True) for key,title,color in [('confirm','Confirmar fase','primary'),('rectify','Rectificar','secondary'),('close','Cerrar confirmación','secondary'),('resolve','Resolver contradicción','warning')]],className='lix-v2-actions'),
          html.Div(id='lix-phase-result',className='mt-3'),html.H6('Historial de decisiones',className='mt-4'),html.Div(id='lix-phase-history'),
        ],id='lix-phase-admin',style={'display':'none'},className='lix-v2-admin')
    ])

clientside_callback("""function(clicks,ids){
    const context=window.dash_clientside.callback_context;
    if(!context.triggered.length)return window.dash_clientside.no_update;
    let id;try{id=JSON.parse(context.triggered[0].prop_id.split('.n_clicks')[0]);}catch(e){return window.dash_clientside.no_update;}
    const i=(ids||[]).findIndex(x=>x.section===id.section);
    if(id.section!=='modules'||!(clicks||[])[i])return window.dash_clientside.no_update;
    let tries=0;
    function focusModules(){
        const table=document.querySelector('#lix-map-modal.show .lix-v2-module-scroll');
        if(table){table.scrollIntoView({block:'center'});table.focus({preventScroll:true});}
        else if(++tries<30)setTimeout(focusModules,100);
    }
    setTimeout(focusModules,150);
    return {section:'modules',click:clicks[i]};
}""",Output('lix-phase-detail-focus','data'),Input({'type':'lix-phase-open-detail','section':ALL},'n_clicks'),
    State({'type':'lix-phase-open-detail','section':ALL},'id'),prevent_initial_call=True)


def history_table(decisions,events):
    if not decisions:return html.P('Sin confirmaciones registradas para esta campaña.',className='text-muted small')
    versions=[html.Li([html.Strong('Versión '+str(o['version'])+' · '+label(o['fase_administrativa'])),fields([
        ('Fecha efectiva',when(o['fecha_desde'])),('Registro',registered(o['fecha_creacion'])),
        ('Usuario',o['usuario_creacion']),('Motivo',o['motivo_texto']),
        *([('Referencia fin drenaje',when(o.get('fecha_fin_drenaje_referencia'))),('Cu++ de referencia',number(o.get('ultima_ley_cu_pp_al_confirmar')))] if o['fase_administrativa']=='ESPERA_RECLAMO' else [])
    ])],className='lix-confirm-history-item') for o in decisions]
    event_items=[html.Li([html.Strong(label(ev['tipo_evento'],EVENTS)),fields([
        ('Fecha efectiva',when(ev['fecha_efectiva'])),('Registro',registered(ev['fecha_registro'])),('Usuario',ev['actor']),('Motivo',ev['motivo'])
    ])],className='lix-confirm-history-item') for ev in events]
    return html.Div([html.Ol(versions),html.H6('Eventos'),html.Ol(event_items)],className='lix-confirm-history')

@callback(Output('lix-phase-selected','data'),Output('lix-phase-effective','date'),
 Input({'type':'lix-parcel','pad':ALL,'parcel':ALL},'n_clicks'),Input('lix-map-date','date'),Input('lix-map-pad','value'),Input('lix-tabs','active_tab'),Input('lix-map-data','data'),State('lix-phase-selected','data'),prevent_initial_call=True)
def select_parcel(clicks,day,pad,tab,data,prior=None):
    trigger=ctx.triggered_id
    if (trigger=='lix-map-data' or isinstance(trigger,dict) and not any(clicks or [])) and prior and data and data.get('model')=='v2' and data.get('fecha')==day:
        row=next((r for r in data['rows'] if r['pad_id']==prior['pad_id'] and r['parcela_id']==prior['parcela_id'] and r['campana_id']==prior['campana_id']),None)
        if row:return prior,no_update
    if not isinstance(trigger,dict) or not any(clicks or []) or not data or data.get('model')!='v2':return None,None
    row=next((r for r in data['rows'] if r['pad_id']==trigger['pad'] and r['parcela_id']==trigger['parcel']),None)
    return ({'pad_id':row['pad_id'],'parcela_id':row['parcela_id'],'campana_id':row['campana_id']},day) if row else (None,None)

@callback(Output('lix-phase-admin','style'),Output('lix-phase-identity','children'),Output('lix-phase-preview','data'),Output('lix-phase-key','data'),
 Output('lix-phase-evidence','children'),Output('lix-phase-history','children'),Output('lix-phase-preview-error','children'),
 Input('lix-phase-selected','data'),Input('lix-phase-effective','date'),Input('lix-phase-refresh','data'))
def preview_admin(selected,effective,refresh):
    empty=({'display':'none'},None,None,None,None,None,None)
    if not selected or not effective or not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):return empty
    try:
        evidence=phase_db.preview(effective,selected['pad_id'],selected['parcela_id']);r=evidence['row']
        if r['campana_id']!=selected['campana_id']:raise ValueError('La fecha pertenece a otra campaña; seleccione nuevamente la parcela.')
        decisions,events=phase_db.history(r['pad_id'],r['parcela_id'],r['campana_id'])
        identity=html.Div([html.Span(f"{r['nombre_pad']} · Parcela {r['numero_parcela']} · Campaña {r['numero_campana']}"),html.Span('Fecha operacional: '+when(r['fecha']))],className='lix-confirm-identity')
        try:phase_db._actor();can_write=True
        except PermissionError:can_write=False
        warning=html.Div(dbc.Alert('Modo solo lectura: puede revisar confirmaciones, pero esta sesión no tiene permiso para registrar cambios.',color='light',className='lix-confirm-readonly-notice'),role='status') if not can_write else None
        # El snapshot completo se conserva en servidor; el Store es solo token y evidencia de revisión.
        data=json.loads(phase_db.dump(evidence))
        data['ui_can_write']=can_write
        return ({'display':'block'},identity,data,str(uuid.uuid4()),confirmation_summary(phase_db.clean(r),evidence['revision']),history_table(decisions,events),warning)
    except Exception as exc:
        log.warning('Evidencia administrativa no disponible (%s)',type(exc).__name__)
        return ({'display':'block'},None,None,None,None,None,dbc.Alert(str(exc) if isinstance(exc,(ValueError,PermissionError)) else 'No fue posible consultar la evidencia.',color='warning'))


@callback(Output('lix-phase-choice','value'),Output('lix-phase-reason','value'),Output('lix-phase-motive','value'),
          Output('lix-phase-observation','value'),Output('lix-phase-reference','value'),Input('lix-phase-selected','data'))
def reset_admin_form(selected):
    return None,None,'','',''


@callback(*[Output('lix-phase-'+key,'disabled') for key in ('choice','effective','reason','motive','observation','reference')],
          Output('lix-phase-form','className'),Input('lix-phase-preview','data'))
def form_editability(preview):
    """Solo presentación: reutiliza el permiso ya calculado, sin autorizar acciones."""
    disabled=not preview or preview.get('ui_can_write') is not True
    return (disabled,)*6+('lix-confirm-form is-readonly' if disabled else 'lix-confirm-form',)


@callback(Output('lix-phase-confirm','disabled'),Output('lix-phase-rectify','disabled'),
          Output('lix-phase-close','disabled'),Output('lix-phase-resolve','disabled'),
          Input('lix-phase-preview','data'),Input('lix-phase-choice','value'),Input('lix-phase-reason','value'),
          Input('lix-phase-motive','value'),Input('lix-phase-effective','date'))
def action_buttons(preview,phase,reason,motive,effective):
    if not preview or preview.get('ui_can_write') is not True:return True,True,True,True
    row=preview['row']
    try:
        effective_day=date.fromisoformat(str(effective))
        valid_date=effective_day<=datetime.now(ZoneInfo('America/Santiago')).date() and str(row['fecha'])[:10]==str(effective)
    except (TypeError,ValueError):valid_date=False
    valid=valid_date and reason in REASONS and isinstance(motive,str) and bool(motive.strip()) and len(motive.strip())<=1000
    complete=valid and phase in ADMIN_PHASES
    context=phase_db.administrative_context(row,preview['revision'])
    compatible=context['compatible'] and row.get('override_status')!='CONFLICTO_OVERRIDE'
    return (not(complete and compatible),not(complete and compatible and context['active']),
            not(valid and context['active']),not(complete and compatible and context['contradiction']))


@callback(Output('lix-phase-drain-reference','children'),Input('lix-phase-choice','value'),Input('lix-phase-preview','data'))
def drain_reference(phase,preview):
    if phase!='ESPERA_RECLAMO' or not preview:return None
    row=preview['row'];when_sample=when(row.get('fecha_ultima_ley_cu_pp'))
    return dbc.Alert('Referencia de fin de drenaje: '+when_sample+' · Cu++: '+number(row.get('valor_ultima_ley_cu_pp'))+'. Última ley positiva disponible hasta la fecha efectiva; se conservará al confirmar.',color='light',className='small')

@callback(Output('lix-phase-result','children'),Output('lix-phase-refresh','data'),
 Input('lix-phase-confirm','n_clicks'),Input('lix-phase-rectify','n_clicks'),Input('lix-phase-close','n_clicks'),Input('lix-phase-resolve','n_clicks'),
 State('lix-phase-preview','data'),State('lix-phase-key','data'),State('lix-phase-choice','value'),State('lix-phase-reason','value'),State('lix-phase-motive','value'),State('lix-phase-observation','value'),State('lix-phase-reference','value'),State('lix-phase-refresh','data'),prevent_initial_call=True)
def submit(confirm,rectify,close,resolve,preview,key,phase,reason,motive,observation,reference,refresh):
    actions={'lix-phase-confirm':'CONFIRMAR','lix-phase-rectify':'RECTIFICAR','lix-phase-close':'CERRAR','lix-phase-resolve':'RESOLVER_CONTRADICCION'}
    action=actions.get(ctx.triggered_id)
    if not action or not preview:raise PreventUpdate
    row=preview['row']
    payload={'accion':action,'fase':phase,'motivo_codigo':reason,'motivo_texto':motive,'observacion':observation,'referencia':reference,
             'fecha_desde':row['fecha'],'pad_id':row['pad_id'],'parcela_id':row['parcela_id'],'campana_id':row['campana_id'],
             'override_id':preview['revision']['decision'],'context_token':preview['context_token'],'revision':preview['revision'],'idempotency_key':key}
    try:
        phase_db.decide(payload)
        return dbc.Alert('Confirmación registrada. El historial se conserva.',color='success'),(refresh or 0)+1
    except (ValueError,PermissionError) as exc:return dbc.Alert(str(exc),color='warning'),no_update
    except Exception as exc:
        log.exception('No se registró la confirmación (%s)',type(exc).__name__)
        return dbc.Alert('No se registró la confirmación. Actualice la evidencia e intente nuevamente.',color='danger'),no_update

@callback(Output('lix-phase-diagnostic','children'),Input('lix-aplicado','data'))
def diagnostic(filters):
    if not filters or not phase_flags.enabled('ENABLE_PHASE_MODEL_V2'):return None
    try:
        rows=phase_db.snapshot(filters['hasta'])
        rows=[r for r in rows if (filters.get('pad') is None or r['pad_id']==filters['pad']) and (filters.get('parcela') is None or r['parcela_id']==filters['parcela'])]
        headings=['PAD','Parcela','Campaña','Estado anterior','Fase del modelo anterior','Fase calculada','Fase confirmada','Fase final','Origen','Condición','Alerta','Días sin riego','Primer riego','Primer aporte','Último riego','Última ley','Proxy previo','Transición mismo día','Información incompleta','Mixto','Contradicción','Versión modelo','Versión alerta']
        values=[]
        for r in rows:
            values.append([r['nombre_pad'],r['numero_parcela'],r['numero_campana'],legacy_label(r['estado_operacional_SQL_original']),legacy_phase_label(r.get('fase_visual_legacy')),
              label(r['fase_calculada_modelo']),label(r['fase_administrativa']) if r['fase_administrativa'] else 'Sin confirmación',label(r['fase_final']),
              'Confirmación operacional' if r['origen_fase_final']=='ADMINISTRADOR' else 'Automático',label(r['condicion_dia'],CONDITIONS),label(r['nivel_alerta'],ALERTS),r['dias_sin_riego_confirmados'],
              *[when(r[x]) for x in ('fecha_primer_riego_reconocido','fecha_primer_cu_pp_valido','fecha_ultimo_riego_real','fecha_ultima_ley_cu_pp')],
              *['Sí' if v else 'No' for v in (r['proxy_previo_riego'],r['transicion_mismo_dia'],r['sin_cobertura'],r['fase_calculada_modelo']=='MIXTO',r['override_status']=='CONTRADICHO')],r['version_modelo'],r['version_alerta']])
        options=[{'value':str(i),'label':f"{r['nombre_pad']} · P{r['numero_parcela']} · C{r.get('numero_campana') or '—'} · {when(r['fecha'])}"} for i,r in enumerate(rows)]
        return dbc.Card(dbc.CardBody([
            html.H5('Comparación puntual V2 / modelo anterior'),
            html.P('Fotografía V2 al '+when(filters['hasta'])+' · valores anteriores conservados.',className='small text-muted'),
            dcc.Store(id='lix-v2-diagnostic-rows',data=json.loads(phase_db.dump(rows))),
            dcc.Dropdown(id='lix-v2-diagnostic-case',options=options,value=None,
                         placeholder='Seleccione un caso',clearable=True,maxHeight=240),
            html.Div(id='lix-v2-diagnostic-detail'),
            html.Details([html.Summary('Ver comparación completa'),html.Div(html.Table([
                html.Thead(html.Tr([html.Th(x) for x in headings])),
                html.Tbody([html.Tr([html.Td('Sin información' if v is None else str(v)) for v in r]) for r in values])
            ],className='table table-sm'),className='lix-v2-scroll')],open=False),
        ]),className='mb-3')
    except Exception as exc:
        log.warning('Diagnóstico V2 no disponible (%s)',type(exc).__name__)
        return dbc.Alert('La comparación operacional nueva no está disponible. El diagnóstico anterior permanece disponible.',color='warning')


@callback(Output('lix-v2-diagnostic-detail','children'),Input('lix-v2-diagnostic-case','value'),State('lix-v2-diagnostic-rows','data'))
def diagnostic_case(selected,rows):
    if selected is None or not rows:return None
    try:row=rows[int(selected)]
    except (ValueError,IndexError,TypeError):return None
    return html.Div([html.P('Resultado calculado: '+label(row['fase_final'])+' · '+label(row['condicion_dia'],CONDITIONS),className='small mt-2'),
        html.P('Modelo anterior: '+legacy_phase_label(row.get('fase_visual_legacy'))+' · '+legacy_label(row.get('estado_operacional_SQL_original')),className='small'),
        html.Details([html.Summary('Ver detalle operacional completo'),detail(row)],open=False)])
