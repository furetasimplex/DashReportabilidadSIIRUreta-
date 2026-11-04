"""Capture a bounded SELECT-only snapshot for the requested case trial."""
import contextlib, hashlib, io, json, os, re, sys
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import event, text

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'DashReportabilidadSIIR'))
os.environ['RECON_SIN_CACHE']='1'
with contextlib.redirect_stdout(io.StringIO()):
    from curvas_recon import db_pipeline as db
    engine=db.get_engine()
assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',db.SCHEMA)
S=db.SCHEMA
@event.listens_for(engine,'do_connect')
def timeout(dialect,conn_rec,cargs,cparams): cparams['timeout']=10
@event.listens_for(engine,'before_cursor_execute')
def guard(conn,cursor,statement,parameters,context,executemany):
    sql=re.sub(r'/\*.*?\*/|--[^\n]*','',statement,flags=re.S).strip().lower()
    if not re.match(r'^(select|with)\b',sql) or re.search(r'\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke)\b',sql):
        raise RuntimeError('Non-SELECT statement blocked')

def rows(conn,sql,params=None):
    return [dict(r) for r in conn.execute(text(sql),params or {}).mappings()]

try:
    with engine.connect() as conn:
        conn.connection.driver_connection.timeout=30
        official=rows(conn,f'''WITH candidates AS (
            SELECT r.id AS allocation_run_id,r.caso_id AS case_id,d.label AS pad,d.parcela_nombre AS pile,
                CAST(DATEADD(day,d.dia_offset,r.semana_lunes) AS date) AS date,
                CAST(d.q AS float) AS q_riego_m3h,CAST(d.q_pls AS float) AS q_drenaje_m3h,
                CAST(d.cu_riego AS float) AS cu_riego_gL,CAST(d.cu_drena AS float) AS cu_drenaje_gL,
                ROW_NUMBER() OVER (PARTITION BY d.label,d.parcela_nombre,DATEADD(day,d.dia_offset,r.semana_lunes) ORDER BY r.id DESC,d.id DESC) AS ranking
            FROM {S}.reconciliacion_detalle_dia d JOIN {S}.reconciliacion_run r ON r.id=d.run_id
            WHERE DATEADD(day,d.dia_offset,r.semana_lunes)>=:history_start
              AND DATEADD(day,d.dia_offset,r.semana_lunes)<=:end
              AND (DATEADD(day,d.dia_offset,r.semana_lunes)<:start OR r.caso_id=:case)
        ) SELECT * FROM candidates WHERE ranking=1 ORDER BY pad,pile,date''',
            {'history_start':date(2026,8,1),'start':date(2026,9,1),'end':date(2026,9,7),'case':10009})
        measurements={}
        for name,table,field in [('riego','riego_diario','caudal_m3h'),('drena_cu','drena_cu_diario','cu_gl')]:
            measurements[name]=rows(conn,f'''SELECT CAST(v.fecha AS date) AS date,p.nombre AS pile,CAST(v.{field} AS float) AS value
                FROM {S}.{table} v JOIN {S}.parcela p ON p.id_parcela=v.parcela_id
                JOIN {S}.material m ON m.id=p.id_pad
                WHERE m.nombre='SULFURO' AND v.fecha>=:start AND v.fecha<=:end''',
                {'start':date(2026,9,1),'end':date(2026,9,7)})
        measurements['cu_riego']=rows(conn,f'''SELECT CAST(c.fecha AS date) AS date,CAST(c.cu_gl AS float) AS value
            FROM {S}.cu_riego_diario c JOIN {S}.material m ON m.id=c.material_id
            WHERE m.nombre='SULFURO' AND c.fecha>=:start AND c.fecha<=:end''',
            {'start':date(2026,9,1),'end':date(2026,9,7)})
        measurements['riego_ingest']=rows(conn,f'''SELECT CAST(v.fecha AS date) AS date,p.nombre AS pile,CAST(v.caudal_m3h AS float) AS value
            FROM {S}.vw_riego_diario_ingest v JOIN {S}.parcela p ON p.id_parcela=v.parcela_id JOIN {S}.material m ON m.id=p.id_pad
            WHERE m.nombre='SULFURO' AND v.fecha>=:start AND v.fecha<=:end''',{'start':date(2026,9,1),'end':date(2026,9,7)})
        measurements['drena_cu_ingest']=rows(conn,f'''SELECT CAST(v.fecha AS date) AS date,p.nombre AS pile,CAST(v.cu_gl AS float) AS value
            FROM {S}.vw_drena_quimica_ingest v JOIN {S}.parcela p ON p.id_parcela=v.parcela_id JOIN {S}.material m ON m.id=p.id_pad
            WHERE m.nombre='SULFURO' AND v.fecha>=:start AND v.fecha<=:end''',{'start':date(2026,9,1),'end':date(2026,9,7)})
        measurements['cu_riego_ingest']=rows(conn,f'''SELECT CAST(fecha AS date) AS date,CAST(cu_pp AS float) AS value
            FROM {S}.vw_riego_sulfuro_refino_base WHERE fecha>=:start AND fecha<=:end''',{'start':date(2026,9,1),'end':date(2026,9,7)})
        drainage_columns=rows(conn,'''SELECT o.name AS object_name,c.name AS column_name
            FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.columns c ON c.object_id=o.object_id
            WHERE s.name=:schema AND o.type IN ('U','V') AND o.name LIKE '%drena%'
                AND (c.name LIKE '%caudal%' OR c.name IN ('q','q_pls','caudal_m3h'))''',{'schema':S})
    # Bypass the persistent read cache; anchor helper contains SELECT only.
    def direct_rows(engine,statement,params,**kwargs):
        with engine.connect() as conn: return conn.execute(statement,params).fetchall()
    db._sql_rows=direct_rows
    cases=db.load_casos()
    case=next(c for c in cases if c['id']==10009)
    with contextlib.redirect_stdout(io.StringIO()):
        anchor=db.load_caso_anchor(case['run_id'],case['modelo_codigo'],case['modelo_version'],case['total_flujos'])
    payload={'metadata':{'case':case,'captured_at':datetime.now().isoformat(),'database_writes':False,
        'allocation_solver_link':'Allocation table does not store originating solver_run_id; latest rows per date are reference, not a verified solver linkage.',
        'measurement_policy':'Raw daily readings; no forward fill or fabricated concentrations.'},
        'official':official,'measurements':measurements,'drainage_flow_source_columns':drainage_columns,'anchor':anchor}
    encoded=json.dumps(payload,default=str,ensure_ascii=False,indent=2).encode('utf-8')
    (OUT/'case10009_select_snapshot.json').write_bytes(encoded)
    print(json.dumps({'case':10009,'solver_run':case['run_id'],'allocation_runs':sorted({r['allocation_run_id'] for r in official if r['case_id']==10009}),
        'official_rows':len(official),'measurements':{k:len(v) for k,v in measurements.items()},'drainage_flow_columns':drainage_columns,
        'sha256':hashlib.sha256(encoded).hexdigest()},default=str))
except Exception as exc:
    print(json.dumps({'status':'capture_failed','error_type':type(exc).__name__}))
    sys.exit(1)
