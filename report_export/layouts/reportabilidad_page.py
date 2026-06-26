from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
import datetime as dt

def _default_dates():
    year = dt.date.today().year
    month = dt.date.today().month
    day = dt.date.today().day
    day_7 = dt.date.today().day-7

    #return f"{year}-{month}-01", f"{year}-{month}-{day}"
    return f"{year}-03-01", f"{year}-03-{day}"


def _report_card(title, description, tipo):
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
                    html.I(className="bi bi-file-earmark-excel me-2"),
                    "Exportar Excel",
                ], id={"type": "report-export-btn", "tipo": tipo},
                   className="rp-btn-export me-2", n_clicks=0),
                dbc.Button([
                    html.I(className="bi bi-file-earmark-pdf me-2"),
                    "Exportar PDF",
                ], id={"type": "report-pdf-btn", "tipo": tipo},
                   className="rp-btn-pdf", n_clicks=0),
            ], className="d-flex flex-wrap gap-2"),
        ])
    ], className="rp-card h-100")


def layout():
    return html.Div([
        # Shared date filter bar
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Fecha Inicio", className="fw-semibold small mb-1"),
                        dcc.DatePickerSingle(
                            id="report-fecha-inicio",
                            display_format="DD-MM-YYYY",
                            date=_default_dates()[0],
                        ),
                    ], width="auto"),
                    dbc.Col([
                        dbc.Label("Fecha Final", className="fw-semibold small mb-1"),
                        dcc.DatePickerSingle(
                            id="report-fecha-final",
                            display_format="DD-MM-YYYY",
                            date=_default_dates()[1],
                        ),
                    ], width="auto"),
                    dbc.Col([
                        html.Div(id="report-fecha-warning", className="mt-1"),
                    ], width="auto", className="d-flex align-items-end"),
                ], className="g-3 align-items-end"),
            ], className="py-3"),
        ], className="mb-4"),

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
                            "Producción Diaria",
                            "Datos conciliados diarios de producción. Superintendencia Medición y Reconciliación.",
                            "prod",
                        ), md=4, className="mb-4"),
                        dbc.Col(_report_card(
                            "Representatividad Torres",
                            "Representatividad diaria de torres de muestreo por turno y tipo de análisis.",
                            "representatividad_torres",
                        ), md=4, className="mb-4"),
                        dbc.Col(_report_card(
                            "Análisis Torres por Turno",
                            "Análisis de las Torres de Muestreo por turno: leyes, granulometrías y fuentes de información.",
                            "reporte_turno",
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
        html.Div([
            dcc.Loading(
                id="loading-report-visualizacion",
                type="circle",
                color="#E86D1F",
                children=html.Div([
                    html.Div(id="report-grafico", className="mb-3"),
                    html.Div(id="report-tabla"),
                ]),
            ),
            html.Div(id="report-historial", className="mt-3"),
            dcc.Download(id="report-download-xlsx"),
            dcc.Download(id="report-download-pdf"),
            html.Div(id="report-status", className="mt-2 text-muted small"),
        ], className="mt-4"),

    ], className="p-3")
