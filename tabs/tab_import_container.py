
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


dash.register_page(__name__, path="/importar_datos", name="Importar Datos")

layout = html.Div([
    dbc.CardHeader(html.H4("Módulo de Importación de Datos", className="p-2")),
    dbc.Tabs(
        id='tabs-importacion',
        active_tab='tab-datos-filtrados',  # cambia 'value' → 'active_tab'
        className="mb-3",
        children=[
            dbc.Tab(label='Datos Planta (datos_filtrados)', tab_id='tab-datos-filtrados'),
            dbc.Tab(label='Movimientos Mina (mov_cam)', tab_id='tab-mov-cam'),
            dbc.Tab(label='Apilado y Rotopala', tab_id='tab-apilado'),
            dbc.Tab(label='Importar Leyes y Granulometría', tab_id='tab-importar-leyes-granulo'),
            dbc.Tab(label='Importar Reporte Recuperaciones', tab_id='tab-importar-recuperacion'),
            dbc.Tab(label='Reclamo Camiones', tab_id='tab-reclamos'),
        ],
    ),
    html.Div(id='content-subtab-importacion', className="mt-3")
])

def register_callbacks(app):
    tab_datos.register_callbacks(app)
    tab_mov.register_callbacks(app)
    tab_apilado.register_callbacks(app)
    tab_leyes_granulo.register_callbacks(app)
    tab_recuperacion.register_callbacks(app)
    tab_reclamos.register_callbacks(app)

    @app.callback(
        Output('content-subtab-importacion', 'children'),
        Input('tabs-importacion', 'active_tab')
    )
    def render_content(subtab):
        if subtab == 'tab-datos-filtrados':
            return tab_datos.layout
        elif subtab == 'tab-mov-cam':
            return tab_mov.layout
        elif subtab == 'tab-apilado':
            return tab_apilado.layout
        elif subtab == 'tab-importar-leyes-granulo':
             return tab_leyes_granulo.layout
        elif subtab == 'tab-importar-recuperacion':
             return tab_recuperacion.layout
        elif subtab == 'tab-reclamos':
            return tab_reclamos.layout
        else:
            return html.Div("Seleccione una pestaña de importación.")
