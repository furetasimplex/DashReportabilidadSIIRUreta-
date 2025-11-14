import pandas as pd
import numpy as np
from dash import html, Input, Output, State, callback  # 👈 ya no necesitas importar dcc
import plotly.graph_objs as go
import plotly.express as px
import dash_bootstrap_components as dbc
from scipy import stats
from skgstat import Variogram
import io
import base64

# Importa layouts (cada uno debe tener su layout ya definido)
import tabs.sulfuro as app1
import tabs.oxido as app2


def render_tab():
    """Devuelve el layout del contenedor con tabs (usando dbc.Tabs)."""
    return html.Div([
        # Stores (mantienen estado)
            dbc.Tabs(
                id="tabs-main",
                active_tab='tab-app1',  # 👈 cambia value= por active_tab=
                className="mb-3",
                children=[
                    dbc.Tab(label='PAD sulfuro', tab_id='tab-app1'),
                    dbc.Tab(label='PAD óxido', tab_id='tab-app2'),
                ],
            ),
            html.Div(id='tabs-content')   
        ,
        # Mantén tus dcc.Store si los usas en callbacks
        html.Div([
            html.Div(id='hidden-store-container', style={'display': 'none'}),
            html.Div([
                html.Div(id='selected-cells'),
                html.Div(id='zoom-level-store')
            ])
        ])
    ])


# ========================
# ✅ CALLBACKS
# ========================

@callback(
    Output('tabs-content', 'children'),
    Input('tabs-main', 'active_tab')  # 👈 cambia value → active_tab
)
def render_content(tab):
    """Renderiza el contenido de cada tab."""
    if tab == 'tab-app1':
        return app1.layout
    elif tab == 'tab-app2':
        return app2.layout
    return html.P("Seleccione una pestaña.")


@callback(
    Output('selected-cells', 'children', allow_duplicate=True),
    Input('tabs-main', 'active_tab'),
    prevent_initial_call=True
)
def clear_selection_on_tab_change(tab):
    """Resetea selección al cambiar de pestaña."""
    return []
