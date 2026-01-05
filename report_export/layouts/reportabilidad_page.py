# Auto-generated on 2025-10-27 18:21:09. Edit as needed.


import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

dash.register_page(__name__, path="/reportabilidad", name="Reportabilidad")

def layout():
    return html.Div([
        dbc.CardHeader(html.H4("📊 Módulo de Reportabilidad", className="p-2 mb-3")),

        dbc.Card([
            dbc.CardHeader("Parámetros de Reporte"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Fecha Inicio"),
                        dcc.DatePickerSingle(
                            id="report-fecha-inicio",
                            display_format="DD-MM-YYYY",
                            date=pd.Timestamp.now().normalize() - pd.Timedelta(days=7)
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Fecha Final"),
                        dcc.DatePickerSingle(
                            id="report-fecha-final",
                            display_format="DD-MM-YYYY",
                            date=pd.Timestamp.now().normalize()
                        ),
                    ], width=3),
                    dbc.Col([
                        dbc.Label("Tipo de Reporte"),
                        dcc.Dropdown(
                            id="report-tipo-reporte",
                            options=[
                                {"label": "Producción Diaria", "value": "prod"},
                                {"label": "Balance Semanal", "value": "balance"},
                                {"label": "Conciliación Mensual", "value": "conciliacion"},
                            ],
                            value="prod",
                            placeholder="Seleccione tipo..."
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Button("Generar Reporte", id="report-btn-generar", color="warning", className="mt-4 w-100")
                    ], width=2)
                ])
            ])
        ], className="mb-4 shadow-sm"),

        dbc.Card([
            dbc.CardHeader("Visualización del Reporte"),
            dbc.CardBody([
                html.Div(id="report-grafico", className="mb-3"),
                html.Div(id="report-tabla")
            ])
        ], className="mb-4 shadow-sm"),

        dbc.Card([
            dbc.CardHeader("Exportar Reportes"),
            dbc.CardBody([
                html.Div(id="report-historial"),
                dbc.ButtonGroup([
                    dbc.Button("📄 Exportar a Excel3", id="report-btn-exportar", color="success"),
                    dbc.Button("🖨️ Generar PDF", id="report-btn-pdf", color="primary", disabled=True)
                ], className="mt-2"),
                dcc.Download(id="report-download-xlsx"),
                html.Div(id="report-status", className="mt-2 text-muted")
            ])
        ], className="shadow-sm mb-4")
    ], className="p-3")
