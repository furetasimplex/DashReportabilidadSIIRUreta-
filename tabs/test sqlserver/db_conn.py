# db_connection.py
import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

# --- Configuración básica (variables de entorno) ---
SQLSERVER_HOST = os.getenv("SQLSERVER_HOST", "MI_SERVIDOR")
SQLSERVER_PORT = int(os.getenv("SQLSERVER_PORT", "1433"))
SQLSERVER_DB   = os.getenv("SQLSERVER_DB", "MiBase")
SQLSERVER_USER = os.getenv("SQLSERVER_USER", "usuario")
SQLSERVER_PWD  = os.getenv("SQLSERVER_PWD", "clave")

# Forzar DSN si así lo prefieres (creado como DSN de Usuario en ODBC)
ODBC_DSN       = os.getenv("ODBC_DSN")  # p.ej., "MiDSN" (opcional)

# Cifrado/Certificado (recomendado mantener Encrypt=yes; cambia solo si tu entorno lo requiere)
ENCRYPT        = os.getenv("MSSQL_ENCRYPT", "yes")     # yes/no
TRUST_CERT     = os.getenv("MSSQL_TRUST_SERVER_CERT", "yes")  # yes/no

# Fallback sin ODBC (no requiere permisos admin)
USE_TDS_FALLBACK = os.getenv("USE_TDS_FALLBACK", "false").lower() in ("1", "true", "yes")


def _available_odbc_drivers_lower():
    """
    Devuelve la lista de drivers ODBC instalados (en minúsculas).
    No falla si pyodbc no está disponible.
    """
    try:
        import pyodbc
        return [d.lower() for d in pyodbc.drivers()]
    except Exception:
        return []


def _pick_best_driver():
    """
    Escoge el mejor driver disponible en el sistema, respetando este orden de preferencia:
    1) ODBC Driver 18 for SQL Server
    2) ODBC Driver 17 for SQL Server
    3) ODBC Driver 13 for SQL Server
    4) SQL Server Native Client 11.0   <-- "Driver nativo" clásico
    5) SQL Server                      <-- muy antiguo, pero a veces presente
    """
    drivers = _available_odbc_drivers_lower()
    preferred = [
        "odbc driver 18 for sql server",
        "odbc driver 17 for sql server",
        "odbc driver 13 for sql server",
        "sql server native client 11.0",
        "sql server",
    ]
    for name in preferred:
        if name in drivers:
            return name  # ya viene en minúsculas
    return None


def _build_pyodbc_engine() -> Engine:
    # Si hay DSN definido, úsalo directamente (sin o con usuario/clave):
    #   - Útil cuando no controlas versión de driver y ya tienes DSN funcional.
    if ODBC_DSN:
        odbc_params = (
            f"DSN={ODBC_DSN};"
            f"UID={SQLSERVER_USER};PWD={SQLSERVER_PWD};"
            f"Encrypt={'yes' if ENCRYPT.lower() in ('1','true','yes') else 'no'};"
            f"TrustServerCertificate={'yes' if TRUST_CERT.lower() in ('1','true','yes') else 'no'};"
            "Connection Timeout=15;"
        )
        conn_str = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_params)}"
        engine = create_engine(conn_str, pool_pre_ping=True, future=True)
        _attach_fast_executemany(engine)
        return engine

    # Si no hay DSN, elegir el mejor driver instalado
    chosen = _pick_best_driver()
    if not chosen:
        raise RuntimeError(
            "No se encontró un driver ODBC para SQL Server. "
            "Instala ODBC Driver 17/18 o define USE_TDS_FALLBACK=true para usar python-tds."
        )

    # Reconstruir el nombre con capitalización estándar para ODBC
    # (puramente cosmético; ODBC es case-insensitive)
    # Nota: si el elegido fue 'sql server native client 11.0', lo admitimos igual.
    driver_title_map = {
        "odbc driver 18 for sql server": "ODBC Driver 18 for SQL Server",
        "odbc driver 17 for sql server": "ODBC Driver 17 for SQL Server",
        "odbc driver 13 for sql server": "ODBC Driver 13 for SQL Server",
        "sql server native client 11.0": "SQL Server Native Client 11.0",
        "sql server": "SQL Server",
    }
    driver_name = driver_title_map.get(chosen, chosen)

    # Algunos drivers antiguos (p.ej., "SQL Server") pueden no tolerar Encrypt=yes;
    # si tienes problemas, prueba ENCRYPT=no temporalmente.
    odbc_params = (
        f"DRIVER={{{{}}}};".format(driver_name) +
        f"SERVER={SQLSERVER_HOST},{SQLSERVER_PORT};"
        f"DATABASE={SQLSERVER_DB};"
        f"UID={SQLSERVER_USER};PWD={SQLSERVER_PWD};"
        f"Encrypt={'yes' if ENCRYPT.lower() in ('1','true','yes') else 'no'};"
        f"TrustServerCertificate={'yes' if TRUST_CERT.lower() in ('1','true','yes') else 'no'};"
        "Connection Timeout=15;"
    )

    conn_str = f"mssql+pyodbc:///?odbc_connect={quote_plus(odbc_params)}"
    engine = create_engine(conn_str, pool_pre_ping=True, future=True)
    _attach_fast_executemany(engine)
    return engine


def _attach_fast_executemany(engine: Engine):
    """Activa fast_executemany en pyodbc para inserciones masivas con pandas.to_sql."""
    try:
        import pyodbc  # noqa: F401
    except Exception:
        return  # si no está pyodbc, no hacemos nada

    @event.listens_for(engine, "before_cursor_execute")
    def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if executemany:
            try:
                cursor.fast_executemany = True
            except Exception:
                pass


def _build_pytds_engine() -> Engine:
    # Fallback puro Python (sin ODBC del SO)
    # pip install python-tds sqlalchemy
    url = (
        f"mssql+pytds://{SQLSERVER_USER}:{quote_plus(SQLSERVER_PWD)}"
        f"@{SQLSERVER_HOST}:{SQLSERVER_PORT}/{SQLSERVER_DB}?charset=utf8"
    )
    return create_engine(url, pool_pre_ping=True, future=True)


def get_engine() -> Engine:
    if USE_TDS_FALLBACK:
        return _build_pytds_engine()
    return _build_pyodbc_engine()


def describe_odbc_environment() -> str:
    """
    Útil para mostrar en tu app/logs qué drivers hay y cuál se eligió.
    """
    drivers = _available_odbc_drivers_lower()
    chosen = _pick_best_driver()
    return (
        "Drivers ODBC disponibles: "
        + (", ".join(drivers) if drivers else "(ninguno)")
        + f" | Driver elegido: {chosen if chosen else '(ninguno)'}"
    )
