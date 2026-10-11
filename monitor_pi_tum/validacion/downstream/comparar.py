"""Diagnóstico SELECT y ejecución de cuerpo de reporte con trazabilidad temporal.

No altera SP/vistas ni escribe tablas persistentes. Guarda SQL exacto ejecutado.
"""
import re
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection
from .inspeccionar import OUT,save

def body(sql):
    # Primer AS BEGIN posterior a cabecera del procedimiento.
    match=re.search(r'\bAS\s+BEGIN\b',sql,re.I)
    if not match:raise ValueError('Cabecera no reconocida')
    return sql[match.end()-5:]

def run(c,sql):
    cursor=c.connection.driver_connection.cursor()
    cursor.execute(sql)
    results=[]
    while True:
        if cursor.description:
            columns=[x[0] for x in cursor.description]
            results.append([dict(zip(columns,r)) for r in cursor.fetchall()])
        if not cursor.nextset():break
    cursor.close()
    return results[-1] if results else []

def main():
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        allmods=[dict(r) for r in c.execute(text("SELECT OBJECT_SCHEMA_NAME(object_id)+'.'+OBJECT_NAME(object_id) nombre,definition FROM sys.sql_modules")).mappings()]
        mods={r['nombre']:r['definition'] for r in allmods}
        deps=[dict(r) for r in c.execute(text("SELECT OBJECT_SCHEMA_NAME(referencing_id)+'.'+OBJECT_NAME(referencing_id) consumidor,referenced_database_name base,referenced_schema_name esquema,referenced_entity_name objeto FROM sys.sql_expression_dependencies")).mappings()]
        roots={'inventar_SpcHidr.'+n for n in ('v_reporte_diario_apilado_test','v_apilado_base_mina_stock_srr','v_apilado_proporcion_final_reporte_test')}
        for _ in range(15):
            new={str(r['esquema'])+'.'+str(r['objeto']) for r in deps if r['consumidor'] in roots and r['base'] in (None,'inventar_SpcHidr')}
            if new<=roots:break
            roots|=new
        for n in roots:
            if mods.get(n):(OUT/(n+'.sql')).write_text(mods[n],encoding='utf-8')
        save('callers_sql_historico',[r for r in deps if r['objeto']=='sp_refrescar_historico_apilado_test'])
        save('menciones_historico',[r for r in allmods if 'Historico_Apilado_Diario' in (r['definition'] or '') and 'srr_tag' not in r['nombre']])
        try:
            save('jobs_historico',[dict(r) for r in c.execute(text("SELECT j.name job,s.step_id,s.step_name,s.database_name,s.command FROM msdb.dbo.sysjobsteps s JOIN msdb.dbo.sysjobs j ON j.job_id=s.job_id WHERE s.command LIKE '%historico_apilado%' OR s.command LIKE '%mantiene_datos_conciliados%'")).mappings()])
        except Exception as e:save('jobs_historico',{'error':str(e)})
        for n in ('v_reporte_diario_apilado_test','Historico_Apilado_Diario','v_apilado_base_mina_stock_srr','v_apilado_proporcion_final_reporte_test','v_srr_tms_origen_turno_emision_test','v_ajuste_camiones_emision_test','Control_Apilado_TMH_v2_test','reporte_turno_cache_emision_test','factor_ajuste_camiones'):
            cols=c.execute(text('SELECT name FROM sys.columns WHERE object_id=OBJECT_ID(:n)'),{'n':'inventar_SpcHidr.'+n}).scalars().all()
            dc=next((x for x in cols if x.lower()=='fecha'),None)
            if dc:
                save('sept_'+n,[dict(r) for r in c.execute(text(f"SELECT * FROM inventar_SpcHidr.{n} WHERE [{dc}] BETWEEN '20260904' AND '20260910'")).mappings()])
                print(n,flush=True)
            else:save('sept_'+n,{'columnas':cols})
        original=mods['inventar_SpcHidr.sp_reporte_turno_emision_test']
        report=body(original)
        target='inventar_SpcHidr.trazabilidad_analitos_tm_emision_test'
        assert report.count(target)==2
        report=report.replace(target,'#traza_diagnostico')
        report="DECLARE @fecha_inicio date='20260904', @fecha_fin date='20260911';\n"+report
        (OUT/'reporte_directo_temporal.sql').write_text(report,encoding='utf-8')
        c.exec_driver_sql('SELECT TOP (0) * INTO #traza_diagnostico FROM '+target)
        save('sept_reporte_directo',run(c,report))
        c.rollback()
if __name__=='__main__':main()
