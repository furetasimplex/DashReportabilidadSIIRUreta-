"""Evidencia de cierre: consultas SELECT a DEV; no despliega ni modifica SQL."""
import json
import subprocess
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

OUT = Path(__file__).parent / 'cierre'
OUT.mkdir(exist_ok=True)
DATES = "'2026-08-31','2026-09-07','2026-09-08','2026-09-10','2026-09-13'"

def save(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, default=str, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    for args, name in [(['status','--short'],'git_status'), (['diff','--stat'],'git_stat'), (['diff'],'git_diff')]:
        (OUT / (name + '.txt')).write_bytes(subprocess.check_output(['git', *args]))
    save('inventario_archivos', [str(p) for p in Path('monitor_pi_tum').rglob('*') if p.is_file() and '__pycache__' not in str(p) and 'cierre' not in p.parts])
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        def query(name, sql):
            try:
                rows = [dict(r) for r in c.execute(text(sql)).mappings()]
                save(name, rows)
                print(name, len(rows), flush=True)
                return rows
            except Exception as e:
                save(name, {'error': str(e)})
                print(name, type(e).__name__, flush=True)
                return []
        objects = query('objetos_dev', "SELECT s.name+'.'+o.name nombre,o.type_desc,o.create_date,o.modify_date,m.definition FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name LIKE '%contingencia%' OR o.name IN ('sp_calcular_balance_flujos','cv25_diario','v_cv25_diario')")
        for r in objects:
            if r['definition']:
                (OUT / (r['nombre']+'.sql')).write_text(r['definition'],encoding='utf-8')
        for suffix, obj in [('RT','v_contingencia_totalizador_resuelto_turno'),('RO','v_contingencia_totalizador_resuelto_operacional_test')]:
            query(suffix, f'SELECT * FROM inventar_SpcHidr.{obj} WHERE fecha_operacional IN ({DATES}) ORDER BY fecha_operacional,turno,equipo_codigo')
        for r in objects:
            name=r['nombre']
            if r['type_desc']=='VIEW' and any(x in name for x in ['reclamo.', 'representatividad','peso_teorico','bd_ton']):
                cols=query('columnas_'+name, f"SELECT name FROM sys.columns WHERE object_id=OBJECT_ID('{name}')")
                datecol=next((x['name'] for x in cols if x['name'].lower() in ('fecha','fecha_operacional')),None)
                if datecol:
                    query('datos_'+name,f'SELECT * FROM {name} WHERE [{datecol}] IN ({DATES})')
        query('cv25_diario',f'SELECT * FROM reclamo.cv25_diario WHERE fecha IN ({DATES})')
        query('dependencias', "SELECT OBJECT_SCHEMA_NAME(referencing_id)+'.'+OBJECT_NAME(referencing_id) consumidor, referenced_schema_name,referenced_entity_name FROM sys.sql_expression_dependencies WHERE OBJECT_NAME(referencing_id) LIKE '%contingencia%' OR referenced_entity_name LIKE '%contingencia%'")

if __name__=='__main__':
    main()
