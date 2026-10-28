"""Pruebas de comportamiento aprobado, causalidad y guardas, sin acceso SQL."""
from datetime import date,timedelta
from unittest.mock import patch
import pytest
from flask import Flask,session
from .phase_model import calculate,alert_level
from . import phase_flags,phase_db,map_db,map_panel
from .test_map import fixture_rows
START=date(2026,1,1)
def module(**kw):return {'modulo_id':1,'fecha_ini_carguio':'2025-12-01','fecha_fin_carguio':'2025-12-31','fecha_ini_retiro':None,'fecha_fin_retiro':None,**kw}
def signals(days,active=(0,),positive=(1,),missing=()):
    q=[{'fecha':START+timedelta(days=i),'caudal':None if i in missing else 2 if i in active else 0} for i in range(days+1)]
    c=[{'fecha':START+timedelta(days=i),'cu_pp':0.2 if i in positive else 0} for i in range(days+1)]
    return q,c
def run(day,**kwargs):
    q,c=signals(day,**kwargs)
    return calculate(START+timedelta(days=day),[module()],q,c)
def test_T01_first_real_irrigation_starts_wetting():
    r=run(0,positive=())
    assert r['fase_final']=='HUMECTACION'
def test_T02_first_positive_after_irrigation_starts_rc():
    assert run(0)['fase_final']=='HUMECTACION'
    assert run(1)['fase_final']=='RIEGO_CONTINUO'
def test_T03_positive_before_first_irrigation_is_flagged_not_rc():
    r=run(2,active=(2,),positive=(1,))
    assert r['fase_final']=='HUMECTACION' and r['proxy_previo_riego']==1
    assert r['fecha_primer_cu_pp_valido'] is None
def test_T04_same_day_transition_at_daily_close():
    r=run(0,positive=(0,))
    assert r['fase_final']=='RIEGO_CONTINUO' and r['transicion_mismo_dia']==1
@pytest.mark.parametrize('length', [7,115])
def test_T05_T06_pause_and_return_never_end_rc(length):
    q,c=signals(length+1,active=(0,length+1),positive=(0,))
    before=calculate(START+timedelta(days=length),[module()],q,c)
    after=calculate(START+timedelta(days=length+1),[module()],q,c)
    assert before['fase_final']==after['fase_final']=='RIEGO_CONTINUO'
    assert before['condicion_dia']=='PAUSA_HIDRAULICA' and after['condicion_dia']=='RIEGO_ACTIVO'
    assert before['dias_sin_riego_confirmados']==length and after['dias_sin_riego_confirmados']==0
@pytest.mark.parametrize('pad,bounds',[(1,(3,22,39)),(2,(3,14,33))])
def test_T07_T08_alert_boundaries_are_not_transitions(pad,bounds):
    for bound,expected,previous in zip(bounds,('PAUSA_RECIENTE','PAUSA_PROLONGADA','PAUSA_EXCEPCIONAL'),('SIN_ALERTA','PAUSA_RECIENTE','PAUSA_PROLONGADA')):
        assert alert_level(pad,'RIEGO_CONTINUO',bound,0)==expected
        assert alert_level(pad,'RIEGO_CONTINUO',bound-1,0)==previous
        assert alert_level(pad,'HUMECTACION',bound,0)=='SIN_ALERTA'
def test_T09_null_breaks_confirmed_suffix_and_keeps_phase():
    r=run(6,positive=(0,),missing=(4,))
    assert r['dias_sin_riego_confirmados']==2 and r['fase_final']=='RIEGO_CONTINUO'
    missing=run(6,positive=(0,),missing=(6,))
    assert missing['caudal_operacional'] is None and missing['riego_activo'] is None
    assert missing['dias_sin_riego_confirmados'] is None and missing['condicion_dia']=='SIN_COBERTURA'
def test_T16_incompatible_modules_are_mixed():
    q,c=signals(1)
    r=calculate(START+timedelta(days=1),[module(),module(modulo_id=2,fecha_fin_carguio=None)],q,c)
    assert r['fase_final']=='MIXTO'
def test_T17_all_modules_must_finish_with_inclusive_retirement_day():
    q,c=signals(5)
    done=module(fecha_ini_retiro='2026-01-02',fecha_fin_retiro='2026-01-04')
    pending=module(modulo_id=2,fecha_ini_retiro='2026-01-02')
    assert calculate('2026-01-06',[done,pending],q,c)['fase_final']=='MIXTO'
    assert calculate('2026-01-04',[done],q,c)['fase_final']=='RECLAMO'
    assert calculate('2026-01-05',[done,done|{'modulo_id':2}],q,c)['fase_final']=='RECLAMADO'
def test_T18_plan_dates_are_ignored():
    q,c=signals(5,positive=(0,))
    planned=module(fecha_plan_detencion='2026-01-02',caudal_target=100)
    assert calculate('2026-01-06',[planned],q,c)==calculate('2026-01-06',[module()],q,c)
def test_T19_flag_off_keeps_exact_legacy_read():
    rows=fixture_rows()
    with patch.object(phase_flags,'enabled',return_value=False),patch.object(phase_db,'snapshot',side_effect=AssertionError('V2 no debe consultarse')),patch.object(map_db,'snapshot',return_value=rows):
        data,error=map_panel.load_map('2026-09-10','lix-map-tab',{'display':'block'},'v2')
    assert error is None and data['model']=='legacy'
    assert [r['estado_operacional'] for r in data['rows']]==[r['estado_operacional'] for r in rows]
def test_T20_write_flag_off_blocks_server_before_transaction():
    with patch.object(phase_flags,'enabled',return_value=False),patch.object(phase_db,'_transaction',side_effect=AssertionError('Sin escritura')):
        with pytest.raises(PermissionError):phase_db.decide({})
def test_future_irrigation_and_chemistry_do_not_change_past():
    q,c=signals(5,active=(3,),positive=(4,))
    a=calculate('2026-01-02',[module()],q,c)
    b=calculate('2026-01-02',[module()],q[:2],c[:2])
    assert a==b and a['fase_final']=='ESPERA_RIEGO'
@pytest.mark.parametrize('caudal,active',[(1,0),(1.000001,1),(-3,0),(None,None)])
def test_closed_activity_threshold_and_null(caudal,active):
    r=calculate(START,[module()],[{'fecha':START,'caudal':caudal}],[{'fecha':START,'cu_pp':0}])
    assert r['riego_activo']==active
    assert r['caudal_operacional']==(0 if caudal is not None and caudal<0 else caudal)
def test_production_cannot_enable_flags_by_environment():
    with patch.dict('os.environ',{'SQLSERVER_DB':'PROD','ENABLE_PHASE_MODEL_V2':'true','ENABLE_OPERATIONAL_PHASE_OVERRIDES_WRITE':'true'}):
        assert not any(phase_flags.enabled(k) for k in phase_flags.NAMES)
def test_missing_session_and_foreign_origin_are_rejected():
    app=Flask(__name__);app.secret_key='unit-test-only'
    with patch.object(phase_flags,'enabled',return_value=True):
        with app.test_request_context('/'): 
            with pytest.raises(PermissionError):phase_db._actor()
        with app.test_request_context('/',method='POST',headers={'Origin':'https://foreign.example'}):
            session['user']='tester'
            with pytest.raises(PermissionError):phase_db._actor()

def test_no_campaign_does_not_attach_parcel_signals():
    q,c=signals(1)
    r=calculate('2026-01-02',[],q,c)
    assert r['fase_final']=='NO_EVALUABLE' and r['riego_activo'] is None

def test_get_cannot_write_decisions():
    app=Flask(__name__);app.secret_key='test-only'
    with patch.object(phase_flags,'enabled',return_value=True),app.test_request_context('/',method='GET'):
        session['user']='tester'
        with pytest.raises(PermissionError):phase_db._actor()

def test_v2_failure_falls_back_to_legacy():
    rows=fixture_rows()
    with patch.object(phase_flags,'enabled',return_value=True),patch.object(phase_db,'snapshot',side_effect=RuntimeError('prueba')),patch.object(map_db,'snapshot',return_value=rows):
        data,warning=map_panel.load_map('2026-09-10','lix-map-tab',{'display':'block'},'v2')
    assert warning is not None and data['model']=='legacy' and len(data['rows'])==60

def test_forced_rollback_wins_over_environment():
    with patch.object(phase_flags,'config',return_value={'force_legacy':True}),patch.object(phase_flags,'is_dev',return_value=True),patch.dict('os.environ',{k:'true' for k in phase_flags.NAMES}):
        assert not any(phase_flags.enabled(k) for k in phase_flags.NAMES)

def test_v2_admin_selection_survives_map_button_refresh():
    from . import phase_panel
    prior={'pad_id':1,'parcela_id':29,'campana_id':4}
    data={'model':'v2','fecha':'2026-10-01','rows':[prior]}
    with patch.object(phase_panel,'ctx') as context:
        context.triggered_id={'type':'lix-parcel','pad':1,'parcel':29}
        selected,effective=phase_panel.select_parcel([0],'2026-10-01',None,'lix-map-tab',data,prior)
    assert selected==prior and effective is __import__('dash').no_update

def test_admin_drain_reference_handles_absent_sample():
    from . import phase_panel
    assert phase_panel.drain_reference('ESPERA_RECLAMO',{'row':{}}) is not None
    assert phase_panel.drain_reference('RIEGO_CONTINUO',{'row':{}}) is None

def test_client_label_does_not_assert_unobserved_conformation():
    from .phase_panel import legacy_label
    assert legacy_label('CONFORMADO')=='Apilado terminado (modelo anterior)'

def test_read_and_alert_flags_are_independent():
    original={'riego_activo_v2':0,'fase_final':'DRENAJE_RESIDUAL','fase_calculada_modelo':'RIEGO_CONTINUO','fase_administrativa':'DRENAJE_RESIDUAL','origen_fase_final':'ADMINISTRADOR','override_id':3,'override_status':'VIGENTE','usuario_creacion':'tester','motivo_texto':'confirmación','motivo_revision_modelo':None,'pad_id':1,'dias_sin_riego_confirmados':40,'nivel_alerta':'SIN_ALERTA'}
    with patch.object(phase_flags,'enabled',side_effect=lambda name:name=='ENABLE_PHASE_ALERTS'):
        r=phase_db.clean(original)
    assert r['fase_final']=='RIEGO_CONTINUO' and r['override_id'] is None and r['nivel_alerta']=='PAUSA_EXCEPCIONAL' and r['usuario_creacion'] is None and r['motivo_texto'] is None
    with patch.object(phase_flags,'enabled',side_effect=lambda name:name=='ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):
        r=phase_db.clean(original)
    assert r['fase_final']=='DRENAJE_RESIDUAL' and r['nivel_alerta']=='SIN_ALERTA'

@pytest.mark.parametrize('trigger',['lix-map-data',{'type':'lix-parcel','pad':1,'parcel':29}])
def test_v2_highlight_uses_final_phase_not_stale_legacy_color(trigger):
    identity={'type':'lix-parcel','pad':1,'parcel':29}
    prior={'pad_id':1,'parcela_id':29,'campana_id':4}
    row=prior|{'model_v2':True,'fase_final':'DRENAJE_RESIDUAL','fase_visual':'CICLO_HIDRAULICO'}
    data={'model':'v2','fecha':'2026-10-01','rows':[row]}
    with patch.object(map_panel,'ctx') as context:
        context.triggered_id=trigger
        colors,_=map_panel.highlight_selection([1],'2026-10-01',None,'lix-map-tab',data,[identity],['lix-parcel hydraulic selected'],prior)
    assert colors[0].startswith('lix-parcel draining')

@pytest.mark.parametrize('enabled,previous,choice,expected',[(True,False,'legacy','v2'),(False,True,'v2','legacy'),(True,True,'legacy',None)])
@pytest.mark.parametrize('dev',[False,True])
def test_feature_activation_on_open_preserves_comparison_choice(enabled,previous,choice,expected,dev):
    with patch.object(phase_flags,'enabled',return_value=enabled),patch.object(phase_flags,'is_dev',return_value=dev):
        style,value,available=map_panel.initialize_model('lix-map-tab',{'display':'block'},choice,previous)
    assert available is enabled and style==({} if enabled and not dev else {'display':'none'})
    assert value is __import__('dash').no_update if expected is None else value==expected

def test_legacy_visual_phase_is_shown_with_natural_label():
    from .phase_panel import legacy_phase_label
    assert legacy_phase_label('CICLO_HIDRAULICO')=='Ciclo hidráulico'
    assert legacy_phase_label('CONFORMADO_PRE_RIEGO')=='Apilado terminado (modelo anterior)'

def test_alert_flag_off_is_respected_in_admin_evidence():
    from . import phase_panel
    row=fixture_rows()[0]|{'fase_final':'RIEGO_CONTINUO','fase_calculada_modelo':'RIEGO_CONTINUO','riego_activo_v2':0,'nivel_alerta':'PAUSA_EXCEPCIONAL','override_status':None,'consolidacion_modulos':'UNANIME','estructura_unica':'DISPONIBLE','retiro_fisico':0}
    evidence={'row':row,'revision':{'decision':0,'evento':0},'context_token':'test-token'}
    selected={k:row[k] for k in ('pad_id','parcela_id','campana_id')}
    with patch.object(phase_flags,'enabled',side_effect=lambda name:name in ('ENABLE_PHASE_MODEL_V2','ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ')),patch.object(phase_db,'preview',return_value=evidence),patch.object(phase_db,'history',return_value=([],[])),patch.object(phase_db,'_actor',side_effect=PermissionError()),patch.object(phase_panel,'confirmation_summary',return_value=None) as show:
        result=phase_panel.preview_admin(selected,'2026-09-10',0)
    assert show.call_args.args[0]['nivel_alerta']=='SIN_ALERTA'
    assert result[2]['row']['nivel_alerta']=='PAUSA_EXCEPCIONAL'  # Token/evidencia técnica no se alteran.
