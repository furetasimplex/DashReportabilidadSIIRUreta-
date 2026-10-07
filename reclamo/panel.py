"""
Dashboard de control de reclamo — Planta Hidrometalurgica Spence.

Doble proposito, tal como fue definido:
  1. Herramienta de control operacional del reclamo de rotopalas y camiones.
  2. Aseguramiento de la integridad de la reportabilidad antes de publicar.

Se apoya integramente en las vistas del esquema [reclamo] de SQL Server. No
duplica ninguna regla de negocio en Python: si una cifra esta mal, se corrige
en la vista, no aca.

Integrado directamente en el sitio SIIR (DashReportabilidadSIIR): no es un
proceso ni una app Dash aparte. layout() se cuelga bajo subtabs-reclamo en
layout.py, y los callbacks quedan registrados en la app Dash del sitio via
el decorador global @callback al importarse este modulo.
"""

from __future__ import annotations

import os
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from dash.dash_table.Format import Format, Group, Scheme

from env_loader import load_app_env

load_app_env()

from . import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paleta y estilos
# ---------------------------------------------------------------------------

AZUL = "#214D70"
GRIS = "#595959"
ROJO = "#A63139"
VERDE = "#1E6B3A"
AMBAR = "#A87718"
FONDO = "#F5F7FA"

CARD = {
    "backgroundColor": "white",
    "borderRadius": "12px",
    "padding": "20px 24px",
    "marginBottom": "18px",
    "border": "1px solid #E4EAF0",
    "boxShadow": "0 3px 14px rgba(28,55,77,0.05)",
}

TITULO_SECCION = {
    "color": AZUL,
    "fontSize": "18px",
    "fontWeight": 600,
    "marginTop": 0,
    "marginBottom": "4px",
}

SUBTITULO = {"color": GRIS, "fontSize": "13px", "lineHeight": "1.55", "marginTop": 0, "marginBottom": "16px"}

TABLA_ESTILO = dict(
    style_cell={
        "fontFamily": "Segoe UI, Arial, sans-serif",
        "fontSize": "12px",
        "padding": "6px 10px",
        "textAlign": "right",
    },
    style_header={
        "backgroundColor": AZUL,
        "color": "white",
        "fontWeight": 600,
        "textAlign": "center",
    },
    style_data_conditional=[
        {"if": {"row_index": "odd"}, "backgroundColor": "#F2F7FB"},
    ],
    style_table={"overflowX": "auto", "minWidth": "100%"},
    style_cell_conditional=[{"if": {"column_id": "Modulo"}, "textAlign": "left"}],
    page_size=15,
    sort_action="native",
    filter_action="none",
)


# ---------------------------------------------------------------------------
# Layout y callbacks: se integran directamente en la app Dash del sitio SIIR
# (un unico proceso, sin app Dash propia ni servidor separado). layout()
# se cuelga bajo subtabs-reclamo en layout.py; los callbacks usan el
# decorador global @callback (no @app.callback) para no depender de una
# instancia de app propia, mismo patron que
# report_export/callbacks/reportabilidad_cb.py.
# ---------------------------------------------------------------------------

def _hoy_chile() -> date:
    return datetime.now(ZoneInfo("America/Santiago")).date()


def _rango_inicial(hoy: date | None = None) -> tuple[date, date]:
    """Mes en curso hasta D-1, o mes anterior completo si hoy es día 1."""
    hoy = hoy or _hoy_chile()
    hasta = hoy - timedelta(days=1)
    desde = hasta.replace(day=1) if hoy.day == 1 else hoy.replace(day=1)
    return desde, hasta


def encabezado():
    return html.Div(
        style={"backgroundColor": AZUL, "padding": "24px 32px", "color": "white"},
        children=[
            html.H1(
                "Control de Reclamo",
                style={"margin": 0, "fontSize": "28px", "fontWeight": 650},
            ),
            html.Div(
                "Seguimiento operacional, validación y preparación del reclamo para publicación",
                style={"fontSize": "14px", "opacity": 0.96, "marginTop": "6px"},
            ),
            html.Div(
                "Reportabilidad SIIR · Planta Hidrometalúrgica Spence",
                style={"fontSize": "12px", "opacity": 0.72, "marginTop": "3px"},
            ),
        ],
    )


def barra_filtros():
    desde_def, hasta_def = _rango_inicial()
    return html.Div(
        style={**CARD, "display": "flex", "alignItems": "flex-end", "gap": "18px",
               "flexWrap": "wrap"},
        children=[
            html.Div([
                html.Label("Período", style={"fontSize": "12px", "color": GRIS,
                                             "display": "block", "marginBottom": "4px"}),
                dcc.DatePickerRange(
                    id="rango",
                    start_date=desde_def,
                    end_date=hasta_def,
                    display_format="DD-MM-YYYY",
                    start_date_placeholder_text="DD-MM-AAAA",
                    end_date_placeholder_text="DD-MM-AAAA",
                    first_day_of_week=1,
                ),
            ]),
            html.Button(
                "Refrescar vista",
                id="btn-actualizar",
                n_clicks=0,
                title="Vuelve a consultar la información mostrada. No sincroniza, recalcula ni publica.",
                style={"backgroundColor": "white", "color": AZUL, "border": f"1px solid {AZUL}",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px"},
            ),
            html.Button(
                "Reprocesar período",
                id="btn-recalcular",
                n_clicks=0,
                title="Sincroniza las fuentes disponibles, actualiza la secuencia de módulos, carga CV25/horas y recalcula el Reclamo para el período seleccionado.",
                style={"backgroundColor": AZUL, "color": "white", "border": "none",
                       "padding": "11px 24px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "14px", "fontWeight": 700},
            ),
            dcc.ConfirmDialog(
                id="confirmar-publicar",
                message="Se publicará el reclamo conciliado del período seleccionado. "
                        "Quedará visible para el resto de la organización. "
                        "Confirme solo si ya revisó la 'Vista previa del dato conciliado'.",
            ),
            html.Div(id="mensaje-accion",
                     style={"fontSize": "12px", "color": GRIS, "flexGrow": 1}),
            html.Div(
                "Para correcciones históricas, seleccione desde la primera fecha afectada hasta el último día que necesite recalcular.",
                style={"flexBasis": "100%", "fontSize": "12px", "color": GRIS},
            ),
        ],
    )


def panel_automatizacion():
    return html.Details(
        style=CARD,
        children=[
            html.Summary("Herramientas avanzadas", style={**TITULO_SECCION, "cursor": "pointer", "fontWeight": 650}),
            html.P(
                "Utilice estas acciones solo para diagnóstico o mantención manual de la secuencia. "
                "No son necesarias en el flujo normal cuando se utiliza ‘Reprocesar período’.",
                style=SUBTITULO,
            ),
            html.Button(
                "Actualizar secuencia de módulos",
                id="btn-automatizacion",
                n_clicks=0,
                title="Ejecuta únicamente la mantención de secuencia. No sincroniza todo el rango ni recalcula el Reclamo diario.",
                style={"backgroundColor": VERDE, "color": "white", "border": "none",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px"},
            ),
            html.H4("Resultado de la última actualización", style={"fontSize": "14px", "color": AZUL,
                                                                   "marginTop": "20px", "marginBottom": "6px"}),
            html.Div(id="resultado-automatizacion", style={"marginTop": "8px"}),
            html.Details(
                open=False,
                style={"marginTop": "12px"},
                children=[
                    html.Summary(
                        "Ver historial de automatización",
                        style={"cursor": "pointer", "fontSize": "13px", "color": AZUL,
                               "fontWeight": 600, "padding": "4px 0"},
                    ),
                    html.P("Este historial conserva eventos de ejecuciones anteriores y no representa necesariamente el número de problemas actualmente activos.",
                           style={**SUBTITULO, "marginTop": "8px"}),
                    html.Div(id="alertas-automatizacion", style={"marginTop": "8px"}),
                ],
            ),
        ],
    )


def panel_semaforo():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Validaciones antes de publicar", style=TITULO_SECCION),
            html.P(
                "Los bloqueos deben resolverse antes de publicar. Las advertencias no impiden "
                "la publicación, pero deben ser revisadas y justificadas.",
                style=SUBTITULO,
            ),
            html.Div(id="semaforo"),
        ],
    )


def panel_resumen_general():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Resumen general", style=TITULO_SECCION),
            html.P(
                "Tonelaje del período seleccionado por PAD y por origen. La comparación "
                "con CV25 corresponde a rotopalas a nivel planta.",
                style=SUBTITULO,
            ),
            html.Div(id="resumen-general"),
        ],
    )


def panel_matriz_mensual():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Vista mensual por módulo", style=TITULO_SECCION),
            html.P(
                "Consulte el tonelaje diario por módulo y PAD. Desplace la tabla horizontalmente para ver todo el período.",
                style=SUBTITULO,
            ),
            html.Label("Origen del tonelaje", style={"fontSize": "12px", "fontWeight": 600, "color": AZUL}),
            dcc.RadioItems(
                id="matriz-metrica",
                options=[
                    {"label": "Rotopala", "value": "rotopala"},
                    {"label": "Camiones", "value": "camiones"},
                    {"label": "Total", "value": "total"},
                ],
                value="total",
                inline=True,
                style={"fontSize": "13px", "marginBottom": "12px"},
                labelStyle={"marginRight": "16px"},
            ),
            dcc.Tabs(
                id="matriz-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Óxidos", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuros", value="2"),
                ],
            ),
            html.Div(id="matriz-mensual", style={"marginTop": "12px"}),
        ],
    )


def panel_remanente():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Tonelaje remanente por módulo", style=TITULO_SECCION),
            html.P(
                "Compare el tonelaje extraído con la base de cada módulo. Los excedentes se destacan para revisión.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="remanente-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Óxidos", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuros", value="2"),
                ],
            ),
            html.Div(id="tabla-remanente", style={"marginTop": "12px"}),
        ],
    )


def panel_preview_conciliados():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Vista previa antes de publicar", style=TITULO_SECCION),
            html.P(
                "Muestra cómo quedaría el reclamo publicado para el período seleccionado. "
                "Esta vista no publica información.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="preview-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Óxidos", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuros", value="2"),
                ],
            ),
            html.Div(id="tabla-preview-conciliados", style={"marginTop": "12px"}),
        ],
    )


def panel_cv25():
    return html.Div(
        style=CARD,
        children=[
            html.H3("CV25 vs Topografía", style=TITULO_SECCION),
            html.P(
                "Compara el tonelaje registrado por CV25 con el tonelaje respaldado por medición "
                "topográfica. Los días sin topografía pueden quedar temporalmente estimados mediante CV25.",
                style=SUBTITULO,
            ),
            html.Div("Brecha diaria y referencia histórica mensual se muestran por separado en el gráfico.",
                     style={"fontSize": "12px", "color": GRIS, "marginBottom": "8px"}),
            dcc.Graph(id="g-cv25", config={"displayModeBar": False}),
            dcc.Graph(id="g-brecha", config={"displayModeBar": False}),
        ],
    )


def panel_rendimiento():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Rendimiento de rotopala", style=TITULO_SECCION),
            html.P(
                "Toneladas secas por hora de operación y horas registradas. Los espacios sin línea "
                "corresponden a días sin información suficiente para calcular rendimiento.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="rendimiento-rotopala-tabs",
                value="1",
                children=[
                    dcc.Tab(label="Rotopala 1 — PAD Óxidos", value="1"),
                    dcc.Tab(label="Rotopala 2 — PAD Sulfuros", value="2"),
                ],
            ),
            dcc.Graph(id="g-rendimiento", config={"displayModeBar": False}),
            dcc.Graph(id="g-horas", config={"displayModeBar": False}),
        ],
    )


def panel_cuadratura():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Cuadratura de módulos", style=TITULO_SECCION),
            html.P(
                "Extracción acumulada frente al volumen base de cada módulo. Los casos "
                "sobre 100 % requieren revisión y un traspaso documentado. El acumulado "
                "parte del inicio de la campaña.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="cuadratura-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Óxidos", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuros", value="2"),
                ],
            ),
            dcc.Graph(id="g-cuadratura", config={"displayModeBar": False}),
            html.Div(id="tabla-cuadratura"),
            html.Hr(style={"border": "none", "borderTop": "1px solid #E0E0E0",
                           "margin": "16px 0"}),
            html.Div([
                html.Label("Revisar un módulo específico",
                           style={"fontSize": "12px", "color": GRIS, "fontWeight": 600,
                                  "display": "block", "marginBottom": "4px"}),
                dcc.Dropdown(id="cuadratura-modulo-select", placeholder="Seleccione un módulo",
                            style={"maxWidth": "420px"}),
            ]),
            html.Div(id="detalle-cuadratura-modulo", style={"marginTop": "12px"}),
        ],
    )


def panel_avance():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Avance diario de rotopala", style=TITULO_SECCION),
            html.P(
                "La topografía es la fuente de validación. Cuando no existe medición topográfica, "
                "el sistema puede utilizar una estimación temporal basada en CV25.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="avance-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Óxidos", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuros", value="2"),
                ],
            ),
            dcc.Graph(id="g-avance", config={"displayModeBar": False}),
            html.Div(id="tabla-avance"),
        ],
    )


_CAMPOS_DR = [
    ("tms", "TMS"),
    ("m3_totales", "Volumen total (m³)"),
    ("densidad", "Densidad"),
    ("m3_apilado", "m³ apilado"),
    ("tmh_apilado", "TMH apilado"),
    ("remanente_m3", "Remanente (m³)"),
    ("remanente_tms", "Remanente TMS"),
]


_CAMPOS_DR_UPD = [c for c in _CAMPOS_DR if c[0] != "densidad"]


def _grid_campos_dr(prefijo: str, campos=None):
    campos = campos if campos is not None else _CAMPOS_DR
    return html.Div(
        style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(120px, 1fr))",
               "gap": "10px"},
        children=[
            html.Div([
                html.Label(etiqueta, style={"fontSize": "12px", "color": GRIS}),
                dcc.Input(id=f"{prefijo}-{campo}", type="number", style={"width": "100%"}),
            ])
            for campo, etiqueta in campos
        ],
    )


def panel_disponible_rotopalas():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Datos base de módulos", style=TITULO_SECCION),
            html.P(
                "Consulta y administra el tonelaje, volumen y densidad utilizados como base "
                "para incorporar módulos a la secuencia de reclamo.",
                style=SUBTITULO,
            ),
            html.P("Después de guardar o agregar una base, seleccione el período afectado y use ‘Reprocesar período’ para incorporar el cambio al Reclamo.",
                   style={"fontSize": "12px", "color": AZUL, "fontWeight": 600}),
            html.Details([
                html.Summary("Ver detalle técnico", style={"cursor": "pointer", "color": AZUL}),
                html.P("Fuente: inventar_SpcHidr.disponible_rotopalas. La usan "
                       "sp_congelar_modulo y sp_auto_congelar_modulos_nuevos. "
                       "Sin m³ totales o densidad válidos, el módulo queda con ALERTA_SIN_BASE. "
                       "Las modificaciones de datos base se escriben en la tabla fuente.",
                       style={**SUBTITULO, "marginTop": "8px"}),
            ], style={"marginBottom": "16px", "fontSize": "12px"}),
            html.Div(
                style={"display": "flex", "alignItems": "flex-end", "gap": "14px",
                       "flexWrap": "wrap", "marginBottom": "14px"},
                children=[
                    html.Div([
                        html.Label("Campaña", style={"fontSize": "12px", "color": GRIS,
                                                      "display": "block", "marginBottom": "4px"}),
                        dcc.Dropdown(id="dr-filtro-campana", placeholder="Todas",
                                     style={"width": "200px"}),
                    ]),
                    html.Div([
                        html.Label("PAD", style={"fontSize": "12px", "color": GRIS,
                                                  "display": "block", "marginBottom": "4px"}),
                        dcc.Dropdown(
                            id="dr-filtro-pad",
                            options=[
                                {"label": "Ambos", "value": 0},
                                {"label": "PAD 1 — Óxidos", "value": 1},
                                {"label": "PAD 2 — Sulfuros", "value": 2},
                            ],
                            value=0, clearable=False, style={"width": "180px"},
                        ),
                    ]),
                    html.Div([
                        html.Label("Módulo (número)", style={"fontSize": "12px", "color": GRIS,
                                                              "display": "block", "marginBottom": "4px"}),
                        dcc.Input(id="dr-filtro-modulo", type="number", placeholder="Todos",
                                  style={"width": "110px"}),
                    ]),
                    html.Div([
                        html.Label("Fecha de conformación desde",
                                   style={"fontSize": "12px", "color": GRIS,
                                          "display": "block", "marginBottom": "4px"}),
                        dcc.DatePickerSingle(id="dr-filtro-fecha-desde", display_format="DD-MM-YYYY", placeholder="DD-MM-AAAA"),
                    ]),
                    html.Div([
                        html.Label("Hasta", style={"fontSize": "12px", "color": GRIS,
                                                    "display": "block", "marginBottom": "4px"}),
                        dcc.DatePickerSingle(id="dr-filtro-fecha-hasta", display_format="DD-MM-YYYY", placeholder="DD-MM-AAAA"),
                    ]),
                    html.Button(
                        "Buscar", id="btn-buscar-dr", n_clicks=0,
                        style={"backgroundColor": AZUL, "color": "white", "border": "none",
                               "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                               "fontSize": "13px"},
                    ),
                ],
            ),
            html.Div(id="tabla-disponible-rotopalas"),
            dcc.Store(id="store-disponible-rotopalas"),
            html.Hr(style={"border": "none", "borderTop": "1px solid #E0E0E0", "margin": "18px 0"}),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(340px, 1fr))",
                       "gap": "24px"},
                children=[
                    html.Details([
                        html.Summary("Editar módulo", style={"fontSize": "14px", "fontWeight": 600,
                                                                 "color": AZUL, "cursor": "pointer"}),
                        html.H4("Actualizar módulo existente",
                               style={"fontSize": "14px", "color": AZUL, "marginBottom": "8px"}),
                        html.P(
                            "Al elegir el registro se precargan sus valores actuales. Solo se "
                            "cambian los campos que modifique; el resto conserva su valor. La "
                            "densidad no se edita a mano: se recalcula sola como TMS / volumen "
                            "(m³ totales) cada vez que guarde.",
                            style={"fontSize": "12px", "color": GRIS, "marginTop": 0},
                        ),
                        html.Div([
                            html.Label("Módulo (busque primero arriba)",
                                       style={"fontSize": "12px", "color": GRIS}),
                            dcc.Dropdown(id="dr-upd-id", placeholder="Seleccione un módulo"),
                        ], style={"marginBottom": "10px"}),
                        _grid_campos_dr("dr-upd", _CAMPOS_DR_UPD[:2]),
                        html.Div(id="dr-upd-densidad-info",
                                style={"fontSize": "12px", "color": AZUL, "marginTop": "8px"}),
                        html.Details([
                            html.Summary("Campos avanzados", style={"cursor": "pointer", "color": AZUL}),
                            _grid_campos_dr("dr-upd", _CAMPOS_DR_UPD[2:]),
                        ], style={"marginTop": "12px", "fontSize": "12px"}),
                        html.Button(
                            "Actualizar", id="btn-dr-actualizar", n_clicks=0,
                            style={"backgroundColor": AMBAR, "color": "white", "border": "none",
                                   "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                                   "fontSize": "13px", "marginTop": "10px"},
                        ),
                        html.Div(id="mensaje-dr-actualizar", style={"fontSize": "13px", "marginTop": "10px"}),
                    ], style={"padding": "16px", "border": "1px solid #DEE6ED", "borderRadius": "8px"}),
                    html.Details([
                        html.Summary("+ Agregar módulo", style={"fontSize": "14px", "fontWeight": 600,
                                                                    "color": AZUL, "cursor": "pointer"}),
                        html.H4("Insertar nuevo registro",
                               style={"fontSize": "14px", "color": AZUL, "marginBottom": "8px"}),
                        html.P(
                            "Se rechaza si ya existe un registro para ese PAD, módulo y campaña "
                            "(use editar en ese caso). Si deja densidad en blanco, se calcula "
                            "como TMS / m³ totales.",
                            style={"fontSize": "12px", "color": GRIS, "marginTop": 0},
                        ),
                        html.Div(
                            style={"display": "grid", "gridTemplateColumns": "1fr 1fr 1fr",
                                   "gap": "10px", "marginBottom": "10px"},
                            children=[
                                html.Div([
                                    html.Label("PAD", style={"fontSize": "12px", "color": GRIS}),
                                    dcc.Dropdown(
                                        id="dr-ins-pad",
                                        options=[{"label": "PAD 1 — Óxidos", "value": 1},
                                                 {"label": "PAD 2 — Sulfuros", "value": 2}],
                                        placeholder="Seleccione",
                                    ),
                                ]),
                                html.Div([
                                    html.Label("Módulo", style={"fontSize": "12px", "color": GRIS}),
                                    dcc.Dropdown(id="dr-ins-modulo", placeholder="Elija PAD primero"),
                                ]),
                                html.Div([
                                    html.Label("Campaña", style={"fontSize": "12px", "color": GRIS}),
                                    dcc.Dropdown(id="dr-ins-campana", placeholder="Seleccione"),
                                ]),
                            ],
                        ),
                        _grid_campos_dr("dr-ins", _CAMPOS_DR[:3]),
                        html.Details([
                            html.Summary("Campos avanzados", style={"cursor": "pointer", "color": AZUL}),
                            _grid_campos_dr("dr-ins", _CAMPOS_DR[3:]),
                        ], style={"marginTop": "12px", "fontSize": "12px"}),
                        html.Button(
                            "Insertar", id="btn-dr-insertar", n_clicks=0,
                            style={"backgroundColor": AZUL, "color": "white", "border": "none",
                                   "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                                   "fontSize": "13px", "marginTop": "10px"},
                        ),
                        html.Div(id="mensaje-dr-insertar", style={"fontSize": "13px", "marginTop": "10px"}),
                    ], style={"padding": "16px", "border": "1px solid #DEE6ED", "borderRadius": "8px"}),
                ],
            ),
        ],
    )


def panel_ajustes():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Ajustes documentados", style=TITULO_SECCION),
            html.P(
                "Los ajustes se registran como propuesta y no modifican los resultados hasta "
                "ser aprobados. El motivo y el antecedente son obligatorios. "
                "Después de la aprobación, reprocesar el período afectado.",
                style=SUBTITULO,
            ),
            html.Div(
                style={"display": "grid",
                       "gridTemplateColumns": "repeat(auto-fit, minmax(210px, 1fr))",
                       "gap": "12px", "marginBottom": "14px"},
                children=[
                    html.Div([
                        html.Label("Fecha de operación", style={"fontSize": "12px", "color": GRIS,
                                                               "display": "block", "marginBottom": "4px"}),
                        dcc.DatePickerSingle(id="aj-fecha", date=_hoy_chile(),
                                             display_format="DD-MM-YYYY", placeholder="DD-MM-AAAA"),
                        html.Div("La fecha del ajuste es independiente del período consultado.",
                                 style={"fontSize": "11px", "color": GRIS, "marginTop": "4px"}),
                    ]),
                    html.Div([
                        html.Label("Módulo", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(id="aj-modulo", placeholder="Seleccione"),
                    ]),
                    html.Div([
                        html.Label("Tipo de ajuste", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(
                            id="aj-tipo",
                            options=[{"label": t.replace("_", " ").title(), "value": t}
                                     for t in ["PISO_ROTOPALA", "EXTRA_PISO_M3",
                                               "EXTRA_TONELAJE_TMS", "TRASPASO_MODULO",
                                               "CORRECCION_VOLUMEN", "CORRECCION_TONELAJE",
                                               "CIERRE_MODULO"]],
                            placeholder="Seleccione",
                        ),
                    ]),
                    html.Div([
                        html.Label("Módulo de destino",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(id="aj-destino", placeholder="Opcional"),
                    ]),
                    html.Div([
                        html.Label("Ajuste de volumen (m³)", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="aj-m3", type="number", style={"width": "100%"}),
                    ]),
                    html.Div([
                        html.Label("Ajuste de tonelaje (TMS)", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="aj-tms", type="number", style={"width": "100%"}),
                    ]),
                    html.Div([
                        html.Label("Tipo de respaldo",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(
                            id="aj-ant-tipo",
                            options=[{"label": {"ACTA_REUNION": "Acta de reunión",
                                                "INFORME_TOPOGRAFIA": "Informe de topografía"}.get(
                                                    t, t.replace("_", " ").title()), "value": t}
                                     for t in ["ACTA_REUNION", "GRABACION", "CORREO",
                                               "INFORME_TOPOGRAFIA", "PLANILLA", "OTRO"]],
                            value="ACTA_REUNION",
                        ),
                    ]),
                    html.Div([
                        html.Label("Referencia / evidencia",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="aj-ant-ref", type="text",
                                  placeholder="ej: grabacion 29-05-2026, 2:20:30",
                                  style={"width": "100%"}),
                    ]),
                ],
            ),
            html.Div([
                html.Label("Motivo", style={"fontSize": "12px", "color": GRIS}),
                dcc.Textarea(id="aj-motivo", style={"width": "100%", "height": "56px"},
                             placeholder="Explique por qué se realiza el ajuste y en qué antecedente se sustenta."),
            ], style={"marginBottom": "12px"}),
            html.Button("Registrar ajuste", id="btn-ajuste", n_clicks=0,
                        style={"backgroundColor": AMBAR, "color": "white", "border": "none",
                               "padding": "9px 22px", "borderRadius": "5px",
                               "cursor": "pointer", "fontSize": "13px"}),
            html.Div(id="mensaje-ajuste",
                     style={"fontSize": "13px", "marginTop": "10px"}),
            html.Hr(style={"border": "none", "borderTop": "1px solid #E0E0E0",
                           "margin": "18px 0"}),
            html.Div(id="tabla-ajustes"),
        ],
    )


def panel_publicacion():
    return html.Div(
        style={**CARD, "borderTop": f"4px solid {ROJO}"},
        children=[
            html.H3("Publicación", style=TITULO_SECCION),
            html.P("Publica el Reclamo ya reprocesado y validado en Datos Conciliados. "
                   "Publicar no recalcula Reclamo. Si hubo cambios de datos, reprocesar antes de publicar.",
                   style=SUBTITULO),
            html.Div([html.Strong("Antes de publicar:"),
                      html.Span("  ✓ período reprocesado   ✓ bloqueos activos resueltos   ✓ vista previa revisada")],
                     style={"fontSize": "12px", "color": AZUL, "marginBottom": "14px"}),
            html.Button(
                "Publicar reclamo conciliado",
                id="btn-publicar",
                n_clicks=0,
                disabled=False,  # Preparado para un bloqueo backend futuro con controles vigentes.
                title="Publica los resultados revisados del período seleccionado.",
                style={"backgroundColor": ROJO, "color": "white", "border": "none",
                       "padding": "11px 20px", "borderRadius": "6px", "cursor": "pointer",
                       "fontSize": "13px", "fontWeight": 600},
            ),
        ],
    )


def layout():
    return html.Div(
    style={"backgroundColor": FONDO, "minHeight": "100vh",
           "fontFamily": "Segoe UI, Arial, sans-serif"},
    children=[
        encabezado(),
        html.Div(
            style={"padding": "22px clamp(14px, 3vw, 34px)", "maxWidth": "1500px", "margin": "0 auto"},
            children=[
                barra_filtros(),
                html.P("Flujo normal: 1. Completar base del módulo si hace falta.  2. Seleccionar período afectado.  "
                       "3. Reprocesar período.  4. Revisar validaciones y vista previa.  5. Publicar cuando corresponda.",
                       style={"fontSize": "12px", "color": AZUL, "margin": "12px 4px"}),
                dcc.Tabs(
                    id="reclamo-main-tabs",
                    value="resumen",
                    colors={"border": "#DCE5EC", "primary": AZUL, "background": "white"},
                    children=[
                        dcc.Tab(label="Resumen", value="resumen", children=html.Div([
                            panel_semaforo(), panel_resumen_general(), panel_cv25(),
                        ], style={"paddingTop": "20px"})),
                        dcc.Tab(label="Reclamo diario", value="diario", children=html.Div([
                            panel_avance(), panel_matriz_mensual(), panel_rendimiento(),
                            panel_preview_conciliados(),
                        ], style={"paddingTop": "20px"})),
                        dcc.Tab(label="Módulos", value="modulos", children=html.Div([
                            panel_automatizacion(),
                            html.H2("Estado de módulos", style={"fontSize": "18px", "color": AZUL,
                                                               "margin": "6px 0 14px"}),
                            panel_cuadratura(), panel_remanente(), panel_disponible_rotopalas(),
                        ], style={"paddingTop": "20px"})),
                        dcc.Tab(label="Ajustes y publicación", value="ajustes", children=html.Div([
                            panel_ajustes(), panel_publicacion(),
                        ], style={"paddingTop": "20px"})),
                    ],
                ),
                html.Div(
                    "Control de Reclamo · Revise las validaciones y la vista previa antes de publicar.",
                    style={"fontSize": "11px", "color": GRIS, "textAlign": "center",
                           "padding": "12px 0 24px"},
                ),
            ],
        ),
    ],
)


# ---------------------------------------------------------------------------
# Utilidades de presentacion
# ---------------------------------------------------------------------------

_MSG_ERROR = "No se pudo completar la operación. Intente de nuevo o contacte a soporte."


def _error_ui(exc: BaseException | None = None, prefijo: str = "Error") -> str:
    """Mensaje seguro para la UI: no expone detalle técnico de SQL/conexión."""
    if exc is not None:
        log.debug("%s: %s", prefijo, exc)
    return _MSG_ERROR


def _layout_base(titulo: str, alto: int = 320) -> dict:
    return dict(
        title=dict(text=titulo, font=dict(size=14, color=AZUL)),
        height=alto,
        margin=dict(l=55, r=25, t=45, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family="Segoe UI, Arial", size=11, color="#333"),
        separators=",.",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )


def _sin_datos(mensaje: str = "Sin datos para el período seleccionado") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=mensaje, showarrow=False,
                       font=dict(size=13, color=GRIS), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_layout(**_layout_base(""), xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    return fig


ETIQUETAS_TABLA = {
    "accion": "Acción", "pad_id": "PAD", "campana": "Campaña",
    "modulo_numero": "Módulo", "detalle": "Detalle",
    "fecha_evento": "Fecha del evento", "fecha_operacion": "Fecha",
    "fuente_reclamo": "Origen", "tms_rotopala_dia": "Rotopala (TMS)",
    "m3_rotopala_dia": "Rotopala (m³)", "m3_camiones_dia": "Camiones (m³)",
    "tms_camiones_dia": "Camiones (TMS)", "flag_calculo": "Estado del cálculo",
    "metodo_calculo": "Método de cálculo", "Total periodo": "Total período",
    "Origen rotopala": "Origen del dato de rotopala",
    "m3_totales": "Volumen base (m³)",
    "m3_camiones_total": "Camiones acumulado (m³)",
    "m3_rotopala_total": "Rotopala acumulado (m³)",
    "porcentaje_extraido": "Extracción (%)",
    "m3_excedente": "Excedente (m³)",
    "tms_excedente": "Excedente (TMS)",
    "modulo_siguiente_propuesto": "Módulo siguiente sugerido",
}

IDS_TECNICOS = {"campana_id", "modulo_id", "id_disponible_rotopalas",
                "secuencia_id", "log_id", "ajuste_id", "Campaña ID", "ID"}


def _numero(valor, decimales=2):
    if pd.isna(valor):
        return "Sin información"
    return f"{float(valor):,.{decimales}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fecha(valor, con_hora=False):
    fecha = pd.to_datetime(valor, errors="coerce")
    return fecha.strftime("%d-%m-%Y %H:%M" if con_hora else "%d-%m-%Y") if pd.notna(fecha) else ""


def _estado(valor):
    return {"PENDIENTE": "Pendiente", "ABIERTO": "Abierto",
            "CERRADO": "Cerrado", "CONGELADO": "Congelado",
            "PROPUESTO": "Propuesto", "RECHAZADO": "Rechazado",
            "APROBADO": "Aprobado"}.get(valor, valor)


def _origen(valor):
    return {"PRELIMINAR_CV25": "Estimación CV25", "TOPOGRAFIA": "Topografía real",
            "SIN_DATO": "Sin información", "AJUSTE_MANUAL": "Ajuste aprobado"}.get(valor, valor)


def _codigo_visible(valor):
    if pd.isna(valor):
        return "Sin información"
    visible = _origen(str(valor))
    return visible if visible != str(valor) else visible.replace("_", " ").capitalize()


def _campana_numero(valor):
    return int(valor) if pd.notna(valor) else "Sin información"


def _matriz_por_campana(sub: pd.DataFrame, campo: str) -> pd.DataFrame:
    """Conserva la identidad de campaña y módulo al pivotar la vista mensual."""
    claves = ["campana_id", "campana", "modulo_id", "modulo_numero"]
    piv = sub.pivot_table(index=claves, columns="dia", values=campo,
                          aggfunc="sum", fill_value=0).reset_index()
    piv = piv.sort_values(["campana", "modulo_numero", "modulo_id"])
    piv = piv.drop(columns=["campana_id", "modulo_id"])
    piv = piv.rename(columns={"campana": "Campaña", "modulo_numero": "Módulo"})
    dias = sorted(col for col in piv.columns if col not in {"Campaña", "Módulo"})
    piv = piv[["Campaña", "Módulo", *dias]]
    piv.insert(2, "Total periodo", piv[dias].sum(axis=1))
    fila_total = {"Campaña": "TOTAL", "Módulo": ""}
    fila_total.update({col: piv[col].sum() for col in ["Total periodo", *dias]})
    piv = pd.concat([piv, pd.DataFrame([fila_total])[piv.columns]], ignore_index=True)
    formato = "%d" if len({(dia.year, dia.month) for dia in dias}) == 1 else "%d-%m"
    return piv.rename(columns={dia: dia.strftime(formato) for dia in dias})

ETIQUETAS_ACCION = {
    "CONGELADO_AUTOMATICO": "Módulo incorporado",
    "ABIERTO_AUTOMATICO": "Módulo habilitado",
    "CERRADO_AUTOMATICO": "Módulo completado",
    "LINEA_BASE_AUTOMATICA": "Base establecida",
    "SECUENCIADO_AUTOMATICO": "Secuencia actualizada",
    "ALERTA_SIN_BASE": "Base pendiente de revisión",
    "ALERTA_FIN_DE_PAD": "Fin de PAD · revisar",
    "ALERTA_FIN_DE_CAMPANA": "Fin de campaña · revisar",
}


def _mostrar_acciones(df: pd.DataFrame) -> pd.DataFrame:
    visible = df.copy()
    visible["accion"] = visible["accion"].map(ETIQUETAS_ACCION).fillna(visible["accion"])
    return visible


def _tabla(df: pd.DataFrame, id_: str, condicionales=None, page_size=None,
           fixed_first=False, hidden_columns=None, tooltip_data=None):
    """
    Renderiza tabla DataTable con soporte para scroll horizontal en pantallas pequeñas.
    Envuelve la tabla en un div con overflow-x: auto cuando el contenido es muy ancho.
    """
    estilo = dict(TABLA_ESTILO)
    if condicionales:
        estilo["style_data_conditional"] = estilo["style_data_conditional"] + condicionales
    if page_size:
        estilo["page_size"] = page_size
    if fixed_first:
        estilo["fixed_columns"] = {"headers": True, "data": 1}
    visible = df.drop(columns=list(IDS_TECNICOS.intersection(df.columns)), errors="ignore").copy()
    for col in visible.columns:
        if col.startswith("fecha_") or col in {"Fecha", "Fecha del evento"}:
            if pd.api.types.is_datetime64_any_dtype(visible[col]) or col.startswith("fecha_"):
                visible[col] = visible[col].map(lambda value: _fecha(value, col in {"fecha_evento", "fecha_solicitud", "fecha_aprobacion"}))
        elif col in {"estado", "estado_secuencia", "Estado"}:
            visible[col] = visible[col].map(_estado)
        elif col in {"fuente_reclamo", "Origen"}:
            visible[col] = visible[col].map(_origen)
        elif col.startswith("flag_") or col in {"metodo_calculo", "tipo_ajuste", "antecedente_tipo"}:
            visible[col] = visible[col].map(_codigo_visible)

    def formato_columna(col):
        precision = 4 if "Densidad" in col else 1 if "%" in col else 2
        return Format(precision=precision, scheme=Scheme.fixed, group=Group.yes,
                      groups=[3], decimal_delimiter=",", group_delimiter=".")

    tabla = dash_table.DataTable(
        id=id_,
        columns=[{"name": ETIQUETAS_TABLA.get(c, c), "id": c,
                  "type": "numeric" if pd.api.types.is_numeric_dtype(visible[c]) else "text",
                  "format": formato_columna(c) if pd.api.types.is_float_dtype(visible[c]) else None}
                 for c in visible.columns],
        data=visible.to_dict("records"),
        tooltip_data=tooltip_data,
        tooltip_duration=None,
        **estilo,
    )

    # Envolver tabla en div con overflow-x: auto para scroll horizontal en tablas anchas
    # Ajustes responsive: min-width garantiza que las columnas tengan espacio mínimo
    # border y border-radius dan apariencia de contenedor
    return html.Div(
        tabla,
        style={
            "overflowX": "auto",
            "overflowY": "visible",
            "borderRadius": "4px",
            "border": "1px solid #E8EAED",
            "minWidth": "100%",  # Asegurar que ocupa todo el ancho disponible
            "WebkitOverflowScrolling": "touch",  # Scroll suave en dispositivos móviles
        }
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("mensaje-accion", "children"),
    Input("btn-recalcular", "n_clicks"),
    State("rango", "start_date"),
    State("rango", "end_date"),
    prevent_initial_call=True,
)
def cb_recalcular(n, desde, hasta):
    try:
        msg = db.recalcular(desde, hasta)
        return html.Span(msg, style={"color": VERDE})
    except Exception as exc:
        log.exception("Error al recalcular")
        return html.Span(_error_ui(exc), style={"color": ROJO})


@callback(
    Output("confirmar-publicar", "displayed"),
    Input("btn-publicar", "n_clicks"),
    prevent_initial_call=True,
)
def cb_pedir_confirmacion_publicar(n):
    return True


@callback(
    Output("mensaje-accion", "children", allow_duplicate=True),
    Input("confirmar-publicar", "submit_n_clicks"),
    State("rango", "start_date"),
    State("rango", "end_date"),
    prevent_initial_call=True,
)
def cb_publicar(n, desde, hasta):
    try:
        msg = db.publicar(desde, hasta)
        return html.Span(msg, style={"color": VERDE, "fontWeight": 600})
    except Exception as exc:
        log.exception("Error al publicar")
        return html.Span(_error_ui(exc, "Error al publicar"), style={"color": ROJO})


@callback(
    Output("resultado-automatizacion", "children"),
    Output("mensaje-accion", "children", allow_duplicate=True),
    Input("btn-automatizacion", "n_clicks"),
    prevent_initial_call=True,
)
def cb_automatizacion(n):
    log.warning("DEBUG_RECLAMO_CLICK n_clicks=%s", n)
    try:
        df = db.mantener_secuencia()
    except Exception as exc:
        log.exception("Error en mantencion automatica de modulos")
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"}), dash.no_update

    if df.empty:
        return (
            html.Div("Sin cambios: nada nuevo que congelar, abrir ni cerrar.",
                     style={"color": VERDE, "fontSize": "13px"}),
            html.Span("Actualización de secuencia ejecutada, sin cambios.", style={"color": VERDE}),
        )

    es_alerta = df["accion"].str.startswith("ALERTA")
    cambios = df[~es_alerta]
    alertas = df[es_alerta]

    cols = ["accion", "pad_id", "campana", "modulo_numero", "detalle"]
    try:
        catalogo = db.campanas_disponible_rotopalas()
        numeros = catalogo.drop_duplicates("campana_id").set_index("campana_id")["campana"]
    except Exception:
        log.exception("No se pudo leer la nomenclatura de campañas")
        numeros = pd.Series(dtype="object")
    cambios = cambios.copy()
    alertas = alertas.copy()
    for parte in (cambios, alertas):
        parte["campana"] = parte["campana_id"].map(numeros)
        parte["campana"] = parte["campana"].map(_campana_numero)
    partes = []

    if not cambios.empty:
        partes.append(html.Div(
            f"{len(cambios)} cambio(s) automatico(s).",
            style={"color": VERDE, "fontSize": "13px", "fontWeight": 600, "padding": "4px 0"}))
        partes.append(_tabla(_mostrar_acciones(cambios[cols]), "t-auto-cambios"))

    if not alertas.empty:
        partes.append(html.Div(
            f"{len(alertas)} caso(s) que requieren revisión.",
            style={"color": ROJO, "fontSize": "13px", "fontWeight": 600, "padding": "10px 0 4px"}))
        partes.append(_tabla(_mostrar_acciones(alertas[cols]), "t-auto-alertas",
                             [{"if": {"row_index": "odd"}, "backgroundColor": "#FDECEA"},
                              {"if": {"row_index": "even"}, "backgroundColor": "#FEF4F3"}]))

    mensaje = f"Actualización de secuencia: {len(cambios)} cambios, {len(alertas)} alertas."
    color = AMBAR if not alertas.empty else VERDE
    return html.Div(partes), html.Span(mensaje, style={"color": color})


@callback(
    Output("alertas-automatizacion", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
)
def cb_alertas_automatizacion(n, _):
    try:
        df = db.alertas_automatizacion()
    except Exception as exc:
        return html.Div(_error_ui(exc, "alertas"),
                        style={"color": ROJO, "fontSize": "12px"})

    if df.empty:
        return html.Div("Sin eventos de alerta registrados en los últimos 30 días.",
                        style={"color": GRIS, "fontSize": "12px"})

    cols = ["accion", "pad_id", "campana", "modulo_numero", "detalle", "fecha_evento"]
    df = df.copy()
    df["campana"] = df["campana"].map(_campana_numero)
    return html.Div([
        html.Div(f"{len(df)} eventos registrados en los últimos 30 días:",
                style={"color": GRIS, "fontSize": "12px", "fontWeight": 600,
                       "padding": "4px 0"}),
        _tabla(_mostrar_acciones(df[cols]), "t-alertas-persistentes"),
    ])


@callback(
    Output("semaforo", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_semaforo(n, _, desde, hasta):
    try:
        df = db.semaforo(desde, hasta)
    except Exception as exc:
        return html.Div(_error_ui(exc, "semaforo"),
                        style={"color": ROJO, "fontSize": "13px"})

    if df.empty:
        return html.Div("Sin controles definidos.", style={"color": GRIS})

    # El orden corresponde a las 14 consultas UNION ALL de db.semaforo.
    # Solo cambia presentación: la severidad SQL y sus recuentos no se alteran.
    alcance = {
        1: "Estado global", 2: "Estado global", 3: "Estado global",
        4: "Estado global", 5: "Estado global", 6: "Estado global",
        7: "Período seleccionado", 8: "Período seleccionado",
        9: "Estado global", 10: "Período seleccionado",
        11: "Período seleccionado", 12: "Últimos 30 días",
        13: "Desde fecha de corte", 14: "Estado global respecto al corte",
    }
    unidades = {
        1: "módulos", 2: "módulos", 3: "grupos rotopala/campaña",
        4: "módulos", 5: "ajustes", 6: "registros de horas",
        7: "combinaciones módulo/día", 8: "días", 9: "ajustes",
        10: "combinaciones campaña/módulo", 11: "eventos",
        12: "eventos registrados", 13: "combinaciones campaña/módulo",
        14: "módulos",
    }

    def tarjeta(row):
        control_original = str(row["control"])
        orden = int(row["orden"])
        es_historial = orden == 12
        control_visible = {
            "Modulos congelados sin secuencia": "Módulos sin secuencia",
            "Cuadratura sobre 100 sin traspaso": "Módulos sobre 100 % sin traspaso",
            "Filas con reclamo preliminar CV25": "Estimaciones CV25 registradas",
            "Brecha CV25 vs topografia sobre 10 pct": "Brecha CV25 vs topografía sobre 10 %",
        }.get(control_original, "Historial de automatización" if es_historial else control_original)
        unidad = unidades.get(orden, "hallazgos")
        if es_historial:
            color, fondo, estado_visible = AZUL, "#EAF2F8", "INFORMACIÓN"
        elif row["resultado"] == "OK":
            color, fondo = VERDE, "#E8F5E9"
            estado_visible = "OK"
        elif row["resultado"] == "NO PUBLICAR":
            color, fondo = ROJO, "#FDECEA"
            estado_visible = "NO PUBLICAR"
        else:
            color, fondo = AMBAR, "#FFF8E1"
            estado_visible = "REVISAR"
        return html.Div(
            style={"backgroundColor": "white", "border": "1px solid #E4EAF0",
                   "borderLeft": f"3px solid {color}",
                   "padding": "12px 14px", "borderRadius": "7px"},
            children=[
                html.Span(estado_visible, style={"display": "inline-block", "fontSize": "10px",
                                                    "fontWeight": 700, "color": color,
                                                    "backgroundColor": fondo, "borderRadius": "12px",
                                                    "padding": "3px 9px", "marginBottom": "7px"}),
                html.Div(control_visible, style={"fontSize": "13px", "color": "#263644"}),
                html.Div(alcance.get(orden, "Alcance no especificado"),
                         style={"fontSize": "10px", "color": GRIS, "marginTop": "4px"}),
                html.Div(f"{int(row['hallazgos'])} {unidad}",
                         style={"fontSize": "14px", "fontWeight": 650, "color": color,
                                "marginTop": "4px"}),
                html.Div("Corresponde a eventos históricos y puede incluir repeticiones o casos ya resueltos.",
                         style={"fontSize": "11px", "color": GRIS, "marginTop": "4px"}) if es_historial else None,
            ],
        )

    def grupo(titulo, sub, vacio):
        return html.Div([
            html.H4(titulo, style={"fontSize": "12px", "letterSpacing": "0.08em",
                                    "color": AZUL, "margin": "16px 0 10px"}),
            html.Div(vacio, style={"fontSize": "12px", "color": GRIS}) if sub.empty else
            html.Div([tarjeta(r) for _, r in sub.iterrows()],
                     style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(240px, 1fr))",
                            "gap": "10px"}),
        ])
    historial = df[df["orden"] == 12]
    vigentes = df[df["orden"] != 12]
    bloqueos = vigentes[vigentes["resultado"] == "NO PUBLICAR"]
    advertencias = vigentes[vigentes["resultado"] == "REVISAR"]
    ok = vigentes[vigentes["resultado"] == "OK"]
    return html.Div([
        grupo("BLOQUEOS", bloqueos, "Sin bloqueos en los controles consultados."),
        grupo("ADVERTENCIAS", advertencias, "Sin advertencias en los controles consultados."),
        grupo("INFORMACIÓN / TRAZABILIDAD", historial, "Sin eventos históricos consultados."),
        html.Details([html.Summary(f"Controles OK ({len(ok)})", style={"color": VERDE,
                                                                       "cursor": "pointer"}),
                      html.Div([tarjeta(r) for _, r in ok.iterrows()],
                               style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(240px, 1fr))",
                                      "gap": "10px", "marginTop": "10px"})],
                     style={"fontSize": "12px", "marginTop": "18px"}),
    ])


@callback(
    Output("resumen-general", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_resumen_general(n, _, desde, hasta):
    try:
        df = db.avance_diario(desde, hasta)
        cv = db.diferencia_cv25(desde, hasta)
        ventanas = {
            pad: db.ventanas_secuencia(pad)
            for pad in (1, 2)
            if not df[(df["pad_id"] == pad) & (df["fuente_reclamo"] == "SIN_DATO")].empty
        }
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    if df.empty:
        return html.Div(
            "Sin datos calculados para el período. Use «Reprocesar período».",
            style={"color": GRIS, "fontSize": "13px"},
        )

    df["tms_camiones_dia"] = df["tms_camiones_dia"].fillna(0)
    df["tms_rotopala_dia"] = df["tms_rotopala_dia"].fillna(0)

    def totales(pad_id):
        sub = df[df["pad_id"] == pad_id]
        camiones = sub["tms_camiones_dia"].sum()
        topo = sub.loc[sub["fuente_reclamo"] == "TOPOGRAFIA", "tms_rotopala_dia"].sum()
        prelim = sub.loc[sub["fuente_reclamo"] == "PRELIMINAR_CV25", "tms_rotopala_dia"].sum()
        ajuste = sub.loc[sub["fuente_reclamo"] == "AJUSTE_MANUAL", "tms_rotopala_dia"].sum()
        sin_dato = _sin_dato_aplicable(
            sub[sub["fuente_reclamo"] == "SIN_DATO"],
            ventanas.get(pad_id, pd.DataFrame()),
        )
        rotopala = topo + prelim + ajuste
        return rotopala, camiones, topo, prelim, ajuste, sin_dato

    r1, c1, topo1, prelim1, aj1, sd1 = totales(1)
    r2, c2, topo2, prelim2, aj2, sd2 = totales(2)
    topo_t, prelim_t, aj_t = topo1 + topo2, prelim1 + prelim2, aj1 + aj2

    def fila(etiqueta, valor, color=GRIS, negrita=False):
        return html.Div(
            [html.Span(etiqueta), html.Span(f"{_numero(valor)} TMS")],
            style={"display": "flex", "justifyContent": "space-between", "gap": "14px",
                   "fontSize": "12px", "color": color, "marginTop": "7px",
                   "fontWeight": 700 if negrita else 400},
        )

    def tarjeta(titulo, rotopala, camiones, topo, prelim, ajuste, sin_dato, color):
        total = rotopala + camiones
        pct_prelim = (prelim * 100.0 / rotopala) if rotopala else 0
        detalle = [
            fila("Rotopala", rotopala, color, True),
            fila("Topografía real", topo, AZUL),
            fila("Estimación CV25",
                 prelim, AMBAR if pct_prelim > 20 else GRIS),
        ]
        if ajuste:
            detalle.append(fila("Ajustes", ajuste, GRIS))
        detalle.append(fila("Camiones", camiones, color, True))
        if sin_dato:
            detalle.append(html.Div(
                f"{sin_dato} combinaciones módulo/día aplicables sin información disponible.",
                style={"fontSize": "11px", "color": GRIS, "marginTop": "8px"}))
        return html.Div(
            style={"backgroundColor": "white", "borderTop": f"3px solid {color}",
                   "borderRadius": "6px", "padding": "12px 16px", "flex": "1",
                   "minWidth": "260px"},
            children=[
                html.Div(titulo, style={"fontSize": "12px", "color": GRIS, "fontWeight": 600}),
                html.Div(f"{_numero(total)} TMS",
                         style={"fontSize": "22px", "fontWeight": 700, "color": color,
                                "marginTop": "2px"}),
                html.Div("(rotopala + camiones)",
                         style={"fontSize": "10px", "color": GRIS, "marginBottom": "4px"}),
                *detalle,
            ],
        )

    tarjetas = html.Div(
        style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
        children=[
            tarjeta("PAD 1 — Óxidos", r1, c1, topo1, prelim1, aj1, sd1, AZUL),
            tarjeta("PAD 2 — Sulfuros", r2, c2, topo2, prelim2, aj2, sd2, AMBAR),
            tarjeta("Planta — total", r1 + r2, c1 + c2, topo_t, prelim_t, aj_t,
                    sd1 + sd2, VERDE),
        ],
    )

    nota_cv25 = None
    comparables = cv[cv["tms_topografia"].notna() & cv["tms_cv25"].notna()]
    if not comparables.empty:
        cv25_periodo = comparables["tms_cv25"].sum()
        topo_periodo = comparables["tms_topografia"].sum()
        if cv25_periodo:
            dif_pct = (topo_periodo - cv25_periodo) * 100.0 / cv25_periodo
            color = AMBAR if abs(dif_pct) > 10 else VERDE
            nota_cv25 = html.Div(
                [
                    html.B("Brecha acumulada del período: "),
                    html.Span(f"{'+' if dif_pct >= 0 else '-'}{_numero(abs(dif_pct), 1)} %",
                              style={"color": color, "fontWeight": 700}),
                    html.Span(f" · Topografía real {_numero(topo_periodo)} TMS · CV25 {_numero(cv25_periodo)} TMS"),
                ],
                style={"fontSize": "12px", "marginTop": "14px", "padding": "12px 14px",
                       "backgroundColor": "#F3F7FA", "borderRadius": "7px", "lineHeight": "1.6"},
            )

    return html.Div([tarjetas, nota_cv25] if nota_cv25 is not None else [tarjetas])


@callback(
    Output("matriz-mensual", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("matriz-metrica", "value"),
    Input("matriz-pad-tabs", "value"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_matriz_mensual(n, _, metrica, pad_tab, desde, hasta):
    try:
        df = db.avance_diario(desde, hasta)
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    pad_id = int(pad_tab)
    sub = df[df["pad_id"] == pad_id].copy()
    if sub.empty:
        return html.Div("Sin datos calculados para este PAD en el período.",
                        style={"color": GRIS, "fontSize": "13px", "padding": "10px 0"})

    sub["dia"] = pd.to_datetime(sub["fecha_operacion"]).dt.normalize()
    sub["tms_camiones_dia"] = sub["tms_camiones_dia"].fillna(0)
    sub["tms_rotopala_dia"] = sub["tms_rotopala_dia"].fillna(0)
    sub["tms_total_dia"] = sub["tms_camiones_dia"] + sub["tms_rotopala_dia"]

    campo = {"rotopala": "tms_rotopala_dia", "camiones": "tms_camiones_dia",
             "total": "tms_total_dia"}[metrica]

    piv = _matriz_por_campana(sub, campo)
    total_periodo = piv.loc[piv["Campaña"] != "TOTAL", "Total periodo"].sum()

    cond_total = [
        {"if": {"filter_query": '{Campaña} = "TOTAL"'},
         "fontWeight": "700", "borderTop": f"2px solid {AZUL}", "backgroundColor": "#EAF2F8"},
        {"if": {"column_id": "Total periodo"},
         "fontWeight": "700", "backgroundColor": "#EDF4F8"},
    ]

    return html.Div([
        html.Div(f"Total del PAD en el período ({'Total' if metrica == 'total' else metrica.title()}): {_numero(total_periodo)} TMS",
                style={"fontSize": "13px", "fontWeight": 600, "color": GRIS,
                       "padding": "4px 0 8px"}),
        _tabla(piv.round(1), f"t-matriz-{pad_id}-{metrica}", cond_total, fixed_first=True),
    ])


@callback(
    Output("tabla-remanente", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("remanente-pad-tabs", "value"),
)
def cb_remanente(n, _, pad_tab):
    try:
        df = db.cuadratura()
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    pad_id = int(pad_tab)
    sub = df[df["pad_id"] == pad_id].copy()
    if sub.empty:
        return html.Div("Sin módulos incorporados en este PAD.",
                        style={"color": GRIS, "fontSize": "13px"})

    sub = sub.sort_values(["campana", "modulo_numero"])
    cols = ["modulo_numero", "campana", "estado_secuencia", "tms_conformado",
            "tms_extraido_total", "tms_saldo_disponible", "porcentaje_extraido",
            "flag_cuadratura"]
    ren = {"modulo_numero": "Módulo", "campana": "Campaña", "estado_secuencia": "Estado",
           "tms_conformado": "TMS base", "tms_extraido_total": "TMS extraído",
           "tms_saldo_disponible": "TMS remanente", "porcentaje_extraido": "% extraído",
           "flag_cuadratura": "Estado cuadratura"}
    tabla = sub[cols].rename(columns=ren).round(1)
    tooltip_remanente = []
    for valor in tabla["TMS remanente"]:
        tooltip_remanente.append({"TMS remanente": {
            "value": f"Valor técnico: {_numero(valor, 1)} TMS" if pd.notna(valor) else "Sin información",
            "type": "text",
        }})
    tabla["TMS remanente"] = tabla["TMS remanente"].map(
        lambda valor: (f"Excedente: {_numero(abs(valor), 1)} TMS" if valor < 0 else f"{_numero(valor, 1)} TMS")
        if pd.notna(valor) else "Sin información"
    )
    tabla["Estado cuadratura"] = tabla["Estado cuadratura"].replace({
        "SOBRE_100_PROPONER_TRASPASO": "Sobre 100 % · requiere traspaso",
        "MODULO_PRACTICAMENTE_AGOTADO": "Próximo a completar",
    })

    cond = [
        {"if": {"filter_query": '{Estado cuadratura} = "Sobre 100 % · requiere traspaso"'},
         "backgroundColor": "#FDECEA", "color": ROJO},
        {"if": {"filter_query": '{Estado cuadratura} = "Próximo a completar"'},
         "backgroundColor": "#FFF8E1"},
        {"if": {"filter_query": '{Estado} = "Abierto"'}, "fontWeight": "600"},
    ]

    total_remanente = sub["tms_saldo_disponible"].sum()
    return html.Div([
        html.Div(f"Remanente total del PAD: {_numero(total_remanente)} TMS",
                style={"fontSize": "13px", "fontWeight": 600, "color": GRIS,
                       "padding": "4px 0 8px"}),
        _tabla(tabla, f"t-remanente-{pad_id}", cond, tooltip_data=tooltip_remanente),
    ])


@callback(
    Output("tabla-preview-conciliados", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("preview-pad-tabs", "value"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_preview_conciliados(n, _, pad_tab, desde, hasta):
    try:
        df = db.avance_diario(desde, hasta)
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    if df.empty:
        return html.Div(
            "Sin datos calculados para el período. Use «Reprocesar período».",
            style={"color": GRIS, "fontSize": "13px"},
        )

    pad = int(pad_tab)
    sub = df[df["pad_id"] == pad].copy()
    if sub.empty:
        return html.Div("Sin datos calculados para este PAD en el período.",
                        style={"color": GRIS, "fontSize": "13px"})

    sub["tms_camiones_dia"]  = sub["tms_camiones_dia"].fillna(0)
    sub["tms_rotopala_dia"]  = sub["tms_rotopala_dia"].fillna(0)
    sub["fecha_operacion"]   = pd.to_datetime(sub["fecha_operacion"])
    sub = sub.sort_values("fecha_operacion")

    # Piso de secuencia: una vez que el modulo "protagonista" de un dia
    # alcanza un numero de modulo, un dia posterior no puede volver a
    # mostrar un modulo MENOR de la misma campaña -- solo una lectura
    # residual minima (caso confirmado PAD1 dia 11: modulo 37 con 0,1 TMS,
    # ya al 99,8 %, tapando al 38 que seguia activo al 11,2 % sin lectura
    # ese dia puntual). El piso se reinicia si cambia la campaña, porque
    # ahi la numeracion de modulos vuelve a partir de otro punto.
    piso_modulo = None
    piso_campana = None
    ultimo_modulo_activo = None
    ultimo_avance_pct = None
    ultima_campana_activa = None

    filas = []
    for fecha, grupo in sub.groupby("fecha_operacion"):
        tms_rotopala = float(grupo["tms_rotopala_dia"].sum())
        tms_camiones = float(grupo["tms_camiones_dia"].sum())

        # Entre los modulos con tonelaje ese dia, el protagonista real es el
        # que TODAVIA se esta llenando -- el de MENOR avance acumulado, no
        # el de mayor TMS (evita que un arrastre de linea base recien
        # establecida, con avance ya alto, tape al modulo realmente activo).
        activos = grupo[(grupo["tms_rotopala_dia"] > 0)
                        & (grupo["fuente_reclamo"] != "SIN_DATO")
                        & grupo["avance_roto_pct"].notna()].copy()
        if activos.empty:
            for fuente_cero in ("TOPOGRAFIA", "PRELIMINAR_CV25"):
                activos = grupo[(grupo["fuente_reclamo"] == fuente_cero)
                                & (grupo["tms_rotopala_dia"] == 0)
                                & grupo["avance_roto_pct"].notna()].copy()
                if not activos.empty:
                    break
        if piso_campana is not None:
            misma_campana = activos["campana_id"] == piso_campana
            activos = activos[~misma_campana | (activos["modulo_numero"] >= piso_modulo)]

        if not activos.empty:
            fila_activa = activos.loc[activos["avance_roto_pct"].idxmin()]
            modulo_activo = int(fila_activa["modulo_numero"])
            avance_pct = float(fila_activa["avance_roto_pct"]) * 100
            fuente = fila_activa["fuente_reclamo"]
            campana_activa = fila_activa["campana_id"]
            campana_visible = _campana_numero(fila_activa["campana"])

            if piso_campana is None or campana_activa != piso_campana:
                piso_campana = campana_activa
                piso_modulo = modulo_activo
            elif modulo_activo > piso_modulo:
                piso_modulo = modulo_activo

            ultimo_modulo_activo, ultimo_avance_pct = modulo_activo, avance_pct
            ultima_campana_activa = campana_visible
        elif ultimo_modulo_activo is not None and tms_rotopala > 0:
            # Hubo tonelaje real ese dia, pero solo en un modulo ya
            # superado (residual): se mantiene el ultimo modulo protagonista
            # conocido en vez de retroceder. El tonelaje real del dia se
            # sigue sumando arriba, esto solo afecta la columna informativa.
            modulo_activo, avance_pct = ultimo_modulo_activo, ultimo_avance_pct
            campana_visible = ultima_campana_activa
            fuente = next((valor for valor in ("TOPOGRAFIA", "PRELIMINAR_CV25", "AJUSTE_MANUAL")
                           if valor in set(grupo["fuente_reclamo"])), None)
        else:
            modulo_activo, avance_pct = None, None
            fuente = next((valor for valor in ("TOPOGRAFIA", "PRELIMINAR_CV25", "AJUSTE_MANUAL")
                           if valor in set(grupo["fuente_reclamo"])), None)
            campana_visible = ""

        # Se proyecta por CV25 UNICAMENTE los dias sin medicion real de
        # topografia -- marcarlo explicito, no dejarlo como un dato mas.
        if fuente == "PRELIMINAR_CV25":
            origen = "Estimación CV25"
        elif fuente == "TOPOGRAFIA":
            origen = "Topografía real"
        else:
            origen = {"AJUSTE_MANUAL": "Ajuste aprobado"}.get(fuente, fuente) if fuente else "Sin información"

        filas.append({
            "Fecha": fecha.strftime("%d-%m-%Y"),
            "Rotopala (TMS)": round(tms_rotopala, 1),
            "Camiones (TMS)": round(tms_camiones, 1),
            "Total (TMS)": round(tms_rotopala + tms_camiones, 1),
            "Campaña": campana_visible,
            "Módulo mayor avance": modulo_activo if modulo_activo is not None else "",
            "% avance módulo": "" if avance_pct is None else f"{_numero(avance_pct, 1)} %",
            "Origen rotopala": origen,
        })

    tabla = pd.DataFrame(filas).reset_index(drop=True)

    cond = [
        {"if": {"filter_query": '{Origen rotopala} = "Estimación CV25"'},
         "backgroundColor": "#FFF8E1", "color": "#8A6D00", "fontWeight": 600},
        {"if": {"filter_query": '{Origen rotopala} = "Sin información"'},
         "color": GRIS},
    ]

    return html.Div([
        html.Div(
            "Ámbar: estimación CV25 en un día sin medición topográfica. "
            "Sin resaltado: topografía real.",
            style={"fontSize": "12px", "color": GRIS, "padding": "0 0 8px"},
        ),
        _tabla(tabla, f"t-preview-conciliados-{pad}", cond, page_size=31),
    ])


@callback(
    Output("g-cv25", "figure"),
    Output("g-brecha", "figure"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_cv25(n, _, desde, hasta):
    try:
        df = db.diferencia_cv25(desde, hasta)
    except Exception as exc:
        return _sin_datos(_error_ui(exc)), _sin_datos("")

    if df.empty:
        return _sin_datos(), _sin_datos()

    f1 = go.Figure()
    f1.add_trace(go.Bar(x=df["fecha"], y=df["tms_cv25"], name="CV25",
                        marker_color="#9DC3E6"))
    f1.add_trace(go.Scatter(x=df["fecha"], y=df["tms_topografia"], name="Topografía real",
                            mode="lines+markers", line=dict(color=AZUL, width=2.5)))
    if df["tms_preliminar"].fillna(0).sum() > 0:
        f1.add_trace(go.Bar(x=df["fecha"], y=df["tms_preliminar"],
                            name="Estimación CV25", marker_color=AMBAR, opacity=0.75))
    f1.update_layout(**_layout_base("Tonelaje diario por fuente", 330),
                     barmode="overlay",
                     yaxis_title="TMS", xaxis_title=None)
    f1.update_xaxes(showgrid=False)
    f1.update_yaxes(gridcolor="#EEE")

    f2 = go.Figure()
    colores = [AMBAR if abs(v or 0) > 10 else VERDE for v in df["diferencia_pct"]]
    f2.add_trace(go.Bar(x=df["fecha"], y=df["diferencia_pct"], marker_color=colores,
                        name="Brecha %"))
    f2.add_hline(y=10, line_dash="dot", line_color=GRIS)
    f2.add_hline(y=-10, line_dash="dot", line_color=GRIS)
    f2.update_layout(**_layout_base("Brecha diaria: (topografía real - CV25) / CV25", 250),
                     yaxis_title="%", showlegend=False)
    f2.update_xaxes(showgrid=False)
    f2.update_yaxes(gridcolor="#EEE", zerolinecolor="#CCC")

    return f1, f2


@callback(
    Output("g-rendimiento", "figure"),
    Output("g-horas", "figure"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("rendimiento-rotopala-tabs", "value"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_rendimiento(n, _, rotopala_tab, desde, hasta):
    try:
        df = db.rendimiento(desde, hasta)
    except Exception as exc:
        return _sin_datos(_error_ui(exc)), _sin_datos("")

    if df.empty:
        return _sin_datos(), _sin_datos()

    rid = int(rotopala_tab)
    df = df[df["rotopala_id"] == rid]
    color = AZUL if rid == 1 else "#E07B39"

    if df.empty:
        return (_sin_datos(f"Sin datos para rotopala {rid} en el período"),
                _sin_datos(""))

    f1 = go.Figure()
    con_corriente = df["corriente_no_null"].fillna(0) > 0
    sin_corriente = df[~con_corriente]
    cero_confirmado = df[con_corriente & (df["horas_operacion"] == 0)]
    f1.add_trace(go.Scatter(x=df["fecha"],
                            y=df["rendimiento_pesometro_tms_hr"].where(con_corriente),
                            name="CV25", mode="lines+markers",
                            line=dict(color=color, width=2)))
    topo_visible = df["rendimiento_topografia_tms_hr"].where(df["tiene_topografia_real"] == 1)
    f1.add_trace(go.Scatter(x=df["fecha"], y=topo_visible,
                            name="Topografía real (días con medición)", mode="lines+markers",
                            line=dict(color=color, width=2, dash="dot"),
                            marker=dict(size=5, symbol="circle-open")))
    f1.add_hrect(y0=1500, y1=4500, fillcolor=VERDE, opacity=0.06, line_width=0)
    f1.update_layout(**_layout_base(f"Rotopala {rid} — tasa horaria de tonelaje "
                                    "(banda de referencia 1.500 a 4.500)", 330),
                     yaxis_title="TMS / hora")
    f1.update_xaxes(showgrid=False)
    f1.update_yaxes(gridcolor="#EEE")

    f2 = go.Figure()
    f2.add_trace(go.Bar(x=df["fecha"], y=df["horas_operacion"].where(con_corriente),
                        name=f"Rotopala {rid}", marker_color=color,
                        hovertemplate="%{x|%d-%m-%Y}<br>Horas: %{y:.1f}<extra></extra>"))
    if not cero_confirmado.empty:
        f2.add_trace(go.Scatter(
            x=cero_confirmado["fecha"], y=[0] * len(cero_confirmado), mode="markers",
            name="0 horas con corriente disponible",
            marker=dict(symbol="circle-open", size=9, color=color),
            hovertemplate="%{x|%d-%m-%Y}<br>0 horas · corriente disponible<extra></extra>",
        ))
    f2.update_layout(**_layout_base(f"Rotopala {rid} — horas de operación por día", 250),
                     yaxis_title="horas", showlegend=not cero_confirmado.empty)
    if not sin_corriente.empty:
        fechas = pd.to_datetime(sin_corriente["fecha"])
        rango = (_fecha(fechas.min()) if len(fechas) == 1 else
                 f"{_fecha(fechas.min())} a {_fecha(fechas.max())}")
        f2.add_annotation(
            x=0, y=1.08, xref="paper", yref="paper", showarrow=False,
            xanchor="left", text=f"Sin cobertura de corriente: {rango}",
            font=dict(size=11, color=GRIS),
        )
    f2.update_xaxes(showgrid=False)
    f2.update_yaxes(gridcolor="#EEE")

    return f1, f2


@callback(
    Output("g-cuadratura", "figure"),
    Output("tabla-cuadratura", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("cuadratura-pad-tabs", "value"),
)
def cb_cuadratura(n, _, pad_tab):
    try:
        df = db.cuadratura()
    except Exception as exc:
        return _sin_datos(_error_ui(exc)), None

    if df.empty:
        return _sin_datos("Sin módulos incorporados"), None

    pad = int(pad_tab)
    df = df[df["pad_id"] == pad]
    if df.empty:
        return _sin_datos("Sin módulos incorporados en este PAD"), None

    df = df.sort_values(["campana", "modulo_numero"])
    top = df.head(40)
    etiquetas = [f"C{int(c)} · M{int(m)}" if pd.notna(c) and pd.notna(m) else "?"
                 for c, m in zip(top["campana"], top["modulo_numero"])]
    hover_data = [
        (etiqueta, _numero(total, 2),
         "sin dato" if pd.isna(inicio) else _fecha(inicio),
         "sin dato" if pd.isna(fin) else _fecha(fin),
         _numero(roto, 3), _numero(camiones, 3))
        for etiqueta, total, inicio, fin, roto, camiones in zip(
            etiquetas, top["m3_totales"], top["fecha_inicio_movimiento"],
            top["fecha_fin_movimiento"], top["m3_rotopala_total"],
            top["m3_camiones_total"])
    ]
    hover = ("%{customdata[0]}<br>"
             "Volumen congelado: %{customdata[1]} m³<br>"
             "Fecha inicio: %{customdata[2]}<br>"
             "Fecha fin: %{customdata[3]}<br>"
             "Rotopala: %{customdata[4]} m³<br>"
             "Camiones: %{customdata[5]} m³<extra></extra>")

    f = go.Figure()
    f.add_trace(go.Bar(
        x=etiquetas,
        y=top["m3_camiones_total"], name="Camiones", marker_color="#E07B39",
        customdata=hover_data, hovertemplate=hover))
    f.add_trace(go.Bar(
        x=etiquetas,
        y=top["m3_rotopala_total"], name="Rotopala", marker_color=AZUL,
        customdata=hover_data, hovertemplate=hover))
    f.add_trace(go.Scatter(
        x=etiquetas,
        y=top["m3_totales"], name="Volumen congelado", mode="lines+markers",
        line=dict(color=ROJO, width=2, dash="dash"),
        customdata=hover_data, hovertemplate=hover))
    layout = _layout_base("Extracción acumulada y volumen base por módulo", 360)
    layout["hovermode"] = "closest"
    f.update_layout(**layout, barmode="stack", yaxis_title="m3")
    f.update_xaxes(showgrid=False)
    f.update_yaxes(gridcolor="#EEE")

    alerta = df[df["flag_cuadratura"] == "SOBRE_100_PROPONER_TRASPASO"]
    if alerta.empty:
        tabla = html.Div("Ningún módulo supera el 100 % de extracción.",
                         style={"color": VERDE, "fontSize": "13px", "padding": "10px 0"})
    else:
        cols = ["campana", "modulo_numero", "m3_totales", "m3_camiones_total", "m3_rotopala_total",
                "porcentaje_extraido", "m3_excedente", "tms_excedente",
                "modulo_siguiente_propuesto"]
        tabla = html.Div([
            html.Div(
                f"{len(alerta)} módulo(s) sobre 100 %. Cada uno requiere un ajuste "
                f"de traspaso de módulo documentado antes de publicar.",
                style={"color": ROJO, "fontSize": "13px", "fontWeight": 600,
                       "padding": "10px 0 6px"},
            ),
            _tabla(alerta[cols].round(2), "t-cuad"),
        ])

    return f, tabla


@callback(
    Output("cuadratura-modulo-select", "options"),
    Output("cuadratura-modulo-select", "value"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("cuadratura-pad-tabs", "value"),
)
def cb_opciones_cuadratura_modulo(n, _, pad_tab):
    try:
        df = db.cuadratura()
    except Exception:
        return [], None

    pad = int(pad_tab)
    sub = df[df["pad_id"] == pad].sort_values("modulo_numero")
    opciones = [
        {"label": f"Módulo {int(r.modulo_numero)} · Campaña {_campana_numero(r.campana)}"
                  f"{' · ' + _estado(r.estado_secuencia) if pd.notna(r.estado_secuencia) else ''}",
         "value": f"{int(r.campana_id)}:{int(r.modulo_id)}"}
        for r in sub.itertuples()
    ]
    return opciones, None


@callback(
    Output("detalle-cuadratura-modulo", "children"),
    Input("cuadratura-modulo-select", "value"),
)
def cb_detalle_cuadratura_modulo(seleccion):
    if not seleccion:
        return None

    campana_id, modulo_id = (int(x) for x in seleccion.split(":"))
    try:
        cuad = db.cuadratura()
        hist = db.historial_modulo(campana_id, modulo_id)
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    fila_cuad = cuad[(cuad["campana_id"] == campana_id) & (cuad["modulo_id"] == modulo_id)]
    resumen = None
    if not fila_cuad.empty:
        r = fila_cuad.iloc[0]
        resumen = html.Div(
            [
                html.Span(f"Módulo {int(r['modulo_numero'])} — Campaña {_campana_numero(r['campana'])}: ",
                          style={"fontWeight": 600}),
                f"volumen base {_numero(r['m3_totales'])} m³ "
                f"({_numero(r['tms_conformado'])} TMS, densidad {_numero(r['densidad_oficial'], 4)} t/m³) · "
                f"extraído {_numero(r['m3_extraido_total'])} m³ ({_numero(r['porcentaje_extraido'], 1)} %) · "
                f"remanente {_numero(r['tms_saldo_disponible'])} TMS · "
                f"estado {_estado(r['estado_secuencia'])}",
            ],
            style={"fontSize": "13px", "color": GRIS, "marginBottom": "10px",
                   "padding": "8px 10px", "backgroundColor": "#F2F7FB", "borderRadius": "5px"},
        )

    if hist.empty:
        tabla = html.Div(
            "Este módulo aún no tiene historial diario. "
            "Use «Reprocesar período» para el período que corresponda.",
            style={"color": GRIS, "fontSize": "13px"},
        )
    else:
        cols = ["fecha_operacion", "m3_rotopala_dia", "tms_rotopala_dia",
                "m3_camiones_dia", "tms_camiones_dia", "avance_total_pct",
                "ajuste_tms", "fuente_reclamo", "metodo_calculo", "flag_calculo"]
        cond = [
            {"if": {"filter_query": '{fuente_reclamo} = "Estimación CV25"'},
             "backgroundColor": "#FFF8E1"},
            {"if": {"filter_query": '{flag_calculo} contains "Revisar"'},
             "backgroundColor": "#FDECEA", "color": ROJO},
        ]
        tabla = html.Div([
            html.Div(f"Historial diario completo ({len(hist)} fila(s)), "
                    "todo el rango disponible, no solo el periodo filtrado arriba:",
                    style={"fontSize": "12px", "color": GRIS, "padding": "4px 0 8px"}),
            _tabla(hist[cols].round(2), f"t-detalle-{campana_id}-{modulo_id}"),
        ])

    return html.Div([resumen, tabla] if resumen is not None else [tabla])


def _sin_dato_aplicable(filas: pd.DataFrame, ventanas: pd.DataFrame) -> int:
    """Cuenta solo módulo/día SIN_DATO dentro de una secuencia operacional."""
    if filas.empty or ventanas.empty:
        return 0
    cruces = filas.merge(
        ventanas.rename(columns={"rotopala_id": "rotopala_secuencia"}),
        on=["campana_id", "modulo_id"], how="left", validate="many_to_one",
    )
    fecha = pd.to_datetime(cruces["fecha_operacion"])
    apertura = pd.to_datetime(cruces["fecha_apertura"])
    cierre = pd.to_datetime(cruces["fecha_cierre"])
    aplicable = (
        cruces["rotopala_secuencia"].notna()
        & ((cruces["estado_secuencia"] == "ABIERTO") | apertura.notna())
        & (apertura.isna() | (fecha >= apertura))
        & (cierre.isna() | (fecha <= cierre))
    )
    return len(cruces.loc[aplicable, ["campana_id", "modulo_id", "fecha_operacion"]].drop_duplicates())


def _motivo_sin_proyeccion(fecha, cv, rotopala_id):
    """Explica la ausencia sin inferir operacion a partir de un cero SQL."""
    if fecha.date() >= _hoy_chile():
        return "DIA_NO_CERRADO"
    if cv is None or cv["flag_preliminar"] == "SIN_CV25":
        return "SIN_CV025"
    cobertura = cv[f"horas_con_dato_r{rotopala_id}"]
    motivos = []
    if pd.isna(cv["tms_dia"]):
        motivos.append("SIN_RESOLVER_CV25")
    if pd.isna(cobertura) or cobertura == 0:
        motivos.append("SIN_COBERTURA")
    if motivos:
        return " / ".join(motivos)
    if pd.isna(cv[f"tms_estimado_r{rotopala_id}"]):
        return "SIN_HORAS_NO_REPARTIBLE"
    return "SIN_MODULO_ELEGIBLE"


@callback(
    Output("g-avance", "figure"),
    Output("tabla-avance", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-accion", "children"),
    Input("avance-pad-tabs", "value"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_avance(n, _, pad_tab, desde, hasta):
    pad = int(pad_tab)
    try:
        df = db.avance_diario(desde, hasta)
        estado = db.estado_proyeccion(pad, hasta)
        cv_dias = db.estado_cv25(desde, hasta)
        df = df[df["pad_id"] == pad]
        sin_dato_filas = df[df["fuente_reclamo"] == "SIN_DATO"]
        ventanas = db.ventanas_secuencia(pad) if not sin_dato_filas.empty else pd.DataFrame()
    except Exception as exc:
        return _sin_datos(_error_ui(exc)), None

    mensajes = []
    fecha_hasta = pd.to_datetime(hasta, errors="coerce")
    if not estado.empty:
        topografias = pd.to_datetime(estado["ultima_topografia"].dropna())
        ultima_topografia = topografias.min() if not topografias.empty else pd.NaT
        if pd.notna(ultima_topografia):
            mensajes.append(html.Div(
                f"Topografía disponible hasta {_fecha(ultima_topografia)}.",
                style={"color": GRIS, "fontSize": "13px", "padding": "10px 0 6px"},
            ))
        prelim_vigente = estado[estado["fecha_preliminar"].notna()]
        if not prelim_vigente.empty:
            fechas_prelim = pd.to_datetime(prelim_vigente["fecha_preliminar"])
            mensajes.append(html.Div(
                f"Proyección vigente para {_fecha(fechas_prelim.max())}.",
                style={"color": AMBAR, "fontSize": "13px", "padding": "4px 0"},
            ))
            if prelim_vigente["tms_preliminar_dia"].notna().all() and (prelim_vigente["tms_preliminar_dia"] == 0).all():
                mensajes.append(html.Div(
                    "Proyección CV25: 0 TMS — sin operación detectada.",
                    style={"color": AMBAR, "fontSize": "13px", "padding": "4px 0"},
                ))
        if pd.notna(fecha_hasta):
            inicio = pd.to_datetime(desde).normalize()
            if pd.notna(ultima_topografia):
                inicio = max(inicio, ultima_topografia.normalize() + pd.Timedelta(days=1))
            cv_por_fecha = {pd.Timestamp(r["fecha"]).normalize(): r
                            for _, r in cv_dias.iterrows()}
            dias_con_fuente = set(pd.to_datetime(
                df.loc[df["fuente_reclamo"].isin(["TOPOGRAFIA", "PRELIMINAR_CV25"]),
                       "fecha_operacion"]).dt.normalize())
            for fecha in pd.date_range(inicio, fecha_hasta.normalize()):
                if fecha in dias_con_fuente:
                    continue
                motivo = _motivo_sin_proyeccion(fecha, cv_por_fecha.get(fecha), pad)
                mensajes.append(html.Div(
                    f"{_fecha(fecha)} · Sin proyección: {motivo}.",
                    style={"color": AMBAR, "fontSize": "13px", "padding": "4px 0"},
                ))

    if df.empty:
        return _sin_datos("Sin datos para este PAD en el período"), html.Div(mensajes)

    agg = (df.groupby(["fecha_operacion", "fuente_reclamo"], as_index=False)
             .agg(tms=("tms_rotopala_dia", "sum")))

    colores = {"TOPOGRAFIA": AZUL, "PRELIMINAR_CV25": AMBAR,
               "AJUSTE_MANUAL": "#7B5EA7", "SIN_DATO": "#CCCCCC"}

    f = go.Figure()
    for fuente in ["TOPOGRAFIA", "PRELIMINAR_CV25", "AJUSTE_MANUAL", "SIN_DATO"]:
        sub = agg[agg["fuente_reclamo"] == fuente]
        if not sub.empty:
            visible_name = {"TOPOGRAFIA": "Topografía real", "PRELIMINAR_CV25": "Estimación CV25",
                            "AJUSTE_MANUAL": "Ajuste", "SIN_DATO": "Sin información"}[fuente]
            f.add_trace(go.Bar(x=sub["fecha_operacion"], y=sub["tms"], name=visible_name,
                               marker_color=colores[fuente],
                               hovertemplate=f"%{{x|%d-%m-%Y}}<br>Origen: {visible_name}"
                                             "<br>Tonelaje: %{y:.2f} TMS<extra></extra>"))
            if fuente == "TOPOGRAFIA":
                ceros = sub[sub["tms"] == 0]
                if not ceros.empty:
                    f.add_trace(go.Scatter(
                        x=ceros["fecha_operacion"], y=ceros["tms"], mode="markers",
                        name="Topografía real (0 TMS)", showlegend=False,
                        marker=dict(symbol="circle-open", size=9, color=AZUL),
                        hovertemplate="%{x|%d-%m-%Y}<br>Origen: Topografía real"
                                      "<br>Tonelaje: 0,00 TMS<extra></extra>",
                    ))
    f.update_layout(**_layout_base(f"PAD {pad} — tonelaje reclamado por rotopala, "
                                   "segun fuente del dato", 330),
                    barmode="stack", yaxis_title="TMS")
    f.update_xaxes(showgrid=False)
    f.update_yaxes(gridcolor="#EEE")

    fuentes = df["fuente_reclamo"]
    prelim = df[fuentes == "PRELIMINAR_CV25"]
    sin_dato = _sin_dato_aplicable(sin_dato_filas, ventanas)
    ajustes = int((fuentes == "AJUSTE_MANUAL").sum())
    if not prelim.empty:
        mensajes.append(html.Div(
            f"{len(prelim)} combinaciones módulo/día con estimación CV25. "
            "Se actualizan al incorporar topografía y reprocesar el período.",
            style={"color": AMBAR, "fontSize": "13px", "fontWeight": 600,
                   "padding": "10px 0 6px"},
        ))
    if sin_dato:
        mensajes.append(html.Div(
            f"{sin_dato} combinación(es) módulo/día aplicables sin respaldo "
            "topográfico ni proyección CV25.",
            style={"color": AMBAR, "fontSize": "13px", "fontWeight": 600,
                   "padding": "10px 0 6px"},
        ))
    if ajustes:
        mensajes.append(html.Div(
            f"{ajustes} fila(s) con ajuste manual aprobado.",
            style={"color": GRIS, "fontSize": "13px", "padding": "10px 0 6px"},
        ))
    if not mensajes:
        mensajes.append(html.Div(
            "El período contiene filas sin fuente de respaldo clasificada.",
            style={"color": AMBAR, "fontSize": "13px", "padding": "10px 0 6px"},
        ))
    if prelim.empty:
        tabla = html.Div(mensajes)
    else:
        cols = ["fecha_operacion", "pad_id", "campana", "modulo_numero", "tms_rotopala_dia",
                "m3_rotopala_dia", "flag_calculo"]
        tabla = html.Div([*mensajes, _tabla(prelim[cols].round(2), "t-prelim")])

    return f, tabla


@callback(
    Output("aj-modulo", "options"),
    Output("aj-destino", "options"),
    Input("btn-actualizar", "n_clicks"),
)
def cb_opciones_modulo(n):
    try:
        df = db.modulos_disponibles()
    except Exception:
        return [], []
    opts = [
        {"label": f"Módulo {int(r.modulo_numero)} · Campaña {_campana_numero(r.campana)} · "
                  f"PAD {int(r.pad_id)} — {'Óxidos' if int(r.pad_id) == 1 else 'Sulfuros'}",
         "value": f"{int(r.campana_id)}|{int(r.pad_id)}|{int(r.modulo_id)}"}
        for r in df.itertuples()
    ]
    return opts, opts


@callback(
    Output("mensaje-ajuste", "children"),
    Input("btn-ajuste", "n_clicks"),
    State("aj-fecha", "date"),
    State("aj-modulo", "value"),
    State("aj-tipo", "value"),
    State("aj-destino", "value"),
    State("aj-m3", "value"),
    State("aj-tms", "value"),
    State("aj-motivo", "value"),
    State("aj-ant-tipo", "value"),
    State("aj-ant-ref", "value"),
    prevent_initial_call=True,
)
def cb_registrar_ajuste(n, fecha, modulo, tipo, destino, m3, tms, motivo,
                        ant_tipo, ant_ref):
    faltantes = []
    if not modulo:
        faltantes.append("modulo")
    if not tipo:
        faltantes.append("tipo de ajuste")
    if not motivo or len(motivo.strip()) < 10:
        faltantes.append("motivo (al menos 10 caracteres)")
    if not ant_ref or len(ant_ref.strip()) < 10:
        faltantes.append("referencia del antecedente (al menos 10 caracteres)")
    if m3 is None and tms is None:
        faltantes.append("delta en m3 o en TMS")
    if tipo == "TRASPASO_MODULO" and not destino:
        faltantes.append("modulo destino")

    if faltantes:
        return html.Span("Falta completar: " + ", ".join(faltantes),
                         style={"color": ROJO})

    campana_id, pad_id, modulo_id = (int(x) for x in modulo.split("|"))
    destino_id = int(destino.split("|")[2]) if destino else None

    try:
        msg = db.registrar_ajuste(
            fecha_operacion=fecha,
            campana_id=campana_id,
            pad_id=pad_id,
            modulo_id=modulo_id,
            tipo_ajuste=tipo,
            motivo=motivo.strip(),
            antecedente_tipo=ant_tipo,
            antecedente_ref=ant_ref.strip(),
            delta_m3=m3,
            delta_tms=tms,
            modulo_destino_id=destino_id,
        )
        return html.Span(msg, style={"color": VERDE})
    except Exception as exc:
        log.exception("Error al registrar ajuste")
        return html.Span(_error_ui(exc), style={"color": ROJO})


@callback(
    Output("tabla-ajustes", "children"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-ajuste", "children"),
    State("rango", "start_date"),
    State("rango", "end_date"),
)
def cb_tabla_ajustes(n, _, desde, hasta):
    try:
        df = db.ajustes(desde, hasta)
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    if df.empty:
        return html.Div("Sin ajustes registrados en el periodo.",
                        style={"color": GRIS, "fontSize": "13px"})

    cols = ["fecha_operacion", "campana", "modulo_numero", "tipo_ajuste",
            "delta_m3", "delta_tms", "estado", "motivo", "antecedente_tipo",
            "antecedente_ref", "usuario_solicita", "usuario_aprueba"]
    cond = [
        {"if": {"filter_query": '{estado} = "Propuesto"'},
         "backgroundColor": "#FFF8E1"},
        {"if": {"filter_query": '{estado} = "Rechazado"'},
         "backgroundColor": "#FDECEA", "color": ROJO},
    ]
    visible = df[cols].copy()
    visible["tipo_ajuste"] = visible["tipo_ajuste"].map(_codigo_visible)
    visible["antecedente_tipo"] = visible["antecedente_tipo"].map(_codigo_visible)
    return _tabla(visible, "t-ajustes", cond)


# ---------------------------------------------------------------------------
# Disponible para rotopalas — peso, volumen y densidad por modulo
# ---------------------------------------------------------------------------

@callback(
    Output("dr-filtro-campana", "options"),
    Output("dr-ins-campana", "options"),
    Input("btn-actualizar", "n_clicks"),
)
def cb_opciones_dr_campana(n):
    try:
        df = db.campanas_disponible_rotopalas()
    except Exception:
        return [], []
    if df.empty:
        return [], []
    opts = [
        {"label": f"Campaña {int(r.campana)}", "value": int(r.campana_id)}
        for r in df.itertuples() if pd.notna(r.campana_id)
    ]
    return opts, opts


@callback(
    Output("dr-ins-modulo", "options"),
    Input("dr-ins-pad", "value"),
)
def cb_opciones_dr_modulo(pad_id):
    if not pad_id:
        return []
    try:
        df = db.catalogo_modulos(pad_id)
    except Exception:
        return []
    return [
        {"label": f"M{int(r.modulo_numero)} (parcela {int(r.parcela_numero)})",
         "value": int(r.modulo_id)}
        for r in df.itertuples()
    ]


@callback(
    Output("tabla-disponible-rotopalas", "children"),
    Output("dr-upd-id", "options"),
    Output("store-disponible-rotopalas", "data"),
    Input("btn-buscar-dr", "n_clicks"),
    Input("btn-actualizar", "n_clicks"),
    Input("mensaje-dr-actualizar", "children"),
    Input("mensaje-dr-insertar", "children"),
    State("dr-filtro-campana", "value"),
    State("dr-filtro-pad", "value"),
    State("dr-filtro-modulo", "value"),
    State("dr-filtro-fecha-desde", "date"),
    State("dr-filtro-fecha-hasta", "date"),
)
def cb_tabla_disponible_rotopalas(n1, n2, _m1, _m2, campana_id, pad, modulo, fdesde, fhasta):
    try:
        df = db.disponible_rotopalas(
            campana_id=campana_id,
            pad_id=pad if pad else None,
            modulo_numero=modulo,
            fecha_desde=fdesde,
            fecha_hasta=fhasta,
        )
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"}), [], None

    if df.empty:
        return html.Div("Sin registros para el filtro seleccionado.",
                        style={"color": GRIS, "fontSize": "13px"}), [], None

    sin_base = int((df["m3_totales"].isna() | df["densidad"].isna()).sum())
    aviso = None
    if sin_base:
        aviso = html.Div(
            f"{sin_base} registros sin m³ totales o densidad: esos módulos no se pueden "
            "congelar automaticamente hasta completarlos.",
            style={"color": ROJO, "fontSize": "12px", "fontWeight": 600, "marginBottom": "8px"},
        )

    opciones_id = [
        {"label": f"Módulo {int(r.modulo_numero)} · Campaña {_campana_numero(r.campana)} · "
                  f"PAD {int(r.pad_id)} — {'Óxidos' if int(r.pad_id) == 1 else 'Sulfuros'}",
         "value": int(r.id_disponible_rotopalas)}
        for r in df.itertuples()
    ]

    tabla_df = df.copy()
    tabla_df["estado_congelado"] = tabla_df["estado_congelado"].fillna("PENDIENTE").map(_estado)
    cols = ["pad_id", "campana", "modulo_numero", "tms", "m3_totales", "densidad",
            "estado_congelado", "fecha_conformacion"]
    ren = {
        "pad_id": "PAD", "modulo_numero": "Módulo",
        "campana": "Campaña",
        "tms": "TMS base", "m3_totales": "Volumen base (m³)", "densidad": "Densidad (t/m³)",
        "m3_apilado": "m³ apilado", "tmh_apilado": "TMH apilado",
        "remanente_m3": "Remanente m³", "remanente_tms": "Remanente TMS",
        "estado_congelado": "Estado", "fecha_conformacion": "Fecha de incorporación",
    }
    tabla = tabla_df[cols].rename(columns=ren).round(3)

    contenido = [html.Div(f"{len(df)} registro(s).",
                          style={"fontSize": "12px", "color": GRIS, "marginBottom": "6px"})]
    if aviso is not None:
        contenido.append(aviso)
    contenido.append(_tabla(tabla, "t-disponible-rotopalas", page_size=15))

    # df crudo (columnas originales, sin renombrar) para precargar el
    # formulario de actualizacion sin volver a consultar la base.
    return html.Div(contenido), opciones_id, df.to_dict("records")


@callback(
    Output("dr-upd-tms", "value"),
    Output("dr-upd-m3_totales", "value"),
    Output("dr-upd-m3_apilado", "value"),
    Output("dr-upd-tmh_apilado", "value"),
    Output("dr-upd-remanente_m3", "value"),
    Output("dr-upd-remanente_tms", "value"),
    Input("dr-upd-id", "value"),
    State("store-disponible-rotopalas", "data"),
)
def cb_dr_prefill(id_dr, data):
    """Al elegir un registro, precarga sus valores actuales en el
    formulario -- se ve que hay antes de decidir que cambiar. Usa los
    datos ya traidos por la busqueda de arriba, sin otra consulta."""
    vacio = (None, None, None, None, None, None)
    if not id_dr or not data:
        return vacio
    df = pd.DataFrame(data)
    fila = df[df["id_disponible_rotopalas"] == id_dr]
    if fila.empty:
        return vacio
    r = fila.iloc[0]

    def _v(campo):
        val = r.get(campo)
        return None if val is None or pd.isna(val) else float(val)

    return (_v("tms"), _v("m3_totales"), _v("m3_apilado"),
            _v("tmh_apilado"), _v("remanente_m3"), _v("remanente_tms"))


@callback(
    Output("dr-upd-densidad-info", "children"),
    Input("dr-upd-tms", "value"),
    Input("dr-upd-m3_totales", "value"),
    Input("dr-upd-id", "value"),
    State("store-disponible-rotopalas", "data"),
)
def cb_dr_densidad_preview(tms, m3_totales, id_dr, data):
    """Densidad de solo lectura: nunca se edita a mano, se recalcula como
    TMS/volumen. Este texto muestra la densidad actual guardada y la que
    quedaria si se guarda con los valores que hay ahora en el formulario."""
    if not id_dr:
        return ""
    densidad_actual = None
    if data:
        df = pd.DataFrame(data)
        fila = df[df["id_disponible_rotopalas"] == id_dr]
        if not fila.empty and pd.notna(fila.iloc[0].get("densidad")):
            densidad_actual = float(fila.iloc[0]["densidad"])

    partes = []
    if densidad_actual is not None:
        partes.append(f"Densidad actual: {_numero(densidad_actual, 4)} t/m³")
    else:
        partes.append("Densidad actual: sin dato")

    if tms is not None and m3_totales:
        partes.append(f"quedará en {_numero(tms / m3_totales, 4)} t/m³ al guardar")
    elif tms is not None or m3_totales is not None:
        partes.append("complete TMS y volumen para ver la densidad recalculada")

    return " · ".join(partes)


@callback(
    Output("mensaje-dr-actualizar", "children"),
    Input("btn-dr-actualizar", "n_clicks"),
    State("dr-upd-id", "value"),
    State("dr-upd-tms", "value"),
    State("dr-upd-m3_totales", "value"),
    State("dr-upd-m3_apilado", "value"),
    State("dr-upd-tmh_apilado", "value"),
    State("dr-upd-remanente_m3", "value"),
    State("dr-upd-remanente_tms", "value"),
    prevent_initial_call=True,
)
def cb_dr_actualizar(n, id_dr, tms, m3_totales, m3_apilado, tmh_apilado,
                      remanente_m3, remanente_tms):
    if not id_dr:
        return html.Span("Seleccione un módulo para actualizar.", style={"color": ROJO})
    campos = (tms, m3_totales, m3_apilado, tmh_apilado, remanente_m3, remanente_tms)
    if all(v is None for v in campos):
        return html.Span("Informe al menos un campo para actualizar.", style={"color": ROJO})
    try:
        # densidad=None a proposito: el SP la recalcula sola desde TMS/m3_totales.
        msg = db.actualizar_disponible_rotopala(
            id_disponible_rotopalas=int(id_dr),
            tms=tms, m3_totales=m3_totales, densidad=None,
            m3_apilado=m3_apilado, tmh_apilado=tmh_apilado,
            remanente_m3=remanente_m3, remanente_tms=remanente_tms,
        )
        aviso = "Base guardada correctamente. Para actualizar el Reclamo, reprocesar el período afectado."
        if "propagado" in msg.lower() or "CONGELADO" in msg:
            aviso += " La base del módulo incorporado también quedó actualizada."
        return html.Span(aviso, style={"color": VERDE})
    except Exception as exc:
        log.exception("Error al actualizar disponible_rotopalas")
        return html.Span(_error_ui(exc), style={"color": ROJO})


@callback(
    Output("mensaje-dr-insertar", "children"),
    Input("btn-dr-insertar", "n_clicks"),
    State("dr-ins-pad", "value"),
    State("dr-ins-modulo", "value"),
    State("dr-ins-campana", "value"),
    State("dr-ins-tms", "value"),
    State("dr-ins-m3_totales", "value"),
    State("dr-ins-densidad", "value"),
    State("dr-ins-m3_apilado", "value"),
    State("dr-ins-tmh_apilado", "value"),
    State("dr-ins-remanente_m3", "value"),
    State("dr-ins-remanente_tms", "value"),
    prevent_initial_call=True,
)
def cb_dr_insertar(n, pad_id, modulo_id, campana_id, tms, m3_totales, densidad,
                    m3_apilado, tmh_apilado, remanente_m3, remanente_tms):
    faltantes = []
    if not pad_id:
        faltantes.append("PAD")
    if not modulo_id:
        faltantes.append("modulo")
    if not campana_id:
        faltantes.append("campaña")
    if faltantes:
        return html.Span("Falta completar: " + ", ".join(faltantes), style={"color": ROJO})
    try:
        msg = db.insertar_disponible_rotopala(
            pad_id=int(pad_id), modulo_id=int(modulo_id), campana_id=int(campana_id),
            tms=tms, m3_totales=m3_totales, densidad=densidad,
            m3_apilado=m3_apilado, tmh_apilado=tmh_apilado,
            remanente_m3=remanente_m3, remanente_tms=remanente_tms,
        )
        return html.Span("Base guardada correctamente. Para actualizar el Reclamo, reprocesar el período afectado.", style={"color": VERDE})
    except Exception as exc:
        log.exception("Error al insertar en disponible_rotopalas")
        return html.Span(_error_ui(exc), style={"color": ROJO})

