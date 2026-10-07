"""Validate the default range and picker behavior without database calls."""
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

from dash import dcc

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import panel

for today, expected in (
    (date(2026, 10, 7), (date(2026, 10, 1), date(2026, 10, 6))),
    (date(2026, 11, 1), (date(2026, 10, 1), date(2026, 10, 31))),
    (date(2026, 11, 15), (date(2026, 11, 1), date(2026, 11, 14))),
):
    assert panel._rango_inicial(today) == expected, today


def find_picker(node):
    if isinstance(node, dcc.DatePickerRange) and node.id == "rango":
        return node
    for child in getattr(node, "children", []) or []:
        match = find_picker(child)
        if match is not None:
            return match
    return None


picker = find_picker(panel.barra_filtros())
assert picker is not None
assert (picker.start_date, picker.end_date) == panel._rango_inicial()
assert getattr(picker, "max_date_allowed", None) is None
assert getattr(picker, "min_date_allowed", None) is None
assert 'Output("rango",' not in (ROOT / "reclamo" / "panel.py").read_text(encoding="utf-8")
layout_source = (ROOT / "layout.py").read_text(encoding="utf-8")
assert 'children=reclamo_panel.layout()' in layout_source
assert 'Output("subtabs-reclamo", "style")' in layout_source

# Reprocesar receives the visible range without alteration; replace the DB
# call so this check cannot execute a stored procedure.
original = panel.db.recalcular
captured = []
try:
    panel.db.recalcular = lambda start, end: captured.append((start, end)) or "OK"
    selected = ("2026-09-01", "2026-10-07")
    panel.cb_recalcular(1, *selected)
    assert captured == [selected]
finally:
    panel.db.recalcular = original

print("PASS defaults for 07-10, 01-11, 15-11; Chile date",
      datetime.now(ZoneInfo("America/Santiago")).date(),
      "picker", picker.start_date, picker.end_date,
      "unrestricted; refresh/tabs do not replace range; reprocesar receives selected range")
