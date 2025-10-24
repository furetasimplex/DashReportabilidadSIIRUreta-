# db_connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from urllib.parse import quote_plus
# import mysql.connector
import pyodbc
from sqlalchemy.engine import URL

load_dotenv()

ENTORNO = int(os.getenv("ENTORNO", 4))  # 1=local MySQL, 2=producción MySQL, 3=SQL Server, 4=SQL Server (macOS ODBC18)


def get_connection():
    """
    Devuelve una conexión "cruda":
      - mysql.connector.connect() para MySQL
      - pyodbc.connect() para SQL Server
    """
    if ENTORNO == 1:  # MySQL local
        MYSQL_HOST = os.getenv("MYSQL_HOST_loc")
        MYSQL_USER = os.getenv("MYSQL_USER_loc")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD_loc")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro")
        # Temporalmente deshabilitado
        return None

    if ENTORNO == 2:  # MySQL producción
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro_r")
        # Temporalmente deshabilitado
        return None

    if ENTORNO == 3:  # SQL Server (tu lógica original con pyodbc)
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")

        conn_str = (
            f"DRIVER={{{{ {SQLSERVER_DRIVER} }}}};"
            f"SERVER={SQLSERVER_HOST};"
            f"DATABASE={SQLSERVER_DB};"
            f"UID={SQLSERVER_USER};"
            f"PWD={{{SQLSERVER_PASSWORD}}};"
            "Encrypt=no;"
            "TrustServerCertificate=yes;"
        )

        print("\n🧩 [DEBUG] Intentando conectar a SQL Server (ENTORNO 3)\n"
              f"DRIVER={SQLSERVER_DRIVER}\nSERVER={SQLSERVER_HOST}\nDATABASE={SQLSERVER_DB}\nUSER={SQLSERVER_USER}\n"
              "----------------------------------------------------")
        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            print("✅ [DEBUG] Conectado correctamente a SQL Server (ENTORNO 3)")
            return conn
        except pyodbc.InterfaceError as e:
            print("❌ [ERROR] Driver ODBC no encontrado o fallo al inicializarlo (E3)")
            print(str(e))
        except pyodbc.Error as e:
            print("❌ [ERROR] pyodbc general (E3):")
            print(str(e))
        except Exception as e:
            print("❌ [ERROR] Excepción inesperada al conectar SQL Server (E3):")
            print(str(e))
        return None

    # --- ENTORNO 4: get_connection() ---
    if ENTORNO == 4:  # SQL Server (macOS) usando ODBC Driver 18
        host = os.getenv("SQLSERVER_HOST")          # p.ej. 149.50.136.234
        port = os.getenv("SQLSERVER_PORT", "1433")
        db   = os.getenv("SQLSERVER_DB")
        user = os.getenv("SQLSERVER_USER")
        pwd  = os.getenv("SQLSERVER_PASSWORD", "")

        # Helper: envolver en llaves ODBC sin espacios y escapando '}' si aparece
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

        print("\n🧩 [DEBUG] ENTORNO 4 (macOS ODBC18) con TLS:")
        print(f"SERVER={host},{port}\nDATABASE={db}\nUSER={user}")
        print("Props: Encrypt=yes; TrustServerCertificate=yes; Authentication=SqlPassword")
        print("----------------------------------------------------")

        try:
            conn = pyodbc.connect(conn_str, timeout=10)
            print("✅ [DEBUG] Conectado correctamente a SQL Server (E4)")
            return conn
        except pyodbc.Error as e:
            print("❌ [ERROR] pyodbc (E4):", e)
        return None

    raise ValueError("❌ ENTORNO no válido. Usa 1=local MySQL, 2=producción MySQL, 3=SQL Server o 4=SQL Server_mac.")


def get_engine():
    """
    Devuelve un SQLAlchemy engine:
      - mysql+pymysql para MySQL
      - mssql+pyodbc (ODBC18) para SQL Server en macOS (ENTORNO 4)
      - (mantengo tu lógica original para ENTORNO 3 con pytds si así lo requieres)
    """
    if ENTORNO == 1:  # MySQL local
        MYSQL_HOST = os.getenv("MYSQL_HOST_loc")
        MYSQL_USER = os.getenv("MYSQL_USER_loc")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD_loc")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro")
        try:
            conn_str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB}"
            return create_engine(conn_str)
        except Exception as e:
            print(f"❌ Error engine MySQL local: {e}")
            return None

    if ENTORNO == 2:  # MySQL producción
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro_r")
        try:
            conn_str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB}"
            return create_engine(conn_str)
        except Exception as e:
            print(f"❌ Error engine MySQL prod: {e}")
            return None

    if ENTORNO == 3:  # SQL Server (mantengo tu pytds)
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD", "")
        SQLSERVER_PASSWORD = SQLSERVER_PASSWORD.replace("@", "%40")
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "SQL Server")
        sqldriver = f"?driver={SQLSERVER_DRIVER.replace(' ', '+')}&Encrypt=no&TrustServerCertificate=yes"

        try:
            conn_str = (
                f"mssql+pytds://{SQLSERVER_USER}:{SQLSERVER_PASSWORD}"
                f"@{SQLSERVER_HOST}/{SQLSERVER_DB}"
            )
            if SQLSERVER_DRIVER != "SQL Server":
                conn_str += sqldriver
            print(conn_str)
            return create_engine(conn_str)
        except Exception as e:
            print(f"❌ Error engine SQL Server (E3): {e}")
            return None

    # --- ENTORNO 4: get_engine() ---
    if ENTORNO == 4:  # SQL Server (macOS) con ODBC 18
        host = os.getenv("SQLSERVER_HOST")
        port = os.getenv("SQLSERVER_PORT", "1433")
        db   = os.getenv("SQLSERVER_DB")
        user = os.getenv("SQLSERVER_USER")
        pwd  = quote_plus(os.getenv("SQLSERVER_PASSWORD", ""))  # URL-escape

        params = (
            "driver=ODBC+Driver+18+for+SQL+Server"
            "&Encrypt=yes"
            "&TrustServerCertificate=yes"
            "&Authentication=SqlPassword"
        )
        url = f"mssql+pyodbc://{user}:{pwd}@{host},{port}/{db}?{params}"
        try:
            return create_engine(url, pool_pre_ping=True, pool_recycle=1800)
        except Exception as e:
            print(f"❌ Error engine SQL Server (E4): {e}")
            return None

    raise ValueError("❌ ENTORNO no válido. Usa 1=local MySQL, 2=producción MySQL, 3=SQL Server o 4=SQL Server_mac.")
