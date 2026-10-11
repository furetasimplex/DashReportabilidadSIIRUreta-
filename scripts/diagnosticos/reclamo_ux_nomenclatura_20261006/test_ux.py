"""Pure presentation and Dash contract checks; no database writes."""
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from reclamo import panel
from preview_app import app

checks = {}
mapping = pd.DataFrame([{"campana_id": 4, "campana": 17}])
with patch.object(panel.db, "campanas_disponible_rotopalas", return_value=mapping):
    opts, insert_opts = panel.cb_opciones_dr_campana(0)
checks["campaign_dropdown_label_and_value"] = opts == [{"label": "Campaña 17", "value": 4}] and insert_opts == opts

fixture = pd.DataFrame([{
    "id_disponible_rotopalas": 100, "pad_id": 1, "modulo_numero": 1,
    "modulo_id": 9, "campana": 17, "campana_id": 4,
    "tms": 100.0, "m3_totales": 50.0, "densidad": 2.0,
    "estado_congelado": "ABIERTO", "fecha_conformacion": "2026-10-06",
}])
with patch.object(panel.db, "disponible_rotopalas", return_value=fixture):
    table, editor_options, store = panel.cb_tabla_disponible_rotopalas(0, 0, None, None, None, None, None, None, None)
checks["editor_no_id_and_operational_campaign"] = editor_options[0] == {
    "label": "Módulo 1 · Campaña 17 · PAD 1 — Óxidos", "value": 100}
table_component = table.children[-1].children
column_names = {item["name"] for item in table_component.columns}
checks["technical_columns_absent"] = not ({"Campaña ID", "modulo_id", "id_disponible_rotopalas", "ID"} & column_names)
checks["state_translated"] = table_component.data[0]["Estado"] == "Abierto"
checks["date_formatted"] = panel._fecha("2026-10-06T12:03:29.826000", True) == "06-10-2026 12:03"
event = pd.DataFrame([{"accion": "ALERTA_SIN_BASE", "pad_id": 1, "campana_id": 4,
                       "campana": 17, "modulo_numero": 1, "detalle": "Revisar",
                       "fecha_evento": "2026-10-06T12:03:29.826000"}])
with patch.object(panel.db, "alertas_automatizacion", return_value=event):
    event_table = panel.cb_alertas_automatizacion(0, None).children[-1].children
checks["event_date_and_campaign"] = (event_table.data[0]["fecha_evento"] == "06-10-2026 12:03"
                                      and event_table.data[0]["campana"] == 17)
checks["local_number"] = panel._numero(91300.1, 2) == "91.300,10"

matrix = panel._matriz_por_campana(pd.DataFrame([
    {"campana_id": 3, "campana": 16, "modulo_id": 11, "modulo_numero": 33, "dia": "01", "total": 1},
    {"campana_id": 4, "campana": 17, "modulo_id": 22, "modulo_numero": 33, "dia": "01", "total": 2},
]), "total")
checks["same_module_separate_campaigns"] = len(matrix) == 3 and set(matrix.iloc[:2]["Campaña"]) == {16, 17}
with patch.object(panel.db, "rendimiento", return_value=pd.DataFrame([{
    "fecha": "2026-10-04", "rotopala_id": 2, "rendimiento_pesometro_tms_hr": 2007.87,
    "rendimiento_topografia_tms_hr": 0.0, "tiene_topografia_real": 0,
    "horas_operacion": 20.0,
}])):
    chart, _ = panel.cb_rendimiento(0, None, "2", "2026-10-04", "2026-10-04")
checks["no_false_topography_zero"] = pd.isna(chart.data[1].y[0])

prior = json.loads((ROOT / "scripts/diagnosticos/reclamo_ux_20261006/ui_contract_after.json").read_text(encoding="utf-8"))
current = json.loads((ROOT / "scripts/diagnosticos/reclamo_ux_20261006/ui_contract_nomenclatura.json").read_text(encoding="utf-8"))
checks["ids_preserved_no_duplicates"] = set(prior["layout_ids"]) == set(current["layout_ids"]) and not current["duplicate_layout_ids"]
checks["callback_decorators_preserved"] = prior["callbacks"] == current["callbacks"]
app._setup_server()
checks["callback_map_26"] = len(app.callback_map) == 26
checks["automatizacion_registered"] = any(
    item["id"] == "btn-automatizacion" and item["property"] == "n_clicks"
    for callback in app.callback_map.values() for item in callback["inputs"])
py_compile.compile(str(ROOT / "reclamo/panel.py"), doraise=True)
py_compile.compile(str(ROOT / "reclamo/db.py"), doraise=True)
checks["py_compile"] = True
checks["git_diff_check"] = subprocess.run(
    ["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True).returncode == 0
(HERE / "tests.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(checks, ensure_ascii=False, indent=2))
if not all(checks.values()):
    raise SystemExit(1)
