import sys, json
from pathlib import Path
from sqlalchemy import text
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
ROOT=Path(__file__).parent
with _engine_dev().connect() as c:
    _assert_dev_connection(c)
    if len(sys.argv)==1:
        rows=c.execute(text("SELECT s.name AS esquema,o.name,o.type_desc,m.definition FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.sql_modules m ON m.object_id=o.object_id")).mappings().all()
        (ROOT/'catalogo.json').write_text(json.dumps([dict(r) for r in rows],default=str,ensure_ascii=False,indent=2),encoding='utf-8')
        rows=c.execute(text("SELECT TABLE_SCHEMA,TABLE_NAME,COLUMN_NAME,DATA_TYPE,ORDINAL_POSITION FROM INFORMATION_SCHEMA.COLUMNS ORDER BY TABLE_SCHEMA,TABLE_NAME,ORDINAL_POSITION")).mappings().all()
        (ROOT/'columnas.json').write_text(json.dumps([dict(r) for r in rows],default=str,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Catalogo y columnas guardados')
    else:
        queries=json.loads((ROOT/sys.argv[1]).read_text(encoding='utf-8'))
        for name,sql in queries.items():
            assert sql.lstrip().upper().startswith(('SELECT','WITH'))
            rows=c.execute(text(sql)).mappings().all()
            (ROOT/(name+'.json')).write_text(json.dumps([dict(r) for r in rows],default=str,ensure_ascii=False,indent=2),encoding='utf-8')
            print(name,len(rows))
