"""BACKFILL EXTRAORDINARIO: inventario SELECT previo, nunca ejecuta procedimientos."""
import hashlib
import json
import os
from pathlib import Path
from sqlalchemy import text
from db_connection import get_engine

P = Path(__file__).parent
ROOTS = ['sp_mantiene_apilado_tmh_v2_test', 'sp_refrescar_historico_apilado_test',
         'sp_mantiene_factor_ajuste_camiones_v2_test', 'sp_refrescar_clays_cufe',
         'sp_actualizar_reporte_turno_cache_emision_test', 'sp_calcular_resumen_intervalo_totTM',
         'sp_refrescar_representatividad_torres', 'sp_sincronizar_bd_ton',
         'sp_mantiene_datos_conciliados_emision_test']

def save(name, value):
    (P / name).write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str)+'\n', encoding='utf-8')

def main():
    if (P/'before.json').exists() or (P/'ejecucion.json').exists():
        raise RuntimeError('Inventario congelado: no sobrescribir evidencia previa al backfill')
    if os.getenv('SQLSERVER_DB', '').lower() != 'inventar_spchidr':
        raise RuntimeError('Solo DEV inventar_SpcHidr')
    with get_engine().connect() as c:
        def q(sql, **params):
            assert sql.lstrip().upper().startswith('SELECT')
            return [dict(r) for r in c.execute(text(sql), params).mappings()]
        assert q('SELECT DB_NAME() AS db')[0]['db'].lower() == 'inventar_spchidr'
        objects = q('SELECT o.object_id,s.name AS schema_name,o.name,o.type_desc,m.definition FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.is_ms_shipped=0')
        deps = q('SELECT referencing_id,referenced_id,referenced_server_name,referenced_database_name,referenced_schema_name,referenced_entity_name FROM sys.sql_expression_dependencies')
        ids = {r['object_id']:r for r in objects}
        wanted = {r['object_id'] for r in objects if r['schema_name']=='inventar_SpcHidr' and r['name'] in ROOTS}
        pending = list(wanted)
        while pending:
            oid = pending.pop()
            for d in deps:
                if d['referencing_id']==oid and d['referenced_id'] in ids and d['referenced_id'] not in wanted:
                    wanted.add(d['referenced_id']); pending.append(d['referenced_id'])
        folder=P/'definitions';folder.mkdir(exist_ok=True)
        result=[]
        for oid in sorted(wanted):
            r=dict(ids[oid]); definition=r.pop('definition')
            if definition:
                (folder/(r['schema_name']+'__'+r['name']+'.sql')).write_text(definition,encoding='utf-8')
                r['sha256']=hashlib.sha256(definition.encode()).hexdigest()
            result.append(r)
        save('objects.json',result)
        save('dependencies.json',[d for d in deps if d['referencing_id'] in wanted])
        save('columns.json',q('SELECT s.name AS schema_name,o.name AS object_name,c.name,c.column_id,t.name AS data_type,c.is_identity,c.is_computed FROM sys.columns c JOIN sys.objects o ON o.object_id=c.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE o.is_ms_shipped=0'))
        save('triggers.json',q('SELECT OBJECT_SCHEMA_NAME(t.parent_id) AS schema_name,OBJECT_NAME(t.parent_id) AS table_name,t.name,t.is_disabled,m.definition FROM sys.triggers t LEFT JOIN sys.sql_modules m ON m.object_id=t.object_id WHERE t.parent_class=1'))
        save('indexes.json',q('SELECT OBJECT_SCHEMA_NAME(i.object_id) AS schema_name,OBJECT_NAME(i.object_id) AS table_name,i.name,i.is_unique,i.is_primary_key,c.name AS column_name,ic.key_ordinal FROM sys.indexes i JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id WHERE i.is_unique=1'))
        save('runtime_before.json',{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('report_export').rglob('*.py')})
        print(json.dumps({'database':'inventar_SpcHidr','root_objects':ROOTS,'objects':len(result),'status':'READ_ONLY_INVENTORY'},ensure_ascii=False))

if __name__=='__main__':main()
