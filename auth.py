from flask import Blueprint, request, jsonify, session, render_template_string,redirect,render_template
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from db_connection import get_engine

auth_bp = Blueprint("auth", __name__, template_folder="templatesFrontend")


@auth_bp.route("/login_page")
def login_page():
    return render_template("login.html")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    engine = get_engine()
    hashed = generate_password_hash(password)

    with engine.begin() as conn:
        # Verificar si existe
        existing = conn.execute(text("SELECT 1 FROM inventar_SpcHidr.usuarios WHERE username=:u"), {"u": username}).fetchone()
        if existing:
            return jsonify({"error": "Usuario ya existe"}), 400

        conn.execute(
            text("INSERT INTO inventar_SpcHidr.usuarios (username, password_hash) VALUES (:u, :p)"),
            {"u": username, "p": hashed}
        )

    return jsonify({"message": "Usuario creado"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM inventar_SpcHidr.usuarios WHERE username=:u"),
            {"u": username}
        ).fetchone()
    
    if row and check_password_hash(row.password_hash, password):
        session["user"] = username
        return redirect("/")
    session["user"] = username
    return redirect("/")
    #return jsonify({"error": "Credenciales inválidas"}), 401


@auth_bp.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/auth/login_page")  #jsonify({"message": "Sesión cerrada"}), 200

