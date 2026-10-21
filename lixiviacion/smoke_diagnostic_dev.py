"""Smoke Fase 1: solo SELECT DEV, comparación con código anterior sin actualizar baseline histórico."""
import ast
import hashlib
import json
import os
from pathlib import Path
from types import ModuleType
from sqlalchemy import text
from . import db, callbacks

OUT=(Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion/diagnostico_fase1')
CASES=[(1,1,'RIEGO_DRENAJE'),(1,17,'MIXTO'),(1,29,'REPOSO_PRE_RECLAMO'),
       (2,33,'MIXTO'),(2,39,'RIEGO_DRENAJE'),(2,41,'REPOSO_PRE_RECLAMO'),(2,60,'APILADO')]


def baseline():
    old=ModuleType('lixiviacion._baseline_db')
    old.__package__='lixiviacion'
    exec(compile((OUT/'db.py').read_text(encoding='utf-8'),str(OUT/'db.py'),'exec'),old.__dict__)
    namespace=callbacks.__dict__.copy()
    tree=ast.parse((OUT/'callbacks.py').read_text(encoding='utf-8'))
    defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('serial','number','figure','figures')]
    exec(compile(ast.Module(body=defs,type_ignores=[]),'baseline_figures','exec'),namespace)
    return old,namespace['figures']


def digest(rows):
    return hashlib.sha256(json.dumps(rows,default=str,sort_keys=True).encode()).hexdigest()


def run():
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    old,old_figures=baseline()
    report={'cases':[],'baseline_transferencia_historica':'30136.221811330','baseline_updated':False}
    with db._connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
    for pad,parcel,state in [(None,None,None)]+CASES:
        f=dict(desde='2026-06-01',hasta='2026-09-10',pad=pad,parcela=parcel,campana=None,estado=None)
        before_tot,before_daily=old.overview(f)
        w,params=old.where(f)
        # Comparar todas las filas de las columnas reales de DataTable, sin guardar dataset.
        sql=f"SELECT {','.join(expr+' AS '+col for col,expr in old.DETAIL.items())} FROM {old.SOURCE} WHERE {w} ORDER BY fecha,pad_id,parcela_id"
        with db._connection() as conn:
            before_table=[dict(r) for r in conn.execute(text(sql),params).mappings()]
        h,timeline=db.operational(f)
        after_tot,after_daily=db.overview(f)
        with db._connection() as conn:
            after_table=[dict(r) for r in conn.execute(text(sql),params).mappings()]
        assert before_tot==after_tot and before_daily==after_daily and before_table==after_table
        before_fig=old_figures(before_daily,single_parcel=parcel is not None)
        after_fig=callbacks.figures(after_daily,single_parcel=parcel is not None)
        assert [g.to_json() for g in before_fig]==[g.to_json() for g in after_fig]
        case={'pad':pad,'parcela_id':parcel,'kpis':after_tot,'v2_rows':len(after_table),
              'v2_sha256':digest(after_table),'four_kpis_unchanged':True,'three_figures_unchanged':True,'table_unchanged':True}
        if parcel is not None:
            assert h['estado_operacional']==state and len(timeline)==102
            assert len({r['fecha'] for r in timeline})==102
            expected='CAMPANA_HIDRAULICA' if (pad,parcel) in ((1,1),(2,39)) else 'FUERA_VENTANA_RIEGO'
            assert h['estado_asignacion']==expected
            assert str(h['fecha'])=='2026-09-10'
            if (pad,parcel)==(1,1): assert str(h['numero_campana'])=='18'
            if expected=='FUERA_VENTANA_RIEGO': assert h['campana_hidraulica_id'] is None
            case.update(header=h,timeline_rows=len(timeline),timeline_sha256=digest(timeline),
                        timeline_traces=len(callbacks.operational_timeline(timeline,f).data))
        report['cases'].append(case)
        print('PASS',pad,parcel,flush=True)
    # Evidencia de preservación del mapa y del baseline histórico.
    audit=json.loads(Path('test_fixtures/lixiviacion/source_contract.json').read_text(encoding='utf-8'))
    preserved=['lixiviacion\\map_db.py','lixiviacion\\map_panel.py','lixiviacion\\map_states.py',
               'assets\\lixiviacion_map.css','lixiviacion\\smoke_dev.py','layout.py']
    report['preserved_files']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()==audit['runtime_hashes'][p] for p in preserved}
    assert all(report['preserved_files'].values())
    report['passed']=True
    (OUT/'smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


if __name__=='__main__': run()
