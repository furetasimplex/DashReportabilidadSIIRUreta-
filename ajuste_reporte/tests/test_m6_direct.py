"""Adaptación del flujo habitual; ninguna escritura real ni uso de10009 como publicación."""
import copy,json,re,threading,uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock,MagicMock
import pandas as pd
import pytest
from ajuste_reporte import rep_prod_adjuster as w

ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(autouse=True)
def no_sql(monkeypatch):
    import pyodbc
    monkeypatch.setattr(pyodbc,'connect',lambda *a,**k:pytest.fail('SQL real prohibido'))
    monkeypatch.setattr(pd.DataFrame,'to_sql',lambda *a,**k:pytest.fail('No persistir tests'))
    monkeypatch.delenv('ENABLE_M6_DATOS_CONCILIADOS_DEV',raising=False)

@pytest.fixture
def bundle():
    # Dataset sintético: valores de regresión reutilizados con OTRO caso/run/fechas.
    f=json.loads((ROOT/'test_fixtures/ajuste_reporte/m6_10009_10082.json').read_text(encoding='utf8'))
    ctx=f['context'];ctx.update(caso_id=20001,solver_run_id=30001,run_caso_id=20001,fecha_inicio='2026-10-12',fecha_fin='2026-10-18')
    for r in f['results']:r.update(caso_id=20001,run_id=30001)
    for i,r in enumerate(f['daily']):r['Fecha']=f'2026-10-{12+i:02d}'
    p=w.prepare_ajuste_m6_125(pd.DataFrame(f['results']),pd.DataFrame(f['catalog']),ctx,pd.DataFrame(f['daily']),pd.DataFrame(f['rules']))
    return ctx,p

def configure(monkeypatch,bundle):
    ctx,p=bundle;engine=Mock();calls=[];stage={}
    monkeypatch.setattr(w,'get_engine',lambda:engine)
    monkeypatch.setattr(w,'get_solver_model_context',lambda *a:ctx)
    monkeypatch.setattr(w,'_m6_standard_guard',lambda *a,**k:None)
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame(columns=['Fecha']))
    monkeypatch.setattr(w,'preview_m6_from_solver',lambda *a,**k:copy.deepcopy(p))
    monkeypatch.setattr(w,'get_table_columns',lambda *a:['Fecha']+w._m6_operational_columns(p))
    monkeypatch.setattr(w,'exec_sql',lambda engine,sql,params:calls.append((sql,params)))
    def write(engine,frame,run,case,version,*a,**k):
        stage['frame']=frame.copy();stage['frame']['caso_id']=case;stage['frame']['version_reglas']=version
    monkeypatch.setattr(w,'write_staging',write)
    monkeypatch.setattr(w,'read_ajustado_run_df',lambda *a:stage['frame'])
    return engine,calls,stage

def test_m6_standard_mapping_staging_log_no_new_infrastructure(monkeypatch,bundle):
    engine,calls,stage=configure(monkeypatch,bundle)
    result=w.run_ajuste_reporte_prod_solver_nuevo(20001)
    assert result['ok'] and result['caso_id']==20001 and result['totales']['solver_run_id']==30001
    assert result['totales']['targets']==bundle[1]['targets']
    assert len(result['totales']['columnas_operacionales'])==47
    assert w._m6_payload_digest(stage['frame'],w._m6_operational_columns(bundle[1]))==result['totales']['payload_sha256']
    assert len(calls)==2 and 'sp_rep_log_start' in calls[0][0] and 'sp_rep_log_end' in calls[1][0]
    assert not any('merge' in q.lower() or 'build_targets' in q.lower() or 'm6_insert_pending' in q.lower() for q,p in calls)
    assert json.loads(calls[1][1]['tot'])['namespace']=='DEV_SIIR.hidro.recon_caso'

def test_overlap_precheck_advisory_rejects_before_staging(monkeypatch,bundle):
    _,calls,stage=configure(monkeypatch,bundle)
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame({'Fecha':['2026-10-13','2026-10-16']}))
    with pytest.raises(w.M6ValidationError,match='2026-10-13, 2026-10-16'):w.run_ajuste_reporte_prod_solver_nuevo(20001)
    assert not calls and not stage

def test_missing_srr_no_silent_drop(monkeypatch,bundle):
    _,calls,stage=configure(monkeypatch,bundle)
    monkeypatch.setattr(w,'get_table_columns',lambda *a:[c for c in w._m6_operational_columns(bundle[1]) if c!='Ley_CuT_Plan_srr'])
    with pytest.raises(w.M6ValidationError,match='CONTRATO_47'):w.run_ajuste_reporte_prod_solver_nuevo(20001)
    assert not calls and not stage

def test_summary_uses_run_targets_not_old_table(monkeypatch,bundle):
    ctx,p=bundle
    monkeypatch.setattr(w,'get_engine',lambda:Mock())
    monkeypatch.setattr(w,'_m6_logged_run',lambda *a:{'targets':p['targets'],'periodo':['2026-10-12','2026-10-18']})
    monkeypatch.setattr(w,'read_ajustado_run_df',lambda *a:p['datos'])
    monkeypatch.setattr(w,'read_targets_df',lambda *a:pytest.fail('Targets históricos incorrectos paraM6'))
    monkeypatch.setattr(w,'_get_periodo_caso_con_fallback',lambda *a:pytest.fail('No rebindear período de un UUID'))
    result=w.build_resumen_comparativo_run(20001,p['run_id'])
    assert result['targets']['F08F09_MASA']==77148.856848
    assert result['periodo']['fecha_inicio']=='2026-10-12'

def make_trace(bundle):
    ctx,p=bundle;fields=w._m6_operational_columns(p)
    return {'modelo_id':ctx['modelo_id'],'solver_run_id':ctx['solver_run_id'],'targets':p['targets'],'version_reglas':1,
            'payload_sha256':w._m6_payload_digest(p['datos'],fields)}

@pytest.mark.parametrize('change',['none','value','null','case','rules','missing_date','duplicate_date','source'])
def test_publication_revalidates_47_and_source_in_transaction(monkeypatch,bundle,change):
    ctx,p=bundle;trace=make_trace(bundle)
    stage=p['datos'].copy();stage['caso_id']=ctx['caso_id'];stage['version_reglas']=1
    current=copy.deepcopy(p)
    if change=='value':stage.loc[0,'SRR_TMS_Turno_A']+=1
    if change=='null':stage.loc[0,'SRR_TMS_Plan']=None
    if change=='case':stage.loc[0,'caso_id']=999
    if change=='rules':stage.loc[0,'version_reglas']=2
    if change=='missing_date':stage=stage.iloc[:-1]
    if change=='duplicate_date':stage.loc[6,'Fecha']=stage.loc[0,'Fecha']
    if change=='source':current['targets']['F3']+=1
    monkeypatch.setattr(w,'_m6_logged_run',lambda *a:trace)
    monkeypatch.setattr(w,'preview_m6_from_solver',lambda *a,**k:current)
    queries=[]
    def read(conn,sql,params):queries.append(sql);return stage
    monkeypatch.setattr(w,'read_sql_df',read)
    if change=='none':assert w._m6_validate_publication(Mock(),20001,p['run_id'])==trace
    else:
        with pytest.raises(w.M6ValidationError):w._m6_validate_publication(Mock(),20001,p['run_id'])
    if change!='source':assert 'UPDLOCK,HOLDLOCK' in queries[0]

def test_standard_flow_stays_closed_without_operational_approval(bundle):
    e=Mock()
    with pytest.raises(w.M6ValidationError,match='PERSISTENCIA_M6_BLOQUEADA'):w._m6_standard_guard(e)
    e.connect.assert_not_called()

def test_model_m6_official_ambiguity_rejected(monkeypatch,bundle):
    ctx,_=bundle
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame([ctx,ctx]))
    with pytest.raises(w.M6ValidationError,match='CASO_RUN_AMBIGUO'):w.get_solver_model_context(Mock(),20001)

def test_legacy_summary_unchanged(monkeypatch,bundle):
    _,p=bundle;seen=[]
    monkeypatch.setattr(w,'get_engine',lambda:Mock());monkeypatch.setattr(w,'_m6_logged_run',lambda *a:None)
    monkeypatch.setattr(w,'read_ajustado_run_df',lambda *a:p['datos'])
    monkeypatch.setattr(w,'_get_periodo_caso_con_fallback',lambda *a:(pd.Timestamp('2026-10-12'),pd.Timestamp('2026-10-18')))
    def targets(*a):seen.append(True);return pd.DataFrame({'target_code':list(p['targets']),'target_value':list(p['targets'].values())})
    monkeypatch.setattr(w,'read_targets_df',targets)
    assert w.build_resumen_comparativo_run(1,p['run_id'])['targets']==p['targets'] and seen

def test_no_numeric_rounding_in_fingerprint(bundle):
    _,p=bundle;fields=w._m6_operational_columns(p);f=p['datos'].copy()
    original=w._m6_payload_digest(f,fields)
    f.loc[0,'Chancado_TMS_Real']=float(f.loc[0,'Chancado_TMS_Real'])+1e-10
    assert w._m6_payload_digest(f,fields)!=original

def test_existing_sql_publication_lock_and_coverage():
    sql=(ROOT/'ajuste_reporte/sql/sp_rep_publish_oficial_validado_new_period.sql').read_text(encoding='utf8')
    assert sql.lstrip().startswith('ALTER PROCEDURE inventar_SpcHidr.sp_rep_publish_oficial_validado')
    assert not re.search(r'\bDELETE\s+FROM|\bCREATE\s+(TABLE|TRIGGER|PROCEDURE)',sql,re.I)
    begin=sql.index('BEGIN TRANSACTION');lock=sql.index('WITH(TABLOCKX,HOLDLOCK)');insert=sql.index('INSERT INTO @periodo')
    assert begin<lock<insert<sql.index('STRING_AGG')<sql.index("IF OBJECT_ID('inventar_SpcHidr.rep_prod_validacion_log'")
    assert 'COUNT(DISTINCT Fecha)' in sql and '@rows_published <> @dias' in sql and 'THROW 50004,@conflicto' in sql
    assert '@modelo_id INT = NULL' in sql and '@solver_run_id INT = NULL' in sql

def test_existing_view_adds_srr_at_end_without_changing_old_selection():
    view=(ROOT/'ajuste_reporte/sql/vw_datos_conciliados_reporte_srr.sql').read_text(encoding='utf8')
    for field in ('SRR_TMS_Turno_A','SRR_TMS_Turno_B','SRR_TMS_promedio_dia','SRR_TMS_Plan','Ley_CuT_Real_srr','Ley_CuT_Plan_srr'):
        assert view.count('['+field+']')==3
    assert "WHERE ISNULL(v.[estado_validacion], 'VALIDADO') = 'VALIDADO'" in view
    assert 'WHERE rn = 1' in view and 'WHERE o.[Fecha] IS NULL' in view

def test_concurrent_new_period_contract_model_only():
    # Modelo de la sección TABLOCKX, NO certificación de locks SQL Server.
    lock=threading.Lock();versions={};barrier=threading.Barrier(2)
    def publish(run):
        barrier.wait()
        with lock:
            dates=['2026-10-12','2026-10-13']
            if any(d in versions for d in dates):return False
            versions.update({d:run for d in dates});return True
    with ThreadPoolExecutor(max_workers=2) as pool:result=list(pool.map(publish,['A','B']))
    assert sorted(result)==[False,True] and len(versions)==2 and len(set(versions.values()))==1

def test_publication_calls_same_sp_with_identity_and_single_connection(monkeypatch,bundle):
    _,p=bundle;conn=MagicMock();engine=MagicMock();engine.begin.return_value.__enter__.return_value=conn
    conn.execute.return_value.scalar_one.return_value=0
    conn.execute.return_value.fetchall.return_value=[(10,7)]
    monkeypatch.setattr(w,'get_engine',lambda:engine)
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame([{'codigo':'hidrometalurgia_125_v2'}]))
    guard=Mock();monkeypatch.setattr(w,'_m6_standard_guard',guard)
    def validate(c,*args):assert c is conn;return {'modelo_id':2,'solver_run_id':30001}
    monkeypatch.setattr(w,'_m6_validate_publication',validate)
    result=w.publicar_run_oficial(20001,p['run_id'],'operador')
    assert result['rows_published']==7 and result['validation_id']==10
    first=conn.execute.call_args_list[0];last=conn.execute.call_args_list[-1]
    assert 'TABLOCKX,HOLDLOCK' in str(first.args[0])
    assert 'sp_rep_publish_oficial_validado' in str(last.args[0]) and 'm6_insert_pending' not in str(last.args[0])
    assert last.args[1]['modelo_id']==2 and last.args[1]['solver_run_id']==30001
    assert guard.call_args_list[-1].kwargs['connection'] is conn

def test_legacy_publication_signature_preserved(monkeypatch,bundle):
    _,p=bundle;conn=MagicMock();engine=MagicMock();engine.begin.return_value.__enter__.return_value=conn
    conn.execute.return_value.fetchall.return_value=[(11,7)]
    monkeypatch.setattr(w,'get_engine',lambda:engine)
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame([{'codigo':'hidrometalurgia_120_completo'}]))
    monkeypatch.setattr(w,'_m6_standard_guard',lambda *a,**k:pytest.fail('No afectar autorizacion120'))
    monkeypatch.setattr(w,'_assert_standard_publication_sql',lambda *a,**k:None)
    assert w.publicar_run_oficial(7,p['run_id'],'legacy')['validation_id']==11
    assert 'modelo_id' not in conn.execute.call_args.args[1]

@pytest.mark.parametrize('unsafe',['safe','old_delete','missing_view','no_backup'])
def test_deployment_guard_checks_real_definitions_not_just_flag(monkeypatch,unsafe):
    from lixiviacion import phase_flags
    folder=ROOT/'auditorias/m6_adaptacion_directa_20261026';path=folder/('test_proof_'+str(uuid.uuid4())+'.json')
    proof={'execute_dev':True,'backup_verified_recoverable':unsafe!='no_backup','backup_reference':'FAKE_TEST_ONLY',
           'backup_sha256':'a'*64,'database_name':'inventar_SpcHidr','server_name':'VPS-5347319-X','new_period_publisher_tested':True,
           'consumers_review_passed':True}
    path.write_text(json.dumps(proof),encoding='utf8')
    monkeypatch.setenv('ENABLE_M6_DATOS_CONCILIADOS_DEV','1');monkeypatch.setenv('M6_DEV_BACKUP_EVIDENCE',str(path))
    monkeypatch.setattr(phase_flags,'is_dev',lambda:True);monkeypatch.setattr(phase_flags,'guard_connection',lambda c:None)
    conn=MagicMock()
    def execute(query,params):
        assert str(query).startswith('SELECT')
        filename='sp_rep_publish_oficial_validado_new_period.sql' if params['name'].endswith('sp_rep_publish_oficial_validado') else 'vw_datos_conciliados_reporte_srr.sql'
        value=(ROOT/'ajuste_reporte/sql'/filename).read_text(encoding='utf8')
        if unsafe=='old_delete' and filename.startswith('sp_'):value='CREATE PROCEDURE old AS DELETE FROM versions'
        if unsafe=='missing_view' and filename.startswith('vw_'):value=None
        result=Mock();result.scalar_one.return_value=value;return result
    conn.execute.side_effect=execute
    try:
        if unsafe=='safe':w._m6_standard_guard(Mock(),connection=conn)
        else:
            with pytest.raises(w.M6ValidationError):w._m6_standard_guard(Mock(),connection=conn)
    finally:path.unlink()

def test_m6_staging_batch_limit_without_changing_legacy_default(monkeypatch,bundle):
    _,p=bundle;calls=[]
    names=['Fecha']+w._m6_operational_columns(p)+['run_id','caso_id','version_reglas','ts_ajuste','factor_chancado','factor_sal','factor_finos','estado']
    monkeypatch.setattr(w,'get_table_columns',lambda *a:names)
    def capture(df,*args,**kwargs):calls.append((len(df.columns),kwargs))
    monkeypatch.setattr(pd.DataFrame,'to_sql',capture)
    w.write_staging(Mock(),p['datos'],uuid.UUID(p['run_id']),20001,1,None,parameter_limit=2000)
    assert calls[0][0]*calls[0][1]['chunksize']<=2000
    w.write_staging(Mock(),p['datos'],uuid.UUID(p['run_id']),20001,1,None)
    assert calls[1][1]['chunksize']==500

def test_120_standard_orchestration_keeps_its_merge_and_targets(monkeypatch,bundle):
    ctx,p=bundle;ctx=dict(ctx,modelo_id=1,modelo_codigo='hidrometalurgia_120_completo',total_flujos=120,legacy_modelo_id=1)
    engine=Mock();calls=[];build=Mock(return_value=p['targets'])
    monkeypatch.setattr(w,'get_engine',lambda:engine);monkeypatch.setattr(w,'get_solver_model_context',lambda *a:ctx)
    monkeypatch.setattr(w,'get_periodo_y_run_solver',lambda *a:(pd.Timestamp(ctx['fecha_inicio']),pd.Timestamp(ctx['fecha_fin']),ctx['solver_run_id']))
    monkeypatch.setattr(w,'build_targets_from_solver_nuevo',build)
    monkeypatch.setattr(w,'load_query1_all_cols',lambda *a:p['datos'])
    monkeypatch.setattr(w,'load_reglas',lambda *a:pd.DataFrame([{'regla_id':1}]))
    monkeypatch.setattr(w,'apply_rules',lambda *a:(p['datos'],{}))
    monkeypatch.setattr(w,'write_staging',lambda *a,**kw:None)
    monkeypatch.setattr(w,'exec_sql',lambda e,q,params:calls.append(q))
    monkeypatch.setattr(w,'_m6_standard_guard',lambda *a,**kw:pytest.fail('No llamar rutaM6 para120'))
    assert w.run_ajuste_reporte_prod_solver_nuevo(20001)['ok']
    build.assert_called_once_with(engine,20001,30001)
    assert any('sp_rep_merge_ajustado_dyn' in q for q in calls)

def test_even_legacy_cannot_call_old_destructive_publisher(monkeypatch,bundle):
    _,p=bundle;conn=MagicMock();engine=MagicMock();engine.begin.return_value.__enter__.return_value=conn
    conn.execute.return_value.scalar_one.return_value='CREATE PROCEDURE old AS DELETE FROM versions'
    monkeypatch.setattr(w,'get_engine',lambda:engine)
    monkeypatch.setattr(w,'read_sql_df',lambda *a,**k:pd.DataFrame([{'codigo':'hidrometalurgia_120_completo'}]))
    with pytest.raises(w.M6ValidationError,match='PUBLICADOR_NO_SEGURO'):w.publicar_run_oficial(7,p['run_id'],'legacy')
    assert all(str(call.args[0]).startswith('SELECT') for call in conn.execute.call_args_list)
