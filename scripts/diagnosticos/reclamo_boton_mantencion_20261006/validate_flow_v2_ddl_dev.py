"""Compile v2 ALTER in a DEV transaction, roll it back, verify exact hash."""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
HERE = Path(__file__).resolve().parent
NAME = "sp_auto_congelar_modulos_nuevos"
EXPECTED = "d43cf1bb4dd6ff52d8a9b774df297370bb0aac97891fe9217c50e66f34bfd98e"
sql = (HERE / "fixes" / "alter_reclamo.sp_auto_congelar_modulos_nuevos_v2.sql").read_text(encoding="utf-8")
with get_engine().connect() as conn:
    ident = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if ident["server_name"] != "VPS-5347319-X" or ident["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Unexpected DB: {ident}")
    before = conn.execute(text("SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"), {"obj": f"reclamo.{NAME}"}).scalar_one()
    before_hash = hashlib.sha256(before.encode("utf-8")).hexdigest()
    if before_hash != EXPECTED:
        raise RuntimeError(f"Definition drift: {before_hash}")
    conn.commit()
    tx = conn.begin()
    try:
        conn.exec_driver_sql(sql)
    finally:
        tx.rollback()
    after = conn.execute(text("SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"), {"obj": f"reclamo.{NAME}"}).scalar_one()
    after_hash = hashlib.sha256(after.encode("utf-8")).hexdigest()
    if after_hash != before_hash:
        raise RuntimeError("DDL was not rolled back")
result = {"identity": ident, "object": f"reclamo.{NAME}", "compiled": True,
          "rollback": True, "hash_before": before_hash, "hash_after": after_hash}
(HERE / "ddl_v2_compile_rollback.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
