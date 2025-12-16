
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

from tabs.tabs_recon_cas import render_recon_cas, register_recon_callbacks
from tabs.tab6 import render_tab6, register_tab6_callbacks
from tabs import tabreportabilidad
from tabs.tab_analisis_reconciliacion import (
    render_tab_analisis_reconciliacion,
    register_analisis_reconciliacion_callbacks
)

layout = dbc.Card(
    [
        dcc.Store(id="active-case", data={}),
        dcc.Store(id="recon-data", data=None, storage_type="memory"),
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
                        dcc.Tab(label="4 Estadística Reconciliación", value="tab-estadistica"),
                    ],
                ),
                
                html.Div(
                    id="recon-content-container", 
                    className="mt-3", 
                    children=[
                        html.Div(
                            id="content-recon-admin", 
                            children=render_recon_cas(), 
                            style={'display': 'block'} 
                        ),
                        html.Div(
                            id="content-recon-6", 
                            children=render_tab6(), 
                            style={'display': 'none'} 
                        ),
                        html.Div(
                            id="content-tab-reporte", 
                            children=tabreportabilidad.render_layout_reporte(), 
                            style={'display': 'none'} 
                        ),
                        html.Div(
                            id="content-tab-estadistica",
                            children=render_tab_analisis_reconciliacion(),
                            style={'display': 'none'}
                        ),
                    ]
                ),
            ]
        ),
    ],
    className="shadow-sm border-0",
)

def register_callbacks(app):
    register_recon_callbacks(app)
    register_tab6_callbacks(app)
    register_analisis_reconciliacion_callbacks(app)

    @app.callback(
    [
        Output("content-recon-admin", "style"),
        Output("content-recon-6", "style"),
        Output("content-tab-reporte", "style"),
        Output("content-tab-estadistica", "style"),
    ],
    Input("recon-subtabs", "value"),
)
    def toggle_tab_content(subtab_value):

        style_show = {'display': 'block'}
        style_hide = {'display': 'none'}

        if subtab_value == "recon-admin":
            return style_show, style_hide, style_hide, style_hide

        elif subtab_value == "recon-6":
            return style_hide, style_show, style_hide, style_hide

        elif subtab_value == "tab-reporte":
            return style_hide, style_hide, style_show, style_hide

        elif subtab_value == "tab-estadistica":
            return style_hide, style_hide, style_hide, style_show

        # fallback OBLIGATORIO (4 valores)
        return style_show, style_hide, style_hide, style_hide

    
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