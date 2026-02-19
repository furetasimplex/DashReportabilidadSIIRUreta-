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
RE_HORA = re.compile(r"(\d{1,2})[:\.](\d{2})")


def extraer_fecha_desde_nombre(filename: str) -> dt.datetime:
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


def construir_ts_por_turno(fecha_base: dt.date, turno: str, hora: dt.time) -> dt.datetime:
    """
    Reglas:
    - Turno A: ts en fecha_base con esa hora.
    - Turno B: si la hora es madrugada (<12), ts en fecha_base + 1; si no, en fecha_base.
    """
    ts = dt.datetime.combine(fecha_base, hora)
    if turno == "B" and hora.hour < 12:
        ts += dt.timedelta(days=1)
    return ts


def procesar_bitacora_completa(contenido, filename, fecha_manual=None):
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

    reg = {}  # (fecha_calendario, turno, torre) -> fila

    # En vez de guardar datetime completo, guardamos la ÚLTIMA HORA válida por (torre, turno)
    last_hora = {}  # (torre, turno) -> dt.time

    for dia, g in df.groupby("dia", sort=True):
        try:
            fecha_base = dt.date(anio, mes, int(dia))
        except Exception:
            continue

        for turno, col in [("A", "txt_u"), ("B", "txt_v")]:
            # 1) Hora global del día-turno desde línea 'TOMA...'
            hora_muestra = None
            for x in g[col].tolist():
                texto = limpiar_texto(x)
                h = extraer_hora_si_es_muestra(texto)
                if h:
                    hora_muestra = h
                    break

            # 2) Comentarios por torre (solo líneas TORRE X)
            comentarios_torre = {}
            for x in g[col].tolist():
                texto = limpiar_texto(x)
                if not texto:
                    continue
                torre = detectar_torre(texto)
                if torre is None:
                    continue
                comentarios_torre[int(torre)] = texto

            # 3) Garantizar 3 torres
            for torre in (1, 2, 3):
                key = (fecha_base, turno, torre)

                # Si hay hora del día-turno: esa manda
                if hora_muestra is not None:
                    ts_final = construir_ts_por_turno(fecha_base, turno, hora_muestra)
                    last_hora[(torre, turno)] = hora_muestra
                else:
                    # Fallback: usar última hora válida del mismo (torre, turno), pero con fecha del día actual
                    h_prev = last_hora.get((torre, turno), None)
                    ts_final = construir_ts_por_turno(fecha_base, turno, h_prev) if h_prev else None

                reg[key] = {
                    "fecha_calendario": fecha_base,
                    "fecha_turno": fecha_base,  # día operacional base
                    "torre": torre,
                    "turno": turno,
                    "ts_toma_muestra": ts_final,
                    "comentario": comentarios_torre.get(torre, None),
                    "nombre_archivo": filename
                }

    df_out = pd.DataFrame(list(reg.values()))
    df_out = df_out.sort_values(["fecha_calendario", "turno", "torre"]).reset_index(drop=True)

    return df_out, f"Mes procesado: {fecha_ref.strftime('%B %Y')} | Registros: {len(df_out)}"


def guardar_bitacora_bd(df):
    if df is None or df.empty:
        return False, "No hay datos para guardar."

    engine = get_engine()
    ESQUEMA = "inventar_SpcHidr"
    TABLA = "bitacora_turnos_consolidada"

    df = df.copy()
    df["fecha_calendario"] = pd.to_datetime(df["fecha_calendario"]).dt.date
    df["fecha_turno"] = pd.to_datetime(df["fecha_turno"]).dt.date

    fmin = df["fecha_turno"].min()
    fmax = df["fecha_turno"].max()

    cols_insert = [
        "fecha_calendario",
        "fecha_turno",
        "torre",
        "turno",
        "ts_toma_muestra",
        "comentario",
        "nombre_archivo"
    ]
    df_ins = df[cols_insert]

    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"""
                    DELETE FROM {ESQUEMA}.{TABLA}
                    WHERE fecha_turno BETWEEN :fmin AND :fmax
                """),
                {"fmin": fmin, "fmax": fmax}
            )

            df_ins.to_sql(
                name=TABLA,
                schema=ESQUEMA,
                con=conn,
                if_exists="append",
                index=False
            )

        return True, f"Se insertaron {len(df_ins)} registros en {ESQUEMA}.{TABLA} (rango fecha_turno {fmin} a {fmax})."

    except Exception as e:
        return False, f"Error al guardar en BD: {e}"
