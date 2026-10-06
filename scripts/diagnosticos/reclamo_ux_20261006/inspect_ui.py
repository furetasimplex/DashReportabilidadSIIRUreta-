"""Capture static Dash layout IDs and callback contracts without database access."""
from __future__ import annotations
import ast, json, sys
from collections import Counter
from pathlib import Path
from dash.development.base_component import Component

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import panel

HERE = Path(__file__).resolve().parent
phase = sys.argv[1] if len(sys.argv) == 2 else "before"
source = (ROOT / "reclamo" / "panel.py").read_text(encoding="utf-8")
tree = ast.parse(source)

ids = []
def walk(component):
    if isinstance(component, Component):
        component_id = getattr(component, "id", None)
        if component_id is not None:
            ids.append(str(component_id))
        walk(getattr(component, "children", None))
    elif isinstance(component, (list, tuple)):
        for item in component: walk(item)
walk(panel.layout())

callbacks = []
db_calls = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        decorators = [ast.unparse(d) for d in node.decorator_list]
        if any(d.startswith("callback(") for d in decorators):
            callbacks.append({"function": node.name, "decorators": decorators})
        for child in ast.walk(node):
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                if isinstance(child.func.value, ast.Name) and child.func.value.id == "db":
                    db_calls.append({"function": node.name, "db_call": child.func.attr})
result = {"phase": phase, "layout_ids": sorted(ids), "duplicate_layout_ids": sorted(k for k,v in Counter(ids).items() if v>1),
          "callbacks": callbacks, "db_calls": db_calls}
(HERE / f"ui_contract_{phase}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"phase": phase, "layout_id_count": len(ids), "duplicates": result["duplicate_layout_ids"],
                  "callback_count": len(callbacks), "db_call_count": len(db_calls)}, indent=2))
