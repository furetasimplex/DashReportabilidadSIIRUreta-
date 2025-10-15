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
from tabs.tabReconHidro.utils.utils_dash import (
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
def render_recon_cas_hidro():
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
                            dbc.Input(id='fecha_inicio_caso_hidro', type='date', value=hoy),
                            dbc.Label("Fecha Inicio_hidro"),
                        ])
                    ], md=2),

                    dbc.Col([
                        dbc.FormFloating([
                            dbc.Input(id='fecha_final_caso_hidro', type='date', value=hoy),
                            dbc.Label("Fecha Final"),
                        ])
                    ], md=2),

                    dbc.Col([
                        html.Label("Opciones", className="fw-semibold"),
                        dbc.Checklist(
                            id="crea-caso_hidro",
                            options=[{"label": "Crear nuevo Caso", "value": "Si"}],
                            value=[],
                            switch=True,
                        ),
                    ], md=3),

                    dbc.Col([
                        dbc.FormFloating([
                            dbc.Input(id='id_caso_activo_hidro', type='number', min=0),
                            dbc.Label("Id Caso"),
                        ])
                    ], md=2),

                    dbc.Col([
                        dbc.Button(
                            [html.I(className="bi bi-cloud-download me-2"), "Obtener Datos"],
                            id='btn-get-casos_hidro', n_clicks=0,
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
                            id="data_casos2_hidro",
                            columnDefs=columnsDefs_data_casos,
                            className='ag-theme-balham',
                            style={"height": "160px", "width": "100%"},
                        )
                    ], md=9),

                    dbc.Col([
                        dbc.Stack([
                            dbc.Button(
                                [html.I(className="bi bi-save me-2"), "Guardar Datos"],
                                id='btn-save-casos_hidro', n_clicks=0,
                                color="success", className="w-100"
                            ),
                            html.Small(id='btn-sim-msg_caso_hidro', className='text-muted', children=' ')
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
                    id="agg-tab2_hidro",
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
                                id="imagen_balance_hidro",
                                style={"width": "100%", "maxWidth": "1100px", "cursor": "zoom-in"}
                            ),
                            type="default"
                        ),
                        dbc.Stack(direction="horizontal", gap=2, className="mt-2", children=[
                            dbc.Button(
                                [html.I(className="bi bi-arrows-fullscreen me-2"), "Ver a pantalla completa"],
                                id="btn-full-img_hidro", color="secondary", outline=True
                            ),
                        ]),
                    ], md=12),
                ]),

                # Modal fullscreen con zoom
                dbc.Modal(
                    id="modal-img_hidro", is_open=False, fullscreen=True, scrollable=True, size="xl",
                    children=[
                        dbc.ModalHeader(dbc.ModalTitle("Imagen: Balance")),
                        dbc.ModalBody([
                            html.Div("Zoom", className="mb-1 small text-muted"),
                            dcc.Slider(id="zoom-img_hidro", min=0.5, max=3, step=0.1, value=1),

                            # Contenedor con scroll para la imagen ampliada
                            html.Div(
                                id="img-zoom-wrappe_hidro",
                                style={"overflow": "auto", "border": "1px solid #eee", "height": "70vh", "marginTop": "0.5rem"},
                                children=html.Img(id="imagen_balance_modal_hidro", style={"width": "100%", "height": "auto"})
                            ),
                        ]),
                        dbc.ModalFooter(
                            dbc.Button("Cerrar", id="close-modal-img_hidro", className="ms-auto")
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
                    id="data_hcas2_hidro",
                    columnDefs=columnsDefs_hist_caso,
                    className='ag-theme-balham',
                    style={"height": "380px", "width": "100%"},
                )
            ])
        ], className="mb-4 shadow-sm border-0"),
    ])


def register_recon_callbacks_hidro(app):

    # ==============================================================================
    # CALLBACK #1: CARGAR CASOS Y SINCRONIZAR EL STORE (FUNCIÓN UNIFICADA)
    # ==============================================================================
    @app.callback(
        Output('data_casos2_hidro', 'rowData'),
        Output('data_hcas2_hidro', 'rowData'),
        Output('id_caso_activo_hidro', 'value'),
        Output('active-case_hidro', 'data'),
        Input('btn-get-casos_hidro', 'n_clicks'),
        Input('id_caso_activo_hidro', 'value'), # <--- AÑADIMOS EL INPUT DEL OTRO CALLBACK
        State('fecha_inicio_caso_hidro', 'value'),
        State('fecha_final_caso_hidro', 'value'),
        State('crea-caso_hidro', 'value'),
        State('recon-data_hidro', 'data'), # <--- Añadimos el State para no perder datos
        prevent_initial_call=True,
    )
    def manejar_casos_y_store(n_clicks, caso_id_manual, inicio, final, crea_caso, shared_data):
        # --- Disparador del callback ---
        triggered_id = ctx.triggered_id

        # --- Normalización estricta del Store del caso activo ---
        # 1) shared_data debe ser SIEMPRE un dict
        if not isinstance(shared_data, dict):
            # Si por error llega una lista de dicts, toma el primero; en otro caso, dict vacío
            if isinstance(shared_data, list) and shared_data and isinstance(shared_data[0], dict):
                shared_data = dict(shared_data[0])  # copia defensiva
            else:
                shared_data = {}

        # 2) Normalizar el flag del checkbox/Select para "crear caso"
        #    Tu UI a veces entrega ['Si'] o ['No']; volvemos a 'Si'/'No'
        if isinstance(crea_caso, (list, tuple)) and crea_caso:
            crea_flag = 'Si' if (crea_caso[0] == 'Si') else 'No'
        elif isinstance(crea_caso, str):
            crea_flag = 'Si' if (crea_caso == 'Si') else 'No'
        else:
            crea_flag = 'No'

        # --- 1) Botón "Obtener Datos" ---
        if triggered_id == 'btn-get-casos_hidro':
            # Consultas a BD
            df_caso = get_data_agua_casos(inicio, final, crea_flag)
            df_hist = get_agua_his_casos(final)

            caso_id_calculado = None
            if df_caso is not None and not df_caso.empty:
                # Asegurar entero
                try:
                    caso_id_calculado = int(df_caso['caso_id'].max())
                except Exception:
                    caso_id_calculado = None

            # Preparar store de caso activo (dict)
            new_shared_data = {
                "caso_id": caso_id_calculado,
                "fecha_inicio": inicio,
                "fecha_fin": final
            }

            return (
                (df_caso.round(4).to_dict('records') if df_caso is not None else []),
                (df_hist.round(4).to_dict('records') if df_hist is not None else []),
                caso_id_calculado,
                new_shared_data
            )

        # --- 2) Cambio manual del ID de caso ---
        if triggered_id == 'id_caso_activo_hidro':
            # Ignorar vacíos/None
            if caso_id_manual in (None, '', ' '):
                return no_update, no_update, no_update, no_update

            # Tipar a entero de forma segura
            try:
                caso_id_manual_int = int(caso_id_manual)
            except Exception:
                # Si no es convertible a int, no tocar nada
                return no_update, no_update, no_update, no_update

            # Actualizar SOLO el store, sin tocar las tablas
            shared_data["caso_id"] = caso_id_manual_int
            # (Si quieres conservar también fechas previas en shared_data, no las borres)
            return no_update, no_update, no_update, shared_data

        # --- 3) Ningún disparador relevante: no hacer nada ---
        return no_update, no_update, no_update, no_update


    # ==============================================================================
    # CALLBACK #2: GUARDAR EDICIÓN DEL CASO ACTIVO (SIN CAMBIOS)
    # ==============================================================================
    @app.callback(
        Output('btn-sim-msg_caso_hidro', 'children'),
        Input('btn-save-casos_hidro', 'n_clicks'),
        State('data_casos2_hidro', 'rowData'),
        State('fecha_final_caso_hidro', 'value'),
        State('id_caso_activo_hidro', 'value'),
        prevent_initial_call=True,
    )
    def guardar_caso_hidro(n_clicks, data_rows, fecha_final, caso_id):
        if not n_clicks or ctx.triggered_id != 'btn-save-casos_hidro':
            return no_update

        try:
            get_data_save_casos(data_rows or [], fecha_final, caso_id)
            return "✅ Datos guardados"
        except Exception as e:
            return f"❌ Error al guardar: {e}"

    # Actualizar imagen según selección e id caso activo
    @app.callback(
        Output('imagen_balance_hidro', 'src'),
        Input('agg-tab2_hidro', 'value'),
        Input('id_caso_activo_hidro', 'value'),
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
        Output("modal-img_hidro", "is_open"),
        Output("imagen_balance_modal_hidro", "src"),
        Input("btn-full-img_hidro", "n_clicks"),
        Input("close-modal-img_hidro", "n_clicks"),
        State("modal-img_hidro", "is_open"),
        State("imagen_balance_hidro", "src"),
        prevent_initial_call=True
    )
    def toggle_modal(n_open, n_close, is_open, src):
        if ctx.triggered_id == "btn-full-img_hidro":
            # también actualizamos el href del link "Abrir en nueva pestaña"
            return True, src
        if ctx.triggered_id == "close-modal-img_hidro":
            return False, no_update
        return is_open, no_update

    # Slider de zoom (simple: cambia el ancho relativo)
    @app.callback(
        Output("imagen_balance_modal_hidro", "style"),
        Input("zoom-img_hidro", "value")
    )
    def zoom_image(zoom):
        zoom = zoom or 1
        return {"width": f"{int(zoom*100)}%", "height": "auto"}