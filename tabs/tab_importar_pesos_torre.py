from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
import base64
import datetime
import sys
import traceback
try:
    from tabs.procesar_pesos_lab import (
        procesar_bitacora_completa,
        guardar_bitacora_bd,
        procesar_pesos_reales_torre,
        guardar_pesos_reales_bd
    )
except ImportError:
    sys.path.append(".")
    from tabs.procesar_pesos_lab import (
        procesar_bitacora_completa,
        guardar_bitacora_bd,
        procesar_pesos_reales_torre,
        guardar_pesos_reales_bd
    )
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
        # 1) Procesar bitácora
        df_final, msg = procesar_bitacora_completa(decoded, filename, fecha_manual)
        df_final, msg = procesar_bitacora_completa(decoded, filename, fecha_manual)

        if df_final is None:
            return dbc.Alert([
                html.H5("No se pudo procesar la bitácora", className="alert-heading"),
                html.P(msg),
                html.Hr(),
                html.P([html.Strong("Archivo: "), filename or "No disponible"]),
                html.Small(
                    "El archivo fue leído, pero no se pudo transformar al formato tabular "
                    "esperado por la base de datos."
                )
            ], color="danger")
        if df_final is None:
            return dbc.Alert(f"Error: {msg}", color="danger")

        columnas_esperadas = {
            "fecha_calendario",
            "fecha_turno",
            "torre",
            "turno",
            "ts_toma_muestra",
            "comentario",
            "nombre_archivo"
        }

        columnas_recibidas = set(df_final.columns)
        faltantes = columnas_esperadas - columnas_recibidas

        if faltantes:
            return dbc.Alert([
                html.H5("Error en estructura de bitácora"),
                html.P(f"Columnas faltantes: {faltantes}"),
                html.P(f"Columnas recibidas: {list(df_final.columns)}"),
                html.P(f"Mensaje procesamiento: {msg}"),
                html.P(f"Archivo: {filename}")
            ], color="danger")

        # 2) Guardar bitácora
        exito, msg_db = guardar_bitacora_bd(df_final)

        # 3) Procesar pesos reales
        df_pesos, msg_pesos = procesar_pesos_reales_torre(decoded, filename, fecha_manual)

        if df_pesos is None:
            exito_pesos = False
            msg_pesos_db = msg_pesos
        else:
            exito_pesos, msg_pesos_db = guardar_pesos_reales_bd(df_pesos)

        color = "success" if exito and exito_pesos else "warning"

        return dbc.Alert([
            html.H5("Resultado de Carga", className="alert-heading"),
            html.P(f"Bitácora - Detección: {msg}"),
            html.P(f"Bitácora - Base de Datos: {msg_db}"),
            html.Hr(),
            html.P(f"Pesos reales - Detección: {msg_pesos}"),
            html.P(f"Pesos reales - Base de Datos: {msg_pesos_db}"),
            html.Small(f"Archivo: {filename}")
        ], color=color)

    except Exception as e:
        error_tipo = type(e).__name__
        error_detalle = str(e)
        error_traceback = traceback.format_exc()

        print("ERROR CRÍTICO EN cargar_bitacora")
        print(error_traceback)

        return dbc.Alert([
            html.H5("Error crítico al cargar la bitácora", className="alert-heading"),

            html.P(
                "El archivo fue recibido, pero ocurrió un error inesperado durante "
                "el procesamiento o guardado de la información."
            ),

            html.Hr(),

            html.P([
                html.Strong("Archivo: "),
                filename if filename else "No disponible"
            ]),

            html.P([
                html.Strong("Tipo de error: "),
                error_tipo
            ]),

            html.P([
                html.Strong("Detalle técnico: "),
                error_detalle if error_detalle else "Sin detalle entregado por Python."
            ]),

            html.Hr(),

            html.Small(
                "Revisa que el archivo tenga el formato esperado, que corresponda "
                "a una bitácora válida y que no esté dañado o vacío."
            )
        ], color="danger")