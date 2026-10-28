"""Panel de Balance M6. Preview y confirmación son acciones separadas."""
import hashlib,json,uuid,time,threading,logging
from dash import html,dcc,dash_table,Input,Output,State,callback,clientside_callback,ctx,no_update
from flask import session
import dash_bootstrap_components as dbc
from . import service
from .build_sql import EQUIPOS

log=logging.getLogger(__name__)
_pending={};_lock=threading.Lock();TTL=900
NOTICE='Esta contingencia afecta exclusivamente al Balance de Masa. No modifica Reportabilidad SIIR.'

from . import presentation as ui

def layout():
    from lixiviacion.phase_flags import is_dev
    if not is_dev():return dbc.Alert('Contingencia para Balance de Masa disponible exclusivamente en DEV.',color='secondary')
    return ui.layout()

table=ui.table

EXAMPLE={('2026-10-04','A','SRR_CV003'),('2026-10-04','B','SRR_CV002'),('2026-10-06','A','SRR_CV003'),('2026-10-06','B','SRR_CV002'),('2026-10-08','A','SRR_CV003'),('2026-10-09','B','SRR_CV002'),('2026-10-10','A','SRR_CV003'),('2026-10-12','A','SRR_CV002'),('2026-10-12','A','SRR_CV003')}

@callback(Output('m6ct-raw','data'),Output('m6ct-caso','options'),Output('m6ct-historial','children'),Output('m6ct-carga-estado','children'),Input('m6ct-cargar','n_clicks'),Input('m6ct-refresh','data'),State('m6ct-periodo','start_date'),State('m6ct-ti','value'),State('m6ct-periodo','end_date'),State('m6ct-tf','value'),State('m6ct-equipos','value'),prevent_initial_call=True,
    running=[(Output('m6ct-cargar','disabled'),True,False),
             (Output('m6ct-cargar','children'),ui.query_button(True),ui.query_button()),
             (Output('m6ct-consultando','style'),{}, {'display':'none'}),
             (Output('m6ct-carga-estado','style'),{'display':'none'},{}),
             (Output('m6ct-preview','disabled'),True,False),
             (Output('m6ct-guardar','disabled'),True,False),
             (Output('m6ct-query-loading','display'),'show','hide')])
def load(n,refresh,i,ti,f,tf,e):
    if not session.get('user'):return [],[],[],dbc.Alert('Sesión requerida.',color='danger')
    try:
        rows=service.load_rows(i,ti,f,tf,e)
        cases=service.cases(i,f)
        history=history_table(service.history(i,f))
        manuals=sum(r.get('modo_m6')=='TUM' for r in rows)
        manual_label='manual vigente' if manuals==1 else 'manuales vigentes'
        return ui.decorate(rows),[{'label':f"{r['caso_id']} · {r['nombre_caso']}",'value':r['caso_id']} for r in cases],history,f'{len(rows)} registros consultados: {len(rows)-manuals} AUTO y {manuals} {manual_label}. Marque únicamente los que desea cambiar.'
    except Exception:
        log.exception('Consulta M6 fallida')
        return [],[],[],dbc.Alert('No se pudo consultar DEV. Revise la conexión y la disponibilidad de la selección de fuentes para Balance de Masa.',color='danger')

def history_table(rows):
    fields=[(k,ui.HEADINGS[k]) for k in ['fecha_operacional','turno','equipo_codigo','modo','version','usuario','fecha_registro','motivo','vigente','solicitud_id','comentario','id']]
    return ui.table([{**r,'vigente':'VIGENTE' if r['vigente'] else 'HISTÓRICA'} for r in rows],fields)

@callback(Output('m6ct-fuentes','data'),Output('m6ct-fuentes','tooltip_data'),Input('m6ct-raw','data'))
def filter_rows(rows):
    data=rows or []
    return data,ui.tooltips(data)

@callback(Output('m6ct-fuentes','filter_query'),Input('m6ct-solo-manuales','value'),State('m6ct-fuentes','filter_query'),prevent_initial_call=True)
def manual_filter(manual,query):
    # Dash construye el filtro nativo sobre columnas visibles. La etiqueta MANUAL
    # se deriva exclusivamente de modo_m6 == TUM, sin cambiar ese criterio.
    clause='{modo_visible} contains "MANUAL · "'
    rest=(query or '')
    for known in (clause,'{modo_m6} = "TUM"'):
        prefix=known+' && '
        if rest==known:rest=''
        elif rest.startswith(prefix):rest=rest[len(prefix):]
    prefix=clause+' && '
    return (prefix+rest if rest else clause) if 'SI' in (manual or []) else rest

@callback(Output('m6ct-fuentes','hidden_columns'),Input('m6ct-columnas','value'))
def extra_columns(visible):return [k for k in ui.EXTRA if k not in (visible or [])]

@callback(Output('m6ct-fuentes','selected_rows'),Output('m6ct-fuentes','selected_row_ids'),Input('m6ct-todos','n_clicks'),Input('m6ct-ninguno','n_clicks'),Input('m6ct-raw','data'),State('m6ct-raw','data'),prevent_initial_call=True)
def mark(t,n,changed,rows):
    if ctx.triggered_id=='m6ct-todos':return list(range(len(rows or []))),[r['id'] for r in rows or []]
    return [],[]

def selected_records(rows,selected):
    # Los índices se admiten solo para compatibilidad de llamadas locales antiguas.
    index={ui.row_id(r):r for r in rows or []}
    out=[]
    for key in selected or []:
        if isinstance(key,int):
            if key<0 or key>=len(rows or []):raise ValueError('Selección inválida.')
            key=ui.row_id(rows[key])
        if key not in index:raise ValueError('Selección fuera de la consulta. Consulte nuevamente.')
        if key not in {ui.row_id(r) for r in out}:out.append(index[key])
    return out

@callback(Output('m6ct-resumen','children'),Output('m6ct-seleccion','children'),Input('m6ct-raw','data'),Input('m6ct-fuentes','selected_row_ids'),Input('m6ct-fuentes','derived_virtual_row_ids'))
def summary(rows,selected,visible):
    rows=rows or [];selected=selected or []
    # Una consulta nueva limpia las marcas en otro callback; tolerar ese intervalo.
    ids={ui.row_id(r) for r in rows}
    selected=[k for k in selected if k in ids]
    chosen=selected_records(rows,selected)
    manuals=sum(r.get('modo_m6')=='TUM' for r in rows)
    hidden=len(set(selected)-set(visible if visible is not None else [ui.row_id(r) for r in rows]))
    current=sum(r.get('modo_m6')=='TUM' for r in chosen)
    metrics=[ui.metric('Registros consultados',str(len(rows))),ui.metric('AUTO',str(len(rows)-manuals)),ui.metric('Manuales vigentes',str(manuals)),ui.metric('Seleccionados',str(len(chosen)))]
    message=[html.P(f"Se modificarán {len(chosen)} registros correspondientes a {len({r['equipo_codigo'] for r in chosen})} correas y {len({r['fecha_operacional'] for r in chosen})} fechas operacionales.")]
    if hidden:message.append(dbc.Alert(f'{hidden} registros seleccionados están ocultos por los filtros y se incluirán en la simulación y confirmación.',color='warning'))
    if current:message.append(dbc.Alert(f'{current} registros seleccionados ya tienen una decisión manual vigente. Revise la acción antes de continuar.',color='warning'))
    return metrics,message

def signature(i,ti,f,tf,e,case,rows,selected,mode,motivo,comentario):
    return hashlib.sha256(json.dumps([i,ti,f,tf,sorted(e or []),case,rows,selected,mode,motivo,comentario],sort_keys=True,ensure_ascii=False).encode()).hexdigest()

@callback(Output('m6ct-impacto','children'),Output('m6ct-token','data'),Output('m6ct-estado','children'),Output('m6ct-confirmacion','value'),Output('m6ct-refresh','data'),Input('m6ct-preview','n_clicks'),Input('m6ct-guardar','n_clicks'),
    State('m6ct-periodo','start_date'),State('m6ct-ti','value'),State('m6ct-periodo','end_date'),State('m6ct-tf','value'),State('m6ct-equipos','value'),State('m6ct-caso','value'),State('m6ct-raw','data'),State('m6ct-fuentes','selected_row_ids'),State('m6ct-modo','value'),State('m6ct-motivo','value'),State('m6ct-comentario','value'),State('m6ct-token','data'),State('m6ct-confirmacion','value'),prevent_initial_call=True,
    running=[(Output('m6ct-action-controls','disabled'),True,False),
             (Output('m6ct-action-busy','data'),True,False)])
def handle_action(*args):
    result=act(*args)
    status=result[2]
    refresh=str(uuid.uuid4()) if ctx.triggered_id=='m6ct-guardar' and isinstance(status,dbc.Alert) and status.color=='success' else no_update
    return (*result,refresh)

clientside_callback(
    """function(busy, previewClicks, saveClicks, action) {
        const fired = (dash_clientside.callback_context.triggered || []).map(x => x.prop_id);
        if (saveClicks && fired.includes('m6ct-guardar.n_clicks')) action = 'save';
        else if (previewClicks && fired.includes('m6ct-preview.n_clicks')) action = 'preview';
        const preview = busy && action !== 'save';
        return [preview ? {display:'none'} : {}, preview ? {} : {display:'none'},
            action === 'save' ? 'Guardando decisiones...' : 'Calculando impacto sobre el Balance de Masa...',
            busy ? {} : {display:'none'}, busy ? {display:'none'} : {}, action];
    }""",
    Output('m6ct-preview-idle','style'),Output('m6ct-preview-busy','style'),
    Output('m6ct-action-progress','children'),Output('m6ct-action-progress','style'),
    Output('m6ct-estado','style'),Output('m6ct-action-kind','data'),
    Input('m6ct-action-busy','data'),Input('m6ct-preview','n_clicks'),Input('m6ct-guardar','n_clicks'),
    State('m6ct-action-kind','data'))

def act(p,g,i,ti,f,tf,e,case,rows,selected,mode,motivo,comentario,token,confirmed):
    invalid_impact=html.P('Sin previsualización válida. Revise la selección y vuelva a previsualizar.',className='m6ct-muted') if ctx.triggered_id=='m6ct-preview' else no_update
    user=session.get('user')
    if not user:return invalid_impact,None,dbc.Alert('Sesión autenticada requerida.',color='danger'),[]
    try:
        service.period(i,ti,f,tf,e)
        if not motivo or not motivo.strip():raise ValueError('Indique el motivo antes de previsualizar.')
        selection=selected_records(rows,selected)
        if not selection:raise ValueError('Marque al menos un registro antes de previsualizar o confirmar decisiones.')
        sig=signature(i,ti,f,tf,e,case,rows,selected,mode,motivo,comentario)
        if ctx.triggered_id=='m6ct-preview':
            # Reconstruir claves con datos efectivos de SQL; no confiar en valores del navegador.
            fresh=service.load_rows(i,ti,f,tf,e)
            index={(r['fecha_operacional'],r['turno'],r['equipo_codigo']):j for j,r in enumerate(fresh)}
            chosen=[index[(r['fecha_operacional'],r['turno'],r['equipo_codigo'])] for r in selection]
            keys=service.selection(fresh,chosen,mode)
            result=service.preview(i,f,None if case is None else int(case),keys)
            comparison=result['comparacion']
            newtoken=str(uuid.uuid4())
            with _lock:
                for old in list(_pending):
                    if time.monotonic()-_pending[old]['time']>TTL:del _pending[old]
                _pending[newtoken]={'time':time.monotonic(),'user':user,'signature':sig,'keys':keys,'request':str(uuid.uuid4()),'motivo':motivo,'comentario':comentario,'huella_entradas':result['huella_entradas']}
            source_preview=[]
            for k in keys:
                r=fresh[index[(k['fecha_operacional'],k['turno'],k['equipo_codigo'])]]
                val=r['valor_auto'] if mode=='AUTO' else (0 if r['equipo_codigo'] in ('PRINCIPAL_CV008','PRINCIPAL_CV108') and r['tum_tmh']<=100 else r['tum_tmh'])
                source_preview.append({**{x:r[x] for x in ['fecha_operacional','turno','equipo_codigo','pi_tmh','tum_tmh','valor_auto']},'valor_vigente':r.get('valor_m6'),'modo_propuesto':mode,'valor_propuesto':val,'delta_TMH':val-r['valor_m6'] if val is not None and r.get('valor_m6') is not None else None})
            return ui.impact(comparison,result.get('fuentes_propuestas',source_preview),result.get('auto_vigente'),result.get('auto_propuesto')),newtoken,dbc.Alert('Previsualización completada. Revise el impacto antes de confirmar decisiones.',color='info'),[]
        if 'SI' not in (confirmed or []):raise ValueError('Marque la confirmación explícita antes de guardar.')
        with _lock:
            pending=_pending.get(token)
            if not pending or pending['user']!=user or pending['signature']!=sig or time.monotonic()-pending['time']>TTL:raise ValueError('Preview vencido o selección modificada. Vuelva a previsualizar.')
            # Mantener el token durante el guardado evita dos confirmaciones concurrentes del mismo preview.
            service.persist(pending['keys'],pending['request'],user,pending['motivo'],pending['comentario'],pending['huella_entradas'])
            del _pending[token]
        return no_update,None,dbc.Alert(f"Se guardaron correctamente {len(pending['keys'])} decisiones para Balance de Masa. Se modificó exclusivamente la selección efectiva de fuentes. Los valores PI/TUM originales permanecen intactos. No se recalcularon ni oficializaron reconciliaciones.",color='success'),[]
    except ValueError as ex:return invalid_impact,None,dbc.Alert(str(ex),color='danger'),[]
    except Exception:
        log.exception('Operación M6 fallida')
        return invalid_impact,None,dbc.Alert('No se completó la operación. Las fuentes o decisiones pueden haber cambiado: consulte y previsualice de nuevo.',color='danger'),[]
