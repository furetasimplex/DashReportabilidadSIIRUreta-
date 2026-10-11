"""Read-only live audit of sequence date writers for PAD2 campaign 10."""
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

OUT = Path(__file__).resolve().parent
DEF_DIR = OUT / "sp_definitions"
DEF_DIR.mkdir(parents=True, exist_ok=True)
TARGETS = {
    "sp_auto_mantener_secuencia",
    "sp_auto_congelar_modulos_nuevos",
    "sp_auto_cerrar_y_avanzar_secuencia",
    "sp_definir_secuencia",
    "v_preliminar_cv25",
    "v_preliminar_cv25_con_acumulado",
}

with get_engine().connect() as conn:
    ident = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    modules = conn.execute(text("""
        SELECT s.name AS schema_name, o.name AS object_name, o.type_desc,
               sm.definition
        FROM sys.objects o
        JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules sm ON sm.object_id=o.object_id
        WHERE (s.name='reclamo' AND o.name IN (
            'sp_auto_mantener_secuencia','sp_auto_congelar_modulos_nuevos',
            'sp_auto_cerrar_y_avanzar_secuencia','sp_definir_secuencia',
            'v_preliminar_cv25','v_preliminar_cv25_con_acumulado'
        ))
        ORDER BY s.name,o.name
    """)).mappings().all()
    date_refs = conn.execute(text("""
        SELECT s.name AS schema_name, o.name AS object_name, o.type_desc,
               sm.definition
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id
        JOIN sys.sql_modules sm ON sm.object_id=o.object_id
        WHERE sm.definition LIKE '%fecha_apertura%'
           OR sm.definition LIKE '%fecha_cierre%'
        ORDER BY s.name,o.name
    """)).mappings().all()
    cols = conn.execute(text("""
        SELECT s.name AS schema_name,t.name AS table_name,c.column_id,c.name AS column_name,
               ty.name AS type_name,c.is_nullable
        FROM sys.tables t JOIN sys.schemas s ON s.schema_id=t.schema_id
        JOIN sys.columns c ON c.object_id=t.object_id
        JOIN sys.types ty ON ty.user_type_id=c.user_type_id
        WHERE (s.name='reclamo' AND t.name IN ('secuencia_rotopala','topografia_avance','modulo_congelado'))
        ORDER BY s.name,t.name,c.column_id
    """)).mappings().all()
    simulation = conn.execute(text("""
        WITH topo AS (
            SELECT [campaña_id], modulo_id,
                   MIN(fecha_medicion) AS primera_topografia,
                   MAX(fecha_medicion) AS ultima_topografia,
                   COUNT(*) AS filas_topografia_vigente
            FROM reclamo.topografia_avance
            WHERE [campaña_id]=10 AND modulo_id BETWEEN 76 AND 80
              AND estado='VIGENTE'
            GROUP BY [campaña_id], modulo_id
        ), seq AS (
            SELECT s.secuencia_id,s.rotopala_id,s.[campaña_id],s.pad_id,s.modulo_id,
                   s.modulo_numero,s.orden_secuencia,s.estado,
                   s.fecha_apertura,s.fecha_cierre,s.observacion,
                   t.primera_topografia,t.ultima_topografia,t.filas_topografia_vigente,
                   LEAD(t.primera_topografia) OVER (
                       PARTITION BY s.rotopala_id,s.[campaña_id]
                       ORDER BY s.orden_secuencia
                   ) AS primera_topografia_siguiente
            FROM reclamo.secuencia_rotopala s
            LEFT JOIN topo t ON t.[campaña_id]=s.[campaña_id] AND t.modulo_id=s.modulo_id
            WHERE s.[campaña_id]=10 AND s.modulo_id BETWEEN 76 AND 80
        )
        SELECT *,
               CASE WHEN primera_topografia IS NOT NULL
                    THEN primera_topografia ELSE fecha_apertura END AS fecha_apertura_propuesta,
               CASE WHEN primera_topografia_siguiente IS NOT NULL
                    THEN primera_topografia_siguiente ELSE fecha_cierre END AS fecha_cierre_propuesta,
               CASE WHEN primera_topografia IS NULL THEN 'SIN_TOPOGRAFIA: conservar fecha actual; no inferir'
                    WHEN primera_topografia_siguiente IS NOT NULL THEN 'APERTURA=primera topo vigente propia; CIERRE=primera topo vigente siguiente'
                    ELSE 'APERTURA=primera topo vigente propia; CIERRE sin evidencia siguiente: conservar actual'
               END AS regla_aplicada
        FROM seq ORDER BY orden_secuencia
    """)).mappings().all()
    action_logs = conn.execute(text("""
        SELECT TOP (200) le.ejecucion_id,le.procedimiento,le.fecha_inicio,le.fecha_fin,
               le.estado AS estado_ejecucion,le.mensaje,
               la.log_id,la.accion,la.pad_id,la.[campaña_id],la.modulo_id,
               la.modulo_numero,la.detalle
        FROM reclamo.log_ejecucion le
        LEFT JOIN reclamo.log_automatizacion la ON la.ejecucion_id=le.ejecucion_id
        WHERE le.procedimiento='reclamo.sp_auto_mantener_secuencia'
          AND (la.[campaña_id]=10 OR la.[campaña_id] IS NULL)
        ORDER BY le.ejecucion_id DESC,la.log_id
    """)).mappings().all()

    for row in modules:
        name = f"{row['schema_name']}.{row['object_name']}.sql"
        (DEF_DIR / name).write_text(row["definition"] or "", encoding="utf-8")
    ref_records = []
    for row in date_refs:
        definition = row["definition"] or ""
        ref_records.append({
            "schema": row["schema_name"],
            "object": row["object_name"],
            "type": row["type_desc"],
            "uses_sysdatetime_date": "CAST(SYSDATETIME() AS DATE)" in definition.upper(),
            "uses_getdate": "GETDATE()" in definition.upper(),
            "uses_current_timestamp": "CURRENT_TIMESTAMP" in definition.upper(),
            "mentions_fecha_transicion": "@FECHATRANSICION" in definition.upper(),
            "definition": definition,
        })

summary = {
    "database_identity": ident,
    "live_definitions": [
        {"schema": r["schema_name"], "object": r["object_name"], "type": r["type_desc"],
         "sha256_utf8": hashlib.sha256((r["definition"] or "").encode("utf-8")).hexdigest(),
         "file": f"sp_definitions/{r['schema_name']}.{r['object_name']}.sql"}
        for r in modules
    ],
    "missing_targets": sorted(TARGETS - {r["object_name"] for r in modules}),
    "date_column_references": ref_records,
    "relevant_table_columns": [dict(r) for r in cols],
    "simulation_campaign_10_modules_76_80": [dict(r) for r in simulation],
    "recent_automation_logs_campaign_10": [dict(r) for r in action_logs],
    "read_only": True,
}
(OUT / "live_backfill_sql_audit.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False,
               default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)),
    encoding="utf-8",
)
snapshot_fields = (
    "secuencia_id", "rotopala_id", "pad_id", "modulo_id", "modulo_numero",
    "orden_secuencia", "estado", "fecha_apertura", "fecha_cierre", "primera_topografia",
    "ultima_topografia", "primera_topografia_siguiente", "fecha_apertura_propuesta",
    "fecha_cierre_propuesta", "regla_aplicada",
)
snapshot = {
    "captured_utc": datetime.now(timezone.utc).isoformat(),
    "database_identity": ident,
    "scope": {"pad_id": 2, "campana_id": 10, "module_ids": [76, 77, 78, 79, 80]},
    "rows": [{"campana_id": 10, **{k: row.get(k) for k in snapshot_fields}}
             for row in summary["simulation_campaign_10_modules_76_80"]],
    "read_only": True,
}
(OUT / "sequence_backfill_snapshot_before.json").write_text(
    json.dumps(snapshot, indent=2, ensure_ascii=False,
               default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)),
    encoding="utf-8",
)
print(json.dumps({"identity": ident, "definitions": summary["live_definitions"],
                  "missing": summary["missing_targets"], "date_reference_objects": [
                      {k: r[k] for k in ("schema","object","type","uses_sysdatetime_date","uses_getdate","uses_current_timestamp","mentions_fecha_transicion")}
                      for r in ref_records], "simulation": summary["simulation_campaign_10_modules_76_80"],
                  "table_columns": summary["relevant_table_columns"]}, indent=2, ensure_ascii=False,
                 default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)))
