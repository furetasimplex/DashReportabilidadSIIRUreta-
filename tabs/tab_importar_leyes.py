from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import base64
import io

# Importamos la función de procesamiento que creamos anteriormente
# Asegúrate de que la ruta sea correcta según tu estructura de carpetas
from tabs.procesar_excel_leyes import procesar_excel_multih

layout = html.Div([
    # --- Título y Descripción ---
    html.Div([
        html.H5("Carga de Reporte Mensual (Torre 1 o Torre 2)", className="text-primary fw-bold"),
        html.P(
            "Sube el archivo Excel mensual completo. El sistema detectará automáticamente la Torre "
            "y procesará solo los días del periodo seleccionado.",
            className="text-muted small"
        )
    ], className="mb-4"),

    # --- Selector de Periodo (Semanal) ---
    dbc.Card([
        dbc.CardBody([
            html.Label("1. Selecciona el periodo a cargar:", className="fw-bold mb-2"),
            dbc.RadioItems(
                id="periodo-selector",
                options=[
                    {"label": "Semana 1 (Días 1-7)", "value": "s1"},
                    {"label": "Semana 2 (Días 8-14)", "value": "s2"},
                    {"label": "Semana 3 (Días 15-21)", "value": "s3"},
                    {"label": "Semana 4 (Días 22-31)", "value": "s4"},
                    {"label": "Mes Completo (1-31)", "value": "full"},
                ],
                value="s1", # Valor por defecto
                inline=True,
                className="mb-3",
                inputClassName="btn-check",
                labelClassName="btn btn-outline-primary me-2",
                labelCheckedClassName="active"
            ),
        ])
    ], className="mb-4 shadow-sm border-0"),

    # --- Zona de Carga (Drag & Drop Estilo Simulador) ---
    dcc.Upload(
        id='upload-leyes-granulo',
        children=html.Div([
            html.Div([
                html.I(className="bi bi-building fs-1 text-info mb-2"), # Icono de Edificio/Torre
                html.H5("Subir Excel de Torre", className="fw-semibold text-dark"),
                html.Small("Arrastra o selecciona el archivo .xlsx", className="text-muted")
            ], className="d-flex flex-column align-items-center justify-content-center h-100")
        ]),
        className="upload-box border-dashed border-info bg-light rounded-3 p-5 shadow-sm position-relative",
        style={
            "cursor": "pointer",
            "border": "2px dashed #0dcaf0", # Borde cian
            "transition": "all 0.3s ease",
            "minHeight": "150px"
        },
        multiple=False
    ),

    # --- Área de Resultados ---
    html.Div([
        dbc.Spinner(
            html.Div(id='import-feedback-leyes-granulo'),
            color="primary",
            type="grow",
            size="sm"
        )
    ], className="mt-4")
])

def register_callbacks(app):
    @app.callback(
        Output('import-feedback-leyes-granulo', 'children'),
        Input('upload-leyes-granulo', 'contents'),
        State('upload-leyes-granulo', 'filename'),
        State('periodo-selector', 'value')
    )
    def importar_excel(contents, filename, periodo_seleccionado):
        if contents is None:
            return ""
        
        try:
            # 1. Definir los días según la selección
            if periodo_seleccionado == "s1":
                dias_a_procesar = list(range(1, 8))   # 1 al 7
            elif periodo_seleccionado == "s2":
                dias_a_procesar = list(range(8, 15))  # 8 al 14
            elif periodo_seleccionado == "s3":
                dias_a_procesar = list(range(15, 22)) # 15 al 21
            elif periodo_seleccionado == "s4":
                dias_a_procesar = list(range(22, 32)) # 22 al 31
            else:
                dias_a_procesar = list(range(1, 32))  # Todo el mes

            # 2. Decodificar archivo
            content_type, content_string = contents.split(',')
            decoded = base64.b64decode(content_string)
            file_like = io.BytesIO(decoded)
            
            # 3. Procesar usando la función que creamos (backend)
            mensaje = procesar_excel_multih(file_like, filename, dias_a_procesar)
            
            # 4. Determinar estilo del mensaje según el resultado
            if "Error" in mensaje:
                color_alerta = "danger"
                icono = "bi bi-exclamation-triangle-fill me-2"
            elif "No se encontraron datos" in mensaje:
                color_alerta = "warning"
                icono = "bi bi-exclamation-circle-fill me-2"
            else:
                color_alerta = "success"
                icono = "bi bi-check-circle-fill me-2"

            # 5. Retornar Alerta Estilizada
            return dbc.Alert(
                children=[
                    html.H4([
                        html.I(className=icono), 
                        " Resultado de la Carga"
                    ], className="alert-heading"),
                    html.Hr(),
                    html.P(mensaje, className="mb-0")
                ],
                color=color_alerta,
                dismissable=True,
                className="shadow-sm border-0"
            )
            
        except Exception as e:
            return dbc.Alert(
                [html.I(className="bi bi-bug-fill me-2"), f"Error crítico: {str(e)}"], 
                color="danger", 
                dismissable=True
            )