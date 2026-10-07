"""Read-only validation of monthly matrix chronology and unchanged TMS."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from reclamo import db, panel


def check(frame, name):
    sub = frame.copy()
    sub["dia"] = pd.to_datetime(sub["fecha_operacion"]).dt.normalize()
    sub["tms_camiones_dia"] = sub["tms_camiones_dia"].fillna(0)
    sub["tms_rotopala_dia"] = sub["tms_rotopala_dia"].fillna(0)
    sub["tms_total_dia"] = sub["tms_camiones_dia"] + sub["tms_rotopala_dia"]
    dates = sorted(sub["dia"].unique())
    fmt = "%d" if len({(day.year, day.month) for day in dates}) == 1 else "%d-%m"
    labels = [day.strftime(fmt) for day in dates]
    for metric in ("tms_rotopala_dia", "tms_camiones_dia", "tms_total_dia"):
        matrix = panel._matriz_por_campana(sub, metric)
        assert matrix.columns.tolist() == ["Campaña", "Módulo", "Total periodo", *labels]
        assert matrix.iloc[-1]["Campaña"] == "TOTAL"
        assert len(matrix) == sub[["campana_id", "modulo_id"]].drop_duplicates().shape[0] + 1
        expected = sub[metric].sum()
        assert abs(float(matrix.iloc[-1]["Total periodo"]) - expected) < 0.01
        assert abs(float(matrix.loc[matrix["Campaña"] != "TOTAL", "Total periodo"].sum()) - expected) < 0.01
        for day, label in zip(dates, labels):
            actual = float(matrix.iloc[-1][label])
            wanted = float(sub.loc[sub["dia"] == day, metric].sum())
            assert abs(actual - wanted) < 0.01, (name, metric, label, actual, wanted)
        for (campana_id, campana, modulo_id, modulo_numero), group in sub.groupby(
            ["campana_id", "campana", "modulo_id", "modulo_numero"]
        ):
            row = matrix[(matrix["Campaña"] == campana) & (matrix["Módulo"] == modulo_numero)]
            assert len(row) == 1, (name, campana_id, modulo_id)
            assert abs(float(row.iloc[0]["Total periodo"]) - float(group[metric].sum())) < 0.01
            for day, label in zip(dates, labels):
                wanted = float(group.loc[group["dia"] == day, metric].sum())
                assert abs(float(row.iloc[0][label]) - wanted) < 0.01, (name, metric, modulo_id, label)
    print("PASS", name, "rows", len(sub), "dates", len(dates),
          "first", labels[0], "last", labels[-1])


synthetic = pd.DataFrame([
    {"campana_id": 17, "campana": 17, "modulo_id": 33, "modulo_numero": 33,
     "fecha_operacion": day, "tms_rotopala_dia": i, "tms_camiones_dia": i * 10}
    for i, day in enumerate(pd.date_range("2026-09-01", "2026-10-07"), 1)
])
check(synthetic, "synthetic-full-range")
for metric in ("tms_rotopala_dia", "tms_camiones_dia", "tms_total_dia"):
    tmp = synthetic.copy()
    tmp["dia"] = pd.to_datetime(tmp["fecha_operacion"]).dt.normalize()
    tmp["tms_total_dia"] = tmp["tms_rotopala_dia"] + tmp["tms_camiones_dia"]
    matrix = panel._matriz_por_campana(tmp, metric)
    assert "01-09" in matrix.columns and "01-10" in matrix.columns
    assert matrix.loc[0, "01-09"] != matrix.loc[0, "01-10"]

actual = db.avance_diario("2026-09-01", "2026-10-07")
for pad in (1, 2):
    subset = actual[actual["pad_id"] == pad]
    if not subset.empty:
        check(subset, f"DEV-PAD{pad}")
