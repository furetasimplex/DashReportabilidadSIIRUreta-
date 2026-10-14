"""Panel Dash para administrar versiones del polinomio de acido."""
import logging
import math
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pandas as pd
from dash import Input, Output, State, callback, ctx, dcc, html, no_update
import dash_bootstrap_components as dbc
from flask import has_request_context, session

from . import db

log = logging.getLogger(__name__)
PREFIX = "polinomio-acido-"
SESSION_KEY = "polinomio_acido_confirmacion"
ETIQUETAS_PARAMETROS = {nombre: etiqueta for nombre, etiqueta, _ in db.PARAMETROS}
POSICIONES_PARAMETROS = {
    nombre: f"P{indice:02d}"
    for indice, nombre in enumerate(db.NOMBRES_PARAMETROS, start=1)
}


def usuario_actual():
    value = session.get("user") if has_request_context() else None
    return value.strip() if isinstance(value, str) and value.strip() else None


def numero(value, decimales=6):
    if value is None or pd.isna(value):
        return "—"
    return f"{Decimal(str(value)):,.{decimales}f}".translate(str.maketrans(",.", ".,"))


def fecha(value):
    if value is None or pd.isna(value):
        return "—"
    return pd.Timestamp(value).strftime("%d-%m-%Y %H:%M")


def comentario_texto(value):
    if value is None:
        return "Sin comentario"
    try:
        if pd.isna(value):
            return "Sin comentario"
    except (TypeError, ValueError):
        pass
    texto = str(value)
    return texto if texto else "Sin comentario"


def fecha_solo(value):
    if value is None or pd.isna(value):
        return "En uso"
    return pd.Timestamp(value).strftime("%d-%m-%Y")


def _campo(nombre, etiqueta):
    limites = {"min": 0, "max": 1} if nombre.startswith("umbral_") else {}
    categoria = categoria_parametro(nombre)
    return dbc.Col([
        dbc.Label([
            html.Span(className=f"polinomio-color-dot {categoria}"),
            html.Span(POSICIONES_PARAMETROS[nombre], className="polinomio-posicion"),
            etiqueta,
        ], html_for=PREFIX + nombre, className="fw-semibold"),
        dbc.Input(id=PREFIX + nombre, type="number", step=0.000001,
                  className=f"polinomio-input {categoria}", **limites),
        dbc.FormText([
            html.I(className="bi bi-link-45deg me-1"),
            "Parámetro: ", html.Code(nombre),
        ]),
    ], md=4, className=f"mb-3 polinomio-campo {categoria}")


def categoria_parametro(nombre):
    if nombre.startswith("umbral_"):
        return "umbral"
    if nombre == "tasa_minima":
        return "minimo"
    if "factor_cus" in nombre:
        return "cus"
    if "factor_co3" in nombre:
        return "co3"
    return "base"


def numero_exacto(value):
    """Presenta toda la precision recibida, sin redondear ni rellenar ceros."""
    valor = Decimal(str(value))
    texto = format(valor, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _parametros_grafico(valores):
    if len(valores) != len(db.NOMBRES_PARAMETROS):
        raise ValueError("Configuración incompleta")
    resultado = {}
    for nombre, valor in zip(db.NOMBRES_PARAMETROS, valores):
        numero_valor = float(valor)
        if not math.isfinite(numero_valor):
            raise ValueError("Configuración incompleta")
        resultado[nombre] = numero_valor
    return resultado


def construir_esquema(p):
    """Representa las ramas y vincula cada valor con su campo editable."""

    def valor(nombre):
        return html.Label([
            html.Span(POSICIONES_PARAMETROS[nombre], className="polinomio-chip-posicion"),
            html.Strong(numero_exacto(p[nombre]), className="polinomio-chip-valor"),
            html.Span(ETIQUETAS_PARAMETROS[nombre], className="polinomio-chip-etiqueta"),
            html.Small(nombre, className="polinomio-chip-nombre"),
            html.I(className="bi bi-pencil-square polinomio-chip-editar"),
        ], htmlFor=PREFIX + nombre,
           title=f"Editar {ETIQUETAS_PARAMETROS[nombre]}",
           className=f"polinomio-chip {categoria_parametro(nombre)}")

    formula_sulfuro = [valor("tasa_base"), " + ", valor("factor_co3"), " × CO3"]
    prueba_oxido = [
        valor("factor_cus_co3_sobre_025"), " × Ln(CuS) + ",
        valor("tasa_base_co3_sobre_025"), " + ",
        valor("factor_co3_co3_sobre_025"), " × CO3",
    ]
    formula_oxido = [
        valor("factor_cus_mineral_oxido"), " × Ln(CuS) + ",
        valor("tasa_basal_mineral_oxido"), " + ",
        valor("factor_co3_mineral_oxido"), " × CO3",
    ]

    return dbc.Card([
        dbc.CardBody([
            dbc.Alert([
                html.I(className="bi bi-cursor me-2"),
                html.Strong("Edición guiada: "),
                "cada código P01–P11 identifica una posición exacta. Haz clic en el parámetro "
                "coloreado para ir directamente a su campo.",
            ], color="primary", className="mb-3"),
            html.Div([
                html.Span("Umbrales", className="polinomio-leyenda umbral"),
                html.Span("Tasa mínima", className="polinomio-leyenda minimo"),
                html.Span("Bases", className="polinomio-leyenda base"),
                html.Span("Factores CuS", className="polinomio-leyenda cus"),
                html.Span("Factores CO3", className="polinomio-leyenda co3"),
            ], className="polinomio-leyendas mb-3"),
            dbc.Row([
                dbc.Col(html.Div("Ácido", className="polinomio-ficha-titulo"), md=2),
                dbc.Col(html.Div([
                    html.H5("Ácido de acuerdo a polinomio:", className="mb-3"),
                    html.Div([
                        html.Strong(["- Mineral Sulfuro (Rs < ", valor("umbral_mineral"), "):"]),
                        html.Div(["Para CO3 ≤ ", valor("umbral_co3"),
                                  " usar tasa de ", valor("tasa_minima"), " kg/t."],
                                 className="polinomio-ficha-linea"),
                        html.Div(["Para CO3 > ", valor("umbral_co3"),
                                  " utilizar polinomio [kg/t]: ", *formula_sulfuro,
                                  " (mínimo ", valor("tasa_minima"), " kg/t)."],
                                 className="polinomio-ficha-linea"),
                    ], className="polinomio-ficha-seccion sulfuro"),
                    html.Div([
                        html.Strong(["- Mineral Óxido (Rs ≥ ", valor("umbral_mineral"), "):"]),
                        html.Div(["Utilizar polinomio (mínimo ", valor("tasa_minima"),
                                  " kg/t) [kg/t]: ", *formula_oxido],
                                 className="polinomio-ficha-linea"),
                        html.Div([html.Strong("Validación del mínimo: "), *prueba_oxido,
                                  " < ", valor("tasa_minima"), " → usar tasa mínima."],
                                 className="polinomio-ficha-linea tecnica"),
                        html.Div("Si CuS es nulo o menor o igual a cero, la función devuelve 0 kg/t.",
                                 className="polinomio-ficha-linea tecnica"),
                    ], className="polinomio-ficha-seccion oxido"),
                ], className="polinomio-ficha-contenido"), md=10),
            ], className="g-0 polinomio-ficha"),
            html.Div("Los parámetros se muestran con toda su precisión, sin redondeo visual. "
                     "La función SQL conserva su salida contractual DECIMAL(18,2).",
                     className="small text-muted mt-3"),
        ]),
    ], className="mb-3 polinomio-esquema")


def layout():
    grupos = []
    for grupo in dict.fromkeys(item[2] for item in db.PARAMETROS):
        campos = [_campo(nombre, etiqueta) for nombre, etiqueta, item_grupo in db.PARAMETROS
                  if item_grupo == grupo]
        grupos.append(dbc.Card(dbc.CardBody([
            html.H5(grupo, className="card-title"), dbc.Row(campos)
        ]), className="mb-3"))
    return html.Div([
        html.H3("Polinomio Ácido", className="mb-1"),
        html.P(
            "Cada versión se aplica según la fecha del dato. Los periodos históricos permanecen congelados.",
            className="text-muted",
        ),
        dcc.Store(id=PREFIX + "refresh", data=0),
        dcc.Store(id=PREFIX + "version-vigente"),
        dcc.Store(id=PREFIX + "token"),
        html.Div(id=PREFIX + "estado", className="mb-3"),
        dbc.Card(dbc.CardBody([
            dbc.Label("Consultar configuración aplicable en una fecha",
                      html_for=PREFIX + "fecha-consulta", className="fw-semibold"),
            dcc.DatePickerSingle(id=PREFIX + "fecha-consulta", date=date.today(),
                                 display_format="DD-MM-YYYY"),
            html.Div(id=PREFIX + "consulta-fecha-resultado", className="mt-2"),
        ]), className="mb-3"),
        html.H4("Fórmula vigente", className="mt-3"),
        html.P("Los colores y nombres técnicos relacionan cada valor con su campo editable.",
               className="small text-muted"),
        html.Div(id=PREFIX + "vista-funcion"),
        *grupos,
        dbc.Card(dbc.CardBody([
            dbc.Label("Inicio de vigencia de la nueva configuración",
                      html_for=PREFIX + "vigencia-desde", className="fw-semibold"),
            dcc.DatePickerSingle(id=PREFIX + "vigencia-desde", display_format="DD-MM-YYYY",
                                 min_date_allowed=date.today()),
            dbc.FormText("Debe ser posterior a la última vigencia registrada."),
        ]), className="mb-3"),
        dbc.Label("Comentario del cambio (opcional)", html_for=PREFIX + "comentario"),
        dbc.Textarea(id=PREFIX + "comentario", maxLength=500, className="mb-3"),
        dbc.Button("Revisar y guardar", id=PREFIX + "revisar", color="primary"),
        html.Div(id=PREFIX + "resultado", className="mt-3"),
        html.H4("Historial de versiones", className="mt-4"),
        html.Div(id=PREFIX + "historial"),
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Confirmar nueva configuración"), close_button=False),
            dbc.ModalBody(id=PREFIX + "resumen"),
            dbc.ModalFooter([
                dbc.Button("Cancelar", id=PREFIX + "cancelar", color="secondary"),
                dbc.Button("Confirmar y enviar", id=PREFIX + "confirmar", color="primary"),
            ]),
        ], id=PREFIX + "modal", is_open=False, backdrop="static", keyboard=False),
    ], className="p-3")


def _detalle_parametros(registro):
    filas = [html.Tr([html.Td(grupo), html.Td(etiqueta), html.Td(numero(registro[nombre]))])
             for nombre, etiqueta, grupo in db.PARAMETROS]
    return dbc.Table([
        html.Thead(html.Tr([html.Th("Grupo"), html.Th("Parámetro"), html.Th("Valor")])),
        html.Tbody(filas),
    ], bordered=True, striped=True, size="sm", responsive=True)


def mostrar_historial(frame):
    if frame is None or frame.empty:
        return dbc.Alert("No existen versiones registradas.", color="warning")
    items = []
    for registro in frame.to_dict("records"):
        hasta = fecha_solo(registro.get("vigencia_hasta"))
        estado = registro.get("estado_vigencia", "")
        titulo = (f"Versión {registro['configuracion_id']} · "
                  f"{fecha_solo(registro['vigencia_desde'])} — {hasta} · {estado}")
        items.append(dbc.AccordionItem([
            html.P([html.Strong("Estado: "), estado]),
            html.P([html.Strong("Registrada por: "), registro['usuario_submit'],
                    " el ", fecha(registro['fecha_submit'])]),
            html.P("Comentario: " + comentario_texto(registro.get("comentario"))),
            _detalle_parametros(registro),
        ], title=titulo, item_id=str(registro["configuracion_id"])))
    return dbc.Accordion(items, start_collapsed=True, always_open=False)


def _estado_vigente(registro):
    if not registro:
        return dbc.Alert("No existe una configuración vigente.", color="warning")
    return dbc.Card(dbc.CardBody([
        html.H5(f"Versión vigente hoy: {registro['configuracion_id']}"),
        html.Div(f"Vigencia: {fecha_solo(registro['vigencia_desde'])} — "
                 f"{fecha_solo(registro.get('vigencia_hasta'))}."),
        html.Div(f"Enviada por {registro['usuario_submit']} el {fecha(registro['fecha_submit'])}."),
        html.Div("Comentario: " + comentario_texto(registro.get("comentario")), className="small"),
    ]), color="light")


@callback(
    Output(PREFIX + "estado", "children"), Output(PREFIX + "historial", "children"),
    Output(PREFIX + "version-vigente", "data"),
    *[Output(PREFIX + nombre, "value") for nombre in db.NOMBRES_PARAMETROS],
    Input(PREFIX + "refresh", "data"),
)
def cargar_configuracion(_refresh):
    try:
        vigente = db.obtener_configuracion_vigente()
        ultima = db.obtener_ultima_configuracion()
        historial = db.obtener_historial()
        valores = [float(ultima[nombre]) if ultima else None for nombre in db.NOMBRES_PARAMETROS]
        version_data = ({"configuracion_id": ultima["configuracion_id"],
                         "vigencia_desde": str(ultima["vigencia_desde"])} if ultima else None)
        return (_estado_vigente(vigente), mostrar_historial(historial),
                version_data, *valores)
    except Exception:
        log.exception("No fue posible cargar el polinomio de acido")
        return (dbc.Alert("No fue posible consultar la configuración del polinomio ácido.", color="danger"),
                "", None, *([None] * len(db.NOMBRES_PARAMETROS)))


@callback(
    Output(PREFIX + "consulta-fecha-resultado", "children"),
    Input(PREFIX + "fecha-consulta", "date"),
    Input(PREFIX + "refresh", "data"),
)
def consultar_fecha(fecha_consulta, _refresh):
    if not fecha_consulta:
        return dbc.Alert("Seleccione una fecha.", color="info")
    try:
        registro = db.obtener_configuracion_para_fecha(fecha_consulta)
        if not registro:
            return dbc.Alert("No existe configuración para esa fecha.", color="warning")
        return html.Div([
            html.Strong(f"Versión {registro['configuracion_id']}"),
            html.Span(f" · {fecha_solo(registro['vigencia_desde'])} — "
                      f"{fecha_solo(registro.get('vigencia_hasta'))}"),
        ])
    except Exception:
        log.exception("No fue posible consultar la configuración por fecha")
        return dbc.Alert("No fue posible consultar esa fecha.", color="danger")


@callback(
    Output(PREFIX + "vista-funcion", "children"),
    *[Input(PREFIX + nombre, "value") for nombre in db.NOMBRES_PARAMETROS],
)
def actualizar_vista_funcion(*valores):
    try:
        parametros = _parametros_grafico(valores)
        return construir_esquema(parametros)
    except (TypeError, ValueError, OverflowError):
        return dbc.Alert(
            "Complete los 11 parámetros con valores válidos para visualizar la función.",
            color="info",
        )


def preparar_confirmacion(valores, comentario, configuracion_esperada, vigencia_desde):
    if not vigencia_desde:
        raise ValueError("Debe indicar la fecha de inicio de vigencia.")
    payload = db.validar_configuracion(
        valores, usuario_actual(), comentario, vigencia_desde=vigencia_desde)
    if configuracion_esperada is None:
        raise ValueError("No existe una versión vigente para revisar.")
    version_id = int(configuracion_esperada["configuracion_id"])
    ultima_fecha = pd.Timestamp(configuracion_esperada["vigencia_desde"]).date()
    if payload["vigencia_desde"] <= ultima_fecha:
        raise ValueError("La nueva vigencia debe comenzar después de la última configuración.")
    token = uuid4().hex
    session[SESSION_KEY] = {
        "token": token, "configuracion_esperada": version_id,
        "vigencia_desde": payload["vigencia_desde"].isoformat(),
        "valores": {nombre: str(payload[nombre]) for nombre in db.NOMBRES_PARAMETROS},
        "usuario": payload["usuario_submit"], "comentario": payload["comentario"],
    }
    fin_anterior = payload["vigencia_desde"] - timedelta(days=1)
    resumen = html.Div([
        dbc.Alert(f"La versión {version_id} quedará vigente hasta "
                  f"{fecha_solo(fin_anterior)}. La nueva versión comenzará el "
                  f"{fecha_solo(payload['vigencia_desde'])}.",
                  color="warning"),
        _detalle_parametros(payload), html.P("Usuario: " + payload["usuario_submit"]),
        html.P("Comentario: " + comentario_texto(payload["comentario"])),
    ])
    return token, resumen


def confirmar_configuracion(token):
    pendiente = session.get(SESSION_KEY) if has_request_context() else None
    if (not pendiente or pendiente.get("token") != token
            or pendiente.get("usuario") != usuario_actual()):
        raise ValueError("La confirmación no está vigente. Revise nuevamente la configuración.")
    resultado = db.insertar_configuracion(
        pendiente["valores"], pendiente["usuario"], pendiente["comentario"],
        pendiente["configuracion_esperada"], pendiente["vigencia_desde"],
    )
    session.pop(SESSION_KEY, None)
    return resultado


_INPUT_STATES = [State(PREFIX + nombre, "value") for nombre in db.NOMBRES_PARAMETROS]


@callback(
    Output(PREFIX + "modal", "is_open"), Output(PREFIX + "resumen", "children"),
    Output(PREFIX + "token", "data"), Output(PREFIX + "resultado", "children"),
    Output(PREFIX + "refresh", "data"),
    Input(PREFIX + "revisar", "n_clicks"), Input(PREFIX + "cancelar", "n_clicks"),
    Input(PREFIX + "confirmar", "n_clicks"), *_INPUT_STATES,
    State(PREFIX + "comentario", "value"), State(PREFIX + "vigencia-desde", "date"),
    State(PREFIX + "version-vigente", "data"),
    State(PREFIX + "token", "data"), State(PREFIX + "refresh", "data"),
    prevent_initial_call=True,
)
def gestionar(_revisar, _cancelar, _confirmar, *estados):
    valores_lista = estados[:len(db.NOMBRES_PARAMETROS)]
    comentario, vigencia_desde, version, token, refresh = estados[len(db.NOMBRES_PARAMETROS):]
    accion = ctx.triggered_id
    try:
        if accion == PREFIX + "cancelar":
            if has_request_context():
                session.pop(SESSION_KEY, None)
            return False, "", None, no_update, no_update
        if accion == PREFIX + "revisar":
            challenge, resumen = preparar_confirmacion(
                dict(zip(db.NOMBRES_PARAMETROS, valores_lista)), comentario,
                version, vigencia_desde)
            return True, resumen, challenge, "", no_update
        if accion == PREFIX + "confirmar":
            resultado = confirmar_configuracion(token)
            mensaje = dbc.Alert(
                f"Configuración {resultado['configuracion_id']} registrada correctamente.", color="success")
            return False, "", None, mensaje, (refresh or 0) + 1
    except Exception as exc:
        log.exception("No se completo la administracion del polinomio de acido")
        if has_request_context():
            session.pop(SESSION_KEY, None)
        mensaje = str(exc) if isinstance(exc, ValueError) else (
            "No fue posible guardar la configuración. Revise la conexión y vuelva a intentarlo.")
        return False, "", None, dbc.Alert(mensaje, color="danger"), no_update
    return (no_update,) * 5
