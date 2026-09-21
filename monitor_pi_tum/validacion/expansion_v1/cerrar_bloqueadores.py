"""Inspección y validación DEV; --apply altera exclusivamente cinco vistas Reclamo TEST."""
import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from monitor_pi_tum.postprocesar_tum_contingencia import ejecutar

ROOT=Path(__file__).parent
OUT=ROOT/'bloqueadores'
NAMES=['reclamo.'+n for n in ('v_cv25_diario','v_preliminar_cv25','v_preliminar_cv25_con_acumulado','v_reclamo_diario','v_diferencia_cv25')]
def save(n,value):
    (OUT/(n+'.json')).write_text(json.dumps(value,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
def metadata(c,n):
    return [dict(r) for r in c.execute(text('SELECT c.name,t.name tipo,c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c JOIN sys.types t ON c.user_type_id=t.user_type_id WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'),{'n':n}).mappings()]
def definition(c,n):
    return c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),{'n':n}).scalar()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    OUT.mkdir(exist_ok=True)
    engine=_engine_dev()
    if args.apply:
        with engine.begin() as c:
            _assert_dev_connection(c)
            originals={n:definition(c,n) for n in NAMES}
            for n in NAMES:
                test=n+'_contingencia_test'
                expected=(OUT/(test+'.antes.sql')).read_text(encoding='utf-8')
                if definition(c,test).replace('\r\n','\n')!=expected.replace('\r\n','\n'):
                    raise RuntimeError('Definición cambió desde inspección: '+test)
            for n in NAMES:
                test=n+'_contingencia_test'
                ddl=re.sub(r'\bCREATE\s+VIEW\b','ALTER VIEW',(ROOT/'ddl'/(test+'.sql')).read_text(encoding='utf-8'),count=1,flags=re.I)
                c.exec_driver_sql(ddl)
                official=metadata(c,n);actual=metadata(c,test)
                numeric=lambda rows:{r['name']:(r['tipo'],r['precision'],r['scale'],r['max_length']) for r in rows if r['tipo'] in ('decimal','numeric','float','real','int','bigint','smallint','tinyint')}
                assert numeric(official)==numeric(actual),(n,official,actual)
            assert originals=={n:definition(c,n) for n in NAMES}
    with engine.connect() as c:
        _assert_dev_connection(c)
        metas={}
        for n in ['reclamo.cv25_diario',*NAMES,*[n+'_contingencia_test' for n in NAMES]]:
            metas[n]=metadata(c,n)
            d=definition(c,n)
            path=OUT/(n+('.despues.sql' if args.apply else '.antes.sql'))
            if d and not path.exists():path.write_text(d,encoding='utf-8')
        save('tipos_despues' if args.apply else 'tipos_antes',metas)
        for batch in (20454,20455):
            plan,_,_=ejecutar(batch,commit=False,engine=engine)
            save('dry_run_'+str(batch),asdict(plan));print('DRY-RUN',batch,asdict(plan),flush=True)
        rows=[dict(r) for r in c.execute(text("SELECT * FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test WHERE fecha_operacional='20260908' AND turno='B' AND equipo_codigo='RIPIOS_CV025'")).mappings()]
        assert len(rows)==1 and rows[0]['valor_final_resuelto'] is None and rows[0]['fuente_resuelta']=='PENDIENTE_TUM'
        save('pendiente_RO',rows)
        if args.apply:
            regression={}
            for n in NAMES:
                cols=[r['name'] for r in metas[n]]
                dc=next(x for x in cols if x in ('fecha','fecha_operacion'))
                results=[]
                for name in (n,n+'_contingencia_test'):
                    results.append([dict(r) for r in c.execute(text(f"SELECT * FROM {name} WHERE [{dc}] IN ('20260831','20260913')")).mappings()])
                canon=lambda rs:sorted(json.dumps(r,default=str,sort_keys=True) for r in rs)
                assert canon(results[0])==canon(results[1]),n
                regression[n]={'filas':len(results[0]),'igualdad_exacta':True,'oficial':results[0],'test':results[1]}
            save('regresion_normal',regression)
            pending=[dict(r) for r in c.execute(text("SELECT * FROM reclamo.v_cv25_diario_contingencia_test WHERE fecha='20260908'")).mappings()]
            assert pending[0]['tmh_dia'] is None and pending[0]['tms_dia'] is None and pending[0]['flag_preliminar']=='PENDIENTE_TUM'
            save('pendiente_reclamo',pending)
    print('Validación completada',flush=True)
if __name__=='__main__':main()
