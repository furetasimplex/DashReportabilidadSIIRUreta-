"""Reconstitucion de un Caso por densidad humeda recalibrada (puro, sin SQL).

Orquesta ``recalibracion`` sobre frames ya leidos:

    1. perfil comun de masa global (seccion 6) y fraccion de volumen
       s_{p,c,d} = V_{p,c,d} / sum V_d;
    2. suministro por PAD+campana+fecha+turno desde el NACIMIENTO de la
       campana; TMS medida (TMH * (1-h/100)) antes del Caso y TMS reconciliada
       del PAD (F18/F19) distribuida por turno dentro de la ventana (sec. 11);
    3. modulos fijados preservados, rho_h por campana, metas y asignacion
       secuencial por turno (secciones 7-10);
    4. ``shift_table`` con las mismas columnas del motor anterior mas las de
       masa humeda y metas, y el itinerario horario estimado (sec. 12).

La unica fuente de verdad del grafico, la tabla, el detalle y la exportacion
son los frames devueltos aqui (seccion 14).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import recalibracion as rc
from .modelo_flujos import FlowCaseError
from .validacion import Aviso

METODO = "recalibrada"
FUENTE_MASA = "RECALIBRACION_DENSIDAD_HUMEDA"
RESOLUCION_HORARIA = "interpolacion_uniforme_12h; estimacion desde asignacion de TMH"
ORIGEN_HORARIO = "asignacion_secuencial_TMH_recalibrada; hora_estimada"
TIMELINE_COLS = ["pad_id", "campana", "modulo", "fecha", "start", "end",
                 "mass_h", "mass_dry", "origen", "resolucion"]


# ----------------------------------------------------------------- entradas

def _norm_apilado(ap, end):
    ap = ap.copy()
    falta = {"fecha", "pad_id", "campana", "modulo", "vol_diario"} - set(ap.columns)
    if falta:
        raise rc.RecalibracionError(f"apilado requiere columnas {sorted(falta)}")
    ap["fecha"] = pd.to_datetime(ap["fecha"]).dt.normalize()
    ap = ap.loc[ap["fecha"] <= pd.Timestamp(end).normalize()].copy()   # sin info posterior al corte
    for c in ("pad_id", "campana", "modulo"):
        ap[c] = pd.to_numeric(ap[c]).astype("int64")
    if "campana_id" not in ap.columns:
        ap["campana_id"] = ap["campana"]
    if "modulo_id" not in ap.columns:
        ap["modulo_id"] = ap["modulo"]
    ap["campana_id"] = pd.to_numeric(ap["campana_id"]).astype("int64")
    ap["modulo_id"] = pd.to_numeric(ap["modulo_id"]).astype("int64")
    ap["vol_diario"] = pd.to_numeric(ap["vol_diario"], errors="coerce")
    if ap["vol_diario"].lt(0).any():
        raise rc.RecalibracionError("volumen diario negativo en el apilado")
    ap["vol_diario"] = ap["vol_diario"].fillna(0.0)
    for col in ("avance", "vol_total_est", "vol_acum_final"):
        if col not in ap.columns:
            ap[col] = np.nan
    # Identidad (seccion 5): ni ambigua ni duplicada.
    checks = [(["pad_id", "campana"], "campana_id", "una campana visible con varios identificadores tecnicos"),
              (["pad_id", "campana_id"], "campana", "un identificador tecnico con varias campanas visibles"),
              (["pad_id", "campana_id", "modulo"], "modulo_id", "un modulo visible con varios modulos fisicos"),
              (["pad_id", "campana_id", "modulo_id"], "modulo", "un modulo fisico con varios numeros visibles")]
    for keys, col, msg in checks:
        if ap.groupby(keys)[col].nunique().gt(1).any():
            raise rc.RecalibracionError(f"Identidad ambigua en el apilado: {msg}")
    dkey = ["pad_id", "campana_id", "modulo_id", "fecha"]
    pos = ap.loc[ap["vol_diario"].gt(0)]
    if pos.duplicated(dkey).any():
        raise rc.RecalibracionError(
            "Identidad duplicada: un modulo tiene dos filas con volumen el mismo dia")
    ap = ap.sort_values(dkey + ["vol_diario"], ascending=[True] * 4 + [False])
    return ap.drop_duplicates(dkey).reset_index(drop=True)


def perfil_global(perfil, fechas_con_volumen, desde):
    """W y D globales por (fecha, turno). Falta de lectura = error (sec. 13).

    * ``SIN_RESOLVER``, TMH ausente/negativa o correa/turno faltante en un dia
      con volumen: ``FlowCaseError`` (no se completa el perfil).
    * TMH cero: TMS cero (no se inventa humedad).
    * TMH positiva sin humedad valida: TMS ausente (NaN)."""
    p = perfil.copy()
    p["fecha"] = pd.to_datetime(p["fecha"]).dt.normalize()
    p["turno"] = p["turno"].astype(str).str.upper().str[-1]
    p["tm"] = p["tm"].astype(str).str.upper() if "tm" in p.columns else "TM1"
    p = p.loc[p["fecha"] >= pd.Timestamp(desde).normalize()]
    if p.duplicated(["fecha", "turno", "tm"]).any():
        raise FlowCaseError("El perfil operativo repite fecha, turno y correa.")
    wet = pd.to_numeric(p["tmh"], errors="coerce")
    hum = pd.to_numeric(p["humedad"], errors="coerce") if "humedad" in p.columns \
        else pd.Series(np.nan, index=p.index)
    fuente = p["fuente"] if "fuente" in p.columns else pd.Series("PI", index=p.index)
    malo = ~np.isfinite(wet) | wet.lt(0) | fuente.isna() | fuente.eq("SIN_RESOLVER")
    need = p["fecha"].isin(set(fechas_con_volumen))
    if (malo & need).any():
        raise FlowCaseError("Faltan lecturas de correa validas para reconstituir la historia de la campana.")
    expected = pd.MultiIndex.from_product(
        [sorted(set(fechas_con_volumen)), ["A", "B"], ["TM1", "TM2"]],
        names=["fecha", "turno", "tm"])
    actual = pd.MultiIndex.from_frame(p[["fecha", "turno", "tm"]])
    if len(expected.difference(actual)):
        raise FlowCaseError("Faltan lecturas de correa o turno en la historia de la campana; no se completan.")
    hum_ok = np.isfinite(hum) & hum.ge(0) & hum.lt(100)
    p["W"] = wet.where(~malo)
    p["D"] = (wet * (1 - hum / 100)).where(wet.ne(0) & hum_ok, np.nan)
    p.loc[wet.eq(0), "D"] = 0.0
    g = p.groupby(["fecha", "turno"]).agg(
        W=("W", lambda s: s.sum(min_count=1)),
        D=("D", lambda s: s.sum(min_count=len(s))),   # una correa sin TMS => TMS ausente
        n_tm=("tm", "nunique"))
    return g


# ------------------------------------------------------------ suministro

def _tms_ventana(tms_pad):
    t = tms_pad.copy()
    t["fecha"] = pd.to_datetime(t["fecha"]).dt.normalize()
    return t.set_index(["pad_id", "fecha"])[["TMS_T1", "TMS_T2"]]


def construir_suministro(ap, pg, tms_pad, start, end):
    """Suministro por PAD+campana(tecnica)+fecha+turno y masa sin destino.

    W = s * W_global; D = s * D_global (medida) antes del Caso;
    D = TMS_PAD,turno * V_campana / V_PAD dentro de la ventana."""
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    vol = ap.loc[ap["vol_diario"].gt(0)]
    v_all = vol.groupby("fecha")["vol_diario"].sum()
    v_pad = vol.groupby(["pad_id", "fecha"])["vol_diario"].sum()
    v_grp = vol.groupby(["pad_id", "campana_id", "campana", "fecha"])["vol_diario"].sum()
    win = _tms_ventana(tms_pad)
    rows = []
    for (pad, cid, camp, fecha), v in v_grp.items():
        s = v / v_all[fecha]
        for turno in ("A", "B"):
            W = s * pg.loc[(fecha, turno), "W"]
            if start <= fecha <= end:
                if (pad, fecha) not in win.index:
                    raise rc.RecalibracionError(
                        f"Falta la TMS reconciliada distribuida del PAD {pad} para {fecha:%Y-%m-%d}")
                D = float(win.loc[(pad, fecha), "TMS_T1" if turno == "A" else "TMS_T2"]) * v / v_pad[(pad, fecha)]
                fuente = "TMS_reconciliada_PAD"
            else:
                D = s * pg.loc[(fecha, turno), "D"]
                fuente = "TMS_medida_perfil"
            rows.append(dict(pad_id=int(pad), campana_id=int(cid), campana=int(camp),
                             fecha=fecha, turno=turno, tmh=float(W), tms=float(D),
                             fuente_tms=fuente, s=float(s)))
    sup = pd.DataFrame(rows, columns=["pad_id", "campana_id", "campana", "fecha",
                                      "turno", "tmh", "tms", "fuente_tms", "s"])
    # Masa positiva en fechas sin volumen en ningun destino: se reporta (sec. 13).
    sin = []
    for (fecha, turno), r in pg.iterrows():
        if fecha not in v_all.index and fecha <= end and pd.notna(r["W"]) and r["W"] > 0:
            sin.append(dict(fecha=fecha, turno=turno, tmh=float(r["W"]),
                            tms=float(r["D"]) if pd.notna(r["D"]) else np.nan,
                            motivo="sin_volumen_destino", pad_id=np.nan,
                            campana=np.nan, campana_id=np.nan))
    return sup, pd.DataFrame(sin, columns=["fecha", "turno", "tmh", "tms", "motivo",
                                           "pad_id", "campana", "campana_id"])


# ------------------------------------------------------------- por grupo

def _fijados_del_grupo(fijados, pad, cid, end, avisos):
    """Modulos CONGELADOS utilizables al corte {modulo_id: fila}."""
    out = {}
    if fijados is None or len(fijados) == 0:
        return out
    f = fijados.copy()
    f = f.loc[(f["pad_id"].astype(int) == pad) & (f["campana_id"].astype(int) == cid)]
    if "estado_congelamiento" in f.columns:
        f = f.loc[f["estado_congelamiento"].astype(str).str.upper().eq("CONGELADO")]
    if f.duplicated("modulo_id").any():
        raise rc.RecalibracionError(
            f"Identidad duplicada entre modulos fijados (PAD {pad}, campana tecnica {cid})")
    for r in f.itertuples():
        tmh = pd.to_numeric(getattr(r, "tmh_fijada", np.nan), errors="coerce")
        fc = pd.to_datetime(getattr(r, "fecha_congelamiento", pd.NaT), errors="coerce")
        fz = pd.to_datetime(getattr(r, "fecha_conformacion", pd.NaT), errors="coerce")
        if pd.isna(fc) or not np.isfinite(tmh) or tmh <= 0 or (pd.notna(fz) and fz > end):
            avisos.append(Aviso("dato", "congelado_incompleto",
                f"Modulo {int(r.modulo_id)} CONGELADO sin TMH fijada directa o con fechas "
                "faltantes/posteriores al corte: se trata como ajustable", 1))
            continue
        if fc > end:
            continue                               # informacion posterior al corte
        out[int(r.modulo_id)] = dict(tmh=float(tmh),
            tms_conformado=pd.to_numeric(getattr(r, "tms_conformado", np.nan), errors="coerce"))
    return out


def _modulos_del_grupo(ap_g, fij):
    m = ap_g.loc[ap_g["vol_diario"].gt(0)].groupby(["modulo_id", "modulo"]).agg(
        primera_actividad=("fecha", "min"), v_real=("vol_diario", "sum")).reset_index()
    est = (ap_g.dropna(subset=["vol_total_est"]).sort_values("fecha")
           .groupby("modulo_id")["vol_total_est"].last())
    m["v_obj"] = m["modulo_id"].map(est)
    if "parcela_id" in ap_g.columns:
        m["parcela_id"] = m["modulo_id"].map(ap_g.dropna(subset=["parcela_id"])
                                              .groupby("modulo_id")["parcela_id"].first())
    else:
        m["parcela_id"] = np.nan
    m = m.sort_values(["primera_actividad", "modulo"]).reset_index(drop=True)
    m["orden"] = np.arange(len(m))
    m["fijado"] = m["modulo_id"].isin(set(fij))
    return m


def reconstituir(ap, perfil, tms_pad, start, end, *, fijados=None, modulos_cat=None,
                 tol_tms=0.01):
    """Reconstitucion completa (ver docstring del modulo).

    ``ap``: control_apilado_diario desde el nacimiento de las campanas hasta el
    corte (``end``); ``perfil``: TMH/humedad por fecha/turno/correa de esa misma
    historia; ``tms_pad``: ``fecha, pad_id, TMS_T1, TMS_T2`` de la ventana del Caso
    (TMS reconciliada F18/F19 distribuida por turno)."""
    start, end = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    ap = _norm_apilado(ap, end)
    if modulos_cat is not None and len(modulos_cat) and "parcela_id" not in ap.columns:
        ap = ap.merge(modulos_cat[["modulo_id", "parcela_id"]].drop_duplicates("modulo_id"),
                      on="modulo_id", how="left")
    avisos = []
    win_vol = ap.loc[ap["fecha"].between(start, end) & ap["vol_diario"].gt(0)]
    if win_vol.empty:
        raise rc.RecalibracionError("La ventana del Caso no tiene volumen de apilado")
    grupos = (win_vol[["pad_id", "campana_id", "campana"]].drop_duplicates()
              .sort_values(["pad_id", "campana_id"]).reset_index(drop=True))
    keep = ap.merge(grupos[["pad_id", "campana_id"]], on=["pad_id", "campana_id"])
    # historia: desde el nacimiento de cada campana evaluada
    nacim = keep.loc[keep["vol_diario"].gt(0)].groupby(["pad_id", "campana_id"])["fecha"].min()
    fechas_vol = sorted(set(ap.loc[ap["vol_diario"].gt(0) & (ap["fecha"] >= nacim.min()), "fecha"]))
    pg = perfil_global(perfil, fechas_vol, nacim.min())
    sup_all, sin_asignar = construir_suministro(
        ap.loc[ap["fecha"] >= nacim.min()], pg, tms_pad, start, end)
    sup_all = sup_all.merge(grupos, on=["pad_id", "campana_id", "campana"])
    sin_asignar["pad_id"] = sin_asignar["pad_id"].astype("float")
    asigs, residuos, mods, gsum = [], [], [], []
    for g in grupos.itertuples(index=False):
        ap_g = ap.loc[ap["pad_id"].eq(g.pad_id) & ap["campana_id"].eq(g.campana_id)]
        sup = sup_all.loc[sup_all["pad_id"].eq(g.pad_id) & sup_all["campana_id"].eq(g.campana_id)]
        fij = _fijados_del_grupo(fijados, g.pad_id, g.campana_id, end, avisos)
        mt = _modulos_del_grupo(ap_g, fij)
        ausentes = set(fij) - set(mt["modulo_id"])
        for mid in sorted(ausentes):
            avisos.append(Aviso("dato", "fijado_sin_volumen",
                f"Modulo fijado {mid} sin volumen en la historia de la campana {g.campana}: ignorado", 1))
            fij.pop(mid)
        mt["fijado"] = mt["modulo_id"].isin(set(fij))
        if mt.empty:
            continue
        w_global = float(sup["tmh"].sum())
        w_fijo = float(sum(v["tmh"] for v in fij.values()))
        v_aj = float(mt.loc[~mt["fijado"], "v_real"].sum())
        rho = rc.densidad_recalibrada(w_global, w_fijo, v_aj)
        abierto_id = mt["modulo_id"].iloc[-1] if not bool(mt["fijado"].iloc[-1]) else None
        mt["abierto"] = mt["modulo_id"].eq(abierto_id)
        meta = rc.metas_humedas(rho, mt["v_obj"]).to_numpy(float)
        mt["meta_tmh"] = np.where(mt["fijado"], mt["modulo_id"].map(lambda i: fij.get(i, {}).get("tmh", np.nan)), meta)
        mt["meta_tmh"] = np.where(mt["abierto"], np.nan, mt["meta_tmh"])
        if rho is None and (~mt["fijado"]).any():
            raise rc.RecalibracionError("densidad no definida con modulos ajustables")
        turnos = sup[["fecha", "turno", "tmh", "tms"]]
        a, r, res = rc.asignar_secuencial(
            turnos, mt.assign(clave=mt["modulo_id"])[["clave", "meta_tmh", "abierto"]])
        rc.conservacion_por_turno(turnos, a, r, exigir=True)
        rc.verificar_fijados(res, {i: v["tmh"] for i, v in fij.items()}, tol_tms=tol_tms,
                             tms_conformado={i: v["tms_conformado"] for i, v in fij.items()})
        res = res.rename(columns={"clave": "modulo_id", "tmh_asignada": "tmh_hasta_corte",
                                  "tms_asignada": "tms_hasta_corte"})
        mt = mt.drop(columns=["meta_tmh", "abierto"]).merge(
            res[["modulo_id", "meta_tmh", "abierto", "cierra", "fraccion_traspaso",
                 "tmh_hasta_corte", "tms_hasta_corte"]], on="modulo_id")
        mt["pad_id"], mt["campana_id"], mt["campana"] = g.pad_id, g.campana_id, g.campana
        mt["rho_h"] = rho
        a = a.rename(columns={"clave": "modulo_id"})
        a["pad_id"], a["campana_id"], a["campana"] = g.pad_id, g.campana_id, g.campana
        a = a.merge(mt[["modulo_id", "modulo"]], on="modulo_id")
        if len(r):
            r = r.assign(pad_id=g.pad_id, campana_id=g.campana_id, campana=g.campana)
            residuos.append(r)
        asigs.append(a)
        mods.append(mt)
        gsum.append(dict(pad_id=g.pad_id, campana_id=g.campana_id, campana=g.campana,
                         nacimiento=nacim[(g.pad_id, g.campana_id)],
                         w_global_campana=w_global, w_fijo=w_fijo, v_ajustable=v_aj,
                         rho_h=rho, n_modulos=len(mt), n_fijados=int(mt["fijado"].sum()),
                         tmh_sin_asignar=float(r["tmh"].sum()) if len(r) else 0.0))
    asig_hist = pd.concat(asigs, ignore_index=True)
    modulos = pd.concat(mods, ignore_index=True)
    grupos_df = pd.DataFrame(gsum)
    resid_df = pd.concat(residuos + [sin_asignar.assign(campana_id=sin_asignar["campana_id"])]
                         if residuos else [sin_asignar], ignore_index=True)
    resid_df = resid_df.loc[resid_df["fecha"] <= end]

    asig = asig_hist.loc[asig_hist["fecha"].between(start, end)].reset_index(drop=True)
    asig = _con_horas(asig, sup_all, pg)
    st = _shift_table(asig, ap, sup_all, pg, tms_pad, modulos, start, end)
    timeline = _timeline(asig)
    # TMS/TMH de la ventana por modulo (para informe)
    ven = asig.groupby(["pad_id", "campana_id", "modulo_id"]).agg(
        tmh_ventana=("tmh", "sum"), tms_ventana=("tms", lambda s: s.sum(min_count=1))).reset_index()
    modulos = modulos.merge(ven, on=["pad_id", "campana_id", "modulo_id"], how="left")
    for c in ("tmh_ventana", "tms_ventana"):
        modulos[c] = modulos[c].fillna(0.0)
    modulos["densidad_usada"] = modulos["rho_h"]
    return dict(shift_table=st, asignaciones=asig, asignaciones_historia=asig_hist,
                sin_asignar=resid_df.reset_index(drop=True), grupos=grupos_df,
                modulos=modulos, timeline=timeline, suministro=sup_all,
                perfil_global=pg, avisos=avisos)


# ----------------------------------------------------------- presentacion

def _con_horas(asig, sup, pg):
    """Hora estimada de cada tramo: t0 + 12 h * W_acum_en_turno / W_turno (sec. 12).

    Varios PAD/campanas en un mismo turno ocupan tramos consecutivos del turno
    (orden PAD, campana), proporcionales a su TMH: supuesto declarado."""
    a = asig.copy()
    if a.empty:
        a["inicio_est"] = pd.NaT
        a["fin_est"] = pd.NaT
        return a
    sup_t = sup.groupby(["fecha", "turno", "pad_id", "campana_id"])["tmh"].sum().reset_index()
    sup_t = sup_t.sort_values(["fecha", "turno", "pad_id", "campana_id"])
    sup_t["offset"] = sup_t.groupby(["fecha", "turno"])["tmh"].cumsum() - sup_t["tmh"]
    a = a.merge(sup_t[["fecha", "turno", "pad_id", "campana_id", "offset"]],
                on=["fecha", "turno", "pad_id", "campana_id"], how="left")
    wturn = a.apply(lambda r: pg.loc[(r["fecha"], r["turno"]), "W"], axis=1)
    t0 = a["fecha"] + pd.to_timedelta(np.where(a["turno"].eq("A"), 8, 20), unit="h")
    a["inicio_est"] = t0 + pd.to_timedelta(12 * (a["offset"] + a["tmh_ini_turno"]) / wturn, unit="h")
    a["fin_est"] = t0 + pd.to_timedelta(12 * (a["offset"] + a["tmh_fin_turno"]) / wturn, unit="h")
    return a.drop(columns=["offset"])


def _timeline(asig):
    if asig.empty:
        return pd.DataFrame(columns=TIMELINE_COLS)
    a = asig.loc[asig["tmh"].gt(0)]
    t = a.groupby(["pad_id", "campana", "modulo", "fecha"]).agg(
        start=("inicio_est", "min"), end=("fin_est", "max"), mass_h=("tmh", "sum"),
        mass_dry=("tms", lambda s: s.sum(min_count=1))).reset_index()
    t["origen"] = ORIGEN_HORARIO
    t["resolucion"] = RESOLUCION_HORARIA
    return t[TIMELINE_COLS].sort_values(["pad_id", "campana", "start", "modulo"]).reset_index(drop=True)


def _shift_table(asig, ap, sup, pg, tms_pad, modulos, start, end):
    key = ["pad_id", "campana_id", "campana", "modulo_id", "modulo", "fecha"]
    a = asig.copy()
    wide = None
    for t, label in ((1, "A"), (2, "B")):
        sub = a.loc[a["turno"].eq(label)].groupby(key).agg(
            **{f"tmh_turno{t}": ("tmh", "sum"),
               f"masa_turno{t}": ("tms", lambda s: s.sum(min_count=1)),
               f"frac_turno{t}": ("fraccion_turno", "sum")}).reset_index()
        wide = sub if wide is None else wide.merge(sub, on=key, how="outer")
    for c in ("tmh_turno1", "tmh_turno2", "masa_turno1", "masa_turno2", "frac_turno1", "frac_turno2"):
        if c not in wide.columns:
            wide[c] = np.nan
    wide[["tmh_turno1", "tmh_turno2", "frac_turno1", "frac_turno2"]] = \
        wide[["tmh_turno1", "tmh_turno2", "frac_turno1", "frac_turno2"]].fillna(0.0)
    # TMS: sin asignacion en el turno => cero explicito; TMS ausente (NaN) se conserva
    # solo cuando el turno recibio TMH con TMS desconocida.
    for t in (1, 2):
        wide[f"masa_turno{t}"] = wide[f"masa_turno{t}"].where(
            wide[f"tmh_turno{t}"].gt(0), 0.0)
    day_w = sup.groupby(["pad_id", "campana_id", "fecha"])["tmh"].sum().rename("w_dia_grupo")
    wa = sup.loc[sup["turno"].eq("A")].groupby(["pad_id", "campana_id", "fecha"])["tmh"].sum().rename("w_A")
    off = a.merge(wa.reset_index(), on=["pad_id", "campana_id", "fecha"], how="left")
    off["w_A"] = off["w_A"].fillna(0.0)
    off["d0"] = np.where(off["turno"].eq("B"), off["w_A"], 0.0) + off["tmh_ini_turno"]
    off["d1"] = off["d0"] + off["tmh"]
    cum = off.groupby(key).agg(d0=("d0", "min"), d1=("d1", "max")).reset_index()
    wide = wide.merge(cum, on=key, how="left").merge(day_w.reset_index(),
                      on=["pad_id", "campana_id", "fecha"], how="left")
    wide["cum_ini"] = wide["d0"] / wide["w_dia_grupo"]
    wide["cum_fin"] = wide["d1"] / wide["w_dia_grupo"]
    wide["asignado"] = True

    vol = ap.loc[ap["fecha"].between(start, end) & ap["vol_diario"].gt(0)].merge(
        asig[["pad_id", "campana_id"]].drop_duplicates(), on=["pad_id", "campana_id"])
    vcols = key + ["vol_diario", "avance"]
    vol = vol[vcols]
    st = vol.merge(wide, on=key, how="outer")
    st["fila_volumetrica"] = st["vol_diario"].notna()
    st["vol_diario"] = st["vol_diario"].fillna(0.0)
    # avance de filas sin volumen: ultimo conocido (informativo)
    # Volumen con asignacion calculada cero => cero explicito (no ausente):
    for c in ("tmh_turno1", "tmh_turno2", "masa_turno1", "masa_turno2", "frac_turno1", "frac_turno2"):
        st.loc[st["asignado"].isna(), c] = 0.0
    st["asignado"] = st["asignado"].fillna(False).astype(bool)
    st["tmh_total"] = st["tmh_turno1"] + st["tmh_turno2"]
    st["masa_total"] = st["masa_turno1"] + st["masa_turno2"]
    st["cruza_turno"] = st["tmh_turno1"].gt(0) & st["tmh_turno2"].gt(0)
    st["medido_en"] = st["fecha"] + pd.Timedelta(days=1, hours=8)
    st["turno1_ini"] = st["fecha"] + pd.Timedelta(hours=8)
    st["turno2_ini"] = st["fecha"] + pd.Timedelta(hours=20)
    # Columnas globales del dia (como el motor de flujos)
    tms_d = tms_pad.copy()
    tms_d["fecha"] = pd.to_datetime(tms_d["fecha"]).dt.normalize()
    tms_day = tms_d.groupby("fecha")[["TMS_T1", "TMS_T2"]].sum()
    tmh_day = pg.reset_index().groupby("fecha")["W"].sum()
    st["TMS_dia"] = st["fecha"].map(tms_day["TMS_T1"] + tms_day["TMS_T2"])
    st["masa_dia"] = st["TMS_dia"]
    st["TMH_dia"] = st["fecha"].map(tmh_day)
    pad_split = tms_d.set_index(["pad_id", "fecha"])
    t1 = pd.Series([pad_split["TMS_T1"].get((p, f), np.nan) for p, f in zip(st.pad_id, st.fecha)], index=st.index)
    t2 = pd.Series([pad_split["TMS_T2"].get((p, f), np.nan) for p, f in zip(st.pad_id, st.fecha)], index=st.index)
    st["boundary"] = (t1 / (t1 + t2)).where((t1 + t2).gt(0), 0.0)
    st["boundary_medida"] = False
    st["boundary_disponible"] = True
    st["boundary_normalizada"] = True
    st["frontera_tipo"] = "distribuida_del_caso"
    st["boundary_src"] = "masa"
    st["fuente_masa"] = FUENTE_MASA
    st["metodo_reconstitucion"] = METODO
    st["H_op"] = np.nan
    st["H_op_src"] = "n/d"
    st["turnos_ok"] = st["tmh_turno1"].gt(0) & st["tmh_turno2"].gt(0)
    act = ap.loc[ap["fecha"].between(start, end) & ap["vol_diario"].gt(0)]
    st["vol_dia_total"] = st["fecha"].map(act.groupby("fecha")["vol_diario"].sum())
    st["n_modulos_dia"] = st["fecha"].map(act.groupby("fecha").size())
    st["frac_vol"] = st["vol_diario"] / st["vol_dia_total"]
    st["densidad"] = (st["masa_total"] / st["vol_diario"]).where(st["vol_diario"].gt(0))
    st["densidad_h"] = (st["tmh_total"] / st["vol_diario"]).where(st["vol_diario"].gt(0))
    st["con_masa"] = st["masa_total"].notna()
    st["vol_con_masa"] = st["vol_diario"].where(st["con_masa"], 0.0)
    # Avance: el de la fila de volumen; sin ella, el ultimo del modulo hasta ese dia
    av = ap.sort_values("fecha")[["pad_id", "campana_id", "modulo_id", "fecha", "avance"]]
    last = {}
    for r in av.itertuples():
        last.setdefault((r.pad_id, r.campana_id, r.modulo_id), []).append((r.fecha, r.avance))
    def _avance(r):
        if pd.notna(r["avance"]):
            return r["avance"]
        hist = [x for f, x in last.get((r.pad_id, r.campana_id, r.modulo_id), []) if f <= r["fecha"] and pd.notna(x)]
        return hist[-1] if hist else np.nan
    st["avance"] = st.apply(_avance, axis=1)
    mm = modulos[["pad_id", "campana_id", "modulo_id", "meta_tmh", "rho_h", "fraccion_traspaso",
                  "fijado", "abierto"]].rename(columns={"rho_h": "rho_h_campana",
                  "fraccion_traspaso": "fraccion_traspaso_modulo", "fijado": "modulo_fijado",
                  "abierto": "modulo_abierto"})
    st = st.merge(mm, on=["pad_id", "campana_id", "modulo_id"], how="left")
    return st.drop(columns=["d0", "d1", "w_dia_grupo"]).sort_values(
        ["fecha", "pad_id", "campana", "cum_ini", "modulo"]).reset_index(drop=True)
