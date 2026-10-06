"""Read-only campaign mapping and coverage check in DEV."""
from pathlib import Path
import json
import sys
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

queries = {
    "mapping": """SELECT [campaña_id] AS campana_id, [campaña] AS campana, COUNT(*) AS registros
                  FROM inventar_SpcHidr.disponible_rotopalas
                  GROUP BY [campaña_id], [campaña] ORDER BY [campaña] DESC""",
    "ambiguous": """SELECT [campaña_id] AS campana_id, COUNT(DISTINCT [campaña]) AS numeros
                    FROM inventar_SpcHidr.disponible_rotopalas
                    GROUP BY [campaña_id] HAVING COUNT(DISTINCT [campaña]) <> 1""",
    "coverage_cuadratura": """SELECT q.[campaña_id] AS campana_id, COUNT(*) AS filas
                                FROM reclamo.v_cuadratura_modulo q
                                LEFT JOIN (SELECT [campaña_id] FROM inventar_SpcHidr.disponible_rotopalas
                                           GROUP BY [campaña_id]) c ON c.[campaña_id]=q.[campaña_id]
                                WHERE c.[campaña_id] IS NULL GROUP BY q.[campaña_id]""",
    "coverage_diario": """SELECT q.[campaña_id] AS campana_id, COUNT(*) AS filas
                            FROM reclamo.calculo_diario q
                            LEFT JOIN (SELECT [campaña_id] FROM inventar_SpcHidr.disponible_rotopalas
                                       GROUP BY [campaña_id]) c ON c.[campaña_id]=q.[campaña_id]
                            WHERE c.[campaña_id] IS NULL GROUP BY q.[campaña_id]""",
    "coverage_alertas": """SELECT q.[campaña_id] AS campana_id, COUNT(*) AS filas
                             FROM reclamo.log_automatizacion q
                             LEFT JOIN (SELECT [campaña_id] FROM inventar_SpcHidr.disponible_rotopalas
                                        GROUP BY [campaña_id]) c ON c.[campaña_id]=q.[campaña_id]
                             WHERE c.[campaña_id] IS NULL GROUP BY q.[campaña_id]""",
    "cv25_extremos": """SELECT fecha,tms_cv25,tms_topografia,diferencia_pct,flag_diferencia
                          FROM reclamo.v_diferencia_cv25
                          WHERE fecha BETWEEN '2026-09-01' AND '2026-10-06'
                            AND ABS(diferencia_pct)>100 ORDER BY ABS(diferencia_pct) DESC""",
    "rendimiento_04_oct": """SELECT fecha,rotopala_id,tms_topografia,rendimiento_topografia_tms_hr,
                               rendimiento_pesometro_tms_hr,horas_operacion
                               FROM reclamo.v_rendimiento_rotopala
                               WHERE fecha='2026-10-04' ORDER BY rotopala_id""",
    "topografia_real_04_oct": """SELECT rotopala_id, COUNT(*) AS filas
                                  FROM reclamo.v_reclamo_diario
                                  WHERE fecha_operacion='2026-10-04' AND fuente_reclamo='TOPOGRAFIA'
                                  GROUP BY rotopala_id""",
    "preliminar_cero": """SELECT COUNT(*) AS filas FROM reclamo.calculo_diario
                             WHERE fecha_operacion BETWEEN '2026-09-01' AND '2026-10-06'
                               AND fuente_reclamo='PRELIMINAR_CV25'
                               AND ISNULL(tms_rotopala_dia,0)=0 AND ISNULL(m3_rotopala_dia,0)=0""",
}
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT DB_NAME() AS database_name")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError(identity)
    result = {"identity": identity, "queries": queries,
              "results": {key: [dict(row) for row in conn.execute(text(sql)).mappings()]
                          for key, sql in queries.items()}}
Path(__file__).with_name("mapping.json").write_text(json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print(json.dumps({key: len(value) for key, value in result["results"].items()}))
