# db_connection.py
import mysql.connector
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

Entorno = int(os.getenv("ENTORNO", 2))  # por defecto 1 si no está definido

if Entorno == 1:
    hosts1 = os.getenv("MYSQL_HOST_loc")
    users1 = os.getenv("MYSQL_USER_loc")
    passwords = os.getenv("MYSQL_PASSWORD_loc")
    bdds = os.getenv("MYSQL_DATA_hidro")
else:
    hosts1 = os.getenv("MYSQL_HOST")
    users1 = os.getenv("MYSQL_USER")
    passwords = os.getenv("MYSQL_PASSWORD")
    bdds = os.getenv("MYSQL_DATA_hidro_r")

def get_connection():
    try:
        return mysql.connector.connect(
            host=hosts1,
            user=users1,
            password=passwords,
            database=bdds
        )
    except mysql.connector.Error as err:
        print(f"❌ Error de conexión a MySQL: {err}")
        return None

def get_engine():
    """
    Conexión tipo SQLAlchemy para uso con pandas.to_sql() o ORM.
    """
    try:
        conn_str = f"mysql+pymysql://{users1}:{passwords}@{hosts1}/{bdds}"
        engine = create_engine(conn_str)
        return engine
    except Exception as e:
        print(f"❌ Error al crear engine SQLAlchemy: {e}")
        return None