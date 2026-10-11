"""Deploy official SP gate and update only its final materialized field in DEV."""
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
select_dc=text("SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")
select_aj=text("SELECT Fecha,Apilado_TMS_Reporte,Sal_TMH_Dia,SRR_TMS_Dia,Delta_Inventario_Chancado_TMS,Chancado_TMS_Reporte FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")

with get_engine().begin() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    if ident['server_name']!=snapshot['identity']['server_name'] or ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong DEV target')
    current=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    if current!=old_def: raise RuntimeError('SP changed since audit')
    before=[dict(r) for r in conn.execute(select_dc).mappings()]
    aj_before=[dict(r) for r in conn.execute(select_aj).mappings()]
    if len(before)!=4 or len(aj_before)!=4: raise RuntimeError('Missing October rows')
    target=[r for r in aj_before if r['Apilado_TMS_Reporte']==0 and r['Sal_TMH_Dia']==0 and r['SRR_TMS_Dia']==0]
    if [str(r['Fecha']) for r in target]!=['2026-10-01','2026-10-02']: raise RuntimeError('Unexpected gate dates')
    conn.exec_driver_sql(alter)
    # Materialize just the reportable output. The full SP refresh would also
    # alter unrelated Reclamo columns due to independently changed source data.
    changed=conn.execute(text('''UPDATE dc SET Chancado_TMS_Real=0
        FROM inventar_SpcHidr.Datos_conciliados_of dc
        JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test aj ON aj.Fecha=dc.Fecha
        WHERE dc.Fecha BETWEEN '2026-10-01' AND '2026-10-04'
          AND aj.Apilado_TMS_Reporte=0 AND aj.Sal_TMH_Dia=0 AND aj.SRR_TMS_Dia=0
          AND dc.Chancado_TMS_Real=aj.Chancado_TMS_Reporte
          AND dc.Chancado_TMS_Real<>0''')).rowcount
    if changed!=2: raise RuntimeError(f'Expected two updates, found {changed}')
    after=[dict(r) for r in conn.execute(select_dc).mappings()]
    aj_after=[dict(r) for r in conn.execute(select_aj).mappings()]
    new_def=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    if aj_before!=aj_after or 'END AS Chancado_TMS_Real,' not in new_def: raise RuntimeError('Source/definition verification failed')
    for a,b in zip(before,after):
        if a['Fecha']!=b['Fecha']: raise RuntimeError('Date alignment changed')
        unexpected=[k for k in a if k!='Chancado_TMS_Real' and a[k]!=b[k]]
        if unexpected: raise RuntimeError(f"Other columns changed on {a['Fecha']}: {unexpected}")
        expected=0 if str(a['Fecha']) in ('2026-10-01','2026-10-02') else a['Chancado_TMS_Real']
        if b['Chancado_TMS_Real']!=expected: raise RuntimeError(f"Unexpected Chancado on {a['Fecha']}")
out={'identity':ident,'before':before,'after':after,'ajuste_before':aj_before,'ajuste_after':aj_after,'definition_after':new_def}
(BASE/'after.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,'updated_rows',changed,'chancado',[(str(a['Fecha']),a['Chancado_TMS_Real'],b['Chancado_TMS_Real']) for a,b in zip(before,after)])
