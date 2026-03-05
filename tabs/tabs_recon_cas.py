# tabs_recon_cas.py
import json
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
import urllib
import time

# Utils propios
from tabs.utils_dash import (
    get_fig_bal_casos,        # devuelve src para <img> (base64/data-url o ruta servible)
    get_agua_his_casos,       # histórico
    get_data_agua_casos,      # caso activo
    get_data_save_casos,
    get_info_caso_html,       # para flowsheet
)

# ====== Ajuste reporte (DEBUG) ======
# OJO: ajusta este import si tu estructura es distinta.
try:
    from ajuste_reporte.rep_prod_adjuster import run_ajuste_reporte_prod
except Exception as _e:
    run_ajuste_reporte_prod = None


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
                            html.Small(id='btn-sim-msg_caso', className='text-muted', children=' '),

                            # ===== NUEVO BOTÓN DEBUG =====
                            dbc.Button(
                                [html.I(className="bi bi-gear-wide-connected me-2"), "Ajustar Reporte (debug)"],
                                id='btn-ajustar-reporte', n_clicks=0,
                                color="warning", outline=False, className="w-100"
                            ),
                            dcc.Loading(
                                html.Div(
                                    id='btn-ajustar-msg',
                                    className="small text-muted",
                                    children=" "
                                ),
                                type="default"
                            ),
                            # =============================
                        ], gap=2)
                    ], md=3),
                ], className="gy-2"),
            ])
        ], className="mb-4 shadow-sm border-0"),

        # --- Visualización ---
        dbc.Card([
            dbc.CardHeader(html.H5("Visualización", className="mb-0")),
            dbc.CardBody([
                html.Div(className="my-3"),
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            html.Iframe(
                                id="flowsheet-iframe",
                                src="/assets/ripios.html",
                                style={
                                    "width": "100%",
                                    "height": "80vh",
                                    "border": "none",
                                    "overflow": "hidden"
                                }
                            ),
                            type="default"
                        ),
                        html.Div(id="dummy-div", style={"display": "none"}),
                    ], md=12),
                ]),
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


def register_recon_callbacks(app):

    # ==============================================================================
    # CALLBACK #1: CARGAR CASOS Y SINCRONIZAR EL STORE (FUNCIÓN UNIFICADA)
    # ==============================================================================
    @app.callback(
        Output('data_casos2', 'rowData'),
        Output('data_hcas2', 'rowData'),
        Output('id_caso_activo', 'value'),
        Output('active-case', 'data'),
        Input('btn-get-casos', 'n_clicks'),
        Input('id_caso_activo', 'value'),
        State('fecha_inicio_caso', 'value'),
        State('fecha_final_caso', 'value'),
        State('crea-caso', 'value'),
        State('recon-data', 'data'),
        prevent_initial_call=True,
    )
    def manejar_casos_y_store(n_clicks, caso_id_manual, inicio, final, crea_caso, shared_data):
        triggered_id = ctx.triggered_id
        print(f"caso id manual: {caso_id_manual}, triggered by: {triggered_id}")

        # Normalización estricta del Store del caso activo
        if not isinstance(shared_data, dict):
            if isinstance(shared_data, list) and shared_data and isinstance(shared_data[0], dict):
                shared_data = dict(shared_data[0])
            else:
                shared_data = {}

        # Normalizar flag crear caso
        if isinstance(crea_caso, (list, tuple)) and crea_caso:
            crea_flag = 'Si' if (crea_caso[0] == 'Si') else 'No'
        elif isinstance(crea_caso, str):
            crea_flag = 'Si' if (crea_caso == 'Si') else 'No'
        else:
            crea_flag = 'No'

        # Botón "Obtener Datos"
        if triggered_id == 'btn-get-casos':
            df_hist = get_agua_his_casos(final)

            if caso_id_manual:
                crea_flag = 'No'
                df_caso_aux = df_hist.loc[df_hist['caso_id'] == caso_id_manual]
                print(f"df_caso_aux: {df_caso_aux}")
                final = df_caso_aux['fecha'].values[0]
                inicio = df_caso_aux['fecha_ini'].values[0]

            df_caso = get_data_agua_casos(inicio, final, crea_flag)

            caso_id_calculado = caso_id_manual
            if df_caso is not None and not df_caso.empty:
                try:
                    caso_id_calculado = int(df_caso['caso_id'].max())
                except Exception:
                    caso_id_calculado = None

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

        # Cambio manual del ID de caso
        if triggered_id == 'id_caso_activo':
            if caso_id_manual in (None, '', ' '):
                return no_update, no_update, no_update, no_update

            try:
                caso_id_manual_int = int(caso_id_manual)
            except Exception:
                return no_update, no_update, no_update, no_update

            shared_data["caso_id"] = caso_id_manual_int
            return no_update, no_update, no_update, shared_data

        return no_update, no_update, no_update, no_update


    # ==============================================================================
    # CALLBACK #2: GUARDAR EDICIÓN DEL CASO ACTIVO (SIN CAMBIOS)
    # ==============================================================================
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
            return no_update

        try:
            get_data_save_casos(data_rows or [], fecha_final, caso_id)
            return "✅ Datos guardados"
        except Exception as e:
            return f"❌ Error al guardar: {e}"


    # ==============================================================================
    # CALLBACK #3: ACTUALIZAR FLOWSHEET SEGÚN CASO
    # ==============================================================================
    @app.callback(
        Output('flowsheet-iframe', 'src'),
        Input("id_caso_activo", "value"),
        prevent_initial_call=True,
    )
    def actualizar_flowsheet(caso_id):
        if not caso_id:
            return no_update

        try:
            info = get_info_caso_html(caso_id)
            flows = info["flowData"]
            nodes = info["nodeData"]

            flow_json_str = json.dumps(flows)
            node_json_str = json.dumps(nodes)

            flow_encoded = urllib.parse.quote(flow_json_str, safe='')
            node_encoded = urllib.parse.quote(node_json_str, safe='')
            metric_encoded = urllib.parse.quote("TMS")

            html_file = "/assets/ripios.html"
            cache_buster = f"?v={time.time()}"

            new_src = (
                f"{html_file}{cache_buster}"
                f"#flowData={flow_encoded}"
                f"&nodeData={node_encoded}"
                f"&metric={metric_encoded}"
            )

            print("Updated iframe src:", new_src)
            return new_src

        except Exception as e:
            print("❌ ERROR en actualizar_flowsheet:", e)
            return no_update


    # ==============================================================================
    # CALLBACK #4 (NUEVO): AJUSTAR REPORTE (DEBUG)
    # ==============================================================================
    @app.callback(
        Output("btn-ajustar-msg", "children"),
        Input("btn-ajustar-reporte", "n_clicks"),
        State("id_caso_activo", "value"),
        prevent_initial_call=True,
    )
    def ajustar_reporte_debug(n_clicks, caso_id):
        if not n_clicks or ctx.triggered_id != "btn-ajustar-reporte":
            return no_update

        if not caso_id:
            return "⚠️ Selecciona un caso (id_caso_activo) antes de ajustar."

        if run_ajuste_reporte_prod is None:
            return "❌ No se pudo importar run_ajuste_reporte_prod. Revisa: ajuste_reporte/rep_prod_adjuster.py"

        try:
            t0 = time.time()
            res = run_ajuste_reporte_prod(int(caso_id))
            dt_s = round(time.time() - t0, 2)

            # res esperado: {"ok": True, "run_id": "...", "totales": {...}}
            if isinstance(res, dict) and res.get("ok"):
                run_id = res.get("run_id", "-")
                tot = res.get("totales", {}) or {}
                sum_ch = tot.get("sum_chancado", None)
                sum_sal = tot.get("sum_sal", None)
                sum_fi = tot.get("sum_finos", None)

                return (
                    f"✅ Ajuste OK | caso={caso_id} | run_id={run_id} | "
                    f"t={dt_s}s | ΣCh={sum_ch} | ΣSal={sum_sal} | ΣFinos={sum_fi}"
                )

            return f"⚠️ Ajuste ejecutado, pero respuesta no esperada: {res}"

        except Exception as e:
            return f"❌ Error ajuste reporte (caso {caso_id}): {e}"