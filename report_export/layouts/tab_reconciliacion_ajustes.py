"""
tab_reconciliacion_ajustes.py
=============================
Layout para la pestaña "Datos Reconciliados" con 4 sub-tabs:
1. Datos Reconciliados - Tabla con ajustes y gráficos
2. Auditoría - Historial completo de cambios
3. Validaciones - Estado de integridad y anomalías
4. Comparativo - Comparación entre versiones
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_ag_grid as dag


def layout():
    """Layout principal de la pestaña Datos Reconciliados"""
    return html.Div([
        # ── CONTROLES PRINCIPALES ─────────────────────────────────────
        dbc.Card([
            dbc.CardHeader(
                html.H6("Parámetros de Reconciliación", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f8f9fa",
                       "letterSpacing": "0.06em", "textTransform": "uppercase"}
            ),
            dbc.CardBody([
                dbc.Row([
                    # Caso de balance
                    dbc.Col([
                        dbc.Label("Caso Balance", className="fw-semibold"),
                        dcc.Dropdown(
                            id="dropdown-caso-recon",
                            placeholder="Seleccione caso",
                            clearable=False,
                        ),
                    ], md=3, className="mb-3"),
                    
                    # Rango de fechas
                    dbc.Col([
                        dbc.Label("Fecha Inicio", className="fw-semibold"),
                        dcc.DatePickerSingle(
                            id="date-inicio-recon",
                            display_format="DD-MM-YYYY",
                            placeholder="DD-MM-YYYY",
                        ),
                    ], md=2, className="mb-3"),
                    
                    dbc.Col([
                        dbc.Label("Fecha Fin", className="fw-semibold"),
                        dcc.DatePickerSingle(
                            id="date-fin-recon",
                            display_format="DD-MM-YYYY",
                            placeholder="DD-MM-YYYY",
                        ),
                    ], md=2, className="mb-3"),
                    
                    # Run ID
                    dbc.Col([
                        dbc.Label("Run ID", className="fw-semibold"),
                        dcc.Dropdown(
                            id="dropdown-run-id-recon",
                            placeholder="Seleccione run",
                            clearable=False,
                        ),
                    ], md=3, className="mb-3"),
                    
                    # Botón procesar
                    dbc.Col([
                        html.Div(className="mb-2"),  # Spacer para alinear con las labels
                        dbc.Button(
                            [html.I(className="bi bi-play-circle me-2"), "Procesar"],
                            id="btn-procesar-recon",
                            color="success",
                            n_clicks=0,
                            className="w-100",
                        ),
                    ], md=2, className="mb-3"),
                ], className="g-3 align-items-end"),
            ]),
        ], className="mb-4"),

        # ── TABS CON 4 SUB-SECCIONES ──────────────────────────────────
        dcc.Tabs(
            id="tabs-reconciliacion",
            value="tab-datos-reconciliados",
            className="rp-tabs",
            children=[
                # ════════════════════════════════════════════════════════
                # TAB 1: DATOS RECONCILIADOS
                # ════════════════════════════════════════════════════════
                dcc.Tab(
                    label="Datos Reconciliados",
                    value="tab-datos-reconciliados",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=html.Div([
                        # Controles de esta sección
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="bi bi-check-circle me-2"), "Marcar como Oficial"],
                                    id="btn-marcar-oficial",
                                    color="primary",
                                    n_clicks=0,
                                    disabled=True,
                                ),
                            ], width="auto"),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="bi bi-download me-2"), "Exportar Excel"],
                                    id="btn-exportar-recon-excel",
                                    color="info",
                                    n_clicks=0,
                                    disabled=True,
                                ),
                            ], width="auto"),
                            dbc.Col([
                                html.Div(id="msg-procesar-recon", 
                                        style={"fontSize": 12, "color": "#666"})
                            ], width="auto", className="ms-auto"),
                        ], className="g-2 mb-3 align-items-center"),

                        # Status message
                        dbc.Alert(
                            id="alert-procesar-recon",
                            is_open=False,
                            dismissable=True,
                            className="mb-3",
                        ),

                        # Tabla principal con ag-grid
                        dcc.Loading(
                            id="loading-tabla-recon",
                            type="circle",
                            color="#E86D1F",
                            children=html.Div([
                                dag.AgGrid(
                                    id="tabla-ajustes-recon",
                                    columnDefs=[],
                                    rowData=[],
                                    className="ag-theme-balham",
                                    style={"width": "100%", "height": "500px"},
                                    csvExportParams={"fileName": "ajustes_reconciliacion.csv"},
                                ),
                            ]),
                        ),

                        # Gráficos
                        dbc.Row([
                            dbc.Col([
                                dcc.Loading(
                                    dcc.Graph(id="grafico-ajustes-por-dia"),
                                    type="circle",
                                )
                            ], md=6, className="mt-3"),
                            dbc.Col([
                                dcc.Loading(
                                    dcc.Graph(id="grafico-distribucion-flujos"),
                                    type="circle",
                                )
                            ], md=6, className="mt-3"),
                        ]),

                        # Store para datos procesados
                        dcc.Store(id="store-datos-procesados"),
                        dcc.Download(id="download-recon-excel"),
                    ], className="mt-2"),
                ),

                # ════════════════════════════════════════════════════════
                # TAB 2: AUDITORÍA
                # ════════════════════════════════════════════════════════
                dcc.Tab(
                    label="Auditoría",
                    value="tab-auditoria",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=html.Div([
                        # Botones de acción
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="bi bi-arrow-clockwise me-2"), "Cargar Historial"],
                                    id="btn-cargar-auditoria",
                                    color="primary",
                                    n_clicks=0,
                                ),
                            ], width="auto"),
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="bi bi-file-earmark-pdf me-2"), "Exportar Reporte"],
                                    id="btn-exportar-auditoria",
                                    color="warning",
                                    n_clicks=0,
                                    disabled=True,
                                ),
                            ], width="auto"),
                        ], className="g-2 mb-3"),

                        # Tabla de auditoría
                        dcc.Loading(
                            id="loading-tabla-auditoria",
                            type="circle",
                            color="#E86D1F",
                            children=html.Div([
                                dag.AgGrid(
                                    id="tabla-auditoria",
                                    columnDefs=[],
                                    rowData=[],
                                    className="ag-theme-balham",
                                    style={"width": "100%", "height": "600px"},
                                ),
                            ]),
                        ),

                        # Detalle de auditoría
                        dbc.Card([
                            dbc.CardHeader("Detalle de Trazabilidad", className="fw-semibold"),
                            dbc.CardBody(id="detalle-auditoria", children=[
                                html.P("Seleccione un registro para ver detalles", 
                                      className="text-muted small")
                            ]),
                        ], className="mt-3"),

                        dcc.Download(id="download-auditoria-pdf"),
                    ], className="mt-2"),
                ),

                # ════════════════════════════════════════════════════════
                # TAB 3: VALIDACIONES
                # ════════════════════════════════════════════════════════
                dcc.Tab(
                    label="Validaciones",
                    value="tab-validaciones",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=html.Div([
                        # Botón para ejecutar validaciones
                        dbc.Row([
                            dbc.Col([
                                dbc.Button(
                                    [html.I(className="bi bi-check2-square me-2"), "Ejecutar Validaciones"],
                                    id="btn-ejecutar-validaciones",
                                    color="primary",
                                    n_clicks=0,
                                    disabled=True,
                                ),
                            ], width="auto"),
                        ], className="g-2 mb-3"),

                        # Validación 1: Integridad de suma
                        dbc.Card([
                            dbc.CardHeader(
                                html.Div([
                                    html.I(className="bi bi-check-circle me-2"),
                                    "Integridad de Suma",
                                ], className="d-flex align-items-center"),
                                className="fw-semibold",
                            ),
                            dbc.CardBody(id="validacion-suma-integridad"),
                        ], className="mb-3"),

                        # Validación 2: Días con valor_medido = 0
                        dbc.Card([
                            dbc.CardHeader(
                                html.Div([
                                    html.I(className="bi bi-exclamation-triangle me-2"),
                                    "Ajustes en Días con Valor Cero",
                                ], className="d-flex align-items-center"),
                                className="fw-semibold",
                            ),
                            dbc.CardBody(id="validacion-dias-cero"),
                        ], className="mb-3"),

                        # Validación 3: Outliers
                        dbc.Card([
                            dbc.CardHeader(
                                html.Div([
                                    html.I(className="bi bi-flag me-2"),
                                    "Detección de Anomalías (Z-score)",
                                ], className="d-flex align-items-center"),
                                className="fw-semibold",
                            ),
                            dbc.CardBody(id="validacion-outliers"),
                        ], className="mb-3"),

                        # Resumen de validaciones
                        dbc.Card([
                            dbc.CardHeader("Resumen de Validaciones", className="fw-semibold"),
                            dbc.CardBody(id="resumen-validaciones", children=[
                                html.P("Sin datos", className="text-muted small")
                            ]),
                        ], className="mb-3"),

                        dcc.Store(id="store-validaciones"),
                    ], className="mt-2"),
                ),

                # ════════════════════════════════════════════════════════
                # TAB 4: COMPARATIVO
                # ════════════════════════════════════════════════════════
                dcc.Tab(
                    label="Comparativo",
                    value="tab-comparativo",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=html.Div([
                        # Selectores de versiones a comparar
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Versión 1", className="fw-semibold"),
                                dcc.Dropdown(
                                    id="dropdown-run-v1",
                                    placeholder="Seleccione primera versión",
                                ),
                            ], md=4, className="mb-3"),
                            
                            dbc.Col([
                                dbc.Label("Versión 2", className="fw-semibold"),
                                dcc.Dropdown(
                                    id="dropdown-run-v2",
                                    placeholder="Seleccione segunda versión",
                                ),
                            ], md=4, className="mb-3"),
                            
                            dbc.Col([
                                html.Div(className="mb-2"),  # Spacer
                                dbc.Button(
                                    [html.I(className="bi bi-arrow-left-right me-2"), "Comparar"],
                                    id="btn-comparar-versiones",
                                    color="success",
                                    n_clicks=0,
                                ),
                            ], md=4, className="mb-3 d-flex align-items-end"),
                        ], className="g-3"),

                        # Resumen comparativo
                        dbc.Card([
                            dbc.CardHeader("Resumen de Diferencias", className="fw-semibold"),
                            dbc.CardBody(id="resumen-comparativo", children=[
                                html.P("Seleccione dos versiones para comparar", 
                                      className="text-muted small")
                            ]),
                        ], className="mb-3"),

                        # Tabla de diferencias por día
                        dcc.Loading(
                            id="loading-tabla-comparativo",
                            type="circle",
                            color="#E86D1F",
                            children=html.Div([
                                dag.AgGrid(
                                    id="tabla-comparativo",
                                    columnDefs=[],
                                    rowData=[],
                                    className="ag-theme-balham",
                                    style={"width": "100%", "height": "400px"},
                                ),
                            ]),
                        ),

                        # Gráfico de diferencias
                        dcc.Loading(
                            dcc.Graph(id="grafico-comparativo"),
                            type="circle",
                            className="mt-3",
                        ),

                        dcc.Store(id="store-comparativo"),
                    ], className="mt-2"),
                ),
            ],
        ),

        # ── MODALES ────────────────────────────────────────────────────
        # Modal para confirmar marcar como oficial
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmar Operación")),
            dbc.ModalBody(
                "¿Está seguro de que desea marcar esta versión como oficial? "
                "La versión oficial anterior será archivada automáticamente."
            ),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id="btn-modal-cancelar", n_clicks=0),
                dbc.Button("Confirmar", id="btn-modal-confirmar", 
                          color="danger", n_clicks=0),
            ]),
        ], id="modal-confirmar-oficial", is_open=False, centered=True),

        # Modal para mensajes de error
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Error"), close_button=True),
            dbc.ModalBody(id="modal-error-body"),
        ], id="modal-error", is_open=False, centered=True),

        # Store para inicialización de casos
        dcc.Store(id="store-init-casos", data={"initialized": True}),
    ])
