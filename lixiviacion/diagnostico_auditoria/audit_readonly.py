"""Inspección DEV: exclusivamente SELECT/CTE, evidencia resumida, sin runtime changes."""
import hashlib
import json
import os
import time
from pathlib import Path
from sqlalchemy import text
from lixiviacion.db import _connection

OUT = Path(__file__).parent
VIEW = 'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2'
FN = 'inventar_SpcHidr.fn_estado_operacional_parcela_diario'


def main():
    if os.getenv('SQLSERVER_DB','').lower() != 'inventar_spchidr':
        raise RuntimeError('Solo DEV')
    files = list(Path('lixiviacion').glob('*.py'))+[Path('layout.py'),Path('assets/lixiviacion_map.css')]
    before = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    log=[]
    def query(conn, label, sql, params=None):
        assert sql.lstrip().upper().startswith(('SELECT','WITH'))
        start=time.perf_counter()
        result=[dict(r) for r in conn.execute(text(sql),params or {}).mappings()]
        log.append({'label':label,'sql':sql,'params':params or {},'seconds':round(time.perf_counter()-start,4)})
        return result
    report={}
    with _connection() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar_one().lower()=='inventar_spchidr'
        pending=[VIEW,FN]
        objects={}
        while pending:
            name=pending.pop(0)
            if name in objects: continue
            meta=query(conn,'object '+name,'''SELECT o.type,o.type_desc,m.definition
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name)''',{'name':name})
            if not meta: objects[name]={'missing':True}; continue
            item=meta[0]
            definition=item.pop('definition')
            if definition:
                (OUT/(name.replace('.','__')+'.sql')).write_text(definition,encoding='utf-8',newline='')
            item['columns']=query(conn,'columns '+name,'''SELECT c.column_id,c.name,TYPE_NAME(c.user_type_id) AS type,
                c.max_length,c.precision,c.scale,c.is_nullable FROM sys.columns c
                WHERE c.object_id=OBJECT_ID(:name) ORDER BY c.column_id''',{'name':name})
            item['dependencies']=query(conn,'dependencies '+name,'''SELECT DISTINCT
                referenced_database_name,referenced_schema_name,referenced_entity_name
                FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID(:name)''',{'name':name})
            objects[name]=item
            # Recorrer solo dependencias locales; jamás conectar a otra base.
            for dep in item['dependencies']:
                if dep['referenced_database_name'] not in (None,'inventar_SpcHidr'): continue
                if dep['referenced_schema_name'] and dep['referenced_entity_name']:
                    pending.append(dep['referenced_schema_name']+'.'+dep['referenced_entity_name'])
        report['objects']=objects
        report['periods']={}
        for start,end in [('2026-09-10','2026-09-10'),('2026-09-01','2026-09-10'),('2026-06-01','2026-09-10')]:
            params={'desde':start,'hasta':end}
            metrics=query(conn,'v2_metrics',f'''WITH b AS (SELECT * FROM {VIEW} WHERE fecha BETWEEN :desde AND :hasta),
                k AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS n FROM b GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS rows,(SELECT COUNT_BIG(*) FROM k) AS unique_keys,
                (SELECT COUNT_BIG(*) FROM k WHERE n>1) AS duplicate_keys,(SELECT MAX(n) FROM k) AS max_per_key,
                (SELECT COUNT_BIG(*) FROM b WHERE pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL) AS null_keys''',params)
            aggregates=query(conn,'v2_aggregates',f'''SELECT pad_id,estado_asignacion,COUNT_BIG(*) AS rows,
                SUM(flujo_m3_d) AS flujo,SUM(transferencia_cu_t_d) AS transferencia,AVG(delta_cu_gl) AS delta,
                COUNT(delta_cu_gl) AS delta_count,COUNT(cu_drenaje_gl) AS drenaje_count,COUNT(cu_refino_gl) AS refino_count,
                SUM(CASE WHEN delta_cu_gl<0 THEN 1 ELSE 0 END) AS negative_delta,
                SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS null_campaign
                FROM {VIEW} WHERE fecha BETWEEN :desde AND :hasta GROUP BY pad_id,estado_asignacion''',params)
            report['periods'][start+'_'+end]={'metrics':metrics,'aggregates':aggregates}
        report['joins']={}
        for start,end in [('2026-09-10','2026-09-10'),('2026-09-01','2026-09-10')]:
            sql=f'''WITH dates AS (SELECT CAST(:desde AS date) AS fecha UNION ALL
                SELECT DATEADD(day,1,fecha) FROM dates WHERE fecha<CAST(:hasta AS date)),
                e AS (SELECT f.* FROM dates d CROSS APPLY {FN}(d.fecha) f),
                b AS (SELECT * FROM {VIEW} WHERE fecha BETWEEN :desde AND :hasta),
                ek AS (SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) n FROM e GROUP BY pad_id,parcela_id,fecha)
                SELECT (SELECT COUNT_BIG(*) FROM b) AS v2_rows,(SELECT COUNT_BIG(*) FROM e) AS estado_rows,
                (SELECT COUNT_BIG(*) FROM ek WHERE n>1) AS estado_duplicate_keys,
                (SELECT COUNT_BIG(*) FROM b LEFT JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS left_join_rows,
                (SELECT COUNT_BIG(*) FROM b INNER JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id) AS inner_join_rows,
                (SELECT COUNT_BIG(*) FROM b WHERE NOT EXISTS (SELECT 1 FROM e WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS v2_unmatched,
                (SELECT COUNT_BIG(*) FROM e WHERE NOT EXISTS (SELECT 1 FROM b WHERE e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id)) AS estado_unmatched,
                (SELECT COUNT_BIG(*) FROM b JOIN e ON e.fecha=b.fecha AND e.pad_id=b.pad_id AND e.parcela_id=b.parcela_id
                 WHERE b.campana_id<>e.campana_id OR (b.campana_id IS NULL AND e.campana_id IS NOT NULL)
                    OR (b.campana_id IS NOT NULL AND e.campana_id IS NULL)) AS campaign_mismatch
                OPTION (MAXRECURSION 100)'''
            report['joins'][start+'_'+end]=query(conn,'join_compatibility',sql,{'desde':start,'hasta':end})
        report['cases']=query(conn,'reference_cases',f'''SELECT e.fecha,e.pad_id,e.numero_parcela,e.parcela_id,
            e.campana_id AS operational_campana_id,e.estado_operacional,e.composicion_modulos,e.riego_activo,e.drenaje_activo,
            b.campana_id AS diagnostic_campana_id,b.numero_campana,b.estado_asignacion,b.flujo_m3_h,b.flujo_m3_d,
            b.cu_drenaje_gl,b.cu_refino_gl,b.delta_cu_gl,b.transferencia_cu_kg_d,b.transferencia_cu_t_d
            FROM {FN}(:fecha) e LEFT JOIN {VIEW} b ON b.fecha=e.fecha AND b.pad_id=e.pad_id AND b.parcela_id=e.parcela_id
            WHERE (e.pad_id=1 AND e.numero_parcela IN (1,17,29)) OR (e.pad_id=2 AND e.numero_parcela IN (1,7,9,28))
            ORDER BY e.pad_id,e.numero_parcela''',{'fecha':'2026-09-10'})
        report['source_keys']={}
        for suffix in ('oxido','sulfuro'):
            for obj,keys in [('vw_flujos_reales_'+suffix+'_long','parcela_id,fecha'),
                             ('vw_drena_concentrados_'+suffix+'_long_operacional','nro_parcela_pad,fecha'),
                             ('vw_riego_'+suffix+'_refino_operacional','fecha')]:
                report['source_keys'][obj]=query(conn,'source_uniqueness '+obj,f'''WITH k AS (
                    SELECT {keys},COUNT_BIG(*) n FROM inventar_SpcHidr.{obj}
                    WHERE fecha BETWEEN :desde AND :hasta GROUP BY {keys})
                    SELECT SUM(n) AS rows,COUNT_BIG(*) AS unique_keys,MAX(n) AS max_per_key,
                    SUM(CASE WHEN n>1 THEN 1 ELSE 0 END) AS duplicate_keys FROM k''',{'desde':'2026-06-01','hasta':'2026-09-10'})
        report['outside_positive']=query(conn,'outside_positive',f'''SELECT fecha,pad_id,parcela_id,nro_parcela_pad,
            campana_id,estado_asignacion,flujo_m3_d,delta_cu_gl,transferencia_cu_t_d
            FROM {VIEW} WHERE fecha BETWEEN :desde AND :hasta
            AND estado_asignacion='FUERA_VENTANA_RIEGO' AND flujo_m3_d>0
            ORDER BY fecha,pad_id,parcela_id''',{'desde':'2026-06-01','hasta':'2026-09-10'})
        positive=report['outside_positive']
        report['outside_positive']={'count':len(positive),'examples':positive[:5]}
        # Captura de las seis consultas reales generadas por helpers existentes.
        # Sustitución temporal en memoria para registrar execute; ningún archivo cambia.
        from contextlib import contextmanager
        from unittest.mock import patch
        from lixiviacion import db
        class Observed:
            def execute(self,statement,params):
                sql=str(statement)
                assert sql.lstrip().upper().startswith('SELECT')
                log.append({'label':'runtime_helper','sql':sql,'params':dict(params)})
                return conn.execute(statement,params)
        @contextmanager
        def observed(): yield Observed()
        f={'desde':'2026-06-01','hasta':'2026-09-10','pad':None,'campana':None,'parcela':None,'estado':None}
        with patch.object(db,'_connection',observed):
            opts=db.options(f)
            totals,daily=db.overview(f)
            page,total,page_number=db.detail(f)
        report['runtime_helpers']={'totals':totals,'daily_rows':len(daily),'detail_total':total,
            'page_rows':len(page),'campaign_options':len(opts[0]),'parcel_options':len(opts[1])}
    after={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    report['runtime_hashes_unchanged']=before==after
    report['runtime_hashes']=after
    report['executed_at']='2026-10-05'
    (OUT/'resultados.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    (OUT/'consultas_readonly.json').write_text(json.dumps(log,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    (OUT/'consultas_readonly.sql').write_text('\n\n'.join('-- '+x['label']+'\n-- Parámetros SQLAlchemy: '+json.dumps(x['params'],default=str)+'\n'+x['sql']+';' for x in log),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('objects','runtime_hashes')},ensure_ascii=False,indent=2,default=str))


if __name__=='__main__': main()
