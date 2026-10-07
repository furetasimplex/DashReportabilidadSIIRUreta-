"""Synthetic presentation checks; no database access."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import panel

original = panel.db.cuadratura
rows = pd.DataFrame([
    {"pad_id": pad, "campana": 17, "modulo_numero": 33,
     "m3_totales": 45438.5, "m3_rotopala_total": 45913.166,
     "m3_camiones_total": 0, "fecha_inicio_movimiento": "2026-05-16",
     "fecha_fin_movimiento": "2026-05-18", "flag_cuadratura": "OK"}
    for pad in (1, 2)
])
try:
    panel.db.cuadratura = lambda: rows
    for pad in (1, 2):
        figure, _ = panel.cb_cuadratura(1, None, str(pad))
        assert len(figure.data) == 3
        assert [float(trace.y[0]) for trace in figure.data] == [0, 45913.166, 45438.5]
        assert figure.layout.hovermode == "closest"
        for trace in figure.data:
            assert trace.hovertemplate.endswith("<extra></extra>")
            assert list(trace.customdata[0]) == ["C17 · M33", "45.438,50",
                                                  "16-05-2026", "18-05-2026",
                                                  "45.913,166", "0,000"]
    rows["fecha_inicio_movimiento"] = None
    rows["fecha_fin_movimiento"] = None
    figure, _ = panel.cb_cuadratura(1, None, "2")
    assert list(figure.data[0].customdata[0])[2:4] == ["sin dato", "sin dato"]
finally:
    panel.db.cuadratura = original

print("PASS: PAD1/PAD2 tooltip order, formatting, missing dates, unchanged values")

original_avance = panel.db.avance_diario
original_estado = panel.db.estado_proyeccion
try:
    panel.db.avance_diario = lambda _desde, _hasta: pd.DataFrame([
        {"fecha_operacion": "2026-10-05", "pad_id": 2,
         "fuente_reclamo": "PRELIMINAR_CV25", "tms_rotopala_dia": 0,
         "campana": 10, "modulo_numero": 16, "m3_rotopala_dia": 0,
         "flag_calculo": "PRELIMINAR_CV25"}
    ])
    panel.db.estado_proyeccion = lambda _pad, _hasta: pd.DataFrame([
        {"modulo_id": 80, "ultima_topografia": "2026-10-04",
         "fecha_preliminar": "2026-10-05", "tms_preliminar_dia": 0}
    ])
    _, message = panel.cb_avance(1, None, "2", "2026-10-04", "2026-10-07")
    content = str(message.to_plotly_json())
    assert "Topografía disponible hasta 04-10-2026" in content
    assert "Proyección vigente para 05-10-2026" in content
    assert "Proyección CV25: 0 TMS" in content
    assert "Sin proyección: pendiente topografía del día anterior" in content
    assert "Todo el período tiene respaldo topográfico" not in content
finally:
    panel.db.avance_diario = original_avance
    panel.db.estado_proyeccion = original_estado

print("PASS: daily advance message distinguishes topography, zero CV25 and no projection")
