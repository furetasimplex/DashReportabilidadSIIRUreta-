# tabs/tab_reporte.py

import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from tabs.tabReconHidro.utils.Exportarexcel import exportar_excel_desbalance
from tabs.tabReconHidro.utils.utils_recon import balance_core
from tabs.tabReconHidro.utils.utils_dash import get_data_publica_casos
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

# ==============================================================================
# 1. DEFINICIÓN DE ESTILOS Y COLUMNAS (Pegar esto ANTES de render_layout_reporte)
# ==============================================================================

fmt_masa = {"function": "d3.format(',.1f')(params.value)"}
fmt_ley = {"function": "d3.format('.3f')(params.value)"}
fmt_pct = {"function": "d3.format('.2f')(params.value) + '%'"}

# Estilos Condicionales (Semáforo)
estilo_error_critico = {
    "styleConditions": [
        {
            "condition": "params.value > 10 || params.value < -10",
            "style": {"backgroundColor": "#ffe6e6", "color": "#b30000", "fontWeight": "bold"} # Rojo suave
        },
        {
            "condition": "(params.value >= 5 && params.value <= 10) || (params.value <= -5 && params.value >= -10)",
            "style": {"backgroundColor": "#fff8e1", "color": "#b35900"} # Naranja suave
        }
    ]
}

# Definición de Columnas (Optimizada para legibilidad)
mis_columnas_pro = [
    {
        "headerName": "Identificación",
        "children": [
            # Pinned left: Esta columna se quedará fija al hacer scroll horizontal
            {"headerName": "Flujo", "field": "Flujo", "width": 130, "pinned": "left", "cellStyle": {"fontWeight": "600", "backgroundColor": "#f8f9fa"}},
            {"headerName": "Cod", "field": "Codigo", "width": 80},
        ]
    },
    {
        "headerName": "Balance de Masa (Ton)",
        "children": [
            {"headerName": "Medida", "field": "Masa medida", "valueFormatter": fmt_masa, "type": "rightAligned", "width": 110},
            {"headerName": "Reconciliada", "field": "Masa recon", "valueFormatter": fmt_masa, "type": "rightAligned", "width": 110, "cellStyle": {"backgroundColor": "#fcfcfc", "color": "#004085"}},
            {"headerName": "Error %", "field": "Error masa", "valueFormatter": fmt_pct, "type": "rightAligned", "width": 90, "cellStyle": estilo_error_critico},
        ]
    },
    {
        "headerName": "Balance de Leyes Cu (%)",
        "children": [
            {"headerName": "Medida", "field": "Ley medida Cu", "valueFormatter": fmt_ley, "type": "rightAligned", "width": 90},
            {"headerName": "Reconciliada", "field": "Ley recon Cu", "valueFormatter": fmt_ley, "type": "rightAligned", "width": 90, "cellStyle": {"backgroundColor": "#fcfcfc", "color": "#004085"}},
            {"headerName": "Error %", "field": "Error ley Cu", "valueFormatter": fmt_pct, "type": "rightAligned", "width": 90, "cellStyle": estilo_error_critico},
        ]
    }
]

# ==============================================================================
# 2. LAYOUT CORREGIDO (Contenedor Controlado)
# ==============================================================================
def render_layout_reporte():
    return html.Div([
        dcc.Download(id="dl-reporte-caso-hidro"),

        # ——————————————————————  SECCIÓN: RECONCILIADOR  ——————————————————————
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 3: Reconciliador", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f1f3f5", "borderBottom": "1px solid #dcdcdc"}
            ),
            dbc.CardBody([
                # Barra de acciones
                dbc.Row([
                    dbc.Col([
                        html.H5('Ejecutar reconciliador Area Hidro y revisión de resultados', className="mb-0 text-dark", style={"fontSize": "1.1rem"})
                    ], width=7),
                    dbc.Col([
                        dbc.Stack([
                            dbc.Button('Ejecutar', id='btn-recon', n_clicks=0, color="success", size="sm", className="px-3 fw-bold"),
                            dbc.Button('Publicar Datos', id='btn-publica-casos', n_clicks=0, color="warning", size="sm", className="px-3 fw-bold text-white"),
                            dbc.Button('Descargar CSV', id='btn-recon-csv', n_clicks=0, color="light", size="sm", className="px-3 border"),
                            dcc.Download(id="descargar-excel-hidro"),
                        ], direction="horizontal", gap=2, className="justify-content-end"),
                        html.Div(id='btn-recon-msg', style={'fontSize': 11}, className="mt-1 text-end text-muted"),
                        html.Div(id='btn-pub-msg_caso-hidro', style={'fontSize': 11}, className="text-end")
                    ], width=5)
                ], className="align-items-center mb-3"),

                # TABLA DE RESULTADOS (EN DIV CONTROLADO)
                # TABLA DE RESULTADOS (EN DIV CONTROLADO)
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            html.Div(
                                style={
                                    "height": "55vh",
                                    "width": "100%",
                                    "maxWidth": "100%",
                                    "overflowX": "auto",     # scroll horizontal interno
                                    "overflowY": "auto",
                                    "borderRadius": "4px",
                                    "border": "1px solid #e0e0e0",
                                },
                                children=[
                                    dag.AgGrid(
                                        id="recon-resultados-hidro",
                                        columnDefs=mis_columnas_pro,
                                        className="ag-theme-alpine custom-grid",

                                        # El grid define su ANCHO NATURAL
                                        # y el scroll queda dentro del contenedor
                                        style={
                                            "height": "100%",
                                            "width": "max-content",
                                        },

                                        csvExportParams={"fileName": "resultados_reconciliados.csv"},

                                        defaultColDef={
                                            "sortable": True,
                                            "filter": True,
                                            "resizable": True,
                                            "minWidth": 120,
                                        },

                                        dashGridOptions={
                                            "rowHeight": 32,
                                            "headerHeight": 35,
                                            "animateRows": False,
                                            "domLayout": "normal",
                                            "ensureDomOrder": True,
                                            "enableCellTextSelection": True,
                                        },
                                    )
                                ]
                            ),
                            type="dot",
                            color="#6c757d",
                        )
                    ], width=12),
                ], className="mb-4"),


                # Tabla de desbalances (Más pequeña)
                dbc.Row([
                    dbc.Col([
                        html.H6("Resumen de Desbalances", className="mb-2 text-secondary", style={"fontSize": "0.9rem"}),
                        dcc.Loading(
                            html.Div(
                                style={"height": "200px", "width": "100%", "border": "1px solid #e0e0e0"},
                                children=dag.AgGrid(
                                    id="recon-desbalances-hidro",
                                    columnDefs=columnsDefs_desbalances,
                                    className='ag-theme-balham',
                                    style={"height": "100%", "width": "100%"},
                                    defaultColDef={"sortable": True, "filter": True, "resizable": True},
                                    dashGridOptions={"rowHeight": 28}
                                )
                            ),
                            type="dot", color="#6c757d"
                        )
                    ], width=12)
                ])
            ], className="pt-3 pb-3 px-3")
        ], className="mb-4 shadow-sm border-0"),

        # ——————————————————————  SECCIÓN: REPORTE  ——————————————————————
        dbc.Card(
            dbc.CardBody([
                html.H4("Módulo de Reportabilidad", className="mb-3 text-dark"),
                dbc.Row([
                    dbc.Col([
                        dbc.Alert("Seleccione un caso activo para generar reporte.", id="display-active-case-hidro-reporte", color="light", className="py-2 small border"),
                        dbc.Button("Generar Reporte", id="btn-generar-reporte-final-hidro", color="primary", size="sm", className="mt-2 w-100", disabled=True),
                        dbc.Button("Exportar Excel", id="btn-export-excel-hidro", color="secondary", outline=True, size="sm", className="mt-2 w-100", disabled=True),
                    ], md=3),
                    dbc.Col([
                        dcc.Loading(html.Div(id="contenido-del-reporte-hidro"))
                    ], md=9),
                ]),
            ]),
            className="shadow-sm border-0"
        )
    ], className="container-fluid py-3")

# 2) CALLBACKS (lógica)
def register_callbacks_reporte(app):

    # ==============================================================================
    # CALLBACK #2: EJECUTAR RECONCILIACIÓN
    # ==============================================================================
    @callback(
    Output('recon-resultados-hidro','rowData'),
    Output('recon-desbalances-hidro','rowData'),
    Input('btn-recon','n_clicks'),
    State('recon-data-hidro','data'),               # ← datos persistidos
    State('active-case-hidro','data'),              # ← caso activo unificado
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
    Output('btn-pub-msg_caso-hidro', 'children'),
    Input('btn-publica-casos', 'n_clicks'),
    State('recon-data-hidro', 'data'),         # <-- 1. AÑADIMOS ESTE STATE
    State('recon-resultados-hidro', 'rowData'),
    State('active-case-hidro', 'data'),
    prevent_initial_call=True
    )
    def get_publica_casos(n_clicks, med_cas, rec_caso, shared): # <-- 2. AÑADIMOS EL ARGUMENTO
        if not n_clicks:
            return no_update
        if not rec_caso:
            return "⚠️ No hay datos reconciliados para publicar."

        try:
            # 3. LLAMAMOS A LA FUNCIÓN CON LOS TRES ARGUMENTOS
            nrows = get_data_publica_casos(med_cas, rec_caso, shared) 
            return f"✅ Publicado correctamente ({nrows} filas)."
        except Exception as e:
            return f"❌ Error al publicar: {e}"

    # ==============================================================================
    # CALLBACK #4: DESCARGAR
    # ==============================================================================
    @app.callback(
        Output("descargar-excel-hidro", "data"),
        Input("btn-recon-csv", "n_clicks"),
        State("recon-resultados-hidro", "rowData"),
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
        Output('display-active-case-hidro-reporte', 'children'),
        Output('btn-generar-reporte-final-hidro', 'disabled'),
        Input('active-case-hidro', 'data')
    )
    def actualizar_info_caso_activo(shared_data):
        if isinstance(shared_data, dict) and shared_data.get('caso_id'):
            return f"✅ Caso Activo ID: {shared_data['caso_id']}", False
        return "❌ No hay ningún caso activo seleccionado.", True
    # CALLBACK 1b: Habilitar/Deshabilitar botón de exportación según caso activo
    @app.callback(
        Output('btn-export-excel-hidro', 'disabled'),
        Input('active-case-hidro', 'data'),
    )
    def habilitar_export(shared_data):
        if isinstance(shared_data, dict) and shared_data.get('caso_id'):
            return False  # habilitar botón
        return True 

    # CALLBACK 2: Generar contenido del reporte (en pantalla)
    @app.callback(
        Output('contenido-del-reporte-hidro', 'children'),
        Input('btn-generar-reporte-final-hidro', 'n_clicks'),
        State('active-case-hidro', 'data'),
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
        Output("dl-reporte-caso-hidro", "data"),
        Input("btn-export-excel-hidro", "n_clicks"),
        State("active-case-hidro", "data"),
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