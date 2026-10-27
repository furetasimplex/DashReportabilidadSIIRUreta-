"""Reconstruct module intervals from observed wet conveyor tonnage.

Daily A/B wet readings define the time boundaries;
module shares are derived from daily volume shares because no measured module
wet-tonnage field exists. Uniform movement within each 12-hour shift is an
explicit fallback used only to map cumulative wet mass to clock time.
"""
import numpy as np
import pandas as pd


CONTRACT = ["pad_id", "campana", "modulo", "fecha", "start", "end",
            "mass_h", "mass_dry", "origen", "resolucion"]


def build_module_timeline(apilado: pd.DataFrame, st: pd.DataFrame,
                          profile: pd.DataFrame, intraday=None) -> pd.DataFrame:
    """Return intraday segment rows from ``apilado``, dry-mass ``st`` and
    ``profile`` (fecha/turno/tmh). Missing or nonpositive profile blocks output;
    missing hours are not imputed.

    Each module gets one daily wet-mass interval based on its share of daily
    volume. The daily cumulative is split at the observed A/B wet boundary and
    mapped uniformly within each 12-hour shift. A plant-wide profile cannot
    identify simultaneous PAD routes, so multiple active PADs fail closed.
    ``mass_dry`` is the already allocated daily TMS from ``st`` (not recomputed
    from wet mass or duplicated across shifts).
    """
    if not {"fecha", "pad_id", "campana", "modulo", "vol_diario"}.issubset(apilado):
        raise ValueError("apilado requiere fecha/pad_id/campana/modulo/vol_diario")
    if not {"fecha", "turno", "tmh"}.issubset(profile):
        raise ValueError("perfil requiere fecha/turno/tmh")
    if "estado" in apilado:
        ap = apilado.loc[apilado.estado.eq("ACTIVO")].copy()
    else:
        ap = apilado.loc[apilado.vol_diario.gt(0)].copy()
    if ap.empty:
        return pd.DataFrame(columns=CONTRACT)
    ap["fecha"] = pd.to_datetime(ap.fecha).dt.normalize()
    p = profile.copy()
    p["fecha"] = pd.to_datetime(p.fecha).dt.normalize()
    p["turno"] = p.turno.astype(str).str.upper()
    has_tm = "tm" in p.columns
    p["tm"] = p.tm.astype(str).str.upper() if has_tm else "TMH"
    p["tmh"] = pd.to_numeric(p.tmh, errors="coerce")
    needed = set(ap.fecha.unique())
    p = p[p.fecha.isin(needed)]
    if p.tmh.isna().any() or (~np.isfinite(p.tmh)).any() or p.tmh.lt(0).any():
        raise ValueError("perfil TMH faltante, no finito o negativo; no se imputan horas")
    if p.duplicated(["fecha", "turno", "tm"]).any():
        raise ValueError("perfil TMH duplicado por fecha, turno y correa")
    if not p.turno.isin(["A", "B"]).all() or (has_tm and not p.tm.isin(["TM1", "TM2"]).all()):
        raise ValueError("identidad de turno/correa no valida en perfil TMH")
    if has_tm:
        expected = pd.MultiIndex.from_product([needed, ["A", "B"], ["TM1", "TM2"]],
                                              names=["fecha", "turno", "tm"])
        actual = pd.MultiIndex.from_frame(p[["fecha", "turno", "tm"]].drop_duplicates())
        if len(expected.difference(actual)):
            raise ValueError("perfil incompleto: falta lectura de una correa en un turno activo")
    totals = p.groupby(["fecha", "turno"], sort=False).tmh.sum().unstack("turno")
    if not {"A", "B"}.issubset(totals.columns):
        raise ValueError("perfil incompleto: se requieren TMH de turnos A y B")
    totals = totals.reindex(pd.DatetimeIndex(needed))
    if totals[["A", "B"]].isna().any().any() or (totals[["A", "B"]] < 0).any().any() or (totals[["A", "B"]].sum(axis=1) <= 0).any():
        raise ValueError("perfil TMH A/B faltante o sin masa positiva; no se imputan horas")
    ap["fecha"] = pd.to_datetime(ap.fecha).dt.normalize()
    dry = st.copy()
    if not dry.empty:
        dry["fecha"] = pd.to_datetime(dry.fecha).dt.normalize()
    rows = []
    for day, g in ap.groupby("fecha", sort=True):
        if day not in totals.index:
            raise ValueError(f"perfil TMH faltante para {day.date()}")
        if g.pad_id.nunique() > 1:
            raise ValueError(f"más de un PAD activo en {day.date()}; el perfil global no identifica la ruta")
        order = [c for c in ["avance", "modulo", "pad_id", "campana"] if c in g]
        asc = [False if c == "avance" else True for c in order]
        g = g.sort_values(order, ascending=asc)
        vol = g.vol_diario.astype(float)
        if vol.isna().any() or (vol < 0).any() or vol.sum() <= 0:
            raise ValueError(f"volumen inválido para {day.date()}")
        a, b = map(float, totals.loc[day, ["A", "B"]])
        wet_total = a + b
        vol_total = float(vol.sum())
        cum = 0.0
        from .intraday_timeline import clock_from_intraday
        detailed_clock, detail_reason = clock_from_intraday(day, p.loc[p.fecha.eq(day)], intraday)
        def to_time(x, side):
            if detailed_clock is not None:
                return detailed_clock(x, side)
            return coarse_time(x)
        def coarse_time(x):
            if a > 0 and x < a:
                return day + pd.Timedelta(hours=8 + 12 * x / a)
            if a > 0 and x == a:
                return day + pd.Timedelta(hours=20)
            if b > 0:
                return day + pd.Timedelta(hours=20 + 12 * max(0.0, x - a) / b)
            return day + pd.Timedelta(hours=20)
        for r in g.itertuples():
            frac = float(r.vol_diario) / vol_total
            w0, w1 = min(cum,1.) * wet_total, min(cum + frac,1.) * wet_total
            cum += frac
            q = dry.loc[(dry.fecha.eq(day)) & (dry.pad_id.eq(r.pad_id)) &
                        (dry.campana.eq(r.campana)) & (dry.modulo.eq(r.modulo))]
            md = (float(q.masa_turno1.iloc[0] + q.masa_turno2.iloc[0])
                  if len(q) and {"masa_turno1", "masa_turno2"}.issubset(q.columns)
                  else np.nan)
            rows.append(dict(pad_id=r.pad_id, campana=r.campana, modulo=r.modulo,
                fecha=day, start=to_time(w0, "start"), end=to_time(w1, "end"),
                mass_h=wet_total*frac, mass_dry=md,
                origen=("totalizadores_TMH_validados; modulo_derivado_frac_vol" if detailed_clock is not None
                        else "perfil_TMH_turno; modulo_derivado_frac_vol"),
                resolucion=(detail_reason if detailed_clock is not None
                            else "interpolacion_uniforme_12h; " + detail_reason)))
    return pd.DataFrame(rows, columns=CONTRACT).sort_values(
        ["pad_id", "campana", "start", "modulo"]).reset_index(drop=True)
