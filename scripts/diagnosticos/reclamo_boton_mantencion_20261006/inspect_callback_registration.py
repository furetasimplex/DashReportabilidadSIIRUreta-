"""Read-only local inspection of Dash callback registration; never invokes callbacks."""
from __future__ import annotations

import inspect
import json
import os
import sys
from collections import Counter
from pathlib import Path

os.environ["DB_STARTUP_CHECK"] = "0"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import main
import reclamo.panel as panel
import reclamo.db as db

app = main.app
app._setup_server()

matches = []
for key, meta in app.callback_map.items():
    inputs = meta.get("inputs", [])
    if any(item.get("id") == "btn-automatizacion" and item.get("property") == "n_clicks" for item in inputs):
        cb = meta.get("callback")
        outputs = meta.get("output", [])
        if not isinstance(outputs, (list, tuple)):
            outputs = [outputs]
        matches.append({
            "callback_key": key,
            "function_name": getattr(cb, "__name__", None),
            "function_module": getattr(cb, "__module__", None),
            "function_file": inspect.getsourcefile(panel.cb_automatizacion),
            "inputs": inputs,
            "outputs": [{"component_id": getattr(o, "component_id", None), "component_property": getattr(o, "component_property", None)} for o in outputs],
            "prevent_initial_call": "True (source decorator)",
            "allow_duplicate": "mensaje-accion.children (source decorator)",
        })

def component_ids(node):
    found = []
    if hasattr(node, "id") and node.id is not None:
        found.append(str(node.id))
    children = getattr(node, "children", None)
    if isinstance(children, (list, tuple)):
        for child in children:
            found.extend(component_ids(child))
    elif children is not None and not isinstance(children, (str, int, float)):
        found.extend(component_ids(children))
    return found

ids = component_ids(app.layout)
duplicates = {key: count for key, count in Counter(ids).items() if count > 1}
result = {
    "main_file": str(Path(inspect.getfile(main)).resolve()),
    "panel_module": panel.__name__,
    "panel_file": str(Path(inspect.getfile(panel)).resolve()),
    "db_module": db.__name__,
    "db_file": str(Path(inspect.getfile(db)).resolve()),
    "panel_imported_during_main_import": "reclamo.panel" in __import__("sys").modules,
    "callback_count_after_dash_setup": len(app.callback_map),
    "automation_callback_matches": matches,
    "suppress_callback_exceptions": app.config.suppress_callback_exceptions,
    "duplicate_ids_in_root_layout": duplicates,
    "layout_contains_automation_button": "btn-automatizacion" in ids,
    "sql_or_callback_invoked": False,
}
out = Path(__file__).with_name("callback_registration_inspection.json")
out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=2, ensure_ascii=False))
