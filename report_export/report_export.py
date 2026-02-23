import pandas as pd
from datetime import date

try:
    from db_connection import get_connection  # usa tu DB_CONNECTION
except Exception as e:
    raise RuntimeError("No se pudo importar get_connection desde db_connection.py") from e

# Nombre completo de la tabla (ajusta si cambia)
TABLE_FQN = "[inventar_SpcHidr].[Datos_conciliados_of]"
TABLE_DATOS_CONCILIADOS = "[inventar_SpcHidr].[inventar_SpcHidr].[Datos_conciliados_of]"

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
    "Produccion_Catodos_Real", "Produccion_Catodos_Plan",
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
