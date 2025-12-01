import pandas as pd
from datetime import date

try:
    from db_connection import get_connection  # usa tu DB_CONNECTION
except Exception as e:
    raise RuntimeError("No se pudo importar get_connection desde db_connection.py") from e

# Nombre completo de la tabla (ajusta si cambia)
TABLE_FQN = "[inventar_SpcHidr].[Datos_conciliados_of]"


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
    WHERE [Fecha] BETWEEN {start_date} AND {end_date}
    ORDER BY [Fecha] ASC
    """
    print(sql_sa )
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
    #print(df)
    # Dejamos Fecha y es_preliminar al inicio
    cols = list(df.columns)
    ordered = []
    for c in ["Fecha", "es_preliminar"]:
        if c in cols:
            ordered.append(c)
            cols.remove(c)
    ordered.extend(cols)
    print(df[ordered])

    return df
