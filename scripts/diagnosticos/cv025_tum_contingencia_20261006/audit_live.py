"""Capture DEV CV025 lineage before changes. SQL operations are SELECT only."""
import hashlib
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
NAMES = (
    "v_contingencia_pi_serie", "v_contingencia_pi_totalizador_turno",
    "v_contingencia_pi_frontera_turno", "v_contingencia_totalizador_diagnostico_turno",
    "v_contingencia_totalizador_resuelto_turno", "sp_cargar_cv25_horas",
    "v_cv25_diario", "v_diferencia_cv25", "v_rendimiento_rotopala",
    "v_preliminar_cv25", "v_preliminar_cv25_con_acumulado",
    "vista_resumen_datos_filtrados", "cv25_diario",
)

def main():
    if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
        raise RuntimeError("DEV only")
    with get_engine().connect() as conn:
        identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
        if identity["database_name"].lower() != "inventar_spchidr":
            raise RuntimeError("Unexpected DB")
        rows = [dict(r) for r in conn.execute(text("""SELECT SCHEMA_NAME(o.schema_id) schema_name,
            o.name,o.type_desc,o.create_date,o.modify_date,m.definition
            FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE o.name IN :names""").bindparams(__import__("sqlalchemy").bindparam("names", expanding=True)), {"names": NAMES}).mappings()]
        columns = [dict(r) for r in conn.execute(text("""SELECT c.name,TYPE_NAME(c.user_type_id) data_type,
            c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity
            FROM sys.columns c WHERE c.object_id=OBJECT_ID('reclamo.cv25_diario')
            ORDER BY c.column_id""")).mappings()]
        deps = [dict(r) for r in conn.execute(text("""SELECT OBJECT_SCHEMA_NAME(d.referencing_id) referencing_schema,
            OBJECT_NAME(d.referencing_id) referencing_name,d.referenced_schema_name,
            d.referenced_entity_name,d.referenced_database_name
            FROM sys.sql_expression_dependencies d WHERE OBJECT_NAME(d.referencing_id) IN :names""").bindparams(__import__("sqlalchemy").bindparam("names", expanding=True)), {"names": NAMES}).mappings()]
        constraints = [dict(r) for r in conn.execute(text("""SELECT name,definition
            FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('reclamo.cv25_diario')""")).mappings()]
        queries = {
            "pi_daily_source": "SELECT CAST(fecha_turno AS date) fecha,cv025tot,cv025_tot,rc_001,rc_002 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE CAST(fecha_turno AS date) BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_turno",
            "resolved_turn": "SELECT * FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE equipo_codigo='RIPIOS_CV025' AND fecha_operacional BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_operacional,turno",
            "resolved_extended": "SELECT fecha_operacional,turno,estado_tecnico_pi,valor_pi_final,tum_disponible,tipo_tum,valor_turno_tum,fuente_resuelta FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE equipo_codigo='RIPIOS_CV025' AND fecha_operacional BETWEEN '2026-09-01' AND '2026-10-06' ORDER BY fecha_operacional,turno",
            "other_equipment": "SELECT fecha_operacional,turno,equipo_codigo,valor_final_resuelto,fuente_resuelta FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE equipo_codigo IN ('CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108','SRR_CV001','SRR_CV002','SRR_CV003') AND fecha_operacional BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY equipo_codigo,fecha_operacional,turno",
            "diagnosis_turn": "SELECT * FROM inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno WHERE equipo_codigo='RIPIOS_CV025' AND fecha_operacional BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_operacional,turno",
            "cv25_daily": "SELECT * FROM reclamo.cv25_diario WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha",
            "cv25_view": "SELECT * FROM reclamo.v_cv25_diario WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha",
            "difference_view": "SELECT * FROM reclamo.v_diferencia_cv25 WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha",
            "preliminar": "SELECT TOP (200) * FROM reclamo.v_preliminar_cv25",
            "preliminar_acumulado": "SELECT TOP (200) * FROM reclamo.v_preliminar_cv25_con_acumulado",
            "rendimiento": "SELECT TOP (200) * FROM reclamo.v_rendimiento_rotopala",
            "horas_turno": "SELECT * FROM reclamo.rotopala_horas_turno WHERE fecha_turno BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_turno,turno,rotopala_id",
        }
        results, errors = {}, {}
        for name, sql in queries.items():
            try:
                assert sql.startswith("SELECT")
                results[name] = [dict(r) for r in conn.execute(text(sql)).mappings()]
                print(name, len(results[name]), flush=True)
            except Exception as exc:
                errors[name] = str(exc)
                print(name, "ERROR", str(exc)[:140], flush=True)
    out = {"identity": identity, "objects": [], "columns_cv25_diario": columns, "constraints_cv25_diario": constraints,
           "dependencies": deps, "queries": queries, "results": results, "errors": errors}
    for r in rows:
        definition = r.pop("definition")
        r["sha256"] = hashlib.sha256((definition or "").encode()).hexdigest()
        r["definition"] = definition
        out["objects"].append(r)
    (HERE / "live_before.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    (HERE / "live_objects_before.sql").write_text("\n\nGO\n\n".join(f"-- {r['schema_name']}.{r['name']} SHA256 {r['sha256']}\n{r['definition']}" for r in out["objects"] if r["definition"]), encoding="utf-8")
    print("identity", identity, "objects", len(rows), "errors", errors)

if __name__ == "__main__":
    main()
