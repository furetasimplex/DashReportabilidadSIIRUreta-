"""Focused, read-only rows for the official Malla pipeline."""
import json, os, sys
from pathlib import Path
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3]; sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV only')
queries={
 'rep': "SELECT * FROM inventar_SpcHidr.v_representatividad_diaria_calculada WHERE Dia='2026-10-04'",
 'validada': "SELECT Fecha,Turno,TM,Representatividad_TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2 FROM inventar_SpcHidr.v_leyes_validadas_tm_turno WHERE Fecha='2026-10-04'",
 'base': "SELECT Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2 FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test WHERE Fecha='2026-10-04'",
 'seed': "SELECT * FROM inventar_SpcHidr.analitos_semilla_reporte_turno WHERE fecha='2026-10-04' AND analito='Malla_Menos_1_2'",
 'last_tm2': "SELECT TOP (8) Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2 FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test WHERE Fecha <= '2026-10-04' AND TM='TM2' AND Fuente_Malla_Menos_1_2 IN ('TORRE_MISMO_TURNO','SEMILLA_INICIO_PERIODO') AND Malla_Menos_1_2 <> 0 ORDER BY Fecha DESC,Turno DESC",
 'last_tm1': "SELECT TOP (5) Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2 FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test WHERE Fecha <= '2026-10-04' AND TM='TM1' AND Fuente_Malla_Menos_1_2 IN ('TORRE_MISMO_TURNO','SEMILLA_INICIO_PERIODO') AND Malla_Menos_1_2 <> 0 ORDER BY Fecha DESC,Turno DESC",
 'malla_catalog': "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name object_name,o.type_desc,c.name column_name FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id WHERE c.name LIKE '%Malla%1%2%' OR c.name LIKE '%Pasante_1_2%' OR c.name LIKE '%porc_1_2%' ORDER BY schema_name,object_name,column_name",
 'near_lab': "SELECT Fecha,Turno,Torre,Pasante_1_2P,Fecha_Carga,ID_Registro FROM inventar_SpcHidr.Informe_TM_lab WHERE Fecha >= '2026-10-01' AND Fecha < '2026-10-07' ORDER BY Fecha,Turno,Torre",
 'rep_03': "SELECT * FROM inventar_SpcHidr.v_representatividad_diaria_calculada WHERE Dia='2026-10-03'",
 'real_03': "SELECT * FROM inventar_SpcHidr.v_peso_real_torre_turno_excel WHERE Fecha='2026-10-03' AND Turno='B' AND Torre='T2'",
 'teo_03': "SELECT * FROM inventar_SpcHidr.v_peso_teorico_turno_torre_excel WHERE Fecha='2026-10-03' AND Turno='B' AND Torre='T2'",
 'base_03': "SELECT Fecha,Turno,TM,Malla_Menos_1_2,Fuente_Malla_Menos_1_2 FROM inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test WHERE Fecha='2026-10-03' AND TM='TM2'",
 'lab_28': "SELECT Fecha,Turno,Torre,Pasante_1_2P,Fecha_Carga,ID_Registro FROM inventar_SpcHidr.Informe_TM_lab WHERE Fecha='2026-09-28' AND Turno='B' AND Torre='T2'",
}
with get_engine().connect() as c:
    ident=dict(c.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('wrong DB')
    result={}
    for name,q in queries.items():
        print('QUERY',name,flush=True)
        try: result[name]=[dict(x) for x in c.execute(text(q)).mappings()]
        except Exception as exc: result[name]={'error':str(exc)}
(BASE/'followup.json').write_text(json.dumps({'identity':ident,'queries':result},default=str,ensure_ascii=False,indent=2),encoding='utf-8')
for k,v in result.items(): print(k, len(v) if isinstance(v,list) else v['error'][:200])
