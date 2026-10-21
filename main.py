import os
from env_loader import load_app_env, require_app_env

load_app_env()
require_app_env("LOGIN_DATABASE", "SECRET_KEY")

# Debe ejecutarse antes de importar layout/auth/report_export: esos módulos
# construyen nombres SQL al importarse y no deben ocultar un .env PROD inválido.
from db_startup_check import run_startup_db_check

run_startup_db_check()

from dash import Dash
import dash_bootstrap_components as dbc
from flask import session, redirect, request

from auth import auth_bp
from layout import create_layout, register_callbacks
from report_export.callbacks.reportabilidad_cb import setup_download_route

external_stylesheets = [
    dbc.themes.FLATLY,
    "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css",
]

external_scripts = [
    "https://cdn.jsdelivr.net/npm/date-fns@4.1.0/locale/es/cdn.min.js",
]

app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    external_scripts=external_scripts,
    suppress_callback_exceptions=True,
    # El sondeo de progreso no debe mantener la pestaña en "Updating...".
    update_title=None,
)
server = app.server
setup_download_route(server)
app.title = "Dashboard Hidrometalurgico Spence"

# 🔐 Config Flask
server.secret_key = os.environ["SECRET_KEY"]
server.register_blueprint(auth_bp, url_prefix="/auth")

# Layout Dash
app.layout = create_layout(app)
register_callbacks(app)

# 🚫 Protege Dash si no hay sesión
@server.before_request
def protect_dash():
    if request.path.startswith("/static"):
        return  # Permitir acceso a archivos estáticos  sin autenticación
    if not session.get("user") and not request.path.startswith("/auth"):
        return redirect("/auth/login_page")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8065"))
    app.run(debug=True, port=port)
