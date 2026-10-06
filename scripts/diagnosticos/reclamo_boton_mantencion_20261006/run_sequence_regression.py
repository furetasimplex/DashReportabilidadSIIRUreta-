"""Run the self-contained table-variable transition regression in DEV."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
sql = (HERE / "tests" / "backfill_date_regression.sql").read_text(encoding="utf-8")
with get_engine().connect() as conn:
    identity = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if identity["server_name"] != "VPS-5347319-X" or identity["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Unexpected target: {identity}")
    conn.commit()
    rows = conn.exec_driver_sql(sql).mappings().all()
    if len(rows) != 1 or rows[0]["resultado"] != "PASS":
        raise RuntimeError(f"Regression did not pass: {rows}")
    result = {"identity": identity, "result": dict(rows[0]), "persistent_writes": False}
(HERE / "regression_result.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print(json.dumps(result, indent=2, default=str))
