"""Integrated DEV validation; no data changes or SP execution."""
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from dash import dash_table

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db, panel


def find_table(node):
    if isinstance(node, dash_table.DataTable):
        return node
    children = getattr(node, "children", None)
    if children is None:
        return None
    if not isinstance(children, (list, tuple)):
        children = [children]
    for child in children:
        match = find_table(child)
        if match is not None:
            return match
    return None


cv = db.diferencia_cv25("2026-10-04", "2026-10-06")
by_day = {str(row.fecha)[:10]: row for row in cv.itertuples()}
day4, day5 = by_day["2026-10-04"], by_day["2026-10-05"]
assert day4.modulos_topografia > 0 and day4.tms_topografia > 0
assert abs(float(day4.diferencia_pct) - (-19.998943)) < 0.0001
assert day5.modulos_topografia == 0
assert pd.isna(day5.tms_topografia)
assert pd.isna(day5.diferencia_topografia_cv25)
assert pd.isna(day5.diferencia_pct)
assert "SIN_TOPOGRAFIA" in day5.flag_diferencia
assert day5.tms_cv25 == 18 and day5.tms_preliminar == 0
figure, gap = panel.cb_cv25(1, None, "2026-10-04", "2026-10-06")
assert pd.isna(figure.data[1].y[1])
assert pd.isna(gap.data[0].y[1])

daily = db.avance_diario("2026-10-01", "2026-10-06")
for pad in (1, 2):
    sub = daily[daily["pad_id"] == pad]
    missing = sub[sub["fuente_reclamo"] == "SIN_DATO"]
    applicable = panel._sin_dato_aplicable(missing, db.ventanas_secuencia(pad))
    print("PAD", pad, "SIN_DATO raw", len(missing), "applicable", applicable)
    assert applicable <= len(missing)

summary = panel.cb_resumen_general(1, None, "2026-10-01", "2026-10-06")
summary_text = str(summary.to_plotly_json())
assert "43 combinaciones módulo/día sin información disponible" not in summary_text
assert "aplicables sin información disponible" not in summary_text
assert "Brecha acumulada del período" in summary_text

preview = panel.cb_preview_conciliados(1, None, "2", "2026-10-01", "2026-10-06")
table = find_table(preview)
assert table is not None
day4_preview = [row for row in table.data if row["Fecha"] == "04-10-2026"]
assert len(day4_preview) == 1 and day4_preview[0]["Origen rotopala"] == "Topografía real"
day5_preview = [row for row in table.data if row["Fecha"] == "05-10-2026"]
assert len(day5_preview) == 1
row = day5_preview[0]
assert row["Campaña"] == 11, row
assert row["Módulo mayor avance"] == 16, row
assert row["Rotopala (TMS)"] == 0
assert row["Origen rotopala"] == "Estimación CV25", row
assert row["% avance módulo"] not in ("", None)
assert panel._rango_inicial(date(2026, 10, 7)) == (date(2026, 10, 1), date(2026, 10, 6))
assert panel._rango_inicial(date(2026, 11, 1)) == (date(2026, 10, 1), date(2026, 10, 31))

print("PASS CV25 no topography, summary applicability, preview zero, default range", row)
