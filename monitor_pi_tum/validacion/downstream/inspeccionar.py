"""Diagnóstico downstream DEV: solo catálogo y SELECT; no refresca datos."""
import json
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection

OUT=Path(__file__).parent/'evidencia'
def save(n,v):
    (OUT/(n+'.json')).write_text(json.dumps(v,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with _engine_dev().connect() as c:
        _assert_dev_connection(c)
        objects=[dict(r) for r in c.execute(text("SELECT s.name+'.'+o.name nombre,o.type_desc,m.definition FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.is_ms_shipped=0")).mappings()]
        deps=[dict(r) for r in c.execute(text("SELECT OBJECT_SCHEMA_NAME(referencing_id)+'.'+OBJECT_NAME(referencing_id) consumidor,referenced_database_name base,referenced_schema_name esquema,referenced_entity_name objeto FROM sys.sql_expression_dependencies")).mappings()]
        save('dependencias',deps)
        selected={o['nombre'] for o in objects if any(x in o['nombre'].lower() for x in ('factor_ajuste','ajuste_camiones','apilado_tmh','reporte_turno_emision','reporte_turno_cache_emision','clays_cufe'))}
        for _ in range(12):
            added={str(d['esquema'])+'.'+str(d['objeto']) for d in deps if d['consumidor'] in selected and d['base'] in (None,'inventar_SpcHidr')}
            if added<=selected:break
            selected|=added
        selected_objects=[o for o in objects if o['nombre'] in selected]
        save('catalogo', [{k:v for k,v in o.items() if k!='definition'} for o in selected_objects])
        for o in selected_objects:
            if o['definition']:(OUT/(o['nombre']+'.sql')).write_text(o['definition'],encoding='utf-8')
        print('Definiciones y objetos',len(selected_objects),flush=True)
        names=[o['nombre'] for o in selected_objects if o['type_desc']=='USER_TABLE' and any(x in o['nombre'].lower() for x in ('factor','ajuste_camiones','control_apilado','reporte_turno_cache_emision'))]
        for n in names:
            cols=[dict(r) for r in c.execute(text('SELECT name,TYPE_NAME(user_type_id) tipo FROM sys.columns WHERE object_id=OBJECT_ID(:n) ORDER BY column_id'),{'n':n}).mappings()]
            save('columnas_'+n,cols)
            datecol=next((r['name'] for r in cols if r['name'].lower()=='fecha'),None)
            if datecol:
                rows=[dict(r) for r in c.execute(text(f"SELECT * FROM {n} WHERE [{datecol}]='20260910'")).mappings()]
                save('baseline_'+n,rows);print(n,len(rows),flush=True)
if __name__=='__main__':main()
