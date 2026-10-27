"""Informe MODULOS desde el resultado del Caso del modelo 125.
Conserva encabezados y formato del informe existente. La masa procede
de la asignacion del motor; calidad ponderada por TMS de modulo/turno.
Campos sin fuente quedan vacios. No ejecuta procedimientos almacenados.
OX y SU identifican pads; no representan mineralogias distintas.
"""
from sqlalchemy import text
from io import BytesIO
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from openpyxl.cell.cell import MergedCell
from openpyxl.utils import get_column_letter

from . import db_source as dbs

PAD = dbs.PAD_SULFUROS     # 2; el otro informe es el del pad 1, de oxidos

# Cada pad tiene su informe: su campana en curso, su forma de agrupar modulos
# en parcelas y su plantilla. Sulfuros agrupa de a cinco modulos y oxidos de a
# dos (verificado contra las dos publicaciones, sin excepciones).
MODULOS_POR_PARCELA = {dbs.PAD_SULFUROS: 5, dbs.PAD_OXIDOS: 2}

COLS_INFORME = ["campana", "parcela", "modulo", "fecha_fin_carguio", "TMH",
                "TMS", "frac_oxidos", "frac_sulfuros"]

# Nombre del pad en las tablas de turno: el historico lo guarda como texto en
# la columna Campania (Oxido / Sulfuro) y la cache de emision en Material
# (OXIDOS / SULFUROS).
MATERIAL_PAD = {dbs.PAD_SULFUROS: ("Sulfuro", "SULFUROS"),
                dbs.PAD_OXIDOS: ("Oxido", "OXIDOS")}

# Bloque de calidad del informe: campo del reporte de turno -> nombre nuestro.
# La fuente canonica es sp_reporte_turno_emision_test; sus campos "Real" viven,
# por tramo de fecha, en Historico_Reporte_Turno (hasta 2026-06-30) y en
# reporte_turno_cache_emision_test (desde ahi). Todos se ponderan por la masa
# seca que el modulo apilo en ese turno.
CALIDAD = {
    "FeT_Real": "FeT",                       # L
    "FeS_Real": "FeS",                       # M
    "CuT_Real": "CuT",                       # N
    "CuS_Real": "CuS",                       # O
    "CO3_Real": "CO3",                       # P
    "ConsH_Real": "consumo_H",               # R
    "Solubilidad_Real": "solubilidad",       # S, y G/H como fraccion
    "CuFe_Real": "CuFe",                     # V
    "CaolBeta_Real": "beta_clay",            # W
    "STOCK": "origen_stock",                 # X
    "MINA": "origen_mina",                   # Y
    "SRR": "origen_srr",                     # Z
    "Malla_Menos_100_Real": "malla_100",     # AG
    "Malla_Menos_1_2_Real": "malla_media",   # AH
}
ORIGEN = ["origen_stock", "origen_mina", "origen_srr"]

# Columna de la hoja MODULOS (1 = A) -> campo de la tabla. Lo que no aparece
# aca se exporta vacio porque no tiene objeto canonico en la base: Q (adicion
# real de H+), U (TC), AI (#325), AJ (limite finos), AK (Sal), AL (humedad) y
# de AM en adelante.
COLUMNAS = {
    1: "campana", 2: "parcela", 3: "modulo", 4: "fecha_fin_carguio",
    5: "TMH", 6: "TMS", 7: "frac_oxidos", 8: "frac_sulfuros",
    9: "altura_prom",
    11: "cu_fino", 12: "FeT", 13: "FeS", 14: "CuT", 15: "CuS", 16: "CO3",
    18: "consumo_H", 19: "solubilidad", 22: "CuFe", 23: "beta_clay",
    24: "origen_stock", 25: "origen_mina", 26: "origen_srr", 27: "origen_suma",
    33: "malla_100", 34: "malla_media", 38: "humedad",
}
COLS_CALIDAD = ["cu_fino"] + list(CALIDAD.values()) + ["origen_suma",
                                                       "cobertura_calidad"]

HOJA = "MODULOS"
HOJA_DETALLE = "DETALLE"
FILA_DATOS = 3            # las dos primeras filas son encabezado

# El informe publicado se usa como plantilla: se abre, se vacian las filas de
# datos de la hoja MODULOS y se escriben las nuestras encima. Asi el archivo
# sale con los mismos colores, formatos y hojas que el original. Si el archivo
# no esta, se cae al encabezado de PLANTILLA, que da la misma forma sin estilo.
# Hay una plantilla por pad: la de oxidos lleva cuatro columnas mas (tipo de
# material por tonelaje) y por eso su encabezado llega a DU y no a DP.
PLANTILLAS_XLSX = {
    dbs.PAD_SULFUROS: Path(__file__).with_name("plantilla_modulos_sulfuros.xlsx"),
    dbs.PAD_OXIDOS: Path(__file__).with_name("plantilla_modulos_oxidos.xlsx"),
}
PLANTILLA_XLSX = PLANTILLAS_XLSX[PAD]

# Encabezado completo de la hoja MODULOS del informe, columnas A:DP, en sus dos
# niveles (nombre y unidad). Las ocho primeras son las que esta base calcula;
# el resto se escribe igual, vacio, para que la hoja exportada tenga la misma
# forma que el informe publicado y se pueda completar sobre ella.
PLANTILLA = (
    ('Campaña', '#'),  # A
    ('Parcela', '#'),  # B
    ('Módulo', '#'),  # C
    ('Fecha Término Carguío', ''),  # D
    ('Mineral Humedo', 't'),  # E
    ('Mineral seco', 't'),  # F
    ('Tipo de material', 'Óxidos'),  # G
    ('', 'Sulfuros'),  # H
    ('Altura, m', 'Real'),  # I
    ('', 'Objetivo'),  # J
    ('Cobre Fino', 't'),  # K
    ('FeT', '%'),  # L
    ('FeS', '%'),  # M
    ('CuT', '%'),  # N
    ('CuS', '%'),  # O
    ('CO3', '%'),  # P
    ('Adición de H+', 'kg/t'),  # Q
    ('Consumo H+', 'kg/t'),  # R
    ('Solubilidad Real', ''),  # S
    ('Definición\n Sulfuros-Mixtos', ''),  # T
    ('TC', 'H+'),  # U
    ('CuFe', '%'),  # V
    ('Beta Clay', '%'),  # W
    ('Stock', '%'),  # X
    ('Mina', '%'),  # Y
    ('SRR', '%'),  # Z
    ('Suma', ''),  # AA
    ('Transicional', '%'),  # AB
    ('Supérgeno', '%'),  # AC
    ('Óxido', '%'),  # AD
    ('SRR', '%'),  # AE
    ('Suma', '%'),  # AF
    ('-#100', '%'),  # AG
    ('1/2"', '%'),  # AH
    ('#325', '%'),  # AI
    ('LIMITE FINOS', '%'),  # AJ
    ('Sal', 'Kg/t'),  # AK
    ('Humedad', '%'),  # AL
    ('SRR', 'SRR CuT'),  # AM
    ('', 'SRR CuS'),  # AN
    ('', 'SRR ClayBeta'),  # AO
    ('', 'SRR Malla 100'),  # AP
    ('', 'SRR CO3'),  # AQ
    ('', 'Recuperación'),  # AR
    ('csrCC', '%'),  # AS
    ('csrCV', '%'),  # AT
    ('csrCPY', '%'),  # AU
    ('CUOXI', '%'),  # AV
    ('CUINS', '%'),  # AW
    ('Total', ''),  # AX
    ('CALIDAD POR ACF', 'ACF3'),  # AY
    ('', 'ACF4'),  # AZ
    ('', 'ACF5'),  # BA
    ('', 'ACF6'),  # BB
    ('', 'ACF7'),  # BC
    ('SUMA', ''),  # BD
    ('CALIDAD POR CONTROL MINERAL', 'CALIDAD 1'),  # BE
    ('', 'CALIDAD 2'),  # BF
    ('', 'CALIDAD 3'),  # BG
    ('SUMA', ''),  # BH
    ('Recuperacion', '%'),  # BI
    ('Parcela', ''),  # BJ
    ('Mineral seco (Mina + Stock + SRR)', 't'),  # BK
    ('Cu fino', ''),  # BL
    ('% de oxidos y sulfuros ', 'oxidos'),  # BM
    ('', 'sulfuros'),  # BN
    ('Transicional', '%'),  # BO
    ('Supérgeno', '%'),  # BP
    ('Óxido', '%'),  # BQ
    ('SRR', '%'),  # BR
    ('Altura', 'm'),  # BS
    ('FeT', '%'),  # BT
    ('FeS', '%'),  # BU
    ('CuT', '%'),  # BV
    ('CuS', '%'),  # BW
    ('CuFe', '%'),  # BX
    ('CO3', '%'),  # BY
    ('Solubilidad', ''),  # BZ
    ('Stock', '%'),  # CA
    ('Mina', '%'),  # CB
    ('SRR', '%'),  # CC
    ('-#100 Ty', '%'),  # CD
    ('1/2"', '%'),  # CE
    ('Control Finos', '%'),  # CF
    ('Sal', 'kg/ton'),  # CG
    ('Humedad', '%'),  # CH
    ('csrCC', '%'),  # CI
    ('csrCV', '%'),  # CJ
    ('csrCPY', '%'),  # CK
    ('CUOXI', '%'),  # CL
    ('CUINS', '%'),  # CM
    ('', ''),  # CN
    ('CALIDAD POR UGM', 'ACF3'),  # CO
    ('', 'ACF4'),  # CP
    ('', 'ACF5'),  # CQ
    ('', 'ACF6'),  # CR
    ('', 'ACF7'),  # CS
    ('', ''),  # CT
    ('CALIDAD POR CONTROL MINERAL', 'CALIDAD 1'),  # CU
    ('', 'CALIDAD 2'),  # CV
    ('', 'CALIDAD 3'),  # CW
    ('', ''),  # CX
    ('CALIDAD RECONCILIADA', 'CALIDAD 1'),  # CY
    ('', 'CALIDAD 2'),  # CZ
    ('', 'CALIDAD 3'),  # DA
    ('', ''),  # DB
    ('Recuperación', '%'),  # DC
    ('', ''),  # DD
    ('SRR', 'CuT'),  # DE
    ('', 'CuS'),  # DF
    ('', 'ClayBeta'),  # DG
    ('', 'Malla 100'),  # DH
    ('', 'CO3'),  # DI
    ('', 'Recuperación'),  # DJ
    ('', ''),  # DK
    ('Fecha inicio Reposo', ''),  # DL
    ('Fecha inicio Humectación', ''),  # DM
    ('Fecha inicio Riego Continuo', ''),  # DN
    ('Días de reposo', ''),  # DO
    ('Días de humectación', ''),  # DP
)

# celdas unidas del encabezado, copiadas del informe
MERGES = ("G1:H1", "I1:J1", "AM1:AR1", "AY1:BC1", "BE1:BG1", "BM1:BN1",
          "CO1:CS1", "CU1:CW1", "CY1:DA1", "DE1:DJ1", "DL1:DL2", "DM1:DM2",
          "DN1:DN2", "DO1:DO2", "DP1:DP2")


def parcela_de(modulo, pad=PAD):
    """Modulo -> parcela. Numeracion correlativa, n modulos por parcela."""
    return np.ceil(np.asarray(modulo, dtype="float64")
                   / MODULOS_POR_PARCELA[pad]).astype("int64")


def calidad_turno(pad=PAD, engine=None, fecha_min=None, fecha_max=None):
    """Fecha + Turno -> masa apilada del turno y su bloque de calidad.

    Une los dos tramos del reporte de turno del pad: Historico_Reporte_Turno,
    que llega hasta el cierre del mes anterior, y la cache de emision, que
    toma desde ahi. Los turnos vienen rotulados TA/TB en el historico y A/B en
    la cache, asi que se normalizan a la letra.

    El origen del mineral (STOCK / MINA / SRR) viene en fraccion en el
    historico y en porcentaje en la cache: se normaliza a porcentaje que suma
    100, que es como lo publica el informe.
    """
    eng = engine or dbs.get_engine()
    hist, cache = MATERIAL_PAD[pad]
    campos = ", ".join(CALIDAD)
    fin_exclusivo = (pd.Timestamp(fecha_max).normalize() + pd.Timedelta(days=1)
                     if fecha_max is not None else None)
    params = {}
    filtro = []
    if fecha_min is not None:
        filtro.append("Fecha >= :fecha_min")
        params["fecha_min"] = pd.Timestamp(fecha_min).date()
    if fin_exclusivo is not None:
        filtro.append("Fecha < :fecha_fin")
        params["fecha_fin"] = fin_exclusivo.date()
    where = (" AND " + " AND ".join(filtro)) if filtro else ""
    t = pd.concat([
        pd.read_sql(text(f"""
        SELECT Fecha, Turno, Apilado_TMS_Real, {campos}
        FROM {dbs.SCHEMA}.Historico_Reporte_Turno
        WHERE Campania = '{hist}'{where}
        """), eng, params=params),
        pd.read_sql(text(f"""
        SELECT Fecha, Turno, Apilado_TMS_Real, {campos}
        FROM {dbs.SCHEMA}.reporte_turno_cache_emision_test
        WHERE Material = '{cache}'{where}
        """), eng, params=params),
    ], ignore_index=True)
    t["fecha"] = pd.to_datetime(t["Fecha"])
    t["turno"] = t["Turno"].astype("string").str.strip().str[-1]
    for c in ["Apilado_TMS_Real"] + list(CALIDAD):
        t[c] = pd.to_numeric(t[c], errors="coerce")
    t = t.rename(columns=dict(CALIDAD, Apilado_TMS_Real="TMS_turno"))
    # el mismo turno puede venir en los dos tramos: manda la cache, que es la
    # que el reporte reemite
    t = t.drop_duplicates(["fecha", "turno"], keep="last")
    suma = t[ORIGEN].sum(axis=1)
    for c in ORIGEN:
        t[c] = t[c] / suma.replace(0, np.nan) * 100
    return t[["fecha", "turno", "TMS_turno"] + list(CALIDAD.values())]






def _celda(v):
    """Valor de pandas -> valor que openpyxl sepa escribir."""
    if v is None or pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.generic):
        return v.item()
    return v


def _escribir_filas(ws, m):
    """Nuestras columnas desde FILA_DATOS, cada una en su letra, sin formato.

    Se escribe por numero de columna y no en orden corrido porque el bloque
    que la base calcula no es contiguo: entre medio quedan las columnas sin
    objeto canonico, que se dejan vacias.
    """
    campos = list(COLUMNAS.items())
    for i, (_, fila) in enumerate(m.iterrows(), start=FILA_DATOS):
        for col, campo in campos:
            ws.cell(i, col, _celda(fila[campo]))


def _escribir_hoja(ws, m):
    """Encabezado completo del informe y nuestras filas debajo, sin plantilla."""
    for col, (titulo, unidad) in enumerate(PLANTILLA, start=1):
        if titulo:
            ws.cell(1, col, titulo)
        if unidad:
            ws.cell(2, col, unidad)
    for rango in MERGES:
        ws.merge_cells(rango)
    _escribir_filas(ws, m)


def _vaciar_datos(ws, desde=FILA_DATOS):
    """Borra los valores de las filas de datos y deja el formato en su lugar.

    Las celdas unidas se saltan: solo la esquina de cada rango es escribible.
    """
    for fila in ws.iter_rows(min_row=desde, max_row=ws.max_row):
        for celda in fila:
            if not isinstance(celda, MergedCell):
                celda.value = None


def _hoja_detalle(wb, m):
    """Hoja con el armado de cada fila, al final del libro."""
    if HOJA_DETALLE in wb.sheetnames:
        del wb[HOJA_DETALLE]
    ws = wb.create_sheet(HOJA_DETALLE)
    if m.empty:
        ws.append(["Sin módulos activos del pad en la ventana de este Caso."])
        ws.append(["La hoja MODULOS conserva el encabezado completo; no se inventan filas ni valores."])
        return
    ws.append(list(m.columns))
    for fila in m.itertuples(index=False, name=None):
        ws.append([_celda(v) for v in fila])


def preparar_modulos_desde_resultado(res, pad, calidad, fecha_min=None,
                                     fecha_max=None):
    """Build the legacy MODULOS contract from one already-loaded Case result.

    The Case's reconciled TMS allocation is the source of module/shift weights.
    Chemistry is read separately at load time and joined in memory by
    operational date and turn. Downloading the prepared workbook never queries
    SQL. No campaign or module numbering is assumed.
    """
    pad = int(pad)
    if pad not in dbs.PADS:
        raise ValueError(f"Pad {pad} no tiene plantilla de informe.")
    ap = res.get("apilado")
    st = res.get("shift_table")
    if ap is None or st is None or ap.empty or st.empty:
        return pd.DataFrame(columns=COLS_INFORME + COLS_CALIDAD + [
            "fecha_ini_carguio", "dias", "dias_con_masa", "volumen",
            "completo", "altura_prom", "humedad"])
    ap = ap.copy()
    st = st.copy()
    ap["fecha"] = pd.to_datetime(ap["fecha"], errors="coerce").dt.normalize()
    st["fecha"] = pd.to_datetime(st["fecha"], errors="coerce").dt.normalize()
    if fecha_min is not None:
        lo = pd.Timestamp(fecha_min).normalize()
        ap = ap.loc[ap.fecha.ge(lo)]
        st = st.loc[st.fecha.ge(lo)]
    if fecha_max is not None:
        hi = pd.Timestamp(fecha_max).normalize()
        ap = ap.loc[ap.fecha.le(hi)]
        st = st.loc[st.fecha.le(hi)]
    ap = ap.loc[ap.pad_id.eq(pad) & ap.vol_diario.gt(0)].copy()
    st = st.loc[st.pad_id.eq(pad)].copy()
    if "estado" in ap:
        ap = ap.loc[ap.estado.eq("ACTIVO")]
    keys = ["pad_id", "campana", "modulo"]
    daykeys = keys + ["fecha"]
    if ap.empty or st.empty:
        return pd.DataFrame(columns=COLS_INFORME + COLS_CALIDAD + [
            "fecha_ini_carguio", "dias", "dias_con_masa", "volumen",
            "completo", "altura_prom", "humedad"])

    # The active engine assigns daily wet mass by module volume share. Its TMS
    # allocation by turn remains module-specific and is retained unchanged.
    daily = (st.groupby("fecha", as_index=False)
             .agg(TMH_dia=("TMH_dia", "first"),
                  vol_dia_total=("vol_dia_total", "first")))
    ap = ap.merge(daily, on="fecha", how="left", validate="many_to_one")
    ap["TMH_asignada"] = (pd.to_numeric(ap.TMH_dia, errors="coerce")
        * pd.to_numeric(ap.vol_diario, errors="coerce")
        / pd.to_numeric(ap.vol_dia_total, errors="coerce").where(
            pd.to_numeric(ap.vol_dia_total, errors="coerce").gt(0)))
    sums = st.groupby(daykeys, as_index=False).agg(
        masa_dia=("masa_total", lambda s: s.sum(min_count=1)),
        masa_turno1=("masa_turno1", lambda s: s.sum(min_count=1)),
        masa_turno2=("masa_turno2", lambda s: s.sum(min_count=1)))
    ap = ap.merge(sums, on=daykeys, how="left", validate="one_to_one")
    base = ap.groupby(keys, as_index=False).agg(
        fecha_ini_carguio=("fecha", "min"),
        fecha_fin_carguio=("fecha", "max"),
        dias=("fecha", "nunique"),
        dias_con_masa=("masa_dia", lambda s: int(s.notna().sum())),
        volumen=("vol_diario", "sum"),
        TMH=("TMH_asignada", lambda s: s.sum(min_count=1)),
        TMS=("masa_dia", lambda s: s.sum(min_count=1)),
        altura_prom=("altura_prom", "last"))
    base["cobertura_masa_completa"] = base.dias.eq(base.dias_con_masa)
    # Module completeness requires both start and end inside the captured data.
    base["completo"] = False
    if {"vol_acum_final", "avance"}.issubset(ap.columns):
        limits = ap.sort_values("fecha").groupby(keys).agg(
            acumulado_final=("vol_acum_final", "last"),
            avance_final=("avance", "last"))
        base = base.merge(limits, left_on=keys, right_index=True, how="left")
        tolerance = base.acumulado_final.abs().mul(0.005).clip(lower=1.0)
        includes_start = (base.volumen - base.acumulado_final).abs().le(tolerance)
        base["completo"] = (includes_start & base.avance_final.ge(0.995)
                             & base.cobertura_masa_completa)
    base["ultimo_dia_en_caso"] = base["fecha_fin_carguio"]
    base.loc[~base.get("avance_final", pd.Series(float("nan"), index=base.index)).ge(0.995), "fecha_fin_carguio"] = pd.NaT
    base["campana"] = pd.to_numeric(base.campana, errors="raise").astype("int64")
    base["modulo"] = pd.to_numeric(base.modulo, errors="raise").astype("int64")
    # Parcel sizes remain the established report convention by physical pad;
    # campaign identity and module count come from the loaded result.
    base["parcela"] = parcela_de(base.modulo, pad=pad)

    # The custom TMS weights below are per module and per turn. This avoids the
    # previous report's global-turn split, which is not valid for the current
    # multi-pad flow allocation.
    q = st[daykeys + ["masa_turno1", "masa_turno2"]].copy()
    q = q.melt(id_vars=daykeys, value_vars=["masa_turno1", "masa_turno2"],
               var_name="turno_src", value_name="peso")
    q["turno"] = q.turno_src.map({"masa_turno1": "A", "masa_turno2": "B"})
    q["peso"] = pd.to_numeric(q.peso, errors="coerce").clip(lower=0)
    if calidad is not None and not calidad.empty:
        cal = calidad.copy()
        cal["fecha"] = pd.to_datetime(cal["fecha"], errors="coerce").dt.normalize()
        cal["turno"] = cal["turno"].astype("string").str.strip().str.upper().str[-1]
        for field in CALIDAD.values():
            if field not in cal:
                cal[field] = np.nan
        cal = cal.drop_duplicates(["fecha", "turno"], keep="last")
        q = q.merge(cal, on=["fecha", "turno"], how="left",
                    validate="many_to_one")
    else:
        q[ list(CALIDAD.values()) ] = np.nan
    quality_rows = []
    for key, group in q.groupby(keys, sort=True, dropna=False):
        row = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
        for field in CALIDAD.values():
            v = pd.to_numeric(group[field], errors="coerce")
            w = group.peso.where(v.notna(), 0.0)
            denom = w.sum(min_count=1)
            row[field] = (float((v.fillna(0.0) * w).sum() / denom)
                          if pd.notna(denom) and denom > 0 else np.nan)
        coverage = group.peso.where(group.get("solubilidad", pd.Series(
            np.nan, index=group.index)).notna(), 0.0).sum(min_count=1)
        total = group.peso.sum(min_count=1)
        row["cobertura_calidad"] = (coverage / total
                                     if pd.notna(total) and total > 0 else np.nan)
        row["origen_suma"] = pd.Series([row.get(c, np.nan) for c in ORIGEN], dtype=float).sum(min_count=1)
        quality_rows.append(row)
    weighted = pd.DataFrame(quality_rows)
    out = base.merge(weighted, on=keys, how="left", validate="one_to_one")
    out["frac_oxidos"] = out["solubilidad"]
    out["frac_sulfuros"] = 1 - out["frac_oxidos"]
    out["cu_fino"] = out["TMS"] * out["CuT"] / 100.0
    out["humedad"] = np.nan
    profile = res.get("perfil_turnos")
    if profile is not None and not profile.empty and {
        "fecha", "turno", "humedad"}.issubset(profile.columns):
        p = profile[["fecha", "turno", "humedad"] +
                    (["tmh"] if "tmh" in profile else [])].copy()
        p["fecha"] = pd.to_datetime(p.fecha, errors="coerce").dt.normalize()
        p["turno"] = p.turno.astype("string").str.strip().str.upper().str[-1]
        p["humedad"] = pd.to_numeric(p.humedad, errors="coerce")
        p["humedad"] = p.humedad.where(p.humedad.between(0, 100))
        p["perfil_peso"] = (pd.to_numeric(p.get("tmh", 1.0), errors="coerce")
                            if "tmh" in p else 1.0)
        p["humedad_x_peso"] = p.humedad * p.perfil_peso
        ph = p.groupby(["fecha", "turno"], as_index=False).agg(
            humedad_num=("humedad_x_peso", lambda s: s.sum(min_count=1)),
            humedad_den=("perfil_peso", lambda s: s.where(
                p.loc[s.index, "humedad"].notna(), 0.0).sum(min_count=1)))
        ph["humedad_turno"] = ph.humedad_num / ph.humedad_den.where(
            ph.humedad_den.gt(0))
        h = q[daykeys + ["turno", "peso"]].merge(
            ph[["fecha", "turno", "humedad_turno"]], on=["fecha", "turno"],
            how="left", validate="many_to_one")
        h["humedad_peso"] = h.humedad_turno * h.peso
        humedad = h.groupby(keys).agg(
            numerador=("humedad_peso", lambda s: s.sum(min_count=1)),
            denominador=("peso", lambda s: s.where(
                h.loc[s.index, "humedad_turno"].notna(), 0.0).sum(min_count=1)))
        humedad["humedad"] = humedad.numerador / humedad.denominador.where(
            humedad.denominador.gt(0))
        out = out.drop(columns=["humedad"]).merge(
            humedad[["humedad"]], left_on=keys, right_index=True,
            how="left", validate="one_to_one")
    return out[COLS_INFORME + COLS_CALIDAD + [
        "fecha_ini_carguio", "dias", "dias_con_masa", "volumen",
        "completo", "cobertura_masa_completa", "ultimo_dia_en_caso", "altura_prom", "humedad"]].sort_values(
            ["campana", "modulo"]).reset_index(drop=True)


def exportar_desde_dataframe(m, destino, pad=PAD, detalle=True,
                              plantilla=None, caso=None):
    """Write the complete MODULOS sheet from prepared rows, with no SQL."""
    pad = int(pad)
    if pad not in dbs.PADS:
        raise ValueError(f"Pad {pad} no tiene plantilla de informe.")
    plantilla = Path(plantilla) if plantilla else PLANTILLAS_XLSX[pad]
    if plantilla.exists():
        wb = openpyxl.load_workbook(plantilla)
        ws = wb[HOJA]
        _vaciar_datos(ws)
        _escribir_filas(ws, m)
        # The legacy auxiliary sheets contain #REF! formula caches. Keep the
        # intact full-width MODULOS sheet and omit broken auxiliary outputs.
        for name in list(wb.sheetnames):
            if name != HOJA:
                del wb[name]
        if detalle:
            _hoja_detalle(wb, m)
        if caso:
            info = wb.create_sheet("CASO")
            info.append(["Campo", "Valor"])
            for key in ("caso_id", "run_id", "modelo_codigo", "fecha_inicio", "fecha_fin"):
                info.append([key, _celda(caso.get(key, caso.get("id") if key == "caso_id" else None))])
            info.append(["Alcance", "Masa y calidad de la ventana del Caso; ver completo en DETALLE."])
            info.append(["Sin actividad", "Si MODULOS no tiene filas, el pad no apilo en la ventana."])
        ws.print_area = f"A1:{get_column_letter(125 if pad == dbs.PAD_OXIDOS else 120)}{max(3, len(m)+2)}"
        ws.freeze_panes = "E3"
        wb.active = wb.index(ws)
        wb.save(destino)
        return m
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        _escribir_hoja(writer.book.create_sheet(HOJA, 0), m)
        if detalle:
            m.to_excel(writer, sheet_name=HOJA_DETALLE, index=False)
    return m






# ultima columna que la base calcula (AH, malla de media pulgada)
_ULTIMA = max(COLUMNAS)
_NOMBRES = [COLUMNAS.get(i, f"col_{i}") for i in range(1, _ULTIMA + 1)]










