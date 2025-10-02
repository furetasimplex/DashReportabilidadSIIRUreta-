# sqlserver_helpers.py
import pandas as pd
import numpy as np
from typing import List, Optional, Any
from db_connection import get_connection  # tu función para abrir conexión


# =========================
# Función para convertir de forma segura
# =========================
def safe_numeric(x):
    """
    Convierte todo lo que se pueda a número:
    - Si es float entero, lo pasa a int
    - Si es float con decimales, deja float
    - Si es None o NaN, deja None
    - Si no se puede convertir, deja el valor original
    """
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    try:
        f = float(x)
        if f.is_integer():
            return int(f)
        return f
    except:
        return x


# =========================
# Sanitizar todo el DataFrame
# =========================
def sanitize_df_for_sqlserver(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia NaN, vacíos y convierte tipos seguros para SQL Server.
    Convierte automáticamente floats enteros a int.
    """
    df_sanitized = df.copy()
    # Dropear columnas que no queremos insertar (por ejemplo identity)
    df_sanitized = df_sanitized.drop(columns=['mov_id'], errors='ignore')
    df_sanitized = df_sanitized.replace({np.nan: None, "": None})

    for col in df_sanitized.columns:
        # Numéricos → safe_numeric
        if pd.api.types.is_numeric_dtype(df_sanitized[col]):
            df_sanitized[col] = df_sanitized[col].apply(safe_numeric)
        # Fechas → datetime
        elif pd.api.types.is_datetime64_any_dtype(df_sanitized[col]):
            df_sanitized[col] = pd.to_datetime(
                df_sanitized[col], errors='coerce'
            ).apply(lambda x: x if pd.notnull(x) else None)
        # Otros → str si no es None
        else:
            df_sanitized[col] = df_sanitized[col].apply(
                lambda x: str(x) if x is not None else None
            )
    return df_sanitized


# =========================
# Leer datos desde SQL Server
# =========================
def df_from_sql(query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:

    print("passaaa")

    if not isinstance(query, str):
        raise ValueError(f"La query debe ser str pero es {type(query)}")
    conn = get_connection()
    if conn is None:
        raise ConnectionError("No se pudo obtener conexión con SQL Server")
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or [])
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame.from_records(rows, columns=columns)
    finally:
        cursor.close()
        conn.close()


# =========================
# Inserción en SQL Server
# =========================
def insert_df_to_sql(df: pd.DataFrame, table_name: str):
    """
    Inserta un DataFrame en SQL Server, convirtiendo automáticamente los tipos.
    """
    if df.empty:
        print("⚠️ DataFrame vacío")
        return

    # Sanitizar todo
    df_sanitized = sanitize_df_for_sqlserver(df)
    # Preparar query
    values = [tuple(row) for row in df_sanitized.to_numpy()]
    columns = ','.join([f"[{col}]" for col in df_sanitized.columns])
    placeholders = ','.join(['?'] * len(df_sanitized.columns))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    conn = get_connection()
    if conn is None:
        raise ConnectionError("No se pudo obtener conexión con SQL Server")
    cursor = conn.cursor()

    try:
        cursor.fast_executemany = True
        cursor.executemany(query, values)
        conn.commit()
        print(f"✅ Insertadas {len(df_sanitized)} filas en {table_name}")
    except Exception as e:
        print("⚠️ Error en executemany, debug fila por fila activado...")
        debug_insert_df(df_sanitized, table_name)
        raise
    finally:
        cursor.close()
        conn.close()


# =========================
# Debug fila por fila
# =========================
def debug_insert_df(df: pd.DataFrame, table_name: str):
    """
    Inserta fila por fila mostrando exactamente qué fila falla.
    Detecta problemas de too many values y conversión de tipos.
    """
    values = [tuple(row) for row in df.to_numpy()]
    columns = ','.join([f"[{col}]" for col in df.columns])
    placeholders = ','.join(['?'] * len(df.columns))
    query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"

    conn = get_connection()
    if conn is None:
        raise ConnectionError("No se pudo obtener conexión con SQL Server")
    cursor = conn.cursor()

    print(f"Debug insert a tabla: {table_name}")
    print(f"Columnas: {df.columns.tolist()}")
    print(f"Total filas: {len(df)}")

    for i, row in enumerate(values):
        try:
            # Debug tipos y valores antes de insertar
            print(f"Fila {i} valores tipos: {[type(v) for v in row]}")
            cursor.execute(query, row)
            if i % 100 == 0:
                print(f"✔️ Fila {i} insertada correctamente")
        except Exception as e:
            print(f"❌ Error en fila {i}")
            print("Valores problemáticos:", row)
            print("Tipos de los valores:", [type(v) for v in row])
            print("Error:", e)
            continue

    conn.commit()
    cursor.close()
    conn.close()
    print("✅ Debug insert completado")



