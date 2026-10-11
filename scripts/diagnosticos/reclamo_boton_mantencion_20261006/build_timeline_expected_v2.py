"""Calculate the reviewed timeline from the immutable read-only DEV snapshot."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
before = json.loads((HERE / "timeline_76_80_before.json").read_text(encoding="utf-8"))
rows = sorted(before["rows"], key=lambda row: row["orden_secuencia"])
expected = []
for i, row in enumerate(rows):
    nxt = rows[i + 1] if i + 1 < len(rows) else None
    first = row["primera_topografia"]
    next_first = nxt["primera_topografia"] if nxt else None
    expected.append({**row,
        "apertura_calculada": first if first else row["apertura_actual"],
        "cierre_calculado": next_first if next_first and row["estado"] == "CERRADO" else row["cierre_actual"],
        "fuente_evidencia": "reclamo.topografia_avance VIGENTE" if first else "sin evidencia; conservar NULL",
        "fuente_transicion": "primera topografia VIGENTE del sucesor" if next_first and row["estado"] == "CERRADO" else "sin transicion demostrable",
    })
assert [r["modulo_id"] for r in expected] == [76,77,78,79,80]
assert expected[-1]["apertura_calculada"] is None and expected[-1]["cierre_calculado"] is None
result = {"source_snapshot": "timeline_76_80_before.json", "identity": before["identity"],
          "rows": expected, "read_only": True}
(HERE / "timeline_76_80_expected.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
