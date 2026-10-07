"""Verify the corrected DEV semaforo and operational data invariants."""
import json
import os
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from db_connection import get_engine
from reclamo import db

BASE = Path(__file__).resolve().parent
if os.getenv("SQLSERVER_DB", "").lower() != "inventar_spchidr":
    raise RuntimeError("DEV only")
before = json.loads((BASE / "snapshot_before.json").read_text(encoding="utf-8"))

semaforo = db.semaforo("2026-10-01", "2026-10-06")
control = semaforo.loc[semaforo["orden"] == 2].iloc[0]
assert control["control"] == "Modulos congelados sin secuencia"
assert control["severidad"] == "BLOQUEANTE"
assert int(control["hallazgos"]) == before["blockers_after_eligible"] == 0
assert control["resultado"] == "OK"

with get_engine().connect() as c:
    assert c.scalar(text("SELECT DB_NAME()")) == before["database"]
    rows = [dict(row) for row in c.execute(text(
        (BASE / "auditoria_elegibilidad.sql").read_text(encoding="utf-8")
    )).mappings()]
    old_count = len(rows)
    new_count = sum(row["bloqueante_aplicable"] for row in rows)
    assert old_count == before["blockers_before"] == 5
    assert new_count == int(control["hallazgos"])
    assert {row["modulo_id"] for row in rows} == {86, 87, 88, 89, 90}
    assert all(row["pad_id"] == 2 and row["campaña_id"] == 10
               and row["modulo_max_topo"] == 16
               and row["evidencia_rotopala"] == 0
               and row["cola_fisica"] == 0 for row in rows)
    seq_count = c.scalar(text("SELECT COUNT(*) FROM reclamo.secuencia_rotopala"))
    frozen_count = c.scalar(text("SELECT COUNT(*) FROM reclamo.modulo_congelado WHERE estado='CONGELADO'"))
    calc = c.scalar(text("SELECT COUNT(*) FROM reclamo.calculo_diario"))
    totals = dict(c.execute(text("""
        SELECT SUM(tms_rotopala_dia) AS tms_rotopala,
               SUM(tms_camiones_dia) AS tms_camiones
        FROM reclamo.calculo_diario
    """)).mappings().one())
    assert seq_count == before["secuencia_rows"]
    assert frozen_count == before["frozen_rows"]
    assert calc == before["calculo_diario_rows"]
    assert str(totals["tms_rotopala"]) == before["calculo_tms_rotopala"]
    assert str(totals["tms_camiones"]) == before["calculo_tms_camiones"]
    cases = [dict(row) for row in c.execute(text("""
        WITH cases(modulo_numero, max_topo, evidencia_rotopala) AS (
            SELECT * FROM (VALUES (16,16,1), (17,16,0), (21,16,0),
                                  (22,16,0)) v(modulo_numero,max_topo,evidencia_rotopala)
        )
        SELECT modulo_numero,
               CASE WHEN evidencia_rotopala = 1 OR
                         (modulo_numero > max_topo AND modulo_numero <= max_topo + 5)
                    THEN 1 ELSE 0 END AS elegible
        FROM cases ORDER BY modulo_numero
    """)).mappings()]
    assert [(r["modulo_numero"], r["elegible"]) for r in cases] == [
        (16, 1), (17, 1), (21, 1), (22, 0)
    ]

print("PASS control2 before", old_count, "after", new_count,
      "secuencia", seq_count, "frozen", frozen_count, "calculo", calc,
      "synthetic evidence/queue still block")
