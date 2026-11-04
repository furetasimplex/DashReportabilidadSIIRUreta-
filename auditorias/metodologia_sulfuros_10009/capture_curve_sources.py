"""SELECT-only curve/control supplement, no synchronization or saved runs."""
import contextlib,hashlib,io,json,re,sys
from pathlib import Path
from sqlalchemy import event,text
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT.parent/'DashReportabilidadSIIR'))
with contextlib.redirect_stdout(io.StringIO()):
 from curvas_recon import db_pipeline as db
 engine=db.get_engine()
S=db.SCHEMA
assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',S)
@event.listens_for(engine,'do_connect')
def timeout(dialect,conn_rec,cargs,cparams): cparams['timeout']=10
@event.listens_for(engine,'before_cursor_execute')
def guard(conn,cursor,statement,parameters,context,executemany):
 sql=re.sub(r'/\*.*?\*/|--[^\n]*','',statement,flags=re.S).strip().lower()
 if not re.match(r'^(select|with)\b',sql) or re.search(r'\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call|grant|revoke)\b',sql): raise RuntimeError('Non-SELECT blocked')
def rows(conn,sql): return [dict(r) for r in conn.execute(text(sql)).mappings()]
try:
 with engine.connect() as conn:
  conn.connection.driver_connection.timeout=30
  out={}
  out['observed_consolidated']=rows(conn,f'''SELECT p.nombre AS pile,CAST(r.fecha AS date) AS date,CAST(r.valor_pct AS float) AS value_pct
   FROM {S}.lectura_recuperacion r JOIN {S}.parcela p ON p.id_parcela=r.parcela_id
   WHERE p.id_pad=2 AND r.fecha>='2026-08-01' AND r.fecha<='2026-09-07' ORDER BY p.nombre,r.fecha''')
  out['observed_primary']=rows(conn,f'''SELECT TRY_CAST(Parcela AS int) AS pile_number,CAST(Fecha_drenaje AS date) AS date,CAST(Recuperacion_parcela AS float) AS value_pct
   FROM {S}.Recuperaciones_pad WHERE PAD='SULFUROS' AND Fecha_drenaje>='2026-08-01' AND Fecha_drenaje<='2026-09-07'
   AND Recuperacion_parcela IS NOT NULL ORDER BY Parcela,Fecha_drenaje''')
  out['campaign_copper']=rows(conn,f'''SELECT TRY_CAST(Parcela AS int) AS pile_number,TRY_CAST(Campana AS int) AS campaign,
   MIN(CAST(Fecha AS date)) AS first_stacking,MAX(CAST(Fecha AS date)) AS last_stacking,SUM(CAST(Finos_cut AS float)) AS cu_apilado_t
   FROM {S}.modulos_turnos WHERE pad_id=2 AND Fecha<='2026-09-07' AND Parcela IS NOT NULL AND Campana IS NOT NULL
   GROUP BY TRY_CAST(Parcela AS int),TRY_CAST(Campana AS int)''')
  out['control_dates']=rows(conn,f'''WITH dedup AS (
   SELECT pad_id,TRY_CAST(nombre_parcela AS int) AS pile_number,TRY_CAST(numero_campana AS int) AS campaign,
    modulo_id,fecha_ini_drenaje,fecha_fin_drenaje,
    ROW_NUMBER() OVER (PARTITION BY pad_id,nombre_parcela,numero_campana,modulo_id ORDER BY id_campana_parcela_control DESC) AS rn
   FROM {S}.campana_parcela_control WHERE pad_id=2 AND fecha_ini_drenaje<='2026-09-07')
   SELECT pile_number,campaign,MIN(CAST(fecha_ini_drenaje AS date)) AS first_module_drainage,
    CASE WHEN COUNT(*)=COUNT(fecha_fin_drenaje) THEN MAX(CAST(fecha_fin_drenaje AS date)) END AS last_module_drainage
   FROM dedup WHERE rn=1 GROUP BY pile_number,campaign''')
 out['metadata']={'database_writes':False,'note':'Control drain start is not irrigation birth. Copper from SUM(Finos_cut), not cut_tm_total grade.'}
 data=json.dumps(out,default=str,ensure_ascii=False,indent=2).encode()
 Path(__file__).with_name('case10009_curve_sources.json').write_bytes(data)
 print(json.dumps({'status':'ok','counts':{k:len(v) for k,v in out.items() if isinstance(v,list)},'sha256':hashlib.sha256(data).hexdigest()}))
except Exception as exc:
 print(json.dumps({'status':'failed','error_type':type(exc).__name__})); sys.exit(1)

