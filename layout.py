from dash import clientside_callback, html, dcc, no_update
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import base64, os
from datetime import datetime

from tabs import tab_report
import report_export.callbacks.reportabilidad_cb
import callbacks.reportabilidad_callbacks
from reclamo import panel as reclamo_panel  # registra sus @callback al importarse
from powerbi_camiones import panel as powerbi_panel  # registra sus @callback al importarse

# === Utilidades ===
project_folder = os.path.dirname(os.path.realpath(__file__))
assets_folder = os.path.join(project_folder, 'assets')

_MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
_DAYS_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}

def _fmt_date():
    now = datetime.now()
    return f"{_DAYS_ES[now.weekday()]}, {now.day} De {_MONTHS_ES[now.month]} De {now.year}"

def local_img_to_html(path, img_name):
    image_filename = os.path.join(path, img_name)
    with open(image_filename, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode("UTF-8")
    return f"data:image/png;base64,{encoded}"


def render_sidebar():
    return html.Div(
        className="siir-sidebar",
        children=[
            # Brand
            html.Div([
                html.I(className="bi bi-grid-3x3 siir-brand-icon"),
                html.Div([
                    html.Div("Sistema SIIR", className="siir-brand-title"),
                    html.Div("Reconciliación y SAP", className="siir-brand-subtitle"),
                ]),
            ], className="siir-sidebar-brand"),

            html.Hr(className="siir-divider"),

            html.Div("ÁREAS DE TRABAJO", className="siir-section-label"),

            dbc.Nav([
                dbc.NavLink([
                    html.I(className="bi bi-file-earmark-text me-2"),
                    "Reportabilidad",
                ], href="#", id="nav-reportabilidad", className="siir-nav-link active", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-truck me-2"),
                    "Administración de Reclamo",
                ], href="#", id="nav-reclamo", className="siir-nav-link", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-cloud-upload me-2"),
                    "Carga PowerBI Camiones",
                ], href="#", id="nav-powerbi", className="siir-nav-link", n_clicks=0),
            ], vertical=True, pills=False),
        ]
    )


def render_main_header():
    return html.Div([
        # Breadcrumb
        html.Div([
            html.Span("SIIR", className="siir-bc-item"),
            html.Span(" / ", className="siir-bc-sep"),
            html.Span("HIDROMETALURGIA", className="siir-bc-item"),
            html.Span(" / ", className="siir-bc-sep"),
            html.Span("REPORTES", className="siir-bc-active"),
        ], className="siir-breadcrumb"),

        # Title + date row
        html.Div([
            # Left: title + welcome
            html.Div([
                html.H1([
                    html.Span("S", className="siir-accent"), "istema ",
                    html.Span("I", className="siir-accent"), "ntegrado de ",
                    html.Span("I", className="siir-accent"), "nformación y ",
                    html.Span("R", className="siir-accent"), "econciliación",
                ], className="siir-main-title"),
                html.Div([
                    html.Span("● ", className="siir-online-dot"),
                    "Bienvenido de vuelta,  ",
                    html.Span("", id="siir-username", className="fw-semibold"),
                ], className="siir-welcome"),
            ]),
            # Right: date + logout
            html.Div([
                html.Div([
                    html.Div("FECHA DEL SISTEMA", className="siir-date-label"),
                    html.Div(_fmt_date(), className="siir-date-value"),
                ], className="siir-date-block"),
                dbc.DropdownMenu(
                    label=html.I(className="bi bi-person-circle fs-5"),
                    children=[
                        dbc.DropdownMenuItem("Cerrar sesión", id="logout-link", n_clicks=0),
                    ],
                    nav=True,
                    align_end=True,
                    className="ms-3",
                ),
            ], className="d-flex align-items-center"),
        ], className="siir-header-row"),

        html.Hr(className="siir-header-divider"),
        dcc.Location(id="page-url", refresh=True),
    ], className="siir-page-header")


def render_footer():
    return html.Div([
        html.Span("2025 Control Estadístico Hidrometalúrgico ", className="fw-semibold"),
        html.Span("· Desarrollado por ", className="siir-footer-muted"),
        html.Span("Simplex Ingeniería", className="siir-footer-brand"),
    ], className="siir-footer")


subtabs = html.Div(
    id="subtabs-container",
    className="tab-anim",
    children=[
        html.Div(id="subtabs-report", children=tab_report.layout()),
        html.Div(
            id="subtabs-reclamo",
            style={"display": "none"},
            children=reclamo_panel.layout(),
        ),
        html.Div(
            id="subtabs-powerbi",
            style={"display": "none"},
            children=powerbi_panel.layout(),
        ),
    ]
)


def create_layout(app):
    return html.Div([
        render_sidebar(),
        html.Div([
            render_main_header(),
            subtabs,
            render_footer(),
        ], className="siir-main"),
    ], className="siir-wrapper")


def register_callbacks(app):
    @app.callback(
        Output("subtabs-report", "style"),
        Output("subtabs-reclamo", "style"),
        Output("subtabs-powerbi", "style"),
        Output("nav-reportabilidad", "className"),
        Output("nav-reclamo", "className"),
        Output("nav-powerbi", "className"),
        Input("nav-reportabilidad", "n_clicks"),
        Input("nav-reclamo", "n_clicks"),
        Input("nav-powerbi", "n_clicks"),
        prevent_initial_call=False,
    )
    def toggle_subtabs(n_rep, n_rec, n_pbc):
        # dash.ctx.triggered_id es None en la carga inicial -> por defecto
        # se muestra Reportabilidad, igual que antes.
        triggered = dash.ctx.triggered_id

        secciones = {
            "nav-reportabilidad": "reportabilidad",
            "nav-reclamo": "reclamo",
            "nav-powerbi": "powerbi",
        }
        activa = secciones.get(triggered, "reportabilidad")

        def estilo(nombre):
            return {"display": "block"} if nombre == activa else {"display": "none"}

        def clase(nombre):
            return "siir-nav-link active" if nombre == activa else "siir-nav-link"

        return (
            estilo("reportabilidad"),
            estilo("reclamo"),
            estilo("powerbi"),
            clase("reportabilidad"),
            clase("reclamo"),
            clase("powerbi"),
        )

    @app.callback(
        Output("siir-username", "children"),
        Input("page-url", "pathname"),
    )
    def update_username(pathname):
        try:
            import flask as _flask
            return _flask.session.get("username", "Invitado")
        except Exception:
            return "Invitado"

    clientside_callback(
        """
        function(n) {
            if (n) {
                fetch('/auth/logout', {method: 'GET'})
                .then(() => {
                    window.location.href = '/auth/login_page';
                });
            }
            return '';
        }
        """,
        Output("logout-link", "children"),
        Input("logout-link", "n_clicks"),
        prevent_initial_call=True
    )
