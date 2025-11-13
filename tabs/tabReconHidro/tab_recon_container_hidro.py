# tabs/tab_recon_container.py
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from .tabs_recon_cas_hidro import render_recon_cas_hidro, register_recon_callbacks_hidro
from .tab_recon_hidro import render_recon_hidro, register_recon_hidro_callbacks
from tabs.tabReconHidro import tabreportabilidad_hidro

layout = dbc.Card(
    [
        dcc.Store(id="active-case-hidro", data={}),
        dcc.Store(id="recon-data-hidro", data=None),
        dbc.CardHeader(
            html.H4(id="header-recon-title-hidro", className="mb-0 text-primary fw-bold")
        ),
       # dbc.CardHeader(html.H4("📈 Reconciliador Hidrometalúrgico Completo", className="mb-0")),
        dbc.CardBody(
            [         
                dcc.Tabs(
                    id="recon-subtabs-hidro",
                    value="recon-admin-hidro",
                    persistence=True,
                    persistence_type="session",
                    children=[
                        dcc.Tab(label="1 Administrar casos", value="recon-admin-hidro"),
                        dcc.Tab(label="2 Reconciliar", value="recon-hidro"),
                        dcc.Tab(label="3 Resumen Reconciliación", value="tab-reporte-hidro"),
                    ],
                ),
                html.Div(id="recon-content-hidro", className="mt-3"),
            ]
        ),
    ],
    className="shadow-sm border-0",
)

def register_callbacks(app):
    register_recon_callbacks_hidro(app)
    register_recon_hidro_callbacks(app)

    @app.callback(Output("recon-content-hidro", "children"), Input("recon-subtabs-hidro", "value"))
    def _render_content_hidro(subtab_value):
        if subtab_value == "recon-admin-hidro":
            return render_recon_cas_hidro()
        elif subtab_value == "recon-hidro":
            return render_recon_hidro()
        elif subtab_value == "tab-reporte-hidro":
            # Aquí puedes llamar a una nueva función o archivo para el layout de reportes
            return tabreportabilidad_hidro.render_layout_reporte()
        return html.Div("Seleccione una pestaña de importación.", className="text-muted")

    
    @app.callback(
        Output("header-recon-title-hidro", "children"),
        Input("active-case-hidro", "data"),
    )
    def update_header(active_case):
        if not active_case or "caso_id" not in active_case:
            return "📈 Reconciliador Área Hidrometalúrgica — Sin caso activo"
        caso_id = active_case.get("caso_id", "—")
        fi = active_case.get("fecha_inicio", "")
        ff = active_case.get("fecha_fin", "")
        # Si no hay caso cargado aún
        if not caso_id:
            return "📈 Reconciliador Área Hidrometalúrgica — Sin caso activo"

        # Si no hay fechas (por ejemplo, caso recién creado)
        if not fi or not ff:
            return f"📈 Reconciliador Área Hidrometalúrgica — Caso activo: {caso_id}"

        # Formato final
        return f"📈 Reconciliador Área Hidrometalúrgica — Caso activo: {caso_id} ({fi} → {ff})"