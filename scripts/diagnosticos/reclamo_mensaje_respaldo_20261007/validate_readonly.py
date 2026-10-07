"""Validate source messaging against DEV sequence windows; no writes."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db, panel

df = db.avance_diario("2026-10-04", "2026-10-06")
for pad in (1, 2):
    sub = df[df["pad_id"] == pad]
    ventanas = db.ventanas_secuencia(pad)
    no_data = sub[sub["fuente_reclamo"] == "SIN_DATO"]
    count = panel._sin_dato_aplicable(no_data, ventanas)
    assert count <= len(no_data)
    print("PAD", pad, "rows", len(sub), "TOPOGRAFIA",
          int((sub["fuente_reclamo"] == "TOPOGRAFIA").sum()),
          "PRELIMINAR_CV25", int((sub["fuente_reclamo"] == "PRELIMINAR_CV25").sum()),
          "SIN_DATO raw", len(no_data), "applicable", count)
    if pad == 2:
        dates = pd.to_datetime(sub["fecha_operacion"])
        day4 = sub[dates == pd.Timestamp("2026-10-04")]
        day5 = sub[dates == pd.Timestamp("2026-10-05")]
        assert set(day4.loc[day4["fuente_reclamo"] == "TOPOGRAFIA", "modulo_numero"]) == {15, 16}
        assert panel._sin_dato_aplicable(day4[day4["fuente_reclamo"] == "SIN_DATO"], ventanas) == 0
        assert len(day5[(day5["modulo_numero"] == 16) &
                        (day5["fuente_reclamo"] == "PRELIMINAR_CV25") &
                        (day5["tms_rotopala_dia"] == 0)]) == 1
        assert not (sub[dates == pd.Timestamp("2026-10-06")]["fuente_reclamo"] == "PRELIMINAR_CV25").any()
    figure, message = panel.cb_avance(1, None, str(pad), "2026-10-04", "2026-10-06")
    content = str(message.to_plotly_json())
    assert "fila(s) sin respaldo" not in content
    if count == 0:
        assert "módulo/día aplicables sin respaldo" not in content
    else:
        assert f"{count} combinación(es) módulo/día aplicables" in content
    if pad == 2:
        assert "Proyección CV25: 0 TMS" in content
        assert "Topografía disponible hasta 04-10-2026" in content
        assert "Proyección vigente para 05-10-2026" in content
    assert len(figure.data) <= 4

# A valid open module-day with no source must still trigger the warning.
synthetic_rows = pd.DataFrame([{"campana_id": 10, "modulo_id": 80,
                                "fecha_operacion": pd.Timestamp("2026-10-06")}])
assert panel._sin_dato_aplicable(synthetic_rows, db.ventanas_secuencia(2)) == 1
windows = pd.DataFrame([
    {"campana_id": 1, "modulo_id": 1, "rotopala_id": 2, "estado_secuencia": "CERRADO",
     "fecha_apertura": "2026-10-01", "fecha_cierre": "2026-10-04"},
    {"campana_id": 1, "modulo_id": 2, "rotopala_id": 2, "estado_secuencia": "PENDIENTE",
     "fecha_apertura": None, "fecha_cierre": None},
    {"campana_id": 1, "modulo_id": 3, "rotopala_id": 2, "estado_secuencia": "ABIERTO",
     "fecha_apertura": "2026-10-05", "fecha_cierre": None},
])
examples = pd.DataFrame([
    {"campana_id": 1, "modulo_id": module, "fecha_operacion": date}
    for module, date in ((1, "2026-10-04"), (1, "2026-10-05"),
                         (2, "2026-10-04"), (3, "2026-10-04"),
                         (3, "2026-10-05"))
])
assert panel._sin_dato_aplicable(examples, windows) == 2
print("PASS applicable-only messaging, PAD1/PAD2, zero-TMS preliminar")
