# db_connection.py
import os
from env_loader import load_app_env
from sqlalchemy import create_engine
from urllib.parse import quote_plus
import pyodbc

load_app_env()

ENTORNO = int(os.getenv("ENTORNO", 4))  # 3=SQL Server ODBC, 4=SQL Server ODBC18
_engine = None


def get_connection():
    """Devuelve una conexion cruda pyodbc a SQL Server."""
    if ENTORNO == 3:  # SQL Server (Windows / ODBC)
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")

        conn_str = (
            f"DRIVER={{{SQLSERVER_DRIVER}}};"
            f"SERVER={SQLSERVER_HOST};"
            f"DATABASE={SQLSERVER_DB};"
            f"UID={SQLSERVER_USER};"
            f"PWD={SQLSERVER_PASSWORD};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )

        print("\n[DEBUG] Intentando conectar a SQL Server (ENTORNO 3)")
        print(f"DRIVER={SQLSERVER_DRIVER}\nSERVER={SQLSERVER_HOST}\nDATABASE={SQLSERVER_DB}\nUSER={SQLSERVER_USER}")
        print("----------------------------------------------------")
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            print("[DEBUG] Conectado correctamente a SQL Server (ENTORNO 3)")
            return conn
        except pyodbc.InterfaceError as e:
            print("[ERROR] Driver ODBC no encontrado o fallo al inicializarlo (E3)")
            print(str(e))
        except pyodbc.Error as e:
            print("[ERROR] pyodbc general (E3):")
            print(str(e))
        except Exception as e:
            print("[ERROR] Excepcion inesperada al conectar SQL Server (E3):")
            print(str(e))
        return None

    if ENTORNO == 4:  # SQL Server con ODBC Driver 18
        host = os.getenv("SQLSERVER_HOST")
        port = os.getenv("SQLSERVER_PORT", "1433")
        db = os.getenv("SQLSERVER_DB")
        user = os.getenv("SQLSERVER_USER")
        pwd = os.getenv("SQLSERVER_PASSWORD", "")

        def odbc_brace(v: str) -> str:
            return "{" + v.replace("}", "}}") + "}"

        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={host},{port};"
            f"DATABASE={db};"
            f"UID={user};"
            f"PWD={odbc_brace(pwd)};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
            "Authentication=SqlPassword;"
        )

        print("\n[DEBUG] ENTORNO 4 (ODBC18) con TLS:")
        print(f"SERVER={host},{port}\nDATABASE={db}\nUSER={user}")
        print("Props: Encrypt=yes; TrustServerCertificate=yes; Authentication=SqlPassword")
        print("----------------------------------------------------")

        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            print("[DEBUG] Conectado correctamente a SQL Server (E4)")
            return conn
        except pyodbc.Error as e:
            print("[ERROR] pyodbc (E4):", e)
        return None

    raise ValueError(
        "[ERROR] ENTORNO no valido. Usa 3=SQL Server o 4=SQL Server ODBC18."
    )


def get_engine():
    """Devuelve un SQLAlchemy engine mssql+pyodbc."""
    global _engine
    if _engine is not None:
        return _engine

    if ENTORNO == 3:  # SQL Server (Windows / ODBC)
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = quote_plus(os.getenv("SQLSERVER_PASSWORD", ""))
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")

        driver_param = SQLSERVER_DRIVER.replace(" ", "+")
        params = f"driver={driver_param}&Encrypt=no&TrustServerCertificate=yes"

        try:
            conn_str = (
                f"mssql+pyodbc://{SQLSERVER_USER}:{SQLSERVER_PASSWORD}"
                f"@{SQLSERVER_HOST}/{SQLSERVER_DB}?{params}"
            )
            print("\n[DEBUG] SQLAlchemy (ENTORNO 3)")
            print(
                f"SERVER={SQLSERVER_HOST} | DATABASE={SQLSERVER_DB} | "
                f"USER={SQLSERVER_USER} | DRIVER={SQLSERVER_DRIVER}"
            )
            _engine = create_engine(conn_str, pool_pre_ping=True, pool_recycle=1800)
            return _engine
        except Exception as e:
            print(f"[ERROR] engine SQL Server (E3): {e}")
            return None

    if ENTORNO == 4:  # SQL Server con ODBC 18
        host = os.getenv("SQLSERVER_HOST")
        port = os.getenv("SQLSERVER_PORT", "1433")
        db = os.getenv("SQLSERVER_DB")
        user = os.getenv("SQLSERVER_USER")
        pwd = quote_plus(os.getenv("SQLSERVER_PASSWORD", ""))

        params = (
            "driver=ODBC+Driver+18+for+SQL+Server"
            "&Encrypt=yes"
            "&TrustServerCertificate=yes"
            "&Authentication=SqlPassword"
        )
        url = f"mssql+pyodbc://{user}:{pwd}@{host},{port}/{db}?{params}"
        try:
            _engine = create_engine(url, pool_pre_ping=True, pool_recycle=1800)
            return _engine
        except Exception as e:
            print(f"[ERROR] Error engine SQL Server (E4): {e}")
            return None

    raise ValueError(
        "[ERROR] ENTORNO no valido. Usa 3=SQL Server o 4=SQL Server ODBC18."
    )
