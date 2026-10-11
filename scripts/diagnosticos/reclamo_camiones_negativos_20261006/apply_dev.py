"""Apply the reviewed one-expression ALTER to DEV and capture read-only post evidence."""
import csv
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine

BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr':
    raise RuntimeError('DEV database required')
before=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
old=next(r['definition'] for r in before['results']['definitions'] if r['name']=='v_cuadratura_modulo')
new=(BASE/'alter_v_cuadratura_modulo.sql').read_text(encoding='utf-8')
if new.count('SELECT TOP (1) c.m3_camiones_acum')!=1 or 'SELECT MAX(c.m3_camiones_acum)' in new:
    raise RuntimeError('Unexpected ALTER contents')

engine=get_engine()
with engine.begin() as conn:
    identity=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    if identity['server_name']!=before['identity']['server_name'] or identity['database_name'].lower()!='inventar_spchidr':
        raise RuntimeError('DEV identity changed')
    current=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cuadratura_modulo'))")).scalar_one()
    if current!=old:
        raise RuntimeError('View changed since before snapshot')
    conn.exec_driver_sql(new)
    after_def=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cuadratura_modulo'))")).scalar_one()
    if 'SELECT TOP (1) c.m3_camiones_acum' not in after_def or 'ORDER BY c.fecha DESC' not in after_def:
        raise RuntimeError('ALTER definition verification failed')
    rows=[dict(r) for r in conn.execute(text('SELECT * FROM reclamo.v_cuadratura_modulo ORDER BY campaña_id,modulo_id')).mappings()]
    cam=[dict(r) for r in conn.execute(text('SELECT fecha,campaña_id,modulo_id,m3_camiones_dia,m3_camiones_acum,tms_camiones_dia,tms_camiones_acum FROM reclamo.v_camiones_acumulado WHERE campaña_id=10 AND modulo_id IN (81,87) ORDER BY modulo_id,fecha')).mappings()]

after={'identity':identity,'definition':after_def,'cuadratura':rows,'camiones':cam}
(BASE/'after.json').write_text(json.dumps(after,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
old_rows={(r['campaña_id'],r['modulo_id']):r for r in before['results']['cuadratura']}
new_rows={(r['campaña_id'],r['modulo_id']):r for r in rows}
if old_rows.keys()!=new_rows.keys() or len(rows)!=len(new_rows):
    raise RuntimeError('Unexpected row count or duplicate campaign/module')
fields=['m3_camiones_sistema','m3_camiones_total','m3_extraido_total','porcentaje_extraido','m3_saldo_disponible']
with (BASE/'before_after.csv').open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f)
    writer.writerow(['campaña_id','modulo_id','modulo_numero']+[x+'_'+s for x in fields for s in ('before','after','delta')])
    for key in sorted(old_rows):
        a,b=old_rows[key],new_rows[key]
        record=[*key,a['modulo_numero']]
        for field in fields:
            va,vb=a[field],b[field]
            record.extend([va,vb,None if va is None or vb is None else float(vb)-float(va)])
        writer.writerow(record)
changed=[key for key in old_rows if any(str(old_rows[key][f])!=str(new_rows[key][f]) for f in fields)]
print(identity,'rows',len(rows),'changed_modules',changed,'negative_rows_before',len(before['results']['negative_camiones']))
