
from flask import redirect, request
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, current_user
)
from flask_bcrypt import Bcrypt
from sqlalchemy import text
import pandas as pd

bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = "/login"

# ======================================================
# CLASE USUARIO
# ======================================================
class User(UserMixin):
    def __init__(self, id, username, password_hash, rol):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.rol = rol

# ======================================================
# INICIALIZAR AUTH
# ======================================================
def init_auth(server, engine):
    bcrypt.init_app(server)
    login_manager.init_app(server)

    @login_manager.user_loader
    def load_user(user_id):
        df = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.usuarios WHERE id = :id"), engine, params={"id": user_id})
        if not df.empty:
            u = df.iloc[0]
            return User(u.id, u.username, u.password_hash, u.rol)
        return None

# ======================================================
# LOGIN HANDLER
# ======================================================
def try_login(username, password, engine):
    df = pd.read_sql(text("SELECT * FROM inventar_SpcHidr.usuarios WHERE username = :u AND activo = 1"), engine, params={"u": username})
    if df.empty:
        return None
    u = df.iloc[0]
    if bcrypt.check_password_hash(u.password_hash, password):
        user = User(u.id, u.username, u.password_hash, u.rol)
        login_user(user)
        return user
    return None

def do_logout():
    logout_user()
