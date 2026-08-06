from dash import html, dcc
import dash_bootstrap_components as dbc
import calendar
import datetime as dt

_MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

_MONTH_RANGE_START = dt.date(2024, 1, 1)


def _reference_month():
    """Mes de referencia: mes anterior si estamos antes del día 5, si no el mes actual."""
    today = dt.date.today()
    if today.day < 5:
        return (today.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    return today.replace(day=1)


def _default_dates():
    return _dates_from_month(_default_month())


def _default_month():
    ref = _reference_month()
    return f"{ref.year:04d}-{ref.month:02d}"


def _max_date_allowed():
    return dt.date.today().strftime("%Y-%m-%d")


def _dates_from_month(mes_val: str):
    """Devuelve (inicio, fin) inclusive para un valor YYYY-MM."""
    year, month = map(int, mes_val.split("-"))
    last_day = calendar.monthrange(year, month)[1]
    ini = f"{year:04d}-{month:02d}-01"
    fin = f"{year:04d}-{month:02d}-{last_day:02d}"
    return ini, fin


_DATEPICKER_KWARGS = {
    "display_format": "DD-MM-YYYY",
    "month_format": "MMMM YYYY",
    "placeholder": "Seleccionar fecha",
    "first_day_of_week": 1,
    "clearable": False,
    "className": "rp-fecha-picker",
    "max_date_allowed": _max_date_allowed(),
}


def _month_options():
    today = dt.date.today()
    end = today.replace(day=1)
    y, m = _MONTH_RANGE_START.year, _MONTH_RANGE_START.month
    options = []
    while (y, m) <= (end.year, end.month):
        val = f"{y:04d}-{m:02d}"
        options.append({"label": f"{_MONTHS_ES[m]} {y}", "value": val})
        m += 1
        if m > 12:
            m = 1
            y += 1
    options.reverse()
    return options


def _report_card(title, description, tipo):
    botones_pdf = []
    if tipo == "representatividad_torres":
        botones_pdf = [
            dbc.Button([
                html.I(className="bi bi-file-earmark-pdf me-2"),
                "PDF Químico vigente",
            ], id={"type": "report-pdf-btn", "tipo": f"{tipo}_quimico"},
               className="rp-btn-pdf", n_clicks=0),
            dbc.Button([
                html.I(className="bi bi-file-earmark-pdf me-2"),
                "PDF Físico vigente",
            ], id={"type": "report-pdf-btn", "tipo": f"{tipo}_fisico"},
               className="rp-btn-pdf", n_clicks=0),
            dbc.Button([
                html.I(className="bi bi-file-earmark-pdf me-2"),
                "PDF SRR vigente",
            ], id={"type": "report-pdf-btn", "tipo": f"{tipo}_srr"},
               className="rp-btn-pdf", n_clicks=0),
        ]
    elif tipo not in {"reporte_turno", "prod"}:
        botones_pdf = [
            dbc.Button([
                html.I(className="bi bi-file-earmark-pdf me-2"),
                "Exportar PDF",
            ], id={"type": "report-pdf-btn", "tipo": tipo},
               className="rp-btn-pdf", n_clicks=0),
        ]

    return dbc.Card([
        dbc.CardBody([
            # Icon + title + badge
            html.Div([
                html.Div(
                    html.I(className="bi bi-file-earmark-text rp-card-icon"),
                    className="rp-card-icon-wrap",
                ),
                html.Div([
                    html.Span(title, className="rp-card-title"),
                    dbc.Badge("Disponible", color="success", pill=True, className="ms-2 rp-badge"),
                ], className="d-flex align-items-center flex-wrap gap-1"),
            ], className="d-flex align-items-center gap-3 mb-2"),

            # Description
            html.P(description, className="rp-card-desc"),

            # Buttons
            html.Div([
                dbc.Button([
                    html.I(className="bi bi-pencil-square me-2"),
                    "Editar comentarios",
                ], id={"type": "report-gen-btn", "tipo": tipo},
                   className="rp-btn-export me-2", n_clicks=0, color="primary")
                if tipo == "representatividad_torres"
                else html.Div(),
                dbc.Button([
                    html.I(className="bi bi-file-earmark-excel me-2"),
                    (
                        "Descargar Excel oficial vigente"
                        if tipo == "representatividad_torres"
                        else "Exportar Excel"
                    ),
                ], id={"type": "report-export-btn", "tipo": tipo},
                   className="rp-btn-export me-2", n_clicks=0),
                *botones_pdf,
            ], className="d-flex flex-wrap gap-2"),
            html.Div(
                [
                    html.P(
                        "Los botones principales descargan el reporte oficial "
                        "vigente. El historial permite descargar una versión "
                        "publicada específica.",
                        className="text-muted small mt-3 mb-0",
                    ),
                ]
                if tipo == "representatividad_torres"
                else []
            ),
        ])
    ], className="rp-card h-100")


def layout():
    return html.Div([
        # Shared date filter bar
        html.Div(
            className="rp-fecha-filter",
            children=[
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Período", className="rp-fecha-label"),
                                dbc.RadioItems(
                                    id="report-fecha-modo",
                                    options=[
                                        {"label": "Mes completo", "value": "mes"},
                                        {"label": "Rango personalizado", "value": "rango"},
                                    ],
                                    value="mes",
                                    inline=True,
                                    className="btn-group rp-fecha-segmented",
                                    inputClassName="btn-check",
                                    labelClassName="btn btn-outline-primary rp-fecha-segment-btn",
                                ),
                            ], width=12),
                        ], className="mb-3"),
                        dbc.Row([
                            dbc.Col(
                                className="rp-fecha-input-col",
                                width="auto",
                                children=[
                                    html.Div(
                                        id="report-fecha-mes-wrap",
                                        children=[
                                            dbc.Label("Mes", className="rp-fecha-label"),
                                            dcc.Dropdown(
                                                id="report-fecha-mes",
                                                options=_month_options(),
                                                value=_default_month(),
                                                clearable=False,
                                                className="rp-fecha-mes-dropdown",
                                            ),
                                        ],
                                    ),
                                    html.Div(
                                        id="report-fecha-rango-wrap",
                                        className="rp-fecha-rango-wrap",
                                        style={"display": "none"},
                                        children=dbc.Row([
                                            dbc.Col([
                                                dbc.Label("Fecha Inicio", className="rp-fecha-label"),
                                                dcc.DatePickerSingle(
                                                    id="report-fecha-inicio",
                                                    date=_default_dates()[0],
                                                    initial_visible_month=_default_dates()[0],
                                                    **_DATEPICKER_KWARGS,
                                                ),
                                            ], width="auto"),
                                            dbc.Col([
                                                dbc.Label("Fecha Final", className="rp-fecha-label"),
                                                dcc.DatePickerSingle(
                                                    id="report-fecha-final",
                                                    date=_default_dates()[1],
                                                    initial_visible_month=_default_dates()[1],
                                                    **_DATEPICKER_KWARGS,
                                                ),
                                            ], width="auto"),
                                        ], className="g-3 align-items-end rp-fecha-rango-row"),
                                    ),
                                ],
                            ),
                            dbc.Col([
                                html.Div(id="report-fecha-warning", className="mt-1"),
                            ], width="auto", className="d-flex align-items-end"),
                        ], className="g-3 align-items-end justify-content-start"),
                    ], className="py-4"),
                ], className="rp-fecha-filter-card mb-4"),
            ],
        ),

        # Subtabs
        dcc.Tabs(
            id="report-subtabs",
            value="tab-diarios",
            className="rp-tabs",
            children=[

                # ── REPORTES DIARIOS ──────────────────────────────────
                dcc.Tab(
                    label="Reportes Diarios",
                    value="tab-diarios",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=dbc.Row([
                        dbc.Col(_report_card(
                            "Representatividad Torres",
                            "Representatividad diaria de torres de muestreo por turno y tipo de análisis.",
                            "representatividad_torres",
                        ), md=4, className="mb-4"),
                        dbc.Col(_report_card(
                            "Análisis Torres de Muestreo",
                            "Análisis de las Torres de Muestreo por turno: leyes, granulometrías y fuentes de información.",
                            "reporte_turno",
                        ), md=4, className="mb-4"),
                        dbc.Col(_report_card(
                            "Datos Conciliados",
                            "Datos conciliados diarios de producción. Superintendencia Medición y Reconciliación.",
                            "prod",
                        ), md=4, className="mb-4"),
                    ], className="g-4 mt-3"),
                ),

                # ── REPORTES SEMANALES ────────────────────────────────
                dcc.Tab(
                    label="Reportes Semanales",
                    value="tab-semanales",
                    className="rp-tab",
                    selected_className="rp-tab--selected",
                    children=dbc.Row([
                        dbc.Col(_report_card(
                            "Balance Semanal",
                            "Balance semanal promedio de producción catódica por período seleccionado.",
                            "balance",
                        ), md=4, className="mb-4"),
                        dbc.Col(_report_card(
                            "Conciliación Mensual",
                            "Conciliación mensual acumulada de producción catódica.",
                            "conciliacion",
                        ), md=4, className="mb-4"),
                    ], className="g-4 mt-3"),
                ),
            ],
        ),

        # ── PROGRESS BAR ─────────────────────────────────────────────
        html.Div(id="report-progress", className="mt-3"),

        # ── RESULT AREA ───────────────────────────────────────────────
        # report-tabla (editor/grilla) VA FUERA de Loading: cada clic en Pad
        # o commit de comentario actualiza props de la grilla/stores y el
        # spinner de Loading provocaba recarga/parpadeo de toda la UI.
        html.Div([
            dcc.Loading(
                id="loading-report-visualizacion",
                type="circle",
                color="#E86D1F",
                children=html.Div(id="report-grafico", className="mb-3"),
            ),
            html.Div(id="report-tabla"),
            html.Div(id="report-historial", className="mt-3"),
            dcc.Store(id="rep-comentarios-store"),
            dcc.Store(id="rep-tab-activo-store"),
            dcc.Store(id="rep-periodo-store"),
            dcc.Store(id="rep-eliminar-id-store"),
            dcc.Store(id="rep-grid-blur-hook", data=0),
            dcc.Store(id="rep-publicar-trigger"),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("Eliminar versión del historial"),
                    ),
                    dbc.ModalBody([
                        html.P(
                            "Esta acción quitará esta versión del historial. "
                            "No se puede deshacer.",
                            className="mb-2",
                        ),
                        html.P(
                            'Escriba "confirmar borrado" para continuar:',
                            className="mb-2 fw-semibold",
                        ),
                        dbc.Input(
                            id="rep-eliminar-texto",
                            type="text",
                            placeholder="confirmar borrado",
                            autocomplete="off",
                        ),
                    ]),
                    dbc.ModalFooter([
                        dbc.Button(
                            "Cancelar",
                            id="rep-eliminar-cancel-btn",
                            color="secondary",
                            outline=True,
                            className="me-2",
                        ),
                        dbc.Button(
                            "Eliminar versión",
                            id="rep-eliminar-confirm-btn",
                            color="danger",
                            disabled=True,
                        ),
                    ]),
                ],
                id="rep-eliminar-modal",
                is_open=False,
                backdrop="static",
            ),
            dbc.Modal(
                dbc.ModalBody(
                    html.Div(
                        [
                            dbc.Spinner(
                                size="sm",
                                color="primary",
                                spinner_class_name="me-2",
                            ),
                            html.Span(
                                "Publicando…",
                                className="fw-semibold",
                            ),
                        ],
                        className=(
                            "d-flex align-items-center "
                            "justify-content-center py-3"
                        ),
                    ),
                ),
                id="rep-publicar-modal",
                is_open=False,
                centered=True,
                size="sm",
                backdrop=True,
                keyboard=False,
            ),
            dbc.Modal(
                [
                    dbc.ModalHeader(
                        dbc.ModalTitle("No se puede generar el reporte"),
                        close_button=False,
                    ),
                    dbc.ModalBody(id="report-error-modal-body"),
                    dbc.ModalFooter(
                        dbc.Button(
                            "Entendido",
                            id="report-error-modal-close",
                            color="primary",
                            n_clicks=0,
                        )
                    ),
                ],
                id="report-error-modal",
                is_open=False,
                centered=True,
                backdrop="static",
            ),
            dcc.Download(id="report-download-xlsx"),
            dcc.Download(id="report-download-pdf"),
            html.Div(id="report-status", className="mt-2 text-muted small"),
        ], className="mt-4"),

    ], className="p-3")
