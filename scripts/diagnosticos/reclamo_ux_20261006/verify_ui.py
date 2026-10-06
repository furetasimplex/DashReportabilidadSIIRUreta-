"""Verify the Reclamo presentation change kept its Dash contract."""
import json
import py_compile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
before = json.loads((HERE / "ui_contract_before.json").read_text(encoding="utf-8"))
after = json.loads((HERE / "ui_contract_after.json").read_text(encoding="utf-8"))
py_compile.compile(str(ROOT / "reclamo" / "panel.py"), doraise=True)

from preview_app import app  # noqa: E402
app._setup_server()
registered = sorted(str(input_) for callback in app.callback_map.values()
                    for input_ in callback["inputs"])
checks = {
    "original_ids_preserved": set(before["layout_ids"]) <= set(after["layout_ids"]),
    "only_new_id_main_tabs": set(after["layout_ids"]) - set(before["layout_ids"]) == {"reclamo-main-tabs"},
    "no_duplicate_layout_ids": after["duplicate_layout_ids"] == [],
    "callback_decorators_unchanged": before["callbacks"] == after["callbacks"],
    "db_calls_unchanged": before["db_calls"] == after["db_calls"],
    "registered_callback_count": len(app.callback_map) == 26,
    "automatizacion_input_registered": any("btn-automatizacion" in item and "n_clicks" in item for item in registered),
    "panel_compiles": True,
}
result = {"checks": checks, "callback_count": len(app.callback_map),
          "ids_before": len(before["layout_ids"]), "ids_after": len(after["layout_ids"]),
          "db_calls": len(after["db_calls"]), "new_ids": sorted(set(after["layout_ids"]) - set(before["layout_ids"]))}
(HERE / "tests.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if not all(checks.values()):
    raise SystemExit(1)
