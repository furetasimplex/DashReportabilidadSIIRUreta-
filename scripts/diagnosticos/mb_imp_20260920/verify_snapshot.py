"""Assertions over the read-only DEV snapshot; does not touch SQL Server."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
data = json.loads((HERE / "snapshot.json").read_text(encoding="utf-8"))["results"]

def row(source, date, shift):
    return next((r for r in data[source] if r["Fecha"] == date and r["Turno"] == shift), None)

checks = {
    "mb_absent_20_a": row("mov_cam", "2026-09-20", "TA") is None
       and row("mov_cam_powerbi", "2026-09-20", "TA") is None
       and row("official", "2026-09-20", "A") is None,
    "imp_present_20_a": row("imp", "2026-09-20", "A") is not None,
    "imp_selected_20_a": row("decision", "2026-09-20", "A")["Fuente_Dato"] == "IMP",
    "mb_wins_with_both_sources": all(
        row("official", date, shift) is not None
        and row("imp", date, shift) is not None
        and row("decision", date, shift)["Fuente_Dato"] == "MINA"
        for date, shift in (("2026-09-19", "A"), ("2026-09-19", "B"), ("2026-09-21", "B"))
    ),
    "no_source_20_b_21_a": all(
        row("official", date, shift) is None
        and row("imp", date, shift) is None
        and row("decision", date, shift) is None
        for date, shift in (("2026-09-20", "B"), ("2026-09-21", "A"))
    ),
    "tm1_tm2_20_a_match_imp": all(
        abs(r["Valor_Final"] - row("imp", "2026-09-20", "A")["CuT"]) < 1e-9
        and r["Fuente_Tecnica"] == "IMP" and r["Resolucion"] == "PROVISIONAL_IMP"
        for r in data["trace"] if r["Fecha"] == "2026-09-20" and r["Turno"] == "A"
        and r["Analito"] == "CuT"
    ),
    "cache_20_a_matches_imp": abs(float(row("cache", "2026-09-20", "A")["CuT_Real"])
       - row("imp", "2026-09-20", "A")["CuT"]) < 1e-6,
}
(HERE / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(checks, ensure_ascii=False, indent=2))
if not all(checks.values()):
    raise SystemExit(1)
