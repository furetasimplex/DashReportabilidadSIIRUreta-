import pandas as pd
import numpy as np
from dash import html, dcc, Input, Output, State, callback  # ← usamos callback global
from dash import dash_table
import plotly.graph_objs as go
import plotly.express as px
from scipy import stats
from skgstat import Variogram
import io
import base64

# Importa layouts y (si los tienes) callbacks internos definidos con @callback
import tabs.sulfuro as app1
import tabs.oxido as app2

def render_tab():
    """Devuelve el layout del contenedor con tabs."""
    return html.Div([
        dcc.Store(id='selected-cells', data=[]),
        dcc.Store(id='zoom-level', data=1),
        dcc.Tabs(
            id="tabs-main",
            value='tab-app1',
            children=[
                dcc.Tab(label='PAD sulfuro', value='tab-app1'),
                dcc.Tab(label='PAD oxido', value='tab-app2'),
            ],
            colors={
                "border": "#018582",
                "primary": "#8ba8b7",
                "background": "#adc2cc "
            }
        ),
        html.Div(id='tabs-content')
    ])

# ❌ No llames app1.register_callbacks(app) / app2.register_callbacks(app) aquí,
# porque 'app' no existe en este módulo. Si esos módulos definen callbacks,
# que usen también @callback (global) o regístralos desde donde sí tienes 'app'.

@callback(
    Output('tabs-content', 'children'),
    Input('tabs-main', 'value')
)
def render_content(tab):
    if tab == 'tab-app1':
        # Asegúrate de que app1.layout exista
        return app1.layout
    elif tab == 'tab-app2':
        # Asegúrate de que app2.layout exista
        return app2.layout
    return html.P("This is an example of a multi-tab app.")

@callback(
    Output('selected-cells', 'data', allow_duplicate=True),  # 👈 importante
    Input('tabs-main', 'value'),
    prevent_initial_call=True
)
def clear_selection_on_tab_change(tab):
    return []
