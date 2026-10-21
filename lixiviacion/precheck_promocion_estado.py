"""Precheck read-only DEV. Respalda definiciones exactas; nunca ejecuta DDL."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from sqlalchemy import text
from .db import _connection

OUT = (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion/promocion_estado_operacional_20261005')
TEST = 'inventar_SpcHidr.fn_estado_operacional_parcela_diario_test_v2'
OFFICIAL = 'inventar_SpcHidr.fn_estado_operacional_parcela_diario'


def run():
    if os.getenv('SQLSERVER_DB','').lower() != 'inventar_spchidr':
        raise RuntimeError('Solo DEV.')
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'precheck.json').exists():
        raise RuntimeError('Evidencia previa existente; no sobrescribir respaldos.')
    with _connection() as conn:
        database = conn.execute(text('SELECT DB_NAME()')).scalar_one()
        if database.lower() != 'inventar_spchidr':
            raise RuntimeError('Conexión fuera de DEV.')
        report={'database':database,'objects':{},'ddl_executed':False}
        definitions={}
        for name,filename in [(TEST,'01_test_v2_original.sql'),(OFFICIAL,'02_oficial_previo.sql')]:
            metadata=conn.execute(text('''SELECT o.object_id,o.type,o.type_desc,
                m.uses_ansi_nulls,m.uses_quoted_identifier
                FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
                WHERE o.object_id=OBJECT_ID(:name)'''),{'name':name}).mappings().one_or_none()
            definition=conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'),{'name':name}).scalar_one()
            definitions[name]=definition
            report['objects'][name]=dict(metadata) if metadata else None
            if metadata and definition is None:
                raise RuntimeError('Definición no disponible; detenerse.')
            (OUT/filename).write_text(definition if definition is not None else '-- El objeto oficial no existía en DEV al realizar este precheck.\n',encoding='utf-8',newline='')
        if not report['objects'][TEST] or report['objects'][TEST]['type'] not in ('IF','TF','FN'):
            raise RuntimeError('TEST V2 no existe o no es función.')
        dependencies=conn.execute(text('''SELECT OBJECT_SCHEMA_NAME(d.referencing_id) AS schema_name,
            OBJECT_NAME(d.referencing_id) AS object_name,d.referenced_schema_name,d.referenced_entity_name,
            d.referenced_id,d.is_ambiguous FROM sys.sql_expression_dependencies d
            WHERE d.referenced_id IN (OBJECT_ID(:official),OBJECT_ID(:test))
            OR d.referencing_id IN (OBJECT_ID(:official),OBJECT_ID(:test))
            OR (d.referenced_schema_name='inventar_SpcHidr'
                AND d.referenced_entity_name IN ('fn_estado_operacional_parcela_diario','fn_estado_operacional_parcela_diario_test_v2'))'''),{'official':OFFICIAL,'test':TEST}).mappings()
        report['dependencies']=[dict(r) for r in dependencies]
        # Complemento textual: referencias dinámicas visibles en módulos, sin ejecutar objetos.
        report['text_references']=[dict(r) for r in conn.execute(text('''SELECT s.name AS schema_name,o.name,o.type_desc
            FROM sys.sql_modules m JOIN sys.objects o ON o.object_id=m.object_id JOIN sys.schemas s ON s.schema_id=o.schema_id
            WHERE m.definition LIKE :needle'''),{'needle':'%fn_estado_operacional_parcela_diario%'}).mappings()]
        rows=[dict(r) for r in conn.execute(text(f'SELECT * FROM {TEST}(:fecha)'),{'fecha':'2026-09-10'}).mappings()]
        report['canonical']={'date':'2026-09-10','rows':len(rows),
            'unique_pad_parcel':len({(r['pad_id'],r['numero_parcela']) for r in rows}),
            'distribution':{str(p):dict(Counter(r['estado_operacional'] for r in rows if r['pad_id']==p)) for p in (1,2)}}
        expected={'1':{'MIXTO':1,'REPOSO_PRE_RECLAMO':12,'RIEGO_DRENAJE':19},
                  '2':{'APILADO':1,'CONFORMADO_PRE_RIEGO':2,'MIXTO':2,'REPOSO_PRE_RECLAMO':5,'RIEGO_DRENAJE':18}}
        report['canonical']['expected']=expected
        report['canonical']['matches_expected']=report['canonical']['distribution']==expected
        report['canonical']['cases']=[r for r in rows if (r['pad_id'],r['numero_parcela']) in ((1,1),(1,17),(2,1),(2,2),(2,7),(2,26),(2,27),(2,28))]
        normalized=definitions[TEST].replace('fn_estado_operacional_parcela_diario_test_v2','fn_estado_operacional_parcela_diario')
        report['normalized_test_sha256']=hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        (OUT/'precheck.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        print(json.dumps({'objects':report['objects'],'canonical':{k:v for k,v in report['canonical'].items() if k!='cases'},
                          'dependencies':report['dependencies']},ensure_ascii=False,indent=2,default=str))


if __name__=='__main__': run()
