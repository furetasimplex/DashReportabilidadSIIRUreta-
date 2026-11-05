"""Nucleo puro de la reconstitucion por densidad humeda recalibrada.

Implementa docs/METODOLOGIA_RECONSTITUCION_DENSIDAD_RECALIBRADA.md:

    * Seccion 8: ``densidad_recalibrada`` (casos particulares explicados).
    * Seccion 9: ``metas_humedas`` (W_obj = rho_h * V_obj).
    * Seccion 10: ``asignar_secuencial`` (llena la meta de un modulo y el
      residual pasa al siguiente DENTRO del mismo turno; la TMS sigue la
      fraccion f de la TMH).
    * Seccion 13: ceros, ausencias y residual no asignable.
    * Seccion 14: ``conservacion_por_turno`` (invariante de conservacion).

No hace E/S ni importa SQL. Todo recibe y devuelve DataFrames o escalares.
"""
from __future__ import annotations

import math
from typing import Hashable, Optional

import numpy as np
import pandas as pd

TOL_REL = 1e-9     # tolerancia relativa de balance de masa
TOL_ABS = 1e-6     # tolerancia absoluta (t) de balance de masa

TURNOS = ("A", "B")


class RecalibracionError(ValueError):
    """Error de balance, identidad o datos de la recalibracion.

    El mensaje explica la causa; nunca se corrige el resultado en silencio."""


def _finito(valor, nombre, *, no_negativo=True):
    try:
        x = float(valor)
    except (TypeError, ValueError):
        raise RecalibracionError(f"{nombre} no es numerico: {valor!r}")
    if not math.isfinite(x):
        raise RecalibracionError(f"{nombre} ausente o no finito")
    if no_negativo and x < 0:
        raise RecalibracionError(f"{nombre} negativo ({x})")
    return x


def _tol(*valores, tol_rel=TOL_REL, tol_abs=TOL_ABS):
    return max(tol_abs, tol_rel * max([abs(float(v)) for v in valores] + [0.0]))


# --------------------------------------------------------------------------
# Seccion 8: densidad humeda recalibrada
# --------------------------------------------------------------------------

def densidad_recalibrada(w_global_campana, w_fijada, v_ajustable, *,
                         tol_rel=TOL_REL, tol_abs=TOL_ABS) -> Optional[float]:
    """rho_h = (W_global,campana - W_fijo) / V_ajustable  [TMH/m3].

    Casos particulares (seccion 8):

    * Sin modulos fijados (``w_fijada`` = 0): se calibra con toda la masa.
    * Todos fijados (``v_ajustable`` = 0) y el balance cierra: devuelve
      ``None`` (no hace falta una densidad nueva).
    * Masa fijada mayor que la global: ``RecalibracionError`` (balance o
      identidad).
    * Masa por asignar positiva y volumen ajustable nulo: ``RecalibracionError``;
      no se inventa una densidad.
    * Masa global explicitamente cero: devuelve 0.0 (se conserva el cero; no se
      crea material).
    """
    wg = _finito(w_global_campana, "TMH global de la campana")
    wf = _finito(w_fijada, "TMH fijada")
    va = _finito(v_ajustable, "volumen ajustable")
    tol = _tol(wg, wf, tol_rel=tol_rel, tol_abs=tol_abs)
    if wf > wg + tol:
        raise RecalibracionError(
            f"Masa fijada ({wf:,.3f} TMH) mayor que la masa global de la campana "
            f"({wg:,.3f} TMH): error de balance o de identidad de modulos fijados")
    por_asignar = max(wg - wf, 0.0)
    if por_asignar <= tol:
        por_asignar = 0.0
    if wg == 0.0:
        return 0.0
    if va <= 0.0:
        if por_asignar == 0.0:
            return None
        raise RecalibracionError(
            f"Quedan {por_asignar:,.3f} TMH por asignar y el volumen ajustable es "
            "nulo: no se inventa una densidad")
    return por_asignar / va


def metas_humedas(rho_h, v_objetivo) -> pd.Series:
    """W_obj = rho_h * V_obj por modulo (seccion 9). ``NaN`` si falta el V_obj.

    ``rho_h`` None (todos fijados) devuelve NaN: no hay metas ajustables."""
    v = pd.to_numeric(pd.Series(v_objetivo), errors="coerce").astype(float)
    if rho_h is None:
        return v * np.nan
    rho = _finito(rho_h, "densidad humeda")
    return v * rho


# --------------------------------------------------------------------------
# Seccion 10: asignacion secuencial por turno
# --------------------------------------------------------------------------

COLS_ASIG = ["fecha", "turno", "clave", "orden", "tmh", "tms", "fraccion_turno",
             "w_turno", "d_turno", "tmh_ini_turno", "tmh_fin_turno", "cierra"]


def _frame_turnos(turnos) -> pd.DataFrame:
    t = turnos.copy()
    falta = {"fecha", "turno", "tmh", "tms"} - set(t.columns)
    if falta:
        raise RecalibracionError(f"turnos requiere columnas {sorted(falta)}")
    t["fecha"] = pd.to_datetime(t["fecha"]).dt.normalize()
    t["turno"] = t["turno"].astype(str).str.upper()
    if not t["turno"].isin(TURNOS).all():
        raise RecalibracionError("turno distinto de A/B")
    if t.duplicated(["fecha", "turno"]).any():
        raise RecalibracionError("suministro repite fecha y turno")
    return t.sort_values(["fecha", "turno"]).reset_index(drop=True)


def asignar_secuencial(turnos: pd.DataFrame, modulos: pd.DataFrame, *,
                       tol_rel=TOL_REL, tol_abs=TOL_ABS):
    """Asigna el suministro por turno a los modulos en secuencia.

    ``turnos``: columnas ``fecha``, ``turno`` (A/B), ``tmh``, ``tms`` (TMS puede
        ser NaN cuando la TMH positiva no tiene humedad valida: la TMS no se
        inventa, se propaga ausente).
    ``modulos``: en orden operacional; columnas ``clave`` (hashable unico),
        ``meta_tmh`` (TMH objetivo; ignorada para el abierto), ``previo_tmh``
        (opcional, TMH ya acumulada), ``abierto`` (opcional: solo el ULTIMO
        puede serlo; recibe el residual sin meta futura).

    Para cada turno y cada modulo con capacidad (seccion 10)::

        P = max(0, meta - previo)        W_m = min(P, W_restante)
        f = W_m / W_restante             D_m = f * D_restante

    se descuentan ambas masas y el residual pasa al siguiente modulo en el
    mismo turno. Lo que ninguna meta puede recibir se devuelve en ``residual``
    (seccion 13); no desaparece.

    Devuelve ``(asignaciones, residual, resumen)``.
    """
    t = _frame_turnos(turnos)
    m = modulos.reset_index(drop=True).copy()
    if "clave" not in m.columns:
        raise RecalibracionError("modulos requiere la columna 'clave'")
    if m["clave"].duplicated().any():
        raise RecalibracionError("identidad de modulo duplicada: se detiene la asignacion")
    if "previo_tmh" not in m.columns:
        m["previo_tmh"] = 0.0
    if "abierto" not in m.columns:
        m["abierto"] = False
    m["abierto"] = m["abierto"].fillna(False).astype(bool)
    n = len(m)
    if m["abierto"].any() and not m["abierto"].iloc[:-1].eq(False).all():
        raise RecalibracionError("solo el ultimo modulo de la secuencia puede estar abierto")
    meta = pd.to_numeric(m["meta_tmh"], errors="coerce").to_numpy(float).copy() \
        if "meta_tmh" in m.columns else np.full(n, np.nan)
    abierto = m["abierto"].to_numpy(bool)
    acum = pd.to_numeric(m["previo_tmh"], errors="coerce").fillna(0.0).to_numpy(float).copy()
    previo = acum.copy()
    if (acum < 0).any():
        raise RecalibracionError("TMH previa negativa")
    for i in range(n):
        if not abierto[i] and not np.isfinite(meta[i]):
            raise RecalibracionError(
                f"El modulo {m['clave'].iloc[i]!r} no tiene meta TMH utilizable "
                "(falta volumen objetivo o densidad); no se inventa")
        if not abierto[i] and meta[i] < 0:
            raise RecalibracionError(f"Meta TMH negativa en {m['clave'].iloc[i]!r}")

    rows, residuos = [], []
    cerrado = np.array([(not abierto[i]) and (meta[i] - acum[i] <= 0.0)
                        for i in range(n)], bool)
    idx = 0
    for tr in t.itertuples(index=False):
        W = _finito(tr.tmh, f"TMH del turno {tr.fecha:%Y-%m-%d}/{tr.turno}")
        D = float(tr.tms) if tr.tms is not None else float("nan")
        if np.isfinite(D) and D < 0:
            raise RecalibracionError(f"TMS negativa en {tr.fecha:%Y-%m-%d}/{tr.turno}")
        if W == 0.0:
            if np.isfinite(D) and D > 0:
                raise RecalibracionError(
                    f"TMS positiva con TMH cero en {tr.fecha:%Y-%m-%d}/{tr.turno}")
            continue                      # cero explicito: se conserva cero
        Wrem, Drem, cum, orden = W, D, 0.0, 0
        while Wrem > 0.0:
            while idx < n and cerrado[idx]:
                idx += 1
            if idx >= n:
                residuos.append(dict(fecha=tr.fecha, turno=tr.turno, tmh=Wrem,
                                     tms=Drem, motivo="metas_agotadas"))
                break
            if abierto[idx]:
                take, cierra = Wrem, False
            else:
                P = max(0.0, meta[idx] - acum[idx])
                take = min(P, Wrem)
                cierra = take >= P
            f = take / Wrem
            dpart = f * Drem
            if take > 0.0 or cierra:
                orden += 1
                rows.append(dict(
                    fecha=tr.fecha, turno=tr.turno, clave=m["clave"].iloc[idx],
                    orden=orden, tmh=take, tms=dpart, fraccion_turno=take / W,
                    w_turno=W, d_turno=D, tmh_ini_turno=cum, tmh_fin_turno=cum + take,
                    cierra=bool(cierra and take > 0.0)))
            cum += take
            Wrem = Wrem - take
            Drem = Drem - dpart if np.isfinite(Drem) else Drem
            if cierra:
                acum[idx] = meta[idx]
                cerrado[idx] = True
            else:
                acum[idx] += take
            if take == 0.0 and not cierra:      # no puede ocurrir; evita bucle
                raise RecalibracionError("asignacion sin avance")
    asig = pd.DataFrame(rows, columns=COLS_ASIG)
    resid = pd.DataFrame(residuos, columns=["fecha", "turno", "tmh", "tms", "motivo"])
    resumen = _resumen_modulos(m, asig, acum, meta, abierto, previo)
    return asig, resid, resumen


def _resumen_modulos(m, asig, acum, meta, abierto, previo) -> pd.DataFrame:
    """Una fila por modulo: TMH/TMS asignadas, cierre y fraccion S (traspaso).

    ``fraccion_traspaso`` es la fraccion f del turno de cierre que queda en el
    modulo (columna S del Control M&R); 1.0 para el ultimo modulo abierto."""
    out = []
    for i, clave in enumerate(m["clave"]):
        a = asig.loc[asig["clave"] == clave] if len(asig) else asig
        if len(a):
            tms = a["tms"].sum(min_count=1)
            ultimo = a.sort_values(["fecha", "turno", "orden"]).iloc[-1]
            if abierto[i]:
                s = 1.0
            elif bool(a["cierra"].any()):
                s = float(a.loc[a["cierra"]].sort_values(["fecha", "turno", "orden"])
                          .iloc[-1]["fraccion_turno"])
            else:
                s = float(ultimo["fraccion_turno"])
            out.append(dict(clave=clave, meta_tmh=None if abierto[i] else meta[i],
                            previo_tmh=float(previo[i]),
                            tmh_asignada=float(a["tmh"].sum()), tms_asignada=tms,
                            acumulado_tmh=float(acum[i]),
                            cierra=bool(a["cierra"].any()), abierto=bool(abierto[i]),
                            fraccion_traspaso=s,
                            ultimo_turno=(ultimo["fecha"], ultimo["turno"])))
        else:
            out.append(dict(clave=clave, meta_tmh=None if abierto[i] else meta[i],
                            previo_tmh=float(previo[i]),
                            tmh_asignada=0.0, tms_asignada=np.nan,
                            acumulado_tmh=float(acum[i]), cierra=False,
                            abierto=bool(abierto[i]),
                            fraccion_traspaso=1.0 if abierto[i] else np.nan,
                            ultimo_turno=None))
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# Seccion 14: invariantes
# --------------------------------------------------------------------------

def conservacion_por_turno(turnos, asig, residual=None, *,
                           tol_rel=TOL_REL, tol_abs=TOL_ABS, exigir=False):
    """sum_m W_m,t + residual = W_t  y  sum_m D_m,t + residual = D_t.

    Devuelve un DataFrame por (fecha, turno) con los errores absolutos. Con
    ``exigir=True`` levanta ``RecalibracionError`` si algun turno excede la
    tolerancia (nunca se fuerza a cero)."""
    t = _frame_turnos(turnos)
    out = t.set_index(["fecha", "turno"])
    for src, pref, nombre in ((asig, "asig", "a"), (residual, "res", "r")):
        if src is not None and len(src):
            g = src.groupby(["fecha", "turno"]).agg(
                tmh_=("tmh", "sum"), tms_=("tms", lambda s: s.sum(min_count=1)))
            out[f"tmh_{pref}"] = g["tmh_"].reindex(out.index)
            out[f"tms_{pref}"] = g["tms_"].reindex(out.index)
        else:
            out[f"tmh_{pref}"] = 0.0
            out[f"tms_{pref}"] = 0.0
    for c in ("tmh_asig", "tms_asig", "tmh_res", "tms_res"):
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    out["err_tmh"] = (out["tmh_asig"] + out["tmh_res"] - out["tmh"]).abs()
    d_conocida = out["tms"].notna()
    out["err_tms"] = ((out["tms_asig"] + out["tms_res"] - out["tms"]).abs()
                      .where(d_conocida, 0.0))
    out["tol"] = [_tol(x, tol_rel=tol_rel, tol_abs=tol_abs) for x in out["tmh"]]
    out["ok"] = (out["err_tmh"] <= out["tol"]) & (out["err_tms"] <= out["tol"])
    if exigir and not out["ok"].all():
        mal = out.loc[~out["ok"]].reset_index().iloc[0]
        raise RecalibracionError(
            f"No se conserva la masa del turno {mal['fecha']:%Y-%m-%d}/{mal['turno']} "
            f"(error TMH {mal['err_tmh']:.3e}, TMS {mal['err_tms']:.3e})")
    return out.reset_index()


def verificar_fijados(resumen: pd.DataFrame, fijados: dict, *, tol_rel=TOL_REL,
                      tol_abs=TOL_ABS, tol_tms=0.01, tms_conformado: Optional[dict] = None):
    """Los modulos fijados conservan su TMH directa (seccion 7).

    ``fijados`` {clave: TMH fijada}. Si la secuencia no alcanzo a cubrirlos, o
    si su TMS asignada contradice la TMS conformada (tolerancia relativa
    ``tol_tms``), se levanta ``RecalibracionError``: no se corrige en silencio."""
    for clave, w in fijados.items():
        fila = resumen.loc[resumen["clave"] == clave]
        asignada = (float(fila["previo_tmh"].iloc[0]) + float(fila["tmh_asignada"].iloc[0])
                    if len(fila) else 0.0)
        if abs(asignada - w) > _tol(w, tol_rel=tol_rel, tol_abs=tol_abs):
            raise RecalibracionError(
                f"Modulo fijado {clave!r}: la secuencia le asigna {asignada:,.3f} TMH "
                f"y su TMH fijada directa es {w:,.3f}; incompatible con el suministro")
        if tms_conformado and clave in tms_conformado and pd.notna(tms_conformado[clave]):
            tms = float(fila["tms_asignada"].iloc[0])
            ref = float(tms_conformado[clave])
            if np.isfinite(tms) and abs(tms - ref) > tol_tms * max(abs(ref), 1.0):
                raise RecalibracionError(
                    f"Modulo fijado {clave!r}: TMS asignada {tms:,.3f} contra TMS "
                    f"conformada {ref:,.3f} (> {tol_tms:.1%}); resultado bloqueado")
