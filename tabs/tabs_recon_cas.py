# tabs_recon_cas.py
import os
import io
import base64
import datetime
import pandas as pd
import numpy as np
import dash
from dash import html, dcc, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from dash import no_update

# Utils propios
from tabs.utils_dash import (
    get_fig_bal_casos,        # devuelve src para <img> (base64/data-url o ruta servible)
    get_agua_his_casos,       # histórico
    get_data_agua_casos,      # caso activo
    get_data_save_casos,      # persiste edición de caso
)

# ====== Definiciones de columnas (AgGrid) ======
columnsDefs_data_casos = [
    {'field': 'caso_id',      'maxWidth': 80,  'editable': False},
    {'field': 'fecha_ini',    'maxWidth': 120, 'editable': False},
    {'field': 'fecha',        'maxWidth': 120, 'editable': True},
    {'field': 'nombre_caso',  'maxWidth': 180, 'editable': True},
    {'field': 'modelo',       'maxWidth': 120, 'editable': True},
    {'field': 'comentarios',  'maxWidth': 260, 'editable': True},
]

columnsDefs_hist_caso = [
    {'field': 'caso_id',      'maxWidth': 80,  'editable': False},
    {'field': 'fecha_ini',    'maxWidth': 120, 'editable': False},
    {'field': 'fecha',        'maxWidth': 120, 'editable': True},
    {'field': 'nombre_caso',  'maxWidth': 180, 'editable': True},
    {'field': 'modelo',       'maxWidth': 120, 'editable': True},
    {'field': 'comentarios',  'maxWidth': 260, 'editable': True},
]

# ====== Layout ======
def render_recon_cas():
    hoy = datetime.datetime.now().strftime('%Y-%m-%d')

    return html.Div([
        # Título
        dbc.Alert([
            html.I(className="bi bi-collection me-2"),
            "Administración de Casos"
        ], color="primary", className="mb-3"),

        # --- Parámetros de entrada ---
        dbc.Card([
            dbc.CardHeader(html.H5("Parámetros de entrada", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.FormFloating([
                            dbc.Input(id='fecha_inicio_caso', type='date', value=hoy),
                            dbc.Label("Fecha Inicio"),
                        ])
                    ], md=2),

                    dbc.Col([
                        dbc.FormFloating([
                            dbc.Input(id='fecha_final_caso', type='date', value=hoy),
                            dbc.Label("Fecha Final"),
                        ])
                    ], md=2),

                    dbc.Col([
                        html.Label("Opciones", className="fw-semibold"),
                        dbc.Checklist(
                            id="crea-caso",
                            options=[{"label": "Crear nuevo Caso", "value": "Si"}],
                            value=[],
                            switch=True,
                        ),
                    ], md=3),

                    dbc.Col([
                        dbc.FormFloating([
                            dbc.Input(id='id_caso_activo', type='number', min=0),
                            dbc.Label("Id Caso"),
                        ])
                    ], md=2),

                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-cloud-download me-2"), "Obtener Datos"],
                            id='btn-get-casos', n_clicks=0,
                            color="primary", className="w-100"
                        )
                    ], md=3),
                ], className="gy-3"),
            ])
        ], className="mb-4 shadow-sm border-0"),

        # --- Caso activo + acciones ---
        dbc.Card([
            dbc.CardHeader(html.H5("Caso activo", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dag.AgGrid(
                            id="data_casos2",
                            columnDefs=columnsDefs_data_casos,
                            className='ag-theme-balham',
                            style={"height": "160px", "width": "100%"},
                        )
                    ], md=9),

                    dbc.Col([
                        dbc.Stack([
                            dbc.Button(
                                [html.I(className="bi bi-save me-2"), "Guardar Datos"],
                                id='btn-save-casos', n_clicks=0,
                                color="success", className="w-100"
                            ),
                            html.Small(id='btn-sim-msg_caso', className='text-muted', children=' ')
                        ], gap=2)
                    ], md=3),
                ], className="gy-2"),
            ])
        ], className="mb-4 shadow-sm border-0"),

        # --- Visualización ---
        dbc.Card([
            dbc.CardHeader(html.H5("Visualización", className="mb-0")),
            dbc.CardBody([
                html.Label("Valores a visualizar", className="fw-semibold"),
                dbc.RadioItems(
                    id="agg-tab2",
                    options=[
                        {"label": "Medidos",      "value": "Medido"},
                        {"label": "Reconciliado", "value": "Reconciliado"},
                        {"label": "Tolerancia",   "value": "Tolerancia"},
                    ],
                    value="Reconciliado",
                    inline=True,
                ),
                html.Div(className="my-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            html.Img(
                                id="imagen_balance",
                                style={"width": "100%", "maxWidth": "1100px", "cursor": "zoom-in"}
                            ),
                            type="default"
                        ),
                        dbc.Stack(direction="horizontal", gap=2, className="mt-2", children=[
                            dbc.Button(
                                [html.I(className="bi bi-arrows-fullscreen me-2"), "Ver a pantalla completa"],
                                id="btn-full-img", color="secondary", outline=True
                            ),
                        ]),
                    ], md=12),
                ]),

                # Modal fullscreen con zoom
                dbc.Modal(
                    id="modal-img", is_open=False, fullscreen=True, scrollable=True, size="xl",
                    children=[
                        dbc.ModalHeader(dbc.ModalTitle("Imagen: Balance")),
                        dbc.ModalBody([
                            html.Div("Zoom", className="mb-1 small text-muted"),
                            dcc.Slider(id="zoom-img", min=0.5, max=3, step=0.1, value=1),

                            # Contenedor con scroll para la imagen ampliada
                            html.Div(
                                id="img-zoom-wrapper",
                                style={"overflow": "auto", "border": "1px solid #eee", "height": "70vh", "marginTop": "0.5rem"},
                                children=html.Img(id="imagen_balance_modal", style={"width": "100%", "height": "auto"})
                            ),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button("Cerrar", id="close-modal-img", className="ms-auto")
                        ),
                    ]
                )
            ])
        ], className="mb-4 shadow-sm border-0"),

        # --- Histórico ---
        dbc.Card([
            dbc.CardHeader(html.H5("Histórico de casos", className="mb-0")),
            dbc.CardBody([
                dag.AgGrid(
                    id="data_hcas2",
                    columnDefs=columnsDefs_hist_caso,
                    className='ag-theme-balham',
                    style={"height": "380px", "width": "100%"},
                )
            ])
        ], className="mb-4 shadow-sm border-0"),
    ])


# ====== Callbacks ======
def register_recon_callbacks(app):

    # Cargar datos de caso activo e histórico
    @app.callback(
        Output('data_casos2', 'rowData'),
        Output('data_hcas2', 'rowData'),
        Output('id_caso_activo', 'value'),
        Input('btn-get-casos', 'n_clicks'),
        State('fecha_inicio_caso', 'value'),
        State('fecha_final_caso', 'value'),
        State('crea-caso', 'value'),
        prevent_initial_call=True,
    )
    def cargar_casos(n_clicks, inicio, final, crea_caso):
        if not n_clicks or ctx.triggered_id != 'btn-get-casos':
            return dash.no_update, dash.no_update, dash.no_update

        crea_flag = 'Si' if (crea_caso == ['Si']) else 'No'
        # Puedes ajustar el formateo si tus funciones requieren hh:mm
        # inicio_tag = f"{inicio} 08:00"
        # final_tag  = f"{final} 07:00"

        df_caso = get_data_agua_casos(inicio, final, crea_flag)
        df_hist = get_agua_his_casos(final)

        caso_id = None
        if df_caso is not None and len(df_caso) > 0 and 'caso_id' in df_caso.columns:
            caso_id = int(df_caso['caso_id'].max())

         # Lo que guardamos en el Store (mínimo el caso_id)
        shared_payload = {
            "caso_id": caso_id,
            "data_casos2": (df_caso.round(4).to_dict('records') if df_caso is not None else [])
        }

        return (
            (df_caso.round(4).to_dict('records') if df_caso is not None else []),
            (df_hist.round(4).to_dict('records') if df_hist is not None else []),
            caso_id
        )
    # Si el usuario tipea manualmente un id, sincroniza el Store
    @app.callback(
        Output('recon-shared', 'data'),
        Input('id_caso_activo', 'value'),
        State('recon-shared', 'data'),
        State('fecha_final_caso', 'value'),
        prevent_initial_call=True
    )
    def sync_store_from_input(caso_id, shared, fecha_fin):
        shared = shared or {}
        shared["caso_id"] = caso_id
        shared["fecha"] = fecha_fin
        return shared

    # Guardar edición del caso activo
    @app.callback(
        Output('btn-sim-msg_caso', 'children'),
        Input('btn-save-casos', 'n_clicks'),
        State('data_casos2', 'rowData'),
        State('fecha_final_caso', 'value'),
        State('id_caso_activo', 'value'),
        prevent_initial_call=True,
    )
    def guardar_caso(n_clicks, data_rows, fecha_final, caso_id):
        if not n_clicks or ctx.triggered_id != 'btn-save-casos':
            return dash.no_update

        try:
            get_data_save_casos(data_rows or [], fecha_final, caso_id)
            return "✅ Datos guardados"
        except Exception as e:
            return f"❌ Error al guardar: {e}"

    # Actualizar imagen según selección e id caso activo
    @app.callback(
        Output('imagen_balance', 'src'),
        Input('agg-tab2', 'value'),
        Input('id_caso_activo', 'value'),
        prevent_initial_call=True,
    )
    def actualizar_imagen(vista, caso_id):
        if not caso_id:
            return dash.no_update
        try:
            return get_fig_bal_casos(caso_id, vista)
        except Exception as e:
            # Si prefieres mostrar una alerta, podrías devolver
            # un 1x1 transparente o similar.
            return dash.no_update
    # Abrir/cerrar modal y propagar el src de la imagen
    @app.callback(
        Output("modal-img", "is_open"),
        Output("imagen_balance_modal", "src"),
        Input("btn-full-img", "n_clicks"),
        Input("close-modal-img", "n_clicks"),
        State("modal-img", "is_open"),
        State("imagen_balance", "src"),
        prevent_initial_call=True
    )
    def toggle_modal(n_open, n_close, is_open, src):
        if ctx.triggered_id == "btn-full-img":
            # también actualizamos el href del link "Abrir en nueva pestaña"
            return True, src
        if ctx.triggered_id == "close-modal-img":
            return False, no_update
        return is_open, no_update

    # Slider de zoom (simple: cambia el ancho relativo)
    @app.callback(
        Output("imagen_balance_modal", "style"),
        Input("zoom-img", "value")
    )
    def zoom_image(zoom):
        zoom = zoom or 1
        return {"width": f"{int(zoom*100)}%", "height": "auto"}
