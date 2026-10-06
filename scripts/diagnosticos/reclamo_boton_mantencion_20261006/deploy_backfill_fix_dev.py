"""Deploy the reviewed temporal fix to the guarded DEV SQL Server only."""
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

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixes"
EXPECTED_BEFORE = {
    "sp_auto_congelar_modulos_nuevos": "c11704af2ae209447d606169f28b72b0aee5a4cf2a577ad93d5b9c45fb37ef1f",
    "sp_auto_mantener_secuencia": "df60d0e06baf77816ac17da786af23f2aa9050f8f2e02b5add336b6013ea3341",
    "sp_auto_cerrar_y_avanzar_secuencia": "4bc0a309313db5f1fc7611526633269dbb1e529d9f052bb9e3827e72a11acd19",
}
NAMES = list(EXPECTED_BEFORE)
engine = get_engine()

with engine.connect() as conn:
    identity = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if identity["database_name"] != "inventar_SpcHidr" or identity["server_name"] != "VPS-5347319-X":
        raise RuntimeError(f"Refusing deployment outside the reviewed DEV target: {identity}")
    current = {}
    for name in NAMES:
        definition = conn.execute(text(
            "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"
        ), {"obj": f"reclamo.{name}"}).scalar_one()
        current[name] = hashlib.sha256(definition.encode("utf-8")).hexdigest()
    if current != EXPECTED_BEFORE:
        raise RuntimeError(f"Live SP definitions changed since audit; no DDL applied: {current}")
    conn.commit()

local_hashes = {}
with engine.begin() as conn:
    for name in NAMES:
        path = FIX / f"alter_reclamo.{name}.sql"
        sql = path.read_text(encoding="utf-8")
        local_hashes[name] = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        conn.exec_driver_sql(sql)

after = {}
with engine.connect() as conn:
    identity_after = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    for name in NAMES:
        definition = conn.execute(text(
            "SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:obj)"
        ), {"obj": f"reclamo.{name}"}).scalar_one()
        after[name] = hashlib.sha256(definition.encode("utf-8")).hexdigest()

result = {
    "applied_utc": datetime.now(timezone.utc).isoformat(),
    "identity": identity_after,
    "objects_modified": [f"reclamo.{name}" for name in NAMES],
    "hash_before": current,
    "candidate_file_hashes": local_hashes,
    "hash_after_live": after,
    "expected_hashes_changed": all(after[name] != current[name] for name in NAMES),
    "scope": "DEV only; no table data updated by deployment",
}
if not result["expected_hashes_changed"]:
    raise RuntimeError("One or more live definition hashes did not change")
(HERE / "deploy_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
