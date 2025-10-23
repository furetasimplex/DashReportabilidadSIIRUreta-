
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

import tabs.tab_import_mov as tab_mov
import tabs.tab_import_datos_filtrados as tab_datos
import tabs.tab_import_apilado as tab_apilado
import tabs.tab_importar_leyes as tab_leyes_granulo
import tabs.tab_importar_recuperaciones as tab_recuperacion
import tabs.tab_importar_reclamo_camiones as tab_reclamos


dash.register_page(__name__, path="/reportabilidad", name="Reportabilidad")

layout = html.Div([
    dbc.CardHeader(html.H4("Módulo de Reportabilidad", className="p-2")),

    html.Div(id='content-subtab-importacion', className="mt-3")
])
def register_callbacks(app):
    tab_datos.register_callbacks(app)
    tab_mov.register_callbacks(app)

    @app.callback(
        Output('content-subtab-importacion', 'children'),
        Input('tabs-importacion', 'active_tab')
    )
    def render_content(subtab):
        if subtab == 'tab-datos-filtrados':
            return tab_datos.layout
        elif subtab == 'tab-mov-cam':
            return tab_mov.layout
        else:
            return html.Div("Seleccione una pestaña de importación.")
