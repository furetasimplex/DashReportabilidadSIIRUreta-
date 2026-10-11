"""Compare the visual semaforo severity before/after with read-only queries."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db, panel

captured = {}
original_read = db._read


def capture(sql, params=None):
    captured["sql"] = sql
    captured["params"] = params
    return original_read(sql, params)


try:
    db._read = capture
    after = db.semaforo("2026-10-01", "2026-10-06")
finally:
    db._read = original_read

new = "SELECT 4, 'Cuadratura sobre 100 sin traspaso', 'ADVERTENCIA',"
old = "SELECT 4, 'Cuadratura sobre 100 sin traspaso', 'BLOQUEANTE',"
assert captured["sql"].count(new) == 1
before = original_read(captured["sql"].replace(new, old, 1), captured["params"])

before = before.sort_values("orden").reset_index(drop=True)
after = after.sort_values("orden").reset_index(drop=True)
assert len(before) == len(after) == 14
assert before.loc[before["orden"] != 4].equals(after.loc[after["orden"] != 4])
old_row = before.loc[before["orden"] == 4].iloc[0]
new_row = after.loc[after["orden"] == 4].iloc[0]
assert int(old_row["hallazgos"]) == int(new_row["hallazgos"]) == 23
assert old_row["control"] == new_row["control"]
assert old_row["severidad"] == "BLOQUEANTE" and old_row["resultado"] == "NO PUBLICAR"
assert new_row["severidad"] == "ADVERTENCIA" and new_row["resultado"] == "REVISAR"

original_semaforo = db.semaforo
try:
    db.semaforo = lambda _desde, _hasta: after
    ui = panel.cb_semaforo(1, None, "2026-10-01", "2026-10-06")
finally:
    db.semaforo = original_semaforo
blockers = str(ui.children[0].to_plotly_json())
warnings = str(ui.children[1].to_plotly_json())
assert "Módulos sobre 100 % sin traspaso" not in blockers
assert "Módulos sobre 100 % sin traspaso" in warnings
assert "REVISAR" in warnings
print("PASS: 23 modules, ADVERTENCIA/REVISAR, all 13 other controls identical")
