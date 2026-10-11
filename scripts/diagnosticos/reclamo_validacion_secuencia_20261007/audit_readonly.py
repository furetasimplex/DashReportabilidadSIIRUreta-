"""Capture live DEV sequence semantics and old/new blocker detail."""
import csv
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine

BASE = Path(__file__).resolve().parent
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")

with get_engine().connect() as c:
    db = c.scalar(text("SELECT DB_NAME()"))
    if db.lower() != "inventar_spchidr":
        raise RuntimeError("Wrong database")
    definitions = {}
    for name in ("sp_auto_mantener_secuencia", "sp_definir_secuencia"):
        definition = c.scalar(text(f"SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.{name}'))"))
        if not definition:
            raise RuntimeError(f"Missing live definition: {name}")
        definitions[name] = definition
    maintain = definitions["sp_auto_mantener_secuencia"]
    define = definitions["sp_definir_secuencia"]
    if "@Siguientes  int = 5" not in maintain and "@Siguientes int = 5" not in maintain:
        raise RuntimeError("Live maintenance default differs from 5")
    if "@Siguientes int = 5" not in define:
        raise RuntimeError("Live sequence default differs from 5")
    if "control_reclamo_diario" not in maintain or "control_reclamo_diario" not in define:
        raise RuntimeError("Unexpected rotopala evidence source")
    old = """SELECT 2, 'Modulos congelados sin secuencia', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.modulo_congelado mc
                    WHERE mc.estado = 'CONGELADO'
                      AND NOT EXISTS (SELECT 1 FROM reclamo.secuencia_rotopala s
                                      WHERE s.[campaña_id] = mc.[campaña_id]
                                        AND s.modulo_id = mc.modulo_id))"""
    (BASE / "definicion_before.sql").write_text(
        "-- Current Python semaforo control 2\n" + old + "\n\nGO\n\n"
        + "-- Live maintenance SP\n" + maintain + "\n\nGO\n\n"
        + "-- Live define-sequence SP\n" + define,
        encoding="utf-8",
    )
    rows = [dict(row) for row in c.execute(text(
        (BASE / "auditoria_elegibilidad.sql").read_text(encoding="utf-8")
    )).mappings()]
    seq_count = c.scalar(text("SELECT COUNT(*) FROM reclamo.secuencia_rotopala"))
    frozen_count = c.scalar(text("SELECT COUNT(*) FROM reclamo.modulo_congelado WHERE estado='CONGELADO'"))
    calc = c.scalar(text("SELECT COUNT(*) FROM reclamo.calculo_diario"))
    totals = dict(c.execute(text("""
        SELECT SUM(tms_rotopala_dia) AS tms_rotopala,
               SUM(tms_camiones_dia) AS tms_camiones
        FROM reclamo.calculo_diario
    """)).mappings().one())

with (BASE / "before_after.csv").open("w", newline="", encoding="utf-8-sig") as stream:
    fields = ["campaña_id", "pad_id", "modulo_id", "modulo_numero", "modulo_max_topo",
              "evidencia_rotopala", "cola_fisica", "bloqueante_antes", "bloqueante_despues"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({**{key: row.get(key) for key in fields},
                         "bloqueante_antes": 1,
                         "bloqueante_despues": row["bloqueante_aplicable"]})

snapshot = {"database": db, "secuencia_rows": seq_count, "frozen_rows": frozen_count,
            "calculo_diario_rows": calc, "blockers_before": len(rows),
            "blockers_after_eligible": sum(row["bloqueante_aplicable"] for row in rows),
            "calculo_tms_rotopala": str(totals["tms_rotopala"]),
            "calculo_tms_camiones": str(totals["tms_camiones"])}
(BASE / "snapshot_before.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
print(snapshot)
for row in rows:
    print({key: row[key] for key in ("campaña_id", "pad_id", "modulo_id", "modulo_numero",
                                    "modulo_max_topo", "evidencia_rotopala", "cola_fisica",
                                    "bloqueante_aplicable")})
