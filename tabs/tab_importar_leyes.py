from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import base64
import io
import datetime

# Importamos tu función de procesamiento (backend)
from tabs.procesar_excel_leyes import procesar_excel_multih

# --- LAYOUT ---
layout = html.Div([
    # --- Título ---
    html.Div([
        html.H5("Carga de Reporte Mensual (Torre 1 o Torre 2)", className="text-primary fw-bold"),
        html.P(
            "Sube el archivo Excel. Puedes cambiar de semana libremente tras cargar. "
            "Si necesitas subir el mismo archivo de nuevo, usa el botón 'Limpiar'.",
            className="text-muted small"
        )
    ], className="mb-4"),

    # --- Selector de Periodo ---
    dbc.Card([
        dbc.CardBody([
            html.Label("1. Selecciona el periodo a cargar:", className="fw-bold mb-2"),
            dbc.RadioItems(
                id="periodo-selector-leyes",
                options=[
                    {"label": "Semana 1 (Días 1-7)", "value": "s1"},
                    {"label": "Semana 2 (Días 8-14)", "value": "s2"},
                    {"label": "Semana 3 (Días 15-21)", "value": "s3"},
                    {"label": "Semana 4 (Días 22-31)", "value": "s4"},
                    {"label": "Todo el Mes (Todas las hojas)", "value": "all"},
                ],
                value="s1",
                inline=True,
                className="mb-3",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary me-2",
                labelCheckedClassName="active"
            ),
        ])
    ], className="mb-3 shadow-sm border-0"),

    # --- Área de Carga (Upload) ---
    dcc.Upload(
        id='upload-leyes-granulo',
        children=html.Div([
            html.Div([
                html.I(className="bi bi-cloud-arrow-up fs-2 text-primary mb-2"),
                html.H6("Arrastra tu Excel aquí o haz clic", className="text-dark"),
                html.Small("Soporta formato .xlsx", className="text-muted")
            ], className="d-flex flex-column align-items-center justify-content-center h-100")
        ]),
        style={
            'width': '100%', 'height': '120px', 'lineHeight': '60px',
            'borderWidth': '2px', 'borderStyle': 'dashed', 'borderRadius': '10px',
            'textAlign': 'center', 'margin': '10px 0', 'backgroundColor': '#f8f9fa',
            'cursor': 'pointer', 'borderColor': '#0d6efd'
        },
        multiple=False
    ),

    # --- Botón de Reset (Para solucionar el bug de resubida) ---
    html.Div([
        html.Button(
            [html.I(className="bi bi-trash me-2"), "Limpiar / Subir otro archivo"],
            id="btn-reset-upload",
            className="btn btn-outline-secondary btn-sm",
            style={"display": "none"} # Se oculta inicialmente
        )
    ], className="d-flex justify-content-end mb-3"),

    # --- Área de Feedback (Resultados) ---
    html.Div([
        dbc.Spinner(
            html.Div(id='output-upload-leyes'),
            color="primary", type="grow", size="sm"
        )
    ], className="mt-4")
])

# --- CALLBACK PRINCIPAL ---
def register_callbacks(app):
    
    # 1. Callback para procesar datos (Carga y cambio de semana)
    @app.callback(
        [Output('output-upload-leyes', 'children'),
         Output('btn-reset-upload', 'style')], # Mostramos el botón reset si hay datos
        [Input('upload-leyes-granulo', 'contents'),
         Input('upload-leyes-granulo', 'last_modified'), # Gatillo extra para cambios de archivo
         Input('periodo-selector-leyes', 'value')],
        [State('upload-leyes-granulo', 'filename')],
        prevent_initial_call=True
    )
    def update_output(list_of_contents, list_of_dates, periodo, filename):
        # Contexto: ¿Quién disparó el callback?
        ctx = callback_context
        if not ctx.triggered:
            return html.Div(), {"display": "none"}

        # Si no hay contenido (por ejemplo, tras limpiar), borramos todo
        if list_of_contents is None:
            return html.Div(), {"display": "none"}

        try:
            # Decodificar
            content_type, content_string = list_of_contents.split(',')
            decoded = base64.b64decode(content_string)
            file_like = io.BytesIO(decoded)

            # Definir rango
            dias_map = {
                "s1": list(range(1, 8)),
                "s2": list(range(8, 15)),
                "s3": list(range(15, 22)),
                "s4": list(range(22, 32)),
                "all": "all"
            }
            dias_a_procesar = dias_map.get(periodo, "all")
            nombre_periodo = periodo.upper() if periodo == "all" else f"SEMANA {periodo[-1]}"

            # Procesar
            mensaje = procesar_excel_multih(file_like, filename, dias_a_procesar)

            # Iconos y Colores
            if "Error" in mensaje or "❌" in mensaje:
                color, icon = "danger", "bi bi-x-circle-fill"
            elif "⚠️" in mensaje:
                color, icon = "warning", "bi bi-exclamation-triangle-fill"
            else:
                color, icon = "success", "bi bi-check-circle-fill"

            # Crear alerta con TIMESTAMP para forzar refresco visual
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            
            alerta = dbc.Alert(
                [
                    html.H5([html.I(className=f"{icon} me-2"), f"Resultado: {nombre_periodo}"], className="alert-heading"),
                    html.P(mensaje),
                    html.Hr(),
                    html.Small(f"Procesado a las {ts} - Archivo: {filename}", className="text-muted")
                ],
                color=color,
                dismissable=True
            )

            # Retornamos Alerta y mostramos el botón de Reset
            return alerta, {"display": "block"}

        except Exception as e:
            return dbc.Alert(f"Error crítico: {str(e)}", color="danger"), {"display": "block"}

    # 2. Callback para LIMPIAR el upload (Reset)
    @app.callback(
        Output('upload-leyes-granulo', 'contents'),
        Input('btn-reset-upload', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_upload_component(n):
        return None # Esto borra el archivo de la memoria y reinicia el componente