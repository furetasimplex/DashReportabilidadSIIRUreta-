"""Diagnóstico de totalizadores: valores originales, sin correcciones."""
from datetime import date, timedelta
import logging
import numpy as np

from dash import Input, Output, State, callback, dcc, html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from balance_m6_contingencia import panel as m6_panel
from lixiviacion.phase_flags import is_dev
from . import db
from . import gestion
from . import factor_camiones_panel

log = logging.getLogger(__name__)
LOCALE_ES = {"format": {
    "shortMonths": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "decimal": ",", "thousands": ".", "grouping": [3],
}}


def numero_chileno(valor, decimales=2):
    return f"{valor:,.{decimales}f}".translate(str.maketrans(",.", ".,"))


def figura_vacia():
    fig = go.Figure()
    fig.update_layout(template="plotly_white", xaxis_title="Fecha y hora",
                      yaxis_title="Totalizador acumulado [TMH]", height=480,
                      separators=",.", showlegend=False,
                      xaxis=dict(tickformat="%d-%b"), yaxis=dict(tickformat=",.2f"),
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
        for titulo, nombre in [("Lectura inicial", "inicial"), ("Lectura final", "final"), ("Variación del totalizador [TMH]", "variacion")]
    ])
    return dbc.Container([
        html.H3("Monitoreo Correas Área Seca", className="my-3", style={"color": "#1F4E78"}),
        dbc.Tabs([
            dbc.Tab([
                html.H4("Tendencia del totalizador acumulado", className="mt-4"),
                dbc.Card(dbc.CardBody(dbc.Row([
                    dbc.Col([
                        html.Label("Rango de fechas", className="d-block"),
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
                    html.P("Diferencia entre la lectura final e inicial del rango. Puede ser negativa y no representa tonelaje corregido.",
                           className="text-muted small"),
                    html.Div(id="pitum-metadata", className="mb-2"),
                    dcc.Graph(id="pitum-grafico", figure=figura_vacia(),
                              config={"displayModeBar": True, "scrollZoom": True, "displaylogo": False,
                                      "locale": "es-CL", "locales": {"es-CL": LOCALE_ES}}),
                ]), id="pitum-cargando"),
                factor_camiones_panel.layout(),
            ], label="Diagnóstico de Correas", tab_id="pitum-diagnostico"),
            dbc.Tab(gestion.layout(),
                    label="Gestión PI / TUM", tab_id="pitum-gestion"),
            *([dbc.Tab(m6_panel.layout(), label="Contingencia para Balance de Masa", tab_id="pitum-contingencia-m6")] if is_dev() else []),
        ], id="pitum-tabs", active_tab="pitum-diagnostico"),
    ], fluid=True)


def _metadata(df, visibles):
    def valores(columna):
        return ", ".join(str(v) for v in df[columna].dropna().unique()) or "Sin información"
    resolucion = ", ".join(numero_chileno(v, 0) for v in df['resolucion_segundos'].dropna().unique()) or "—"
    tipo = valores('tipo_senal').replace('TOTALIZADOR', 'Totalizador')
    resumen = (f"Visualización resumida: {numero_chileno(visibles, 0)} de {numero_chileno(len(df), 0)} lecturas."
               if visibles < len(df) else f"Visualización completa: {numero_chileno(len(df), 0)} lecturas.")
    return html.Div([
        html.Div([f"Resolución: {resolucion} s · {resumen} ",
                  html.Span("ⓘ", id="pitum-info-tecnica", tabIndex=0,
                            **{"aria-label": "Información técnica del totalizador"}, style={"cursor": "help"})]),
        html.Div("Los indicadores consideran todas las lecturas."),
        html.Small("Seleccione un rango menor para visualizar mayor detalle.", className="text-muted") if visibles < len(df) else None,
        dbc.Tooltip([f"Fuente: {valores('fuente')}", html.Br(), f"Tipo de señal: {tipo}",
                     html.Br(), f"Resolución original: {resolucion} s"],
                    target="pitum-info-tecnica", trigger="hover focus", placement="bottom"),
    ])


def _puntos_visuales(df, objetivo=6000):
    """Selecciona lecturas originales; preserva extremos y fronteras de NULL.

    El objetivo es orientativo: las discontinuidades nunca se eliminan para
    cumplir un límite. No se usa esta selección para indicadores ni cálculos.
    """
    if len(df) <= objetivo:
        return df
    valores = df['valor'].to_numpy()
    nulos = df['valor'].isna().to_numpy()
    seleccion = {0, len(df) - 1}
    cambios = np.flatnonzero(nulos[1:] != nulos[:-1])
    seleccion.update(cambios.tolist())
    seleccion.update((cambios + 1).tolist())
    for bloque in np.array_split(np.arange(len(df)), max(1, objetivo // 4)):
        seleccion.update((int(bloque[0]), int(bloque[-1])))
        validos = bloque[~nulos[bloque]]
        if len(validos):
            seleccion.add(int(validos[np.argmin(valores[validos])]))
            seleccion.add(int(validos[np.argmax(valores[validos])]))
    # Conserva ambos lados de cada descenso (posible reinicio del totalizador).
    descensos = np.flatnonzero(valores[1:] < valores[:-1])
    seleccion.update(descensos.tolist())
    seleccion.update((descensos + 1).tolist())
    return df.iloc[sorted(seleccion)]


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
            numero_chileno(v) for v in (validos.iloc[0], validos.iloc[-1], validos.iloc[-1] - validos.iloc[0]))
        fig = figura_vacia()
        visual = _puntos_visuales(df)
        fig.update_xaxes(type="date")
        fig.add_trace(go.Scatter(
            x=visual["timestamp"], y=visual["valor"], customdata=visual[["correa"]],
            mode="lines", name=correa, connectgaps=False, line={"color": "#1F4E78", "shape": "linear"},
            hovertemplate="Fecha y hora: %{x|%d-%m-%Y %H:%M:%S}<br>Correa: %{customdata[0]}"
                          "<br>Totalizador acumulado [TMH]: %{y:,.2f}<extra></extra>",
        ))
        alerta = dbc.Alert("El período contiene únicamente valores NULL.", color="info") if validos.empty else ""
        metadata = _metadata(df, len(visual))
        return fig, *resumen, metadata, alerta
    except Exception:
        log.exception("Error consultando tendencia PI/TUM: correa=%s inicio=%s fin=%s", correa, inicio, fin)
        return aviso("No fue posible consultar la tendencia del totalizador.", "danger")
