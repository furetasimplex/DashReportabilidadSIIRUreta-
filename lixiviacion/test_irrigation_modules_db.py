import copy,uuid
from contextlib import contextmanager
from unittest.mock import Mock
import pytest
from . import irrigation_modules_db as db, irrigation_modules_model as model
from .test_irrigation_modules_model import roster

def snapshot(active=None):
    r=roster();context={'roster':r,'referencia':None,'revision':{'id':None,'version':0,'evento':None}}
    return dict(roster=r,referencia=None,revision=dict(id=1 if active else None,version=1 if active else 0),
        context_token=model.digest(context).hex(),contexto=context,vigente=active,seleccion=[])

def payload(s):return dict(fecha='2026-10-19',pad_id=2,parcela_id=59,estado='SELECCION_CONOCIDA',
    seleccion=[195,197,198],motivo='QA selección manual',context_token=s['context_token'],idempotency_key=str(uuid.uuid4()))

def configure(monkeypatch,s):
    conn=Mock();writes=[]
    @contextmanager
    def connection(existing=None):yield conn
    monkeypatch.setattr(db,'_connection',connection)
    monkeypatch.setattr(db,'_lock',Mock())
    monkeypatch.setattr(db,'_snapshot',lambda *a,**k:copy.deepcopy(s))
    monkeypatch.setattr(db,'_duplicate',lambda *a:None)
    monkeypatch.setattr(db,'_rows',lambda *a,**k:[{'familia_id':str(uuid.uuid4())}])
    monkeypatch.setattr(db,'_insert',lambda c,t,v,id_column=None:(writes.append((t,v)) or 23))
    actor=Mock(return_value='admin_qa');monkeypatch.setattr(db.phase_db,'_actor',actor)
    return writes,actor

def test_confirm_uses_existing_actor_and_only_modular_tables(monkeypatch):
    s=snapshot();writes,actor=configure(monkeypatch,s)
    result=db.confirm_modules(payload(s));actor.assert_called_once_with()
    assert result['id_confirmacion']==23
    assert len(writes)==7 and {x[0] for x in writes}=={db.CONF,db.DETAIL,db.EVENT}
    assert writes[0][1]['cantidad_confirmada']==3
    assert [v['modulo_id'] for t,v in writes if t==db.DETAIL and v['seleccionado']]==[195,197,198]
    assert all('fase' not in key for _,v in writes for key in v)

def test_auth_denies_before_connection(monkeypatch):
    gate=Mock(side_effect=PermissionError('no admin'));monkeypatch.setattr(db.phase_db,'_actor',gate)
    connect=Mock(side_effect=AssertionError('No conectar'));monkeypatch.setattr(db,'_connection',connect)
    with pytest.raises(PermissionError):db.confirm_modules(payload(snapshot()))
    connect.assert_not_called()

def test_stale_no_insert(monkeypatch):
    s=snapshot();writes,_=configure(monkeypatch,s);p=payload(s);p['context_token']='stale'
    with pytest.raises(model.StaleContextError):db.confirm_modules(p)
    assert not writes

@pytest.mark.parametrize('state,count',[('NINGUN_MODULO',0),('SIN_INFORMACION',None)])
def test_explicit_state_and_detail(monkeypatch,state,count):
    s=snapshot();writes,_=configure(monkeypatch,s);p=payload(s);p.update(estado=state,seleccion=[])
    db.confirm_modules(p)
    assert writes[0][1]['cantidad_confirmada']==count
    assert not any(v['seleccionado'] for t,v in writes if t==db.DETAIL)

def test_rectification_append_and_close_event_only(monkeypatch):
    s=snapshot({'id_confirmacion':1});writes,_=configure(monkeypatch,s)
    db.rectify_modules(payload(s))
    assert writes[0][1]['supersede_id']==1 and writes[0][1]['version']==2
    writes.clear();db.close_modules(payload(s))
    assert len(writes)==1 and writes[0][0]==db.EVENT and writes[0][1]['tipo_evento']=='CERRAR'

def test_duplicate_retry_returns_without_new_write(monkeypatch):
    s=snapshot();writes,_=configure(monkeypatch,s)
    monkeypatch.setattr(db,'_duplicate',lambda *a:dict(id_confirmacion=8,reintento=True))
    assert db.confirm_modules(payload(s))['reintento'] and not writes

def test_non_dev_never_connects(monkeypatch):
    monkeypatch.setattr(db.phase_flags,'is_dev',lambda:False)
    with pytest.raises(PermissionError):db.modular_snapshot('2026-10-19',2,59)


def test_import_cli_defaults_to_dry_run_without_insert(monkeypatch,tmp_path):
    from scripts import importar_referencia_modulos_riego_dev as cli
    source=tmp_path/'referencia_sintetica.txt';source.write_text('QA',encoding='utf8')
    monkeypatch.setattr(cli,'load_app_env',lambda:None)
    monkeypatch.setattr(cli.db,'preview_reference',lambda *a:dict(snapshot={'context_token':'fixture'},referencia={'estado':'VALIDA'}))
    persist=Mock(side_effect=AssertionError('Dry run no debe persistir'));monkeypatch.setattr(cli.db,'import_reference',persist)
    result=cli.main(['--fecha','2026-10-19','--pad','2','--parcela','59','--cantidad-modulos','3','--archivo',str(source),'--fuente','QA_EN_MEMORIA'])
    assert result['modo']=='dry-run' and len(result['hash_archivo'])==64
    persist.assert_not_called()


@pytest.mark.parametrize('phase',['MIXTO','RECLAMADO'])
def test_phase_is_not_a_precondition_for_modular_confirmation(monkeypatch,phase):
    s=snapshot();s['fase_final']=phase;writes,_=configure(monkeypatch,s)
    db.confirm_modules(payload(s))
    assert len(writes)==7 and writes[0][1]['cantidad_confirmada']==3
