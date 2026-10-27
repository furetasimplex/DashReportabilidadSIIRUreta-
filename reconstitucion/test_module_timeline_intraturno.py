"""Regressions for cumulative daily and validated 10-second timeline clocks."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest


APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from .module_timeline import build_module_timeline
except ImportError:
    from reconstitucion.module_timeline import build_module_timeline  # noqa: E402


def make_inputs(two_modules=True):
    day = pd.Timestamp("2026-10-06")
    modules = [
        dict(fecha=day, pad_id=2, campana=12, modulo=5, avance=.9,
             vol_diario=40., estado="ACTIVO"),
    ]
    if two_modules:
        modules.append(dict(fecha=day, pad_id=2, campana=12, modulo=6,
             avance=.1, vol_diario=60., estado="ACTIVO"))
    ap = pd.DataFrame(modules)
    dry = pd.DataFrame([
        dict(fecha=day, pad_id=2, campana=12, modulo=5,
             masa_turno1=12., masa_turno2=8.),
        *([dict(fecha=day, pad_id=2, campana=12, modulo=6,
             masa_turno1=30., masa_turno2=15.)] if two_modules else []),
    ])
    profile = pd.DataFrame([
        dict(fecha=day, turno="A", tm="TM1", tmh=40.),
        dict(fecha=day, turno="A", tm="TM2", tmh=40.),
        dict(fecha=day, turno="B", tm="TM1", tmh=10.),
        dict(fecha=day, turno="B", tm="TM2", tmh=10.),
    ])
    return day, ap, dry, profile


def make_intraday(day, profile):
    rows = []
    for p in profile.itertuples():
        start = day + pd.Timedelta(hours=8 if p.turno == "A" else 20)
        delta = float(p.tmh) / 4320
        ends = pd.date_range(start + pd.Timedelta(seconds=10), periods=4320, freq="10s")
        starts = ends - pd.Timedelta(seconds=10)
        rows.extend(dict(fecha_op=day, turno=p.turno, tm=p.tm,
                         start=s, end=e, mass_h=delta, quality="ok")
                    for s, e in zip(starts, ends))
    return pd.DataFrame(rows)


def test_daily_cumulative_crosses_A_once_then_B_and_conserves_wet_and_dry():
    day, ap, st, profile = make_inputs()
    out = build_module_timeline(ap, st, profile)
    m5 = out.loc[out.modulo.eq(5)].iloc[0]
    m6 = out.loc[out.modulo.eq(6)].iloc[0]
    # 40% of 100 TMH is 40 t; 40/80 of A's 12 h ends at 14:00.
    assert m5.start == day + pd.Timedelta(hours=8)
    assert abs(m5.end - (day + pd.Timedelta(hours=14))) <= pd.Timedelta(microseconds=1)
    assert m6.start == m5.end
    assert m6.end == day + pd.Timedelta(days=1, hours=8)
    assert out.mass_h.sum() == pytest.approx(profile.tmh.sum())
    # TMS is preserved from the assigned shift balances despite different wet/dry ratio.
    assert out.set_index("modulo").loc[5, "mass_dry"] == pytest.approx(20.)
    assert out.set_index("modulo").loc[6, "mass_dry"] == pytest.approx(45.)
    assert out.mass_dry.sum() == pytest.approx(65.)


def test_validated_10s_increments_replace_uniform_shift_interpolation():
    day, ap, st, profile = make_inputs()
    out = build_module_timeline(ap, st, profile, intraday=make_intraday(day, profile))
    m5 = out.loc[out.modulo.eq(5)].iloc[0]
    assert abs(m5.end - (day + pd.Timedelta(hours=14))) <= pd.Timedelta(microseconds=1)
    assert out.resolucion.eq("totalizadores_10s_validados_con_TMH_turno").all()
    assert out.mass_h.sum() == pytest.approx(100.)
    assert out.mass_dry.sum() == pytest.approx(65.)


def test_incomplete_10s_coverage_explicitly_falls_back_to_A_B_boundary():
    day, ap, st, profile = make_inputs()
    raw = make_intraday(day, profile).iloc[1:].copy()
    out = build_module_timeline(ap, st, profile, intraday=raw)
    assert out.loc[out.modulo.eq(5), "end"].iloc[0] == day + pd.Timedelta(hours=14)
    assert out.resolucion.str.contains("cobertura_intraturno_incompleta").all()
    assert out.resolucion.str.contains("interpolacion_uniforme_12h").all()


def test_daily_global_profile_rejects_ambiguous_simultaneous_pads():
    day, ap, st, profile = make_inputs()
    ap.loc[1, "pad_id"] = 1
    st.loc[1, "pad_id"] = 1
    with pytest.raises(ValueError, match="más de un PAD activo"):
        build_module_timeline(ap, st, profile, intraday=make_intraday(day, profile))


def test_float_cumulative_threshold_preserves_both_sides_of_pause():
    day, ap, st, profile = make_inputs()
    ap['vol_diario'] = 50.
    profile['tmh'] = 50.
    raw = make_intraday(day, profile)
    for tm in ('TM1', 'TM2'):
        a = raw.index[raw.turno.eq('A') & raw.tm.eq(tm)]
        b = raw.index[raw.turno.eq('B') & raw.tm.eq(tm)]
        raw.loc[a, 'mass_h'] = 0.
        raw.loc[b, 'mass_h'] = 0.
        raw.loc[a[:3960], 'mass_h'] = 50./3960
        raw.loc[b[360:], 'mass_h'] = 50./3960
    out = build_module_timeline(ap, st, profile, intraday=raw).set_index('modulo')
    assert out.loc[5, 'end'] == day + pd.Timedelta(hours=19)
    assert out.loc[6, 'start'] == day + pd.Timedelta(hours=21)
    assert out.mass_h.sum() == pytest.approx(200.)
