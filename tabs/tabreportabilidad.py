# tabs/tab_reporte.py

import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path

# IMPORT CORREGIDO: si export_excel.py está dentro de la carpeta 'tabs'
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
        # Componente de descarga (obligatorio para dcc.send_file)
        dcc.Download(id="dl-reporte-caso"),

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
    ])


# 2) CALLBACKS (lógica)
def register_callbacks_reporte(app):

    # CALLBACK 1: Mostrar caso activo y habilitar "Generar Reporte"
    @app.callback(
        Output('display-active-case-reporte', 'children'),
        Output('btn-generar-reporte-final', 'disabled'),
        Input('recon-shared', 'data')
    )
    def actualizar_info_caso_activo(shared_data):
        if shared_data and shared_data.get('caso_id'):
            caso_id = shared_data.get('caso_id')
            mensaje = f"✅ Caso Activo ID: {caso_id}"
            return mensaje, False
        else:
            mensaje = "❌ No hay ningún caso activo seleccionado."
            return mensaje, True

    # CALLBACK 1b: Habilitar/Deshabilitar botón de exportación según caso activo
    @app.callback(
        Output('btn-export-excel', 'disabled'),
        Input('recon-shared', 'data'),
    )
    def habilitar_export(shared_data):
        return not (shared_data and shared_data.get('caso_id'))

    # CALLBACK 2: Generar contenido del reporte (en pantalla)
    @app.callback(
        Output('contenido-del-reporte', 'children'),
        Input('btn-generar-reporte-final', 'n_clicks'),
        State('recon-shared', 'data'),
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
        State("recon-shared", "data"),
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
