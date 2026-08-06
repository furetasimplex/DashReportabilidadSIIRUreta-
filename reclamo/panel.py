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
from datetime import date, timedelta

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback_context, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from . import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Paleta y estilos
# ---------------------------------------------------------------------------

AZUL = "#1F4E78"
GRIS = "#595959"
ROJO = "#C00000"
VERDE = "#1E6B3A"
AMBAR = "#BF8F00"
FONDO = "#F5F7FA"

CARD = {
    "backgroundColor": "white",
    "borderRadius": "8px",
    "padding": "16px 20px",
    "marginBottom": "16px",
    "boxShadow": "0 1px 3px rgba(0,0,0,0.08)",
}

TITULO_SECCION = {
    "color": AZUL,
    "fontSize": "17px",
    "fontWeight": 600,
    "marginTop": 0,
    "marginBottom": "4px",
}

SUBTITULO = {"color": GRIS, "fontSize": "13px", "marginTop": 0, "marginBottom": "14px"}

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
    page_size=15,
    sort_action="native",
    filter_action="native",
)


# ---------------------------------------------------------------------------
# Layout y callbacks: se integran directamente en la app Dash del sitio SIIR
# (un unico proceso, sin app Dash propia ni servidor separado). layout()
# se cuelga bajo subtabs-reclamo en layout.py; los callbacks usan el
# decorador global @callback (no @app.callback) para no depender de una
# instancia de app propia, mismo patron que
# report_export/callbacks/reportabilidad_cb.py.
# ---------------------------------------------------------------------------

HOY = date.today()
DESDE_DEF = HOY.replace(day=1)
HASTA_DEF = HOY


def encabezado():
    return html.Div(
        style={"backgroundColor": AZUL, "padding": "18px 26px", "color": "white"},
        children=[
            html.H1(
                "Control de Reclamo",
                style={"margin": 0, "fontSize": "24px", "fontWeight": 600},
            ),
            html.Div(
                "Reportabilidad SIIR — Planta Hidrometalúrgica Spence",
                style={"fontSize": "13px", "opacity": 0.85, "marginTop": "3px"},
            ),
        ],
    )


def barra_filtros():
    return html.Div(
        style={**CARD, "display": "flex", "alignItems": "flex-end", "gap": "18px",
               "flexWrap": "wrap"},
        children=[
            html.Div([
                html.Label("Periodo", style={"fontSize": "12px", "color": GRIS,
                                             "display": "block", "marginBottom": "4px"}),
                dcc.DatePickerRange(
                    id="rango",
                    start_date=DESDE_DEF,
                    end_date=HASTA_DEF,
                    display_format="DD-MM-YYYY",
                    first_day_of_week=1,
                ),
            ]),
            html.Div([
                html.Label("PAD", style={"fontSize": "12px", "color": GRIS,
                                         "display": "block", "marginBottom": "4px"}),
                dcc.Dropdown(
                    id="filtro-pad",
                    options=[
                        {"label": "Ambos", "value": 0},
                        {"label": "PAD 1 — Oxido (Rotopala 1)", "value": 1},
                        {"label": "PAD 2 — Sulfuro (Rotopala 2)", "value": 2},
                    ],
                    value=0,
                    clearable=False,
                    style={"width": "260px"},
                ),
            ]),
            html.Button(
                "Actualizar",
                id="btn-actualizar",
                n_clicks=0,
                style={"backgroundColor": AZUL, "color": "white", "border": "none",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px"},
            ),
            html.Button(
                "Recalcular reclamo",
                id="btn-recalcular",
                n_clicks=0,
                style={"backgroundColor": "white", "color": AZUL, "border": f"1px solid {AZUL}",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px"},
            ),
            html.Button(
                "Publicar dato conciliado",
                id="btn-publicar",
                n_clicks=0,
                title="Publica el reclamo del periodo seleccionado. Queda visible para el resto de la organización.",
                style={"backgroundColor": "white", "color": ROJO, "border": f"1px solid {ROJO}",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px", "fontWeight": 600},
            ),
            dcc.ConfirmDialog(
                id="confirmar-publicar",
                message="Se publicará el dato conciliado del periodo seleccionado. "
                        "Quedará visible para el resto de la organización. "
                        "Confirme solo si ya revisó la 'Vista previa del dato conciliado'.",
            ),
            html.Div(id="mensaje-accion",
                     style={"fontSize": "12px", "color": GRIS, "flexGrow": 1}),
        ],
    )


def panel_automatizacion():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Mantencion automatica de modulos", style=TITULO_SECCION),
            html.P(
                "Congela los módulos nuevos que aparecen en topografía o camiones, cierra "
                "los que llegan a 100 % y abre el que sigue en la secuencia. "
                "Los casos que no se pueden decidir solos (fin de PAD, cambio de campaña) "
                "quedan como alerta para revisar aquí.",
                style=SUBTITULO,
            ),
            html.Button(
                "Actualizar modulos (congelar / abrir / cerrar)",
                id="btn-automatizacion",
                n_clicks=0,
                style={"backgroundColor": VERDE, "color": "white", "border": "none",
                       "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                       "fontSize": "13px"},
            ),
            html.Div(id="resultado-automatizacion", style={"marginTop": "12px"}),
            html.Details(
                open=False,
                style={"marginTop": "12px"},
                children=[
                    html.Summary(
                        "Ver alertas pendientes (historico)",
                        style={"cursor": "pointer", "fontSize": "13px", "color": AZUL,
                               "fontWeight": 600, "padding": "4px 0"},
                    ),
                    html.Div(id="alertas-automatizacion", style={"marginTop": "8px"}),
                ],
            ),
        ],
    )


def panel_semaforo():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Semaforo de integridad", style=TITULO_SECCION),
            html.P(
                "Los controles bloqueantes deben quedar en cero antes de publicar. "
                "Los de advertencia no impiden publicar, pero deben poder explicarse. "
                "Esta pantalla solo valida: no publica nada hasta que usted pulse "
                "'Publicar datos conciliados'. Revise primero la vista previa más abajo.",
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
                "Tonelaje del periodo seleccionado, separado por PAD y por origen "
                "(camiones o rotopala). CV25 se contrasta solo a nivel planta: recibe la "
                "carga conjunta de ambas rotopalas y no recibe camiones (regla R7).",
                style=SUBTITULO,
            ),
            html.Div(id="resumen-general"),
        ],
    )


def panel_matriz_mensual():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Vista mensual por modulo", style=TITULO_SECCION),
            html.P(
                "Un modulo por fila, un dia por columna: la misma lectura del libro de "
                "Nueva Revision Ripios, separada por PAD y por origen del tonelaje.",
                style=SUBTITULO,
            ),
            dcc.RadioItems(
                id="matriz-metrica",
                options=[
                    {"label": "Rotopala", "value": "rotopala"},
                    {"label": "Camiones", "value": "camiones"},
                    {"label": "Total (camiones + rotopala)", "value": "total"},
                ],
                value="rotopala",
                inline=True,
                style={"fontSize": "13px", "marginBottom": "12px"},
                labelStyle={"marginRight": "16px"},
            ),
            dcc.Tabs(
                id="matriz-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Oxido", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuro", value="2"),
                ],
            ),
            html.Div(id="matriz-mensual", style={"marginTop": "12px"}),
        ],
    )


def panel_remanente():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Resumen por modulo — tonelaje remanente", style=TITULO_SECCION),
            html.P(
                "Extraido acumulado desde el inicio de la campana (incluye la linea base "
                "fijada al corte) contra el volumen congelado del modulo, en TMS. El "
                "remanente es lo que queda disponible antes de pasar al siguiente modulo. "
                "Si un numero de modulo se reutiliza en una campana nueva, aparece como fila "
                "aparte (columna Campana): nunca se mezcla el acumulado de la campana anterior "
                "con el de la nueva.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="remanente-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Oxido", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuro", value="2"),
                ],
            ),
            html.Div(id="tabla-remanente", style={"marginTop": "12px"}),
        ],
    )


def panel_preview_conciliados():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Vista previa del dato conciliado", style=TITULO_SECCION),
            html.P(
                "Así quedaría el dato publicado por día: tonelaje de rotopala "
                "(con correcciones de línea base, densidad y cierre de secuencia), "
                "tonelaje de camiones, el módulo que más avanzó ese día con su porcentaje, "
                "y el origen del dato. Los días sin medición topográfica se proyectan con "
                "CV25 y quedan marcados en amarillo. Esta vista no publica nada.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="preview-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Oxido", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuro", value="2"),
                ],
            ),
            html.Div(id="tabla-preview-conciliados", style={"marginTop": "12px"}),
        ],
    )


def panel_cv25():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Totalizador CV25 contra topografia", style=TITULO_SECCION),
            html.P(
                "CV25 recibe la carga conjunta de ambas rotopalas y no recibe camiones, "
                "por lo que se compara solo contra el reclamo de rotopala. La banda "
                "historica de brecha mensual observada en el libro de ripios va de "
                "-10,9 % a +3,3 %.",
                style=SUBTITULO,
            ),
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
                "Toneladas secas por hora de operacion. La linea solida es el pesometro "
                "(CV25, tonelaje asignado por hora operada); la linea punteada es "
                "topografia, y solo tiene valor en los dias en que ESA rotopala tuvo una "
                "medicion topografica real: los dias donde el modulo abierto todavia se "
                "reporta con preliminar CV25 (sin medicion propia) quedan en cero aca, "
                "aunque el modulo si haya publicado tonelaje preliminar. Las horas se "
                "derivan del conteo de muestras de corriente sobre umbral en "
                "datos_filtrados.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="rendimiento-rotopala-tabs",
                value="1",
                children=[
                    dcc.Tab(label="Rotopala 1 — PAD Oxido", value="1"),
                    dcc.Tab(label="Rotopala 2 — PAD Sulfuro", value="2"),
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
            html.H3("Cuadratura por modulo", style=TITULO_SECCION),
            html.P(
                "Extraccion acumulada contra el volumen congelado del modulo. Todo lo "
                "que supere 100 % requiere un ajuste de traspaso al modulo siguiente, "
                "documentado. El acumulado parte del inicio de la campana, no del mes.",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="cuadratura-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Oxido", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuro", value="2"),
                ],
            ),
            dcc.Graph(id="g-cuadratura", config={"displayModeBar": False}),
            html.Div(id="tabla-cuadratura"),
            html.Hr(style={"border": "none", "borderTop": "1px solid #E0E0E0",
                           "margin": "16px 0"}),
            html.Div([
                html.Label("Auditar un modulo especifico",
                           style={"fontSize": "12px", "color": GRIS, "fontWeight": 600,
                                  "display": "block", "marginBottom": "4px"}),
                dcc.Dropdown(id="cuadratura-modulo-select", placeholder="Seleccione un modulo",
                            style={"maxWidth": "420px"}),
            ]),
            html.Div(id="detalle-cuadratura-modulo", style={"marginTop": "12px"}),
        ],
    )


def panel_avance():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Avance diario por fuente", style=TITULO_SECCION),
            html.P(
                "El dato oficial es la validación topográfica. Las barras en ámbar son "
                "reclamo preliminar proyectado desde CV25: se corrigen solos al cargar "
                "la topografía y recalcular el periodo. El preliminar reparte el tonelaje "
                "de la correa CV25 entre los módulos abiertos de esa rotopala "
                "(en partes iguales si hay más de uno).",
                style=SUBTITULO,
            ),
            dcc.Tabs(
                id="avance-pad-tabs",
                value="1",
                children=[
                    dcc.Tab(label="PAD 1 — Oxido", value="1"),
                    dcc.Tab(label="PAD 2 — Sulfuro", value="2"),
                ],
            ),
            dcc.Graph(id="g-avance", config={"displayModeBar": False}),
            html.Div(id="tabla-avance"),
        ],
    )


_CAMPOS_DR = [
    ("tms", "TMS"),
    ("m3_totales", "M3 totales"),
    ("densidad", "Densidad"),
    ("m3_apilado", "M3 apilado"),
    ("tmh_apilado", "TMH apilado"),
    ("remanente_m3", "Remanente m3"),
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
            html.H3("Disponible para rotopalas — peso, volumen y densidad", style=TITULO_SECCION),
            html.P(
                "inventar_SpcHidr.disponible_rotopalas: tabla fuente que leen DIRECTO "
                "sp_congelar_modulo y sp_auto_congelar_modulos_nuevos para el peso, volumen "
                "y densidad de cada modulo. Un modulo sin m3_totales o densidad no se congela "
                "solo (queda como ALERTA_SIN_BASE). Los cambios de aqui se escriben directo "
                "sobre la tabla fuente, sin capa de aprobacion.",
                style=SUBTITULO,
            ),
            html.Div(
                style={"display": "flex", "alignItems": "flex-end", "gap": "14px",
                       "flexWrap": "wrap", "marginBottom": "14px"},
                children=[
                    html.Div([
                        html.Label("Campaña", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(id="dr-filtro-campana", placeholder="Todas",
                                     style={"width": "200px"}),
                    ]),
                    html.Div([
                        html.Label("PAD", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(
                            id="dr-filtro-pad",
                            options=[
                                {"label": "Ambos", "value": 0},
                                {"label": "PAD 1 — Oxido", "value": 1},
                                {"label": "PAD 2 — Sulfuro", "value": 2},
                            ],
                            value=0, clearable=False, style={"width": "180px"},
                        ),
                    ]),
                    html.Div([
                        html.Label("Modulo (numero)", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="dr-filtro-modulo", type="number", placeholder="Todos",
                                  style={"width": "110px"}),
                    ]),
                    html.Div([
                        html.Label("Fecha conformacion desde",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.DatePickerSingle(id="dr-filtro-fecha-desde", display_format="DD-MM-YYYY"),
                    ]),
                    html.Div([
                        html.Label("hasta", style={"fontSize": "12px", "color": GRIS}),
                        dcc.DatePickerSingle(id="dr-filtro-fecha-hasta", display_format="DD-MM-YYYY"),
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
                    html.Div([
                        html.H4("Actualizar registro existente",
                               style={"fontSize": "14px", "color": AZUL, "marginBottom": "8px"}),
                        html.P(
                            "Al elegir el registro se precargan sus valores actuales. Solo se "
                            "cambian los campos que modifique; el resto conserva su valor. La "
                            "densidad no se edita a mano: se recalcula sola como TMS / volumen "
                            "(m3 totales) cada vez que guarde.",
                            style={"fontSize": "12px", "color": GRIS, "marginTop": 0},
                        ),
                        html.Div([
                            html.Label("Registro (busque primero arriba)",
                                       style={"fontSize": "12px", "color": GRIS}),
                            dcc.Dropdown(id="dr-upd-id", placeholder="Seleccione un ID"),
                        ], style={"marginBottom": "10px"}),
                        _grid_campos_dr("dr-upd", _CAMPOS_DR_UPD),
                        html.Div(id="dr-upd-densidad-info",
                                style={"fontSize": "12px", "color": AZUL, "marginTop": "8px"}),
                        html.Button(
                            "Actualizar", id="btn-dr-actualizar", n_clicks=0,
                            style={"backgroundColor": AMBAR, "color": "white", "border": "none",
                                   "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                                   "fontSize": "13px", "marginTop": "10px"},
                        ),
                        html.Div(id="mensaje-dr-actualizar", style={"fontSize": "13px", "marginTop": "10px"}),
                    ]),
                    html.Div([
                        html.H4("Insertar nuevo registro",
                               style={"fontSize": "14px", "color": AZUL, "marginBottom": "8px"}),
                        html.P(
                            "Se rechaza si ya existe una fila para ese PAD, modulo y campaña "
                            "(use actualizar en ese caso). Si deja Densidad en blanco, se "
                            "calcula sola como TMS / m3 totales.",
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
                                        options=[{"label": "PAD 1 — Oxido", "value": 1},
                                                 {"label": "PAD 2 — Sulfuro", "value": 2}],
                                        placeholder="Seleccione",
                                    ),
                                ]),
                                html.Div([
                                    html.Label("Modulo", style={"fontSize": "12px", "color": GRIS}),
                                    dcc.Dropdown(id="dr-ins-modulo", placeholder="Elija PAD primero"),
                                ]),
                                html.Div([
                                    html.Label("Campaña", style={"fontSize": "12px", "color": GRIS}),
                                    dcc.Dropdown(id="dr-ins-campana", placeholder="Seleccione"),
                                ]),
                            ],
                        ),
                        _grid_campos_dr("dr-ins"),
                        html.Button(
                            "Insertar", id="btn-dr-insertar", n_clicks=0,
                            style={"backgroundColor": AZUL, "color": "white", "border": "none",
                                   "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                                   "fontSize": "13px", "marginTop": "10px"},
                        ),
                        html.Div(id="mensaje-dr-insertar", style={"fontSize": "13px", "marginTop": "10px"}),
                    ]),
                ],
            ),
        ],
    )


def panel_ajustes():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Ajustes manuales", style=TITULO_SECCION),
            html.P(
                "Todo ajuste nace como propuesta y no altera ninguna cifra hasta "
                "que se aprueba. El motivo y el antecedente son obligatorios.",
                style=SUBTITULO,
            ),
            html.Div(
                style={"display": "grid",
                       "gridTemplateColumns": "repeat(auto-fit, minmax(210px, 1fr))",
                       "gap": "12px", "marginBottom": "14px"},
                children=[
                    html.Div([
                        html.Label("Fecha de operacion", style={"fontSize": "12px", "color": GRIS}),
                        dcc.DatePickerSingle(id="aj-fecha", date=HOY,
                                             display_format="DD-MM-YYYY"),
                    ]),
                    html.Div([
                        html.Label("Modulo", style={"fontSize": "12px", "color": GRIS}),
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
                        html.Label("Modulo destino (solo traspaso)",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(id="aj-destino", placeholder="Opcional"),
                    ]),
                    html.Div([
                        html.Label("Delta m3", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="aj-m3", type="number", style={"width": "100%"}),
                    ]),
                    html.Div([
                        html.Label("Delta TMS", style={"fontSize": "12px", "color": GRIS}),
                        dcc.Input(id="aj-tms", type="number", style={"width": "100%"}),
                    ]),
                    html.Div([
                        html.Label("Tipo de antecedente",
                                   style={"fontSize": "12px", "color": GRIS}),
                        dcc.Dropdown(
                            id="aj-ant-tipo",
                            options=[{"label": t.replace("_", " ").title(), "value": t}
                                     for t in ["ACTA_REUNION", "GRABACION", "CORREO",
                                               "INFORME_TOPOGRAFIA", "PLANILLA", "OTRO"]],
                            value="ACTA_REUNION",
                        ),
                    ]),
                    html.Div([
                        html.Label("Referencia del antecedente",
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
                             placeholder="Por que se ajusta y en que se sustenta"),
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


def layout():
    return html.Div(
    style={"backgroundColor": FONDO, "minHeight": "100vh",
           "fontFamily": "Segoe UI, Arial, sans-serif"},
    children=[
        encabezado(),
        html.Div(
            style={"padding": "18px 26px", "maxWidth": "1500px", "margin": "0 auto"},
            children=[
                barra_filtros(),
                panel_automatizacion(),
                panel_semaforo(),
                panel_resumen_general(),
                panel_cv25(),
                panel_rendimiento(),
                panel_matriz_mensual(),
                panel_cuadratura(),
                panel_remanente(),
                panel_avance(),
                panel_preview_conciliados(),
                panel_disponible_rotopalas(),
                panel_ajustes(),
                html.Div(
                    "Control de reclamo — use el semáforo y la vista previa antes de publicar.",
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
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1),
    )


def _sin_datos(mensaje: str = "Sin datos para el periodo seleccionado") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=mensaje, showarrow=False,
                       font=dict(size=13, color=GRIS), x=0.5, y=0.5,
                       xref="paper", yref="paper")
    fig.update_layout(**_layout_base(""), xaxis=dict(visible=False),
                      yaxis=dict(visible=False))
    return fig


def _tabla(df: pd.DataFrame, id_: str, condicionales=None, page_size=None) -> dash_table.DataTable:
    estilo = dict(TABLA_ESTILO)
    if condicionales:
        estilo["style_data_conditional"] = estilo["style_data_conditional"] + condicionales
    if page_size:
        estilo["page_size"] = page_size
    return dash_table.DataTable(
        id=id_,
        columns=[{"name": c, "id": c,
                  "type": "numeric" if pd.api.types.is_numeric_dtype(df[c]) else "text",
                  "format": {"specifier": ",.2f"} if pd.api.types.is_float_dtype(df[c]) else None}
                 for c in df.columns],
        data=df.to_dict("records"),
        **estilo,
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
    try:
        df = db.mantener_secuencia()
    except Exception as exc:
        log.exception("Error en mantencion automatica de modulos")
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"}), dash.no_update

    if df.empty:
        return (
            html.Div("Sin cambios: nada nuevo que congelar, abrir ni cerrar.",
                     style={"color": VERDE, "fontSize": "13px"}),
            html.Span("Mantencion automatica ejecutada, sin cambios.", style={"color": VERDE}),
        )

    es_alerta = df["accion"].str.startswith("ALERTA")
    cambios = df[~es_alerta]
    alertas = df[es_alerta]

    cols = ["accion", "pad_id", "campana_id", "modulo_numero", "detalle"]
    partes = []

    if not cambios.empty:
        partes.append(html.Div(
            f"{len(cambios)} cambio(s) automatico(s).",
            style={"color": VERDE, "fontSize": "13px", "fontWeight": 600, "padding": "4px 0"}))
        partes.append(_tabla(cambios[cols], "t-auto-cambios"))

    if not alertas.empty:
        partes.append(html.Div(
            f"{len(alertas)} caso(s) que no se pudieron resolver solos. Requieren revision.",
            style={"color": ROJO, "fontSize": "13px", "fontWeight": 600, "padding": "10px 0 4px"}))
        partes.append(_tabla(alertas[cols], "t-auto-alertas",
                             [{"if": {"row_index": "odd"}, "backgroundColor": "#FDECEA"},
                              {"if": {"row_index": "even"}, "backgroundColor": "#FEF4F3"}]))

    mensaje = f"Mantencion automatica: {len(cambios)} cambios, {len(alertas)} alertas."
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
        return html.Div("Sin alertas pendientes de los ultimos 30 dias.",
                        style={"color": GRIS, "fontSize": "12px"})

    cols = ["accion", "pad_id", "campana_id", "modulo_numero", "detalle", "fecha_evento"]
    return html.Div([
        html.Div(f"{len(df)} alerta(s) pendiente(s) de los ultimos 30 dias:",
                style={"color": ROJO, "fontSize": "12px", "fontWeight": 600,
                       "padding": "4px 0"}),
        _tabla(df[cols], "t-alertas-persistentes"),
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

    def tarjeta(row):
        if row["resultado"] == "OK":
            color, fondo = VERDE, "#E8F5E9"
        elif row["resultado"] == "NO PUBLICAR":
            color, fondo = ROJO, "#FDECEA"
        else:
            color, fondo = AMBAR, "#FFF8E1"
        return html.Div(
            style={"backgroundColor": fondo, "borderLeft": f"4px solid {color}",
                   "padding": "10px 14px", "borderRadius": "5px"},
            children=[
                html.Div(row["control"], style={"fontSize": "12px", "color": "#333"}),
                html.Div(
                    f"{int(row['hallazgos'])}  ·  {row['resultado']}",
                    style={"fontSize": "15px", "fontWeight": 600, "color": color,
                           "marginTop": "3px"},
                ),
            ],
        )

    return html.Div(
        style={"display": "grid",
               "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
               "gap": "10px"},
        children=[tarjeta(r) for _, r in df.iterrows()],
    )


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
    except Exception as exc:
        return html.Div(_error_ui(exc), style={"color": ROJO, "fontSize": "13px"})

    if df.empty:
        return html.Div(
            "Sin datos calculados para el periodo. Use «Recalcular reclamo».",
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
        sin_dato = int((sub["fuente_reclamo"] == "SIN_DATO").sum())
        rotopala = topo + prelim + ajuste
        return rotopala, camiones, topo, prelim, ajuste, sin_dato

    r1, c1, topo1, prelim1, aj1, sd1 = totales(1)
    r2, c2, topo2, prelim2, aj2, sd2 = totales(2)
    topo_t, prelim_t, aj_t = topo1 + topo2, prelim1 + prelim2, aj1 + aj2

    def fila(etiqueta, valor, color=GRIS, negrita=False):
        return html.Div(
            f"{etiqueta}: {valor:,.0f} TMS",
            style={"fontSize": "11px", "color": color, "marginTop": "2px",
                   "fontWeight": 700 if negrita else 400},
        )

    def tarjeta(titulo, rotopala, camiones, topo, prelim, ajuste, sin_dato, color):
        total = rotopala + camiones
        pct_prelim = (prelim * 100.0 / rotopala) if rotopala else 0
        detalle = [
            fila("Rotopala (topografia + preliminar + ajustes)", rotopala, color, True),
            fila("  de la cual, topografia real", topo, AZUL),
            fila("  de la cual, preliminar CV25 (aun sin medicion)",
                 prelim, AMBAR if pct_prelim > 20 else GRIS),
        ]
        if ajuste:
            detalle.append(fila("  de la cual, ajuste manual aprobado", ajuste, GRIS))
        detalle.append(fila("Camiones", camiones, color, True))
        if sin_dato:
            detalle.append(html.Div(
                f"{sin_dato} fila(s) modulo x dia sin ningun dato (ni topografia ni CV25).",
                style={"fontSize": "11px", "color": ROJO, "marginTop": "4px"}))
        return html.Div(
            style={"backgroundColor": "white", "borderTop": f"3px solid {color}",
                   "borderRadius": "6px", "padding": "12px 16px", "flex": "1",
                   "minWidth": "260px"},
            children=[
                html.Div(titulo, style={"fontSize": "12px", "color": GRIS, "fontWeight": 600}),
                html.Div(f"{total:,.0f} TMS",
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
            tarjeta("PAD 1 — Oxido", r1, c1, topo1, prelim1, aj1, sd1, AZUL),
            tarjeta("PAD 2 — Sulfuro", r2, c2, topo2, prelim2, aj2, sd2, "#E07B39"),
            tarjeta("Planta — total", r1 + r2, c1 + c2, topo_t, prelim_t, aj_t,
                    sd1 + sd2, VERDE),
        ],
    )

    nota_cv25 = None
    if not cv.empty:
        cv25_periodo = cv["tms_cv25"].fillna(0).sum()
        topo_periodo = cv["tms_topografia"].fillna(0).sum()
        if cv25_periodo:
            dif_pct = (topo_periodo - cv25_periodo) * 100.0 / cv25_periodo
            color = ROJO if abs(dif_pct) > 10 else VERDE
            nota_cv25 = html.Div(
                [
                    html.Div(
                        [
                            "Como se arma cada numero (todo en TMS, mismas unidades en "
                            "toda la pantalla): ",
                            html.B(f"{topo_t:,.0f}"), " topografia real  +  ",
                            html.B(f"{prelim_t:,.0f}"), " preliminar CV25  +  ",
                            html.B(f"{aj_t:,.0f}"), " ajustes  =  ",
                            html.B(f"{r1 + r2:,.0f}"), " Rotopala total (la cifra grande "
                            "de las tarjetas de arriba).",
                        ],
                        style={"color": GRIS},
                    ),
                    html.Div(
                        [
                            "La correa CV25 NO se compara contra ese total: se compara solo "
                            "contra la topografia real, porque CV25 y la topografia miden lo "
                            "mismo (lo que pasa por la correa) mientras que el preliminar es "
                            "una proyeccion temporal que todavia no tiene medicion topografica "
                            "propia. Por eso: ",
                            html.B(f"{topo_periodo:,.0f}"), " (topografia) contra ",
                            html.B(f"{cv25_periodo:,.0f}"), " (CV25)  →  brecha ",
                            html.Span(f"{dif_pct:+.1f} %", style={"color": color,
                                                                   "fontWeight": 700}),
                            ".",
                        ],
                        style={"color": GRIS, "marginTop": "5px"},
                    ),
                ],
                style={"fontSize": "12px", "marginTop": "10px", "lineHeight": "1.6"},
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
        return html.Div("Sin datos calculados para este PAD en el periodo.",
                        style={"color": GRIS, "fontSize": "13px", "padding": "10px 0"})

    sub["dia"] = pd.to_datetime(sub["fecha_operacion"]).dt.strftime("%d")
    sub["tms_camiones_dia"] = sub["tms_camiones_dia"].fillna(0)
    sub["tms_rotopala_dia"] = sub["tms_rotopala_dia"].fillna(0)
    sub["tms_total_dia"] = sub["tms_camiones_dia"] + sub["tms_rotopala_dia"]

    campo = {"rotopala": "tms_rotopala_dia", "camiones": "tms_camiones_dia",
             "total": "tms_total_dia"}[metrica]

    piv = sub.pivot_table(index="modulo_numero", columns="dia", values=campo,
                          aggfunc="sum", fill_value=0)
    piv = piv.reindex(sorted(piv.index), axis=0)
    piv.insert(0, "Total periodo", piv.sum(axis=1))
    piv = piv.reset_index().rename(columns={"modulo_numero": "Modulo"})

    total_periodo = piv["Total periodo"].sum()

    # Fila de totales por dia (columna), ademas de la columna "Total periodo"
    # que ya suma por modulo (fila). Pedido explicito del usuario para
    # facilitar la comparacion contra el Excel oficial, que si trae total
    # por dia.
    fila_total = {"Modulo": "TOTAL"}
    for col in piv.columns:
        if col != "Modulo":
            fila_total[col] = piv[col].sum()
    piv = pd.concat([piv, pd.DataFrame([fila_total])[piv.columns]], ignore_index=True)

    cond_total = [
        {"if": {"filter_query": '{Modulo} = "TOTAL"'},
         "fontWeight": "700", "borderTop": f"2px solid {GRIS}"},
    ]

    return html.Div([
        html.Div(f"Total del PAD en el periodo ({metrica}): {total_periodo:,.0f} TMS",
                style={"fontSize": "13px", "fontWeight": 600, "color": GRIS,
                       "padding": "4px 0 8px"}),
        _tabla(piv.round(1), f"t-matriz-{pad_id}-{metrica}", cond_total),
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
        return html.Div("Sin modulos congelados en este PAD.",
                        style={"color": GRIS, "fontSize": "13px"})

    sub = sub.sort_values(["modulo_numero", "campana_id"])
    cols = ["modulo_numero", "campana_id", "estado_secuencia", "tms_conformado",
            "tms_extraido_total", "tms_saldo_disponible", "porcentaje_extraido",
            "flag_cuadratura"]
    ren = {"modulo_numero": "Modulo", "campana_id": "Campaña", "estado_secuencia": "Estado",
           "tms_conformado": "TMS congelado", "tms_extraido_total": "TMS extraido",
           "tms_saldo_disponible": "TMS remanente", "porcentaje_extraido": "% extraido",
           "flag_cuadratura": "Estado cuadratura"}
    tabla = sub[cols].rename(columns=ren).round(1)

    cond = [
        {"if": {"filter_query": '{Estado cuadratura} = "SOBRE_100_PROPONER_TRASPASO"'},
         "backgroundColor": "#FDECEA", "color": ROJO},
        {"if": {"filter_query": '{Estado cuadratura} = "MODULO_PRACTICAMENTE_AGOTADO"'},
         "backgroundColor": "#FFF8E1"},
        {"if": {"filter_query": '{Estado} = "ABIERTO"'}, "fontWeight": "600"},
    ]

    total_remanente = sub["tms_saldo_disponible"].sum()
    return html.Div([
        html.Div(f"Remanente total del PAD: {total_remanente:,.0f} TMS",
                style={"fontSize": "13px", "fontWeight": 600, "color": GRIS,
                       "padding": "4px 0 8px"}),
        _tabla(tabla, f"t-remanente-{pad_id}", cond),
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
            "Sin datos calculados para el periodo. Use «Recalcular reclamo».",
            style={"color": GRIS, "fontSize": "13px"},
        )

    pad = int(pad_tab)
    sub = df[df["pad_id"] == pad].copy()
    if sub.empty:
        return html.Div("Sin datos calculados para este PAD en el periodo.",
                        style={"color": GRIS, "fontSize": "13px"})

    sub["tms_camiones_dia"]  = sub["tms_camiones_dia"].fillna(0)
    sub["tms_rotopala_dia"]  = sub["tms_rotopala_dia"].fillna(0)
    sub["avance_roto_pct"]   = sub["avance_roto_pct"].fillna(0)
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

    filas = []
    for fecha, grupo in sub.groupby("fecha_operacion"):
        tms_rotopala = float(grupo["tms_rotopala_dia"].sum())
        tms_camiones = float(grupo["tms_camiones_dia"].sum())

        # Entre los modulos con tonelaje ese dia, el protagonista real es el
        # que TODAVIA se esta llenando -- el de MENOR avance acumulado, no
        # el de mayor TMS (evita que un arrastre de linea base recien
        # establecida, con avance ya alto, tape al modulo realmente activo).
        activos = grupo[grupo["tms_rotopala_dia"] > 0].copy()
        if piso_campana is not None:
            misma_campana = activos["campana_id"] == piso_campana
            activos = activos[~misma_campana | (activos["modulo_numero"] >= piso_modulo)]

        if not activos.empty:
            fila_activa = activos.loc[activos["avance_roto_pct"].idxmin()]
            modulo_activo = int(fila_activa["modulo_numero"])
            avance_pct = float(fila_activa["avance_roto_pct"]) * 100
            fuente = fila_activa["fuente_reclamo"]
            campana_activa = fila_activa["campana_id"]

            if piso_campana is None or campana_activa != piso_campana:
                piso_campana = campana_activa
                piso_modulo = modulo_activo
            elif modulo_activo > piso_modulo:
                piso_modulo = modulo_activo

            ultimo_modulo_activo, ultimo_avance_pct = modulo_activo, avance_pct
        elif ultimo_modulo_activo is not None and tms_rotopala > 0:
            # Hubo tonelaje real ese dia, pero solo en un modulo ya
            # superado (residual): se mantiene el ultimo modulo protagonista
            # conocido en vez de retroceder. El tonelaje real del dia se
            # sigue sumando arriba, esto solo afecta la columna informativa.
            modulo_activo, avance_pct = ultimo_modulo_activo, ultimo_avance_pct
            fuente = "TOPOGRAFIA"
        else:
            modulo_activo, avance_pct, fuente = None, None, None

        # Se proyecta por CV25 UNICAMENTE los dias sin medicion real de
        # topografia -- marcarlo explicito, no dejarlo como un dato mas.
        if fuente == "PRELIMINAR_CV25":
            origen = "PROYECTADO (CV25)"
        elif fuente == "TOPOGRAFIA":
            origen = "REAL (topografia)"
        elif tms_rotopala == 0 and tms_camiones == 0:
            origen = "SIN DATO"
        else:
            origen = fuente or "SIN DATO"

        filas.append({
            "Fecha": fecha.strftime("%Y-%m-%d"),
            "Rotopala (TMS)": round(tms_rotopala, 1),
            "Camiones (TMS)": round(tms_camiones, 1),
            "Total (TMS)": round(tms_rotopala + tms_camiones, 1),
            "Modulo mayor avance": modulo_activo if modulo_activo is not None else "",
            "% avance modulo": "" if avance_pct is None else f"{avance_pct:.1f}%",
            "Origen rotopala": origen,
        })

    tabla = pd.DataFrame(filas).sort_values("Fecha").reset_index(drop=True)

    cond = [
        {"if": {"filter_query": '{Origen rotopala} = "PROYECTADO (CV25)"'},
         "backgroundColor": "#FFF8E1", "color": "#8A6D00", "fontWeight": 600},
        {"if": {"filter_query": '{Origen rotopala} = "SIN DATO"'},
         "color": GRIS},
    ]

    return html.Div([
        html.Div(
            "Amarillo = dia proyectado desde CV25 por no tener medicion real de "
            "topografia (unico caso donde se proyecta). Sin color = medicion real.",
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
    f1.add_trace(go.Bar(x=df["fecha"], y=df["tms_cv25"], name="CV25 (pesometro)",
                        marker_color="#9DC3E6"))
    f1.add_trace(go.Scatter(x=df["fecha"], y=df["tms_topografia"], name="Topografia",
                            mode="lines+markers", line=dict(color=AZUL, width=2.5)))
    if df["tms_preliminar"].fillna(0).sum() > 0:
        f1.add_trace(go.Bar(x=df["fecha"], y=df["tms_preliminar"],
                            name="Preliminar CV25", marker_color=AMBAR, opacity=0.75))
    f1.update_layout(**_layout_base("Tonelaje diario: correa contra topografia", 330),
                     barmode="overlay",
                     yaxis_title="TMS", xaxis_title=None)
    f1.update_xaxes(showgrid=False)
    f1.update_yaxes(gridcolor="#EEE")

    f2 = go.Figure()
    colores = [ROJO if abs(v or 0) > 10 else VERDE for v in df["diferencia_pct"]]
    f2.add_trace(go.Bar(x=df["fecha"], y=df["diferencia_pct"], marker_color=colores,
                        name="Brecha %"))
    f2.add_hline(y=10, line_dash="dot", line_color=GRIS)
    f2.add_hline(y=-10, line_dash="dot", line_color=GRIS)
    f2.update_layout(**_layout_base("Brecha porcentual (topografia - CV25) / CV25", 250),
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
        return (_sin_datos(f"Sin datos para rotopala {rid} en el periodo"),
                _sin_datos(""))

    f1 = go.Figure()
    f1.add_trace(go.Scatter(x=df["fecha"], y=df["rendimiento_pesometro_tms_hr"],
                            name="Pesometro (CV25)", mode="lines+markers",
                            line=dict(color=color, width=2)))
    f1.add_trace(go.Scatter(x=df["fecha"], y=df["rendimiento_topografia_tms_hr"],
                            name="Topografia (solo dias con medicion propia)", mode="lines+markers",
                            line=dict(color=color, width=2, dash="dot"),
                            marker=dict(size=5, symbol="circle-open")))
    f1.add_hrect(y0=1500, y1=4500, fillcolor=VERDE, opacity=0.06, line_width=0)
    f1.update_layout(**_layout_base(f"Rotopala {rid} — tasa horaria de tonelaje "
                                    "(banda de referencia 1.500 a 4.500)", 330),
                     yaxis_title="TMS / hora")
    f1.update_xaxes(showgrid=False)
    f1.update_yaxes(gridcolor="#EEE")

    f2 = go.Figure()
    f2.add_trace(go.Bar(x=df["fecha"], y=df["horas_operacion"],
                        name=f"Rotopala {rid}", marker_color=color))
    f2.update_layout(**_layout_base(f"Rotopala {rid} — horas de operacion por dia", 250),
                     yaxis_title="horas", showlegend=False)
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
        return _sin_datos("Sin modulos congelados"), None

    pad = int(pad_tab)
    df = df[df["pad_id"] == pad]
    if df.empty:
        return _sin_datos("Sin modulos congelados en este PAD"), None

    df = df.sort_values("modulo_numero")
    top = df.head(40)

    f = go.Figure()
    f.add_trace(go.Bar(
        x=[f"M{int(m)}" if pd.notna(m) else "?" for m in top["modulo_numero"]],
        y=top["m3_camiones_total"], name="Camiones", marker_color="#E07B39"))
    f.add_trace(go.Bar(
        x=[f"M{int(m)}" if pd.notna(m) else "?" for m in top["modulo_numero"]],
        y=top["m3_rotopala_total"], name="Rotopala", marker_color=AZUL))
    f.add_trace(go.Scatter(
        x=[f"M{int(m)}" if pd.notna(m) else "?" for m in top["modulo_numero"]],
        y=top["m3_totales"], name="Volumen congelado", mode="lines+markers",
        line=dict(color=ROJO, width=2, dash="dash")))
    f.update_layout(**_layout_base("Extraccion acumulada contra volumen congelado, por modulo", 360),
                    barmode="stack", yaxis_title="m3")
    f.update_xaxes(showgrid=False)
    f.update_yaxes(gridcolor="#EEE")

    alerta = df[df["flag_cuadratura"] == "SOBRE_100_PROPONER_TRASPASO"]
    if alerta.empty:
        tabla = html.Div("Ningun modulo supera el 100 % de extraccion.",
                         style={"color": VERDE, "fontSize": "13px", "padding": "10px 0"})
    else:
        cols = ["modulo_numero", "m3_totales", "m3_camiones_total", "m3_rotopala_total",
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
        {"label": f"Modulo {int(r.modulo_numero)}  (campaña {int(r.campana_id)}"
                  f"{'  ·  ' + r.estado_secuencia if pd.notna(r.estado_secuencia) else ''})",
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
                html.Span(f"Modulo {int(r['modulo_numero'])} — campaña {campana_id}: ",
                          style={"fontWeight": 600}),
                f"volumen congelado {r['m3_totales']:,.0f} m3 "
                f"({r['tms_conformado']:,.0f} TMS, densidad {r['densidad_oficial']:.4f})  ·  "
                f"extraido {r['m3_extraido_total']:,.0f} m3 ({r['porcentaje_extraido']:.1f} %)  "
                f"·  remanente {r['tms_saldo_disponible']:,.0f} TMS  ·  "
                f"estado {r['flag_cuadratura']}",
            ],
            style={"fontSize": "13px", "color": GRIS, "marginBottom": "10px",
                   "padding": "8px 10px", "backgroundColor": "#F2F7FB", "borderRadius": "5px"},
        )

    if hist.empty:
        tabla = html.Div(
            "Este módulo aún no tiene historial diario. "
            "Use «Recalcular reclamo» para el periodo que corresponda.",
            style={"color": GRIS, "fontSize": "13px"},
        )
    else:
        cols = ["fecha_operacion", "m3_rotopala_dia", "tms_rotopala_dia",
                "m3_camiones_dia", "tms_camiones_dia", "avance_total_pct",
                "ajuste_tms", "fuente_reclamo", "metodo_calculo", "flag_calculo"]
        cond = [
            {"if": {"filter_query": '{fuente_reclamo} = "PRELIMINAR_CV25"'},
             "backgroundColor": "#FFF8E1"},
            {"if": {"filter_query": '{flag_calculo} contains "REVISAR"'},
             "backgroundColor": "#FDECEA", "color": ROJO},
        ]
        tabla = html.Div([
            html.Div(f"Historial diario completo ({len(hist)} fila(s)), "
                    "todo el rango disponible, no solo el periodo filtrado arriba:",
                    style={"fontSize": "12px", "color": GRIS, "padding": "4px 0 8px"}),
            _tabla(hist[cols].round(2), f"t-detalle-{campana_id}-{modulo_id}"),
        ])

    return html.Div([resumen, tabla] if resumen is not None else [tabla])


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
    try:
        df = db.avance_diario(desde, hasta)
    except Exception as exc:
        return _sin_datos(_error_ui(exc)), None

    if df.empty:
        return _sin_datos(), None

    pad = int(pad_tab)
    df = df[df["pad_id"] == pad]
    if df.empty:
        return _sin_datos("Sin datos para este PAD en el periodo"), None

    agg = (df.groupby(["fecha_operacion", "fuente_reclamo"], as_index=False)
             .agg(tms=("tms_rotopala_dia", "sum")))

    colores = {"TOPOGRAFIA": AZUL, "PRELIMINAR_CV25": AMBAR,
               "AJUSTE_MANUAL": "#7B5EA7", "SIN_DATO": "#CCCCCC"}

    f = go.Figure()
    for fuente in ["TOPOGRAFIA", "PRELIMINAR_CV25", "AJUSTE_MANUAL", "SIN_DATO"]:
        sub = agg[agg["fuente_reclamo"] == fuente]
        if not sub.empty:
            f.add_trace(go.Bar(x=sub["fecha_operacion"], y=sub["tms"], name=fuente,
                               marker_color=colores[fuente]))
    f.update_layout(**_layout_base(f"PAD {pad} — tonelaje reclamado por rotopala, "
                                   "segun fuente del dato", 330),
                    barmode="stack", yaxis_title="TMS")
    f.update_xaxes(showgrid=False)
    f.update_yaxes(gridcolor="#EEE")

    prelim = df[df["fuente_reclamo"] == "PRELIMINAR_CV25"]
    if prelim.empty:
        tabla = html.Div("Todo el periodo tiene respaldo topografico.",
                         style={"color": VERDE, "fontSize": "13px", "padding": "10px 0"})
    else:
        cols = ["fecha_operacion", "pad_id", "modulo_numero", "tms_rotopala_dia",
                "m3_rotopala_dia", "flag_calculo"]
        tabla = html.Div([
            html.Div(
                f"{len(prelim)} fila(s) publicadas con fuente preliminar CV25. "
                f"Se corrigen solas al cargar la topografia y reprocesar el rango.",
                style={"color": AMBAR, "fontSize": "13px", "fontWeight": 600,
                       "padding": "10px 0 6px"},
            ),
            _tabla(prelim[cols].round(2), "t-prelim"),
        ])

    return f, tabla


@callback(
    Output("aj-modulo", "options"),
    Output("aj-destino", "options"),
    Input("btn-actualizar", "n_clicks"),
    State("filtro-pad", "value"),
)
def cb_opciones_modulo(n, pad):
    try:
        df = db.modulos_disponibles()
    except Exception:
        return [], []
    if pad:
        df = df[df["pad_id"] == pad]
    opts = [
        {"label": f"M{int(r.modulo_numero)} · PAD {int(r.pad_id)} · campana {int(r.campana_id)}",
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

    cols = ["ajuste_id", "fecha_operacion", "modulo_id", "tipo_ajuste",
            "delta_m3", "delta_tms", "estado", "motivo", "antecedente_tipo",
            "antecedente_ref", "usuario_solicita", "usuario_aprueba"]
    cond = [
        {"if": {"filter_query": '{estado} = "PROPUESTO"'},
         "backgroundColor": "#FFF8E1"},
        {"if": {"filter_query": '{estado} = "RECHAZADO"'},
         "backgroundColor": "#FDECEA", "color": ROJO},
    ]
    return _tabla(df[cols], "t-ajustes", cond)


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
        {"label": f"Campaña {int(r.campana)} (id {int(r.campana_id)})", "value": int(r.campana_id)}
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
            f"{sin_base} registro(s) sin m3_totales o densidad: esos modulos no se pueden "
            "congelar automaticamente hasta completarlos.",
            style={"color": ROJO, "fontSize": "12px", "fontWeight": 600, "marginBottom": "8px"},
        )

    opciones_id = [
        {"label": f"ID {int(r.id_disponible_rotopalas)} · M{int(r.modulo_numero)} · "
                  f"PAD {int(r.pad_id)} · campaña {int(r.campana_id)}",
         "value": int(r.id_disponible_rotopalas)}
        for r in df.itertuples()
    ]

    tabla_df = df.copy()
    tabla_df["estado_congelado"] = tabla_df["estado_congelado"].fillna("PENDIENTE")
    tabla_df["fecha_conformacion"] = pd.to_datetime(
        tabla_df["fecha_conformacion"], errors="coerce"
    ).dt.strftime("%Y-%m-%d").fillna("")

    cols = ["id_disponible_rotopalas", "pad_id", "modulo_numero", "campana", "campana_id",
            "tms", "m3_totales", "densidad", "m3_apilado", "tmh_apilado",
            "remanente_m3", "remanente_tms", "estado_congelado", "fecha_conformacion"]
    ren = {
        "id_disponible_rotopalas": "ID", "pad_id": "PAD", "modulo_numero": "Modulo",
        "campana": "Campaña", "campana_id": "Campaña ID",
        "tms": "TMS", "m3_totales": "M3 totales", "densidad": "Densidad",
        "m3_apilado": "M3 apilado", "tmh_apilado": "TMH apilado",
        "remanente_m3": "Remanente m3", "remanente_tms": "Remanente TMS",
        "estado_congelado": "Estado", "fecha_conformacion": "Fecha conformacion",
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
        partes.append(f"Densidad actual: {densidad_actual:.4f}")
    else:
        partes.append("Densidad actual: sin dato")

    if tms is not None and m3_totales:
        partes.append(f"quedara en {tms / m3_totales:.4f} al guardar")
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
        return html.Span("Seleccione un registro (ID) para actualizar.", style={"color": ROJO})
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
        return html.Span(msg, style={"color": VERDE})
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
        return html.Span(msg, style={"color": VERDE})
    except Exception as exc:
        log.exception("Error al insertar en disponible_rotopalas")
        return html.Span(_error_ui(exc), style={"color": ROJO})

