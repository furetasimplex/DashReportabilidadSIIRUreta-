"""Read-only static and fixture validation; never invokes write callbacks or SQL SPs."""
import inspect
import json
import os
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

os.environ["DB_STARTUP_CHECK"] = "0"
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import main
from reclamo import panel

HERE = Path(__file__).resolve().parent
main.app._setup_server()

def walk(node):
    if isinstance(node, (list, tuple)):
        for child in node:
            yield from walk(child)
    elif hasattr(node, "to_plotly_json"):
        yield node
        yield from walk(getattr(node, "children", None))

def text_of(node):
    return " ".join(str(x) for x in walk(node) if isinstance(getattr(x, "children", None), str))

layout = panel.layout()
ids = [str(x.id) for x in walk(layout) if getattr(x, "id", None) is not None]
duplicates = {k: v for k, v in Counter(ids).items() if v > 1}
callbacks = main.app.callback_map

def input_callbacks(component_id):
    return [key for key, meta in callbacks.items()
            if any(x.get("id") == component_id and x.get("property") == "n_clicks"
                   for x in meta.get("inputs", []))]

original = panel.db.modulos_disponibles
panel.db.modulos_disponibles = lambda: pd.DataFrame([
    {"campana_id": 11, "pad_id": 1, "modulo_id": 15, "modulo_numero": 15, "campana": 11},
    {"campana_id": 11, "pad_id": 2, "modulo_id": 16, "modulo_numero": 16, "campana": 11},
])
try:
    opts, destinations = panel.cb_opciones_modulo(0)
finally:
    panel.db.modulos_disponibles = original

original_sem = panel.db.semaforo
panel.db.semaforo = lambda desde, hasta: pd.DataFrame([
    {"orden": i, "control": "Alertas de automatizacion sin resolver (30 dias)" if i == 12 else f"Control {i}",
     "resultado": "NO PUBLICAR" if i in (1, 12, 14) else "REVISAR", "hallazgos": i}
    for i in range(1, 15)
])
try:
    semaforo = panel.cb_semaforo(0, None, "2026-09-01", "2026-10-04")
finally:
    panel.db.semaforo = original_sem

groups = [x for x in walk(semaforo) if getattr(x, "__class__", None).__name__ == "H4"]
group_names = [x.children for x in groups]
history_cards = [x for x in walk(semaforo) if getattr(x, "__class__", None).__name__ == "Div"
                 and "Historial de automatización" in str(getattr(x, "children", ""))]
source = inspect.getsource(panel)
checks = {
    "no_global_pad_id": "filtro-pad" not in ids,
    "no_orphan_global_pad_callback": not any(x.get("id") == "filtro-pad" for meta in callbacks.values() for x in meta.get("inputs", []) + meta.get("state", [])),
    "no_duplicate_ids": not duplicates,
    "main_buttons_registered": all(input_callbacks(x) for x in ["btn-actualizar", "btn-recalcular", "btn-automatizacion", "btn-publicar", "btn-dr-actualizar", "btn-dr-insertar"]),
    "adjustment_options_include_both_pads": len(opts) == 2 and {x["value"] for x in opts} == {"11|1|15", "11|2|16"} and all("PAD" in x["label"] for x in opts) and opts == destinations,
    "advanced_section_collapsed": any(x.__class__.__name__ == "Details" and any(getattr(c, "children", None) == "Herramientas avanzadas" for c in walk(x)) and not getattr(x, "open", False) for x in walk(layout)),
    "history_info_group": "INFORMACIÓN / TRAZABILIDAD" in group_names,
    "history_visible_info": any("INFORMACIÓN" in text_of(x) and "Últimos 30 días" in text_of(x) for x in history_cards),
    "history_not_in_blockers": "Historial de automatización" not in text_of(semaforo.children[0]) and "Control 1" in text_of(semaforo.children[0]) and "Control 14" in text_of(semaforo.children[0]),
    "scope_shown_on_cards": all(label in text_of(semaforo) for label in ["Estado global", "Período seleccionado", "Últimos 30 días", "Desde fecha de corte"]),
    "base_save_no_recalculate": "db.recalcular" not in inspect.getsource(panel.cb_dr_actualizar) and "db.recalcular" not in inspect.getsource(panel.cb_dr_insertar),
    "reprocess_calls_recalculate": "db.recalcular" in inspect.getsource(panel.cb_recalcular),
    "sequence_calls_maintain_only": "db.mantener_secuencia" in inspect.getsource(panel.cb_automatizacion) and "db.recalcular" not in inspect.getsource(panel.cb_automatizacion),
    "publication_calls_publish_only": "db.publicar" in inspect.getsource(panel.cb_publicar) and "db.recalcular" not in inspect.getsource(panel.cb_publicar),
    "no_global_pad_reference": '"filtro-pad"' not in source,
}
result = {"checks": checks, "pass": all(checks.values()), "callback_count": len(callbacks),
          "duplicate_ids": duplicates, "adjustment_options": opts, "semaforo_groups": group_names,
          "buttons": {x: input_callbacks(x) for x in ["btn-actualizar", "btn-recalcular", "btn-automatizacion", "btn-publicar"]},
          "write_callbacks_invoked": False, "sql_sp_invoked": False}
(HERE / "tests.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
if not result["pass"]:
    raise SystemExit(1)
