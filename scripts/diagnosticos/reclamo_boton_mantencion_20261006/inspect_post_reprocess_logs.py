"""Read DEV automation logs related to the completed Reclamo recalculation."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
HERE = Path(__file__).resolve().parent
sql = text("""
SELECT TOP (120) le.ejecucion_id, le.procedimiento, le.fecha_inicio, le.fecha_fin,
       le.estado AS estado_ejecucion, la.log_id, la.accion, la.pad_id,
       la.[campaÃ±a_id] AS campana_id, la.modulo_id, la.modulo_numero, la.detalle
FROM reclamo.log_ejecucion le
LEFT JOIN reclamo.log_automatizacion la ON la.ejecucion_id=le.ejecucion_id
WHERE le.fecha_inicio >= '2026-10-06T14:32:00'
  AND le.procedimiento IN ('reclamo.sp_auto_mantener_secuencia',
                           'reclamo.sp_auto_cerrar_y_avanzar_secuencia',
                           'reclamo.sp_auto_congelar_modulos_nuevos')
ORDER BY le.ejecucion_id DESC, la.log_id
""")
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if identity["server_name"] != "VPS-5347319-X" or identity["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Refusing inspection outside guarded DEV: {identity}")
    rows = [dict(r) for r in conn.execute(sql).mappings()]
result = {"identity": identity, "inspected_utc": datetime.now(timezone.utc).isoformat(), "rows": rows}
(HERE / "post_reprocess_automation_logs.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
