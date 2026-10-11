"""Execute the proposed view body as a bounded SELECT in DEV, before DDL."""
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")
sql = (HERE / "cv025_view_select.sql").read_text(encoding="utf-8").strip()
if not sql.upper().startswith("WITH PI_RAW AS"):
    raise RuntimeError("Unexpected query")
with get_engine().connect() as conn:
    identity = conn.execute(text("SELECT DB_NAME()")).scalar()
    if identity.lower() != "inventar_spchidr":
        raise RuntimeError("Unexpected DB")
    rows = [dict(r) for r in conn.execute(text(sql + "\nWHERE s.fecha BETWEEN :start AND :end ORDER BY s.fecha"),
                                         {"start": "2026-09-01", "end": "2026-09-15"}).mappings()]
    missing_tum = [dict(r) for r in conn.execute(text(sql + "\nWHERE s.fecha=:day ORDER BY s.fecha"),
                                                {"day": "2026-10-06"}).mappings()]
(HERE / "view_select_result.json").write_text(json.dumps(rows, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
(HERE / "missing_tum_case.json").write_text(json.dumps(missing_tum, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
for r in rows:
    print(r["fecha"],r["pi_diario_original"],r["tum_diario"],r["episodio_id"],r["estado_episodio"],r["tmh_resuelto"])
print("rows",len(rows))
print("missing_tum",[(x["fecha"],x["estado_episodio"],x["tmh_resuelto"]) for x in missing_tum])
