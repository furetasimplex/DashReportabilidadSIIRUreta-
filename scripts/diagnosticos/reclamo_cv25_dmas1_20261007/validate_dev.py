"""Read-only regression evidence for the DEV D+1 projection rule."""
import csv
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
from reclamo import db

BASE = Path(__file__).resolve().parent
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")

with get_engine().connect() as connection:
    database = connection.scalar(text("SELECT DB_NAME()"))
    if database.lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    topo = [dict(row) for row in connection.execute(text("""
        SELECT mb.modulo_id, mb.pad_id, mb.rotopala_id,
               MAX(ta.fecha_medicion) AS ultima_topografia
        FROM reclamo.v_modulo_base mb
        LEFT JOIN reclamo.topografia_avance ta
          ON ta.[campaña_id] = mb.[campaña_id]
         AND ta.modulo_id = mb.modulo_id AND ta.estado = 'VIGENTE'
        WHERE mb.estado_secuencia = 'ABIERTO'
        GROUP BY mb.modulo_id, mb.pad_id, mb.rotopala_id
    """)).mappings()]
    cv = [dict(row) for row in connection.execute(text("""
        SELECT fecha, tms_estimado_r2, horas_r2, flag_preliminar
        FROM reclamo.v_cv25_diario
        WHERE fecha BETWEEN '2026-10-04' AND '2026-10-07'
        ORDER BY fecha
    """)).mappings()]
    prelim = [dict(row) for row in connection.execute(text("""
        SELECT fecha_operacion, modulo_id, pad_id, rotopala_id,
               tms_preliminar_dia, fuente_reclamo
        FROM reclamo.v_preliminar_cv25
        WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-07'
        ORDER BY fecha_operacion, modulo_id
    """)).mappings()]
    reclamo = [dict(row) for row in connection.execute(text("""
        SELECT fecha_operacion, modulo_id, fuente_reclamo, tms_rotopala_dia
        FROM reclamo.v_reclamo_diario
        WHERE fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
          AND modulo_id = 80 ORDER BY fecha_operacion
    """)).mappings()]
    material = [dict(row) for row in connection.execute(text("""
        SELECT fecha_operacion, fuente_reclamo, COUNT(*) AS filas
        FROM reclamo.calculo_diario WHERE pad_id = 2
          AND fecha_operacion BETWEEN '2026-10-04' AND '2026-10-06'
        GROUP BY fecha_operacion, fuente_reclamo
        ORDER BY fecha_operacion, fuente_reclamo
    """)).mappings()]
    definition = connection.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_preliminar_cv25'))"))
    eligible_after_topo05 = [str(row[0])[:10] for row in connection.execute(text("""
        SELECT fecha FROM reclamo.v_cv25_diario
        WHERE fecha BETWEEN '2026-10-05' AND '2026-10-07'
          AND fecha = DATEADD(DAY, 1, CAST('2026-10-05' AS date))
    """))]

assert "cv.fecha = DATEADD(DAY, 1, a.ultima_medicion_topografica)" in definition
topo80 = next(row for row in topo if row["modulo_id"] == 80)
assert str(topo80["ultima_topografia"])[:10] == "2026-10-04"
cv_by_day = {str(row["fecha"])[:10]: row for row in cv}
assert cv_by_day["2026-10-05"]["tms_estimado_r2"] == 0
assert cv_by_day["2026-10-05"]["flag_preliminar"] == "CERO_OPERACION_CONFIRMADO"
assert cv_by_day["2026-10-06"]["tms_estimado_r2"] is None
prelim80 = [row for row in prelim if row["modulo_id"] == 80]
assert len(prelim80) == 1 and str(prelim80[0]["fecha_operacion"])[:10] == "2026-10-05"
assert prelim80[0]["tms_preliminar_dia"] == 0
assert any(str(row["fecha_operacion"])[:10] == "2026-10-04" and row["fuente_reclamo"] == "TOPOGRAFIA" for row in reclamo)
assert any(str(row["fecha_operacion"])[:10] == "2026-10-05" and row["fuente_reclamo"] == "PRELIMINAR_CV25" for row in reclamo)
assert not any(str(row["fecha_operacion"])[:10] == "2026-10-06" and row["fuente_reclamo"] == "PRELIMINAR_CV25" for row in reclamo)

# Read-only counterfactual: with real topography on 05-10, only 06-10
# satisfies the date gate. Its unresolved CV25 still blocks a numeric value.
assert eligible_after_topo05 == ["2026-10-06"]
dashboard_state = db.estado_proyeccion(2, "2026-10-07")
assert len(dashboard_state) == 1
assert str(dashboard_state.iloc[0]["ultima_topografia"])[:10] == "2026-10-04"
assert str(dashboard_state.iloc[0]["fecha_preliminar"])[:10] == "2026-10-05"

with (BASE / "before_after.csv").open("w", newline="", encoding="utf-8-sig") as stream:
    writer = csv.DictWriter(stream, fieldnames=["fecha", "topografia_actual", "cv25_r2", "flag_cv25",
                                                "preliminar_actual", "fuente_v_reclamo", "elegible_con_topo_05"])
    writer.writeheader()
    for day in ("2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07"):
        writer.writerow({"fecha": day, "topografia_actual": str(topo80["ultima_topografia"])[:10],
                         "cv25_r2": cv_by_day.get(day, {}).get("tms_estimado_r2"),
                         "flag_cv25": cv_by_day.get(day, {}).get("flag_preliminar"),
                         "preliminar_actual": next((row["tms_preliminar_dia"] for row in prelim80
                                                      if str(row["fecha_operacion"])[:10] == day), None),
                         "fuente_v_reclamo": next((row["fuente_reclamo"] for row in reclamo
                                                    if str(row["fecha_operacion"])[:10] == day), None),
                         "elegible_con_topo_05": day in eligible_after_topo05})

print("PASS", database, "topo80", topo80, "prelim", prelim80,
      "materialized", material, "counterfactual_eligible", eligible_after_topo05)
