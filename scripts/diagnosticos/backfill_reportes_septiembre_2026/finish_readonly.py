"""Validación post-backfill, exclusivamente SELECT; nunca reintenta bloques."""
from collections import Counter
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from sqlalchemy import text
from scripts.backfill_septiembre_2026_reportes import P,START,END,TABLES,read,save,validate
from scripts.diagnosticos.backfill_reportes_septiembre_2026.review_precheck import outside
from db_connection import get_engine

def main():
    with get_engine().connect() as c:
        assert c.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        final={}; (P/'after_rows').mkdir(exist_ok=True)
        for table,col in TABLES.items():
            rows=[dict(r) for r in c.execute(text(f'SELECT * FROM inventar_SpcHidr.[{table}] WHERE [{col}]>=:a AND [{col}]<=:b'),{'a':START,'b':END}).mappings()]
            save('after_rows/'+table+'.json',rows)
            original=read('backup_logico/'+table+'.json')
            dates=Counter(str(r[col])[:10] for r in rows)
            sums={}
            for field in rows[0] if rows else []:
                values=[r[field] for r in rows if isinstance(r[field],(int,float,Decimal)) and not isinstance(r[field],bool)]
                if values:sums[field]=str(sum(Decimal(str(v)) for v in values))
            encoded=sorted(json.dumps(r,default=str,sort_keys=True,ensure_ascii=False) for r in rows)
            final[table]={'filas_antes':len(original),'filas_despues':len(rows),'por_fecha':dict(sorted(dates.items())),'agregados_despues':sums,'nulls_despues':{k:sum(r[k] is None for r in rows) for k in rows[0]} if rows else {},'sha256':hashlib.sha256('\n'.join(encoded).encode()).hexdigest()}
        save('after.json',final)
        out=outside(c);save('outside_after.json',out)
        same=out==read('outside_before.json')
        from report_export.report_export import fetch_fecha_corte_operacional_representatividad,fetch_fecha_corte_apilado_tmh_report
        save('octubre_readonly.json',{'fuera_septiembre_identico':same,'corte_representatividad':fetch_fecha_corte_operacional_representatividad(date(2026,10,1),date(2026,10,31),conn=c),'corte_apilado':fetch_fecha_corte_apilado_tmh_report(date(2026,10,1),date(2026,10,31),conn=c),'recalculado':False})
        unchanged=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in read('runtime_before.json').items())
        save('runtime_check.json',{'sin_cambios':unchanged})
        assert unchanged and same, 'Cambios inesperados runtime o fuera de septiembre: revisar, no restaurar automáticamente'
        log=read('ejecucion.json')
        if log['estado']=='DETENIDO':
            print('Ejecución detenida: evidencia posterior capturada; no continuar downstream')
            return
        for phase in ('representatividad','analisis_tm','datos_conciliados'):validate(c,phase)
        # Umbral y evaluabilidad ya presentes en sp_sincronizar_bd_ton LIVE.
        flags=[]
        for row in read('after_rows/BD_Ton.json'):
            for tm in ('TM1','TM2'):
                for turno in ('TA','TB'):
                    evaluable=row['Evaluable_'+tm+'_'+turno]
                    for kind,suffix,field in [('quimico','Qui','Muestra_representativa_'+tm+'_'+turno),('fisico','Fis','FISICO_'+tm+'_'+turno)]:
                        rep=row['Rep_'+tm+'_'+turno+'_'+suffix]
                        expected=None if not evaluable else int(rep is not None and Decimal(str(rep))>=Decimal('0.75'))
                        if row[field]!=expected:flags.append({'fecha':row['Fecha'],'campo':field,'actual':row[field],'esperado':expected})
        repcheck=read('validacion_representatividad.json');repcheck['umbral_075_evaluabilidad']={'diferencias':flags,'estado':'PASS' if not flags else 'FAIL'}
        save('validacion_representatividad.json',repcheck)
        assert not flags,'Diferencia flags Representatividad'
        profiles={}
        for table,fields in [('trazabilidad_analitos_tm_emision_test',['Fuente_Tecnica','Analito','TM_Destino']),('reporte_turno_cache_emision_test',['Fuente_Info_Quimica','Fuente_Info_Fisica']),('Control_Factor_Ajuste_Camiones_v2_test',['Fuente_Camiones','Estado_Calculo'])]:
            rs=read('after_rows/'+table+'.json')
            profiles[table]={field:dict(Counter(str(row[field]) for row in rs)) for field in fields}
        save('perfiles_fuentes.json',profiles)
        emission=[dict(r) for r in c.execute(text('SELECT * FROM inventar_SpcHidr.v_ajuste_camiones_emision_test WHERE Fecha>=:a AND Fecha<=:b'),{'a':START,'b':END}).mappings()]
        save('factor_emision_after.json',emission)
        save('casos_canonicos_actuales.json',[r for r in emission if str(r['Fecha'])[:10] in ('2026-09-02','2026-09-14','2026-09-16','2026-09-20','2026-09-21','2026-09-22')])
        print('POSTCHECK PASS: cobertura y contrato, runtime intacto, resultados fuera de septiembre idénticos')

if __name__=='__main__':main()
