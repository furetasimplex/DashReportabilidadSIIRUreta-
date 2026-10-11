"""Read-only validation of DEV sequence dates and Reclamo outputs after backfill."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
engine = get_engine()
queries = {
    "sequence": """
        SELECT secuencia_id, modulo_id, modulo_numero, estado,
               CONVERT(varchar(10), fecha_apertura, 23) AS fecha_apertura,
               CONVERT(varchar(10), fecha_cierre, 23) AS fecha_cierre
        FROM reclamo.secuencia_rotopala
        WHERE [campaña_id]=10 AND modulo_id BETWEEN 76 AND 80
        ORDER BY modulo_id
    """,
    "topography": """
        SELECT modulo_id, CONVERT(varchar(10), fecha_medicion, 23) AS fecha_medicion,
               COUNT_BIG(*) AS filas
        FROM reclamo.topografia_avance
        WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id IN (78,79)
          AND fecha_medicion >= '2026-09-26' AND fecha_medicion < '2026-10-04'
        GROUP BY modulo_id, CONVERT(varchar(10), fecha_medicion, 23)
        ORDER BY modulo_id, fecha_medicion
    """,
    "preliminary_oct04": """
        SELECT fecha_operacion, [campaña_id] AS campana_id, pad_id, modulo_id,
               modulo_numero, rotopala_id, horas_rotopala, tms_preliminar_dia,
               fuente_reclamo, flag_preliminar
        FROM reclamo.v_preliminar_cv25
        WHERE fecha_operacion='2026-10-04' AND pad_id=2 AND [campaña_id]=10
    """,
    "daily_oct04": """
        SELECT fecha_operacion, pad_id, [campaña_id] AS campana_id, modulo_id,
               rotopala_id, tms_rotopala_dia, fuente_reclamo
        FROM reclamo.v_reclamo_diario
        WHERE fecha_operacion='2026-10-04' AND pad_id=2 AND [campaña_id]=10
    """,
    "difference_oct04": """
        SELECT * FROM reclamo.v_diferencia_cv25 WHERE fecha='2026-10-04'
    """,
}
with engine.connect() as conn:
    identity = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if identity["server_name"] != "VPS-5347319-X" or identity["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Refusing validation outside guarded DEV: {identity}")
    result = {"identity": identity, "validated_utc": datetime.now(timezone.utc).isoformat()}
    for name, sql in queries.items():
        result[name] = [dict(row) for row in conn.execute(text(sql)).mappings()]
(HERE / "post_reprocess_validation.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print(json.dumps(result, indent=2, default=str))
