"""Execute the guarded SQL migration script against DEV and capture OUTPUT."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
sql = (HERE / "fixes" / "migrate_campaign10_sequence_dates.sql").read_text(encoding="utf-8")
engine = get_engine()
with engine.connect() as conn:
    identity = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if identity["server_name"] != "VPS-5347319-X" or identity["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Refusing migration outside guarded DEV: {identity}")
    conn.commit()
    rows = conn.exec_driver_sql(sql).mappings().all()
    result = {
        "applied_utc": datetime.now(timezone.utc).isoformat(),
        "identity": identity,
        "output_changes": [dict(row) for row in rows],
        "scope": "campaign 10 / PAD2 / modules 76-79; dates only",
        "rollback_script": "fixes/rollback_campaign10_sequence_dates.sql",
    }
    if len(rows) != 4:
        raise RuntimeError(f"Expected four OUTPUT rows, got {len(rows)}")
(HERE / "migration_result.json").write_text(
    json.dumps(result, indent=2, ensure_ascii=False,
               default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)),
    encoding="utf-8",
)
print(json.dumps(result, indent=2, ensure_ascii=False,
                 default=lambda value: value.isoformat() if hasattr(value, "isoformat") else str(value)))
