"""Compile candidate ALTER batches in DEV and roll the metadata transaction back."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

HERE = Path(__file__).resolve().parent
FIX = HERE / "fixes"
NAMES = [
    "sp_auto_congelar_modulos_nuevos",
    "sp_auto_mantener_secuencia",
    "sp_auto_cerrar_y_avanzar_secuencia",
]
engine = get_engine()
with engine.connect() as conn:
    ident = dict(conn.execute(text(
        "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, SUSER_SNAME() AS login_name"
    )).mappings().one())
    if ident["database_name"] != "inventar_SpcHidr" or ident["server_name"] != "VPS-5347319-X":
        raise RuntimeError(f"Refusing DDL compile against unexpected target: {ident}")
    before = {}
    for name in NAMES:
        definition = conn.execute(text("""
            SELECT sm.definition FROM sys.sql_modules sm
            WHERE sm.object_id=OBJECT_ID(:obj)
        """), {"obj": f"reclamo.{name}"}).scalar_one()
        before[name] = hashlib.sha256(definition.encode("utf-8")).hexdigest()

    conn.commit()
    tx = conn.begin()
    try:
        for name in NAMES:
            sql = (FIX / f"alter_reclamo.{name}.sql").read_text(encoding="utf-8")
            conn.exec_driver_sql(sql)
        tx.rollback()
    except Exception:
        if tx.is_active:
            tx.rollback()
        raise

    after = {}
    for name in NAMES:
        definition = conn.execute(text("""
            SELECT sm.definition FROM sys.sql_modules sm
            WHERE sm.object_id=OBJECT_ID(:obj)
        """), {"obj": f"reclamo.{name}"}).scalar_one()
        after[name] = hashlib.sha256(definition.encode("utf-8")).hexdigest()
    result = {
        "identity": ident,
        "compiled_alter_batches": NAMES,
        "transaction": "ROLLBACK",
        "definitions_unchanged_after_rollback": before == after,
        "hash_before": before,
        "hash_after": after,
        "persistent_change": False,
    }
    if before != after:
        raise RuntimeError("SQL definitions changed despite rollback")
    (HERE / "ddl_compile_rollback.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
