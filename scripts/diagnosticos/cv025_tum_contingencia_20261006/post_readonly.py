"""Independent post-commit SELECT validation and downstream inventory."""
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
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")
queries = {
    "cv25": "SELECT fecha,tmh_cv025tot,tmh_cv025_tot,tmh_dia,tms_dia,humedad_pct,tag_utilizado,fuente,metodo,flag,observacion FROM reclamo.cv25_diario WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha",
    "graph": "SELECT fecha,tms_cv25,tms_topografia,tms_preliminar,tms_publicado,diferencia_pct,flag_diferencia FROM reclamo.v_diferencia_cv25 WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha",
    "rendimiento": "SELECT * FROM reclamo.v_rendimiento_rotopala WHERE fecha BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha,rotopala_id",
    "preliminar": "SELECT * FROM reclamo.v_preliminar_cv25 WHERE fecha_operacion BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_operacion,modulo_id,rotopala_id",
    "preliminar_acumulado": "SELECT * FROM reclamo.v_preliminar_cv25_con_acumulado WHERE fecha_operacion BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_operacion,modulo_id",
    "missing_tum": "SELECT fecha,estado_episodio,fuente_resuelta_dia,tmh_resuelto FROM inventar_SpcHidr.v_contingencia_cv025_diario_resuelto WHERE fecha='2026-10-06'",
    "hours": "SELECT fecha_turno,turno,rotopala_id,muestras_sobre_umbral,horas_por_muestra,horas_operacion,flag FROM reclamo.rotopala_horas_turno WHERE fecha_turno BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY fecha_turno,turno,rotopala_id",
    "other_equipment": "SELECT fecha_operacional,turno,equipo_codigo,valor_final_resuelto,fuente_resuelta FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno WHERE equipo_codigo IN ('CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108','SRR_CV001','SRR_CV002','SRR_CV003') AND fecha_operacional BETWEEN '2026-09-01' AND '2026-09-15' ORDER BY equipo_codigo,fecha_operacional,turno",
    "downstream": "SELECT OBJECT_SCHEMA_NAME(d.referencing_id) referencing_schema,OBJECT_NAME(d.referencing_id) referencing_name,o.type_desc,d.referenced_entity_name FROM sys.sql_expression_dependencies d JOIN sys.objects o ON o.object_id=d.referencing_id WHERE d.referenced_entity_name IN ('cv25_diario','v_cv25_diario','v_preliminar_cv25','v_preliminar_cv25_con_acumulado','v_diferencia_cv25','v_rendimiento_rotopala') ORDER BY d.referenced_entity_name,referencing_schema,referencing_name",
    "modified_objects": "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.modify_date,m.definition FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN ('v_contingencia_cv025_diario_resuelto','sp_cargar_cv25_horas','v_cv25_diario','v_diferencia_cv25')",
    "downstream_definitions": "SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE o.name IN ('sp_calcular_reclamo_diario','v_reclamo_diario','v_reclamo_para_conciliados','v_preliminar_cv25','v_preliminar_cv25_con_acumulado','v_rendimiento_rotopala','sp_mantiene_datos_conciliados_emision_test')",
    "downstream_dependencies": "SELECT OBJECT_SCHEMA_NAME(d.referencing_id) referencing_schema,OBJECT_NAME(d.referencing_id) referencing_name,d.referenced_schema_name,d.referenced_entity_name FROM sys.sql_expression_dependencies d WHERE OBJECT_NAME(d.referencing_id) IN ('sp_calcular_reclamo_diario','v_reclamo_diario','v_reclamo_para_conciliados','sp_mantiene_datos_conciliados_emision_test')",
    "cv25_constraints": "SELECT name,definition FROM sys.check_constraints WHERE parent_object_id=OBJECT_ID('reclamo.cv25_diario') ORDER BY name",
}
with get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
    if identity["database_name"].lower() != "inventar_spchidr":
        raise RuntimeError("Wrong DB")
    data = {k:[dict(r) for r in conn.execute(text(sql)).mappings()] for k,sql in queries.items()}
for row in data["modified_objects"]:
    row["sha256"] = hashlib.sha256((row.pop("definition") or "").encode()).hexdigest()
for row in data["downstream_definitions"]:
    row["sha256"] = hashlib.sha256((row.pop("definition") or "").encode()).hexdigest()
out = {"identity":identity,"queries":queries,"results":data}
(HERE / "post_commit_readonly.json").write_text(json.dumps(out, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
print("identity",identity,"counts",{k:len(v) for k,v in data.items()})
