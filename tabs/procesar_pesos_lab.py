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
    "JULIO": 7, "AGOSTO": 8, "SEPTIEMBRE": 9, "OCTUBRE": 10,
    "NOVIEMBRE": 11, "DICIEMBRE": 12
}

RE_TORRE = re.compile(r"\bTORRE\s*(\d+)\b", re.IGNORECASE)
RE_HORA = re.compile(r"(\d{1,2})[:\.](\d{2})")


def convertir_fecha_excel(valor, fecha_manual=None):
    """
    Convierte una fecha desde Excel serial, datetime, date o string.
    """
    if pd.isna(valor):
        return None

    if isinstance(valor, (dt.datetime, dt.date)):
        return pd.to_datetime(valor).date()

    if isinstance(valor, (int, float)):
        return pd.to_datetime(valor, unit="D", origin="1899-12-30").date()

    try:
        return pd.to_datetime(valor).date()
    except Exception:
        if fecha_manual is not None:
            return fecha_manual.date() if hasattr(fecha_manual, "date") else fecha_manual
        return None


def extraer_hora(texto):
    """
    Extrae horas desde textos como:
    'TOMA DE MUESTRA A LAS 18:30 H.'
    'TOMA DE MUESTRA A LAS 7:20 HRS.'
    """
    if texto is None or pd.isna(texto):
        return None

    texto = str(texto)
    m = RE_HORA.search(texto)

    if not m:
        return None

    hora = int(m.group(1))
    minuto = int(m.group(2))

    if hora > 23 or minuto > 59:
        return None

    return dt.time(hora, minuto)


def limpiar_texto(valor):
    """
    Limpia celdas vacías, NaN o textos nulos.
    Devuelve None cuando no hay contenido válido.
    """
    if valor is None or pd.isna(valor):
        return None

    texto = str(valor).strip()

    if texto == "" or texto.lower() in ["nan", "none"]:
        return None

    return texto


def extraer_fecha_desde_nombre(filename: str) -> dt.datetime:
    """
    Intenta detectar año y mes desde el nombre del archivo.
    Si no encuentra, usa mes/año actual.
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


def detectar_torre(texto: str):
    """
    Detecta textos tipo TORRE 1, TORRE 2, TORRE 3.
    """
    if not texto:
        return None

    m = RE_TORRE.search(texto)

    if not m:
        return None

    t = int(m.group(1))

    return t if t in (1, 2, 3) else None


def extraer_hora_si_es_muestra(texto: str):
    """
    Extrae hora solo si el texto contiene la palabra TOMA.
    Se conserva por compatibilidad con versiones anteriores.
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


def construir_ts_por_turno(fecha_base: dt.date, turno: str, hora: dt.time) -> dt.datetime:
    """
    Reglas:
    - Turno A: la muestra pertenece al mismo día operacional.
    - Turno B: si la muestra es en la madrugada, pertenece al día calendario siguiente.

    Ejemplo:
    fecha_base = 2026-01-03
    turno = B
    hora = 07:25
    resultado = 2026-01-04 07:25
    """
    ts = dt.datetime.combine(fecha_base, hora)

    if turno == "B" and hora.hour < 12:
        ts += dt.timedelta(days=1)

    return ts

def procesar_bitacora_completa(decoded, filename, fecha_manual=None):
    """
    Procesa dinámicamente la hoja 'Pesos y Novedades' del Excel Peso Torre.

    Lógica:
    - Detecta las fechas en columna B.
    - Cada fecha define un bloque hasta la siguiente fecha.
    - Dentro del bloque busca comentarios por torre y horario de toma de muestra.
    - Si existe "TOMA DE MUESTRA A LAS HH:MM", usa esa hora real.
    - Si no existe hora explícita, usa horario estándar:
        Turno A -> 20:00 del mismo día
        Turno B -> 08:00 del día siguiente
    - Conserva días detenidos o sin muestra explícita para que no desaparezcan del reporte.
    """
    try:
        df = pd.read_excel(
            io.BytesIO(decoded),
            sheet_name="Pesos y Novedades",
            header=None
        )
    except Exception as e:
        return None, f"No se pudo leer la hoja 'Pesos y Novedades': {e}"

    registros = []

    # En el archivo, los datos empiezan aproximadamente en la fila Excel 7.
    # En pandas eso corresponde al índice 6.
    fila_inicio = 6

    # Columnas de novedades:
    # U = índice 20 = Turno A
    # V = índice 21 = Turno B
    config_turnos = {
        "A": 20,
        "B": 21
    }

    # ------------------------------------------------------------------
    # 1) Detectar dinámicamente todas las filas que contienen fecha
    # ------------------------------------------------------------------
    filas_fecha = []

    for idx in range(fila_inicio, len(df)):
        fecha_raw = df.iat[idx, 1] if df.shape[1] > 1 else None
        fecha = convertir_fecha_excel(fecha_raw, fecha_manual)

        if fecha is not None:
            filas_fecha.append((idx, fecha))

    if not filas_fecha:
        return None, (
            "No se encontraron fechas válidas en la hoja 'Pesos y Novedades'. "
            "Verifica que las fechas estén en la columna B."
        )

    # ------------------------------------------------------------------
    # 2) Funciones internas auxiliares
    # ------------------------------------------------------------------
    def textos_columna_bloque(row_ini, row_fin, col):
        """
        Obtiene textos no vacíos de una columna específica dentro del bloque.
        """
        textos = []

        if col >= df.shape[1]:
            return textos

        for r in range(row_ini, row_fin):
            valor = limpiar_texto(df.iat[r, col])
            if valor is not None:
                textos.append(valor)

        return textos

    def buscar_hora_muestra(textos):
        """
        Busca el texto 'TOMA DE MUESTRA...' y extrae la hora.
        Si no aparece, devuelve None.
        """
        for texto in textos:
            texto_upper = texto.upper()

            if "TOMA" in texto_upper and "MUESTRA" in texto_upper:
                hora = extraer_hora(texto)
                if hora is not None:
                    return hora

        return None

    def separar_comentarios(textos):
        """
        Separa comentarios por torre y comentarios generales.

        Devuelve:
            comentarios_torre = {1: texto, 2: texto, 3: texto}
            comentarios_generales = [textos generales]
        """
        comentarios_torre = {
            1: [],
            2: [],
            3: []
        }

        comentarios_generales = []

        for texto in textos:
            texto_upper = texto.upper()

            # No usar la frase de toma de muestra como comentario operacional
            if "TOMA" in texto_upper and "MUESTRA" in texto_upper:
                continue

            torre_detectada = detectar_torre(texto)

            if torre_detectada in comentarios_torre:
                comentarios_torre[torre_detectada].append(texto)
            else:
                comentarios_generales.append(texto)

        return comentarios_torre, comentarios_generales

    def comentario_final_para_torre(comentarios_torre, comentarios_generales, torre):
        """
        Construye comentario final para una torre.
        Si no hay comentario específico de torre, usa comentarios generales.
        Si tampoco hay comentarios generales, deja 'SIN REGISTRO'.
        """
        partes = []

        if comentarios_torre.get(torre):
            partes.extend(comentarios_torre[torre])

        if comentarios_generales:
            partes.extend(comentarios_generales)

        if not partes:
            return "SIN REGISTRO"

        # Eliminar duplicados conservando orden
        partes_limpias = []
        for p in partes:
            if p not in partes_limpias:
                partes_limpias.append(p)

        return " | ".join(partes_limpias)

    def ts_estandar(fecha_base, turno):
        """
        Horario estándar si no existe toma explícita.
        """
        if turno == "A":
            return dt.datetime.combine(fecha_base, dt.time(20, 0))

        if turno == "B":
            return dt.datetime.combine(
                fecha_base + dt.timedelta(days=1),
                dt.time(8, 0)
            )

        return None

    # ------------------------------------------------------------------
    # 3) Procesar cada bloque fecha -> siguiente fecha
    # ------------------------------------------------------------------
    for pos, (row_ini, fecha_calendario) in enumerate(filas_fecha):
        if pos + 1 < len(filas_fecha):
            row_fin = filas_fecha[pos + 1][0]
        else:
            row_fin = len(df)

        for turno, col_novedad in config_turnos.items():
            textos = textos_columna_bloque(row_ini, row_fin, col_novedad)

            # Hora real si existe "TOMA DE MUESTRA A LAS..."
            hora_muestra = buscar_hora_muestra(textos)

            if hora_muestra is not None:
                ts_toma_muestra = construir_ts_por_turno(
                    fecha_base=fecha_calendario,
                    turno=turno,
                    hora=hora_muestra
                )
            else:
                # Si no hay hora explícita, no dejamos perder el día:
                # usamos horario estándar del turno.
                ts_toma_muestra = ts_estandar(fecha_calendario, turno)

            comentarios_torre, comentarios_generales = separar_comentarios(textos)

            # Siempre generamos T1, T2 y T3 para conservar el día,
            # incluso si el bloque no trae comentario específico para una torre.
            for torre in [1, 2, 3]:
                comentario = comentario_final_para_torre(
                    comentarios_torre=comentarios_torre,
                    comentarios_generales=comentarios_generales,
                    torre=torre
                )

                registros.append({
                    "fecha_calendario": fecha_calendario,
                    "fecha_turno": fecha_calendario,
                    "torre": torre,
                    "turno": turno,
                    "ts_toma_muestra": ts_toma_muestra,
                    "comentario": comentario,
                    "nombre_archivo": filename
                })

    if not registros:
        return None, (
            "No se encontraron novedades válidas en la hoja 'Pesos y Novedades'. "
            "Verifica que el archivo mantenga el formato esperado."
        )

    df_out = pd.DataFrame(registros)

    columnas_esperadas = [
        "fecha_calendario",
        "fecha_turno",
        "torre",
        "turno",
        "ts_toma_muestra",
        "comentario",
        "nombre_archivo"
    ]

    faltantes = [col for col in columnas_esperadas if col not in df_out.columns]

    if faltantes:
        return None, (
            f"El procesamiento generó una tabla incompleta. "
            f"Columnas faltantes: {', '.join(faltantes)}. "
            f"Columnas generadas: {', '.join(df_out.columns)}"
        )
    
        df_out = df_out[columnas_esperadas]

    # ------------------------------------------------------------
    # Evitar duplicados por fecha_turno + torre + turno
    # Algunos días del Excel pueden tener bloques irregulares o fechas repetidas.
    # La tabla SQL tiene índice único para fecha_turno, torre y turno.
    # ------------------------------------------------------------
    df_out = (
        df_out
        .groupby(["fecha_turno", "torre", "turno"], as_index=False)
        .agg({
            "fecha_calendario": "first",
            "ts_toma_muestra": "first",
            "comentario": lambda x: " | ".join(
                dict.fromkeys(
                    str(v).strip()
                    for v in x
                    if pd.notna(v) and str(v).strip() not in ["", "nan", "None"]
                )
            ),
            "nombre_archivo": "first"
        })
    )

    df_out = df_out[
        [
            "fecha_calendario",
            "fecha_turno",
            "torre",
            "turno",
            "ts_toma_muestra",
            "comentario",
            "nombre_archivo"
        ]
    ]

    df_out = df_out.sort_values(
        ["fecha_calendario", "turno", "torre"]
    ).reset_index(drop=True)

    return df_out, f"Bitácora procesada correctamente: {len(df_out)} registros generados."

def guardar_bitacora_bd(df):
    """
    Guarda la bitácora procesada en inventar_SpcHidr.bitacora_turnos_consolidada.
    Borra previamente el rango de fecha_turno cargado para evitar duplicados.
    """
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

        return True, (
            f"Se insertaron {len(df_ins)} registros en {ESQUEMA}.{TABLA} "
            f"(rango fecha_turno {fmin} a {fmax})."
        )

    except Exception as e:
        return False, f"Error al guardar en BD: {e}"


def procesar_pesos_reales_torre(contenido, filename, fecha_manual=None):
    """
    Extrae pesos reales desde el Excel Peso Torre.

    Resultado:
        Fecha | Turno | Torre | PesoReal_Quimico | PesoReal_Fisico | nombre_archivo

    Regla:
        Peso físico = retiro físico 1 + retiro físico 2.
        Si un valor físico viene en gramos, por ejemplo 14765, se interpreta como 14.765 kg.
    """
    fecha_ref = fecha_manual if fecha_manual else extraer_fecha_desde_nombre(filename)
    anio, mes = fecha_ref.year, fecha_ref.month

    try:
        bio = io.BytesIO(contenido)
        df = pd.read_excel(bio, sheet_name=0, header=None)
    except Exception as e:
        return None, f"Error Excel pesos reales: {e}"

    start_row = 6
    registros = []

    def to_num(x):
        if x is None or pd.isna(x):
            return 0.0
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return 0.0

    def val_quimico(row, col):
        if row is None or col >= df.shape[1]:
            return 0.0
        return to_num(df.iat[row, col])

    def val_fisico(row, col):
        if row is None or col >= df.shape[1]:
            return 0.0

        num = to_num(df.iat[row, col])

        if num > 1000:
            num = num / 1000.0

        return num

    for r in range(start_row, len(df)):
        fecha_raw = df.iat[r, 1] if df.shape[1] > 1 else None

        if pd.isna(fecha_raw):
            continue

        try:
            fecha = pd.to_datetime(fecha_raw).date()
        except Exception:
            continue

        # Procesar solo el mes/año del archivo.
        if fecha.year != anio or fecha.month != mes:
            continue

        # Segunda fila de retiro físico del mismo día.
        r2 = r + 2 if r + 2 < len(df) else None

        # T1 Turno A
        registros.append({
            "Fecha": fecha,
            "Turno": "A",
            "Torre": "T1",
            "PesoReal_Quimico": val_quimico(r, 2),
            "PesoReal_Fisico": val_fisico(r, 4) + val_fisico(r2, 4),
            "nombre_archivo": filename
        })

        # T1 Turno B
        registros.append({
            "Fecha": fecha,
            "Turno": "B",
            "Torre": "T1",
            "PesoReal_Quimico": val_quimico(r, 5),
            "PesoReal_Fisico": val_fisico(r, 7) + val_fisico(r2, 7),
            "nombre_archivo": filename
        })

        # T2 Turno A
        registros.append({
            "Fecha": fecha,
            "Turno": "A",
            "Torre": "T2",
            "PesoReal_Quimico": val_quimico(r, 8),
            "PesoReal_Fisico": val_fisico(r, 10) + val_fisico(r2, 10),
            "nombre_archivo": filename
        })

        # T2 Turno B
        registros.append({
            "Fecha": fecha,
            "Turno": "B",
            "Torre": "T2",
            "PesoReal_Quimico": val_quimico(r, 11),
            "PesoReal_Fisico": val_fisico(r, 13) + val_fisico(r2, 13),
            "nombre_archivo": filename
        })

    
    df_out = pd.DataFrame(registros)

    if df_out.empty:
        return None, "No se encontraron pesos reales."

    # ------------------------------------------------------------
    # Evitar duplicados por Fecha + Turno + Torre.
    # Algunos bloques irregulares del Excel pueden generar filas
    # repetidas para la misma combinación.
    #
    # En los duplicados observados, normalmente aparece una fila en 0
    # y otra con el valor válido, por eso se conserva el valor máximo.
    # ------------------------------------------------------------
    df_out = (
        df_out
        .groupby(["Fecha", "Turno", "Torre"], as_index=False)
        .agg({
            "PesoReal_Quimico": "max",
            "PesoReal_Fisico": "max",
            "nombre_archivo": "first"
        })
    )

    df_out = df_out.sort_values(
        ["Fecha", "Turno", "Torre"]
    ).reset_index(drop=True)

    return df_out, f"Pesos reales procesados: {len(df_out)} registros."

def guardar_pesos_reales_bd(df):
    """
    Guarda pesos reales en inventar_SpcHidr.peso_real_torre_turno.
    Borra previamente el rango de fechas cargado para evitar duplicados.
    """
    if df is None or df.empty:
        return False, "No hay pesos reales para guardar."

    engine = get_engine()
    ESQUEMA = "inventar_SpcHidr"
    TABLA = "peso_real_torre_turno"

    df = df.copy()
    df["Fecha"] = pd.to_datetime(df["Fecha"]).dt.date

    fmin = df["Fecha"].min()
    fmax = df["Fecha"].max()

    cols_insert = [
        "Fecha",
        "Turno",
        "Torre",
        "PesoReal_Quimico",
        "PesoReal_Fisico",
        "nombre_archivo"
    ]

    df_ins = df[cols_insert]

    try:
        with engine.begin() as conn:
            conn.execute(
                text(f"""
                    DELETE FROM {ESQUEMA}.{TABLA}
                    WHERE Fecha BETWEEN :fmin AND :fmax
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

        return True, f"Se insertaron {len(df_ins)} registros en {ESQUEMA}.{TABLA} entre {fmin} y {fmax}."
    
    except Exception as e:
        return False, f"Error al guardar pesos reales en BD: {e}"