
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

import tabs.tab_import_mov as tab_mov
import tabs.tab_import_datos_filtrados as tab_datos
import tabs.tab_import_apilado as tab_apilado
import tabs.tab_importar_leyes as tab_leyes_granulo
import tabs.tab_importar_recuperaciones as tab_recuperacion


dash.register_page(__name__, path="/importar_datos", name="Importar Datos")

layout = html.Div([
    html.H4("Módulo de Importación de Datos"),
    dcc.Tabs(
        id='tabs-importacion',
        value='tab-datos-filtrados',
        children=[
            dcc.Tab(label='Datos Planta (datos_filtrados)', value='tab-datos-filtrados'),
            dcc.Tab(label='Movimientos Mina (mov_cam)', value='tab-mov-cam'),
            dcc.Tab(label='Apilado y Rotopala', value='tab-apilado'),
            dcc.Tab(label='Importar Leyes y Granulometría', value='tab-importar-leyes-granulo'),
            dcc.Tab(label='Importar Reporte recuperaciones', value='tab-importar-recuperacion'),
        ]
    ),
    html.Div(id='content-subtab-importacion', style={"marginTop": "20px"})
])

def register_callbacks(app):
    tab_datos.register_callbacks(app)
    tab_mov.register_callbacks(app)
    tab_apilado.register_callbacks(app)
    tab_leyes_granulo.register_callbacks(app)
    tab_recuperacion.register_callbacks(app)

    @app.callback(
        Output('content-subtab-importacion', 'children'),
        Input('tabs-importacion', 'value')
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
        else:
            return html.Div("Seleccione una pestaña de importación.")
