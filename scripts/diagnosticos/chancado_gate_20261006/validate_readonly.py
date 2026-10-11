"""Read-only official balance and five-case regression for Chancado gate."""
import json
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine
from report_export.report_export import fetch_balance_chancado_report
from report_export.export_to_excel import _validar_balance_chancado, _agregar_hoja_balance_chancado

BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV database required')
before=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
after=json.loads((BASE/'after.json').read_text(encoding='utf-8'))
balance=fetch_balance_chancado_report(date(2026,10,1),date(2026,10,4))
_validar_balance_chancado(balance.copy())
wb=Workbook()
_agregar_hoja_balance_chancado(wb,balance.copy())
preview=BASE/'balance_chancado_dev_preview.xlsx'
wb.save(preview)
rendered=load_workbook(preview,read_only=True,data_only=True)['Balance Chancado']
assert [rendered.cell(5,c).value for c in (7,8,9,10,11)]==[
    'Apilado TMS neto aplicado','Variación inventario TMS','Sal','SRR TMS Balance','Chancado TMS']
assert [rendered.cell(r,11).value for r in (6,7)]==[0,0]
assert abs(rendered.cell(6,8).value-147.51238555955297)<1e-6
assert abs(rendered.cell(7,8).value+133.40134699605733)<1e-6
rows=[]
for row in balance.to_dict('records'):
    day=pd.Timestamp(row['Fecha']).strftime('%Y-%m-%d')
    expected=next(x for x in after['after'] if x['Fecha']==day)
    source=next(x for x in after['ajuste_after'] if x['Fecha']==day)
    assert abs(float(row['Chancado_TMS_Real'])-float(expected['Chancado_TMS_Real']))<1e-6
    for field in ('Apilado_TMS_Reporte','Sal_TMH_Dia','SRR_TMS_Dia','Delta_Inventario_Chancado_TMS'):
        assert abs(float(row[field])-float(source[field]))<1e-6
    rows.append({'Fecha':day,'Apilado':row['Apilado_TMS_Reporte'],
                 'Sal':row['Sal_TMH_Dia'],'SRR':row['SRR_TMS_Dia'],
                 'Delta_Inventario':row['Delta_Inventario_Chancado_TMS'],
                 'Chancado_Calculado':row['Chancado_TMS_Reporte'],
                 'Chancado_Real':row['Chancado_TMS_Real']})
assert [float(r['Chancado_Real'])==0 for r in rows[:2]]==[True,True]
for r in rows[2:]: assert abs(float(r['Chancado_Calculado'])-float(r['Chancado_Real']))<1e-6

cases=[('delta_positivo',0,0,0,147.512,0),
       ('delta_negativo',0,0,0,-133.401,0),
       ('flujos_tres',1000,100,500,20,520),
       ('solo_sal',0,100,0,20,20),
       ('solo_srr',0,0,500,20,-480)]
synthetic=pd.concat([balance.iloc[[0]].copy() for _ in cases],ignore_index=True)
for i,(name,ap,sal,srr,delta,real) in enumerate(cases):
    synthetic.at[i,'Fecha']=pd.Timestamp(date(2026,1,i+1))
    synthetic.at[i,'Apilado_TMS_Reporte']=ap
    synthetic.at[i,'Sal_TMH_Dia']=sal
    synthetic.at[i,'SRR_TMS_Dia']=srr
    synthetic.at[i,'Delta_Inventario_Chancado_TMS']=delta
    synthetic.at[i,'Chancado_TMS_Reporte']=ap+delta-srr
    synthetic.at[i,'Chancado_TMS_Real']=real
    synthetic.at[i,'Diferencia_vs_Datos_Conciliados']=ap+delta-srr-real
_validar_balance_chancado(synthetic)

hist=[r for r in before['results']['ajuste_hist']
      if r['Apilado_TMS_Reporte']==0 and r['Sal_TMH_Dia']==0 and r['SRR_TMS_Dia']==0
      and r['Delta_Inventario_Chancado_TMS'] not in (0,None)]
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    definition=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    sql_cases=[dict(r) for r in conn.execute(text('''SELECT nombre,
        CASE WHEN apilado=0 AND sal=0 AND srr=0 THEN 0 ELSE calculado END AS reportable
        FROM (VALUES
            ('delta_positivo',0.0,0.0,0.0,147.512,0.0),
            ('delta_negativo',0.0,0.0,0.0,-133.401,0.0),
            ('flujos_tres',1000.0,100.0,500.0,520.0,520.0),
            ('solo_sal',0.0,100.0,0.0,20.0,20.0),
            ('solo_srr',0.0,0.0,500.0,-480.0,-480.0),
            ('nulo_desconocido',CAST(NULL AS float),0.0,0.0,20.0,20.0)
        ) AS c(nombre,apilado,sal,srr,calculado,esperado)''')).mappings()]
if (ident['database_name'].lower()!='inventar_spchidr'
        or definition.count('ch.Chancado_TMS_Real')!=3
        or definition.count('aj.Chancado_TMS_Reporte')!=1):
    raise RuntimeError('DEV SP not installed')
assert [r['nombre'] for r in sql_cases]==[c[0] for c in cases]+['nulo_desconocido']
assert [float(r['reportable']) for r in sql_cases]==[c[-1] for c in cases]+[20]
out={'identity':ident,'october':rows,'synthetic_cases':[c[0] for c in cases],
     'sql_cases':sql_cases,
     'historical_affected':[{'Fecha':r['Fecha'],'Antes':r['Chancado_TMS_Reporte'],
                             'Esperado':0,'Delta_Inventario':r['Delta_Inventario_Chancado_TMS']} for r in hist]}
(BASE/'validation.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print('PASS balance_rows',len(rows),'synthetic_cases',len(cases),'historical_affected',len(hist),
      'dates',[r['Fecha'] for r in hist])
