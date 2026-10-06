"""Solo SELECT DEV. No invoca editor/exportadores ni refrescos."""
import ast, csv, hashlib, json, calendar
from pathlib import Path
from datetime import date, timedelta
from sqlalchemy import text
from db_connection import get_engine

P=Path(__file__).parent
def save(name,x): (P/name).write_text(json.dumps(x,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
def csvsave(name,rows):
    if rows:
        with (P/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def run():
    paths=list(Path('report_export').rglob('*.py'))+[Path('layout.py')]
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    save('runtime_before.json',hashes)
    tree=ast.parse(Path('report_export/report_export.py').read_text(encoding='utf-8-sig'))
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='fetch_fecha_corte_operacional_representatividad')
    sql=next(n.value.value for n in fn.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='sql' for t in n.targets))
    (P/'consulta_fecha_cerrada.sql').write_text(sql,encoding='utf-8')
    calls=[];queries=[]
    with get_engine().connect() as conn:
        def q(s,params=None):
            assert s.lstrip().upper().startswith(('SELECT',';WITH','WITH'))
            queries.append({'sql':s,'params':params})
            return [dict(r) for r in conn.execute(text(s),params or {}).mappings()]
        assert q('SELECT DB_NAME() AS db')[0]['db'].lower()=='inventar_spchidr'
        maximo=q('SELECT MIN(fecha) AS min_fecha,MAX(fecha) AS max_fecha FROM inventar_SpcHidr.tot_TM')[0]
        meta=q("SELECT c.name,t.name AS tipo FROM sys.columns c JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.v_bitacora_rangos_norm') ORDER BY c.column_id")
        save('columns.json',meta)
        defs={}
        for obj in ('inventar_SpcHidr.v_bitacora_rangos_norm',):
            d=q('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj)) AS ddl',{'obj':obj})[0]['ddl']
            (P/(obj.split('.')[-1]+'.sql')).write_text(d,encoding='utf-8');defs[obj]=hashlib.sha256(d.encode()).hexdigest()
        deps=q("SELECT referenced_schema_name,referenced_entity_name FROM sys.sql_expression_dependencies WHERE referencing_id=OBJECT_ID('inventar_SpcHidr.v_bitacora_rangos_norm')")
        for d in deps:
            obj=f"{d['referenced_schema_name']}.{d['referenced_entity_name']}"
            definition=q('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj)) AS ddl',{'obj':obj})[0]['ddl']
            if definition:(P/(obj.replace('.','__')+'.sql')).write_text(definition,encoding='utf-8')
        ranges=[('septiembre','2026-09-01','2026-09-30'),('octubre_mes','2026-10-01','2026-10-31'),('octubre_rango','2026-10-01','2026-10-03'),('global','1900-01-01','9999-12-31')]
        for label,start,end in ranges:
            rows=q(sql,{'start':start,'end':end});calls.append({'caso':label,'start':start,'end':end,'resultado':rows})
        raw=q("SELECT * FROM inventar_SpcHidr.v_bitacora_rangos_norm WHERE fecha_turno BETWEEN '2026-09-01' AND '2026-10-31' AND Torre IN ('T1','T2','SRR')")
        save('rangos_fuente.json',raw)
        totals=q("SELECT CAST(fecha AS date) AS fecha,COUNT_BIG(*) AS registros,MIN(fecha) AS primer_ts,MAX(fecha) AS ultimo_ts FROM inventar_SpcHidr.tot_TM WHERE fecha >= '2026-09-28' AND fecha < '2026-11-01' GROUP BY CAST(fecha AS date) ORDER BY fecha")
        csvsave('totalizador_por_fecha.csv',totals)
        maximum=q("SELECT MAX(fecha_turno) AS max_fecha_rangos,MAX(CASE WHEN fecha_turno BETWEEN '2026-10-01' AND '2026-10-31' THEN fecha_turno END) AS max_fecha_octubre FROM inventar_SpcHidr.v_bitacora_rangos_norm WHERE Torre IN ('T1','T2','SRR')")[0]
        coverage=[]
        for i in range(61):
            day=date(2026,9,1)+timedelta(days=i)
            rs=[r for r in raw if str(r['fecha_turno'])[:10]==str(day)]
            end=max((r['ts_fin'] for r in rs if r['ts_fin'] is not None),default=None)
            turns=next((c['name'] for c in meta if c['name'].lower() in ('turno','turno_op','turno_norm','turno_normalizado')),None)
            closed=end is not None and maximo['max_fecha'] is not None and end<=maximo['max_fecha']
            coverage.append({'fecha':str(day),'rangos':len(rs),'torres':','.join(sorted({str(r['Torre']) for r in rs})),
                'turnos':','.join(sorted({str(r[turns]) for r in rs})) if turns else 'ver fuente',
                'max_ts_fin_dia':end,'max_totalizador':maximo['max_fecha'],'cerrada_segun_query':closed,
                'condicion':'CUMPLE' if closed else ('SIN_RANGOS' if not rs else 'FIN_POSTERIOR_A_MAX_TOTALIZADOR_O_NULL')})
        csvsave('cobertura_septiembre.csv',coverage[:30]);csvsave('cobertura_octubre.csv',coverage[30:])
        csvsave('resultado_fechas.csv',[r for r in coverage if '2026-09-28'<=r['fecha']<='2026-10-03'])
    save('parametros.json',calls);save('queries.json',queries)
    save('resultados.json',{'max_totalizador':maximo,'max_rangos':maximum,'casos':calls,'dependencias':deps,'definition_hashes':defs,
        'runtime_unchanged':all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())})
    print(json.dumps({'max_totalizador':maximo,'max_rangos':maximum,'casos':calls,'deps':deps},default=str))

if __name__=='__main__':run()
