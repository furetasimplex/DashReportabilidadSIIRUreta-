import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import pandas as pd

dash.register_page(__name__, path="/reportabilidad", name="Reportabilidad")

def layout():
    return html.Div([
        dbc.CardHeader(html.H4("📊 Módulo de Reportabilidad", className="p-2 mb-3")),

        # =======================
        # PARÁMETROS DE REPORTE
        # =======================
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

        # =======================
        # VISUALIZACIÓN
        # =======================
        dbc.Card([
            dbc.CardHeader("Visualización del Reporte"),
            dbc.CardBody([
                html.Div(id="report-grafico", className="mb-3"),
                html.Div(id="report-tabla")
            ])
        ], className="mb-4 shadow-sm"),

        # =======================
        # HISTORIAL / EXPORTACIÓN
        # =======================
        dbc.Card([
            dbc.CardHeader("Historial de Reportes"),
            dbc.CardBody([
                html.Div(id="report-historial"),
                dbc.ButtonGroup([
                    dbc.Button("📄 Exportar a Excel", color="success"),
                    dbc.Button("🖨️ Generar PDF", color="primary")
                ], className="mt-2")
            ])
        ], className="shadow-sm mb-4")
    ], className="p-3")


# =======================
# CALLBACKS
# =======================
def register_callbacks(app):

    @app.callback(
        [Output("report-grafico", "children"),
         Output("report-tabla", "children"),
         Output("report-historial", "children")],
        Input("report-btn-generar", "n_clicks"),
        Input("report-tipo-reporte", "value"),
        prevent_initial_call=True
    )
    def generar_reporte(n, tipo):
        # Simulación de dataset temporal
        df = pd.DataFrame({
            "Día": pd.date_range("2025-10-01", periods=7),
            "Producción (t)": [4500, 4800, 4700, 4900, 5100, 4950, 5050]
        })

        fig = px.line(df, x="Día", y="Producción (t)", markers=True, title="Producción Diaria")
        grafico = dcc.Graph(figure=fig)

        tabla = dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, className="mt-3")

        historial = dbc.Table(
            [
                html.Thead(html.Tr([html.Th("Fecha"), html.Th("Tipo"), html.Th("Usuario")]),
                           style={"backgroundColor": "#FEEBC8"}),
                html.Tbody([
                    html.Tr([html.Td("23-10-2025"), html.Td("Producción Diaria"), html.Td("CRamos")]),
                    html.Tr([html.Td("22-10-2025"), html.Td("Conciliación Mensual"), html.Td("MVera")]),
                ])
            ], bordered=True, hover=True
        )

        return grafico, tabla, historial
