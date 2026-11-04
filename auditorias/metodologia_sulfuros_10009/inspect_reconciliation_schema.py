"""Inspect reconciliation metadata with SELECT only; no values or writes."""
import contextlib, io, json, sys, re
from pathlib import Path
from sqlalchemy import event, text

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'DashReportabilidadSIIR'))
with contextlib.redirect_stdout(io.StringIO()):
    from curvas_recon import db_pipeline as db
    engine = db.get_engine()

@event.listens_for(engine, 'before_cursor_execute')
def require_select(conn, cursor, statement, parameters, context, executemany):
    cleaned = re.sub(r'/\*.*?\*/|--[^\n]*', '', statement, flags=re.S).strip()
    if not re.match(r'(?is)^(select|with)\b', cleaned) or re.search(r'(?i)\b(insert|update|delete|merge|truncate|alter|drop|create|exec|execute|call)\b', cleaned):
        raise ValueError('Non-SELECT blocked')
    cursor.connection.timeout = 20

q = text('''SELECT t.name AS tabla, c.name AS columna, ty.name AS tipo,
                   c.is_nullable AS permite_nulo
FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
JOIN sys.columns c ON c.object_id=t.object_id
JOIN sys.types ty ON c.user_type_id=ty.user_type_id
WHERE s.name=:schema AND t.name IN
('reconciliacion_run','reconciliacion_detalle','reconciliacion_detalle_dia','lectura_recuperacion',
 'Recuperaciones_pad','stg_recuperaciones_oficial','Recuperaciones_pad_pre_oficial','modulos_turnos')
ORDER BY t.name,c.column_id''')
try:
    with engine.connect() as conn:
        rows = [dict(r) for r in conn.execute(q, {'schema': db.SCHEMA}).mappings()]
    print(json.dumps(rows, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({'status':'failed','error_type':type(exc).__name__}))
    raise SystemExit(1)
