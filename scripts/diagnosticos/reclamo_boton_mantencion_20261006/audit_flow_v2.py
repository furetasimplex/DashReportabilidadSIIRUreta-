"""Read-only DEV audit for the Reclamo phased backfill."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
DEF_DIR = HERE / "sp_definitions_v2_before"
DEF_DIR.mkdir(exist_ok=True)
NAMES = (
    "sp_auto_mantener_secuencia", "sp_auto_congelar_modulos_nuevos",
    "sp_auto_cerrar_y_avanzar_secuencia", "sp_congelar_modulo",
    "sp_definir_secuencia", "sp_sincronizar_desde_etl",
)
with get_engine().connect() as conn:
    ident = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if ident["server_name"] != "VPS-5347319-X" or ident["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Refusing audit outside DEV: {ident}")
    definitions = {}
    for name in NAMES:
        definition = conn.execute(text("SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"), {"obj": f"reclamo.{name}"}).scalar_one()
        (DEF_DIR / f"reclamo.{name}.sql").write_text(definition, encoding="utf-8")
        definitions[name] = hashlib.sha256(definition.encode("utf-8")).hexdigest()
    rows = [dict(r) for r in conn.execute(text("""
        WITH topo AS (
          SELECT [campaña_id],pad_id,modulo_id,MIN(CAST(fecha_medicion AS date)) AS primera_topografia,
                 MAX(CAST(fecha_medicion AS date)) AS ultima_topografia
          FROM reclamo.topografia_avance
          WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 80 AND estado='VIGENTE'
          GROUP BY [campaña_id],pad_id,modulo_id
        ), source AS (
          SELECT [campaña_id],pad_id,modulo_id,MIN(CAST(fecha AS date)) AS primera_fuente,
                 MAX(CAST(fecha AS date)) AS ultima_fuente
          FROM inventar_SpcHidr.control_reclamo_diario
          WHERE [campaña_id]=10 AND pad_id=2 AND modulo_id BETWEEN 76 AND 80
            AND COALESCE(volumen_diario_m3,0)>0
          GROUP BY [campaña_id],pad_id,modulo_id
        )
        SELECT s.secuencia_id,s.modulo_id,s.modulo_numero,s.orden_secuencia,s.estado,
               CONVERT(varchar(10),s.fecha_apertura,23) AS apertura_actual,
               CONVERT(varchar(10),s.fecha_cierre,23) AS cierre_actual,
               CONVERT(varchar(10),t.primera_topografia,23) AS primera_topografia,
               CONVERT(varchar(10),t.ultima_topografia,23) AS ultima_topografia,
               CONVERT(varchar(10),f.primera_fuente,23) AS primera_fuente,
               CONVERT(varchar(10),f.ultima_fuente,23) AS ultima_fuente
        FROM reclamo.secuencia_rotopala s
        LEFT JOIN topo t ON t.[campaña_id]=s.[campaña_id] AND t.pad_id=s.pad_id AND t.modulo_id=s.modulo_id
        LEFT JOIN source f ON f.[campaña_id]=s.[campaña_id] AND f.pad_id=s.pad_id AND f.modulo_id=s.modulo_id
        WHERE s.[campaña_id]=10 AND s.pad_id=2 AND s.modulo_id BETWEEN 76 AND 80
        ORDER BY s.orden_secuencia
    """)).mappings()]
    logs = [dict(r) for r in conn.execute(text("""
        SELECT TOP (200) le.ejecucion_id,le.procedimiento,le.fecha_inicio,le.fecha_fin,
               le.estado AS estado_ejecucion,le.mensaje,la.log_id,la.accion,
               la.[campaña_id] AS campana_id,la.modulo_id,la.detalle
        FROM reclamo.log_ejecucion le
        LEFT JOIN reclamo.log_automatizacion la ON la.ejecucion_id=le.ejecucion_id
        WHERE le.fecha_inicio >= '2026-10-06T11:30:00'
          AND le.procedimiento='reclamo.sp_auto_mantener_secuencia'
        ORDER BY le.ejecucion_id DESC,la.log_id
    """)).mappings()]
result = {"captured_utc": datetime.now(timezone.utc).isoformat(), "identity": ident,
          "definition_hashes": definitions, "rows": rows, "automation_logs": logs, "read_only": True}
(HERE / "flow_v2_live_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
(HERE / "timeline_76_80_before.json").write_text(json.dumps({k: result[k] for k in ("captured_utc","identity","rows","read_only")}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
print(json.dumps({"identity": ident, "definition_hashes": definitions, "rows": rows,
                  "automation_logs": logs}, ensure_ascii=False, indent=2, default=str))
