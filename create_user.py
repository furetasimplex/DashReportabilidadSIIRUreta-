from flask_bcrypt import Bcrypt
import sqlalchemy
from sqlalchemy import text
from db_connection import get_engine

bcrypt = Bcrypt()
engine = get_engine()

password_hash = bcrypt.generate_password_hash("admin123").decode('utf-8')
query = text("INSERT INTO inventar_SpcHidr.usuarios (username, password_hash, nombre, rol) VALUES (:u, :p, :n, :r)")
with engine.begin() as conn:
    conn.execute(query, {"u": "admin", "p": password_hash, "n": "Administrador", "r": "admin"})
