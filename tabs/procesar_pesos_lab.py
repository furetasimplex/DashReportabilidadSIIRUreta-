import io
import re
import datetime as dt
import pandas as pd
from sqlalchemy import text
from db_connection import get_engine

MESES = {
    "ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AGO": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DIC": 12,
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4, "MAYO": 5, "JUNIO": 6,
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
}

RE_TORRE = re.compile(r"\bTORRE\s*(\d+)\b", re.IGNORECASE)
RE_HORA  = re.compile(r"(\d{1,2})[:\.](\d{2})")

def extraer_fecha_desde_nombre(filename: str) -> dt.datetime:
    """
    Detecta mes/año desde el nombre del archivo.
    Si no encuentra, usa mes/año actual.
    Retorna datetime(anio, mes, 1).
    """
    name = (filename or "").upper()
    hoy = dt.datetime.now()
    anio = hoy.year
    mes = hoy.month

    m_anio = re.search(r"20\d{2}", name)
    if m_anio:
        anio = int(m_anio.group(0))

    for k, v in MESES.items():
        if k in name:
            mes = v
            break

    return dt.datetime(anio, mes, 1)

def limpiar_texto(x) -> str:
    if x is None or pd.isna(x):
        return ""
    s = str(x).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s

def detectar_torre(texto: str):
    if not texto:
        return None
    m = RE_TORRE.search(texto)
    if not m:
        return None
    t = int(m.group(1))
    return t if t in (1, 2, 3) else None

def extraer_hora_si_es_muestra(texto: str):
    """
    Retorna datetime.time SOLO si el texto contiene 'TOMA' y una hora HH:MM.
    """
    if not texto:
        return None
    t = texto.upper()
    if "TOMA" not in t:
        return None

    m = RE_HORA.search(t)
    if not m:
        return None

    h = int(m.group(1))
    mm = int(m.group(2))
    if 0 <= h <= 23 and 0 <= mm <= 59:
        return dt.time(h, mm)
    return None

def procesar_bitacora_completa(contenido, filename, fecha_manual=None):
    """
    - Lee día + U (turno A) + V (turno B)
    - Por día/turno detecta 1 hora global de 'TOMA...'
    - Inserta SOLO 3 registros por turno (torre 1..3)
    - comentario: SOLO texto de torre (no incluye 'TOMA...')
    - ts_toma_muestra: si hay hora del día -> esa, si no -> forward-fill desde última válida por (torre, turno)
    """
    fecha_ref = fecha_manual if fecha_manual else extraer_fecha_desde_nombre(filename)
    anio, mes = fecha_ref.year, fecha_ref.month

    try:
        bio = io.BytesIO(contenido)
        df = pd.read_excel(bio, sheet_name=0, header=None, usecols=[1, 20, 21])
    except Exception as e:
        return None, f"Error Excel: {e}"

    start_row = 6
    df = df.iloc[start_row:].copy()
    df.columns = ["dia_raw", "txt_u", "txt_v"]
    df["dia_raw"] = df["dia_raw"].ffill()

    def parse_dia(x):
        if pd.isna(x):
            return None
        s = str(x).split(".")[0].strip()
        return int(s) if s.isdigit() else None

    df["dia"] = df["dia_raw"].apply(parse_dia)
    df = df[df["dia"].notna()].copy()

    reg = {}      # (fecha, torre, turno) -> fila
    last_ts = {}  # (torre, turno) -> datetime

    for dia, g in df.groupby("dia", sort=True):
        try:
            fecha_base = dt.date(anio, mes, int(dia))
        except:
            continue

        for turno, col in [("A", "txt_u"), ("B", "txt_v")]:
            # 1) Hora global del día-turno (si existe)
            hora_muestra = None
            for x in g[col].tolist():
                texto = limpiar_texto(x)
                h = extraer_hora_si_es_muestra(texto)
                if h:
                    hora_muestra = h
                    break

            ts_muestra = None
            if hora_muestra:
                ts_muestra = dt.datetime.combine(fecha_base, hora_muestra)
                if turno == "B" and hora_muestra.hour < 12:
                    ts_muestra += dt.timedelta(days=1)

            # 2) Registros por torre
            for x in g[col].tolist():
                texto = limpiar_texto(x)
                if not texto:
                    continue

                torre = detectar_torre(texto)
                if torre is None:
                    # Aquí caen las líneas "TOMA..." sin torre: NO crean registro y NO van a comentario
                    continue

                key = (fecha_base, int(torre), turno)
                if key not in reg:
                    reg[key] = {
                        "fecha_calendario": fecha_base,
                        "torre": int(torre),
                        "turno": turno,
                        "ts_toma_muestra": None,
                        "comentario": None,
                        "nombre_archivo": filename
                    }

                # comentario SOLO texto torre
                reg[key]["comentario"] = texto

                # ts: muestra del día si existe; si no, hereda última válida por (torre, turno)
                if ts_muestra is not None:
                    reg[key]["ts_toma_muestra"] = ts_muestra
                    last_ts[(int(torre), turno)] = ts_muestra
                else:
                    reg[key]["ts_toma_muestra"] = last_ts.get((int(torre), turno), None)

    df_out = pd.DataFrame(list(reg.values()))
    df_out = df_out.sort_values(["fecha_calendario", "torre", "turno"]).reset_index(drop=True)

    return df_out, f"Mes procesado: {fecha_ref.strftime('%B %Y')} | Registros: {len(df_out)}"

def guardar_bitacora_bd(df):
    if df is None or df.empty:
        return False, "No hay datos para guardar."

    engine = get_engine()
    ESQUEMA = "inventar_SpcHidr"
    TABLA = "bitacora_turnos_consolidada"

    fmin = pd.to_datetime(df["fecha_calendario"]).min().date()
    fmax = pd.to_datetime(df["fecha_calendario"]).max().date()

    try:
        with engine.begin() as conn:
            # Limpieza del rango para permitir recargas sin conflicto del índice único
            conn.execute(
                text(f"""
                    DELETE FROM {ESQUEMA}.{TABLA}
                    WHERE fecha_calendario BETWEEN :fmin AND :fmax
                """),
                {"fmin": fmin, "fmax": fmax}
            )

            df.to_sql(
                name=TABLA,
                schema=ESQUEMA,
                con=conn,
                if_exists="append",
                index=False
            )

        return True, f"Se insertaron {len(df)} registros en {ESQUEMA}.{TABLA} (rango {fmin} a {fmax})."
    except Exception as e:
        return False, f"Error al guardar en BD: {e}"