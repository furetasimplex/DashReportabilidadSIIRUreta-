"""Validación READ ONLY DEV del estado diario, distribución y casos aprobados."""
import json
import os
from collections import Counter
from pathlib import Path
from sqlalchemy import text
from . import map_db


def run():
    if os.getenv('SQLSERVER_DB','').lower() != 'inventar_spchidr':
        raise RuntimeError('Solo DEV.')
    with map_db._connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower() == 'inventar_spchidr'
    rows=map_db.snapshot('2026-09-10')
    # Canónico actualizado por validación de fuentes DEV; ninguna regla SQL cambió.
    expected={1:{'MIXTO':1,'REPOSO_PRE_RECLAMO':12,'RIEGO_DRENAJE':19},
              2:{'APILADO':1,'CONFORMADO_PRE_RIEGO':2,'MIXTO':2,'REPOSO_PRE_RECLAMO':5,'RIEGO_DRENAJE':18}}
    distribution={p:dict(Counter(r['estado_operacional'] for r in rows if r['pad_id']==p)) for p in (1,2)}
    assert distribution==expected, distribution
    cases={(1,17):('MIXTO','APILADO = 1 | CONFORMADO_PRE_RIEGO = 1'),
           (2,1):('MIXTO','RECLAMADO = 4 | RECLAMO = 1'),
           (2,2):('MIXTO','RECLAMO = 1 | REPOSO_PRE_RECLAMO = 4'),
           (2,26):('CONFORMADO_PRE_RIEGO',None),(2,27):('CONFORMADO_PRE_RIEGO',None),
           (2,28):('APILADO',None)}
    checked=[]
    for key,(state,composition) in cases.items():
        row=next(r for r in rows if (r['pad_id'],r['numero_parcela'])==key)
        assert row['estado_operacional']==state
        if composition is not None: assert row['composicion_modulos']==composition
        checked.append(row)
    next_day=map_db.snapshot('2026-09-11')
    report={'fecha':'2026-09-10','filas':len(rows),'distribucion':distribution,
            'casos':checked,'filas_11_09':len(next_day),'passed':True}
    Path(__file__).with_name('SMOKE_MAP_DEV.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({'filas':len(rows),'distribucion':distribution,'casos':len(checked),'passed':True},ensure_ascii=False))


if __name__=='__main__': run()
