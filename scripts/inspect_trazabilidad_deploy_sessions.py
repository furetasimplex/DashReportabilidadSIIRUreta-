from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine
from sqlalchemy import text

sql = text("""
SELECT
    r.session_id, r.status, r.command, r.blocking_session_id,
    r.wait_type, r.wait_time, r.total_elapsed_time,
    s.host_name, s.program_name, s.login_name,
    SUBSTRING(q.text, (r.statement_start_offset/2)+1,
      ((CASE r.statement_end_offset WHEN -1 THEN DATALENGTH(q.text)
        ELSE r.statement_end_offset END-r.statement_start_offset)/2)+1) statement_text
FROM sys.dm_exec_requests r
JOIN sys.dm_exec_sessions s ON s.session_id=r.session_id
CROSS APPLY sys.dm_exec_sql_text(r.sql_handle) q
WHERE r.session_id <> @@SPID
  AND (q.text LIKE '%sp_actualizar_reporte_turno_cache_emision_test%'
       OR q.text LIKE '%trazabilidad_analitos%'
       OR r.blocking_session_id <> 0)
ORDER BY r.total_elapsed_time DESC;
""")

with get_engine().connect() as conn:
    for row in conn.execute(sql).mappings():
        print(dict(row))
