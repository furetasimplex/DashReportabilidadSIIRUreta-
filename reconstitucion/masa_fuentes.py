"""Fuentes de masa del reparto secuencial.

    oficial  la que usa el dash. Por fecha y sin mezclar fuentes dentro de un dia: 1) Datos_conciliados_of_ver,
             2) si falta y la fecha es anterior a la puesta en marcha (puesta_en_marcha.json), el libro Excel oficial (CSV versionado,
             generado por auditorias/validacion_excel_db_20261106/extraer_apilado_libros.py), 3) ausencia con
             excepcion. Nunca lee Datos_conciliados_of. Los libros entran por el CSV, sin escrituras en SQL.
    of       testeo, solo por seleccion explicita y con aviso visible: Datos_conciliados_of, para comparar con los libros.

El libro ya trae la masa por PAD y campana: va directo, no se reparte por volumen.
"""
from __future__ import annotations

from pathlib import Path

import json

import numpy as np
import pandas as pd

FUENTES_MASA = ("oficial", "of")
LIBROS_CSV = Path(__file__).resolve().parent / "datos_oficiales" / "apilado_libros.csv"
RUTA_PUESTA_EN_MARCHA = Path(__file__).resolve().parent / "datos_oficiales" / "puesta_en_marcha.json"
RTOL = 1e-6


def inicio_metodo_digital(ruta=None):
    """Fecha de puesta en marcha oficial del metodo digital, leida del archivo versionado.

    Sin valor por defecto: archivo ausente, JSON invalido o fecha invalida son un error claro.
    """
    ruta = Path(ruta or RUTA_PUESTA_EN_MARCHA)
    try:
        crudo = json.loads(ruta.read_text(encoding="utf8"))
        fecha = pd.Timestamp(crudo["fecha"])
        if pd.isna(fecha):
            raise ValueError("fecha vacia")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Falta o es invalida la fecha de puesta en marcha en {ruta.name} "
                         f"(se espera {{\"fecha\": \"AAAA-MM-DD\"}}): {exc}") from exc
    return fecha.normalize()


def load_libros(path=None):
    df = pd.read_csv(path or LIBROS_CSV, parse_dates=["fecha"])
    for col in ("tmh_a", "tmh_b", "tms_a", "tms_b"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _distinto(a, b):
    return not np.isclose(a, b, rtol=RTOL, atol=1e-6)


def combinar_ver_libro(ver, libros, start, cutoff, inicio=None):
    """Devuelve (masa por fecha con trazabilidad, excepciones de fuente)."""
    start, cutoff = pd.Timestamp(start).normalize(), pd.Timestamp(cutoff).normalize()
    ver = pd.DataFrame(ver).copy()
    if ver.empty:
        ver = pd.DataFrame(columns=["fecha", "etiqueta", "tmh_a", "tmh_b", "tms", "caso_id"])
    ver["fecha"] = pd.to_datetime(ver.fecha).dt.normalize()
    ver["pad_id"], ver["campana"], ver["tms_a"], ver["tms_b"] = np.nan, np.nan, np.nan, np.nan
    ver["fuente"] = "VER"
    excepciones = []
    lib = libros.loc[libros.fecha.between(start, min(cutoff, (inicio if inicio is not None else inicio_metodo_digital()) - pd.Timedelta(days=1)))].copy()
    # Dos libros con la misma fecha y PAD: si difieren no se elige; el dia queda sin libro.
    validos, ignorar = [], set()
    for (dia, pad), g in lib.groupby(["fecha", "pad_id"]):
        if len(g) > 1:
            t = g[["tmh_a", "tmh_b", "tms_a", "tms_b"]].fillna(0.0).to_numpy()
            if any(_distinto(t[0, j], t[i, j]) for i in range(1, len(t)) for j in range(4)):
                excepciones.append(dict(fecha=dia, tipo="LIBROS_EN_CONFLICTO", tmh=float(t[:, 0].sum() + t[:, 1].sum()), tms=0.0,
                    detalle=f"PAD {pad}: {', '.join(g.libro)} traen valores distintos; el dia queda sin masa de libro."))
                ignorar.add((dia, pad))
                continue
        validos.append(g.iloc[0])
    lib = pd.DataFrame(validos) if validos else lib.iloc[0:0]
    lib = lib.loc[[(d, p) not in ignorar for d, p in zip(lib.fecha, lib.pad_id)]] if len(lib) else lib
    en_ver = ver.set_index("fecha")
    filas = []
    for dia, g in lib.groupby("fecha"):
        if dia in en_ver.index:
            v = en_ver.loc[[dia]]
            tmh_v = float(v.tmh_a.fillna(0).sum() + v.tmh_b.fillna(0).sum())
            tms_v = float(v.tms.fillna(0).sum())
            tmh_l = float(g.tmh_a.fillna(0).sum() + g.tmh_b.fillna(0).sum())
            tms_l = float(g.tms_a.fillna(0).sum() + g.tms_b.fillna(0).sum())
            if _distinto(tmh_v, tmh_l) or _distinto(tms_v, tms_l):
                excepciones.append(dict(fecha=dia, tipo="LIBRO_DIFIERE_DE_VER", tmh=tmh_v, tms=tms_v,
                    detalle=f"ver gana. TMH ver {tmh_v:.1f} libro {tmh_l:.1f} (dif {tmh_v - tmh_l:+.1f}); "
                            f"TMS ver {tms_v:.1f} libro {tms_l:.1f} (dif {tms_v - tms_l:+.1f})."))
            continue
        for r in g.itertuples(index=False):
            filas.append(dict(fecha=dia, etiqueta="", tmh_a=r.tmh_a, tmh_b=r.tmh_b,
                              tms=np.nansum([r.tms_a, r.tms_b]) if np.isfinite([r.tms_a, r.tms_b]).any() else np.nan,
                              caso_id=np.nan, pad_id=float(r.pad_id), campana=float(r.campana),
                              tms_a=r.tms_a, tms_b=r.tms_b, fuente="LIBRO_EXCEL"))
    out = pd.concat([ver, pd.DataFrame(filas, columns=ver.columns)], ignore_index=True)
    out = out.sort_values(["fecha", "fuente"]).reset_index(drop=True)
    exc = pd.DataFrame(excepciones, columns=["fecha", "tipo", "tmh", "tms", "detalle"])
    return out, exc
