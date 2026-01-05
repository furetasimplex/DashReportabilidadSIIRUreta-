# Auto-generated on 2025-10-27 18:21:09. Edit as needed.


from datetime import date
from dash import html, dcc
import dash_bootstrap_components as dbc

def layout():
    return dbc.Container([
        html.H4("Exportar Reporte Datos Conciliados (SQL Server → Excel)"),
        html.P("Selecciona la fecha hasta la cual incluir datos. El sistema toma automáticamente el día 1 del mes de esa fecha como inicio."),
        dbc.Row([
            dbc.Col([
                dbc.Label("Fecha hasta (inclusive)"),
                dcc.DatePickerSingle(
                    id="rep_fecha_hasta",
                    date=date.today(),
                    display_format="DD-MM-YYYY",
                    first_day_of_week=1,
                    clearable=False,
                ),
            ], md=4),
        ], className="gy-3"),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                dbc.Button("Generar y descargar Excel 2", id="rep_btn_exportar", n_clicks=0, color="primary"),
                dcc.Download(id="rep_descarga_xlsx"),
                html.Div(id="rep_status", className="mt-3 text-muted")
            ], md=6)
        ]),
        html.Hr(),
        html.Small("Nota: Las filas marcadas con * corresponden a información preliminar."),
    ], fluid=True)
