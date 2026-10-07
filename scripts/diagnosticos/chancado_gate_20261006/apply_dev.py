"""Apply official DEV SP gate and materialize October 1-4 atomically."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine

BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV database required')
snapshot=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
old_def=next(r['definition'] for r in snapshot['results']['definitions'] if r['name']=='sp_mantiene_datos_conciliados_emision_test')
alter=(BASE/'alter_sp_mantiene_datos_conciliados_emision_test.sql').read_text(encoding='utf-8')
if alter.count('END AS Chancado_TMS_Real,')!=1: raise RuntimeError('Unexpected ALTER')

select_dc=text("SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")
select_aj=text("SELECT Fecha,Apilado_TMS_Reporte,Sal_TMH_Dia,SRR_TMS_Dia,Delta_Inventario_Chancado_TMS,Chancado_TMS_Reporte FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")

engine=get_engine()
with engine.begin() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    if ident['server_name']!=snapshot['identity']['server_name'] or ident['database_name'].lower()!='inventar_spchidr':
        raise RuntimeError('Wrong DEV target')
    current=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    if current!=old_def: raise RuntimeError('SP changed since read-only snapshot')
    before=[dict(r) for r in conn.execute(select_dc).mappings()]
    aj_before=[dict(r) for r in conn.execute(select_aj).mappings()]
    if len(before)!=4 or len(aj_before)!=4: raise RuntimeError('October 1-4 rows missing')
    conn.exec_driver_sql(alter)
    conn.execute(text('''EXEC inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
        @FechaInicio='2026-10-01',@FechaFin='2026-10-04',@DiasReproceso=0,@RefrescarFactor=0'''))
    after=[dict(r) for r in conn.execute(select_dc).mappings()]
    aj_after=[dict(r) for r in conn.execute(select_aj).mappings()]
    actual_def=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    if len(after)!=4 or aj_before!=aj_after or 'END AS Chancado_TMS_Real,' not in actual_def:
        raise RuntimeError('Row count, source, or definition changed unexpectedly')
    for old,new,aj in zip(before,after,aj_after):
        if old['Fecha']!=new['Fecha'] or new['Fecha']!=aj['Fecha']: raise RuntimeError('Date alignment changed')
        unexpected=[k for k in old if k!='Chancado_TMS_Real' and old[k]!=new[k]]
        if unexpected: raise RuntimeError(f"Other Datos Conciliados fields changed on {new['Fecha']}: {unexpected}")
        gate=all(aj[k]==0 for k in ('Apilado_TMS_Reporte','Sal_TMH_Dia','SRR_TMS_Dia'))
        expected=0 if gate else aj['Chancado_TMS_Reporte']
        if new['Chancado_TMS_Real'] is None or abs(float(new['Chancado_TMS_Real'])-float(expected))>0.000001:
            raise RuntimeError(f"Unexpected Chancado on {new['Fecha']}")
        if not gate and old['Chancado_TMS_Real']!=new['Chancado_TMS_Real']:
            raise RuntimeError(f"Active-flow day changed on {new['Fecha']}")

out={'identity':ident,'before':before,'after':after,'ajuste_before':aj_before,'ajuste_after':aj_after,
     'definition_after':actual_def}
(BASE/'after.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,'updated_dates',[str(r['Fecha']) for r in after],
      'chancado_before_after',[(str(a['Fecha']),a['Chancado_TMS_Real'],b['Chancado_TMS_Real']) for a,b in zip(before,after)])
