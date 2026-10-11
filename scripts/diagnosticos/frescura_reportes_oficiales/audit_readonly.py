"""Read-only DEV evidence for the current official reporting routes."""
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
QUERIES = {
    "objects": """SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.type_desc,
      o.create_date,o.modify_date FROM sys.objects o WHERE o.name IN
      ('reporte_turno_cache','reporte_turno_cache_emision_test','sp_actualizar_reporte_turno_cache_emision_test',
       'sp_reporte_turno_emision_test','fn_generador_reporte_diario_emision_test',
       'Datos_conciliados_of','Datos_conciliados_of_emision_test','sp_mantiene_datos_conciliados_emision_test',
       'reporte_torre_oficial_cab','reporte_torre_oficial_snapshot','reporte_torre_oficial_detalle',
       'representatividad_torres_resultado','sp_reporte_representatividad_torres',
       'sp_refrescar_representatividad_torres','v_conciliacion_chancado_v2')""",
    "columns": """SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,c.name column_name,t.name data_type
       FROM sys.objects o JOIN sys.columns c ON c.object_id=o.object_id
       JOIN sys.types t ON t.user_type_id=c.user_type_id
       WHERE o.name IN ('reporte_turno_cache_emision_test','Datos_conciliados_of',
         'reporte_torre_oficial_cab','reporte_torre_oficial_snapshot','reporte_torre_oficial_detalle',
         'representatividad_torres_resultado','trazabilidad_analitos_tm_emision_test')
       ORDER BY o.name,c.column_id""",
    "dependencies": """SELECT OBJECT_SCHEMA_NAME(d.referencing_id) referencing_schema,
       OBJECT_NAME(d.referencing_id) referencing_name,d.referenced_schema_name,d.referenced_entity_name
       FROM sys.sql_expression_dependencies d WHERE OBJECT_NAME(d.referencing_id) IN
       ('sp_actualizar_reporte_turno_cache_emision_test','sp_reporte_turno_emision_test',
        'fn_generador_reporte_diario_emision_test','sp_mantiene_datos_conciliados_emision_test',
        'sp_refrescar_representatividad_torres','sp_reporte_representatividad_torres',
        'v_conciliacion_chancado_v2')""",
    "definitions": """SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,m.definition
       FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id
       WHERE o.name IN ('sp_actualizar_reporte_turno_cache_emision_test','sp_reporte_turno_emision_test',
        'fn_generador_reporte_diario_emision_test','sp_mantiene_datos_conciliados_emision_test',
        'sp_refrescar_representatividad_torres','sp_reporte_representatividad_torres',
        'v_conciliacion_chancado_v2')""",
    "cache_month": """SELECT * FROM inventar_SpcHidr.reporte_turno_cache_emision_test
       WHERE Fecha BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY Fecha,Turno""",
    "dc_month": """SELECT * FROM inventar_SpcHidr.Datos_conciliados_of
       WHERE Fecha BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY Fecha""",
    "rep_result_month": """SELECT * FROM inventar_SpcHidr.representatividad_torres_resultado
       WHERE Dia BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY Dia""",
    "rep_live_month": """SELECT * FROM inventar_SpcHidr.v_representatividad_diaria_calculada
       WHERE Dia BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY Dia""",
    "rep_cab": """SELECT * FROM inventar_SpcHidr.reporte_torre_oficial_cab
       WHERE periodo_mes='2026-09' ORDER BY id_reporte""",
    "rep_snapshot": """SELECT bloque,payload FROM inventar_SpcHidr.reporte_torre_oficial_snapshot
       WHERE id_reporte=(SELECT MAX(id_reporte) FROM inventar_SpcHidr.reporte_torre_oficial_cab
           WHERE periodo_mes='2026-09' AND activo=1)""",
    "rep_detail": """SELECT * FROM inventar_SpcHidr.reporte_torre_oficial_detalle
       WHERE id_reporte=(SELECT MAX(id_reporte) FROM inventar_SpcHidr.reporte_torre_oficial_cab
           WHERE periodo_mes='2026-09' AND activo=1) ORDER BY Fecha,Turno""",
    "trace_month": """SELECT * FROM inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
       WHERE Fecha BETWEEN '2026-09-01' AND '2026-09-30' ORDER BY Fecha,Turno""",
    "decision_sep20": """SELECT * FROM inventar_SpcHidr.v_conciliacion_chancado_v2
       WHERE Fecha='2026-09-20' AND Turno='A'""",
    "generator_month": """SELECT * FROM inventar_SpcHidr.fn_generador_reporte_diario_emision_test(
       '2026-09-01','2026-10-01') ORDER BY Fecha""",
}

def main():
    if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
        raise RuntimeError("DEV database expected")
    with get_engine().connect() as conn:
        identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name, DB_NAME() database_name, SYSDATETIME() observed_at")).mappings().one())
        if identity["database_name"].lower() != "inventar_spchidr":
            raise RuntimeError("Unexpected database")
        out = {"identity": identity, "queries": QUERIES, "results": {}, "errors": {}}
        for key, sql in QUERIES.items():
            try:
                assert sql.lstrip().upper().startswith("SELECT")
                out["results"][key] = [dict(r) for r in conn.execute(text(sql)).mappings()]
                print(key, len(out["results"][key]), flush=True)
            except Exception as exc:
                out["errors"][key] = str(exc)
                print(key, "ERROR", str(exc)[:160], flush=True)
    (HERE / "evidencia_dev.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    print("saved", HERE / "evidencia_dev.json")

if __name__ == "__main__":
    main()
