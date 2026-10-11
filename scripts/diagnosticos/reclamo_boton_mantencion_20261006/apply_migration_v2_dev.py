"""Apply the reviewed v2 date-only migration in an owned DB transaction."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
HERE = Path(__file__).resolve().parent
sql = (HERE / "fixes" / "migrate_campaign10_sequence_dates_v2.sql").read_text(encoding="utf-8")
expected = json.loads((HERE / "timeline_76_80_expected.json").read_text(encoding="utf-8"))
engine = get_engine()
with engine.begin() as conn:
    ident = dict(conn.execute(text("SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name")).mappings().one())
    if ident["server_name"] != "VPS-5347319-X" or ident["database_name"] != "inventar_SpcHidr":
        raise RuntimeError(f"Unexpected DB: {ident}")
    rows = [dict(r) for r in conn.exec_driver_sql(sql).mappings()]
    if len(rows) != 4:
        raise RuntimeError(f"Expected four date corrections, got {len(rows)}")
    by_mod = {r["modulo_id"]: r for r in rows}
    for proposal in expected["rows"]:
        mod = proposal["modulo_id"]
        if mod == 80:
            continue
        row = by_mod[mod]
        if str(row["new_apertura"]) != proposal["apertura_calculada"] or (
            str(row["new_cierre"]) if row["new_cierre"] is not None else None
        ) != proposal["cierre_calculado"]:
            raise RuntimeError(f"Date output differs from simulation for module {mod}: {row}")
result = {"applied_utc": datetime.now(timezone.utc).isoformat(), "identity": ident,
          "changes": rows, "rollback": "rollback_v2.sql"}
(HERE / "migration_v2_after.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
print(json.dumps(result, indent=2, default=str))
