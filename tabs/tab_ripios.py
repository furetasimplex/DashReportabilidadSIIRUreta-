import pandas as pd
import numpy as np
from dash import html, Input, Output, State, callback, dcc  # 👈 ya no necesitas importar dcc
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
    return html.Div([

        # Stores globales
        dcc.Store(id='selected-cells-sulfuro', storage_type='memory'),
        dcc.Store(id='selected-cells-oxido', storage_type='memory'),
        dcc.Store(id='zoom-level-store', storage_type='memory'),

        dbc.Tabs(
            id="tabs-main",
            active_tab='tab-app1',
            className="mb-3",
            children=[

                dbc.Tab(
                    label='PAD sulfuro',
                    tab_id='tab-app1',
                    children=app1.layout()    # ⬅ directo, sin callback
                ),

                dbc.Tab(
                    label='PAD óxido',
                    tab_id='tab-app2',
                    children=app2.layout()    # ⬅ directo, sin callback
                ),
            ],
        ),
    ])

# ========================
# ✅ CALLBACKS
# ========================

@callback(
    Output('selected-cells', 'data', allow_duplicate=True),
    Input('tabs-main', 'active_tab'),
    prevent_initial_call=True
)
def clear_selection_on_tab_change(tab):
    """Resetea selección al cambiar de pestaña."""
    return []
