"""CURRENT_SMOKE DEV: contrato e invariantes, sin totales históricos esperados."""
import json
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
from sqlalchemy import text
from . import db, map_db
from .smoke_evidence import write_evidence, definition_hashes

PERIOD = {'desde':'2026-06-01', 'hasta':'2026-09-10'}


def null_equal(a, b):
    return a == b  # None es distinto de cero.


def check_rows(rows):
    keys = [(r['fecha'],r['pad_id'],r['parcela_id']) for r in rows]
    assert len(keys)==len(set(keys)), 'CONTRACT: claves duplicadas'
    assert rows, 'CONTRACT: período sin filas'
    for r in rows:
        assert all(r[k] is not None for k in ('fecha','pad_id','parcela_id','nro_parcela_pad','estado_asignacion'))
        assert r['pad_id'] in (1,2)
        expected='FUERA_VENTANA_RIEGO' if r['campana_id'] is None else 'CAMPANA_HIDRAULICA'
        assert r['estado_asignacion']==expected, 'CONTRACT: asignación hidráulica inconsistente'
        assert null_equal(r['delta_cu_gl'],r['expected_delta']), 'FORMULA: delta'
        assert null_equal(r['transferencia_cu_t_d'],r['expected_t']), 'FORMULA: transferencia'
    return {'rows':len(rows),'unique_keys':len(set(keys)),
            'nulls':{k:sum(r[k] is None for r in rows) for k in rows[0]}}


def run():
    report={'passed':False,'checks':{},'expected_totals':None}
    hashes=None
    try:
        with db._connection() as conn:
            assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr', 'Solo DEV'
            hashes=definition_hashes(conn,[db.SOURCE,db.OP_SOURCE,map_db.MODULE_SOURCE] if hasattr(map_db,'MODULE_SOURCE') else [db.SOURCE,db.OP_SOURCE])
            contract=[dict(r) for r in conn.execute(text('''SELECT c.column_id,c.name,t.name AS type,c.max_length,c.precision,c.scale,c.is_nullable
                FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id
                WHERE c.object_id=OBJECT_ID(:obj) ORDER BY c.column_id'''),{'obj':db.SOURCE}).mappings()]
            expected=json.loads(Path('test_fixtures/lixiviacion/source_contract.json').read_text(encoding='utf-8'))['objects'][db.SOURCE]['columns']
            assert contract==expected, 'CONTRACT: columnas/tipos/nullability cambiaron'
            report['checks']['contract']=True
            rows=[dict(r) for r in conn.execute(text(f'''SELECT fecha,pad_id,parcela_id,nro_parcela_pad,campana_id,estado_asignacion,
                flujo_m3_d,cu_drenaje_gl,cu_refino_gl,delta_cu_gl,transferencia_cu_t_d,
                cu_drenaje_gl-cu_refino_gl AS expected_delta,
                CAST(CAST(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl) AS decimal(31,6))/CAST(1000.0 AS decimal(5,1)) AS decimal(38,9)) AS expected_t
                FROM {db.SOURCE} WHERE fecha BETWEEN :desde AND :hasta ORDER BY fecha,pad_id,parcela_id'''),PERIOD).mappings()]
            report['checks']['rows']=check_rows(rows)
            # Este período de referencia tiene cobertura física aprobada de las 60 parcelas.
            counts=Counter((r['fecha'],r['pad_id']) for r in rows)
            assert len(counts)==204 and all(n==(32 if p==1 else 28) for (_,p),n in counts.items()), 'COVERAGE: faltan fechas/parcelas'
            with localcontext() as ctx:
                ctx.prec=70
                totals={}
                for field in ('flujo_m3_d','transferencia_cu_t_d'):
                    sums={pad:sum((r[field] for r in rows if r['pad_id']==pad and r[field] is not None),Decimal(0)) for pad in (1,2)}
                    sql_total=conn.execute(text(f'SELECT SUM({field}) FROM {db.SOURCE} WHERE fecha BETWEEN :desde AND :hasta'),PERIOD).scalar_one()
                    observed=sum(sums.values()) if any(r[field] is not None for r in rows) else None
                    assert observed==sql_total, 'DATA_DRIFT_OR_INVARIANT: suma PAD/total cambió durante lectura'
                    totals[field]={'PAD':sums,'total':sql_total}
                report['observed']=totals
            assert hashes==definition_hashes(conn,list(hashes)), 'CONTRACT: definición cambió durante smoke'
        report['checks']['coverage_60_reference_period']=True
        report['checks']['formulas_null_safe']=True
        # Los siete canónicos y la separación de campañas se validan por el ejecutor regression_diagnostic.
        report['passed']=True
    except Exception as exc:
        report['failure']=str(exc)
        raise
    finally:
        write_evidence('CURRENT_SMOKE','v2',report,period=PERIOD,definitions=hashes)


if __name__=='__main__': run()
