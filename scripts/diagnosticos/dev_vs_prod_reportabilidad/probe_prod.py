"""Read-only identity and candidate official-object probe for PROD."""
import os
import sys
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["SQLSERVER_DB"] = "inventar_SpcHidr_PROD"
from db_connection import get_engine

try:
    with get_engine().connect() as conn:
        row = dict(conn.execute(text("SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at")).mappings().one())
        if row["database_name"].lower() != "inventar_spchidr_prod":
            raise RuntimeError("Unexpected database")
        print(row)
        objects = conn.execute(text("""SELECT SCHEMA_NAME(o.schema_id) schema_name,o.name,o.type_desc,o.modify_date
        FROM sys.objects o WHERE o.name IN
        ('reporte_turno_cache_emision_test','sp_actualizar_reporte_turno_cache_emision_test',
        'sp_reporte_turno_emision_test','fn_generador_reporte_diario_emision_test',
        'Datos_conciliados_of','sp_mantiene_datos_conciliados_emision_test',
        'reporte_torre_oficial_cab','reporte_torre_oficial_snapshot',
        'sp_refrescar_representatividad_torres','v_conciliacion_chancado_v2')
        ORDER BY o.name""")).mappings().all()
        for x in objects:
            print(dict(x))
except Exception as exc:
    print("PROD_CONNECTION_ERROR", type(exc).__name__, str(exc).split("(Background on this error")[0][-650:])

import db_connection
db_connection._engine = None
os.environ["SQLSERVER_DB"] = "inventar_SpcHidr"
with get_engine().connect() as conn:
    print("DEV_IDENTITY",dict(conn.execute(text("SELECT @@SERVERNAME server_name, DB_NAME() database_name")).mappings().one()))
    print("DATABASES",[dict(r) for r in conn.execute(text("""SELECT name,state_desc,HAS_DBACCESS(name) has_access
        FROM sys.databases WHERE name IN ('inventar_SpcHidr','inventar_SpcHidr_PROD','DEV_SIIR','PROD_SIIR')""")).mappings()])
