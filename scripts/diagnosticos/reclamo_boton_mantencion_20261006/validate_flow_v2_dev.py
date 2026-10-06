"""Read-only DEV validation before/after the v2 reprocess."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
HERE = Path(__file__).resolve().parent
if len(sys.argv) != 2 or sys.argv[1] not in ("migration_persisted", "post_reprocess_v2", "idempotence_v2"):
    raise SystemExit("Usage: validate_flow_v2_dev.py {migration_persisted|post_reprocess_v2|idempotence_v2}")
phase = sys.argv[1]
queries = {
    "sequence": """
        SELECT secuencia_id,modulo_id,modulo_numero,estado,
               CONVERT(varchar(10),fecha_apertura,23) AS apertura,
               CONVERT(varchar(10),fecha_cierre,23) AS cierre
        FROM reclamo.secuencia_rotopala
        WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 80
        ORDER BY modulo_id
    """,
    "topography_26sep_03oct": """
        SELECT modulo_id,CONVERT(varchar(10),fecha_medicion,23) AS fecha,
               estado,medicion_valida
        FROM reclamo.topografia_avance
        WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id IN (78,79)
          AND fecha_medicion>='2026-09-26' AND fecha_medicion<'2026-10-04'
        ORDER BY fecha_medicion,modulo_id
    """,
    "topography_04oct": """
        SELECT modulo_id,CONVERT(varchar(10),fecha_medicion,23) AS fecha
        FROM reclamo.topografia_avance
        WHERE [campaña_id]=10 AND pad_id=2 AND fecha_medicion='2026-10-04'
    """,
    "preliminary_04oct": """
        SELECT fecha_operacion,[campaña_id] AS campana_id,pad_id,modulo_id,
               modulo_numero,rotopala_id,horas_rotopala,tms_preliminar_dia,
               fuente_reclamo,flag_preliminar
        FROM reclamo.v_preliminar_cv25
        WHERE fecha_operacion='2026-10-04' AND pad_id=2 AND [campaña_id]=10
    """,
    "daily_topography": """
        SELECT fecha_operacion,modulo_id,rotopala_id,tms_rotopala_dia,fuente_reclamo
        FROM reclamo.v_reclamo_diario
        WHERE fecha_operacion>='2026-09-26' AND fecha_operacion<'2026-10-04'
          AND pad_id=2 AND [campaña_id]=10 AND modulo_id IN (78,79)
        ORDER BY fecha_operacion,modulo_id
    """,
    "daily_04oct": """
        SELECT fecha_operacion,modulo_id,rotopala_id,tms_rotopala_dia,fuente_reclamo
        FROM reclamo.v_reclamo_diario
        WHERE fecha_operacion='2026-10-04' AND pad_id=2 AND [campaña_id]=10
    """,
    "difference_04oct": "SELECT * FROM reclamo.v_diferencia_cv25 WHERE fecha='2026-10-04'",
}
with get_engine().connect() as conn:
    ident = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if ident["server_name"] != "VPS-5347319-X" or ident["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Unexpected DB: {ident}")
    result = {"identity": ident, "phase": phase, "captured_utc": datetime.now(timezone.utc).isoformat()}
    for name, sql in queries.items():
        result[name] = [dict(r) for r in conn.execute(text(sql)).mappings()]
expected = json.loads((HERE / "timeline_76_80_expected.json").read_text(encoding="utf-8"))
by_mod = {r["modulo_id"]: r for r in result["sequence"]}
result["dates_match_expected"] = all(
    by_mod[r["modulo_id"]]["apertura"] == r["apertura_calculada"]
    and by_mod[r["modulo_id"]]["cierre"] == r["cierre_calculado"]
    and by_mod[r["modulo_id"]]["estado"] == r["estado"]
    for r in expected["rows"]
)
(HERE / f"{phase}.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
