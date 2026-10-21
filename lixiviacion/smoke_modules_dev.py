"""Solo lectura DEV: módulos reales desde la fuente configurada en map_db."""
import json
import os
from pathlib import Path
from sqlalchemy import text
from . import map_db


def run():
    (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion').mkdir(parents=True, exist_ok=True)
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    with map_db._connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
    rows=map_db.snapshot('2026-09-10')
    cases={(1,29):[(57,'REPOSO_PRE_RECLAMO'),(58,'REPOSO_PRE_RECLAMO')],
           (1,17):[(33,'CONFORMADO_PRE_RIEGO'),(34,'APILADO')],
           (2,1):[(1,'RECLAMADO'),(2,'RECLAMADO'),(3,'RECLAMADO'),(4,'RECLAMADO'),(5,'RECLAMO')]}
    report={'parcelas':len(rows),'cases':[]}
    for (pad,number),expected in cases.items():
        row=next(r for r in rows if r['pad_id']==pad and r['numero_parcela']==number)
        modules=map_db.fetch_modulos_parcela('2026-09-10',pad,row['parcela_id'])
        assert len(modules)==row['modulos_total']
        assert [(int(m['nombre_modulo']),m['estado_modulo']) for m in modules]==expected
        report['cases'].append({'pad':pad,'parcela':number,'modulos_total':row['modulos_total'],'modules':modules})
    report['passed']=True
    (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion/SMOKE_MODULES_DEV.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2,default=str))


if __name__=='__main__': run()
