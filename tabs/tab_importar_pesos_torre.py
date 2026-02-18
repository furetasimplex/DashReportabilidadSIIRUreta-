from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import base64
import datetime
import sys

try:
    from tabs.procesar_pesos_lab import procesar_bitacora_completa, guardar_bitacora_bd
except ImportError:
    sys.path.append(".")
    from tabs.procesar_pesos_lab import procesar_bitacora_completa, guardar_bitacora_bd

layout = html.Div([
    dbc.Card([
        dbc.CardHeader("Carga Bitácora Operacional (Novedades + Horarios)"),
        dbc.CardBody([
            dbc.Alert(
                "El sistema intentará detectar el mes desde el nombre del archivo. "
                "Si no lo logra, usará el selector de fecha manual.",
                color="info",
                className="mb-3",
                style={"fontSize": "0.9rem"}
            ),
            html.Div([
                html.Label("Corrección Manual de Mes (Opcional):", className="fw-bold"),
                dcc.DatePickerSingle(
                    id="date-picker-manual",
                    min_date_allowed=datetime.date(2020, 1, 1),
                    max_date_allowed=datetime.date(2030, 12, 31),
                    placeholder="Seleccionar solo si falla auto-detección",
                    display_format="MMMM YYYY",
                    style={"width": "100%"}
                ),
            ], className="mb-3"),

            dcc.Upload(
                id="upload-bitacora",
                children=html.Div(["Arrastra o ", html.A("Selecciona Archivo")]),
                style={
                    "width": "100%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center"
                },
                multiple=False
            ),

            html.Div(id="output-bitacora", className="mt-3")
        ])
    ])
])

@callback(
    Output("output-bitacora", "children"),
    Input("upload-bitacora", "contents"),
    State("upload-bitacora", "filename"),
    State("date-picker-manual", "date"),
    prevent_initial_call=True
)
def cargar_bitacora(contents, filename, fecha_manual_str):
    if not contents:
        return ""

    try:
        decoded = base64.b64decode(contents.split(",")[1])
    except Exception as e:
        return dbc.Alert(f"Error decodificando archivo: {e}", color="danger")

    fecha_manual = None
    if fecha_manual_str:
        try:
            fecha_manual = datetime.datetime.strptime(fecha_manual_str, "%Y-%m-%d")
        except Exception as e:
            return dbc.Alert(f"Fecha manual inválida: {e}", color="danger")

    try:
        df_final, msg = procesar_bitacora_completa(decoded, filename, fecha_manual)

        if df_final is None:
            return dbc.Alert(f"Error: {msg}", color="danger")

        exito, msg_db = guardar_bitacora_bd(df_final)
        color = "success" if exito else "danger"

        return dbc.Alert([
            html.H5("Resultado de Carga", className="alert-heading"),
            html.P(f"Detección: {msg}"),
            html.P(f"Base de Datos: {msg_db}"),
            html.Small(f"Archivo: {filename}")
        ], color=color)

    except Exception as e:
        return dbc.Alert(f"Error crítico: {e}", color="danger")
