"""Validación SELECT-only de presentación y vista local sin acciones de escritura."""
import sys, json, re, ast, subprocess
from pathlib import Path
from datetime import date
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
import pandas as pd
from sqlalchemy import text
from dash import Dash, html
from reclamo import panel, db

baseline = ast.parse(subprocess.check_output(["git", "show", "HEAD:reclamo/panel.py"], cwd=ROOT).decode("utf-8"))
current = ast.parse((ROOT / "reclamo/panel.py").read_text(encoding="utf-8"))
def db_calls(tree):
    return [ast.dump(n, include_attributes=False) for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "db"]
assert db_calls(baseline) == db_calls(current), "Cambió un llamado al backend"
protected = ["_motivo_sin_proyeccion", "_sin_dato_aplicable", "cb_recalcular", "cb_publicar", "cb_registrar_ajuste", "cb_dr_actualizar", "cb_dr_insertar", "barra_filtros"]
for name in protected:
    old = next(n for n in baseline.body if isinstance(n, ast.FunctionDef) and n.name == name)
    new = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == name)
    assert ast.dump(old, include_attributes=False) == ast.dump(new, include_attributes=False), name

with db.get_engine().connect() as conn:
    identity = dict(conn.execute(text("SELECT DB_NAME() AS database_name")).mappings().one())
    assert identity["database_name"].lower() == "inventar_spchidr", identity

desde, hasta = "2026-10-01", "2026-10-07"
avance = db.avance_diario(desde, hasta)
cv = db.estado_cv25(desde, hasta)
rendimiento = db.rendimiento(desde, hasta)
original = avance.copy(deep=True)
for codigo, esperado in panel.ESTADO_CLIENTE.items():
    assert panel.traducir_estado_cliente(codigo) == esperado
assert panel.traducir_estado_cliente(None) == "Sin información"
assert panel.traducir_estado_cliente("SIN_NUEVO_ESTADO") == "Sin información"
assert panel.traducir_estado_cliente("NUEVO_ESTADO") == "Nuevo estado"
assert panel._mensaje_sin_proyeccion("SIN_RESOLVER_CV25 / SIN_COBERTURA") == "Sin proyección por falta de información de CV25 y corriente."
fixture = pd.DataFrame({"flag_calculo": list(panel.ESTADO_CLIENTE), "nota": ["Estado: " + c for c in panel.ESTADO_CLIENTE]})
fixture_original = fixture.copy(deep=True)
table = panel._tabla(fixture, "test", tooltip_data=[{"flag_calculo": {"value": c, "type": "text"}} for c in panel.ESTADO_CLIENTE]).children
pd.testing.assert_frame_equal(fixture, fixture_original)
assert all(row["flag_calculo"] == panel.ESTADO_CLIENTE[c] for row, c in zip(table.data, panel.ESTADO_CLIENTE))
assert all(tip["flag_calculo"]["value"] == panel.ESTADO_CLIENTE[c] for tip, c in zip(table.tooltip_data, panel.ESTADO_CLIENTE))

def serial(value):
    if hasattr(value, "to_plotly_json"):
        return serial(value.to_plotly_json())
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return str(value) if not isinstance(value, (str, int, float, bool, type(None))) else value

panel._hoy_chile = lambda: date(2026, 10, 7)
children, summaries = [], {}
for pad in (1, 2):
    figure, messages = panel.cb_avance(0, None, str(pad), desde, hasta)
    _, hours = panel.cb_rendimiento(0, None, str(pad), desde, hasta)
    data = avance[avance.pad_id == pad].copy()
    data["fecha_operacion"] = pd.to_datetime(data["fecha_operacion"]).dt.normalize()
    status = data.groupby("fecha_operacion")["fuente_reclamo"].apply(lambda s: sorted(set(s))).to_dict()
    rows = []
    for fecha in pd.date_range(desde, hasta):
        sources = status.get(fecha, [])
        source = next((s for s in ("TOPOGRAFIA", "PRELIMINAR_CV25") if s in sources), None)
        matching = cv[pd.to_datetime(cv.fecha).dt.normalize() == fecha]
        reason = source or panel._motivo_sin_proyeccion(fecha, None if matching.empty else matching.iloc[0], pad)
        rows.append({"Fecha": panel._fecha(fecha), "Estado del cálculo": panel.traducir_estado_cliente(reason)})
    expected = ["Topografía real"] * 4 + (["Sin información de corriente", "CV25 sin información suficiente / Sin información de corriente"] if pad == 1 else ["Estimación CV25", "CV25 sin información suficiente"]) + ["Día en curso"]
    assert [r["Estado del cálculo"] for r in rows] == expected
    summaries[str(pad)] = rows
    table = panel._tabla(pd.DataFrame(rows), "estados-" + str(pad))
    from dash import dcc
    block = html.Div([html.H2(f"PAD{pad} · 01-10-2026 a 07-10-2026"), table, dcc.Graph(figure=figure), messages, dcc.Graph(figure=hours)])
    preview = panel.cb_preview_conciliados(0, None, str(pad), desde, hasta)
    visible = json.dumps(serial([block, preview]), ensure_ascii=False)
    assert not re.search(r"SIN_|_CV25|DIA_NO_CERRADO|TOPOGRAFIA|PRELIMINAR_CV25|CERO_OPERACION_CONFIRMADO", visible), visible
    children.append(block)
pd.testing.assert_frame_equal(avance, original)
result = {"identity": identity, "pad_status": summaries, "protected_logic_and_backend_calls_unchanged": True, "preview_checked": True, "source_dataframe_unchanged": True, "table_tooltips_pass": True, "no_visible_technical_codes": True, "sql_write_executed": False}
Path(__file__).with_name("validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
if "--serve" in sys.argv:
    app = Dash(__name__)
    app.layout = html.Div(children, style={"fontFamily": "Segoe UI", "maxWidth": "1150px", "margin": "auto", "padding": "20px"})
    app.run(host="127.0.0.1", port=8107, debug=False)
