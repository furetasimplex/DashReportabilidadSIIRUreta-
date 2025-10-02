# tabs/tab4.py
import pandas as pd
import numpy as np
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import plotly.express as px
import plotly.figure_factory as ff
from db_connection import get_connection
from scipy import stats
from skgstat import Variogram
import base64

# ---------------- Helpers ----------------
def _empty_fig(title="Sin datos"):
    fig = go.Figure()
    fig.update_layout(template="plotly_white",
                      margin=dict(l=10, r=10, t=40, b=10),
                      title=title)
    return fig

def _to_csv_href(df):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    return "data:text/csv;base64," + b64

# ---------------- Layout ----------------
def render_tab4():
    conn = get_connection()
    fechas_df = pd.read_sql("SELECT MIN(CAST(Fecha AS DATE)) as min_fecha, MAX(CAST(Fecha AS DATE)) as max_fecha FROM inventar_SpcHidr.vista_control_torres", conn)
    conn.close()

    torres = ['TM1', 'TM2']
    min_fecha = fechas_df['min_fecha'][0]
    max_fecha = fechas_df['max_fecha'][0]

    return html.Div([
        dbc.Alert([html.I(className="bi bi-broadcast-pin me-2"),
                   "Control de Torres de Muestreo"],
                  color="primary", className="mb-3"),

        # Filtros superiores
        dbc.Card([
            dbc.CardHeader(html.H5("Parámetros de consulta", className="mb-0")),
            dbc.CardBody(
                dbc.Row([
                      dbc.Col(
                        html.Div([
                        html.Label("Seleccionar fecha: ", style={'marginLeft': '10px', 'marginRight': '10px'}),
                        dcc.DatePickerRange(
                            id='fecha-rango-tab4',
                            min_date_allowed=min_fecha,
                            max_date_allowed=max_fecha,
                            start_date=min_fecha,
                            end_date=max_fecha,
                            display_format='YYYY-MM-DD'
                        ),
                    ], style={'display': 'flex', 'alignItems': 'center'}),
                                    
                                    md=6, lg=4
                                ),
                    dbc.Col([
                        html.Label("Torre", className="fw-semibold"),
                        dbc.Checklist(
                            id='torre-selector-tab4',
                            options=[{"label": t, "value": t} for t in torres],
                            value=torres, inline=True
                        ),
                    ], md=4, lg=4),
                    dbc.Col([
                        html.Label("Elemento a analizar", className="fw-semibold"),
                        dcc.Dropdown(id='elemento-tab4', multi=False, placeholder="Seleccione un elemento…")
                    ], md=3, lg=3),
                ], className="g-3")
            ),
            dbc.CardFooter(
                dbc.Button([html.I(className="bi bi-arrow-repeat me-2"), "Actualizar"],
                           id="actualizar-tab4", n_clicks=0, color="primary")
            )
        ], className="mb-4 shadow-sm border-0"),

        # Sección 1
        dbc.Card([
            dbc.CardHeader(html.H5("Sección 1: Representatividad por torre y turno", className="mb-0")),
            dbc.CardBody([
                html.Div(id="kpi-tab4", className="mb-3"),
                dbc.Row([
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-represent-tab4"), type="default"), lg=6, className="mb-3"),
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-dist-tab4"), type="default"), lg=6, className="mb-3"),
                ], className="g-3"),
            ])
        ], className="mb-4 shadow-sm border-0"),

        # Sección 2
        dbc.Card([
            dbc.CardHeader(html.H5("Sección 2: Análisis del elemento seleccionado", className="mb-0")),
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-linea-comp-tab4"), type="default"), lg=6, className="mb-3"),
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-cusum-tab4"), type="default"), lg=6, className="mb-3"),
                ], className="g-3")
            )
        ], className="mb-4 shadow-sm border-0"),

        # Sección 3
        dbc.Card([
            dbc.CardHeader(html.H5("Sección 3: Correlación valores", className="mb-0")),
            dbc.CardBody(dcc.Loading(dcc.Graph(id="graf-correlacion-tab4"), type="default"))
        ], className="mb-4 shadow-sm border-0"),

        # Sección 4
        dbc.Card([
            dbc.CardHeader(html.H5("Sección 4: Prueba de Sesgo entre Torres", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-sesgo-tab4"), type="default"), lg=6, className="mb-3"),
                    dbc.Col(dcc.Loading(dcc.Graph(id="graf-sesgo-dist-tab4"), type="default"), lg=6, className="mb-3"),
                ], className="g-3"),
                html.Div(id="resultado-sesgo-tab4", className="fw-semibold mt-2")
            ])
        ], className="mb-4 shadow-sm border-0"),

        # Sección 5
        dbc.Card([
            dbc.CardHeader(html.H5("Sección 5: Variografía del elemento seleccionado", className="mb-0")),
            dbc.CardBody([
                dcc.Loading(dcc.Graph(id="graf-variograma-tab4"), type="default"),
                html.Hr(),
                html.H5("📋 Parámetros de Variogramas por Torre", className="mt-2"),
                html.Div(id="tabla-variogramas-tab4")
            ])
        ], className="mb-4 shadow-sm border-0"),

        # Descargas
        dbc.Card([
            dbc.CardHeader(html.H6("Descargas", className="mb-0")),
            dbc.CardBody(dbc.Stack([
                html.A("📌  Descargar datos representatividad", id="descargar-represent-tab4",
                       download="representatividad.csv", href="", target="_blank"),
                html.A("📌  Descargar datos elemento", id="descargar-elemento-tab4",
                       download="elemento.csv", href="", target="_blank")
            ], gap=2))
        ], className="mb-4 shadow-sm border-0"),
    ])

# ---------------- Callbacks ----------------
def register_tab4_callbacks(app):

    @app.callback(
        [
            Output("elemento-tab4", "options"),
            Output("graf-represent-tab4", "figure"),
            Output("graf-dist-tab4", "figure"),
            Output("graf-linea-comp-tab4", "figure"),
            Output("graf-cusum-tab4", "figure"),
            Output("graf-correlacion-tab4", "figure"),
            Output("graf-sesgo-tab4", "figure"),
            Output("graf-sesgo-dist-tab4", "figure"),
            Output("resultado-sesgo-tab4", "children"),
            Output("kpi-tab4", "children"),
            Output("descargar-represent-tab4", "href"),
            Output("descargar-elemento-tab4", "href"),
            Output("graf-variograma-tab4", "figure"),
            Output("tabla-variogramas-tab4", "children"),
        ],
        Input("actualizar-tab4", "n_clicks"),
        State("fecha-rango-tab4", "start_date"),
        State("fecha-rango-tab4", "end_date"),
        State("torre-selector-tab4", "value"),
        State("elemento-tab4", "value"),
        prevent_initial_call=False
    )
    def actualizar_graficos(n_clicks, start_date, end_date, torres, elemento):
        # Leer datos
        conn = get_connection()
        query = f"""
            SELECT Torre,Turno,Fecha,Representatividad FROM inventar_SpcHidr.vista_control_torres
            WHERE Fecha
            BETWEEN '{start_date}' AND '{end_date}'
        """
        print(query)
        print(conn)
        df = pd.read_sql(query, conn)
        print(df)
        conn.close()

        # Filtrar torres + preparar tipos
        torres = torres or ['TM1', 'TM2']
        df = df[df['Torre'].isin(torres)]
        if df.empty:
            opts = []
            return (opts, *_empty_all())

        df['Fecha'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['Representatividad'] = pd.to_numeric(df['Representatividad'], errors='coerce').fillna(0)

        # Opciones de elemento (todas numéricas excepto meta columnas)
        meta_cols = ['Fecha', 'Torre', 'Turno', 'Representatividad', 'Apilado']
        numeric_cols = [c for c in df.select_dtypes(include='number').columns if c not in meta_cols]
        opts = [{"label": c, "value": c} for c in sorted(numeric_cols)]

        # Si no hay elemento seleccionado todavía -> placeholders
        if not elemento or elemento not in df.columns or not pd.api.types.is_numeric_dtype(df[elemento]):
            rep_fig = _empty_fig("Seleccione un elemento para continuar")
            dist_fig = _empty_fig("Seleccione un elemento para continuar")
            linea_fig = _empty_fig("Seleccione un elemento para continuar")
            cusum_fig = _empty_fig("Seleccione un elemento para continuar")
            corr_fig = _empty_fig("Seleccione un elemento para continuar")
            sesgo_fig = _empty_fig("Seleccione un elemento para continuar")
            sesgo_dist_fig = _empty_fig("Seleccione un elemento para continuar")
            res_sesgo = "—"
            kpi = html.Div("Seleccione filtros para ver KPIs", className="text-muted")
            rep_href = ""
            elem_href = ""
            variog_fig = _empty_fig("Seleccione un elemento para continuar")
            tabla_vario = html.Div()

            # Aún así, podemos mostrar representatividad básica
            if not df.empty:
                rep_fig = px.line(df, x='Fecha', y='Representatividad', color='Torre', line_dash='Turno', markers=True)
                rep_fig.update_layout(title="Representatividad en el tiempo")
                dist_fig = px.histogram(df, x='Representatividad', color='Torre', marginal='rug', nbins=30,
                                        title="Distribución Representatividad")
                kpi = _kpi_rep(df)

                rep_href = _to_csv_href(df[['Fecha','Torre','Turno','Representatividad']])

            return (opts, rep_fig, dist_fig, linea_fig, cusum_fig, corr_fig,
                    sesgo_fig, sesgo_dist_fig, res_sesgo, kpi, rep_href, elem_href,
                    variog_fig, tabla_vario)

        # --------- Sección 1: Representatividad ----------
        rep_fig = px.line(df, x='Fecha', y='Representatividad', color='Torre', line_dash='Turno', markers=True)
        rep_fig.update_layout(title="Representatividad en el tiempo")

        dist_fig = px.histogram(df, x='Representatividad', color='Torre', marginal='rug', nbins=30,
                                title="Distribución Representatividad")

        kpi = _kpi_rep(df)

        # --------- Sección 2: Línea + CUSUM ----------
        linea_fig = px.line(df, x='Fecha', y=elemento, color='Torre', line_dash='Turno', markers=True)
        mean_e = df[elemento].mean()
        std_e = df[elemento].std()
        linea_fig.add_hline(y=mean_e + std_e, line_dash="dash", line_color="blue")
        linea_fig.add_hline(y=mean_e - std_e, line_dash="dash", line_color="blue")
        linea_fig.add_hline(y=mean_e + 2*std_e, line_dash="dot", line_color="red")
        linea_fig.add_hline(y=mean_e - 2*std_e, line_dash="dot", line_color="red")
        linea_fig.update_layout(title=f"Tendencia del elemento {elemento}")

        df_sorted = df.sort_values("Fecha")
        df_sorted['cusum'] = (df_sorted[elemento] - mean_e).cumsum()
        cusum_fig = px.line(df_sorted, x='Fecha', y='cusum', color='Torre', line_dash='Turno', title="CUSUM")

        # --------- Sección 3: Correlación TM1 vs TM2 ----------
        df_pivot = df.pivot_table(index="Fecha", columns="Torre", values=elemento)
        if 'TM1' in df_pivot.columns and 'TM2' in df_pivot.columns:
            corr_fig = px.scatter(df_pivot.reset_index(), x='TM1', y='TM2', trendline='ols',
                                  title="Correlación TM1 vs TM2")
            min_val = np.nanmin([df_pivot['TM1'].min(), df_pivot['TM2'].min()])
            max_val = np.nanmax([df_pivot['TM1'].max(), df_pivot['TM2'].max()])
            corr_fig.add_trace(go.Scatter(x=[min_val, max_val], y=[min_val, max_val],
                                          mode='lines', name='y = x',
                                          line=dict(dash='dot', color='gray')))
        else:
            corr_fig = _empty_fig("No hay TM1 y TM2 simultáneamente")

        # --------- Sección 4: Sesgo ----------
        if all(t in df_pivot.columns for t in ['TM1', 'TM2']):
            df_p = df_pivot[['TM1', 'TM2']].dropna()
            if not df_p.empty:
                t_stat, p_value = stats.ttest_rel(df_p['TM1'], df_p['TM2'])
                sesgo_fig = go.Figure()
                sesgo_fig.add_trace(go.Scatter(x=df_p.index, y=df_p['TM1'], name='TM1'))
                sesgo_fig.add_trace(go.Scatter(x=df_p.index, y=df_p['TM2'], name='TM2'))
                sesgo_fig.update_layout(title="Sesgo TM1 vs TM2", template="plotly_white")

                dif = df_p['TM1'] - df_p['TM2']
                sesgo_dist_fig = px.histogram(dif, nbins=30, title="Distribución de la diferencia TM1 - TM2")
                res_sesgo = f"t = {t_stat:.2f}, p = {p_value:.4f}"
            else:
                sesgo_fig = _empty_fig("Sin datos pareados TM1/TM2")
                sesgo_dist_fig = _empty_fig("Sin datos pareados TM1/TM2")
                res_sesgo = "No hay datos suficientes para calcular el sesgo."
        else:
            sesgo_fig = _empty_fig("Faltan torres TM1/TM2")
            sesgo_dist_fig = _empty_fig("Faltan torres TM1/TM2")
            res_sesgo = "No se puede calcular el sesgo: se necesita TM1 y TM2."

        # --------- Sección 5: Variograma ----------
        variog_fig = go.Figure()
        tabla_variogramas = []

        for torre in df['Torre'].unique():
            df_t = df[df['Torre'] == torre][['Fecha', elemento]].dropna().sort_values("Fecha")
            if len(df_t) > 5:
                coords = df_t['Fecha'].map(pd.Timestamp.toordinal).values.reshape(-1, 1)
                values = df_t[elemento].values
                try:
                    V = Variogram(coords, values, normalize=False, n_lags=10)
                    h_vals = V.bins
                    gamma_vals = V.experimental
                    model_vals = V.fitted_model(h_vals)

                    variog_fig.add_trace(go.Scatter(x=h_vals, y=gamma_vals,
                                                    mode='lines+markers', name=f'{torre} Experimental'))
                    variog_fig.add_trace(go.Scatter(x=h_vals, y=model_vals,
                                                    mode='lines', name=f'{torre} Modelo'))

                    tabla_variogramas.append({
                        "Torre": torre,
                        "Modelo": V.model.__name__,
                        "Nugget": round(V.parameters[0], 4),
                        "Sill": round(V.parameters[0] + V.parameters[1], 4),
                        "Range": round(V.parameters[2], 2),
                        "Effective Range": round(V.describe().get("effective_range", np.nan), 2)
                    })
                except Exception:
                    continue

        if variog_fig.data:
            variog_fig.update_layout(title="Variograma Experimental y Modelo por Torre",
                                     xaxis_title="Lag (días)", yaxis_title="Semivarianza γ(h)",
                                     template="plotly_white")
        else:
            variog_fig = _empty_fig("No hay suficientes datos para variograma")

        df_tab_vario = pd.DataFrame(tabla_variogramas)
        if not df_tab_vario.empty:
            tabla_vario = dbc.Table.from_dataframe(
                df_tab_vario, striped=True, bordered=False, hover=True, size="sm",
                class_name="mb-0 text-center"
            )
        else:
            tabla_vario = html.Div("Sin parámetros estimados.", className="text-muted")

        # --------- Descargas ----------
        rep_href = _to_csv_href(df[['Fecha', 'Torre', 'Turno', 'Representatividad']])
        elem_cols = ['Fecha', 'Torre', 'Turno']
        if elemento in df.columns:
            elem_cols.append(elemento)
        elem_href = _to_csv_href(df[elem_cols])

        return (opts, rep_fig, dist_fig, linea_fig, cusum_fig, corr_fig,
                sesgo_fig, sesgo_dist_fig, res_sesgo, kpi, rep_href, elem_href,
                variog_fig, tabla_vario)

    # --- KPI helper (representatividad) ---
    def _kpi_rep(df):
        media = df['Representatividad'].mean()
        std = df['Representatividad'].std()
        bajo_76 = (df['Representatividad'] < 0.76).mean() * 100
        return dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Media", className="small text-muted"),
                html.H4(f"{media:.2f}", className="mb-0")
            ]), className="shadow-sm border-0"), md=4, lg=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Desv. Estándar", className="small text-muted"),
                html.H4(f"{std:.2f}", className="mb-0")
            ]), className="shadow-sm border-0"), md=4, lg=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("< 76%", className="small text-muted"),
                html.H4(f"{bajo_76:.1f}%", className="mb-0")
            ]), className="shadow-sm border-0"), md=4, lg=3),
        ], className="g-3")

def _empty_all():
    """Convenience pack of empty/placeholder returns in the same order (except first ‘options’)."""
    return (
        _empty_fig(),  # graf-represent
        _empty_fig(),  # graf-dist
        _empty_fig(),  # graf-linea
        _empty_fig(),  # graf-cusum
        _empty_fig(),  # graf-correlacion
        _empty_fig(),  # graf-sesgo
        _empty_fig(),  # graf-sesgo-dist
        "—",           # resultado sesgo
        html.Div("Seleccione filtros para ver KPIs", className="text-muted"),
        "",            # href rep
        "",            # href elem
        _empty_fig(),  # variograma
        html.Div()     # tabla variogramas
    )
