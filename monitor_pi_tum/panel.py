"""Diagnóstico de totalizadores: valores originales, sin correcciones."""
from datetime import date, timedelta
import logging

from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from . import db
from . import gestion

log = logging.getLogger(__name__)


def figura_vacia():
    fig = go.Figure()
    fig.update_layout(template="plotly_white", xaxis_title="Fecha/hora",
                      yaxis_title="Valor acumulado", height=480,
                      margin=dict(l=65, r=25, t=30, b=60))
    return fig


def layout():
    hoy = date.today()
    inicio_mes = hoy.replace(day=1).isoformat()
    ayer = (hoy - timedelta(days=1)).isoformat()
    cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Div(titulo, className="text-muted"),
            html.H4("—", id=f"pitum-{nombre}", className="mb-0"),
        ])), md=4, className="mb-3")
        for titulo, nombre in [("Valor inicial", "inicial"), ("Valor final", "final"), ("Variación", "variacion")]
    ])
    return dbc.Container([
        html.H3("Monitoreo Correas Área Seca", className="my-3", style={"color": "#1F4E78"}),
        dbc.Tabs([
            dbc.Tab([
                html.H4("Tendencia del Totalizador Acumulado", className="mt-4"),
                dbc.Card(dbc.CardBody(dbc.Row([
                    dbc.Col([
                        html.Label("Fecha inicio / Fecha término", className="d-block"),
                        dcc.DatePickerRange(id="pitum-fechas", start_date=inicio_mes, end_date=ayer,
                                            display_format="DD-MM-YYYY", first_day_of_week=1,
                                            minimum_nights=0),
                    ], md=6, className="mb-2"),
                    dbc.Col([
                        dbc.Label("Correa", html_for="pitum-correa"),
                        dcc.Dropdown(id="pitum-correa", options=list(db.CORREAS),
                                     value="CV008", clearable=False),
                    ], md=4, className="mb-2"),
                    dbc.Col(dbc.Button("Actualizar", id="pitum-actualizar", n_clicks=0,
                                       color="primary", className="mt-4"), md=2),
                ])), className="mb-3"),
                dcc.Loading(html.Div([
                    html.Div(id="pitum-alerta"), cards,
                    html.P("Variación visual del rango; puede ser negativa y no representa tonelaje corregido.",
                           className="text-muted small"),
                    html.Div(id="pitum-metadata", className="mb-2"),
                    dcc.Graph(id="pitum-grafico", figure=figura_vacia(),
                              config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False}),
                ]), id="pitum-cargando"),
            ], label="Diagnóstico de Correas", tab_id="pitum-diagnostico"),
            dbc.Tab(gestion.layout(),
                    label="Gestión PI / TUM", tab_id="pitum-gestion"),
        ], id="pitum-tabs", active_tab="pitum-diagnostico"),
    ], fluid=True)


def _metadata(df):
    def valores(columna):
        return ", ".join(str(v) for v in df[columna].dropna().unique()) or "Sin información"
    return (f"Fuente: {valores('fuente')} · Resolución (segundos): "
            f"{valores('resolucion_segundos')} · Tipo: {valores('tipo_senal')}")


@callback(
    Output("pitum-grafico", "figure"), Output("pitum-inicial", "children"),
    Output("pitum-final", "children"), Output("pitum-variacion", "children"),
    Output("pitum-metadata", "children"), Output("pitum-alerta", "children"),
    Input("pitum-actualizar", "n_clicks"), State("pitum-fechas", "start_date"),
    State("pitum-fechas", "end_date"), State("pitum-correa", "value"),
    prevent_initial_call=True,
)
def actualizar_tendencia(n_clicks, inicio, fin, correa):
    def aviso(mensaje, color):
        return figura_vacia(), "—", "—", "—", "", dbc.Alert(mensaje, color=color)
    try:
        if not inicio or not fin or date.fromisoformat(inicio) > date.fromisoformat(fin) or correa not in db.CORREAS:
            return aviso("Seleccione fechas válidas (inicio no posterior al término) y una correa.", "warning")
    except (ValueError, TypeError):
        return aviso("Seleccione fechas válidas y una correa.", "warning")
    try:
        df = db.obtener_tendencia_totalizador(inicio, fin, correa)
        if df.empty:
            return aviso("No existen datos para la correa y período seleccionados.", "info")
        df = df.sort_values("timestamp", kind="stable")
        validos = df["valor"].dropna()
        resumen = ("—", "—", "—") if validos.empty else tuple(
            f"{v:,.2f}" for v in (validos.iloc[0], validos.iloc[-1], validos.iloc[-1] - validos.iloc[0]))
        fig = figura_vacia()
        fig.add_trace(go.Scattergl(
            x=df["timestamp"], y=df["valor"], customdata=df[["correa"]],
            mode="lines", name=correa, connectgaps=False, line={"color": "#1F4E78", "shape": "linear"},
            hovertemplate="Correa: %{customdata[0]}<br>Fecha/hora: %{x|%d-%m-%Y %H:%M:%S}"
                          "<br>Valor acumulado: %{y}<extra></extra>",
        ))
        alerta = dbc.Alert("El período contiene únicamente valores NULL.", color="info") if validos.empty else ""
        return fig, *resumen, _metadata(df), alerta
    except Exception:
        log.exception("Error consultando tendencia PI/TUM: correa=%s inicio=%s fin=%s", correa, inicio, fin)
        return aviso("No fue posible consultar la tendencia del totalizador.", "danger")
