"""Preserve missing-current NULL when CV025 itself is zero, DEV only."""

import hashlib
import sys
from pathlib import Path

from sqlalchemy import text

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT))

from db_connection import get_engine  # noqa: E402


OBJECT = "reclamo.v_cv25_diario"
baseline_file = ROOT / "scripts/diagnosticos/reclamo_cv25_dmas1_20261007/alter_v_cv25_diario.sql"
baseline = baseline_file.read_text(encoding="utf-8")
baseline = baseline[baseline.index("ALTER VIEW"):].strip()

with get_engine().connect() as conn:
    server, database = conn.execute(text("SELECT @@SERVERNAME, DB_NAME()")).one()
    if (server, database) != ("VPS-5347319-X", "inventar_SpcHidr"):
        raise RuntimeError(f"Unexpected SQL target: {server}/{database}")
    before = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if not before or before.replace("CREATE VIEW", "ALTER VIEW", 1).strip() != baseline:
        raise RuntimeError("Active coverage view differs from audited baseline")

    after = before
    for roto in (1, 2):
        missing = (
            f"        WHEN COALESCE(hr.horas_r{roto}, 0) = 0\n"
            f"         AND COALESCE(cv.horas_con_dato_r{roto}, 0) = 0\n"
            "            THEN NULL\n\n"
        )
        start = "        WHEN cv.tms_dia IS NULL THEN NULL\n"
        zero = "        WHEN COALESCE(cv.tms_dia, 0) = 0\n            THEN 0\n\n"
        coverage_zero = (
            f"        WHEN COALESCE(hr.horas_r{roto}, 0) = 0\n"
            f"         AND COALESCE(cv.horas_con_dato_r{roto}, 0) > 0\n"
            "            THEN 0\n\n"
        )
        old = start + zero + coverage_zero + missing
        new = start + missing + zero + coverage_zero
        if after.count(old) != 1:
            raise RuntimeError(f"Expected coverage conditions exactly once for R{roto}")
        after = after.replace(old, new, 1)

    after = after.replace("CREATE VIEW", "ALTER VIEW", 1)
    (BASE / "before_coverage.sql").write_text(
        before.replace("CREATE VIEW", "ALTER VIEW", 1), encoding="utf-8"
    )
    (BASE / "alter_coverage.sql").write_text(after, encoding="utf-8")

with get_engine().begin() as conn:
    server, database = conn.execute(text("SELECT @@SERVERNAME, DB_NAME()")).one()
    if (server, database) != ("VPS-5347319-X", "inventar_SpcHidr"):
        raise RuntimeError(f"Unexpected SQL target: {server}/{database}")
    current = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if current != before:
        raise RuntimeError("Coverage view changed between audit and deployment")
    conn.exec_driver_sql(after)
    deployed = conn.scalar(
        text("SELECT OBJECT_DEFINITION(OBJECT_ID(:name))"), {"name": OBJECT}
    )
    if not deployed or deployed.replace("CREATE VIEW", "ALTER VIEW", 1).strip() != after.strip():
        raise RuntimeError("Deployed coverage view did not match prepared SQL")

print("DEV view updated:", OBJECT)
print("before_sha256:", hashlib.sha256(before.encode()).hexdigest())
print("after_sha256:", hashlib.sha256(deployed.encode()).hexdigest())
