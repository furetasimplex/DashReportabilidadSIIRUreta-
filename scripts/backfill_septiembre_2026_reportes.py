"""BACKFILL EXTRAORDINARIO — NO USAR COMO RUNTIME. Septiembre 2026, solo DEV.

La ejecución permanece bloqueada mientras no se complete la revisión de prechecks.
El modo predeterminado solamente consulta y respalda; no invoca ningún refresco.
"""
import argparse
from collections import Counter
from datetime import date, timedelta, datetime
import hashlib
import json
import os
import time
from pathlib import Path
from sqlalchemy import text
from db_connection import get_engine

P = Path(__file__).parent/'diagnosticos/backfill_reportes_septiembre_2026'
START, END = date(2026,9,1), date(2026,9,30)
TABLES = {'Resumen_Intervalo_TotTM':'fecha_turno', 'BD_Ton':'Fecha',
 'representatividad_torres_resultado':'Dia', 'Control_Apilado_TMH_v2_test':'Fecha',
 'Control_Factor_Ajuste_Camiones_v2_test':'Fecha','Historico_Apilado_Diario':'Fecha',
 'Clays_CuFe':'Fecha','Clays_CuFe_trazabilidad':'Fecha',
 'trazabilidad_analitos_tm_emision_test':'Fecha','reporte_turno_cache_emision_test':'Fecha',
 'Datos_conciliados_of':'Fecha'}

def save(name,obj):
    (P/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')

def blocks(days):
    result=[]; day=START
    while day<=END:
        end=min(day+timedelta(days=days-1),END)
        result.append({'desde':str(day),'hasta':str(end)})
        day=end+timedelta(days=1)
    return result

def read(name):
    return json.loads((P/name).read_text(encoding='utf-8'))

def validate(c, phase):
    checks={}
    specs={'representatividad':[('representatividad_torres_resultado','Dia',1),('BD_Ton','Fecha',1),('Resumen_Intervalo_TotTM','fecha_turno',6)],
           'analisis_tm':[('reporte_turno_cache_emision_test','Fecha',2)],
           'datos_conciliados':[('Datos_conciliados_of','Fecha',1)]}
    for table,col,expected in specs[phase]:
        counts=[dict(r) for r in c.execute(text(f'SELECT CAST([{col}] AS date) AS fecha,COUNT(*) AS filas FROM inventar_SpcHidr.[{table}] WHERE [{col}]>=:a AND [{col}]<=:b GROUP BY CAST([{col}] AS date) ORDER BY fecha'),{'a':START,'b':END}).mappings()]
        checks[table]={'por_fecha':counts,'pass':len(counts)==30 and all(r['filas']==expected for r in counts)}
    if phase=='analisis_tm':
        dup=c.execute(text("SELECT COUNT(*) FROM (SELECT Fecha,Turno FROM inventar_SpcHidr.reporte_turno_cache_emision_test WHERE Fecha BETWEEN :a AND :b GROUP BY Fecha,Turno HAVING COUNT(*)<>1) x"),{'a':START,'b':END}).scalar_one()
        checks['duplicados_fecha_turno']={'cantidad':dup,'pass':dup==0}
    if phase=='datos_conciliados':
        # Reutilizar el validador de contrato aplicado/publicado ya existente.
        from report_export.report_export import fetch_balance_chancado_report
        from report_export.export_to_excel import _validar_balance_chancado
        balance=fetch_balance_chancado_report(START,END,conn=c)
        _validar_balance_chancado(balance)
        checks['balance_con_validacion_runtime']={'filas':len(balance),'pass':len(balance)==30}
    status='PASS' if all(v['pass'] for v in checks.values()) else 'FAIL'
    result={'estado':status,'checks':checks,'alcance':'Cobertura/grano y validadores runtime; UI/export se informa por separado.'}
    save('validacion_'+phase+'.json',result)
    if status!='PASS':raise RuntimeError('Validacion fallida: '+phase)
    return result

def execute():
    from report_export import report_export as r
    pre=read('precheck.json')
    if pre.get('estado')!='PASS':raise RuntimeError('Precheck no PASS')
    if (P/'ejecucion.json').exists():raise RuntimeError('Ya existe ejecución; no reanudar automáticamente')
    for path,h in read('runtime_before.json').items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=h:raise RuntimeError('Runtime cambió: '+path)
    with get_engine().connect() as c:
        assert c.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        for obj in read('objects.json'):
            if 'sha256' not in obj:continue
            ddl=c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),{'n':obj['schema_name']+'.'+obj['name']}).scalar_one()
            if not ddl or hashlib.sha256(ddl.encode()).hexdigest()!=obj['sha256']:raise RuntimeError('DDL cambió: '+obj['name'])
    log={'estado':'EN_CURSO','db':'inventar_SpcHidr','bloques':[]};save('ejecucion.json',log)
    helpers={'representatividad':r.refrescar_representatividad_para_exportacion,'analisis_tm':r.refrescar_dependencias_reporte_turno_emision,'datos_conciliados':r.refrescar_dependencias_datos_conciliados_emision}
    try:
        for phase,helper in helpers.items():
            for block in read('plan_bloques.json')[phase]:
                a,b=date.fromisoformat(block['desde']),date.fromisoformat(block['hasta'])
                if not START<=a<=b<=END:raise RuntimeError('Fuera de septiembre')
                entry={**block,'reporte':phase,'helper':helper.__name__,'inicio':datetime.now().isoformat(),'estado':'INICIADO'}
                log['bloques'].append(entry);save('ejecucion.json',log);t=time.monotonic()
                print('INICIO',phase,a,b,flush=True)
                try:
                    result=helper(a,b)
                    entry.update(estado='COMMIT',resultado=result,fin=datetime.now().isoformat(),duracion_segundos=time.monotonic()-t)
                    print('COMMIT',phase,a,b,round(time.monotonic()-t,2),flush=True)
                except Exception as e:
                    entry.update(estado='ERROR_DETENIDO',error=str(e),fin=datetime.now().isoformat(),duracion_segundos=time.monotonic()-t)
                    raise
                finally:save('ejecucion.json',log)
            with get_engine().connect() as c:validate(c,phase)
        log['estado']='BACKFILL_PASS_PENDIENTE_UI'
    except Exception as e:
        log.update(estado='DETENIDO',error=str(e));raise
    finally:save('ejecucion.json',log)

def snapshot(c):
    result={}; (P/'backup_logico').mkdir(exist_ok=True)
    for table,col in TABLES.items():
        rows=[dict(r) for r in c.execute(text(f'SELECT * FROM inventar_SpcHidr.[{table}] WHERE [{col}]>=:a AND [{col}]<:b'),{'a':START,'b':END+timedelta(days=1)}).mappings()]
        encoded=sorted(json.dumps(r,default=str,sort_keys=True,ensure_ascii=False) for r in rows)
        daily={}
        for day in sorted({str(r[col])[:10] for r in rows}):
            dayrows=sorted(json.dumps(r,default=str,sort_keys=True,ensure_ascii=False) for r in rows if str(r[col])[:10]==day)
            daily[day]={'count':len(dayrows),'sha256':hashlib.sha256('\n'.join(dayrows).encode()).hexdigest()}
        result[table]={'count':len(rows),'por_fecha':daily,'sha256':hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}
        save('backup_logico/'+table+'.json',rows)
        print(table,len(rows),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr':raise RuntimeError('Solo DEV')
    if args.execute:return execute()
    if (P/'before.json').exists():raise RuntimeError('No sobrescribir snapshot previo; revisar evidencia existente.')
    plan={'periodo':[str(START),str(END)],'representatividad':blocks(7),'analisis_tm':blocks(7),'datos_conciliados':blocks(15),'ejecuciones_planeadas':12,'criterio':'Ventanas runtime de recálculo 7/7/15; no son máximos generales de rango.'}
    save('plan_bloques.json',plan)
    from report_export.report_export import fetch_fecha_corte_operacional_representatividad, fetch_fecha_corte_apilado_tmh_report
    with get_engine().connect() as c:
        assert c.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        print('DB objetivo: inventar_SpcHidr (DEV); solo SELECT',flush=True)
        cortes={'representatividad':fetch_fecha_corte_operacional_representatividad(START,END,conn=c),'apilado':fetch_fecha_corte_apilado_tmh_report(START,END,conn=c)}
        cobertura=[dict(r) for r in c.execute(text("SELECT fecha_turno,COUNT(*) AS registros,COUNT(DISTINCT CONCAT(Torre,'|',turno_op)) AS claves,MAX(ts_fin) AS fin_dia FROM inventar_SpcHidr.v_bitacora_rangos_norm WHERE fecha_turno>=:a AND fecha_turno<=:b AND Torre IN ('T1','T2','SRR') GROUP BY fecha_turno ORDER BY fecha_turno"),{'a':START,'b':END}).mappings()]
        pi=[dict(r) for r in c.execute(text("SELECT * FROM inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno WHERE fecha_operacional>=:a AND fecha_operacional<=:b AND equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108') AND turno IN ('A','B')"),{'a':START,'b':END}).mappings()]
        save('fuente_pi_tum.json',pi)
        pre={'estado':'PENDIENTE_REVISION','cortes':cortes,'cobertura_bitacora':cobertura,'filas_pi_tum':len(pi),'max_totalizador':c.execute(text('SELECT MAX(fecha) FROM inventar_SpcHidr.tot_TM')).scalar_one(),'octubre_corte_readonly':fetch_fecha_corte_operacional_representatividad(date(2026,10,1),date(2026,10,31),conn=c)}
        save('precheck.json',pre)
        save('before.json',snapshot(c))
        print(json.dumps({'cortes':cortes,'plan':plan},default=str,ensure_ascii=False))

if __name__=='__main__':main()
