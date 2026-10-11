"""Perfil del callback real en memoria y metadatos adicionales; exclusivamente DEV SELECT."""
from contextlib import contextmanager
from datetime import date
import json
import os
from pathlib import Path
import time
from unittest.mock import patch
from sqlalchemy import text
from dash._utils import to_json
from lixiviacion import db,callbacks

OUT=Path(__file__).parent


def run():
    assert os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr'
    with db._connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        definition=conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'),{'name':db.OP_SOURCE}).scalar_one()
        (OUT/'funcion_instalada_snapshot.sql').write_text(definition,encoding='utf-8',newline='')
        report={}
        queries={
            'table_rows':'''SELECT t.name,SUM(p.row_count) AS approximate_rows
                FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
                JOIN sys.dm_db_partition_stats p ON p.object_id=t.object_id AND p.index_id IN (0,1)
                WHERE s.name='inventar_SpcHidr' AND t.name IN
                ('campana_parcela_control','flujos_reales_oxido','flujos_reales_sulfuro',
                'drena_concentrados_oxido','drena_concentrados_sulfuro','pad','parcela') GROUP BY t.name''',
            'query_store_matches':'''SELECT q.query_id,p.plan_id,rs.count_executions,rs.avg_duration,
                rs.avg_cpu_time,rs.avg_logical_io_reads,rs.last_execution_time,
                i.start_time AS interval_start,i.end_time AS interval_end,qt.query_sql_text
                FROM sys.query_store_query_text qt JOIN sys.query_store_query q ON q.query_text_id=qt.query_text_id
                JOIN sys.query_store_plan p ON p.query_id=q.query_id
                JOIN sys.query_store_runtime_stats rs ON rs.plan_id=p.plan_id
                JOIN sys.query_store_runtime_stats_interval i ON i.runtime_stats_interval_id=rs.runtime_stats_interval_id
                WHERE qt.query_sql_text LIKE '%WITH fechas AS%'
                AND qt.query_sql_text LIKE '%fn_estado_operacional_parcela_diario%'
                AND qt.query_sql_text NOT LIKE '%sys.query_store_query_text%'
                ORDER BY rs.last_execution_time DESC''',
            'source_counts':'''SELECT 'CPC' AS source,COUNT_BIG(*) AS rows FROM inventar_SpcHidr.campana_parcela_control
                UNION ALL SELECT 'flujo_ox',COUNT_BIG(*) FROM inventar_SpcHidr.v_flujos_oxido_unpivot
                UNION ALL SELECT 'flujo_sulf',COUNT_BIG(*) FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot
                UNION ALL SELECT 'drenaje_ox',COUNT_BIG(*) FROM inventar_SpcHidr.v_drena_oxido_operacional
                UNION ALL SELECT 'drenaje_sulf',COUNT_BIG(*) FROM inventar_SpcHidr.v_drena_sulfuro_operacional
                UNION ALL SELECT 'pad',COUNT_BIG(*) FROM inventar_SpcHidr.pad
                UNION ALL SELECT 'parcela',COUNT_BIG(*) FROM inventar_SpcHidr.parcela''',
        }
        for label,sql in queries.items():
            try: report[label]=[dict(r) for r in conn.execute(text(sql)).mappings()]
            except Exception as exc: report[label]={'unavailable':type(exc).__name__,'detail':str(exc)[:500]}
        (OUT/'metadata_supplement.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        (OUT/'metadata_supplement.sql').write_text('\n\n'.join('-- '+k+'\n'+v+';' for k,v in queries.items()),encoding='utf-8')
    original=db._connection
    profiles=[]
    for pad,parcel in ((1,1),(2,39)):
        calls=[]
        class Proxy:
            def __init__(self,conn): self.conn=conn
            def execute(self,statement,params):
                start=time.perf_counter()
                result=self.conn.execute(statement,params)
                returned=time.perf_counter()
                class Result:
                    def mappings(self):
                        rows=list(result.mappings())
                        end=time.perf_counter()
                        calls.append({'sql':str(statement),'params':params,'execute_seconds':returned-start,
                            'fetch_mapping_seconds':end-returned,'total_seconds':end-start,'rows':len(rows)})
                        return rows
                return Result()
        @contextmanager
        def observed():
            with original() as conn: yield Proxy(conn)
        filters={'desde':'2026-06-01','hasta':'2026-09-10','pad':pad,'parcela':parcel,'campana':None,'estado':None}
        start=time.perf_counter()
        with patch.object(db,'_connection',observed): component=callbacks.load_operational(filters)
        built=time.perf_counter();payload=to_json(component);serialized=time.perf_counter()
        assert len(calls)==2 and calls[1]['rows']==102
        profiles.append({'pad':pad,'parcela_id':parcel,'calls':calls,'callback_seconds':built-start,
            'callback_other_seconds':built-start-sum(c['total_seconds'] for c in calls),
            'component_serialization_seconds':serialized-built,'payload_bytes':len(payload.encode())})
        print('Callback profile',pad,round(built-start,3),flush=True)
        (OUT/'callback_profile.json').write_text(json.dumps(profiles,indent=2,default=str),encoding='utf-8')


if __name__=='__main__': run()
