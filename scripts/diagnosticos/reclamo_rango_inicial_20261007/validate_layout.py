"""Import the real main module and inspect its constructed Dash layout."""
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from dash import dcc

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ["DB_STARTUP_CHECK"] = "0"  # layout check; no database needed
import main
from reclamo import panel


def find(node, id_):
    if getattr(node, "id", None) == id_:
        return node
    children = getattr(node, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        found = find(child, id_)
        if found is not None:
            return found
    return None


picker = find(main.app.layout, "rango")
adjustment = find(main.app.layout, "aj-fecha")
assert isinstance(picker, dcc.DatePickerRange)
assert isinstance(adjustment, dcc.DatePickerSingle)
today = datetime.now(ZoneInfo("America/Santiago")).date()
assert (picker.start_date, picker.end_date) == panel._rango_inicial(today)
assert adjustment.date == today
assert getattr(picker, "max_date_allowed", None) is None
print("PASS main layout: range", picker.start_date, picker.end_date,
      "aj-fecha", adjustment.date, "Chile today", today)
