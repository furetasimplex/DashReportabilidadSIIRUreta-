# db_connection.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Definimos entorno
def get_connection():
    ENTORNO = int(os.getenv("ENTORNO", 3))  # por defecto 2#local=1, produccion=2, test=3 SQL Server
    engine = None
    if ENTORNO == 1:
        MYSQL_HOST = os.getenv("MYSQL_HOST_loc")
        MYSQL_USER = os.getenv("MYSQL_USER_loc")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD_loc")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro")
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST_loc")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB_loc")
        """
        Devuelve engine SQLAlchemy para MySQL para local
        """
        try:
            conn_str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB}"
            engine = create_engine(conn_str)
            return engine
        except Exception as e:
            print(f"❌ Error al crear engine MySQL: {e}")
            return None

    if ENTORNO == 2:
        MYSQL_HOST = os.getenv("MYSQL_HOST")
        MYSQL_USER = os.getenv("MYSQL_USER")
        MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
        MYSQL_DB = os.getenv("MYSQL_DATA_hidro_r")
        SQLSERVER_HOST = os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB = os.getenv("SQLSERVER_DB")

        """
        Devuelve engine SQLAlchemy para MySQL
        """
        try:
            conn_str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:3306/{MYSQL_DB}"
            engine = create_engine(conn_str)
            return engine
        except Exception as e:
            print(f"❌ Error al crear engine MySQL: {e}")
            return None

    if ENTORNO == 3:
        SQLSERVER_HOST=os.getenv("SQLSERVER_HOST")
        SQLSERVER_DB=os.getenv("SQLSERVER_DB")
        SQLSERVER_USER=os.getenv("SQLSERVER_USER")
        SQLSERVER_PASSWORD=os.getenv("SQLSERVER_PASSWORD")
        #SQLSERVER_SCHEMA=os.getenv("SQLSERVER_SCHEMA")

        """
        Devuelve engine SQLAlchemy para SQL Server
        Requiere tener instalado: pip install pyodbc
        """
        try:
            # Usando ODBC Driver 18 para SQL Server, ajusta según tu instalación
            conn_str = (
                f"mssql+pyodbc://{SQLSERVER_USER}:{SQLSERVER_PASSWORD}"
                f"@{SQLSERVER_HOST}/{SQLSERVER_DB}?driver=SQL+Server"
            )#ODBC+Driver+18+for+SQL+Server"
            engine = create_engine(conn_str)
            return engine
        except Exception as e:
            print(f"❌ Error al crear engine SQL Server: {e}")
            return None
    else:
        raise ValueError("❌ Entorno no válido. Usa 1 (local), 2 (producción) o 3 (test).")

    #get_mysql_engine():

    #def get_sqlserver_engine():

