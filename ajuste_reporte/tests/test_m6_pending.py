"""Pruebas offline: preparador real, adapter con repositorio en memoria y SQL estático.

El fake NO certifica compilación, triggers, hash estilo3 ni transacciones SQL Server.
"""
import copy,json,hashlib,threading,uuid
from dataclasses import replace
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import Mock
import pandas as pd
import pytest
from ajuste_reporte import m6_pending as m
from ajuste_reporte import m6_pending_sql as s

ROOT=Path(__file__).resolve().parents[2]
RUN='b6c00000-0000-4000-8000-000000010009'

@pytest.fixture(autouse=True)
def no_driver_sql(monkeypatch):
    import pyodbc
    monkeypatch.setattr(pyodbc,'connect',lambda *a,**k:pytest.fail('SQL real prohibido en tests offline'))

@pytest.fixture
def prepared():
    f=json.loads((ROOT/'test_fixtures/ajuste_reporte/m6_10009_10082.json').read_text(encoding='utf8'))
    return m.prepare_pending(pd.DataFrame(f['results']),pd.DataFrame(f['catalog']),f['context'],pd.DataFrame(f['daily']),pd.DataFrame(f['rules']),run_id=RUN)

def test_real_preparer_19_28_and_four_targets(prepared):
    p=prepared['preparador'];assert len(p['columnas_heredadas'])==28 and len(p['columnas_ajustadas'])==19
    assert all(p['targets'][k]==v for k,v in m.EXPECTED.items())
    assert prepared['publicable'] is prepared['persistido'] is False
    assert prepared['run_id']!=str(prepared['context']['solver_run_id'])
    assert next(d for d in p['diagnosticos'] if d['codigo']=='CONTRASTE_BRUTO_ASIGNADO')['diferencia_masa']==pytest.approx(.043440,abs=1e-8)

def test_all47_null_and_six_srr(prepared):
    assert all(len(r)==48 for r in prepared['records'])
    assert len([n for n in m.FIELDS if n.startswith('SRR_') or n.endswith('_srr')])==6
    assert any(v is None for r in prepared['records'] for v in r.values())
    assert json.loads(prepared['payload_json'])==prepared['records']
    assert m.compare_payload(prepared['records'],copy.deepcopy(prepared['records']))

@pytest.mark.parametrize('field,value',[('Humedad_Turno_A',99.0),('Campana_apilado','alterada'),('SRR_TMS_Plan',None)])
def test_exact_comparison_detects_changes(prepared,field,value):
    rows=copy.deepcopy(prepared['records']);rows[0][field]=value
    with pytest.raises(m.PendingGateError):m.compare_payload(prepared['records'],rows)

@pytest.mark.parametrize('mutation',['missing','duplicate','outside','null_date','missing_column','nonfinite','text_long','fractional_int'])
def test_contract_rejections(prepared,mutation):
    f=pd.DataFrame(prepared['records'])
    if mutation=='missing':f=f.iloc[:-1]
    elif mutation=='duplicate':f.loc[6,'Fecha']=f.loc[0,'Fecha']
    elif mutation=='outside':f.loc[6,'Fecha']='2026-09-08'
    elif mutation=='null_date':f.loc[0,'Fecha']=None
    elif mutation=='missing_column':f=f.drop(columns=[m.FIELDS[0]])
    elif mutation=='nonfinite':f.loc[0,'Chancado_TMS_Real']=float('inf')
    elif mutation=='text_long':f.loc[0,'Campana_apilado']='á'*256
    elif mutation=='fractional_int':f['Modulo_apilado']=f['Modulo_apilado'].astype(float);f.loc[0,'Modulo_apilado']=1.5
    with pytest.raises((ValueError,m.PendingGateError)):m.payload_records(f)

def valid_evidence(baseline):
    return m.ExecutionEvidence(execute_dev=True,actor='QA_OPERADOR',server_name='VPS-5347319-X',database_name='inventar_SpcHidr',
        backup_verified_recoverable=True,backup_reference='FAKE_TEST_ONLY',backup_sha256='a'*64,
        protection_overlap_test_passed=True,protection_test_reference='FAKE_TEST_ONLY',consumers_review_passed=True,
        baseline_sha256=m.history_digest(baseline))

@pytest.mark.parametrize('patch',[{'execute_dev':False},{'execute_dev':1},{'backup_verified_recoverable':False},
    {'backup_reference':''},{'backup_sha256':''},{'protection_overlap_test_passed':False},{'protection_test_reference':''},
    {'consumers_review_passed':False},{'database_name':'inventar_SpcHidr_PROD'},{'server_name':'otro'},
    {'actor':''},{'baseline_sha256':''}])
def test_gate_before_any_connection(prepared,patch):
    engine=Mock()
    with pytest.raises(m.PendingGateError):m.execute_pending(engine,prepared,evidence=replace(valid_evidence([]),**patch))
    engine.connect.assert_not_called()

class Result:
    def __init__(self,rows=None,scalar=None):self.rows=rows or [];self.scalar=scalar
    def mappings(self):return self.rows
    def scalar_one(self):return self.scalar

class MemoryEngine:
    def __init__(self):
        self.history=[{'run_id':'11111111-1111-4111-8111-111111111111','Fecha':'2023-01-01','estado_validacion':'VALIDADO','es_activa':True,'original':'NULL preserved'}]
        self.reader=[{'Fecha':'2023-01-01','original':None}];self.stage={};self.lots={};self.calls=[];self.lock=threading.RLock();self.context=None
        self.corrupt_stage=False;self.change_reader=False
    def connect(self):return self
    def execution_options(self,**kw):assert kw=={'isolation_level':'SERIALIZABLE'};return self
    def __enter__(self):return self
    def __exit__(self,*a):pass
    @contextmanager
    def begin(self):
        with self.lock:
            prior=copy.deepcopy((self.history,self.reader,self.stage,self.lots))
            try:yield self
            except Exception:self.history,self.reader,self.stage,self.lots=prior;raise
    def invalidate(self):self.context=None
    def execute(self,query,params=None):
        query=str(query);p=params or {};self.calls.append(query)
        if query==s.HASH_JSON_SQL:return Result(scalar=hashlib.sha256(p['payload_json'].encode('utf-16le')).digest())
        if query.startswith('EXEC sys.sp_set_session_context'):
            self.context=None if '@value=NULL' in query else 1;return Result()
        if query.startswith('EXEC '+s.PROC):
            run=p['run'];rows=json.loads(p['payload']);identity=(p['caso'],p['modelo'],p['solver'],p['hash'],p['usuario'])
            assert self.context==1
            if run in self.lots:
                if self.lots[run]!=identity:raise m.PendingGateError('UUID modificado')
                return Result([{'rows_inserted':0,'idempotent':True}])
            if any(str(r['run_id'])==run for r in self.history) or run in self.stage:raise m.PendingGateError('UUIDhistorico')
            self.lots[run]=identity;self.stage[run]=copy.deepcopy(rows)
            self.history+= [{**r,'run_id':run,'caso_id':10009,'estado_validacion':'PENDIENTE','es_activa':False} for r in rows]
            if self.corrupt_stage:self.stage[run][0]['SRR_TMS_Turno_A']+=1
            if self.change_reader:self.reader.append({'unexpected':True})
            return Result([{'rows_inserted':7,'idempotent':False}])
        if query.startswith('SELECT run_id FROM '+s.LOT):return Result([{'run_id':p['run']}] if p['run'] in self.lots else [])
        if query.startswith('SELECT * FROM inventar_SpcHidr.vw_datos_conciliados_reporte'):return Result(copy.deepcopy(self.reader))
        if query.startswith('SELECT Fecha,'):return Result(copy.deepcopy(self.stage.get(p['run'],[])))
        if query.startswith('SELECT * FROM '+s.VERSIONS):
            rows=[r for r in self.history if not p or r['run_id']==p['run']];return Result(copy.deepcopy(rows))
        raise AssertionError('Consulta inesperada en fake; no se ejecutaSQL: '+query[:70])
    def legacy_publish_overlap(self,start,end):
        # Contrato de DELETE por Fecha del SP real; modelo en memoria, no trigger SQL.
        with self.begin():
            deleted=[r for r in self.history if start<=r['Fecha']<=end]
            if any(r['run_id'] in self.lots for r in deleted):raise m.PendingGateError('legacy DELETE protegido; operación completa revertida')
            self.history=[r for r in self.history if r not in deleted]

@pytest.fixture
def engine(monkeypatch,prepared):
    e=MemoryEngine()
    monkeypatch.setattr(m,'_guard_dev',lambda c:{'server_name':'VPS-5347319-X','db':'inventar_SpcHidr'})
    monkeypatch.setattr(m,'check_installed_contract',lambda c:None)
    monkeypatch.setattr(m,'load_prepare',lambda c,**kw:copy.deepcopy(prepared))
    return e

def test_atomic_insert_pending_and_idempotence(engine,prepared):
    original=copy.deepcopy(engine.history);ev=valid_evidence(original)
    first=m.execute_pending(engine,prepared,evidence=ev)
    assert first['rows_inserted']==7 and first['comparacion_47_exacta'] and not first['publicable']
    assert engine.history[:1]==original and len(engine.history)==8
    second=m.execute_pending(engine,prepared,evidence=ev)
    assert second['idempotent'] and second['rows_inserted']==0 and len(engine.history)==8
    assert engine.context is None
    for q in engine.calls:assert 'sp_rep_merge' not in q and 'SetActiveRun' not in q and 'ClearActiveRun' not in q and 'sp_rep_publish_oficial_validado' not in q

def test_uuid_modified_rejected_without_mutation(engine,prepared):
    ev=valid_evidence(engine.history);m.execute_pending(engine,prepared,evidence=ev);before=copy.deepcopy(engine.history)
    altered=copy.deepcopy(prepared);altered['records'][0]['Chancado_TMS_Real']+=1;altered['payload_json']=m.serialize_payload(altered['records'])
    with pytest.raises(m.PendingGateError,match='UUID'):m.execute_pending(engine,altered,evidence=ev)
    assert engine.history==before and engine.context is None

@pytest.mark.parametrize('flag',['corrupt_stage','change_reader'])
def test_readback_or_consumer_failure_rolls_back_everything(engine,prepared,flag):
    ev=valid_evidence(engine.history);before=copy.deepcopy(engine.history);setattr(engine,flag,True)
    with pytest.raises(m.PendingGateError):m.execute_pending(engine,prepared,evidence=ev)
    assert engine.history==before and not engine.lots and not engine.stage and engine.context is None

def test_legacy_overlapping_delete_rejects_entire_mixed_operation(engine,prepared):
    ev=valid_evidence(engine.history);m.execute_pending(engine,prepared,evidence=ev)
    legacy={'run_id':'22222222-2222-4222-8222-222222222222','Fecha':'2026-09-04','estado_validacion':'VALIDADO','es_activa':True}
    engine.history.append(legacy);before=copy.deepcopy(engine.history)
    with pytest.raises(m.PendingGateError,match='legacy DELETE'):engine.legacy_publish_overlap('2026-09-01','2026-09-07')
    assert engine.history==before and legacy in engine.history
    engine.legacy_publish_overlap('2023-01-01','2023-01-01')
    assert len(engine.history)==8  # El guard limitado NO resuelve borrados históricos legacy.

def test_unregistered_existing_uuid_is_not_reinterpreted(engine,prepared):
    ev=valid_evidence(engine.history);engine.stage[RUN]=copy.deepcopy(prepared['records'])
    with pytest.raises(m.PendingGateError,match='UUIDhistorico'):m.execute_pending(engine,prepared,evidence=ev)
    assert not engine.lots and len(engine.history)==1

def test_stale_baseline_or_changed_source_rejected(engine,prepared,monkeypatch):
    ev=valid_evidence(engine.history);engine.history[0]['original']='cambio'
    with pytest.raises(m.PendingGateError,match='histórico'):m.execute_pending(engine,prepared,evidence=ev)
    ev=valid_evidence(engine.history);current=copy.deepcopy(prepared);current['records'][0]['SRR_TMS_Plan']=999
    monkeypatch.setattr(m,'load_prepare',lambda c,**kw:current)
    with pytest.raises(m.PendingGateError):m.execute_pending(engine,prepared,evidence=ev)
    assert not engine.lots

def test_sql_structure_is_scoped_and_no_legacy_merge_delete():
    definition=s.proc_definition();script=s.installation_script()
    assert 'DELETE FROM' not in definition and '\n UPDATE ' not in definition and 'MERGE' not in definition
    assert 'sp_rep_publish_oficial_validado' not in definition
    assert "'PENDIENTE'" in definition and "'VALIDADO'" not in definition
    assert 'deleted d JOIN '+s.LOT in s.GUARD_DEFINITION
    assert 'AFTER INSERT,UPDATE,DELETE' in s.GUARD_DEFINITION
    assert 'ISNULL(HASHBYTES' in definition and 'sp_getapplock' in definition
    assert ':setvar ApproveM6PendingDEV "0"' in script
    assert 'CREATE TABLE' in s.TABLE_DEFINITION and script.count('CREATE TABLE')==1
    for c in s.COLUMNS:assert s.quote(c['name']) in definition
    assert len(s.CONTRACT['adjusted'])==19 and len(s.CONTRACT['inherited'])==28

def test_source_and_legacy_identity_explicit(prepared):
    other=dict(prepared['context'],modelo_id=1,modelo_codigo='hidrometalurgia_120_completo',total_flujos=120)
    with pytest.raises(m.PendingGateError):m.validate_context(other)
    assert m.prepare_ajuste_m6_125.__module__=='ajuste_reporte.rep_prod_adjuster'

def test_cli_execute_without_evidence_cannot_connect(monkeypatch,tmp_path):
    import db_connection
    connect=Mock();monkeypatch.setattr(db_connection,'get_engine',connect)
    with pytest.raises(m.PendingGateError,match='evidencias'):
        m.main(['--caso','10009','--modelo','2','--solver-run','10082','--execute-dev',
                '--output',str(ROOT/'auditorias/_unused_pending_test.json')])
    connect.assert_not_called()

def test_installation_file_matches_generator():
    assert (ROOT/'ajuste_reporte/sql/m6_pending_dev.sql').read_text(encoding='utf8')==s.installation_script()
