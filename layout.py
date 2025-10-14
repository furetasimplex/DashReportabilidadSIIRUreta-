from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import base64, os
from dash import callback_context

# === Importa tus tabs ===
from tabs.tab1 import render_tab1, register_tab1_callbacks
from tabs.tab2 import render_tab2, register_tab2_callbacks
from tabs.tab3 import render_tab3, register_tab3_callbacks
from tabs.tab4 import render_tab4, register_tab4_callbacks
from tabs.tab_ripios import render_tab
from tabs import sulfuro as tab_sulfuro
from tabs import oxido as tab_oxido
from tabs import tabreportabilidad
from tabs.hidroApp.tab_hidro import render_layout_hidro
from tabs.hidroApp.callbacks_hidro import register_apphidro_callbacks
from tabs import tab_recon_container, tab_import_container


# === Utilidades ===
project_folder = os.path.dirname(os.path.realpath(__file__))
assets_folder = os.path.join(project_folder, 'assets')

def local_img_to_html(path, img_name):
    image_filename = os.path.join(path, img_name)
    with open(image_filename, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode("UTF-8")
    return f"data:image/png;base64,{encoded}"

"""             
dbc.Col(html.Img(src=local_img_to_html(assets_folder, 'logo.png'),
            style={'height': '36px'}), width="auto"),
"""

def render_header():
    return dbc.Row(
        [
            dbc.Col(html.Img(src=local_img_to_html(assets_folder, 'spenceBhpLogo.png'),
                             style={'height': '70px'}), width="auto"),
            dbc.Col(html.Div("Control Estadístico Hidrometalúrgico",
                             className="fs-3 fw-bold"), width="auto"),
        ],
        className="align-items-center g-4 py-2"
    )

def render_footer():
    return dbc.Container(
        dbc.Row(
            [
                # Logo a la izquierda
                dbc.Col(
                    html.Img(
                        src=local_img_to_html(assets_folder, "logo.png"),
                        style={"height": "36px", "objectFit": "contain"},
                    ),
                    width="auto",
                ),

                # Texto centrado
                dbc.Col(
                    html.Div(
                        [
                            html.Span("2025 Control Estadístico Hidrometalúrgico ", className="fw-semibold"),
                            html.Span("· Desarrollado por ", className="text-secondary"),
                            html.Span("Simplex Ingeniería", className="text-primary fw-semibold"),
                        ],
                        className="text-center small",
                    ),
                    className="d-flex align-items-center justify-content-center",
                ),

                dbc.Col(
                    html.Div(
                        [
                            html.A(
                                html.I(className="bi bi-envelope-fill"),
                                href="mailto:contacto@simplexingenieria.cl",
                                className="text-primary mx-2",
                            ),
                        ],
                        className="d-flex justify-content-center align-items-center",
                    ),
                    width="auto",
                ),
            ],
            className="align-items-center justify-content-between py-2",
        ),
        fluid=True,
        className="footer-container bg-white border-top shadow-sm mt-4 py-2 rounded-3",
    )


def create_layout(app):
    # Registrar callbacks previos (igual que antes)
    register_tab1_callbacks(app)
    register_tab2_callbacks(app)
    register_tab3_callbacks(app)
    register_tab4_callbacks(app)
    tab_recon_container.register_callbacks(app)
    tab_import_container.register_callbacks(app)
    register_apphidro_callbacks(app)
    tab_sulfuro.register_callbacks(app)
    tab_oxido.register_callbacks(app)
    tabreportabilidad.register_callbacks_reporte(app)

    navbar = dbc.Navbar(
        dbc.Container(
            [
                dbc.Nav(
                    [
                        dbc.NavLink("📊 Resumen Estadístico Mina", href="#", id="nav-mina", className="text-primary fw-semibold mx-2"),
                        dbc.NavLink("⚙️ Control Área Seca", href="#", id="nav-seca", className="text-primary fw-semibold mx-2"),
                        dbc.NavLink("💧 Control Área Húmeda", href="#", id="nav-humeda", className="text-primary fw-semibold mx-2"),
                        dbc.NavLink("📦 Administración y Reconciliación", href="#", id="nav-admin", className="text-primary fw-semibold mx-2"),
                    ],
                    pills=True,
                    justified=True,
                    className="rounded-3 p-1 bg-white",
                ),
            ],
            fluid=True,
        ),
        color="light",
        dark=False,
        class_name="border-0 shadow-sm rounded-3 mb-3 py-1",
    )

    return dbc.Container(
        [
            render_header(),
            navbar,
            html.Div(id="subtabs-container", className="mt-2"),
            html.Div(id="tab-content", className="mt-3"),
            render_footer(),

        ],
        fluid=True,
        className="py-3",
    )


def register_callbacks(app):
    @app.callback(
        Output("nav-mina", "active"),
        Output("nav-seca", "active"),
        Output("nav-humeda", "active"),
        Output("nav-admin", "active"),
        Input("nav-mina", "n_clicks"),
        Input("nav-seca", "n_clicks"),
        Input("nav-humeda", "n_clicks"),
        Input("nav-admin", "n_clicks"),
        prevent_initial_call=False,
    )
    def toggle_active(mina, seca, humeda, admin):
        ctx = callback_context
        # Si no hay interacción aún, deja activo el primero
        if not ctx.triggered:
            return True, False, False, False

        clicked = ctx.triggered[0]["prop_id"].split(".")[0]
        return (
            clicked == "nav-mina",
            clicked == "nav-seca",
            clicked == "nav-humeda",
            clicked == "nav-admin",
        )
        # === 2️⃣ Renderizar subtabs según grupo activo ===

    @app.callback(
        Output("subtabs-container", "children"),
        [
            Input("nav-mina", "n_clicks"),
            Input("nav-seca", "n_clicks"),
            Input("nav-humeda", "n_clicks"),
            Input("nav-admin", "n_clicks"),
        ],
        prevent_initial_call=False,
    )
    def render_subtabs(mina, seca, humeda, admin):
        ctx = callback_context
        if not ctx.triggered:
            return render_tab1()
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "nav-mina":
            return render_tab1()

        elif button_id == "nav-seca":
            return dcc.Tabs(
                id="subtabs",
                value="tab2",
                className="subtabs",
                children=[
                    dcc.Tab(label="Conciliación Operacional", value="tab2"),
                    dcc.Tab(label="Control Apilado", value="tab3"),
                    dcc.Tab(label="Torres de Muestreo", value="tab4"),
                ],
            )

        elif button_id == "nav-humeda":
            return dcc.Tabs(
                id="subtabs",
                value="tab5",
                className="subtabs",
                children=[
                    dcc.Tab(label="Recuperación", value="tab5"),
                    dcc.Tab(label="Control de Riego", value="tab8"),
                    dcc.Tab(label="Producción Catódica", value="tab9"),
                ],
            )

        elif button_id == "nav-admin":
            return dcc.Tabs(
                id="subtabs",
                value="tab7",
                className="subtabs",
                children=[
                    dcc.Tab(label="Importar data base", value="tab7"),
                    dcc.Tab(label="Reconciliador", value="recon"),
                    dcc.Tab(label="Reconciliador Hidro", value="recon_hidro"),
                ],
            )

        return None

    # === Renderizar contenido según subtab activo ===
    @app.callback(Output("tab-content", "children"), Input("subtabs", "value"), prevent_initial_call=True)
    def render_subtab_content(tab):
        if tab == "tab2":
            return render_tab2()
        elif tab == "tab3":
            return render_tab3()
        elif tab == "tab4":
            return render_tab4()
        elif tab == "tab5":
            return render_tab()
        elif tab == "tab8":
            return html.Div("Control de riego no implementado aún.", className="fw-semibold")
        elif tab == "tab9":
            return html.Div("Producción catódica no implementado aún.", className="fw-semibold")
        elif tab == "tab7":
            return tab_import_container.layout
        elif tab == "recon":
            return tab_recon_container.layout
        elif tab == "recon_hidro":
            return render_layout_hidro()
        return html.Div("Seleccione una pestaña.")
