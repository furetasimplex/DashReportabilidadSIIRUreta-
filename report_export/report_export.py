import os
import pandas as pd
import numpy as np
from datetime import date
try:
    from db_connection import get_connection  # usa tu DB_CONNECTION
except Exception as e:
    raise RuntimeError("No se pudo importar get_connection desde db_connection.py") from e

# Nombre completo de la tabla (ajusta si cambia)
TABLE_FQN = "[inventar_SpcHidr].[Datos_conciliados_of]"
TABLE_DATOS_CONCILIADOS = "[inventar_SpcHidr].[inventar_SpcHidr].[Datos_conciliados_of]"
# Ruta del logo BHP
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)

BHP_LOGO_PATH = os.path.join(PROJECT_DIR, "assets", "logoBHP.png")
# Columnas exactas para el reporte "Producción Diaria" / plantilla Datos conciliados
COLUMNAS_DATOS_CONCILIADOS = [
    "Fecha", "Chancado_TMS_Real", "Humedad_Turno_A", "Humedad_Turno_B", "Humedad_promedio_dia",
    "Sal_turno_A", "Sal_Turno_B", "Sal_promedio_dia",
    "Apilado_TMH_turno_A", "Apilado_TMH_turno_B", "Apilado_TMH_promedio_dia",
    "Apilado_TMS_Real", "Apilado_TMS_Plan", "Campana_apilado", "Modulo_apilado", "Avance_apilado",
    "Ley_CuT_Real", "Ley_CuT_Plan", "Cobre_fino_Apilado_Real", "Cobre_fino_Apilado_Plan",
    "TMS_Rotopala_1_Real", "TMS_Rotopala_1_Plan", "Campana_reclamo_oxidos", "Modulo_reclamo_oxidos", "Avance_reclamo_oxidos",
    "TMS_Rotopala_2_Real", "TMS_Rotopala_2_Plan", "Campana_reclamo_sulfuros", "modulo_reclamo_sulfuros", "Avance_reclamo_sulfuros",
    "Camiones_TMS_Reclamo_Oxidos", "Camiones_TMS_Reclamo_Sulfuros", "Movido", "Extraido",
    "Camiones_TMS_total", "Camiones_TMS_plan", "Campana_reclamo_camiones", "Modulo_reclamo_camiones",
    "Total_Ripios_Incluye_Camiones_Real", "Total_Ripios_Incluye_Camiones_Plan",
    "Produccion_Catodos_Real", "Produccion_Catodos_Plan","Estado"
]


def first_day_of_month(d: date) -> date:
    return date(d.year, d.month, 1)


def fetch_report_data(end_date: date) -> pd.DataFrame:
    """
    Lee desde SQL Server usando lo que devuelva get_connection():

      - Si get_connection() devuelve un Engine SQLAlchemy:
            usa sqlalchemy.text + .connect()

      - Si get_connection() devuelve una conexión DBAPI (pyodbc.Connection, etc.):
            usa query string simple + parámetros posicionales (?).

    Trae datos desde el día 1 del mes de end_date hasta end_date (inclusive)
    y añade/normaliza la columna 'es_preliminar'.
    """
    start_date = first_day_of_month(end_date)
    conn_or_engine = get_connection()

    if conn_or_engine is None:
        raise RuntimeError("get_connection() devolvió None: revisar DB_CONNECTION.")

    # Versión DBAPI (pyodbc) → placeholders '?'
    sql_dbapi = f"""
    SELECT *
    FROM {TABLE_FQN}
    WHERE [Fecha] BETWEEN ? AND ?
    ORDER BY [Fecha] ASC
    """

    # Versión SQLAlchemy → placeholders ':start' y ':end'
    sql_sa = f"""
    SELECT *
    FROM {TABLE_FQN}
    WHERE [Fecha] BETWEEN :start AND :end
    ORDER BY [Fecha] ASC
    """

    try:
        # Caso 1: conexión DBAPI (pyodbc, etc.) → tiene cursor()
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(start_date, end_date),
            )

        # Caso 2: Engine SQLAlchemy → tiene connect(), pero normalmente NO cursor()
        else:
            from sqlalchemy import text  # solo si de verdad usamos SA
            with conn_or_engine.connect() as conn:  # type: ignore[attr-defined]
                df = pd.read_sql(
                    text(sql_sa),
                    conn,
                    params={"start": start_date, "end": end_date},
                )

    except Exception as e:
        raise RuntimeError(f"Error al conectar/leer SQL Server en fetch_report_data: {e}") from e

    # ===== Manejar columna es_preliminar =====
    prelim = None
    for candidate in ["es_preliminar", "preliminar", "estado"]:
        if candidate in df.columns:
            prelim = candidate
            break

    if prelim is None:
        df["es_preliminar"] = False
    else:
        if df[prelim].dtype == bool:
            df["es_preliminar"] = df[prelim]
        else:
            df["es_preliminar"] = df[prelim].astype(str).str.lower().isin(
                ["1", "true", "sí", "si", "preliminar", "preliminary", "pre"]
            )

    # Dejamos Fecha y es_preliminar al inicio
    cols = list(df.columns)
    ordered = []
    for c in ["Fecha", "es_preliminar"]:
        if c in cols:
            ordered.append(c)
            cols.remove(c)
    ordered.extend(cols)

    return df[ordered]


def fetch_datos_conciliados_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta exacta para el reporte de Producción Diaria / plantilla Datos conciliados.
    Respeta el rango de fechas seleccionado (fecha inicio y fecha final).
    """
    conn_or_engine = get_connection()
    if conn_or_engine is None:
        raise RuntimeError("get_connection() devolvió None: revisar conexión a la base de datos.")

    cols = ", ".join(f"[{c}]" for c in COLUMNAS_DATOS_CONCILIADOS)
    sql_dbapi = f"""
    SELECT {cols}
    FROM {TABLE_DATOS_CONCILIADOS}
    WHERE [Fecha] BETWEEN ? AND ?
    ORDER BY [Fecha] ASC
    """
    sql_sa = f"""
    SELECT {cols}
    FROM {TABLE_DATOS_CONCILIADOS}
    WHERE [Fecha] BETWEEN :start AND :end
    ORDER BY [Fecha] ASC
    """

    try:
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(start_date, end_date),
            )
        else:
            from sqlalchemy import text
            with conn_or_engine.connect() as conn:
                df = pd.read_sql(
                    text(sql_sa),
                    conn,
                    params={"start": start_date, "end": end_date},
                )
    except Exception as e:
        raise RuntimeError(f"Error al leer Datos_conciliados_of: {e}") from e

    # Asegurar orden de columnas
    df = df[[c for c in COLUMNAS_DATOS_CONCILIADOS if c in df.columns]]
    return df

def fetch_representatividad_torres_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta el reporte rápido de representatividad de torres desde procedimiento almacenado.
    Lee desde la tabla física representatividad_torres_resultado mediante:
    inventar_SpcHidr.sp_reporte_representatividad_torres
    """
    conn_or_engine = get_connection()

    if conn_or_engine is None:
        raise RuntimeError("get_connection() devolvió None: revisar conexión a la base de datos.")

    sql_dbapi = """
    EXEC inventar_SpcHidr.sp_reporte_representatividad_torres
        @fecha_inicio = ?,
        @fecha_fin = ?
    """

    sql_sa = """
    EXEC inventar_SpcHidr.sp_reporte_representatividad_torres
        @fecha_inicio = :start,
        @fecha_fin = :end
    """

    try:
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(start_date, end_date),
            )
        else:
            from sqlalchemy import text
            with conn_or_engine.connect() as conn:
                df = pd.read_sql(
                    text(sql_sa),
                    conn,
                    params={"start": start_date, "end": end_date},
                )

    except Exception as e:
        raise RuntimeError(f"Error al leer representatividad de torres: {e}") from e

    return df
def fetch_reporte_turno_report(start_date: date, end_date: date) -> pd.DataFrame:
    """
    Consulta el reporte por turno desde el procedimiento almacenado:

        inventar_SpcHidr.sp_reporte_turno_test

    Importante:
    El procedimiento trabaja con lógica:
        Fecha >= @fecha_inicio
        Fecha <  @fecha_fin
    """

    conn_or_engine = get_connection()

    if conn_or_engine is None:
        raise RuntimeError("get_connection() devolvió None: revisar conexión a la base de datos.")

    sql_dbapi = """
    EXEC inventar_SpcHidr.sp_reporte_turno_test
        @fecha_inicio = ?,
        @fecha_fin = ?
    """

    sql_sa = """
    EXEC inventar_SpcHidr.sp_reporte_turno_test
        @fecha_inicio = :start,
        @fecha_fin = :end
    """

    try:
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(start_date, end_date),
            )
        else:
            from sqlalchemy import text
            with conn_or_engine.connect() as conn:
                df = pd.read_sql(
                    text(sql_sa),
                    conn,
                    params={"start": start_date, "end": end_date},
                )

    except Exception as e:
        raise RuntimeError(f"Error al leer reporte por turno: {e}") from e

    return df


def fetch_reporte_turno_cache(start_date: date, end_date: date) -> pd.DataFrame: 
    """
    Consulta el reporte por turno desde la tabla cache:

        inventar_SpcHidr.reporte_turno_cache

    Mucho más rápido que ejecutar el SP completo.
    """

    conn_or_engine = get_connection()

    if conn_or_engine is None:
        raise RuntimeError("get_connection() devolvió None: revisar conexión a la base de datos.")

    sql_dbapi = """
    SELECT
        Fecha,
        Campania,
        Material,
        Modulo,
        Avance,
        Turno,
        Apilado_TMS_Real,
        Apilado_TMS_Plan_Mensual,
        STOCK,
        MINA,
        SRR,
        CuT_Real,
        CuT_Plan_Mensual,
        CuT_Plan_Semanal,
        CuS_Real,
        CuS_Plan_Mensual,
        CuS_Plan_Semanal,
        Solubilidad_Real,
        Solubilidad_Plan_Mensual,
        Solubilidad_Plan_Semanal,
        CO3_Real,
        CO3_Plan_Mensual,
        CO3_Plan_Semanal,
        CuFe_Real,
        CuFe_Plan_Mensual,
        CuFe_Plan_Semanal,
        FeT_Real,
        FeS_Real,
        ConsH_Real,
        Malla_Menos_1_2_Real,
        Malla_Menos_1_2_Plan_Semanal,
        Malla_Menos_100_Real,
        Malla_Menos_100_Plan_Mensual,
        Malla_Menos_100_Plan_Semanal,
        CaolBeta_Real,
        CaolBeta_Plan_Mensual,
        CaolBeta_Plan_Semanal,
        Dosis_Acido_Ideal_TM,
        Dosis_Acido_Programa_Semanal,
        Muestra_Quimica,
        Muestra_Fisica
    FROM inventar_SpcHidr.reporte_turno_cache
    WHERE Fecha >= ?
      AND Fecha < ?
    ORDER BY Fecha, Turno;
    """

    sql_sa = """
    SELECT
        Fecha,
        Campania,
        Material,
        Modulo,
        Avance,
        Turno,
        Apilado_TMS_Real,
        Apilado_TMS_Plan_Mensual,
        STOCK,
        MINA,
        SRR,
        CuT_Real,
        CuT_Plan_Mensual,
        CuT_Plan_Semanal,
        CuS_Real,
        CuS_Plan_Mensual,
        CuS_Plan_Semanal,
        Solubilidad_Real,
        Solubilidad_Plan_Mensual,
        Solubilidad_Plan_Semanal,
        CO3_Real,
        CO3_Plan_Mensual,
        CO3_Plan_Semanal,
        CuFe_Real,
        CuFe_Plan_Mensual,
        CuFe_Plan_Semanal,
        FeT_Real,
        FeS_Real,
        ConsH_Real,
        Malla_Menos_1_2_Real,
        Malla_Menos_1_2_Plan_Semanal,
        Malla_Menos_100_Real,
        Malla_Menos_100_Plan_Mensual,
        Malla_Menos_100_Plan_Semanal,
        CaolBeta_Real,
        CaolBeta_Plan_Mensual,
        CaolBeta_Plan_Semanal,
        Dosis_Acido_Ideal_TM,
        Dosis_Acido_Programa_Semanal,
        Muestra_Quimica,
        Muestra_Fisica
    FROM inventar_SpcHidr.reporte_turno_cache
    WHERE Fecha >= :start
      AND Fecha < :end
    ORDER BY Fecha, Turno;
    """

    try:
        if hasattr(conn_or_engine, "cursor"):
            df = pd.read_sql(
                sql_dbapi,
                conn_or_engine,
                params=(start_date, end_date),
            )
        else:
            from sqlalchemy import text
            with conn_or_engine.connect() as conn:
                df = pd.read_sql(
                    text(sql_sa),
                    conn,
                    params={"start": start_date, "end": end_date},
                )

    except Exception as e:
        raise RuntimeError(f"Error al leer reporte por turno desde cache: {e}") from e

    return df

def preparar_df_reporte_turno_excel(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "Fecha" in df.columns:
        df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")

    if "Turno" in df.columns:
        df["Turno"] = df["Turno"].astype(str).str.upper().str.strip()
        df["Turno_excel"] = df["Turno"].map({"A": "TA", "B": "TB"}).fillna(df["Turno"])
    else:
        df["Turno_excel"] = ""

    if "Fecha" in df.columns:
        df["Fecha_Turno"] = df["Fecha"].dt.strftime("%d-%m-%Y") + " " + df["Turno_excel"]
        df["Semana"] = "Semana " + (((df["Fecha"].dt.day - 1) // 7) + 1).astype(str)
    else:
        df["Fecha_Turno"] = ""
        df["Semana"] = ""

    for col in ["STOCK", "MINA", "SRR"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            df[col] = np.where(df[col] > 1, df[col] / 100, df[col])

    return df

def export_reporte_turno_estilo_leyes_finos(df: pd.DataFrame, output):
    """
    Exporta el reporte por turno con formato visual similar al archivo:
    'Actual Reporte Leyes y Finos - Reporte por Turno'.

    Esta versión mejora:
    - Encabezados combinados tipo plantilla.
    - Grupos superiores en filas 19-22.
    - Tabla desde fila 23.
    - Celdas verticales combinadas entre TA/TB para variables comunes del día.
    """

    df = preparar_df_reporte_turno_excel(df)

    columnas = [
        "Fecha",
        "Campania",
        "Material",
        "Modulo",
        "Avance",
        "Turno_excel",

        "Apilado_TMS_Real",
        "Apilado_TMS_Plan_Mensual",

        "STOCK",
        "MINA",
        "SRR",

        "CuT_Real",
        "CuT_Plan_Mensual",
        "CuT_Plan_Semanal",

        "CuS_Real",
        "CuS_Plan_Mensual",
        "CuS_Plan_Semanal",

        "Solubilidad_Real",
        "Solubilidad_Plan_Mensual",
        "Solubilidad_Plan_Semanal",

        "CO3_Real",
        "CO3_Plan_Mensual",
        "CO3_Plan_Semanal",

        "CuFe_Real",
        "FeT_Real",
        "FeS_Real",
        "ConsH_Real",

        "Malla_Menos_1_2_Real",
        "Malla_Menos_1_2_Plan_Semanal",

        "Malla_Menos_100_Real",
        "Malla_Menos_100_Plan_Mensual",
        "Malla_Menos_100_Plan_Semanal",

        "CaolBeta_Real",
        "CaolBeta_Plan_Mensual",
        "CaolBeta_Plan_Semanal",

        "Dosis_Acido_Ideal_TM",
        "Dosis_Acido_Programa_Semanal",

        "Muestra_Quimica",
        "Muestra_Fisica",
    ]

    columnas_finales = [c for c in columnas if c in df.columns]
    df_export = df[columnas_finales].copy()
    col_offset = 2  # deja columnas A:B como margen visual
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        sheet_name = "Reporte por Turno"
        worksheet = workbook.add_worksheet(sheet_name)
        writer.sheets[sheet_name] = worksheet
        # ============================================================
        # LOGO BHP
        # ============================================================
        if os.path.exists(BHP_LOGO_PATH):
            worksheet.insert_image(
                "B1",
                BHP_LOGO_PATH,
                {
                    "x_scale": 1.15,
                    "y_scale": 1.15,
                    "x_offset": 5,
                    "y_offset": 3,
                    "object_position": 1,
                }
            )

        # ============================================================
        # FORMATOS
        # ============================================================
        fmt_titulo = workbook.add_format({
            "bold": True,
            "font_size": 16,
            "align": "left",
            "valign": "vcenter"
        })

        fmt_subtitulo = workbook.add_format({
        "bold": True,
        "font_size": 16,
        "align": "left",
        "valign": "vcenter"
        })

        fmt_grupo = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9EAF7",
            "border": 1,
            "text_wrap": True
        })

        fmt_header = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#9DC3E6",
            "font_color": "#1F4E79",
            "border": 1,
            "text_wrap": True
        })

        fmt_header_claro = workbook.add_format({
            "bold": True,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#D9EAF7",
            "font_color": "#1F4E79",
            "border": 1,
            "text_wrap": True
        })

        fmt_texto = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "text_wrap": True
        })

        fmt_texto_gris = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#F2F2F2",
            "text_wrap": True
        })

        fmt_fecha = workbook.add_format({
            "num_format": "dd-mm-yyyy",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_numero = workbook.add_format({
            "num_format": "#,##0",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_decimal = workbook.add_format({
            "num_format": "0.00",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_porcentaje = workbook.add_format({
            "num_format": "0.00%",
            "border": 1,
            "align": "center",
            "valign": "vcenter"
        })

        fmt_blanco = workbook.add_format({
            "border": 1,
            "align": "center",
            "valign": "vcenter",
            "bg_color": "#FFFFFF"
        })

        # ============================================================
        # ENCABEZADO INSTITUCIONAL
        # ============================================================
        worksheet.merge_range("G2:AM2", "Superintendencia de Medición y Reconciliación", fmt_titulo)
        worksheet.merge_range("G3:AM3", "Gerencia de Planificación de la Producción", fmt_subtitulo)
        worksheet.merge_range("G4:AM4", "Minerals Americas / Pampa Norte / Spence", fmt_subtitulo)

        # ============================================================
        # ENCABEZADOS TIPO PLANTILLA
        # Excel:
        # fila 19 -> índice 18
        # fila 20 -> índice 19
        # fila 21 -> índice 20
        # fila 22 -> índice 21
        # fila 23 datos -> índice 22
        # ============================================================

        worksheet.merge_range("N19:AC20", "Análisis Químicos", fmt_grupo)
        worksheet.merge_range("AD19:AH20", "Granulometrías", fmt_grupo)
        worksheet.merge_range("AI19:AK20", "NIR", fmt_grupo)
        worksheet.merge_range("AL19:AM20", "Dosis de ácido", fmt_grupo)
        worksheet.merge_range("AN19:AO21", "Fuentes de información", fmt_grupo)

        worksheet.merge_range("C21:C22", "Fecha", fmt_header_claro)
        worksheet.merge_range("D21:D22", "Campaña", fmt_header_claro)
        worksheet.merge_range("E21:E22", "Material", fmt_header_claro)
        worksheet.merge_range("F21:F22", "Módulo", fmt_header_claro)
        worksheet.merge_range("G21:G22", "Avance", fmt_header_claro)
        worksheet.merge_range("H21:H22", "Turno", fmt_header_claro)

        worksheet.merge_range("I21:J21", "Apilado TMS", fmt_header)
        worksheet.write("I22", "TMS", fmt_header)
        worksheet.write("J22", "Plan", fmt_header)

        worksheet.write("K21", "STOCK", fmt_header)
        worksheet.write("L21", "MINA", fmt_header)
        worksheet.write("M21", "SRR", fmt_header)
        worksheet.write("K22", "%", fmt_header)
        worksheet.write("L22", "%", fmt_header)
        worksheet.write("M22", "%", fmt_header)

        worksheet.merge_range("N21:P21", "CuT %", fmt_header)
        worksheet.write("N22", "Real", fmt_header)
        worksheet.write("O22", "Programa", fmt_header)
        worksheet.write("P22", "Plan", fmt_header)

        worksheet.merge_range("Q21:S21", "CuS %", fmt_header)
        worksheet.write("Q22", "Real", fmt_header)
        worksheet.write("R22", "Programa", fmt_header)
        worksheet.write("S22", "Plan", fmt_header)

        worksheet.merge_range("T21:V21", "Solubilidad %", fmt_header)
        worksheet.write("T22", "Real", fmt_header)
        worksheet.write("U22", "Programa", fmt_header)
        worksheet.write("V22", "Plan", fmt_header)

        worksheet.merge_range("W21:Y21", "CO3 %", fmt_header)
        worksheet.write("W22", "Real", fmt_header)
        worksheet.write("X22", "Programa", fmt_header)
        worksheet.write("Y22", "Plan", fmt_header)

        worksheet.write("Z21", "CuFe", fmt_header)
        worksheet.write("AA21", "FeT %", fmt_header)
        worksheet.write("AB21", "FeS %", fmt_header)
        worksheet.write("AC21", "Consumo de Acido kg/ton", fmt_header)

        worksheet.write("Z22", "Real", fmt_header)
        worksheet.write("AA22", "Real", fmt_header)
        worksheet.write("AB22", "Real", fmt_header)
        worksheet.write("AC22", "Real", fmt_header)

        worksheet.merge_range("AD21:AE21", "-1/2´", fmt_header)
        worksheet.write("AD22", "Real", fmt_header)
        worksheet.write("AE22", "Plan", fmt_header)

        worksheet.merge_range("AF21:AH21", "-100#Ty", fmt_header)
        worksheet.write("AF22", "Real", fmt_header)
        worksheet.write("AG22", "Programa", fmt_header)
        worksheet.write("AH22", "Plan", fmt_header)

        worksheet.merge_range("AI21:AK21", "CaolBeta%", fmt_header)
        worksheet.write("AI22", "Real", fmt_header)
        worksheet.write("AJ22", "Programa", fmt_header)
        worksheet.write("AK22", "Plan", fmt_header)

        worksheet.write("AL21", "", fmt_header)
        worksheet.write("AM21", "", fmt_header)
        worksheet.write("AL22", "Ideal TM", fmt_header)
        worksheet.write("AM22", "Programa semanal", fmt_header)

        worksheet.write("AN22", "Muestra química", fmt_header)
        worksheet.write("AO22", "Muestra física", fmt_header)
        # ============================================================
        # MAPEO DE FORMATOS POR COLUMNA
        # ============================================================
        columnas_numero_0 = [
            "Apilado_TMS_Real",
            "Apilado_TMS_Plan_Mensual",
        ]

        columnas_porcentaje = [
            "STOCK",
            "MINA",
            "SRR",
        ]

        columnas_grises = [
            "Semana",
            "Fecha",
            "Campania",
            "Material",
            "Modulo",
            "Avance",
        ]

        def formato_columna(col_name):
            if col_name == "Fecha":
                return fmt_fecha
            if col_name in columnas_numero_0:
                return fmt_numero
            if col_name in columnas_porcentaje:
                return fmt_porcentaje
            if col_name in columnas_grises:
                return fmt_texto_gris
            return fmt_decimal

        def es_numero_invalido(value):
            """
            Detecta NaN, inf y -inf antes de escribir en Excel.
            """
            if pd.isna(value):
                return True

            if isinstance(value, (int, float, np.integer, np.floating)):
                return not np.isfinite(value)

            return False


        def escribir_valor(row_idx, excel_col, col_name, value, formato=None):
            if formato is None:
                formato = formato_columna(col_name)

            # Controla NaN, inf, -inf
            if es_numero_invalido(value):
                worksheet.write(row_idx, excel_col, "", fmt_texto)
                return

            if col_name == "Fecha":
                value_fecha = pd.to_datetime(value, errors="coerce")
                if pd.isna(value_fecha):
                    worksheet.write(row_idx, excel_col, "", fmt_texto)
                else:
                    worksheet.write_datetime(row_idx, excel_col, value_fecha.to_pydatetime(), fmt_fecha)
                return

            if col_name in columnas_numero_0:
                worksheet.write_number(row_idx, excel_col, float(value), fmt_numero)
                return

            if col_name in columnas_porcentaje:
                worksheet.write_number(row_idx, excel_col, float(value), fmt_porcentaje)
                return

            if isinstance(value, (int, float, np.integer, np.floating)):
                worksheet.write_number(row_idx, excel_col, float(value), formato)
                return

            worksheet.write(row_idx, excel_col, value, formato if formato is not None else fmt_texto)

        def valor_limpio(value):
            if es_numero_invalido(value):
                return ""
            return value

        # ============================================================
        # DATOS DESDE FILA 23
        # ============================================================
        fila_data = 22

        # Columnas que se deben combinar verticalmente entre TA/TB
        # Solo estética. No cambia datos.
        columnas_merge_vertical = [
            "Fecha",
            "Campania",
            "Material",
            "Modulo",
            "Avance",

            "Apilado_TMS_Plan_Mensual",

            "CuT_Plan_Mensual",
            "CuT_Plan_Semanal",
            "CuS_Plan_Mensual",
            "CuS_Plan_Semanal",
            "Solubilidad_Plan_Mensual",
            "Solubilidad_Plan_Semanal",
            "CO3_Plan_Mensual",
            "CO3_Plan_Semanal",

            "Malla_Menos_1_2_Plan_Semanal",
            "Malla_Menos_100_Plan_Mensual",
            "Malla_Menos_100_Plan_Semanal",

            "CaolBeta_Plan_Mensual",
            "CaolBeta_Plan_Semanal",
            "Dosis_Acido_Ideal_TM",
            "Dosis_Acido_Programa_Semanal",
        ]

        columnas_merge_vertical = [c for c in columnas_merge_vertical if c in df_export.columns]

        celdas_saltadas = set()

        for i, (_, row) in enumerate(df_export.iterrows()):
            excel_row = fila_data + i

            for col_idx, col_name in enumerate(columnas_finales):
                excel_col = col_idx + col_offset
                if (excel_row, excel_col) in celdas_saltadas:
                    continue

                value = row[col_name]

                # Intento de merge vertical con fila siguiente
                puede_merge = (
                    col_name in columnas_merge_vertical
                    and i + 1 < len(df_export)
                )

                if puede_merge:
                    row_next = df_export.iloc[i + 1]

                    misma_fecha = False
                    if "Fecha" in df_export.columns:
                        f1 = pd.to_datetime(row.get("Fecha"), errors="coerce")
                        f2 = pd.to_datetime(row_next.get("Fecha"), errors="coerce")
                        misma_fecha = pd.notna(f1) and pd.notna(f2) and f1.date() == f2.date()

                    v1 = valor_limpio(value)
                    v2 = valor_limpio(row_next[col_name])

                    mismos_valores = str(v1) == str(v2)

                    if misma_fecha and mismos_valores:
                        formato = formato_columna(col_name)

                        # xlsxwriter permite merge_range con formatos.
                        # Para fechas conviene escribir el valor como texto visual para evitar problemas.
                        if col_name == "Fecha":
                            fecha_txt = pd.to_datetime(value).strftime("%d-%m-%Y") if pd.notna(value) else ""
                            worksheet.merge_range(
                                excel_row, 
                                excel_col, 
                                excel_row + 1, 
                                excel_col, 
                                fecha_txt, 
                                fmt_texto_gris
                                )
                        else:
                            if es_numero_invalido(value):
                                worksheet.merge_range(
                                    excel_row,
                                    excel_col,
                                    excel_row + 1,
                                    excel_col,
                                    "",
                                    fmt_texto
                                )
                            else:
                                worksheet.merge_range(
                                    excel_row,
                                    excel_col,
                                    excel_row + 1,
                                    excel_col,
                                    value,
                                    formato
                                )
                        celdas_saltadas.add((excel_row + 1, excel_col))
                        continue

                # Escritura normal
                if col_name in ["Fecha_Turno", "Turno_excel", "Muestra_Quimica", "Muestra_Fisica"]:
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_texto)
                elif col_name in columnas_grises:
                    escribir_valor(excel_row, excel_col, col_name, value, fmt_texto_gris)
                else:
                    escribir_valor(excel_row, excel_col, col_name, value)

        # ============================================================
        # FORMATO GENERAL
        # ============================================================
        worksheet.set_column("A:A", 4)
        worksheet.set_column("B:B", 4)
        worksheet.set_column("C:C", 18)
        worksheet.set_column("D:D", 11)
        worksheet.set_column("E:E", 13)
        worksheet.set_column("F:F", 13)
        worksheet.set_column("G:G", 13)
        worksheet.set_column("H:H", 11)

        worksheet.set_column("I:J", 13)
        worksheet.set_column("K:M", 9)
        worksheet.set_column("L:W", 11)
        worksheet.set_column("X:AA", 12)
        worksheet.set_column("AB:AF", 12)
        worksheet.set_column("AG:AI", 12)
        worksheet.set_column("AJ:AK", 15)
        worksheet.set_column("AL:AM", 18)
        worksheet.set_column("AN:AO", 18)
        worksheet.set_column("AP:AP", 3)
        
        # Espacio superior para logo y encabezado institucional
        worksheet.set_row(0, 42)
        worksheet.set_row(1, 42)
        worksheet.set_row(2, 28)
        worksheet.set_row(3, 24)
        worksheet.set_row(4, 24)
        worksheet.set_row(5, 24)

        worksheet.set_row(18, 22)
        worksheet.set_row(19, 22)
        worksheet.set_row(20, 28)
        worksheet.set_row(21, 32)

        # Alto de filas de datos
        for r in range(fila_data, fila_data + len(df_export)):
            worksheet.set_row(r, 20)

        last_row = fila_data + len(df_export)
        last_col = len(columnas_finales) - 1 + col_offset

        # ============================================================
        # MARGEN VISUAL + FRANJA / MARCO DEL REPORTE
        # ============================================================

        # Márgenes reales de impresión
        worksheet.set_margins(
            left=0.35,
            right=0.35,
            top=0.35,
            bottom=0.35
        )

        # Centrar horizontalmente al imprimir
        worksheet.center_horizontally()

        # Orientación y ajuste a página
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)

        # Definir área de impresión considerando logo + tabla
        worksheet.print_area(0, 0, last_row + 2, last_col + 1)

        # Marco exterior visual del reporte
        fmt_marco_superior = workbook.add_format({
            "top": 2,
            "top_color": "#808080"
        })

        fmt_marco_inferior = workbook.add_format({
            "bottom": 2,
            "bottom_color": "#808080"
        })

        fmt_marco_izquierdo = workbook.add_format({
            "left": 2,
            "left_color": "#808080"
        })

        fmt_marco_derecho = workbook.add_format({
            "right": 2,
            "right_color": "#808080"
        })

        # Coordenadas del marco visual
        marco_fila_ini = 0
        marco_fila_fin = last_row + 2
        marco_col_ini = 0
        marco_col_fin = last_col + 1

        # Borde superior
        for c in range(marco_col_ini, marco_col_fin + 1):
            worksheet.write_blank(marco_fila_ini, c, None, fmt_marco_superior)

        # Borde inferior
        for c in range(marco_col_ini, marco_col_fin + 1):
            worksheet.write_blank(marco_fila_fin, c, None, fmt_marco_inferior)

        # Borde izquierdo
        for r in range(marco_fila_ini, marco_fila_fin + 1):
            worksheet.write_blank(r, marco_col_ini, None, fmt_marco_izquierdo)

        # Borde derecho
        for r in range(marco_fila_ini, marco_fila_fin + 1):
            worksheet.write_blank(r, marco_col_fin, None, fmt_marco_derecho)
        # Ocultar líneas de cuadrícula para parecer más plantilla
        worksheet.hide_gridlines(2)
