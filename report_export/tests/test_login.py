"""Verifica que /auth/login valide contra la tabla Django de LOGIN_DATABASE."""
import os
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from flask import Flask
from passlib.hash import django_pbkdf2_sha256

os.environ.setdefault("LOGIN_DATABASE", "DEV_SIIR.dbo.auth_user")
import auth  # noqa: E402  (LOGIN_DATABASE se lee al importar)


def make_client(monkeypatch, password_hash):
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        SimpleNamespace(password=password_hash) if password_hash else None
    )
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    monkeypatch.setattr(auth, "get_engine", lambda: engine)

    app = Flask(__name__)
    app.secret_key = "test"
    app.register_blueprint(auth.auth_bp, url_prefix="/auth")
    return app.test_client(), conn


@pytest.fixture
def hash_valido():
    return django_pbkdf2_sha256.hash("correcta")


def test_password_correcta_crea_sesion(monkeypatch, hash_valido):
    client, conn = make_client(monkeypatch, hash_valido)
    res = client.post("/auth/login", data={"username": "u", "password": "correcta"})
    assert res.headers["Location"] == "/"
    with client.session_transaction() as s:
        assert s["user"] == "u"
    assert "DEV_SIIR.dbo.auth_user" in str(conn.execute.call_args[0][0])


def test_password_incorrecta_no_crea_sesion(monkeypatch, hash_valido):
    client, _ = make_client(monkeypatch, hash_valido)
    res = client.post("/auth/login", data={"username": "u", "password": "mala"})
    assert res.headers["Location"].endswith("/auth/login_page?error=1")
    with client.session_transaction() as s:
        assert "user" not in s


def test_usuario_inexistente(monkeypatch):
    client, _ = make_client(monkeypatch, None)
    res = client.post("/auth/login", data={"username": "nadie", "password": "x"})
    assert res.headers["Location"].endswith("/auth/login_page?error=1")


def test_password_inusable_django(monkeypatch):
    """Django guarda '!xxx' para cuentas sin password: no debe reventar."""
    client, _ = make_client(monkeypatch, "!aBcDeF123456789")
    res = client.post("/auth/login", data={"username": "u", "password": ""})
    assert res.headers["Location"].endswith("/auth/login_page?error=1")
