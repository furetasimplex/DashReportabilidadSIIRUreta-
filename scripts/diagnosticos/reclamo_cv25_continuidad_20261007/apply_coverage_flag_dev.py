"""Label days with neither current signal as lacking coverage, DEV only."""

import hashlib
import sys
from pathlib import Path

from sqlalchemy import text

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine  # noqa: E402


OBJECT = "reclamo.v_cv25_diario"
BASELINE = (BASE / "alter_coverage.sql").read_text(encoding="utf-8").strip()
OLD = "        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'\n"
NEW = (
    OLD
    + "        WHEN COALESCE(cv.horas_con_dato_r1, 0) = 0\n"
    + "         AND COALESCE(cv.horas_con_dato_r2, 0) = 0\n"
    + "            THEN 'SIN_COBERTURA_CORRIENTES'\n"
)

with get_engine().connect() as conn:
    server, database = conn.execute(text("SELECT @@SERVERNAME, DB_NAME()")).one()
    if (server, database) != ("VPS-5347319-X", "inventar_SpcHidr"):
        raise RuntimeError(f"Unexpected SQL target: {server}/{database}")
    before = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if not before or before.replace("CREATE VIEW", "ALTER VIEW", 1).strip() != BASELINE:
        raise RuntimeError("Active view differs from the audited coverage version")
    if before.count(OLD) != 1:
        raise RuntimeError("Expected flag condition exactly once")
    after = before.replace(OLD, NEW, 1).replace("CREATE VIEW", "ALTER VIEW", 1)
    (BASE / "alter_coverage_flag.sql").write_text(after, encoding="utf-8")

with get_engine().begin() as conn:
    server, database = conn.execute(text("SELECT @@SERVERNAME, DB_NAME()")).one()
    if (server, database) != ("VPS-5347319-X", "inventar_SpcHidr"):
        raise RuntimeError(f"Unexpected SQL target: {server}/{database}")
    current = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if current != before:
        raise RuntimeError("View changed between audit and deployment")
    conn.exec_driver_sql(after)
    deployed = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if not deployed or deployed.replace("CREATE VIEW", "ALTER VIEW", 1).strip() != after.strip():
        raise RuntimeError("Deployed view did not match prepared SQL")

print("DEV view updated:", OBJECT)
print("before_sha256:", hashlib.sha256(before.encode()).hexdigest())
print("after_sha256:", hashlib.sha256(deployed.encode()).hexdigest())
