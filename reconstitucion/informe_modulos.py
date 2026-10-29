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
from openpyxl.formula.translate import Translator
from openpyxl.utils import get_column_letter, column_index_from_string
from copy import copy
import re

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
EXTRA_COLUMNAS = {
    45: "csrCC", 46: "csrCV", 47: "csrCPY", 48: "CUOXI", 49: "CUINS",
    50: "suma_CSR", 51: "ACF03", 52: "ACF04", 53: "ACF05",
    54: "ACF06", 55: "ACF07", 56: "suma_ACF",
    57: "Calidad01", 58: "Calidad02", 59: "Calidad03", 60: "suma_Calidad",
    39: "CuT_SRR", 40: "CuS_SRR", 41: "ClayBeta_SRR",
    42: "Malla100_SRR", 43: "CO3_SRR", 44: "Recuperacion_SRR",
    37: "sal_kg_t", 116: "fecha_ini_reposo",
}
EXTRA_FIELDS = set(EXTRA_COLUMNAS.values())
COLUMNAS = {
    1: "campana", 2: "parcela", 3: "modulo", 4: "fecha_fin_carguio",
    5: "TMH", 6: "TMS", 7: "frac_oxidos", 8: "frac_sulfuros",
    9: "altura_prom", 11: "cu_fino", 12: "FeT", 13: "FeS",
    14: "CuT", 15: "CuS", 16: "CO3", 18: "consumo_H",
    19: "solubilidad", 20: "clasificacion_contractual",
    22: "CuFe", 23: "beta_clay", 24: "origen_stock",
    25: "origen_mina", 26: "origen_srr", 27: "origen_suma",
    31: "origen_srr", 33: "malla_100", 34: "malla_media", 38: "humedad",
    **EXTRA_COLUMNAS,
}
COLS_CALIDAD = ["cu_fino"] + list(CALIDAD.values()) + ["origen_suma",
    "cobertura_calidad", "clasificacion_contractual"]

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
    ('CampaÃ±a', '#'),  # A
    ('Parcela', '#'),  # B
    ('MÃ³dulo', '#'),  # C
    ('Fecha TÃ©rmino CarguÃ­o', ''),  # D
    ('Mineral Humedo', 't'),  # E
    ('Mineral seco', 't'),  # F
    ('Tipo de material', 'Ã“xidos'),  # G
    ('', 'Sulfuros'),  # H
    ('Altura, m', 'Real'),  # I
    ('', 'Objetivo'),  # J
    ('Cobre Fino', 't'),  # K
    ('FeT', '%'),  # L
    ('FeS', '%'),  # M
    ('CuT', '%'),  # N
    ('CuS', '%'),  # O
    ('CO3', '%'),  # P
    ('AdiciÃ³n de H+', 'kg/t'),  # Q
    ('Consumo H+', 'kg/t'),  # R
    ('Solubilidad Real', ''),  # S
    ('DefiniciÃ³n\n Sulfuros-Mixtos', ''),  # T
    ('TC', 'H+'),  # U
    ('CuFe', '%'),  # V
    ('Beta Clay', '%'),  # W
    ('Stock', '%'),  # X
    ('Mina', '%'),  # Y
    ('SRR', '%'),  # Z
    ('Suma', ''),  # AA
    ('Transicional', '%'),  # AB
    ('SupÃ©rgeno', '%'),  # AC
    ('Ã“xido', '%'),  # AD
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
    ('', 'RecuperaciÃ³n'),  # AR
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
    ('SupÃ©rgeno', '%'),  # BP
    ('Ã“xido', '%'),  # BQ
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
    ('RecuperaciÃ³n', '%'),  # DC
    ('', ''),  # DD
    ('SRR', 'CuT'),  # DE
    ('', 'CuS'),  # DF
    ('', 'ClayBeta'),  # DG
    ('', 'Malla 100'),  # DH
    ('', 'CO3'),  # DI
    ('', 'RecuperaciÃ³n'),  # DJ
    ('', ''),  # DK
    ('Fecha inicio Reposo', ''),  # DL
    ('Fecha inicio HumectaciÃ³n', ''),  # DM
    ('Fecha inicio Riego Continuo', ''),  # DN
    ('DÃ­as de reposo', ''),  # DO
    ('DÃ­as de humectaciÃ³n', ''),  # DP
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







def derivar_campos_extra_por_modulo(shift_table, calidad, movcam=None, srr=None,
                                    datos_turno=None):
    """Derive report extension fields from explicit turn sources and weights.

    ACF/control use Ton-weighted mov_cam POND numerators. CSR uses Ton * CuT.
    Mina+Stock support is allocated by module TMS * turn origin share; SRR is a
    separate source weighted by module TMS * SRR origin share. Missing sources
    stay missing and coverage is measured against module TMS.
    """
    st = shift_table.copy()
    st["fecha"] = pd.to_datetime(st.fecha, errors="coerce").dt.normalize()
    qual = calidad.copy() if calidad is not None else pd.DataFrame()
    if not qual.empty:
        qual["fecha"] = pd.to_datetime(qual.fecha, errors="coerce").dt.normalize()
        qual["turno"] = qual.turno.astype("string").str.strip().str.upper().str[-1]
    turns = []
    for r in st.itertuples(index=False):
        for turn, col in (("A", "masa_turno1"), ("B", "masa_turno2")):
            mass = pd.to_numeric(pd.Series([getattr(r, col)]), errors="coerce").iloc[0]
            if pd.isna(mass) or mass <= 0:
                continue
            turns.append({"pad_id": r.pad_id, "campana": int(r.campana),
                "modulo": int(r.modulo), "fecha": r.fecha, "turno": turn,
                "tms": float(mass)})
    w = pd.DataFrame(turns)
    if w.empty:
        return pd.DataFrame(columns=["campana", "modulo"])
    if not qual.empty:
        qcols = [c for c in ("fecha", "turno", "origen_stock", "origen_mina", "origen_srr") if c in qual]
        q = qual[qcols].drop_duplicates(["fecha", "turno"], keep="last")
        w = w.merge(q, on=["fecha", "turno"], how="left", validate="many_to_one")
    for c in ("origen_stock", "origen_mina", "origen_srr"):
        if c not in w: w[c] = np.nan
        w[c] = pd.to_numeric(w[c], errors="coerce")
    w["ms_share"] = (w.origen_stock + w.origen_mina) / 100.0
    w["srr_share"] = w.origen_srr / 100.0

    # Pooled, source-row metrics by turn. Do not attribute truck rows directly;
    # only their source composition is pooled, then allocated via reconstructed TMS.
    pooled = {}
    if movcam is not None and not movcam.empty:
        mov = movcam.copy()
        mov["_fecha"] = pd.to_datetime(mov.Fecha, errors="coerce").dt.normalize()
        mov["_turno"] = mov.Turno.astype("string").str.strip().str.upper().str[-1]
        keep = mov.Destino.astype("string").str.strip().str.upper().eq("CH01")
        keep &= mov.Origen.astype("string").str.strip().str.casefold().isin({"mina", "stock"})
        fase = mov.Fase.astype("string").str.strip().str.casefold()
        origen = mov.Origen.astype("string").str.strip().str.casefold()
        # Mina rows with unknown phase remain usable; Stock requires known non-SRR phase.
        keep &= fase.fillna("unknown").ne("srr") & (origen.eq("mina") | fase.notna())
        mov = mov.loc[keep].copy()
        for (date, turn), g in mov.groupby(["_fecha", "_turno"], sort=True):
            ton = pd.to_numeric(g.Ton, errors="coerce")
            rec = {"source_ton": ton.sum(min_count=1)}
            for field, pond in [(f"ACF0{i}", f"PONDACF0{i}") for i in range(3,8)] + [(f"Calidad0{i}", f"PONDCalidad0{i}") for i in range(1,4)]:
                if pond in g:
                    pv = pd.to_numeric(g[pond], errors="coerce")
                    valid = pv.notna() & ton.notna()
                    den = ton[valid].sum(min_count=1)
                    rec[field] = pv[valid].sum(min_count=1) / den if pd.notna(den) and den > 0 else np.nan
                    rec[field+"_source"] = ton[valid].sum(min_count=1) / rec["source_ton"] if pd.notna(rec["source_ton"]) and rec["source_ton"] > 0 else 0.0
            cut = pd.to_numeric(g.get("CuTG00", pd.Series(np.nan,index=g.index)),errors="coerce")
            for field, pond in [("csrCC","PONDcsrCCG15"),("csrCV","PONDcrsCVG16"),("csrCPY","PONDcsrCPYG17"),("CUOXI","PONDcsrCUOXI"),("CUINS","PONDcsrCUINS")]:
                if pond in g:
                    pv=pd.to_numeric(g[pond],errors="coerce"); valid=pv.notna()&ton.notna()&cut.notna()
                    den=(ton[valid]*cut[valid]).sum(min_count=1)
                    rec[field]=100*pv[valid].sum(min_count=1)/den if pd.notna(den) and den>0 else np.nan
                    rec[field+"_source"]=ton[valid].sum(min_count=1)/rec["source_ton"] if valid.any() and pd.notna(rec["source_ton"]) and rec["source_ton"]>0 else 0.0
            rec["cut"] = (ton*cut).sum(min_count=1)/ton.where(cut.notna()).sum(min_count=1) if cut.notna().any() else np.nan
            pooled[(date,turn)] = rec

    # SRR has its own measured turn profile; never substitute Mina+Stock metrics.
    srrmap = {}
    if srr is not None and not srr.empty:
        sr=srr.copy(); sr["fecha"]=pd.to_datetime(sr.Fecha,errors="coerce").dt.normalize(); sr["turno"]=sr.Turno.astype("string").str.strip().str.upper().str[-1]
        if sr.duplicated(["fecha","turno"]).any(): raise ValueError("SRR duplicado fecha/turno")
        srrmap={(r.fecha,r.turno):r._asdict() for r in sr.itertuples(index=False)}
    dcomap={}
    if datos_turno is not None and not datos_turno.empty:
        dd=datos_turno.copy()
        by_lower={str(c).casefold():c for c in dd.columns}
        def source_col(name): return by_lower.get(name.casefold())
        date_col=source_col("Fecha")
        if date_col is not None: dd["_fecha_extra"]=pd.to_datetime(dd[date_col],errors="coerce").dt.normalize()
        for suffix,turn in (("A","A"),("B","B")):
            needed=[f"Apilado_TMH_turno_{suffix}",f"Sal_turno_{suffix}",f"Humedad_Turno_{suffix}"]
            cols=[source_col(c) for c in needed]
            if date_col is None or any(c is None for c in cols): continue
            tmh,salt,hum=(pd.to_numeric(dd[c],errors="coerce") for c in cols)
            tms=(tmh+salt)*(1-hum/100)-salt
            dose=1000*salt/tms.where(tms.gt(0))
            for date,val in zip(dd._fecha_extra,dose): dcomap[(date,turn)]=val

    result=[]
    ms_specs={**{f"ACF0{i}":("mass",f"ACF0{i}") for i in range(3,8)},
              **{f"Calidad0{i}":("mass",f"Calidad0{i}") for i in range(1,4)},
              **{"csrCC":("cu","csrCC"),"csrCV":("cu","csrCV"),"csrCPY":("cu","csrCPY"),"CUOXI":("cu","CUOXI"),"CUINS":("cu","CUINS")}}
    srr_fields=["CuT_SRR","CuS_SRR","ClayBeta_SRR","Malla100_SRR","CO3_SRR","Recuperacion_SRR"]
    for (camp,module),g in w.groupby(["campana","modulo"],sort=True):
        total=float(g.tms.sum()); row={"campana":camp,"modulo":module}
        for field,(kind,source_field) in ms_specs.items():
            num=den=covered=0.0
            for it in g.itertuples(index=False):
                rec=pooled.get((it.fecha,it.turno)); share=it.ms_share
                if rec is None or pd.isna(share) or share<=0: continue
                v=rec.get(source_field,np.nan); cov=rec.get(source_field+"_source",0)
                if pd.isna(v) or cov<=0: continue
                mass=it.tms*share; weight=mass
                if kind=="cu":
                    cut=rec.get("cut",np.nan)
                    if pd.isna(cut) or cut<=0: continue
                    weight*=cut
                num+=v*weight; den+=weight; covered+=mass*min(float(cov),1)
            row[field]=num/den if den>0 else np.nan
            row["cobertura_"+field]=min(covered/total,1) if total>0 else 0
            row["fuente_"+field]="mov_cam POND CH01 Mina+Stock; attribution por masa modulo-turno y origen del turno"
            row["alcance_"+field]="Parcial segun cobertura; ACF/control por Ton y CSR por Ton * CuT. No representa SRR."
        for field in srr_fields:
            num=den=covered=0.0
            for it in g.itertuples(index=False):
                sr=srrmap.get((it.fecha,it.turno)); share=it.srr_share
                if sr is None or pd.isna(share) or share<=0: continue
                value=pd.to_numeric(pd.Series([sr.get(field)]),errors="coerce").iloc[0]
                sr_tms=pd.to_numeric(pd.Series([sr.get("SRR_TMS_Turno")]),errors="coerce").iloc[0]
                if pd.isna(value) or pd.isna(sr_tms): continue
                wt=it.tms*share
                if wt<=0: continue
                num+=value*wt; den+=wt; covered+=wt
            row[field]=num/den if den>0 else np.nan
            row["cobertura_"+field]=min(covered/total,1) if total>0 else 0
            row["fuente_"+field]="SRR turno independiente ponderado por TMS modulo-turno * origen SRR"
            row["alcance_"+field]="Atributo del componente SRR; no es recuperacion global ni incluye Mina+Stock."
        for field, comps in (("suma_ACF",[f"ACF0{i}" for i in range(3,8)]),("suma_Calidad",[f"Calidad0{i}" for i in range(1,4)]),("suma_CSR",["csrCC","csrCV","csrCPY","CUOXI","CUINS"])):
            vals=[row.get(c,np.nan) for c in comps]
            row[field]=sum(vals) if all(pd.notna(v) and np.isfinite(v) for v in vals) else np.nan
            row["cobertura_"+field]=min((row.get("cobertura_"+c,0) for c in comps),default=0)
            row["fuente_"+field]="Suma calculada solo cuando todos los componentes estan disponibles"
            row["alcance_"+field]="Sin componentes faltantes; no se sustituyen faltantes por cero."
        # Salt is a separate measured turn input and uses the module's turn TMS.
        num=den=0.0
        for it in g.itertuples(index=False):
            val=dcomap.get((it.fecha,it.turno))
            if val is None or pd.isna(val): continue
            num+=float(val)*it.tms; den+=it.tms
        row["sal_kg_t"]=num/den if den>0 else np.nan
        row["cobertura_sal_kg_t"]=den/total if total>0 else 0
        row["fuente_sal_kg_t"]="Datos_conciliados_of por turno; dosis derivada"
        row["alcance_sal_kg_t"]="1000 * sal/TMS medido del turno; ponderado por TMS modulo-turno."
        result.append(row)
    return pd.DataFrame(result)


def cargar_campos_extra(res, pad, case, engine):
    """Case-bounded read loader; pure aggregation remains separately testable."""
    if int(pad) not in dbs.PADS:
        return pd.DataFrame()
    st = res.get("shift_table")
    if st is None or st.empty:
        return pd.DataFrame()
    st = st.copy()
    st["fecha"] = pd.to_datetime(st.fecha, errors="coerce").dt.normalize()
    lo, hi = pd.Timestamp(case["fecha_inicio"]).normalize(), pd.Timestamp(case["fecha_fin"]).normalize()
    st = st.loc[st.pad_id.eq(int(pad)) & st.fecha.between(lo, hi)]
    if st.empty:
        return pd.DataFrame()
    quality = res.get("_informe_calidad_por_pad", {}).get(int(pad), pd.DataFrame())
    from .fuentes_informe import cargar_fuentes
    fuentes = cargar_fuentes(engine, lo, hi)
    extras = derivar_campos_extra_por_modulo(
        st, quality, movcam=fuentes.get("movcam"), srr=fuentes.get("srr"),
        datos_turno=fuentes.get("datos_turno"))
    from .fuentes_informe import cargar_reposo
    ciclos, cycle_warnings = cargar_reposo(engine, pad, zip(st.campana, st.modulo))
    extras = incorporar_reposo(extras, ciclos)
    warnings = " | ".join(fuentes.get("warnings", []) + cycle_warnings)
    extras["advertencias_fuentes"] = warnings
    return extras

def incorporar_reposo(extras, ciclos):
    """Join hito de control por campa?a/m?dulo, dentro del PAD ya consultado."""
    out = extras.copy()
    out['fecha_ini_reposo'] = pd.NaT
    out['cobertura_fecha_ini_reposo'] = 0.0
    out['fuente_fecha_ini_reposo'] = 'campana_parcela_control.fecha_ini_reposo'
    if ciclos is None or ciclos.empty or out.empty:
        return out
    c = ciclos.copy()
    c['campana'] = pd.to_numeric(c.numero_campana, errors='coerce')
    c['modulo'] = pd.to_numeric(c.nombre_modulo, errors='coerce')
    c['fecha_ini_reposo'] = pd.to_datetime(c.fecha_ini_reposo, errors='coerce').dt.normalize()
    for i, row in out.iterrows():
        hits = c.loc[c.campana.eq(row.campana) & c.modulo.eq(row.modulo), 'fecha_ini_reposo']
        dates = hits.dropna().unique()
        if len(dates) == 1:
            out.loc[i, 'fecha_ini_reposo'] = pd.Timestamp(dates[0])
            out.loc[i, 'cobertura_fecha_ini_reposo'] = 1.0
        elif len(dates) > 1:
            raise ValueError('Reposo con fechas contradictorias para campana/modulo.')
    return out


def _celda(v):
    """Valor de pandas -> valor que openpyxl sepa escribir."""
    if v is None or pd.isna(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    if isinstance(v, np.generic):
        return v.item()
    return v


def _escribir_filas(ws, m, pad=None):
    """Nuestras columnas desde FILA_DATOS, cada una en su letra, sin formato.

    Se escribe por numero de columna y no en orden corrido porque el bloque
    que la base calcula no es contiguo: entre medio quedan las columnas sin
    objeto canonico, que se dejan vacias.
    """
    campos = list(COLUMNAS.items())
    formula_cols = {col for col in _formulas_por_fila(pad)
                    if ws.cell(FILA_DATOS, col).data_type == "f"} if pad in dbs.PADS else set()
    for i, (_, fila) in enumerate(m.iterrows(), start=FILA_DATOS):
        for col, campo in campos:
            if col in formula_cols:
                continue
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
    # La plantilla conserva formato hasta 1.000 filas y 340 columnas, pero
    # la mayor parte del rectangulo no tiene valores. Recorrer solo celdas
    # materializadas reduce el costo sin tocar estilos ni rangos combinados.
    for celda in tuple(ws._cells.values()):
        if (celda.row >= desde and not isinstance(celda, MergedCell)
                and celda.data_type != "f"):
            celda.value = None


def _formulas_por_fila(pad):
    """Columnas calculadas por las fórmulas originales de MODULOS."""
    formulas = {7, 8, 27, 56, 57, 58, 59, 60}
    if pad == dbs.PAD_SULFUROS:
        formulas.update({11, 19, 20, 21, 32, 50, 119, 120})
    return formulas


def _formula_origen(ws, row, col):
    cell = ws.cell(row, col)
    if cell.data_type == "f":
        return cell.value, row
    for r in range(3, ws.max_row + 1):
        cell = ws.cell(r, col)
        if cell.data_type == "f":
            return cell.value, r
    return None, None


def _formula_guardada(formula):
    """Keep official equations; guard missing inputs and zero denominators."""
    if not formula:
        return formula
    m = re.fullmatch(r"=S(\d+)", formula)
    if m:
        r = m.group(1)
        return f'=IF(S{r}="","",S{r})'
    m = re.fullmatch(r"=1-G(\d+)", formula)
    if m:
        r = m.group(1)
        return f'=IF(G{r}="","",1-G{r})'
    m = re.fullmatch(r"=\+?F(\d+)\*N(\d+)/100", formula)
    if m:
        r = m.group(1)
        return f'=IF(OR(F{r}="",N{r}=""),"",F{r}*N{r}/100)'
    m = re.fullmatch(r"=O(\d+)/N(\d+)", formula)
    if m:
        o, n = m.groups()
        return f'=IF(OR(O{o}="",N{n}="",N{n}=0),"",O{o}/N{n})'
    m = re.match(r"=IF\(S(\d+) <0\.25,", formula)
    if m:
        r = m.group(1)
        return f'=IF(S{r}="","",{formula[1:]})'
    m = re.match(r"=\+?IF\(P(\d+)>0\.3,", formula)
    if m and "LN(O" in formula:
        r = m.group(1)
        return f'=IF(OR(O{r}="",O{r}<=0,P{r}=""),"",{formula.lstrip("=+")})'
    m = re.fullmatch(r"=\+?D(\d+)", formula)
    if m:
        r = m.group(1)
        return f'=IF(D{r}="","",D{r})'
    m = re.fullmatch(r"=\+?(D[MN])(\d+)-(D[LMN])(\d+)", formula)
    if m:
        left, lr, right, rr = m.groups()
        return f'=IF(OR({left}{lr}="",{right}{rr}=""),"",{left}{lr}-{right}{rr})'
    m = re.fullmatch(r"=\+?SUM\(([A-Z]+)(\d+):([A-Z]+)(\d+)\)", formula)
    if m and m.group(2) == m.group(4):
        left, row, right, _ = m.groups()
        count = column_index_from_string(right) - column_index_from_string(left) + 1
        area = f'{left}{row}:{right}{row}'
        return f'=IF(COUNT({area})={count},{formula.lstrip("=+")},"")'
    m = re.fullmatch(r"=\+?([A-Z]+\d+)\+([A-Z]+\d+)", formula)
    if m:
        left, right = m.groups()
        return f'=IF(COUNT({left},{right})=2,{left}+{right},"")'
    m = re.fullmatch(r"=\+?([A-Z]+\d+)", formula)
    if m:
        ref = m.group(1)
        return f'=IF({ref}="","",{ref})'
    m = re.fullmatch(r"=\+?([A-Z]+\d+)\*([A-Z]+\d+)/100", formula)
    if m:
        left, right = m.groups()
        return f'=IF(COUNT({left},{right})=2,{left}*{right}/100,"")'
    sep = formula.rfind("/")
    if sep > 0 and formula[sep + 1:].startswith(("SUM(", "SUMPRODUCT(")):
        numerator, denominator = formula[1:sep], formula[sep + 1:]
        first = re.search(r'SUMPRODUCT\((\$?[A-Z]+\$?\d+:\$?[A-Z]+\$?\d+)', numerator)
        if first:
            return f'=IF(OR({denominator}=0,COUNT({first.group(1)})=0),"",{numerator}/{denominator})'
        return f'=IF({denominator}=0,"",{numerator}/{denominator})'
    return formula


def _traducir_formula(formula, origen, destino, end_source=None, end_target=None):
    translated = Translator(formula, origin=f"A{origen}").translate_formula(f"A{destino}")
    translated_end = destino + end_source - origen if end_source is not None else None
    if translated_end is not None and end_target is not None and translated_end != end_target:
        translated = re.sub(
            rf"(?<![A-Z0-9_])(\$?[A-Z]{{1,3}}\$?){translated_end}(?!\d)",
            lambda m: f"{m.group(1)}{end_target}", translated)
    return _formula_guardada(translated)


def _escribir_formulas(ws, m, pad, reposo_patron=None):
    """Restore valid formulas on live rows and summaries keyed by campaign/parcel."""
    if m.empty:
        for cell in tuple(ws._cells.values()):
            if cell.row >= FILA_DATOS and not isinstance(cell, MergedCell) and cell.data_type == "f":
                cell.value = None
        return
    formula_cols = _formulas_por_fila(pad)
    per_row = [(c, ws.cell(FILA_DATOS, c).value)
               for c in sorted(formula_cols)
               if ws.cell(FILA_DATOS, c).data_type == "f"]
    reposo_fallback, reposo_origen = (reposo_patron or _formula_origen(ws, FILA_DATOS, 116)) if pad == dbs.PAD_SULFUROS else (None, None)
    summary_row = 3 if pad == dbs.PAD_SULFUROS else 67
    summaries = []
    for c in range(62, 115):
        formula, src = _formula_origen(ws, summary_row, c)
        if formula:
            summaries.append((c, formula, src))
    for cell in tuple(ws._cells.values()):
        if cell.row >= FILA_DATOS and not isinstance(cell, MergedCell) and cell.data_type == "f":
            cell.value = None
    template_rows = ws.max_row
    for row in range(FILA_DATOS, FILA_DATOS + len(m)):
        if row > template_rows:
            pattern = FILA_DATOS + ((row - FILA_DATOS) % MODULOS_POR_PARCELA[pad])
            for col in range(1, ws.max_column + 1):
                src_cell, dst_cell = ws.cell(pattern, col), ws.cell(row, col)
                if src_cell.has_style:
                    dst_cell._style = copy(src_cell._style)
            ws.row_dimensions[row].height = ws.row_dimensions[pattern].height
        for col, formula in per_row:
            ws.cell(row, col, _traducir_formula(formula, FILA_DATOS, row))
        if pad == dbs.PAD_SULFUROS:
            explicit = (m.iloc[row - FILA_DATOS].get("fecha_ini_reposo")
                        if "fecha_ini_reposo" in m.columns else None)
            if (explicit is None or pd.isna(explicit)) and reposo_fallback:
                ws.cell(row, 116, _traducir_formula(reposo_fallback, reposo_origen, row))
    keys = list(m[["campana", "parcela"]].itertuples(index=False, name=None))
    groups, first = [], 0
    for i in range(1, len(keys) + 1):
        if i == len(keys) or keys[i] != keys[first]:
            groups.append((first, i - 1))
            first = i
    for first, last in groups:
        row0, row1 = FILA_DATOS + first, FILA_DATOS + last
        for col, formula, src in summaries:
            span = MODULOS_POR_PARCELA[pad]
            ws.cell(row0, col, _traducir_formula(
                formula, src, row0, end_source=src + span - 1, end_target=row1))
            ws.cell(row0, col)._style = copy(ws.cell(src, col)._style)


def _hoja_detalle(wb, m):
    """Hoja con el armado de cada fila, al final del libro."""
    if HOJA_DETALLE in wb.sheetnames:
        del wb[HOJA_DETALLE]
    ws = wb.create_sheet(HOJA_DETALLE)
    if m.empty:
        ws.append(["Sin mÃ³dulos activos del pad en la ventana de este Caso."])
        ws.append(["La hoja MODULOS conserva el encabezado completo; no se inventan filas ni valores."])
        return
    ws.append(list(m.columns))
    for fila in m.itertuples(index=False, name=None):
        ws.append([_celda(v) for v in fila])


def preparar_modulos_desde_resultado(res, pad, calidad, fecha_min=None,
                                     fecha_max=None, extras=None):
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
                  vol_dia_total_st=("vol_dia_total", "first")))
    ap = ap.merge(daily, on="fecha", how="left", validate="many_to_one")
    vol_den = (pd.to_numeric(ap.vol_dia_total, errors="coerce")
               if "vol_dia_total" in ap else
               pd.to_numeric(ap.vol_dia_total_st, errors="coerce"))
    ap["TMH_asignada"] = (pd.to_numeric(ap.TMH_dia, errors="coerce")
        * pd.to_numeric(ap.vol_diario, errors="coerce")
        / vol_den.where(vol_den.gt(0)))
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
    # T and AE are literal legacy report rules: T follows solubility; AE=Z.
    out["clasificacion_contractual"] = np.where(
        out["solubilidad"].notna(),
        np.where(out["solubilidad"] < 0.25, "Sulfuros", "mixtos"), None)
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
    if extras is not None and not extras.empty:
        ext = extras.copy()
        if not {"campana", "modulo"}.issubset(ext.columns):
            raise ValueError("extras requiere claves campana y modulo")
        ext["campana"] = pd.to_numeric(ext.campana, errors="raise").astype("int64")
        ext["modulo"] = pd.to_numeric(ext.modulo, errors="raise").astype("int64")
        if ext.duplicated(["campana", "modulo"]).any():
            raise ValueError("extras tiene duplicados campana/modulo")
        allowed = set(zip(out.campana.astype(int), out.modulo.astype(int)))
        if not set(zip(ext.campana.astype(int), ext.modulo.astype(int))).issubset(allowed):
            raise ValueError("extras contiene modulos fuera del Caso/pad")
        ext = ext.loc[:, [c for c in ext.columns if c in EXTRA_FIELDS or c in {"campana", "modulo", "advertencias_fuentes"} or c.startswith(("cobertura_", "fuente_", "alcance_"))]]
        out = out.merge(ext, on=["campana", "modulo"], how="left", validate="one_to_one")
    for field in EXTRA_FIELDS:
        if field not in out:
            out[field] = np.nan
    detail_fields = [c for c in out.columns if c.startswith(("cobertura_", "fuente_", "alcance_")) or c == "advertencias_fuentes"]
    output_columns = list(dict.fromkeys(
        COLS_INFORME + COLS_CALIDAD + list(EXTRA_COLUMNAS.values()) + detail_fields + [
            "fecha_ini_carguio", "dias", "dias_con_masa", "volumen",
            "completo", "cobertura_masa_completa", "ultimo_dia_en_caso", "altura_prom", "humedad"]))
    return out[output_columns].sort_values(
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
        reposo_patron = _formula_origen(ws, FILA_DATOS, 116) if pad == dbs.PAD_SULFUROS else None
        _escribir_filas(ws, m, pad)
        _escribir_formulas(ws, m, pad, reposo_patron=reposo_patron)
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
            if "advertencias_fuentes" in m:
                warnings = sorted({str(v) for v in m["advertencias_fuentes"].dropna() if str(v).strip()})
                for warning in warnings:
                    info.append(["Fuente adicional", warning])
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











