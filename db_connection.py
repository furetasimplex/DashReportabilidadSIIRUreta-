# db_connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import mysql.connector
import pyodbc

load_dotenv()

ENTORNO = int(os.getenv("ENTORNO", 3))  # 1=local MySQL, 2=producción MySQL, 3=SQL Server

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
        try:
            return mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
        except mysql.connector.Error as err:
            print(f"❌ Error conexión MySQL local: {err}")
            return None

    if ENTORNO == 2:  # MySQL producción
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro_r")
        try:
            return mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
        except mysql.connector.Error as err:
            print(f"❌ Error conexión MySQL prod: {err}")
            return None

    if ENTORNO == 3:  # SQL Server
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")       # Ej: "xxxxxxxxxxx.bhpbilliton.net\\SQL2017"
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "SQL Server")
        try:
            conn_str = (
                f"DRIVER={{{SQLSERVER_DRIVER}}};"
                f"SERVER={SQLSERVER_HOST};"
                f"DATABASE={SQLSERVER_DB};"
                f"UID={SQLSERVER_USER};"
                f"PWD={SQLSERVER_PASSWORD}"
            )
            return pyodbc.connect(conn_str)
        except Exception as e:
            print(f"❌ Error conexión SQL Server: {e}")
            return None

    raise ValueError("❌ ENTORNO no válido. Usa 1=local MySQL, 2=producción MySQL o 3=SQL Server.")


def get_engine():
    """
    Devuelve un SQLAlchemy engine:
      - mysql+pymysql para MySQL
      - mssql+pyodbc para SQL Server
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

    if ENTORNO == 3:  # SQL Server
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST_CLEAN")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")
        SQLSERVER_USER = os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD = os.getenv("SQLSERVER_PASSWORD")
        SQLSERVER_PASSWORD =  SQLSERVER_PASSWORD.replace("@","%40")
        SQLSERVER_DRIVER = os.getenv("SQLSERVER_DRIVER", "SQL Server")
        try:
            conn_str = (
                f"mssql+pytds://{SQLSERVER_USER}:{SQLSERVER_PASSWORD}"
                f"@SCL0TSP01S01.ent.bhpbilliton.net\\SQL2017/{SQLSERVER_DB}"
                #f"?driver={SQLSERVER_DRIVER.replace(' ', '+')}"
            )
            print(conn_str)
            return create_engine(conn_str)
        except Exception as e:
            print(f"❌ Error engine SQL Server: {e}")
            return None

    raise ValueError("❌ ENTORNO no válido. Usa 1=local MySQL, 2=producción MySQL o 3=SQL Server.")
