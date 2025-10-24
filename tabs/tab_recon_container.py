# tabs/tab_recon_container.py
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from tabs.tabs_recon_cas import render_recon_cas, register_recon_callbacks
from tabs.tab6 import render_tab6, register_tab6_callbacks
from tabs import tabreportabilidad

layout = dbc.Card(
    [
        dcc.Store(id="active-case", data={}),
        dcc.Store(id="recon-data", data=None),
        dbc.CardHeader(
            html.H4(id="header-recon-title", className="mb-0 text-primary fw-bold")
        ),
        dbc.CardBody(
            [
                
                dcc.Tabs(
                    id="recon-subtabs",
                    value="recon-admin",
                    persistence=True,
                    persistence_type="session",
                    children=[
                        dcc.Tab(label="1 Administrar casos", value="recon-admin"),
                        dcc.Tab(label="2 Reconciliar", value="recon-6"),
                        dcc.Tab(label="3 Resumen Reconciliación", value="tab-reporte"),
                    ],
                ),
                html.Div(id="recon-content", className="mt-3"),
            ]
        ),
    ],
    className="shadow-sm border-0",
)

def register_callbacks(app):
    register_recon_callbacks(app)
    register_tab6_callbacks(app)

    @app.callback(Output("recon-content", "children"), Input("recon-subtabs", "value"))
    def _render_content(subtab_value):
        if subtab_value == "recon-admin":
            return render_recon_cas()
        elif subtab_value == "recon-6":
            return render_tab6()
        elif subtab_value == "tab-reporte":
            # Aquí puedes llamar a una nueva función o archivo para el layout de reportes
            return tabreportabilidad.render_layout_reporte()
        return html.Div("Seleccione una pestaña de importación.", className="text-muted")
    
    @app.callback(
        Output("header-recon-title", "children"),
        Input("active-case", "data"),
    )
    def update_header(active_case):
        if not active_case or "caso_id" not in active_case:
            return "📈 Reconciliador Área Seca — Sin caso activo"
        caso_id = active_case.get("caso_id", "—")
        fi = active_case.get("fecha_inicio", "")
        ff = active_case.get("fecha_fin", "")
        return f"📈 Reconciliador Área Seca — Caso activo: {caso_id} ({fi} → {ff})"