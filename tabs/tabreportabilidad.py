# tabs/tab_reporte.py

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from .Exportarexcel import exportar_excel_desbalance
from .utils_recon import balance_core
from .utils_dash import get_data_publica_casos
import dash_ag_grid as dag
import numpy as np
import io

dict_style_boton_2 = {
    'background': '#C0E48C', 'color': 'black', 'border-color': '#7EB72B',
    'border-radius': '10px',
    'width': '100%',
    'fontSize': 10,
    'height': '40px',
    'textAlign': 'center'
}

# === ColumnDefs requeridos para AgGrid (import desde Tab6 con fallback local) ===
try:
    # Ajusta la ruta si tu paquete/tabs tiene otro nombre
    from tabs.tab6 import columnsDefs_resultados, columnsDefs_desbalances
except Exception:
    # Fallback mínimo por si no se puede importar desde tab6
    columnsDefs_resultados = [
        {"headerName": "Flujo", "field": "Flujo"},
        {"headerName": "Masa Reconciliada (t)", "field": "Masa Reconciliada", "type": "rightAligned"},
        {"headerName": "Ley Cu Reconciliada (frac)", "field": "Ley_Cu_Reconciliada", "type": "rightAligned"},
        {"headerName": "Masa Medida (t)", "field": "Masa Medida", "type": "rightAligned"},
        {"headerName": "Ley Cu Medida (frac)", "field": "Cu", "type": "rightAligned"},
        {"headerName": "Código", "field": "Codigo"},
        {"headerName": "id_flujo", "field": "id_flujo"},
    ]
    columnsDefs_desbalances = [
        {"headerName": "Área", "field": "Area"},
        {"headerName": "Desbalance masa_Ini", "field": "Desbalance masa_Ini", "type": "rightAligned"},
        {"headerName": "Desbalance masa (Recon)", "field": "Desbalance masa", "type": "rightAligned"},
        {"headerName": "Desbalance fino Cu (Recon)", "field": "Desbalance fino Cu", "type": "rightAligned"},
    ]

from tabs.Exportarexcel import exportar_excel_desbalance

# ----- Rutas base -----
# Este archivo vive en app/tabs/, por eso parents[1] apunta a la carpeta app/
BASE_DIR = Path(__file__).resolve().parents[1]

# TEMPLATE CORREGIDO: el archivo base está en 'app/Desbalance Formato Base.xlsx'
TEMPLATE_XLSX = str(BASE_DIR / "Desbalance Formato Base.xlsx")

# Carpeta de salida (se crea automáticamente si no existe)
OUTPUT_DIR = BASE_DIR / "Desbalances"

# 1) LAYOUT (vista)
def render_layout_reporte():
    return html.Div([
        # Componente de descarga (si usas exportación adicional)
        dcc.Download(id="dl-reporte-caso"),

        # ——————————————————————  SECCIÓN: RECONCILIADOR (arriba)  ——————————————————————
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 2: Reconciliador", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f8f9fa",
                       "letterSpacing": "0.06em", "textTransform": "uppercase"}
            ),
            dbc.CardBody([
                # Barra de acciones
                dbc.Row([
                    dbc.Col([
                        html.H5('Ejecutar reconciliador y revisión de resultados', className="mb-0")
                    ], width=8),
                    dbc.Col([
                        dbc.Button('Ejecutar', id='btn-recon', n_clicks=0,
                                   style=dict_style_boton_2, className="me-2"),
                        dbc.Button('Publicar Datos', id='btn-publica-casos', n_clicks=0,
                                   style=dict_style_boton_2, className="me-2"),
                        dbc.Button('Descargar', id='btn-recon-csv', n_clicks=0,
                                   style=dict_style_boton_2),
                        dcc.Download(id="descargar-excel"),
                        html.Div(id='btn-recon-msg', style={'fontSize': 12}, className="mt-1"),
                        html.Div(id='btn-pub-msg_caso', style={'fontSize': 12})
                    ], width=4, className="text-end")
                ], className="align-items-center mb-3"),

                # Tabla de resultados
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dag.AgGrid(
                                id="recon-resultados",
                                columnDefs=columnsDefs_resultados,
                                className='ag-theme-balham',
                                style={"width": "100%"},
                                csvExportParams={"fileName": "resultados_reconciliados.csv"},
                                defaultColDef={
                                    "sortable": True, "filter": True, "resizable": True, "minWidth": 90
                                },
                                dashGridOptions={
                                    "rowHeight": 28, "headerHeight": 28, "animateRows": False,
                                    "suppressMenuHide": True, "ensureDomOrder": True,
                                    "alwaysShowHorizontalScroll": True
                                }
                            ),
                            type="default"
                        )
                    ], width=12)
                ], className="mb-3"),

                # Tabla de desbalances
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dag.AgGrid(
                                id="recon-desbalances",
                                columnDefs=columnsDefs_desbalances,
                                className='ag-theme-balham',
                                style={"width": "100%"},
                                defaultColDef={
                                    "sortable": True, "filter": True, "resizable": True, "minWidth": 90
                                },
                                dashGridOptions={
                                    "rowHeight": 28, "headerHeight": 28, "animateRows": False,
                                    "suppressMenuHide": True, "ensureDomOrder": True,
                                    "alwaysShowHorizontalScroll": True
                                }
                            ),
                            type="default"
                        )
                    ], width=12)
                ])
            ], className="pt-3 pb-2")
        ], className="mb-3 shadow-sm border-0"),

        # ——————————————————————  SECCIÓN: REPORTE (debajo)  ——————————————————————
        dbc.Card(
            dbc.CardBody([
                html.H4("Módulo de Reportabilidad", className="mb-3"),
                dbc.Row([
                    # Columna 1: Controles e información del caso
                    dbc.Col([
                        html.P(
                            "El reporte se generará para el caso activo seleccionado en la pestaña 'Administrar casos'.",
                            className="text-muted"
                        ),

                        # Caso activo
                        dbc.Alert(
                            "No hay ningún caso activo seleccionado.",
                            id="display-active-case-reporte",
                            color="info",
                            className="mt-3"
                        ),

                        # Botón para generar contenido en pantalla
                        dbc.Button(
                            "Generar Reporte del Caso Activo",
                            id="btn-generar-reporte-final",
                            color="primary",
                            className="mt-3 w-100",
                            disabled=True
                        ),

                        # Botón para exportar el Excel (template)
                        dbc.Button(
                            "Exportar Excel (Desbalance)",
                            id="btn-export-excel",
                            color="secondary",
                            className="mt-2 w-100",
                            disabled=True
                        ),
                    ], md=4),

                    # Columna 2: Contenido del reporte en pantalla
                    dbc.Col([
                        dcc.Loading(
                            html.Div(id="contenido-del-reporte")
                        )
                    ], md=8),
                ]),
            ]),
            className="shadow-sm border-0"
        )
    ], className="pt-3")

# 2) CALLBACKS (lógica)
def register_callbacks_reporte(app):

    # ==============================================================================
    # CALLBACK #2: EJECUTAR RECONCILIACIÓN
    # ==============================================================================
    @callback(
    Output('recon-resultados','rowData'),
    Output('recon-desbalances','rowData'),
    Input('btn-recon','n_clicks'),
    State('recon-data','data'),               # ← datos persistidos
    State('active-case','data'),              # ← caso activo unificado
    prevent_initial_call=True
)
    def get_recon(n_clicks, data_base, active_case):
        if not n_clicks:
            return [], []
        if not data_base:
            return [], []

        try:
            # 1) Base desde la grilla
            dfb = pd.DataFrame(data_base)

            # 2) Normalización numérica
            dfb['id_flujo'] = pd.to_numeric(dfb.get('id_flujo', np.arange(1, len(dfb)+1)), errors='coerce')
            dfb.sort_values('id_flujo', inplace=True)

            dfb['Flujo'] = pd.to_numeric(dfb.get('Flujo', 0), errors='coerce').fillna(0.0)
            dfb['Cu']    = pd.to_numeric(dfb.get('Cu', 0),    errors='coerce').fillna(0.0)

            dfb['Tolerancia']    = pd.to_numeric(dfb.get('Tolerancia', 0),    errors='coerce').fillna(0.0)
            dfb['Tolerancia_cu'] = pd.to_numeric(dfb.get('Tolerancia_cu', 0), errors='coerce').fillna(0.0)

            # 3) Mediciones: matriz Nx2 => [Tonelaje, Ley_Cu (fracción)]
            mediciones = np.column_stack([
                dfb['Flujo'].to_numpy(dtype=float),
                (dfb['Cu'] / 100.0).to_numpy(dtype=float),
            ])

            # 4) Matriz de errores relativa Nx2 (masa, ley Cu), en fracción
            eps = 1e-6  # evita divisiones por cero si usuario deja 0.0
            error_df = pd.DataFrame({
                0: (dfb['Tolerancia']    / 100.0).replace(0.0, eps).to_numpy(dtype=float),
                1: (dfb['Tolerancia_cu'] / 100.0).replace(0.0, eps).to_numpy(dtype=float),
            })

            # 5) Reconciliar
            resultados, des_recon, des_ini = balance_core(mediciones, error=error_df, fn="Normal")

            # 6) Desbalances (igual que tu versión estable)
            des_ini.rename(columns={0: 'Area', 'Desbalance masa': 'Desbalance masa_Ini'}, inplace=True)
            des_recon.rename(columns={0: 'Area'}, inplace=True)
            df_des = des_ini.merge(des_recon, how='left', on='Area')

            # 7) Consolidar con datos iniciales (medida vs recon)
            df_med_all = dfb.copy()
            df_med_all.rename(columns={'Flujo': 'Masa Medida', 'nombre_flujo': 'Flujo', 'codigo_flujo': 'Codigo'}, inplace=True)
            df_out = resultados.merge(df_med_all, how='left', on='Flujo')

            return df_out.round(4).to_dict('records'), df_des.round(4).to_dict('records')

        except Exception as e:
            print(f"❌ Error durante la reconciliación final: {e}")
            return [], []

    # ==============================================================================
    # CALLBACK #3: PUBLICAR DATOS
    # ==============================================================================
    @app.callback(
        Output('btn-pub-msg_caso', 'children'),
        Input('btn-publica-casos', 'n_clicks'),
        State('recon-resultados', 'rowData'),
        State('active-case', 'data'),
        prevent_initial_call=True
    )
    def get_publica_casos(n_clicks, rec_caso, shared):
        if not n_clicks:
            return no_update
        try:
            # Asumo que get_data_publica_casos no necesita med_cas
            nrows = get_data_publica_casos(rec_caso, shared) 
            return f"✅ Publicado correctamente ({nrows} filas)."
        except Exception as e:
            return f"❌ Error al publicar: {e}"

    # ==============================================================================
    # CALLBACK #4: DESCARGAR
    # ==============================================================================
    @app.callback(
        Output("descargar-excel", "data"),
        Input("btn-recon-csv", "n_clicks"),
        State("recon-resultados", "rowData"),
        prevent_initial_call=True
    )
    def generar_excel(n_clicks, rec_caso):
        if not rec_caso:
            return False
        df_rec = pd.DataFrame(rec_caso)
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_rec.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)
        return dcc.send_bytes(buffer.read(), filename="reconciliacion.xlsx")

    # CALLBACK 1: Mostrar caso activo y habilitar "Generar Reporte"
    @app.callback(
        Output('display-active-case-reporte', 'children'),
        Output('btn-generar-reporte-final', 'disabled'),
        Input('active-case', 'data')
    )
    def actualizar_info_caso_activo(shared_data):
        if isinstance(shared_data, dict) and shared_data.get('caso_id'):
            return f"✅ Caso Activo ID: {shared_data['caso_id']}", False
        return "❌ No hay ningún caso activo seleccionado.", True
    # CALLBACK 1b: Habilitar/Deshabilitar botón de exportación según caso activo
    @app.callback(
        Output('btn-export-excel', 'disabled'),
        Input('active-case', 'data'),
    )
    def habilitar_export(shared_data):
        if isinstance(shared_data, dict) and shared_data.get('caso_id'):
            return False  # habilitar botón
        return True 

    # CALLBACK 2: Generar contenido del reporte (en pantalla)
    @app.callback(
        Output('contenido-del-reporte', 'children'),
        Input('btn-generar-reporte-final', 'n_clicks'),
        State('active-case', 'data'),
        prevent_initial_call=True
    )
    def generar_reporte_del_caso(n_clicks, shared_data):
        if not n_clicks:
            return ""

        caso_id_activo = (shared_data or {}).get('caso_id')
        if not caso_id_activo:
            return dbc.Alert("Error: No se encontró un caso activo.", color="danger")

        # Ejemplo mínimo para visualizar (sustituir por tu consulta real si corresponde)
        datos_reporte_ficticio = {
            'Flujo': ['Alimentación', 'Concentrado', 'Relave'],
            'Masa Reconciliada (t)': [1000, 150, 850],
            'Ley Cu Reconciliada (%)': [1.20, 5.80, 0.25]
        }
        df_reporte = pd.DataFrame(datos_reporte_ficticio)
        tabla = dbc.Table.from_dataframe(df_reporte, striped=True, bordered=True, hover=True, size="sm")

        return html.Div([
            html.H5(f"Reporte para el Caso ID: {caso_id_activo}"),
            tabla
        ])

    # CALLBACK 3: Exportar Excel usando el template y Data_balance_rec
    @app.callback(
        Output("dl-reporte-caso", "data"),
        Input("btn-export-excel", "n_clicks"),
        State("active-case", "data"),
        prevent_initial_call=True
    )
    def exportar_excel(n_clicks, shared_data):
        if not n_clicks:
            raise dash.exceptions.PreventUpdate
        if not shared_data or not shared_data.get("caso_id"):
            raise dash.exceptions.PreventUpdate

        caso_id = int(shared_data["caso_id"])

        # Asegurar carpeta de salida y construir ruta del archivo
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"Desbalance_caso_{caso_id}.xlsx"

        # Generar Excel a partir del template ubicado en app/Desbalance Formato Base.xlsx
        exportar_excel_desbalance(caso_id, TEMPLATE_XLSX, str(out_path))

        # Disparar descarga
        return dcc.send_file(str(out_path))
