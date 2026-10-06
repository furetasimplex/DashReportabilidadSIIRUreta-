"""Auditoría secuencial DEV. Solo SELECT y SET STATISTICS de sesión; nunca altera runtime."""
import argparse
from datetime import date,timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import time
from sqlalchemy import text
from lixiviacion import db,callbacks

OUT=Path(__file__).parent
END=date(2026,9,10)
CALENDAR='''WITH fechas AS (SELECT CAST(:desde AS date) AS fecha UNION ALL
SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date))
SELECT COUNT(*) AS dias FROM fechas OPTION (MAXRECURSION 32767)'''
SINGLE=f"SELECT {','.join(db.OP_FIELDS)} FROM {db.OP_SOURCE}(:fecha) WHERE pad_id=:pad_id AND parcela_id=:parcela_id"


def save(name,value):
    (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')


def hashes():
    files=list(Path('lixiviacion').glob('*.py'))+[Path('layout.py')]+list(Path('assets').glob('*.css'))
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def execute(raw,engine,sql,params):
    compiled=text(sql).compile(dialect=engine.dialect)
    cursor=raw.cursor()
    start=time.perf_counter()
    cursor.execute(str(compiled),tuple(params[k] for k in compiled.positiontup))
    messages=[]; datasets=[]; plans=[]
    while True:
        messages.extend(str(m[1]) for m in cursor.messages)
        if cursor.description:
            names=[c[0] for c in cursor.description]
            rs=cursor.fetchall()
            if len(names)==1 and rs and isinstance(rs[0][0],str) and '<ShowPlanXML' in rs[0][0]:
                plans.extend(r[0] for r in rs)
            else:
                datasets.append([dict(zip(names,r)) for r in rs])
            messages.extend(str(m[1]) for m in cursor.messages)
        if not cursor.nextset():
            messages.extend(str(m[1]) for m in cursor.messages)
            break
    elapsed=time.perf_counter()-start
    cursor.close()
    # Algunas versiones ODBC conservan mensajes al llamar fetchall: eliminar solo repetición adyacente.
    clean=[]
    for m in messages:
        if not clean or clean[-1]!=m: clean.append(m)
    return datasets,clean,plans,elapsed


def measure(raw,engine,label,sql,params,rep=1,plan=False):
    if plan: raw.cursor().execute('SET STATISTICS XML ON').close()
    try: data,msg,plans,elapsed=execute(raw,engine,sql,params)
    finally:
        if plan: raw.cursor().execute('SET STATISTICS XML OFF').close()
    stem=f'{label}_r{rep}'
    (OUT/'statistics_io_time'/f'{stem}.txt').write_text('\n'.join(msg),encoding='utf-8')
    for i,p in enumerate(plans):
        (OUT/'plans'/f'{label}_actualplan{("_"+str(i)) if i else ""}.sqlplan').write_text(p,encoding='utf-8')
    rows=data[0] if data else []
    io=[]
    pattern=r"Table '([^']+)'. Scan count (\d+), logical reads (\d+), physical reads (\d+), (?:page server reads \d+, )?read-ahead reads (\d+)"
    for m in re.finditer(pattern,'\n'.join(msg)):
        io.append(dict(zip(('object','scan_count','logical_reads','physical_reads','read_ahead_reads'),[m[1]]+[int(m[j]) for j in range(2,6)])))
    times=[{'cpu_ms':int(m[1]),'elapsed_ms':int(m[2])} for m in re.finditer(r'CPU time = (\d+) ms,\s*elapsed time = (\d+) ms','\n'.join(msg))]
    result={'label':label,'rep':rep,'params':params,'rows':len(rows),'client_seconds':elapsed,'io':io,
            'time_messages':times,'actual_plans':len(plans),'with_statistics_xml':plan}
    print(stem,round(elapsed,3),'s',len(rows),'rows',len(io),'IO messages',flush=True)
    return result,rows


def metadata(raw,engine):
    def read(name,sql):
        try: return execute(raw,engine,sql,{})[0]
        except Exception as e: return {'unavailable':type(e).__name__,'detail':str(e)[:700]}
    tables="'campana_parcela_control','flujos_reales_oxido','flujos_reales_sulfuro','drena_concentrados_oxido','drena_concentrados_sulfuro','pad','parcela'"
    save('indices.json',read('indexes',f'''SELECT s.name AS schema_name,t.name AS table_name,i.name,i.type_desc,i.is_unique,
        i.is_disabled,i.filter_definition,c.name AS column_name,ic.key_ordinal,ic.is_included_column
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id JOIN sys.indexes i ON i.object_id=t.object_id
        LEFT JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
        LEFT JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
        WHERE s.name='inventar_SpcHidr' AND t.name IN ({tables}) ORDER BY t.name,i.index_id,ic.key_ordinal,ic.index_column_id'''))
    save('estadisticas.json',read('stats',f'''SELECT t.name AS table_name,st.name,st.auto_created,st.user_created,
        p.last_updated,p.rows,p.rows_sampled,p.steps,p.modification_counter
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.stats st ON st.object_id=t.object_id OUTER APPLY sys.dm_db_stats_properties(st.object_id,st.stats_id) p
        WHERE s.name='inventar_SpcHidr' AND t.name IN ({tables})'''))
    save('dmv_query_store.json',{'options':read('qs','SELECT actual_state_desc,desired_state_desc,readonly_reason FROM sys.database_query_store_options'),
        'matching_cache':read('cache',"""SELECT qs.execution_count,qs.total_elapsed_time/NULLIF(qs.execution_count,0) AS avg_elapsed_us,
        qs.total_worker_time/NULLIF(qs.execution_count,0) AS avg_cpu_us,
        qs.total_logical_reads/NULLIF(qs.execution_count,0) AS avg_logical_reads,qs.last_execution_time,
        CONVERT(varchar(130),qs.query_hash,1) AS query_hash,CONVERT(varchar(130),qs.query_plan_hash,1) AS plan_hash,
        SUBSTRING(t.text,(qs.statement_start_offset/2)+1,((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(t.text)
        ELSE qs.statement_end_offset END-qs.statement_start_offset)/2)+1) AS statement_text
        FROM sys.dm_exec_query_stats qs CROSS APPLY sys.dm_exec_sql_text(qs.sql_handle) t
        WHERE t.dbid=DB_ID() AND t.text LIKE '%WITH fechas AS%' AND t.text LIKE '%fn_estado_operacional_parcela_diario%'
        AND t.text NOT LIKE '%sys.dm_exec_query_stats%'""")})


def run(probe=False):
    if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('Solo DEV')
    OUT.mkdir(exist_ok=True)
    for d in ('plans','statistics_io_time'): (OUT/d).mkdir(exist_ok=True)
    (OUT/'timeline_actual.sql').write_text(db.OP_TIMELINE_SQL,encoding='utf-8')
    (OUT/'cabecera_actual.sql').write_text(db.OP_HEADER_SQL,encoding='utf-8')
    (OUT/'calendar_only.sql').write_text(CALENDAR,encoding='utf-8')
    (OUT/'single_day.sql').write_text(SINGLE,encoding='utf-8')
    before=hashes();save('runtime_before.json',before)
    engine=db.get_engine()
    raw=engine.raw_connection()
    measurements=[]; profiles=[]
    try:
        cur=raw.cursor();cur.execute('SELECT DB_NAME()');assert cur.fetchone()[0].lower()=='inventar_spchidr';cur.close()
        # Session settings se desactivan en finally; no cambiar idioma, compatibilidad, MAXDOP ni caches.
        raw.cursor().execute('SET STATISTICS IO ON; SET STATISTICS TIME ON').close()
        identities=execute(raw,engine,f'SELECT pad_id,parcela_id,numero_parcela FROM {db.OP_SOURCE}(:fecha)',{'fecha':END})[0][0]
        cases=[(1,1),(1,17),(1,29),(2,1),(2,7),(2,9),(2,28)]
        lookup={(r['pad_id'],r['numero_parcela']):r['parcela_id'] for r in identities}
        save('identities.json',[r for r in identities if (r['pad_id'],r['numero_parcela']) in cases])
        def take(label,sql,params,rep=1,plan=False):
            result,rows=measure(raw,engine,label,sql,params,rep,plan)
            measurements.append(result);save('mediciones.json',measurements)
            return rows
        if probe:
            take('probe_calendar',CALENDAR,{'desde':date(2026,6,1),'hasta':END})
            take('probe_single',SINGLE,{'fecha':END,'pad_id':1,'parcela_id':lookup[(1,1)]},plan=True)
            return
        for pad,num in cases:
            for days in ([1,7,31,62,102] if (pad,num) in ((1,1),(2,7)) else [102]):
                params={'desde':END-timedelta(days=days-1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
                for rep in (1,2,3):
                    rows=take(f'timeline_{days}d_{"ox" if pad==1 else "sulf"}_p{num}',db.OP_TIMELINE_SQL,params,rep)
                    assert len(rows)==days and len({r['fecha'] for r in rows})==days
                    assert all((r['pad_id'],r['parcela_id'])==(pad,lookup[(pad,num)]) for r in rows)
                    begin=time.perf_counter();fig=callbacks.operational_timeline(rows,{'desde':str(params['desde']),'hasta':str(END)});built=time.perf_counter()
                    payload=fig.to_json();serialized=time.perf_counter()
                    profiles.append({'pad':pad,'parcel_number':num,'days':days,'rep':rep,
                        'figure_seconds':built-begin,'serialization_seconds':serialized-built,'json_bytes':len(payload.encode()),
                        'sql_execute_fetch_seconds':measurements[-1]['client_seconds']})
                    save('python_profile.json',profiles)
        for rep in (1,2,3): take('calendar_102d',CALENDAR,{'desde':date(2026,6,1),'hasta':END},rep)
        for pad,num in ((1,1),(2,7)):
            params={'fecha':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]}
            for rep in (1,2,3):
                take(f'single_{pad}',SINGLE,params,rep)
                take(f'header_{pad}',db.OP_HEADER_SQL,params,rep)
            take(f'single_{pad}',SINGLE,params,4,True)
            take(f'timeline_102d_{"ox" if pad==1 else "sulf"}_p{num}',db.OP_TIMELINE_SQL,
                 {'desde':date(2026,6,1),'hasta':END,'pad_id':pad,'parcela_id':lookup[(pad,num)]},4,True)
        for obj in ('campana_parcela_control','v_flujos_oxido_unpivot','v_flujos_sulfuro_unpivot',
                    'v_drena_oxido_operacional','v_drena_sulfuro_operacional','pad','parcela'):
            sql=f'SELECT COUNT_BIG(*) AS rows FROM inventar_SpcHidr.{obj}'
            (OUT/(obj+'_probe.sql')).write_text(sql,encoding='utf-8')
            for rep in (1,2,3): take('source_'+obj,sql,{},rep)
        metadata(raw,engine)
    finally:
        raw.cursor().execute('SET STATISTICS XML OFF; SET STATISTICS IO OFF; SET STATISTICS TIME OFF').close()
        raw.rollback();raw.close()
        after=hashes();save('runtime_after.json',{'unchanged':before==after,'hashes':after})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--probe',action='store_true');a=p.parse_args();run(a.probe)
