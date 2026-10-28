"""UX/cobertura y permisos: sin SQL real ni registros administrativos."""
import copy,json,uuid
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch,MagicMock
import pytest
from flask import Flask,session,request
import auth
from . import phase_db,phase_panel,map_panel,map_db
from .test_map import text_content

def row(**kw):
    return dict(fecha='2026-10-15',nombre_pad='Óxidos',pad_id=1,parcela_id=24,numero_parcela=24,
        campana_id=1,numero_campana=18,fase_final='RIEGO_CONTINUO',fase_calculada_modelo='RIEGO_CONTINUO',
        condicion_dia='SIN_COBERTURA',nivel_alerta='SIN_COBERTURA',caudal_operacional=None,cu_pp=None,
        revision_requerida=1,motivo_revision_modelo='SIN_COBERTURA',sin_cobertura=1,override_status=None,
        override_id=None,consolidacion_modulos='UNANIME',estructura_unica='DISPONIBLE',retiro_fisico=0,**kw)

def components(c):
    if isinstance(c,list):
        for child in c:yield from components(child)
    elif hasattr(c,'to_plotly_json'):
        yield c;yield from components(getattr(c,'children',None))

def test_initial_form_empty_and_reset_on_campaign_change():
    c={getattr(x,'id',None):x for x in components(phase_panel.layout()) if isinstance(getattr(x,'id',None),str)}
    assert c['lix-phase-choice'].value is None and c['lix-phase-reason'].value is None
    assert all(getattr(c['lix-phase-'+key],'value',None) in ('',None) for key in ['motive','observation','reference'])
    assert phase_panel.reset_admin_form({'campana_id':9})==(None,None,'','','')

def preview(**kw):return {'row':dict(row(),**kw),'revision':{'decision':kw.get('override_id') or 0},'ui_can_write':True}

@pytest.mark.parametrize('phase,reason,motive,effective',[(None,'OTRO','texto','2026-10-15'),('HUMECTACION',None,'texto','2026-10-15'),('HUMECTACION','OTRO','   ','2026-10-15'),('HUMECTACION','OTRO','texto','mal'),('HUMECTACION','OTRO','texto','2100-01-01')])
def test_buttons_incomplete(phase,reason,motive,effective):
    assert phase_panel.action_buttons(preview(),phase,reason,motive,effective)==(True,True,True,True)

def test_buttons_require_real_prior_and_pending_contradiction():
    args=('HUMECTACION','OTRO','Justificación','2026-10-15')
    assert phase_panel.action_buttons(preview(),*args)==(False,True,True,True)
    assert phase_panel.action_buttons(preview(override_id=9,override_status='VIGENTE'),*args)==(False,False,False,True)
    assert phase_panel.action_buttons(preview(override_id=9,override_status='CONTRADICHO'),*args)==(False,False,False,False)
    assert phase_panel.action_buttons(preview(override_id=9,override_status='CERRADO_MANUAL'),*args)==(False,True,True,True)
    p=preview();p['ui_can_write']=False
    assert phase_panel.action_buttons(p,*args)==(True,True,True,True)

@pytest.mark.parametrize('field,value',[('fase',None),('motivo_codigo',None),('motivo_texto','  '),('fecha_desde','mal')])
def test_backend_rejects_incomplete_before_transaction(field,value):
    p={'accion':'CONFIRMAR','fase':'HUMECTACION','motivo_codigo':'OTRO','motivo_texto':'Justificación','fecha_desde':'2026-10-15'}
    p[field]=value
    with patch.object(phase_db,'_actor',return_value='qa'),patch.object(phase_db,'_transaction') as tx:
        with pytest.raises(ValueError):phase_db.decide(p)
    tx.assert_not_called()

@pytest.mark.parametrize('action',['CONFIRMAR','RECTIFICAR','CERRAR','RESOLVER_CONTRADICCION'])
def test_direct_http_unauthorized_user_cannot_write(action):
    app=Flask(__name__);app.secret_key='fixture-only'
    @app.post('/test-admin-action')
    def endpoint():
        try:phase_db.decide(request.json)
        except PermissionError:return '',403
        return '',500
    client=app.test_client()
    with client.session_transaction() as s:s['user']='ordinary'
    with patch.object(phase_db.phase_flags,'enabled',return_value=True),patch.object(auth,'user_can_write_operational_decisions',return_value=False) as permission,patch.object(phase_db,'_transaction') as tx:
        assert client.post('/test-admin-action',json={'accion':action}).status_code==403
    permission.assert_called_once_with('ordinary');tx.assert_not_called()


@pytest.mark.parametrize('button',['confirm','rectify','close','resolve'])
def test_real_dash_endpoint_rejects_unauthorized_user_with_forged_ui_permission(button):
    from dash import Dash,Input,Output,State
    app=Dash(__name__);app.server.secret_key='fixture-only'
    app.layout=phase_panel.layout()
    app.callback(Output('lix-phase-result','children'),Output('lix-phase-refresh','data'),
        *[Input('lix-phase-'+key,'n_clicks') for key in ['confirm','rectify','close','resolve']],
        *[State('lix-phase-'+key,prop) for key,prop in [('preview','data'),('key','data'),('choice','value'),('reason','value'),('motive','value'),('observation','value'),('reference','value'),('refresh','data')]],
        prevent_initial_call=True)(phase_panel.submit)
    client=app.server.test_client()
    with client.session_transaction() as s:s['user']='ordinary'
    states=[preview(),str(uuid.uuid4()),'HUMECTACION','OTRO','Justificación','','',0]
    p=states[0];p.update(context_token='forged');p['revision'].update(evento=0)
    keys=[('preview','data'),('key','data'),('choice','value'),('reason','value'),('motive','value'),('observation','value'),('reference','value'),('refresh','data')]
    with patch.object(phase_db.phase_flags,'enabled',return_value=True),patch.object(auth,'user_can_write_operational_decisions',return_value=False) as permission,patch.object(phase_db,'_transaction') as tx:
        result=client.post('/_dash-update-component',json={
            'output':'..lix-phase-result.children...lix-phase-refresh.data..',
            'outputs':[dict(id='lix-phase-result',property='children'),dict(id='lix-phase-refresh',property='data')],
            'changedPropIds':['lix-phase-'+button+'.n_clicks'],
            'inputs':[dict(id='lix-phase-'+key,property='n_clicks',value=int(key==button)) for key in ['confirm','rectify','close','resolve']],
            'state':[dict(id='lix-phase-'+key,property=prop,value=value) for (key,prop),value in zip(keys,states)]})
    assert result.status_code==200
    assert 'usuario activo con permiso' in result.get_data(as_text=True)
    permission.assert_called_once_with('ordinary');tx.assert_not_called()

@pytest.mark.parametrize('admin',[0,1,None])
def test_admin_permission_comes_from_existing_django_flags(admin):
    engine=MagicMock();connection=engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar.return_value=admin
    with patch.object(auth,'get_engine',return_value=engine):assert auth.user_is_admin('alice') is (admin==1)
    sql=str(connection.execute.call_args.args[0])
    assert 'is_active=1' in sql and 'is_staff=1 OR is_superuser=1' in sql
    assert connection.execute.call_args.args[1]=={'u':'alice'}

def test_permission_query_failure_denies():
    with patch.object(auth,'get_engine',side_effect=RuntimeError('no disponible')):assert not auth.user_is_admin('alice')

@pytest.mark.parametrize('action,status,prior',[('RECTIFICAR',None,False),('CERRAR','FINALIZADO',True),('RESOLVER_CONTRADICCION','VIGENTE',True)])
def test_backend_rechecks_active_decision_before_any_write(action,status,prior):
    r=dict(row(),override_id=9 if prior else None,override_status=status)
    revision={'decision':9 if prior else 0,'evento':0}
    latest={'id_override':9,'version':1,'familia_override_id':str(uuid.uuid4())} if prior else None
    conn=MagicMock();conn.execute.return_value.mappings.return_value.first.return_value=None
    conn.execute.return_value.scalar_one.return_value=None
    @contextmanager
    def transaction():yield conn
    payload={'accion':action,'fase':'HUMECTACION','motivo_codigo':'OTRO','motivo_texto':'Justificación',
             'fecha_desde':'2026-10-15','pad_id':1,'parcela_id':24,'campana_id':1,'idempotency_key':str(uuid.uuid4()),
             'revision':revision,'context_token':'token','override_id':9 if prior else None}
    with patch.object(phase_db,'_actor',return_value='qa'),patch.object(phase_db,'_transaction',transaction),patch.object(phase_db,'_revision',return_value=(revision,latest)),patch.object(phase_db,'_row',return_value=r),patch.object(phase_db,'_fingerprint',return_value='token'),patch.object(phase_db,'_event') as event:
        with pytest.raises(ValueError):phase_db.decide(payload)
    event.assert_not_called()
    assert all(str(call.args[0]).lstrip().startswith('SELECT') for call in conn.execute.call_args_list)

def test_permission_is_rechecked_not_cached_in_session():
    app=Flask(__name__);app.secret_key='fixture-only'
    with app.test_request_context('/',method='POST'),patch.object(phase_db.phase_flags,'enabled',return_value=True),patch.object(auth,'user_can_write_operational_decisions',side_effect=[True,False]):
        session['user']='admin'
        assert phase_db._actor()=='admin'
        with pytest.raises(PermissionError):phase_db._actor()

def test_missing_is_not_zero_in_drawer_and_no_data_is_mutated():
    absent=row();zero=dict(absent,caudal_operacional=0,cu_pp=0,dias_sin_riego_confirmados=123)
    before=copy.deepcopy(zero)
    a,b=text_content(phase_panel.detail(absent)),text_content(phase_panel.detail(zero))
    assert 'Sin información' in a and '0,000' in b and '123' in b
    assert zero==before and absent['caudal_operacional'] is None
    assert 'Cu++ drenaje' in b and 'Último Cu++ positivo' in b
    assert ('Estado del modelo anterior' in b) is (not phase_panel.phase_flags.is_dev())

def test_global_gap_suppresses_only_redundant_parcel_warning():
    r=row()
    assert not phase_panel.parcel_review_visible(r,{'riego','quimica'})
    assert phase_panel.parcel_review_visible(r,{'riego'})  # Química ausente solo en esta parcela.
    for k,v in [('fase_final','MIXTO'),('proxy_previo_riego',1),('override_status','CONTRADICHO')]:
        assert phase_panel.parcel_review_visible(dict(r,**{k:v}),{'riego','quimica'})
    assert 'fase reconocida se conserva' in text_content(phase_panel.detail(r))

def test_global_notice_uses_real_dates_and_zero_rows_are_available():
    coverage=[dict(pad_id=1,fuente='riego',ultima_fecha='2026-10-12',parcelas_con_dato=0,parcelas_esperadas=32),
              dict(pad_id=1,fuente='quimica',ultima_fecha='2026-10-13',parcelas_con_dato=32,parcelas_esperadas=32)]
    text=text_content(map_panel.coverage_notice(coverage,1,'2026-10-15'))
    assert '15-10-2026' in text and '12-10-2026' in text and '13-10-2026' in text
    coverage[0]['parcelas_con_dato']=32
    assert map_panel.coverage_notice(coverage,1,'2026-10-15') is None

def test_coverage_sql_uses_existing_sources_and_counts_nonnull_including_zero():
    calls=[]
    class Result:
        def mappings(self):return []
    class Conn:
        def execute(self,sql,params):calls.append((str(sql),params));return Result()
    @contextmanager
    def connection():yield Conn()
    with patch.object(map_db,'_connection',connection),patch.object(phase_db.phase_flags,'guard_connection'):
        assert map_db.source_coverage('2026-10-15')==[]
    sql=calls[0][0]
    assert 'caudal IS NOT NULL' in sql and 'cu_pp IS NOT NULL' in sql
    assert 'caudal>0' not in sql and 'caudal > 0' not in sql
    for name in ['v_flujos_oxido_unpivot','v_flujos_sulfuro_unpivot','v_drena_oxido_operacional','v_drena_sulfuro_operacional']:assert name in sql

def test_modules_remain_complete_inside_focusable_region():
    r=row();r['detalle_modulos']=json.dumps([dict(modulo_id=3,nombre_modulo='Módulo 3',estado_estructural='RECLAMO',fecha_ini_retiro='2025-08-04',fecha_fin_retiro='2025-08-14')])
    c=phase_panel.module_table(r)
    region=next(x for x in components(c) if getattr(x,'role',None)=='region')
    assert region.tabIndex==0 and 'lix-v2-module-scroll' in region.className
    for value in ['Módulo','Situación','Inicio apilado','Fin apilado','Inicio retiro','Fin retiro','04-08-2025','14-08-2025']:assert value in text_content(c)


def test_diagnostic_keeps_all_cases_with_single_selector_and_closed_comparison():
    r=dict(row(),estado_operacional_SQL_original='SIN_COBERTURA',fase_visual_legacy=None,
        fase_administrativa=None,origen_fase_final='AUTOMATICO',dias_sin_riego_confirmados=None,
        fecha_primer_riego_reconocido=None,fecha_primer_cu_pp_valido=None,fecha_ultimo_riego_real=None,
        fecha_ultima_ley_cu_pp=None,proxy_previo_riego=0,transicion_mismo_dia=0,version_modelo='v2',version_alerta='v2')
    rows=[dict(r,numero_parcela=i,parcela_id=i) for i in range(1,33)]
    with patch.object(phase_db,'snapshot',return_value=rows),patch.object(phase_db.phase_flags,'enabled',return_value=True):
        card=phase_panel.diagnostic({'hasta':'2026-10-15'})
    cs=list(components(card));dropdown=next(x for x in cs if getattr(x,'id',None)=='lix-v2-diagnostic-case')
    assert len(dropdown.options)==32
    assert next(x for x in cs if type(x).__name__=='Details').open is False
    assert next(x for x in cs if getattr(x,'id',None)=='lix-v2-diagnostic-rows').data==rows
    assert '32' in text_content(phase_panel.diagnostic_case('31',rows))


def test_priority_messages_survive_and_reclaimed_coverage_is_secondary():
    mixed=dict(row(),fase_final='MIXTO',proxy_previo_riego=1)
    content=text_content(phase_panel.detail(mixed))
    for message in ['Los módulos presentan situaciones diferentes','la fase reconocida se conserva','Existe una muestra anterior al primer riego reconocido']:
        assert message in content
    reclaimed=dict(row(),fase_final='RECLAMADO')
    alert=next(x for x in components(phase_panel.detail(reclaimed)) if type(x).__name__=='Alert')
    assert alert.color=='light' and alert.className=='lix-v2-review-secondary'
