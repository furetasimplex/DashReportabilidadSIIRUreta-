from dash import html, dcc
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import base64, os

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

def render_header():
    return dbc.Row(
        [
            dbc.Col(html.Img(src=local_img_to_html(assets_folder, 'logo.png'),
                             style={'height': '36px'}), width="auto"),
            dbc.Col(html.Img(src=local_img_to_html(assets_folder, 'spenceBhpLogo.png'),
                             style={'height': '70px'}), width="auto"),
            dbc.Col(html.Div("Control Estadístico Hidrometalúrgico",
                             className="fs-3 fw-bold"), width="auto"),
        ],
        className="align-items-center g-4 py-2"
    )


# ======================================
# LAYOUT PRINCIPAL (dcc.Tabs agrupados)
# ======================================
def create_layout(app):
    # Registrar callbacks existentes
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

    # Layout principal
    return dbc.Container(
        [
            render_header(),

            dcc.Store(id="active-case", data={}, storage_type="memory"),
            dcc.Store(id="recon-data", data=[], storage_type="memory"),
            dcc.Store(id="recon-results", data=[], storage_type="memory"),

            dbc.Card(
                dbc.CardBody(
                    [
                        # ==== Tabs principales agrupados ====
                        dcc.Tabs(
                            id="tabs",
                            value="tab1",
                            className="custom-tabs",
                            children=[
                                # Grupo 1
                                dcc.Tab(label="📊 Resumen Estadístico Mina", value="tab1"),

                                # Separador visual
                                dcc.Tab(label="── Área Seca ──", value="sep1", disabled=True, className="separator-tab"),

                                # Grupo 2
                                dcc.Tab(label="Conciliación Operacional", value="tab2"),
                                dcc.Tab(label="Control Apilado", value="tab3"),
                                dcc.Tab(label="Torres de Muestreo", value="tab4"),

                                dcc.Tab(label="── Área Húmeda ──", value="sep2", disabled=True, className="separator-tab"),

                                # Grupo 3
                                dcc.Tab(label="Recuperación", value="tab5"),
                                dcc.Tab(label="Control de Riego", value="tab8"),
                                dcc.Tab(label="Producción Catódica", value="tab9"),

                                dcc.Tab(label="── Administración ──", value="sep3", disabled=True, className="separator-tab"),

                                # Grupo 4
                                dcc.Tab(label="Importar data base", value="tab7"),
                                dcc.Tab(label="Reconciliador", value="recon"),
                                dcc.Tab(label="Reconciliador Hidro", value="recon_hidro"),
                            ],
                        ),

                        html.Div(id="tab-content", className="mt-4"),
                    ]
                ),
                className="shadow-sm border-0"
            ),
        ],
        fluid=True,
        className="py-3"
    )


# ======================================
# CALLBACKS (idéntico al tuyo original)
# ======================================
def register_callbacks(app):
    @app.callback(Output("tab-content", "children"), Input("tabs", "value"))
    def render_content(tab):
        if tab == "tab1":
            return render_tab1()
        # Control área seca
        elif tab == "tab2":
            return render_tab2()
        elif tab == "tab3":
            return render_tab3()
        elif tab == "tab4":
            return render_tab4()
        # Control área húmeda
        elif tab == "tab5":
            return render_tab()
        elif tab == "tab8":
            return html.Div("Control de riego no implementado aún.")
        elif tab == "tab9":
            return html.Div("Producción catódica no implementado aún.")
        # Administración
        elif tab == "tab7":
            return tab_import_container.layout
        elif tab == "recon":
            return tab_recon_container.layout
        elif tab == "recon_hidro":
            return render_layout_hidro()
        return html.Div("Contenido no implementado aún.")
