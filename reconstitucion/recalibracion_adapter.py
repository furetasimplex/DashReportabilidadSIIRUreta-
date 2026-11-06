"""Pure sequential adapter for the DB-only recalibrated M&R method.

Inputs are already loaded and case-scoped by the production engine/DB loader.
No IO occurs here. Only the Case's reconciled PAD/turn dry mass is redistributed;
historical profile rows seed the campaign sequence and never replace Case mass.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
import math

import numpy as np
import pandas as pd

try:
    from .recalibracion_mr import ModuleObservation, RecalibrationError, calibrate_density
except ImportError:  # direct import in isolated offline tests
    from recalibracion_mr import ModuleObservation, RecalibrationError, calibrate_density


def _date(value):
    return pd.Timestamp(value).normalize()


def _finite(value, label, *, nonnegative=True):
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise RecalibrationError(f"{label}: valor no numérico.") from exc
    if not math.isfinite(out) or (nonnegative and out < 0):
        raise RecalibrationError(f"{label}: valor no finito o negativo.")
    return out


def _campaign_scope(history, pad_id, campana_id):
    h = history.loc[history.pad_id.eq(pad_id) & history.campana_id.eq(campana_id)].copy()
    if h.empty:
        raise RecalibrationError(f"PAD {pad_id}/campaña DB {campana_id}: falta historia desde nacimiento.")
    h["fecha"] = pd.to_datetime(h.fecha).dt.normalize()
    required_identity = ["pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo"]
    if h[required_identity].isna().any().any():
        raise RecalibrationError("Historia DB contiene identidad de PAD/campaña/parcela/módulo nula.")
    h["vol_diario"] = pd.to_numeric(h.vol_diario, errors="coerce")
    if h.vol_diario.isna().any() or (~np.isfinite(h.vol_diario)).any() or h.vol_diario.lt(0).any():
        raise RecalibrationError(f"PAD {pad_id}/campaña {campana_id}: volumen histórico inválido.")
    return h


def _profile_turns(profile):
    required = {"fecha", "turno", "tmh", "humedad"}
    if not required.issubset(profile.columns):
        raise RecalibrationError("Perfil hist??rico requiere fecha/turno/TMH/humedad.")
    p = profile.copy()
    p["fecha"] = pd.to_datetime(p.fecha).dt.normalize()
    p["turno"] = p.turno.astype(str).str.upper()
    p["tmh"] = pd.to_numeric(p.tmh, errors="coerce")
    p["humedad"] = pd.to_numeric(p.humedad, errors="coerce")
    keys = ["fecha", "turno"] + (["tm"] if "tm" in p else [])
    if p.duplicated(keys).any():
        raise RecalibrationError("Perfil hist??rico repite fecha/turno/correa.")
    if p.tmh.isna().any() or (~np.isfinite(p.tmh)).any() or p.tmh.lt(0).any():
        raise RecalibrationError("Perfil hist??rico TMH faltante, no finito o negativo.")
    if "fuente" in p and p.fuente.astype(str).str.upper().str.contains("SIN_RESOLVER").any():
        raise RecalibrationError("Perfil hist??rico contiene TMH/TMS SIN_RESOLVER.")
    invalid = p.humedad.notna() & ((~np.isfinite(p.humedad)) | p.humedad.lt(0) | p.humedad.ge(100))
    if (invalid | (p.humedad.isna() & p.tmh.gt(0))).any():
        raise RecalibrationError("Humedad faltante/inv??lida con TMH positiva; no se puede calcular TMS.")
    p["tms"] = np.where(p.tmh.eq(0), 0.0, p.tmh * (1.0 - p.humedad / 100.0))
    return p.groupby(["fecha", "turno"], as_index=False)[["tmh", "tms"]].sum()


def _assign(supplies, modules, cutoff):
    """Sequential wet-cap assignment; equal dry fraction follows each wet take."""
    wet = [0.0] * len(modules)
    dry = [0.0] * len(modules)
    out = []
    eps = 1e-10
    for supply in supplies:
        d, shift, in_wet, in_dry = supply
        left_w, left_d = in_wet, in_dry
        for i, module in enumerate(modules):
            target = module["target"]
            if left_w <= eps and left_d <= eps:
                break
            if target is None:
                take_w, take_d = left_w, left_d
            else:
                pending = max(0.0, target - wet[i])
                take_w = min(pending, left_w)
                take_d = left_d * (take_w / left_w) if left_w > eps else 0.0
            if take_w > eps or take_d > eps:
                before = wet[i]
                wet[i] += take_w
                dry[i] += take_d
                left_w -= take_w
                left_d -= take_d
                out.append({"fecha": d, "turno": shift, **module["identity"],
                    "tmh_asignada": take_w, "tms_asignada": take_d,
                    "tmh_previa": before, "tmh_acumulada": wet[i],
                    "objetivo_tmh": target})
        if left_w > 1e-7 or left_d > 1e-7:
            raise RecalibrationError(
                f"Secuencia agotada {d:%Y-%m-%d} turno {shift}: "
                f"residual {left_w:.6g} TMH/{left_d:.6g} TMS.")
    return out, wet, dry


def _allocate_chain(cadena, despacho, excepciones, scope, pad, campaign_id, visible, case_end):
    """Asigna con metas encadenadas desde los datos iniciales de la campana.

    Toda la secuencia, incluida la ventana del Caso, usa TMH y TMS de la masa
    conciliada (OF): una sola base, donde TMS <= TMH en cada turno. El cierre con
    el flujo reconciliado del PAD se aplica despues, con un factor por PAD.
    """
    from .secuencia_campana import chain_targets
    scope = scope.assign(vol_diario=pd.to_numeric(scope.vol_diario, errors="coerce"),
                         vol_total_est=pd.to_numeric(scope.vol_total_est, errors="coerce"))
    supply = despacho.loc[despacho.pad_id.eq(pad) & despacho.campana_id.eq(campaign_id)
                          & despacho.campana.eq(visible)]
    huecos = excepciones.loc[excepciones.tipo.eq("MASA_SIN_VOLUMEN"), "fecha"]
    sin_masa = excepciones.loc[excepciones.tipo.eq("VOLUMEN_SIN_MASA"), "fecha"]
    targets, open_id, log = chain_targets(supply, scope, cadena["cortes"], case_end, huecos, sin_masa)
    identities = scope.sort_values(["modulo", "modulo_id"]).drop_duplicates("modulo_id", keep="last")
    defs = []
    for row in identities.itertuples(index=False):
        mid = int(row.modulo_id)
        if mid in targets or mid == open_id:
            defs.append({"identity": {"pad_id": int(pad), "campana_id": int(campaign_id),
                "campana": int(row.campana), "parcela_id": int(row.parcela_id),
                "modulo_id": mid, "modulo": int(row.modulo)},
                "target": targets.get(mid)})
    # El abierto recibe el saldo: siempre al final, aunque su numero no sea el mayor.
    defs.sort(key=lambda m: m["identity"]["modulo_id"] == open_id)
    rows = [(r.fecha, r.turno, r.tmh, r.tms) for r in supply.itertuples(index=False)]
    rows.sort(key=lambda x: (x[0], 0 if x[1] == "A" else 1))
    alloc, _wet, _dry = _assign(rows, defs, case_end)
    final = log[-1]
    return alloc, {"pad_id": int(pad), "campana_id": int(campaign_id),
        "density_tmh_per_m3": final["density_tmh_per_m3"],
        "tmh_global_campaign": final["tmh_global_campaign"], "tmh_fixed": final["tmh_fixed"],
        "volume_adjustable_real_m3": final["volume_adjustable_real_m3"],
        "cortes_calibrados": len(log)}


#: Con la fuente oficial (ver) k es un control de integridad: debe ser 1 dentro de esto.
TOLERANCIA_K_VER = 1e-4


def _factores_flujo_of(by_pad, alloc, case_start, case_end, tolerancia=None, escalar=True):
    """Factor por PAD entre la TMS de la fuente y el flujo reconciliado del Caso.

    Informado: flujo del PAD / TMS de la fuente del PAD en la ventana. Aplicado: ese mismo
    cuando ``escalar`` (regimen digital y modo of); 1 en el regimen previo, donde la tabla
    cierra con la fuente y la diferencia contra el flujo queda como pendiente visible.
    Con ``tolerancia`` (regimen digital) un k fuera de 1 +- tolerancia genera una excepcion.
    Devuelve (k aplicado, flujo por PAD, TMS de la fuente por PAD, filas de excepcion, k informado).
    """
    dias = by_pad.index.get_level_values("fecha")
    ventana = by_pad.loc[(dias >= case_start) & (dias <= case_end)]
    flujo = (ventana.TMS_T1 + ventana.TMS_T2).groupby(level="pad_id").sum()
    tms_of = alloc.groupby("pad_id").tms_of.sum() if not alloc.empty else pd.Series(dtype=float)
    k, informado, avisos = {}, {}, []
    for pad in sorted(set(flujo.index) | set(tms_of.index)):
        f, base = float(flujo.get(pad, 0.0)), float(tms_of.get(pad, 0.0))
        informado[int(pad)] = f / base if base > 1e-9 else np.nan
        if not escalar:
            k[int(pad)] = 1.0
            if abs(f - base) > 1e-6:
                avisos.append(dict(fecha=case_end, tipo="FLUJO_PENDIENTE_VS_FUENTE", tmh=0.0, tms=f - base,
                    detalle=f"PAD {pad}: flujo {f:.3f} TMS, fuente {base:.3f} TMS, diferencia {f - base:+.3f} TMS "
                            f"(factor informado {informado[int(pad)]:.6f}). Régimen previo: la tabla cierra con la fuente."))
            continue
        if f > 1e-9 and base <= 1e-9:
            raise RecalibrationError(
                f"PAD {pad}: flujo reconciliado {f:.6g} TMS sin TMS conciliada (OF) en la ventana "
                f"del Caso; no se fabrica masa.")
        if f <= 1e-9:
            k[int(pad)] = 0.0
            if base > 1e-9 or float(alloc.loc[alloc.pad_id.eq(pad), "tmh_of"].sum()) > 1e-9:
                por_dia = alloc.loc[alloc.pad_id.eq(pad)].groupby("fecha")[["tmh_of", "tms_of"]].sum()
                for dia, r in por_dia.loc[(por_dia.tmh_of > 1e-9) | (por_dia.tms_of > 1e-9)].iterrows():
                    avisos.append(dict(fecha=dia, tipo="FLUJO_CERO_CON_MASA_OF", tmh=float(r.tmh_of),
                        tms=float(r.tms_of), detalle=f"PAD {pad}: flujo del Caso en cero; la masa oficial queda en cero y se conservan las columnas OF."))
            continue
        k[int(pad)] = f / base
        if tolerancia is not None and abs(k[int(pad)] - 1.0) > tolerancia:
            avisos.append(dict(fecha=case_start, tipo="FACTOR_FLUJO_FUERA_TOLERANCIA", tmh=0.0, tms=base,
                detalle=f"PAD {pad}: flujo {f:.6g} / TMS de la fuente {base:.6g} = {k[int(pad)]:.6f}; "
                        f"fuera de 1 ± {tolerancia:g}. La tabla se escala para cerrar con el flujo."))
    return k, flujo.to_dict(), tms_of.to_dict(), avisos, informado


def _verificar_cadena(template, despacho, objetivo_pad, factor_pad, case_start, case_end, contra="flujo reconciliado"):
    """Conservacion de la rama cadena: por PAD contra el flujo (regimen digital) o contra la fuente
    (regimen previo) y por turno contra la fuente."""
    for pad, flujo in objetivo_pad.items():
        got = float(template.loc[template.pad_id.eq(pad), ["masa_turno1", "masa_turno2"]].sum().sum())
        if not np.isclose(got, flujo, rtol=1e-10, atol=1e-6):
            raise RecalibrationError(
                f"Conservación TMS del PAD {pad} falló: tabla {got:.9g} contra {contra} {flujo:.9g}.")
    window = despacho.loc[despacho.fecha.between(case_start, case_end)]
    source = window.groupby(["fecha", "pad_id", "turno"]).tms.sum()
    got = pd.concat({"A": template.groupby(["fecha", "pad_id"]).TMS_of_turno1.sum(),
                     "B": template.groupby(["fecha", "pad_id"]).TMS_of_turno2.sum()},
                    names=["turno"]).reorder_levels(["fecha", "pad_id", "turno"])
    both = pd.concat([source.rename("fuente"), got.rename("tabla")], axis=1).fillna(0.0)
    bad = both.loc[~np.isclose(both.fuente, both.tabla, rtol=1e-9, atol=1e-6)]
    if not bad.empty:
        raise RecalibrationError(f"Conservación TMS por turno contra la fuente falló en {bad.index[0]}.")
    k = template.pad_id.map(factor_pad).astype(float).fillna(0.0)
    for official, base in (("masa_turno1", "TMS_of_turno1"), ("masa_turno2", "TMS_of_turno2"),
                           ("TMH_turno1", "TMH_of_turno1"), ("TMH_turno2", "TMH_of_turno2")):
        if not np.allclose(template[official], template[base] * k, rtol=1e-12, atol=1e-9):
            raise RecalibrationError(f"{official} no es la base de la fuente por el factor del PAD.")


def apply_recalibrated_distribution(result, history, profile, fixed, caso, *, intraday=None, cadena=None):
    """Rebuild sequential Case allocations while retaining reconciled PAD TMS.

    ``history`` is campaign apilado from birth through the Case end and includes
    all PADs needed to apportion global belt TMH by daily real volume. ``fixed``
    contains exact frozen modules with direct wet/dry DB totals and as-of dates.
    ``result`` is the existing flow-Case result before its timeline is built.
    """
    case_start, case_end = (_date(caso[k]) for k in ("fecha_inicio", "fecha_fin"))
    # digital: cierra con el flujo; previo: cierra con la fuente; of: testeo, escala como el digital sin control.
    regimen = cadena.get("regimen", "digital") if cadena is not None else None
    end_day = case_end
    h = pd.DataFrame(history).copy()
    if h.empty:
        raise RecalibrationError("La DB no devolvió historia de apilado desde nacimiento.")
    h["fecha"] = pd.to_datetime(h.fecha).dt.normalize()
    required_history = ["fecha", "pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo", "vol_diario", "vol_total_est"]
    missing_history = [col for col in required_history if col not in h]
    if missing_history:
        raise RecalibrationError(f"Historia DB sin columnas requeridas: {missing_history}.")
    if h[["pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo"]].isna().any().any():
        raise RecalibrationError("Historia DB contiene identidad PAD/campa?a/parcela/m?dulo nula.")
    if h.fecha.gt(end_day).any():
        raise RecalibrationError("La historia contiene apilado posterior al fin del Caso.")
    p = _profile_turns(pd.DataFrame(profile))
    if p.fecha.max() > end_day:
        raise RecalibrationError("El perfil contiene lecturas posteriores al fin del Caso.")
    if "tm" in pd.DataFrame(profile):
        expected = {"TM1", "TM2"}
        for day, block in pd.DataFrame(profile).assign(fecha=lambda d: pd.to_datetime(d.fecha).dt.normalize()).groupby("fecha"):
            for shift in ("A", "B"):
                belts = set(block.loc[block.turno.astype(str).str.upper().eq(shift), "tm"].astype(str).str.upper())
                if not expected.issubset(belts):
                    raise RecalibrationError(f"Perfil incompleto: falta TM1/TM2 para {day:%Y-%m-%d} turno {shift}.")
    ap = result["apilado"].copy()
    ap["fecha"] = pd.to_datetime(ap.fecha).dt.normalize()
    if not ap.fecha.between(case_start, case_end).all():
        raise RecalibrationError("El apilado de salida sale de la ventana del Caso.")
    pad_mass = result["masa_por_pad"].copy()
    pad_mass["fecha"] = pd.to_datetime(pad_mass.fecha).dt.normalize()
    f = pd.DataFrame(fixed or [])
    if not f.empty:
        for col in ("pad_id", "campana_id", "modulo_id"):
            if col not in f:
                raise RecalibrationError(f"DB de módulos fijos: falta identidad {col}.")
        f["fecha_congelamiento"] = pd.to_datetime(f.fecha_congelamiento, errors="coerce").dt.normalize()
        f["fecha_cierre"] = pd.to_datetime(f.fecha_cierre, errors="coerce").dt.normalize()
        if f[["fecha_congelamiento", "fecha_cierre"]].isna().any().any():
            raise RecalibrationError("Módulo CONGELADO sin fechas de congelamiento/cierre; corte no acreditado.")
        active_pairs = {(int(pad), int(cid)) for pad, cid, _vis in ap.loc[ap.vol_diario.gt(0), ["pad_id", "campana_id", "campana"]].drop_duplicates().itertuples(index=False, name=None)}
        for row in f.itertuples(index=False):
            if (int(row.pad_id), int(row.campana_id)) in active_pairs and pd.isna(getattr(row, "campana", np.nan)):
                raise RecalibrationError(f"M?dulo congelado {row.modulo_id}: falta identidad visible de campa?a en DB.")
        if f.duplicated(["pad_id", "campana_id", "modulo_id"]).any():
            raise RecalibrationError("DB devuelve m?dulos congelados con identidad duplicada; no se puede preservar TMH.")
        if f.fecha_congelamiento.gt(end_day).any() or f.fecha_cierre.gt(end_day).any():
            raise RecalibrationError("El loader incluyó módulo congelado después del fin del Caso.")

    # Global belt wet/dry by turn, split to pad/campaign by observed real volume.
    hist_vol = (h.groupby(["fecha", "pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo"],
                          as_index=False).agg(vol_diario=("vol_diario", "sum"),
                              vol_total_est=("vol_total_est", "last")))
    daily_scope = hist_vol.groupby(["fecha", "pad_id", "campana_id", "campana"], as_index=False).vol_diario.sum()
    daily_global = daily_scope.groupby("fecha").vol_diario.sum()
    profile_by_day = p.groupby("fecha").tmh.sum().to_dict()
    if cadena is None and any(float(tmh) > 0 and float(daily_global.get(day, 0.0)) <= 0
           for day, tmh in profile_by_day.items()):
        raise RecalibrationError("Perfil con TMH positiva sin volumen global DB en esa fecha.")
    total_vol_day = daily_global.to_dict()
    scope_volume = daily_scope.set_index(["fecha", "pad_id", "campana_id", "campana"]).vol_diario.to_dict()
    turns = p.set_index(["fecha", "turno"])
    by_pad = pad_mass.set_index(["fecha", "pad_id"])
    if not {"pad_id", "campana_id", "campana", "vol_diario"}.issubset(ap.columns):
        raise RecalibrationError("Apilado del Caso requiere PAD/campa?a visible/ID/volumen.")
    case_pad_vol = ap.groupby(["fecha", "pad_id"]).vol_diario.sum().to_dict()
    scopes = list(ap.loc[ap.vol_diario.gt(0), ["pad_id", "campana_id", "campana"]]
                  .drop_duplicates().itertuples(index=False, name=None))
    all_allocations, calibrations = [], []
    despacho, excepciones = None, pd.DataFrame()
    if cadena is not None:
        from .secuencia_campana import despachar
        volumes = h.assign(vol_diario=pd.to_numeric(h.vol_diario, errors="coerce"))
        despacho, excepciones = despachar(cadena["conciliado"], volumes, case_end)
        extra = cadena.get("excepciones_fuente")
        if extra is not None and len(extra):
            excepciones = pd.concat([excepciones, pd.DataFrame(extra)], ignore_index=True)
    for pad, campaign_id, visible_campaign in scopes:
        scope = hist_vol.loc[hist_vol.pad_id.eq(pad) & hist_vol.campana_id.eq(campaign_id)
                             & hist_vol.campana.eq(visible_campaign)].copy()
        if scope.empty:
            raise RecalibrationError(f"PAD {pad}/campa?a {visible_campaign}: falta historia DB desde nacimiento.")
        if cadena is not None:
            alloc, calibration_row = _allocate_chain(cadena, despacho, excepciones, scope, pad,
                                                     campaign_id, visible_campaign, case_end)
            all_allocations.extend(alloc)
            calibrations.append(calibration_row)
            continue
        identity_modules = scope.sort_values(["modulo", "modulo_id"]).drop_duplicates("modulo_id", keep="last")
        fixed_scope = (f.loc[f.pad_id.eq(pad) & f.campana_id.eq(campaign_id)
                             & f.campana.eq(visible_campaign)].copy()
                       if not f.empty and "campana" in f else pd.DataFrame())
        fixed_by_id = {int(r.modulo_id): r._asdict() for r in fixed_scope.itertuples(index=False)}
        row_ids = set(identity_modules.modulo_id.astype(int))
        missing = set(fixed_by_id) - row_ids
        if missing:
            raise RecalibrationError(f"PAD {pad}/campaña {campaign_id}: módulo congelado ausente de historia {sorted(missing)}.")
        # Highest physical module number with recent activity is the open final;
        # closed/fixed modules remain capped by the persisted DB wet total.
        not_fixed = identity_modules.loc[~identity_modules.modulo_id.astype(int).isin(fixed_by_id)]
        latest_activity = scope.loc[scope.vol_diario.gt(0), "fecha"].max()
        open_candidates = not_fixed.loc[not_fixed.modulo_id.isin(
            scope.loc[scope.fecha.eq(latest_activity) & scope.vol_diario.gt(0), "modulo_id"].unique())]
        if open_candidates.empty and not not_fixed.empty:
            open_candidates = not_fixed.sort_values(["modulo", "modulo_id"]).tail(1)
        open_id = (int(open_candidates.sort_values(["modulo", "modulo_id"]).iloc[-1].modulo_id)
                   if not open_candidates.empty else None)
        module_observations = []
        for row in identity_modules.itertuples(index=False):
            mid = int(row.modulo_id)
            frow = fixed_by_id.get(mid)
            vol_real = float(scope.loc[scope.modulo_id.eq(mid), "vol_diario"].sum())
            fixed_tmh = frow.get("tmh_apilado") if frow else None
            module_observations.append(ModuleObservation(
                pad_id=int(pad), campana_id=int(campaign_id), modulo_id=mid,
                volume_real_m3=vol_real,
                volume_objetivo_m3=(None if frow else row.vol_total_est),
                frozen=bool(frow),
                fecha_congelamiento=(frow.get("fecha_congelamiento") if frow else None),
                fecha_cierre=(frow.get("fecha_cierre") if frow else None),
                tmh_fijada=(None if fixed_tmh is None or pd.isna(fixed_tmh) else float(fixed_tmh)),
                abierto_al_corte=(mid == open_id and not bool(frow))))

        total_campaign_tmh = 0.0
        for (day, p_id, c_id, visible), vol in scope_volume.items():
            if p_id != pad or c_id != campaign_id or visible != visible_campaign:
                continue
            gvol = float(total_vol_day.get(day, 0.0))
            if gvol <= 0:
                if float(profile_by_day.get(day, 0.0)) > 0:
                    raise RecalibrationError(f"Perfil TMH positiva y volumen global nulo {day:%Y-%m-%d}.")
                continue
            share = float(vol) / gvol
            for shift in ("A", "B"):
                if (day, shift) not in turns.index:
                    if vol > 0:
                        raise RecalibrationError(f"Perfil TMH/TMS ausente {day:%Y-%m-%d} turno {shift}.")
                    continue
                total_campaign_tmh += float(turns.loc[(day, shift), "tmh"]) * share
        calibration = calibrate_density(total_campaign_tmh, module_observations,
            pad_id=int(pad), campana_id=int(campaign_id), cutoff=end_day.date())
        calibrations.append({"pad_id": int(pad), "campana_id": int(campaign_id),
            "density_tmh_per_m3": calibration.density_tmh_per_m3,
            "tmh_global_campaign": calibration.total_tmh,
            "tmh_fixed": calibration.fixed_tmh,
            "volume_adjustable_real_m3": calibration.adjustable_volume_real_m3})

        # Preserve campaign-specific turn supplies from birth. Historical TMS is
        # the measured profile; within the Case only, dry supply comes from the
        # reconciled PAD/run and is split by real campaign volume share.
        module_defs = []
        for m in module_observations:
            target = calibration.targets_tmh[m.modulo_id]
            row = identity_modules.loc[identity_modules.modulo_id.eq(m.modulo_id)].iloc[0]
            module_defs.append({"identity": {"pad_id": int(pad), "campana_id": int(campaign_id),
                "campana": int(row.campana), "parcela_id": int(row.parcela_id),
                "modulo_id": int(m.modulo_id), "modulo": int(row.modulo)},
                "target": target})
        module_defs.sort(key=lambda m: (m["identity"]["modulo"], m["identity"]["modulo_id"]))
        if sum(m["target"] is None for m in module_defs) > 1 or any(
            m["target"] is None for m in module_defs[:-1]):
            raise RecalibrationError(f"PAD {pad}/campaña {campaign_id}: el último abierto no es el último de la secuencia.")
        supplies = []
        days = sorted(scope.fecha.unique())
        for day in days:
            vol_campaign = float(scope.loc[scope.fecha.eq(day), "vol_diario"].sum())
            if vol_campaign <= 0:
                continue
            gvol = float(total_vol_day.get(day, 0.0))
            if gvol <= 0:
                if float(profile_by_day.get(pd.Timestamp(day), 0.0)) > 0:
                    raise RecalibrationError(f"Perfil TMH positiva y volumen global nulo {pd.Timestamp(day):%Y-%m-%d}.")
                continue
            share_global = vol_campaign / gvol
            share_pad = vol_campaign / float(case_pad_vol.get((day, pad), vol_campaign)) if case_start <= day <= case_end else 0.0
            for shift in ("A", "B"):
                if (day, shift) not in turns.index:
                    raise RecalibrationError(f"Perfil TMH/TMS ausente {day:%Y-%m-%d} turno {shift}.")
                wet = float(turns.loc[(day, shift), "tmh"]) * share_global
                if case_start <= day <= case_end:
                    if (day, pad) not in by_pad.index:
                        raise RecalibrationError(f"Caso sin masa reconciliada PAD {pad} {day:%Y-%m-%d}.")
                    # Divide the reconciled PAD turn among campaigns by volume.
                    tms = float(by_pad.loc[(day, pad), "TMS_T1" if shift == "A" else "TMS_T2"]) * share_pad
                else:
                    tms = float(turns.loc[(day, shift), "tms"]) * share_global
                supplies.append((pd.Timestamp(day), shift, wet, tms))
        supplies.sort(key=lambda x: (x[0], 0 if x[1] == "A" else 1))
        alloc, module_wet, module_dry = _assign(supplies, module_defs, end_day)
        for i, m in enumerate(module_defs):
            if m["identity"]["modulo_id"] in fixed_by_id:
                frow = fixed_by_id[m["identity"]["modulo_id"]]
                fixed_tms = frow.get("tms_conformado")
                if fixed_tms is not None and not pd.isna(fixed_tms) and not np.isclose(
                    module_dry[i], float(fixed_tms), rtol=1e-9, atol=1e-5):
                    raise RecalibrationError(
                        f"Módulo congelado {m['identity']['modulo_id']}: TMS secuencial "
                        "no coincide con TMS_conformado DB; no se preserva el fijo.")
        all_allocations.extend(alloc)

    current = [r for r in all_allocations if case_start <= r["fecha"] <= case_end]
    if not current and cadena is not None:
        # Con flujo positivo la causa es la ausencia de masa de la fuente en la ventana.
        _factores_flujo_of(by_pad, pd.DataFrame(columns=["pad_id", "fecha", "tmh_of", "tms_of"]),
                           case_start, case_end, escalar=regimen != "previo")
    if not current:
        raise RecalibrationError("La secuencia recalibrada no asignó masa en la ventana del Caso.")
    alloc = pd.DataFrame(current)
    factor_pad = flujo_pad = tms_of_pad = factor_informado = None
    if cadena is not None:
        # Base OF intacta; la tabla oficial es OF x k, con k por PAD contra el flujo.
        alloc["tmh_of"] = alloc.tmh_asignada
        alloc["tms_of"] = alloc.tms_asignada
        factor_pad, flujo_pad, tms_of_pad, avisos_flujo, factor_informado = _factores_flujo_of(
            by_pad, alloc, case_start, case_end,
            TOLERANCIA_K_VER if regimen == "digital" else None, escalar=regimen != "previo")
        if avisos_flujo:
            excepciones = pd.concat([excepciones, pd.DataFrame(avisos_flujo)], ignore_index=True)
        alloc["factor_flujo_of"] = alloc.pad_id.map(factor_pad).astype(float)
        alloc["tmh_asignada"] = alloc.tmh_of * alloc.factor_flujo_of
        alloc["tms_asignada"] = alloc.tms_of * alloc.factor_flujo_of
    # The same module may receive two segments in a turn when it closes; sum them.
    identity_keys = ["pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo"]
    value_names = {"tmh_asignada": ("TMH_turno1", "TMH_turno2"), "tms_asignada": ("masa_turno1", "masa_turno2")}
    if cadena is not None:
        value_names.update({"tmh_of": ("TMH_of_turno1", "TMH_of_turno2"),
                            "tms_of": ("TMS_of_turno1", "TMS_of_turno2")})
    grouped = (alloc.groupby(["fecha", *identity_keys, "turno"],
        as_index=False)[list(value_names)].sum())
    pivot_keys = ["fecha", *identity_keys]
    allocations = None
    for value, (name_a, name_b) in value_names.items():
        wide = (grouped.pivot(index=pivot_keys, columns="turno", values=value).fillna(0)
                .rename(columns={"A": name_a, "B": name_b}))
        allocations = wide if allocations is None else allocations.join(wide)
    allocations = allocations.reset_index()
    # DB history supplies the physical identity: the engine apilado frame has
    # module_id/campaign_id but intentionally no parcel_id.
    idmap = hist_vol[["pad_id", "campana_id", "campana", "parcela_id", "modulo_id", "modulo"]].drop_duplicates()
    if idmap.duplicated(["pad_id", "campana_id", "campana", "modulo"]).any():
        raise RecalibrationError("Historia DB no resuelve identidad ?nica por m?dulo visible.")
    observed = ap.groupby(["fecha", "pad_id", "campana_id", "campana", "modulo"], as_index=False).agg(
        vol_diario=("vol_diario", "sum"), avance=("avance", "last"))
    observed["fecha"] = pd.to_datetime(observed.fecha).dt.normalize()
    observed = observed.merge(idmap, on=["pad_id", "campana_id", "campana", "modulo"],
        how="left", validate="many_to_one")
    if observed[["modulo_id", "parcela_id"]].isna().any().any():
        raise RecalibrationError("No se pudo resolver identidad f?sica del apilado del Caso desde historia DB.")
    keys = ["fecha", "pad_id", "campana_id", "parcela_id", "modulo_id"]
    template = observed.merge(allocations.drop(columns=["campana", "modulo"]), on=keys, how="outer", validate="one_to_one")
    # Masa asignada a un modulo en un dia sin volumen suyo (p. ej. meta pendiente tras
    # huecos de masa): la fila nace del reparto y la identidad se completa desde la historia.
    ident = idmap.drop_duplicates("modulo_id").set_index("modulo_id")
    for col in ("campana", "modulo", "pad_id", "campana_id", "parcela_id"):
        template[col] = template[col].fillna(template.modulo_id.map(ident[col]))
    for col in [c for names in value_names.values() for c in names]:
        if col not in template:  # un turno sin ninguna asignacion en la ventana
            template[col] = 0.0
        template[col] = template[col].fillna(0.0)
    template["vol_diario"] = template.vol_diario.fillna(0.0)
    template["avance"] = template.avance.fillna(0.0)
    template["estado"] = np.where(template.vol_diario.gt(0), "ACTIVO", "SIN_INICIO")
    template["frac_vol"] = 0.0
    template["cum_ini"] = np.nan
    template["cum_fin"] = np.nan
    template["frac_turno1"] = np.nan
    template["frac_turno2"] = np.nan
    template["cruza_turno"] = template.TMH_turno1.gt(1e-9) & template.TMH_turno2.gt(1e-9)
    template["boundary"] = np.nan
    template["boundary_medida"] = False
    template["boundary_disponible"] = False
    template["boundary_normalizada"] = True
    template["frontera_tipo"] = "secuencial_por_masa"
    template["boundary_src"] = "recalibracion_db"
    template["fuente_masa"] = ("CASO_RECONCILIADO_PAD_TURNO" if cadena is None
                               else "MASA_FUENTE_ESCALADA_A_FLUJO_CASO_PAD")
    if cadena is not None:
        # Trazabilidad por fila y por turno de la fuente de la masa (VER, LIBRO_EXCEL, OF).
        origen = despacho.groupby(["fecha", "pad_id", "turno"]).fuente.agg(lambda s: ",".join(sorted(set(s)))).to_dict()
        for col, turno in (("fuente_dato_turno1", "A"), ("fuente_dato_turno2", "B")):
            template[col] = [origen.get((d, p, turno), "SIN_DATO") for d, p in zip(template.fecha, template.pad_id)]
    template["turnos_ok"] = True
    template["con_masa"] = True
    template["vol_con_masa"] = template.vol_diario
    template["medido_en"] = template.fecha + pd.Timedelta(days=1, hours=8)
    template["turno1_ini"] = template.fecha + pd.Timedelta(hours=8)
    template["turno2_ini"] = template.fecha + pd.Timedelta(hours=20)
    global_daily = result["masa"].copy()
    global_daily["fecha"] = pd.to_datetime(global_daily.fecha).dt.normalize()
    global_daily = global_daily.set_index("fecha")
    template["TMS_dia"] = template.fecha.map(global_daily.TMS)
    template["masa_dia"] = template.TMS_dia
    tmh_daily = p.groupby("fecha").tmh.sum()
    template["TMH_dia"] = template.fecha.map(tmh_daily)
    if cadena is not None:
        # Los totales diarios son los de la tabla oficial; la base OF queda aparte.
        official_tms = (template.masa_turno1 + template.masa_turno2).groupby(template.fecha).sum()
        official_tmh = (template.TMH_turno1 + template.TMH_turno2).groupby(template.fecha).sum()
        template["TMS_dia"] = template.fecha.map(official_tms)
        template["masa_dia"] = template.TMS_dia
        template["TMH_dia"] = template.fecha.map(official_tmh)
        template["TMH_of_dia"] = template.fecha.map(
            (template.TMH_of_turno1 + template.TMH_of_turno2).groupby(template.fecha).sum())
        template["TMS_of_dia"] = template.fecha.map(
            (template.TMS_of_turno1 + template.TMS_of_turno2).groupby(template.fecha).sum())
    template["H_op"] = template.fecha.map(global_daily.H_op)
    template["H_op_src"] = template.fecha.map(global_daily.H_op_src) if "H_op_src" in global_daily else "DB_horas"
    template["vol_dia_total"] = template.fecha.map(ap.groupby("fecha").vol_diario.sum())
    template["n_modulos_dia"] = template.groupby("fecha").modulo.transform("nunique")
    template["masa_total"] = template.masa_turno1 + template.masa_turno2
    template["densidad"] = np.where(template.vol_diario.gt(0), template.masa_total / template.vol_diario, np.nan)
    template["metodo_reparto"] = "SECUENCIAL_DENSIDAD_RECALIBRADA_DB"
    template["densidad_calibrada"] = np.nan
    for row in calibrations:
        msk = template.pad_id.eq(row["pad_id"]) & template.campana_id.eq(row["campana_id"])
        template.loc[msk, "densidad_calibrada"] = row["density_tmh_per_m3"]

    if cadena is None:
        # Case PAD/turn mass must match the reconciled source exactly.
        got = template.groupby(["fecha", "pad_id"])[["masa_turno1", "masa_turno2"]].sum()
        for key2, source in by_pad.loc[((by_pad.index.get_level_values("fecha") >= case_start) & (by_pad.index.get_level_values("fecha") <= case_end))].iterrows():
            gotrow = got.loc[key2] if key2 in got.index else None
            if gotrow is None and np.isclose(source.TMS_T1, 0.0, atol=1e-8) and np.isclose(source.TMS_T2, 0.0, atol=1e-8):
                continue
            if gotrow is None or not np.isclose(gotrow.masa_turno1, source.TMS_T1, rtol=1e-10, atol=1e-5) or not np.isclose(
                gotrow.masa_turno2, source.TMS_T2, rtol=1e-10, atol=1e-5):
                raise RecalibrationError(f"Conservación TMS PAD/turno falló en {key2}.")
    else:
        _verificar_cadena(template, despacho, tms_of_pad if regimen == "previo" else flujo_pad, factor_pad,
                          case_start, case_end, "TMS de la fuente" if regimen == "previo" else "flujo reconciliado")
        for row in calibrations:
            row["factor_flujo_of"] = factor_informado.get(int(row["pad_id"]), np.nan)
            row["factor_aplicado"] = factor_pad.get(int(row["pad_id"]), np.nan)
            row["pendiente_flujo_tms"] = flujo_pad.get(int(row["pad_id"]), 0.0) - tms_of_pad.get(int(row["pad_id"]), 0.0) if regimen == "previo" else 0.0
            row["regimen"] = regimen
            row["flujo_tms_ventana"] = flujo_pad.get(int(row["pad_id"]), 0.0)
            row["tms_of_ventana"] = tms_of_pad.get(int(row["pad_id"]), 0.0)

    # Timeline uses the new sequential wet intervals. Times are estimated from
    # per-turn cumulative wet mass; this adapter deliberately labels the 12 h
    # fallback and does not claim 10-second timing precision. En la rama cadena
    # la fraccion del turno usa la TMH de la fuente sin escalar (el turno suma 12 h)
    # y las masas del intervalo son las oficiales (fuente x k).
    wet_of_col = "tmh_asignada" if cadena is None else "tmh_of"
    timeline_rows = []
    for (day, shift), block in alloc.groupby(["fecha", "turno"], sort=True):
        total = float(block[wet_of_col].sum())
        if total <= 0:
            continue
        global_turn = float(turns.loc[(day, shift), "tmh"])
        base = day + pd.Timedelta(hours=8 if shift == "A" else 20)
        offset = 0.0
        for r in block.sort_values(["pad_id", "campana_id", "modulo"]).itertuples(index=False):
            start = base + pd.Timedelta(hours=12 * offset / global_turn) if global_turn > 0 else base
            offset += float(getattr(r, wet_of_col))
            end = base + pd.Timedelta(hours=12 * offset / global_turn) if global_turn > 0 else base
            if float(r.tmh_asignada) <= 0 and float(r.tms_asignada) <= 0:
                continue
            timeline_rows.append(dict(pad_id=int(r.pad_id), campana=int(r.campana), modulo=int(r.modulo),
                fecha=day, start=start, end=end, mass_h=float(r.tmh_asignada),
                mass_dry=float(r.tms_asignada), origen="perfil_TMH_turno;secuencial_por_masa",
                resolucion="estimado_uniforme_12h;fraccion_ruta_por_volumen"))
    timeline = pd.DataFrame(timeline_rows, columns=["pad_id", "campana", "modulo", "fecha", "start", "end", "mass_h", "mass_dry", "origen", "resolucion"])
    out = dict(result)
    out["shift_table"] = template
    out["module_timeline"] = timeline
    out["itinerario"] = timeline
    out["nuevo_itinerario"] = timeline
    out["recalibracion_mr"] = pd.DataFrame(calibrations)
    out["excepciones_reparto"] = excepciones
    try:
        from .engine import daily_shift_summary, module_summary, weekly_summary
    except ImportError:
        daily_shift_summary = module_summary = weekly_summary = None
    if daily_shift_summary:
        sem = result.get("sem")
        out["daily"] = daily_shift_summary(template, sem) if sem else daily_shift_summary(template)
        out["modules"] = module_summary(template)
        out["weekly"] = weekly_summary(template, sem) if sem else weekly_summary(template)
    else:
        out["daily"] = out["modules"] = out["weekly"] = None
    if cadena is not None:
        _rehacer_balances(out, result, template, ap, regimen)
    return out


def _rehacer_balances(out, result, template, ap, regimen):
    """Alinea masa diaria, masa por PAD y cuadraturas con la tabla oficial.

    La distribucion previa al gancho repartia el flujo con el perfil de correas;
    la tabla oficial usa la fuente de masa. Se conserva la version del perfil en
    columnas ``*_perfil``. Sin el motor (pruebas aisladas) no se recalcula.
    """
    try:
        from .engine import cuadratura_masa
    except ImportError:
        return
    turnos = {"TMS_T1": "masa_turno1", "TMS_T2": "masa_turno2"}
    by_pad = result["masa_por_pad"].copy()
    by_pad["fecha"] = pd.to_datetime(by_pad.fecha).dt.normalize()
    if regimen == "previo":
        # La tabla cierra con la fuente; el flujo publicado queda como referencia y la
        # diferencia aparece como masa pendiente en cuadratura y cuadratura_pad.
        masa = result["masa"].copy()
        masa["fecha"] = pd.to_datetime(masa.fecha).dt.normalize()
        _cuadraturas(out, ap, masa, by_pad, template, cuadratura_masa)
        return
    pad_day = template.groupby(["fecha", "pad_id"])[list(turnos.values())].sum()
    keys = pd.MultiIndex.from_frame(by_pad[["fecha", "pad_id"]])
    for col in ("TMS", *turnos):
        by_pad[f"{col}_perfil"] = by_pad[col]
    for col, source in turnos.items():
        by_pad[col] = pad_day[source].reindex(keys).fillna(0.0).to_numpy()
    by_pad["TMS"] = by_pad.TMS_T1 + by_pad.TMS_T2
    masa = result["masa"].copy()
    masa["fecha"] = pd.to_datetime(masa.fecha).dt.normalize()
    for col in ("TMS", *turnos):
        masa[f"{col}_perfil"] = masa[col]
    day = by_pad.groupby("fecha")[["TMS", *turnos]].sum()
    for col in ("TMS", *turnos):
        masa[col] = masa.fecha.map(day[col]).fillna(0.0)
    masa["boundary"] = masa.TMS_T1.div(masa.TMS).where(masa.TMS.gt(0), 0.0)
    masa["turnos_ok"] = masa.TMS_T1.gt(0) & masa.TMS_T2.gt(0)
    masa["fuente_masa"] = template.fuente_masa.iloc[0]
    out["masa"], out["masa_por_pad"] = masa, by_pad
    _cuadraturas(out, ap, masa, by_pad, template, cuadratura_masa)


def _cuadraturas(out, ap, masa, by_pad, template, cuadratura_masa):
    out["cuadratura"] = cuadratura_masa(ap, masa, template)
    checks = []
    for pad in sorted(by_pad.pad_id.unique()):
        check = cuadratura_masa(ap[ap.pad_id.eq(pad)], by_pad[by_pad.pad_id.eq(pad)].copy(),
                                template[template.pad_id.eq(pad)])
        check["pad_id"] = pad
        checks.append(check)
    out["cuadratura_pad"] = pd.concat(checks, ignore_index=True)
