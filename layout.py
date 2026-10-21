from dash import clientside_callback, html, dcc, no_update
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import base64, os
from datetime import datetime

from tabs import tab_report, tab_curvas, tab_reconstitucion
import report_export.callbacks.reportabilidad_cb
import callbacks.reportabilidad_callbacks
from reclamo import panel as reclamo_panel  # registra sus @callback al importarse
from powerbi_camiones import panel as powerbi_panel  # registra sus @callback al importarse
from monitor_pi_tum import panel as monitor_pitum_panel
from lixiviacion import panel as lixiviacion_panel
from polinomio_acido import panel as polinomio_acido_panel

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
            # Compatibilidad del antiguo disparador; el acceso visible vive en Monitoreo.
            html.Button(id="nav-balance-m6", n_clicks=0, hidden=True, tabIndex=-1,
                        **{"aria-hidden": "true"}),
            dcc.Store(id="monitor-route-sync"),

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
                dbc.NavLink([
                    html.I(className="bi bi-activity me-2"),
                    "Monitoreo Correas Área Seca",
                ], href="#", id="nav-monitor-pitum", className="siir-nav-link", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-droplet me-2"),
                    "Lixiviación",
                ], href="#", id="nav-lixiviacion", className="siir-nav-link", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-calculator me-2"),
                    "Polinomio Ácido",
                ], href="#", id="nav-polinomio-acido", className="siir-nav-link", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-graph-up-arrow me-2"),
                    "Curvas y reconciliación",
                ], href="#", id="nav-curvas-recon", className="siir-nav-link", n_clicks=0),
                dbc.NavLink([
                    html.I(className="bi bi-stack me-2"),
                    "Reconstitución de Módulos",
                ], href="#", id="nav-reconstitucion", className="siir-nav-link", n_clicks=0),
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
            html.Span("REPORTABILIDAD", id="siir-bc-active", className="siir-bc-active"),
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
        html.Div(
            id="subtabs-monitor-pitum",
            style={"display": "none"},
            children=monitor_pitum_panel.layout(),
        ),
        html.Div(id="subtabs-lixiviacion", style={"display": "none"},
                 children=lixiviacion_panel.layout()),
        html.Div(id="subtabs-polinomio-acido", style={"display": "none"},
                 children=polinomio_acido_panel.layout()),
        # El árbol de Curvas se crea al entrar en la sección. Los callbacks de
        # la pestaña sí quedan registrados al iniciar la app.
        html.Div(id="subtabs-curvas-recon", style={"display": "none"}),
        html.Div(id="subtabs-reconstitucion", style={"display": "none"}),
        html.Div(id="subtabs-balance-m6", style={"display": "none"}),
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
        Output("subtabs-monitor-pitum", "style"),
        Output("subtabs-lixiviacion", "style"),
        Output("subtabs-polinomio-acido", "style"),
        Output("subtabs-curvas-recon", "style"),
        Output("subtabs-curvas-recon", "children"),
        Output("subtabs-reconstitucion", "style"),
        Output("subtabs-reconstitucion", "children"),
        Output("nav-reportabilidad", "className"),
        Output("nav-reclamo", "className"),
        Output("nav-powerbi", "className"),
        Output("nav-monitor-pitum", "className"),
        Output("nav-lixiviacion", "className"),
        Output("nav-polinomio-acido", "className"),
        Output("nav-curvas-recon", "className"),
        Output("nav-reconstitucion", "className"),
        Output("siir-bc-active", "children"),
        Output("subtabs-balance-m6", "style"),
        Output("subtabs-balance-m6", "children"),
        Output("nav-balance-m6", "className"),
        Output("pitum-tabs", "active_tab"),
        Input("nav-reportabilidad", "n_clicks"),
        Input("nav-reclamo", "n_clicks"),
        Input("nav-powerbi", "n_clicks"),
        Input("nav-monitor-pitum", "n_clicks"),
        Input("nav-lixiviacion", "n_clicks"),
        Input("nav-polinomio-acido", "n_clicks"),
        Input("nav-curvas-recon", "n_clicks"),
        Input("nav-reconstitucion", "n_clicks"),
        Input("nav-balance-m6", "n_clicks"),
        Input("page-url", "pathname"),
        Input("page-url", "hash"),
        State("subtabs-curvas-recon", "children"),
        State("subtabs-reconstitucion", "children"),
        State("subtabs-balance-m6", "children"),
        prevent_initial_call=False,
    )
    def toggle_subtabs(n_rep, n_rec, n_pbc, n_pitum, n_lix, n_polinomio, n_curvas,
                       n_reconstitucion, n_balance_m6, pathname, url_hash, mounted_curvas, mounted_reconstitucion,
                       mounted_balance_m6):
        # dash.ctx.triggered_id es None en la carga inicial -> por defecto
        # se muestra Reportabilidad, igual que antes.
        triggered = dash.ctx.triggered_id
        route_tabs = {
            "#monitoreo-correas/diagnostico": "pitum-diagnostico",
            "#monitoreo-correas/gestion-pi-tum": "pitum-gestion",
            "#monitoreo-correas/contingencia-m6": "pitum-contingencia-m6",
            "#balance-m6": "pitum-contingencia-m6",
            "#contingencia-m6": "pitum-contingencia-m6",
        }
        route_tab = None
        if triggered in (None, "page-url"):
            route_tab = route_tabs.get(url_hash)
            if route_tab is None and (pathname or "").rstrip("/") in ("/balance-m6", "/contingencia-m6"):
                route_tab = "pitum-contingencia-m6"
            if route_tab:
                triggered = "nav-balance-m6" if route_tab == "pitum-contingencia-m6" else "nav-monitor-pitum"
            elif triggered == "page-url":
                # Los href="#" existentes no deben sobrescribir el clic de otro menú.
                return (dash.no_update,) * 23

        secciones = {
            "nav-balance-m6": "monitor-pitum",
            "nav-curvas-recon": "curvas-recon",
            "nav-reconstitucion": "reconstitucion",
            "nav-reportabilidad": "reportabilidad",
            "nav-reclamo": "reclamo",
            "nav-powerbi": "powerbi",
            "nav-monitor-pitum": "monitor-pitum",
            "nav-lixiviacion": "lixiviacion",
            "nav-polinomio-acido": "polinomio-acido",
        }
        activa = secciones.get(triggered, "reportabilidad")

        def estilo(nombre):
            return {"display": "block"} if nombre == activa else {"display": "none"}

        def clase(nombre):
            return "siir-nav-link active" if nombre == activa else "siir-nav-link"

        children = dash.no_update
        if activa == "curvas-recon" and not mounted_curvas:
            children = tab_curvas.layout()
        reconstitucion_children = dash.no_update
        if activa == "reconstitucion" and not mounted_reconstitucion:
            reconstitucion_children = tab_reconstitucion.layout()
        titles = {
            "balance-m6": "BALANCE DE MASA M6",
            "reportabilidad": "REPORTABILIDAD", "reclamo": "ADMINISTRACIÓN DE RECLAMO",
            "powerbi": "CARGA POWERBI CAMIONES", "monitor-pitum": "MONITOREO CORREAS",
            "lixiviacion": "LIXIVIACIÓN", "polinomio-acido": "POLINOMIO ÁCIDO",
            "curvas-recon": "CURVAS Y RECONCILIACIÓN",
            "reconstitucion": "RECONSTITUCIÓN DE MÓDULOS",
        }
        return (
            estilo("reportabilidad"),
            estilo("reclamo"),
            estilo("powerbi"),
            estilo("monitor-pitum"),
            estilo("lixiviacion"),
            estilo("polinomio-acido"),
            estilo("curvas-recon"), children,
            estilo("reconstitucion"), reconstitucion_children,
            clase("reportabilidad"),
            clase("reclamo"),
            clase("powerbi"),
            clase("monitor-pitum"),
            clase("lixiviacion"),
            clase("polinomio-acido"),
            clase("curvas-recon"), clase("reconstitucion"), titles[activa],
            estilo("balance-m6"),
            dash.no_update,
            clase("balance-m6"),
            "pitum-contingencia-m6" if triggered == "nav-balance-m6" else (route_tab or dash.no_update),
        )

    clientside_callback(
        """function(tab, style) {
            const routes = {
                'pitum-diagnostico': '#monitoreo-correas/diagnostico',
                'pitum-gestion': '#monitoreo-correas/gestion-pi-tum',
                'pitum-contingencia-m6': '#monitoreo-correas/contingencia-m6'
            };
            const current = window.location.hash;
            const path = window.location.pathname;
            const visible = style && style.display === 'block';
            const normalizedPath = path.endsWith('/') ? path.slice(0, -1) : path;
            const canonicalPath = ['/balance-m6', '/contingencia-m6'].includes(normalizedPath) && visible ? '/' : path;
            const target = visible ? routes[tab] : '';
            if (target === undefined) return window.dash_clientside.no_update;
            if ((target !== current || canonicalPath !== path) && (visible || Object.values(routes).includes(current))) {
                window.history.replaceState(null, '', canonicalPath + window.location.search + target);
                // Mantener dcc.Location coherente para el próximo enlace o recarga.
                window.dispatchEvent(new PopStateEvent('popstate'));
            }
            return target;
        }""",
        Output("monitor-route-sync", "data"),
        Input("pitum-tabs", "active_tab"), Input("subtabs-monitor-pitum", "style"),
        prevent_initial_call=True,
    )

    tab_curvas.register_callbacks(app)
    tab_reconstitucion.register_callbacks(app)

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
