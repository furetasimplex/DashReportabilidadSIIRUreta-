"""Simulación con cuerpos SQL vigentes y tablas # locales; nunca escribe tablas DEV.

Redirecciones documentadas: Histórico, factor, cache y trazabilidad a temporales.
No crea/altera procedimientos o vistas. ROLLBACK al cerrar cada escenario.
"""
import re
import argparse
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection
from .inspeccionar import OUT,save
from .comparar import body,run

def sql(n):return (OUT/('inventar_SpcHidr.'+n+'.sql')).read_text(encoding='utf-8')
def ref(s,n,t):return re.sub(r'\[?inventar_SpcHidr\]?\s*\.\s*\[?'+re.escape(n)+r'\]?',lambda _:t,s,flags=re.I)
def view(n):return re.split(r'\bAS\b',sql(n),maxsplit=1,flags=re.I)[1]
def dynamic(s):return "EXEC sys.sp_executesql N'"+s.replace("'","''")+"';"
def factor_sql():
    calc=ref(ref(body(sql('sp_factor_ajuste_camiones_test')),'Historico_Apilado_Diario','#hist'),'v_srr_tms_origen_turno_emision_test','#srr')
    calc="DECLARE @FechaInicio date='20260910',@FechaFin date='20260910';\n"+calc
    keeper=ref(ref(body(sql('sp_mantiene_factor_ajuste_camiones_v2_test')),'Control_Factor_Ajuste_Camiones_v2_test','#factor'),'v_srr_tms_origen_turno_emision_test','#srr')
    keeper=keeper.replace("'#factor'", "'tempdb..#factor'")
    keeper,n=re.subn(r'EXEC\s+\[inventar_SpcHidr\]\.\[sp_factor_ajuste_camiones_test\]\s+@FechaInicio\s*=\s*@FechaInicioProceso,\s*@FechaFin\s*=\s*@FechaFin;',lambda _:dynamic(calc),keeper,flags=re.I)
    assert n==1
    return "DECLARE @FechaInicio date='20260910',@FechaFin date='20260910',@DiasReproceso int=0;\n"+keeper
def report_sql():
    s=ref(body(sql('sp_reporte_turno_emision_test')),'trazabilidad_analitos_tm_emision_test','#traza')
    s=ref(s,'v_ajuste_camiones_emision_test','#ajuste')
    return "DECLARE @fecha_inicio date='20260910',@fecha_fin date='20260911';\n"+s
def snapshot(c):
    get=lambda q:[dict(r) for r in c.execute(text(q)).mappings()]
    return {'factor':get('SELECT * FROM #factor'),'cache':get('SELECT * FROM #cache ORDER BY Turno'),'srr':get('SELECT * FROM #srr ORDER BY Turno'),'aplicacion':get('SELECT * FROM #ajuste')}
def refresh_view(c,name,target,source,replacement):
    run(c,'DELETE FROM '+target+'; INSERT INTO '+target+' '+dynamic(ref(view(name),source,replacement)))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--cap',action='store_true');args=parser.parse_args()
    engine=_engine_dev()
    keeper=factor_sql();report=report_sql()
    (OUT/'sim_factor.sql').write_text(keeper,encoding='utf-8')
    (OUT/'sim_reporte.sql').write_text(report,encoding='utf-8')
    scenarios=[('CAP_SINTETICO',True,'FCFCFC')] if args.cap else [('A_original',False,'FC'),('B_original',False,'CFC'),('A_historico',True,'FC'),('B_historico',True,'CFC')]
    for label,hist,steps in scenarios:
        with engine.connect() as c:
            _assert_dev_connection(c)
            persistent=lambda: {n:[dict(r) for r in c.execute(text('SELECT * FROM inventar_SpcHidr.'+n+" WHERE Fecha='20260910'")).mappings()] for n in ('Historico_Apilado_Diario','Control_Factor_Ajuste_Camiones_v2_test','reporte_turno_cache_emision_test','trazabilidad_analitos_tm_emision_test')}
            before=persistent()
            for table,target in [('Historico_Apilado_Diario','#hist'),('Control_Factor_Ajuste_Camiones_v2_test','#factor'),('reporte_turno_cache_emision_test','#cache'),('v_srr_tms_origen_turno_emision_test','#srr'),('v_ajuste_camiones_emision_test','#ajuste')]:
                run(c,f"SELECT * INTO {target} FROM inventar_SpcHidr.{table} WHERE Fecha='20260910';")
            run(c,'SELECT TOP (0) * INTO #traza FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test;')
            if args.cap:
                run(c,'UPDATE #cache SET Apilado_TMS_Real=1000;')
                refresh_view(c,'v_srr_tms_origen_turno_emision_test','#srr','reporte_turno_cache_emision_test','#cache')
            result={'baseline':snapshot(c),'pasos':[]}
            if hist:
                h=ref(body(sql('sp_refrescar_historico_apilado_test')),'Historico_Apilado_Diario','#hist')
                run(c,"DECLARE @FechaInicio date='20260910',@FechaFin date='20260910',@DiasReproceso int=0;\n"+h)
            for step in steps:
                if step=='F':
                    refresh_view(c,'v_srr_tms_origen_turno_emision_test','#srr','reporte_turno_cache_emision_test','#cache')
                    run(c,keeper)
                    refresh_view(c,'v_ajuste_camiones_emision_test','#ajuste','Control_Factor_Ajuste_Camiones_v2_test','#factor')
                else:
                    rows=run(c,report)
                    assert len(rows)==2,(label,len(rows))
                    for row in rows:
                        assignments=','.join('['+k+']=:'+k for k in row if k not in ('Fecha','Turno'))
                        c.execute(text('UPDATE #cache SET '+assignments+' WHERE Fecha=:Fecha AND Turno=:Turno'),row)
                    refresh_view(c,'v_srr_tms_origen_turno_emision_test','#srr','reporte_turno_cache_emision_test','#cache')
                result['pasos'].append({'paso':step,**snapshot(c)})
                print(label,step,flush=True)
            result['persistentes_identicos']=before==persistent()
            assert result['persistentes_identicos']
            save('secuencia_'+label,result)
            c.rollback()
    if args.cap:return
    # Reporte directo de septiembre: única escritura desviada a #traza.
    with engine.connect() as c:
        _assert_dev_connection(c)
        run(c,'SELECT TOP (0) * INTO #traza FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test;')
        s=ref(body(sql('sp_reporte_turno_emision_test')),'trazabilidad_analitos_tm_emision_test','#traza')
        save('sept_reporte_directo',run(c,"DECLARE @fecha_inicio date='20260904',@fecha_fin date='20260911';\n"+s))
        c.rollback()
if __name__=='__main__':main()
