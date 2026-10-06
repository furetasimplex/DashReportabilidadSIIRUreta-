"""Deploy the single reviewed preparation-mode SP change to DEV."""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
HERE = Path(__file__).resolve().parent
NAME = "sp_auto_congelar_modulos_nuevos"
EXPECTED = "d43cf1bb4dd6ff52d8a9b774df297370bb0aac97891fe9217c50e66f34bfd98e"
sql = (HERE / "fixes" / "alter_reclamo.sp_auto_congelar_modulos_nuevos_v2.sql").read_text(encoding="utf-8")
engine = get_engine()
with engine.begin() as conn:
    ident = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if ident["server_name"] != "VPS-5347319-X" or ident["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Unexpected DB: {ident}")
    definition = conn.execute(text("SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"), {"obj": f"reclamo.{NAME}"}).scalar_one()
    before = hashlib.sha256(definition.encode("utf-8")).hexdigest()
    if before != EXPECTED:
        raise RuntimeError(f"Definition drift: {before}")
    conn.exec_driver_sql(sql)
with engine.connect() as conn:
    after_definition = conn.execute(text("SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"), {"obj": f"reclamo.{NAME}"}).scalar_one()
    after = hashlib.sha256(after_definition.encode("utf-8")).hexdigest()
if after == before or "@SoloPreparar bit = 0" not in after_definition:
    raise RuntimeError("V2 DDL did not persist")
result = {"deployed_utc": datetime.now(timezone.utc).isoformat(), "identity": ident,
          "object": f"reclamo.{NAME}", "hash_before": before, "hash_after": after,
          "candidate_hash": hashlib.sha256(sql.encode("utf-8")).hexdigest()}
(HERE / "deploy_flow_v2.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
