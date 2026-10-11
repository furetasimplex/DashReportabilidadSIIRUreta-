"""Extract SQL catalog for the report pipeline with SELECT only.

DEV uses this checkout's .env. PROD requires explicit
SIIR_AUDIT_PROD_HOST/DB/USER/PASSWORD environment variables. Never logs secrets.
"""
import hashlib
import json
import os
import sys
from collections import deque
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from env_loader import load_app_env

load_app_env()
from sqlalchemy import create_engine
from urllib.parse import quote_plus

HERE = Path(__file__).resolve().parent
ROOT_NAMES = {
    "sp_actualizar_reporte_turno_cache_emision_test",
    "sp_reporte_turno_emision_test",
    "sp_generador_reporte_diario_emision_test",
    "fn_generador_reporte_diario_emision_test",
    "sp_mantiene_datos_conciliados_emision_test",
    "sp_refrescar_representatividad_torres",
    "sp_reporte_representatividad_torres",
    "sp_calcular_resumen_intervalo_totTM",
    "sp_sincronizar_bd_ton",
    "sp_gestion_representatividad_fy",
    "reporte_turno_cache_emision_test",
    "Datos_conciliados_of",
    "representatividad_torres_resultado",
    "reporte_torre_oficial_cab",
    "reporte_torre_oficial_snapshot",
    "reporte_torre_oficial_detalle",
    "v_ley_cu_srr_resuelta_emision_test",
    "fn_reconstitucion_srr_turno_emision_test",
    "fn_reconstitucion_srr_emision_test",
    "v_conciliacion_chancado_v2",
    "v_datos_apilado_tmh_v2",
    "v_reporte_turno_campania_modulo_test",
    "v_reporte_turno_fuentes_info_test",
    "trazabilidad_analitos_tm_emision_test",
}

def engine_for(target):
    if target == "DEV":
        host = os.environ["SQLSERVER_HOST"]
        db = "inventar_SpcHidr"
        user = os.environ["SQLSERVER_USER"]
        password = os.environ["SQLSERVER_PASSWORD"]
    elif target == "PROD":
        host = os.environ["SIIR_AUDIT_PROD_HOST"]
        db = os.environ.get("SIIR_AUDIT_PROD_DB", "inventar_SpcHidr_PROD")
        user = os.environ["SIIR_AUDIT_PROD_USER"]
        password = os.environ["SIIR_AUDIT_PROD_PASSWORD"]
    else:
        raise ValueError(target)
    driver = os.environ.get("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server").replace(" ", "+")
    url = f"mssql+pyodbc://{user}:{quote_plus(password)}@{host}/{db}?driver={driver}&Encrypt=no&TrustServerCertificate=yes"
    return create_engine(url, pool_pre_ping=True), db

def main(target):
    engine, expected_db = engine_for(target)
    with engine.connect() as conn:
        identity = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
        if identity["database_name"].lower() != expected_db.lower():
            raise RuntimeError("Unexpected DB identity")
        objects = [dict(r) for r in conn.execute(text("""SELECT o.object_id,SCHEMA_NAME(o.schema_id) schema_name,
            o.name,o.type_desc,o.create_date,o.modify_date,m.definition
            FROM sys.objects o LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
            WHERE o.is_ms_shipped=0""")).mappings()]
        deps = [dict(r) for r in conn.execute(text("""SELECT referencing_id,referenced_id,
            referenced_server_name,referenced_database_name,referenced_schema_name,referenced_entity_name
            FROM sys.sql_expression_dependencies""")).mappings()]
        cols = [dict(r) for r in conn.execute(text("""SELECT c.object_id,c.column_id,c.name,
            TYPE_NAME(c.user_type_id) data_type,c.max_length,c.precision,c.scale,c.is_nullable,c.is_identity
            FROM sys.columns c""")).mappings()]
        indexes = [dict(r) for r in conn.execute(text("""SELECT i.object_id,i.index_id,i.name,i.type_desc,
            i.is_unique,i.is_primary_key,ic.key_ordinal,c.name column_name
            FROM sys.indexes i LEFT JOIN sys.index_columns ic ON ic.object_id=i.object_id AND ic.index_id=i.index_id
            LEFT JOIN sys.columns c ON c.object_id=ic.object_id AND c.column_id=ic.column_id
            WHERE i.is_hypothetical=0""")).mappings()]
    by_id = {x["object_id"]: x for x in objects}
    selected = {x["object_id"] for x in objects if x["name"] in ROOT_NAMES and x["schema_name"] in ("inventar_SpcHidr", "reclamo", "hidro")}
    pending = deque(selected)
    while pending:
        parent = pending.popleft()
        for dep in deps:
            child = dep["referenced_id"]
            if dep["referencing_id"] == parent and child in by_id and child not in selected:
                selected.add(child)
                pending.append(child)
    rows = []
    for oid in selected:
        obj = by_id[oid]
        definition = obj["definition"]
        columns = [x for x in cols if x["object_id"] == oid]
        table_indexes = [x for x in indexes if x["object_id"] == oid]
        stable_columns = [{k: v for k, v in x.items() if k != "object_id"} for x in columns]
        stable_indexes = [{k: v for k, v in x.items() if k != "object_id"} for x in table_indexes]
        signature = definition if definition is not None else json.dumps({"columns": stable_columns, "indexes": stable_indexes}, sort_keys=True, default=str)
        rows.append({"schema": obj["schema_name"], "name": obj["name"], "type": obj["type_desc"],
                     "create_date": obj["create_date"], "modify_date": obj["modify_date"],
                     "sha256": hashlib.sha256(signature.encode("utf-8")).hexdigest(),
                     "definition": definition, "columns": stable_columns, "indexes": stable_indexes,
                     "dependencies": [x for x in deps if x["referencing_id"] == oid]})
    output = {"identity": identity, "roots_present": sorted(x["name"] for x in objects if x["name"] in ROOT_NAMES),
              "roots_missing": sorted(ROOT_NAMES - {x["name"] for x in objects}),
              "objects": sorted(rows, key=lambda x: (x["schema"], x["name"]))}
    file = HERE / f"catalog_{target.lower()}.json"
    file.write_text(json.dumps(output, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    print({"target": target, "identity": identity, "roots_present": len(output["roots_present"]),
           "roots_missing": output["roots_missing"], "closure_objects": len(rows), "file": str(file)})

if __name__ == "__main__":
    main(sys.argv[1].upper())
