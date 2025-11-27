# tabs/tab1.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from db_connection import get_connection
from datetime import datetime

VARIABLES_VALIDAS = [
    "Tonelaje", "CuT", "CuS", "Razón solubilidad", "Carbonato",
    "Rec Lix", "Malla 100", "Clay Beta", "CUFE", "Fe"
]

# ---------- DATA ----------
def load_data(fecha_ini, fecha_fin):
    query = f"""
        SELECT
            Fecha, 
            Turno, 
            Origen, 
            Fase, 
            Ton as Tonelaje, 
            PONDCuTG00 as CuT,
            PONDCusG01 as CuS, 
            PONDRS as [Razón solubilidad], 
            PONDC03G02 as Carbonato,
            PONDRecLixG03 as [Rec Lix], 
            POND100G07 as [Malla 100], 
            PONDClayBG10 as [Clay Beta],
            PONDCUFE as CUFE, 
            PONDFE as Fe
        FROM inventar_SpcHidr.resumen_mina
        WHERE Fecha BETWEEN '{fecha_ini}' AND '{fecha_fin}'
    """
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    df = pd.read_sql(query, conn)
    conn.close()

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Origen"] = df["Origen"].apply(lambda x: "Mina" if "mina" in str(x).lower() else "Stock")
    df["Semana"] = df["Fecha"].dt.isocalendar().week
    df["Año"] = df["Fecha"].dt.year
    df["Mes"] = df["Fecha"].dt.to_period("M").astype(str)
    return df

# ---------- LAYOUT ----------
def render_tab1():
    return html.Div([
        # Título
        dbc.Alert([
            html.I(className="bi bi-speedometer2 me-2"),
            "Resumen Estadístico Mina"
        ], color="primary", className="mb-3"),

        # Filtros de rango (Card)
        dbc.Card([
            dbc.CardHeader(html.H5("Rango de fechas", className="mb-0")),
            dbc.CardBody(
                dbc.Row([
                    
                     dbc.Col([
                        html.Label("Fecha Fin", className="form-label fw-semibold"),
                        dcc.DatePickerSingle(
                            id="fecha-inicio",
                            date="2024-01-01",
                            display_format="YYYY-MM-DD",
                            className="w-100"   # ocupa el ancho de la columna
                        ),
                    ], md=2),
                    dbc.Col([
                        html.Label("Fecha Inicio", className="form-label fw-semibold"),
                        dcc.DatePickerSingle(
                            id="fecha-fin",
                            date="2025-12-31",
                            display_format="YYYY-MM-DD",
                            className="w-100"   # ocupa el ancho de la columna
                        ),
                    ], md=2),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-arrow-repeat me-2"), "Actualizar"],
                            id="boton-filtrar", n_clicks=1, color="primary", className="mt-2 mt-md-0"
                        ),
                        md=2
                    ),
                ], className="g-3")
            )
        ], className="mb-4 shadow-sm border-0"),

        # Contenedor dinámico tras cargar datos
        html.Div(id="filtros-tab1")
    ])

# ---------- CALLBACKS ----------
def register_tab1_callbacks(app):
    @app.callback(
        Output("filtros-tab1", "children"),
        Input("boton-filtrar", "n_clicks"),
        State("fecha-inicio", "date"),
        State("fecha-fin", "date"),
        prevent_initial_call=False
    )
    def actualizar_con_fechas(n_clicks, fecha_ini, fecha_fin):
        if not fecha_ini or not fecha_fin:
            return dbc.Alert("⚠️ Seleccione ambas fechas.", color="warning", className="mb-3")

        df = load_data(fecha_ini, fecha_fin)

        if df.empty:
            return dbc.Alert("⚠️ No se encontraron datos para el rango seleccionado.", color="warning", className="mb-3")

        origenes = ["Todos"] + sorted(df["Origen"].unique())
        fases = ["Todas"] + sorted(df["Fase"].dropna().unique())

        # Panel de controles + gráficos en layout de 2 columnas
        return html.Div([
            dbc.Row([
                # Columna izquierda: controles
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H6("Controles", className="mb-0")),
                        dbc.CardBody([
                            html.Label("Origen", className="fw-semibold"),
                            dcc.Dropdown(
                                id="filtro-origen",
                                options=[{"label": x, "value": x} for x in origenes],
                                value="Todos"
                            ),
                            html.Div(className="mb-3"),

                            html.Label("Fase", className="fw-semibold"),
                            dcc.Dropdown(
                                id="filtro-fase",
                                options=[{"label": x, "value": x} for x in fases],
                                value="Todas"
                            ),
                            html.Div(className="mb-3"),

                            html.Label("Variable(s) a analizar", className="fw-semibold"),
                            dcc.Dropdown(
                                id="filtro-variable",
                                options=[{"label": v, "value": v} for v in VARIABLES_VALIDAS],
                                value=["Tonelaje"], multi=True
                            ),
                            html.Div(className="mb-3"),

                            html.Label("Agregación temporal", className="fw-semibold"),
                            dbc.RadioItems(
                                id="agregacion-tiempo",
                                options=[
                                    {"label": "Diaria", "value": "dia"},
                                    {"label": "Semanal", "value": "semana"},
                                    {"label": "Mensual", "value": "mes"}
                                ],
                                value="semana",
                                inline=True
                            ),

                            html.Hr(),

                            html.Label("Variable secundaria (scatter)", className="fw-semibold"),
                            dcc.Dropdown(
                                id="variable-secundaria",
                                options=[{"label": v, "value": v} for v in VARIABLES_VALIDAS],
                                value="CuT"
                            ),

                            # Store con los datos base ya filtrados por fecha
                            dcc.Store(id="datos-filtrados", data=df.to_dict("records"))
                        ])
                    ], className="shadow-sm border-0"),
                ], md=4, lg=3),

                # Columna derecha: visualizaciones
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Tendencias temporales", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="grafico-linea"), type="default")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Distribución", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="grafico-histograma"), type="default")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Scatter con tendencia", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="scatter-plot"), type="default")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Matriz de Correlación", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="heatmap-correlacion"), type="default")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Boxplot por Turno", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(dcc.Graph(id="boxplot-turno"), type="default")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("KPIs dinámicos", className="mb-0")),
                                dbc.CardBody(
                                    html.Div(id="kpi-dinamico", className="d-flex flex-wrap gap-3")
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardHeader(html.H6("Estadísticas descriptivas", className="mb-0")),
                                dbc.CardBody(
                                    dcc.Loading(
                                        html.Div(id="tabla-estadisticas"),
                                        type="default"
                                    )
                                )
                            ], className="mb-3 shadow-sm border-0")
                        ], md=12),
                    ]),
                ], md=8, lg=9),
            ], className="g-3"),
        ])

    @app.callback(
        Output("grafico-linea", "figure"),
        Output("grafico-histograma", "figure"),
        Output("tabla-estadisticas", "children"),
        Output("heatmap-correlacion", "figure"),
        Output("scatter-plot", "figure"),
        Output("boxplot-turno", "figure"),
        Output("kpi-dinamico", "children"),
        Input("filtro-origen", "value"),
        Input("filtro-fase", "value"),
        Input("filtro-variable", "value"),
        Input("variable-secundaria", "value"),
        Input("agregacion-tiempo", "value"),
        State("datos-filtrados", "data")
    )
    def actualizar_graficos(origen, fase, variables, var2, frecuencia, data_dict):
        df = pd.DataFrame(data_dict)

        # Filtros
        if origen and origen != "Todos":
            df = df[df["Origen"] == origen]
        if fase and fase != "Todas":
            df = df[df["Fase"] == fase]

        # Agregación temporal
        if frecuencia == "dia":
            df["Fecha"] = pd.to_datetime(df["Fecha"])  # asegúrate de que sea datetime real
            df_group = (
                df.groupby(df["Fecha"].dt.date)[variables]
                .mean()
                .reset_index()
                .rename(columns={"Fecha": "Fecha"})
            )
            df_group["Fecha"] = pd.to_datetime(df_group["Fecha"])
        elif frecuencia == "semana":
            df_group = df.groupby(["Año", "Semana"])[variables].mean().reset_index()
            df_group["Fecha"] = pd.to_datetime(
                df_group["Año"].astype(str) + "-W" + df_group["Semana"].astype(str) + "-1",
                format="%G-W%V-%u"
            )
        else:
            df_group = df.groupby("Mes")[variables].mean().reset_index()
            df_group["Fecha"] = pd.to_datetime(df_group["Mes"] + "-01")

        # Línea
        fig_line = go.Figure()
        for var in variables:
            fig_line.add_trace(go.Scatter(
                x=df_group["Fecha"], y=df_group[var],
                mode="lines+markers", name=var
            ))
        fig_line.update_layout(
            title=None, template="plotly_white",
            xaxis_title="Fecha", yaxis_title="Valor",
            hovermode="x unified", margin=dict(l=10, r=10, t=10, b=10)
        )

        # Histograma
        fig_hist = px.histogram(
            df, x=variables[0], nbins=30, template="plotly_white"
        ).update_layout(margin=dict(l=10, r=10, t=10, b=10))

        # Tabla descriptores
        desc = df[VARIABLES_VALIDAS].describe().round(2).reset_index().rename(columns={"index": "Estadística"})
        table = dash_table.DataTable(
            columns=[{"name": col, "id": col} for col in desc.columns],
            data=desc.to_dict("records"),
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "center", "padding": "6px"},
            style_header={"backgroundColor": "#f8f9fa", "fontWeight": "bold"},
            page_size=10
        )

        # Correlación
        corr = df[VARIABLES_VALIDAS].corr().round(2)
        fig_corr = px.imshow(
            corr, text_auto=True, color_continuous_scale="RdBu_r",
            template="plotly_white"
        ).update_layout(margin=dict(l=10, r=10, t=10, b=10))

        # Scatter + tendencia
        fig_scatter = px.scatter(
            df, x=variables[0], y=var2, trendline="ols", template="plotly_white"
        ).update_layout(margin=dict(l=10, r=10, t=10, b=10))

        # Boxplot por turno
        fig_box = px.box(
            df, x="Turno", y=variables[0], template="plotly_white"
        ).update_layout(margin=dict(l=10, r=10, t=10, b=10))

        # KPIs (cards bootstrap)
        kpi_cards = []
        for var in variables:
            media = df[var].mean()
            mediana = df[var].median()
            ultima = df[var].iloc[-1] if len(df[var]) else 0
            variacion = ((ultima - media) / media) * 100 if media else 0
            kpi_cards.append(
                dbc.Card(
                    dbc.CardBody([
                        html.Div(var, className="fw-semibold small text-muted"),
                        html.H4(f"{media:.2f}", className="mb-0"),
                        html.Div(f"Mediana: {mediana:.2f}", className="small text-muted"),
                        html.Div(f"Última vs media: {variacion:.1f}%", className="small"),
                    ]), className="shadow-sm border-0", style={"minWidth": "170px"}
                )
            )

        return fig_line, fig_hist, table, fig_corr, fig_scatter, fig_box, kpi_cards
