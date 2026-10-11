"""Run the normal Reclamo recalculation for the requested closed date range in DEV."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
from reclamo import db

HERE = Path(__file__).resolve().parent
engine = get_engine()
with engine.connect() as conn:
    identity = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if identity["server_name"] != "VPS-5347319-X" or identity["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Refusing recalculation outside guarded DEV: {identity}")

message = db.recalcular("2026-09-26", "2026-10-04")
result = {
    "executed_utc": datetime.now(timezone.utc).isoformat(),
    "identity": identity,
    "date_range": ["2026-09-26", "2026-10-04"],
    "message": message,
}
(HERE / "reprocess_result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
print(json.dumps(result, indent=2))
