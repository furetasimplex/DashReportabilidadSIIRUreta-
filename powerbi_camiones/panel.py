"""
Panel de carga del Export de PowerBI camiones — Planta Hidrometalurgica
Spence.

Sube el Excel "Export" de PowerBI camiones, lo valida, muestra una vista
previa, y solo al confirmar lo carga en inventar_SpcHidr.mov_cam_powerbi
(reemplazando el rango de fechas del archivo). Fuente pensada como
alternativa/paralela a inventar_SpcHidr.mov_cam: los SP que hoy leen
mov_cam se redirigiran aca mas adelante, en un paso separado.

Integrado directamente en el sitio SIIR (DashReportabilidadSIIR): layout()
se cuelga bajo un nuevo item del sidebar en layout.py, y los callbacks
quedan registrados en la app Dash del sitio via el decorador global
@callback al importarse este modulo (mismo patron que reclamo/panel.py).
"""

from __future__ import annotations

import logging

import dash
from dash import dcc, html, dash_table, Input, Output, State, callback
import pandas as pd

from env_loader import load_app_env

load_app_env()

from . import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


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
    style_table={
        "overflowX": "auto",   # 33 columnas no caben en pantalla: scroll horizontal
        "maxWidth": "100%",
    },
    style_cell={
        "fontFamily": "Segoe UI, Arial, sans-serif",
        "fontSize": "12px",
        "padding": "6px 10px",
        "textAlign": "right",
        "minWidth": "90px",
        "maxWidth": "220px",
        "whiteSpace": "normal",
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

_MSG_ERROR = "No se pudo completar la operación. Intente de nuevo o contacte a soporte."


def _error_ui(exc: BaseException | None = None, prefijo: str = "Error") -> str:
    if exc is not None:
        log.debug("%s: %s", prefijo, exc)
    return _MSG_ERROR


def _usuario_actual() -> str:
    try:
        import flask as _flask
        return _flask.session.get("username", "desconocido")
    except Exception:
        return "desconocido"


def _tabla(df: pd.DataFrame, id_: str, page_size: int = 15) -> dash_table.DataTable:
    estilo = dict(TABLA_ESTILO)
    estilo["page_size"] = page_size
    return dash_table.DataTable(
        id=id_,
        columns=[{"name": c, "id": c} for c in df.columns],
        data=df.to_dict("records"),
        **estilo,
    )


def encabezado():
    return html.Div(
        style={"backgroundColor": AZUL, "padding": "18px 26px", "color": "white"},
        children=[
            html.H1(
                "Carga PowerBI Camiones",
                style={"margin": 0, "fontSize": "24px", "fontWeight": 600},
            ),
            html.Div(
                "Reportabilidad SIIR — Planta Hidrometalúrgica Spence",
                style={"fontSize": "13px", "opacity": 0.85, "marginTop": "3px"},
            ),
        ],
    )


def panel_carga():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Cargar Export de PowerBI camiones", style=TITULO_SECCION),
            html.P(
                "Suba el archivo Excel tal como lo exporta PowerBI (hoja "
                "\"Export\"). Se valida y se muestra una vista previa antes "
                "de tocar la base de datos. Al confirmar, reemplaza en "
                "inventar_SpcHidr.mov_cam_powerbi todo el rango de fechas "
                "que trae el archivo — si vuelve a subir un periodo ya "
                "cargado, se reemplaza por la version nueva, sin duplicar.",
                style=SUBTITULO,
            ),
            dcc.Upload(
                id="pbc-upload",
                children=html.Div([
                    html.I(className="bi bi-cloud-upload me-2"),
                    "Arrastre el archivo aqui o haga clic para seleccionar",
                ]),
                style={
                    "width": "100%", "minHeight": "70px", "lineHeight": "70px",
                    "borderWidth": "2px", "borderStyle": "dashed", "borderRadius": "8px",
                    "borderColor": AZUL, "textAlign": "center", "color": AZUL,
                    "fontSize": "13px", "cursor": "pointer",
                },
                multiple=False,
            ),
            dcc.Store(id="pbc-store-registros"),
            dcc.Store(id="pbc-store-archivo"),
            html.Div(id="pbc-mensaje-preview", style={"marginTop": "12px", "fontSize": "13px"}),
            html.Div(id="pbc-tabla-preview", style={"marginTop": "10px"}),
            html.Div(
                style={"marginTop": "14px", "display": "flex", "alignItems": "center", "gap": "14px"},
                children=[
                    html.Button(
                        "Cargar a la base de datos",
                        id="pbc-btn-cargar",
                        n_clicks=0,
                        disabled=True,
                        style={"backgroundColor": ROJO, "color": "white", "border": "none",
                               "padding": "9px 22px", "borderRadius": "5px", "cursor": "pointer",
                               "fontSize": "13px", "fontWeight": 600},
                    ),
                    dcc.ConfirmDialog(
                        id="pbc-confirmar-carga",
                        message="Se reemplazaran en inventar_SpcHidr.mov_cam_powerbi todas las "
                                "filas del rango de fechas que trae este archivo. Confirme solo "
                                "despues de revisar la vista previa.",
                    ),
                    html.Div(id="pbc-mensaje-carga", style={"fontSize": "13px"}),
                ],
            ),
        ],
    )


def panel_historial():
    return html.Div(
        style=CARD,
        children=[
            html.H3("Ultimas cargas", style=TITULO_SECCION),
            html.P(
                "Bitacora simple de los archivos cargados: quien, cuando, "
                "y que rango de fechas trajo cada uno.",
                style=SUBTITULO,
            ),
            html.Div(id="pbc-tabla-historial"),
        ],
    )


def layout():
    return html.Div(
        style={"backgroundColor": FONDO, "minHeight": "100vh",
               "fontFamily": "Segoe UI, Arial, sans-serif"},
        children=[
            encabezado(),
            html.Div(
                style={"padding": "18px 26px", "maxWidth": "1300px", "margin": "0 auto"},
                children=[
                    panel_carga(),
                    panel_historial(),
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

@callback(
    Output("pbc-mensaje-preview", "children"),
    Output("pbc-tabla-preview", "children"),
    Output("pbc-store-registros", "data"),
    Output("pbc-store-archivo", "data"),
    Output("pbc-btn-cargar", "disabled"),
    Input("pbc-upload", "contents"),
    State("pbc-upload", "filename"),
    prevent_initial_call=True,
)
def cb_preview_upload(contents, filename):
    if contents is None:
        return "", None, None, None, True

    try:
        df = db.leer_excel(contents, filename)
    except db.ArchivoInvalidoError as exc:
        return (
            html.Span(str(exc), style={"color": ROJO}),
            None, None, None, True,
        )
    except Exception as exc:
        log.exception("Error al leer el archivo subido")
        return (
            html.Span(_error_ui(exc, "lectura de archivo"), style={"color": ROJO}),
            None, None, None, True,
        )

    r = db.resumen(df)
    partes = [
        html.Span(
            f"{r['filas']} fila(s) validas, hoja \"{r['hoja_leida']}\", "
            f"periodo {r['fecha_min']} a {r['fecha_max']}.",
            style={"color": VERDE, "fontWeight": 600},
        ),
    ]
    if r["filas_sin_fecha_descartadas"]:
        partes.append(html.Div(
            f"Se descartaron {r['filas_sin_fecha_descartadas']} fila(s) sin fecha valida.",
            style={"color": AMBAR, "marginTop": "4px"},
        ))
    partes.append(html.Div(
        "Revise la vista previa y presione \"Cargar a la base de datos\" para confirmar.",
        style={"color": GRIS, "marginTop": "4px"},
    ))

    preview_df = df.drop(columns=["archivo_origen", "usuario_carga"], errors="ignore").head(200)
    tabla = _tabla(preview_df, "pbc-datatable-preview")

    return (
        html.Div(partes),
        tabla,
        df.to_json(date_format="iso", orient="split"),
        filename,
        False,
    )


@callback(
    Output("pbc-confirmar-carga", "displayed"),
    Input("pbc-btn-cargar", "n_clicks"),
    prevent_initial_call=True,
)
def cb_pedir_confirmacion_carga(n):
    return True


@callback(
    Output("pbc-mensaje-carga", "children"),
    Output("pbc-tabla-historial", "children", allow_duplicate=True),
    Input("pbc-confirmar-carga", "submit_n_clicks"),
    State("pbc-store-registros", "data"),
    State("pbc-store-archivo", "data"),
    prevent_initial_call=True,
)
def cb_cargar(n, registros_json, archivo):
    if not registros_json:
        return html.Span("No hay datos para cargar. Suba un archivo primero.",
                          style={"color": ROJO}), dash.no_update

    try:
        df = pd.read_json(registros_json, orient="split")
        df["fecha"] = pd.to_datetime(df["fecha"]).dt.date
        usuario = _usuario_actual()
        msg = db.cargar(df, usuario=usuario, archivo_origen=archivo or "desconocido")
    except Exception as exc:
        log.exception("Error al cargar PowerBI camiones")
        return html.Span(_error_ui(exc, "carga"), style={"color": ROJO}), dash.no_update

    return html.Span(msg, style={"color": VERDE, "fontWeight": 600}), _render_historial()


@callback(
    Output("pbc-tabla-historial", "children"),
    Input("pbc-mensaje-carga", "children"),
)
def cb_historial_inicial(_):
    return _render_historial()


def _render_historial():
    try:
        df = db.historial()
    except Exception as exc:
        return html.Div(_error_ui(exc, "historial"), style={"color": ROJO, "fontSize": "12px"})

    if df.empty:
        return html.Div("Sin cargas registradas todavia.",
                         style={"color": GRIS, "fontSize": "12px"})

    ren = {
        "archivo_origen": "Archivo", "usuario_carga": "Usuario",
        "fecha_desde": "Desde", "fecha_hasta": "Hasta",
        "filas": "Filas", "fecha_carga": "Cargado",
    }
    return _tabla(df.rename(columns=ren), "pbc-datatable-historial")
