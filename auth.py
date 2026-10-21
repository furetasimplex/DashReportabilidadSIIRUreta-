import os
import re

from flask import Blueprint, request, session, redirect, render_template
from sqlalchemy import text
from passlib.hash import django_pbkdf2_sha256
from db_connection import get_engine
from env_loader import load_app_env, require_app_env

load_app_env()

auth_bp = Blueprint("auth", __name__, template_folder="templatesFrontend")


LOGIN_TABLE = require_app_env("LOGIN_DATABASE")["LOGIN_DATABASE"]
if not re.fullmatch(r"[\w.]+", LOGIN_TABLE):
    raise ValueError(f"LOGIN_DATABASE inválido: {LOGIN_TABLE!r}")


def user_is_admin(username):
    """Permiso administrativo vigente del usuario Django existente; fail closed."""
    if not isinstance(username, str) or not username.strip():
        return False
    try:
        with get_engine().connect() as conn:
            allowed = conn.execute(text(
                f"SELECT CASE WHEN is_staff=1 OR is_superuser=1 THEN 1 ELSE 0 END "
                f"FROM {LOGIN_TABLE} WHERE username=:u AND is_active=1"
            ), {"u": username.strip()}).scalar()
        return allowed == 1
    except Exception:
        return False


@auth_bp.route("/login_page")
def login_page():
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            # ponytail: la tabla no se puede parametrizar; viene de env, validada arriba.
            text(f"SELECT password FROM {LOGIN_TABLE} WHERE username=:u AND is_active=1"),
            {"u": username}
        ).fetchone()

    # Django guarda "!xxxx" para cuentas sin password usable -> verify() tira ValueError.
    if row and django_pbkdf2_sha256.identify(row.password) \
            and django_pbkdf2_sha256.verify(password, row.password):
        session["user"] = username
        return redirect("/")
    return redirect("/auth/login_page?error=1")


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/auth/login_page")
