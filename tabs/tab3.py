# tabs/tab3.py
import pandas as pd
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
import plotly.figure_factory as ff
from db_connection import get_connection
from urllib.parse import quote

# ---------------------------------
# Helpers
# ---------------------------------
def load_data(fecha_ini, fecha_fin, pad):
    query = f"""
        SELECT
            modulos_turnos.Campana, 
            modulos_turnos.Parcela, 
            modulos_turnos.Modulo, 
            modulos_turnos.Fecha, 
            modulos_turnos.PAD, 
            modulos_turnos.Turno, 
            modulos_turnos.Humedad, 
            modulos_turnos.TMH, 
            modulos_turnos.TMS, 
            modulos_turnos.Sal, 
            modulos_turnos.CuT_TM, 
            modulos_turnos.CuS_TM, 
            modulos_turnos.Cu_Insoluble, 
            modulos_turnos.Tasa_Oxidacion, 
            modulos_turnos.FeT, 
            modulos_turnos.FeS, 
            modulos_turnos.CO3, 
            modulos_turnos.Consumo_H, 
            modulos_turnos.[Adición_H], 
            modulos_turnos.[Altura Módulo], 
            modulos_turnos.Caolinita, 
            modulos_turnos.Cuarzo, 
            modulos_turnos.M34, 
            modulos_turnos.M10, 
            modulos_turnos.M100, 
            modulos_turnos.Mina, 
            modulos_turnos.stock, 
            modulos_turnos.CSR_Cps, 
            modulos_turnos.CSR_Cc, 
            modulos_turnos.CSR_Cu, 
            modulos_turnos.Betaclay, 
            modulos_turnos.CuFe
        FROM inventar_SpcHidr.modulos_turnos
        WHERE Fecha BETWEEN '{fecha_ini}' AND '{fecha_fin}' AND PAD='{pad}'
    """
    conn = get_connection()
    if conn is None:
        return pd.DataFrame()

    df = pd.read_sql(query, conn)
    conn.close()

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce")
    df["Semana"] = df["Fecha"].dt.isocalendar().week
    df["Año"] = df["Fecha"].dt.year
    df["Mes"] = df["Fecha"].dt.to_period("M").astype(str)
    return df


def _empty_fig(title="Sin datos"):
    fig = go.Figure()
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=10, r=10, t=40, b=10),
        title=title
    )
    return fig


# ---------------------------------
# Layout
# ---------------------------------
def render_tab3():
    return html.Div([
        # Título
        dbc.Alert(
            [html.I(className="bi bi-layers-half me-2"), "Resumen Estadístico Pilas"],
            color="primary", className="mb-3"
        ),

        # Filtros superiores
        dbc.Card([
            dbc.CardHeader(html.H5("Parámetros de consulta", className="mb-0")),
            dbc.CardBody(
                dbc.Row([
                     dbc.Col([
                        html.Label("Fecha Inicio", className="form-label fw-semibold"),
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
                    dbc.Col([
                        html.Label("Selección PAD", className="fw-semibold"),
                        dbc.RadioItems(
                            id="sel-PAD",
                            options=[
                                {"label": "Sulfuro", "value": "SULFUROS"},
                                {"label": "Óxidos", "value": "OXIDOS"}
                            ],
                            value="SULFUROS",
                            inline=True,
                        ),
                    ], md=4),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-arrow-repeat me-2"), "Actualizar"],
                            id="boton-filtrar", n_clicks=1, color="primary", className="mt-2 mt-md-0"
                        ),
                        md=2
                    )
                ], className="g-3")
            )
        ], className="mb-4 shadow-sm border-0"),

        # Controles secundarios
        dbc.Card([
            dbc.CardHeader(html.H5("Controles de visualización", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Variable del mapa de calor", className="fw-semibold"),
                        dcc.Dropdown(id="var_heat_tab3"),
                    ], md=6, lg=3),
                    dbc.Col([
                        html.Label("Campaña", className="fw-semibold"),
                        dcc.Dropdown(id="campania_tab3"),
                    ], md=6, lg=3),
                    dbc.Col([
                        html.Label("Parcela", className="fw-semibold"),
                        dcc.Dropdown(id="parcela_tab3"),
                    ], md=6, lg=3),
                    dbc.Col([
                        html.Label("Módulo", className="fw-semibold"),
                        dcc.Dropdown(id="modulo_tab3"),
                    ], md=6, lg=3),
                ], className="g-3")
            ])
        ], className="mb-4 shadow-sm border-0"),

        # Tabs de visualización
        dcc.Tabs([
            dcc.Tab(label='Visualización', children=[
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader(html.H6("Mapa de Calor", className="mb-0")),
                            dbc.CardBody(dcc.Loading(dcc.Graph(id="heatmap_tab3"), type="default"))
                        ], className="shadow-sm border-0"),
                        md=12, className="mb-3"
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader(html.H6("Variables Clave (Temporal)", className="mb-0")),
                            dbc.CardBody(dcc.Loading(dcc.Graph(id="dual_axis_tab3"), type="default"))
                        ], className="shadow-sm border-0"),
                        md=12, className="mb-3"
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader(html.H6("Estadística Descriptiva", className="mb-0")),
                            dbc.CardBody(dcc.Loading(html.Div(id="stats_tab3"), type="default"))
                        ], className="shadow-sm border-0"),
                        md=12, className="mb-3"
                    ),
                ]),
                dbc.Row([
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-download me-2"), "Descargar CSV"],
                            id="btn-dl-tab3", color="secondary", outline=True, className="me-2"
                        ),
                        md="auto"
                    ),
                    dbc.Col(
                        html.A("Abrir CSV", id="download_tab3", download="filtrado_tab3.csv",
                               href="", target="_blank", className="align-self-center"),
                        md="auto"
                    ),
                ], className="g-2 mb-3"),
            ]),
            dcc.Tab(label='Correlaciones', children=[
                dbc.Card([
                    dbc.CardHeader(html.H6("Matriz de Correlación", className="mb-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="correlacion_tab3"), type="default"))
                ], className="shadow-sm border-0 mt-3"),
            ])
        ])
    ])


# ---------------------------------
# Callbacks
# ---------------------------------
def register_tab3_callbacks(app):
    # Cargar opciones y también establecer VALORES por defecto
    @app.callback(
        [
            Output("var_heat_tab3", "options"),
            Output("campania_tab3", "options"),
            Output("parcela_tab3", "options"),
            Output("modulo_tab3", "options"),
            Output("var_heat_tab3", "value"),
            Output("campania_tab3", "value"),
            Output("parcela_tab3", "value"),
            Output("modulo_tab3", "value"),
        ],
        [Input("boton-filtrar", "n_clicks")],
        [State("fecha-inicio", "date"),
         State("fecha-fin", "date"),
         State("sel-PAD", "value")]
    )
    def actualizar_filtros(n_clicks, f_ini, f_fin, pad):
        df = load_data(f_ini, f_fin, pad)

        if df.empty:
            return [], [], [], [], None, None, None, None

        # Variables para heatmap: prioriza numéricas
        numeric_cols = df.select_dtypes(include='number').columns.tolist()
        # si tienes preferidas:
        prefer = ['TMH', 'TMS', 'M34', 'M10', 'M100', 'CuT_TM', 'CuS_TM']
        default_var = next((v for v in prefer if v in numeric_cols), (numeric_cols[0] if numeric_cols else None))
        var_options = [{"label": v, "value": v} for v in numeric_cols]

        camp_opts = [{"label": str(c), "value": c} for c in sorted(df['Campana'].dropna().unique())]
        camp_val = camp_opts[0]['value'] if camp_opts else None

        parc_opts = [{"label": "Todas", "value": "Todas"}] + \
                    [{"label": str(p), "value": p} for p in sorted(df['Parcela'].dropna().unique())]
        parc_val = "Todas"

        mod_opts = [{"label": "Todos", "value": "Todos"}] + \
                   [{"label": str(m), "value": m} for m in sorted(df['Modulo'].dropna().unique())]
        mod_val = "Todos"

        return var_options, camp_opts, parc_opts, mod_opts, default_var, camp_val, parc_val, mod_val

    @app.callback(
        [
            Output("heatmap_tab3", "figure"),
            Output("dual_axis_tab3", "figure"),
            Output("stats_tab3", "children"),
            Output("download_tab3", "href"),
            Output("correlacion_tab3", "figure")
        ],
        [
            Input("var_heat_tab3", "value"),
            Input("campania_tab3", "value"),
            Input("parcela_tab3", "value"),
            Input("modulo_tab3", "value"),
            Input("fecha-inicio", "date"),
            Input("fecha-fin", "date"),
            Input("sel-PAD", "value")
        ]
    )
    def actualizar_visualizaciones(variable, campania, parcela, modulo, f_ini, f_fin, pad):
        df = load_data(f_ini, f_fin, pad)
        if df.empty:
            return _empty_fig(), _empty_fig(), html.Div("Sin datos"), "", _empty_fig()

        # Si aún no hay valor seleccionado (entrada inicial), devuelve placeholders
        if variable is None or campania is None:
            return _empty_fig("Seleccione filtros"), _empty_fig("Seleccione filtros"), html.Div("Seleccione filtros"), "", _empty_fig("Seleccione filtros")

        # Filtrado
        df = df[df['Campana'] == campania]
        if parcela and parcela != "Todas":
            df = df[df['Parcela'] == parcela]
        if modulo and modulo != "Todos":
            df = df[df['Modulo'] == modulo]

        if df.empty:
            return _empty_fig("Sin datos tras filtros"), _empty_fig("Sin datos tras filtros"), html.Div("Sin datos tras filtros"), "", _empty_fig("Sin datos tras filtros")

        # --- Heatmap
        if variable not in df.columns or not pd.api.types.is_numeric_dtype(df[variable]):
            fig_heat = _empty_fig(f"{variable} no disponible o no numérica")
        else:
            heat_data = df.pivot_table(index='Modulo', columns='Fecha', values=variable, aggfunc='mean')
            if heat_data.empty:
                fig_heat = _empty_fig("Sin datos para mapa de calor")
            else:
                fig_heat = px.imshow(
                    heat_data, aspect='auto', color_continuous_scale='Viridis',
                    labels={'color': variable}, title=f"Mapa de Calor de {variable}"
                )
                fig_heat.update_layout(margin=dict(l=10, r=10, t=40, b=10))

        # --- Serie temporal (dual/varias líneas)
        fig_dual = go.Figure()
        for var in ['CuT_TM', 'CuS_TM', 'Cu_Insoluble']:
            if var in df.columns and pd.api.types.is_numeric_dtype(df[var]):
                fig_dual.add_trace(go.Scatter(x=df['Fecha'], y=df[var], mode='lines', name=var))
        if not fig_dual.data:
            fig_dual = _empty_fig("Sin variables clave disponibles")
        else:
            fig_dual.update_layout(title="Comportamiento Temporal de Variables Clave",
                                   xaxis_title="Fecha", template="plotly_white",
                                   margin=dict(l=10, r=10, t=40, b=10))

        # --- Estadísticas
        if variable in df.columns and pd.api.types.is_numeric_dtype(df[variable]):
            stats = df[variable].describe().round(2).to_frame().reset_index()
            mean = float(stats.loc[stats['index'] == 'mean', variable].values[0]) if 'mean' in stats['index'].values else 0
            std = float(stats.loc[stats['index'] == 'std', variable].values[0]) if 'std' in stats['index'].values else 0
            cv = round((std / mean) * 100, 2) if mean else 0
            stats.loc[len(stats.index)] = ['Coef. de Variación (%)', cv]
            stats.columns = ['Estadístico', variable]
            stats_table = dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in stats.columns],
                data=stats.to_dict("records"),
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'center', 'padding': '6px'},
                style_header={'backgroundColor': '#f8f9fa', 'fontWeight': 'bold'}
            )
        else:
            stats_table = html.Div("Seleccione una variable numérica.", className="text-muted")

        # --- CSV (data URL seguro)
        csv_string = df.to_csv(index=False)
        csv_href = "data:text/csv;charset=utf-8," + quote(csv_string)

        # --- Correlación
        vars_corr = [v for v in ['CuT_TM', 'CuS_TM', 'Cu_Insoluble', 'TMH', 'TMS'] if v in df.columns]
        if len(vars_corr) >= 2:
            corr_df = df[vars_corr].corr().round(2)
            fig_corr = ff.create_annotated_heatmap(
                z=corr_df.values, x=list(corr_df.columns), y=list(corr_df.index),
                colorscale='RdBu', zmin=-1, zmax=1, showscale=True
            )
            fig_corr.update_layout(title="Matriz de Correlación", margin=dict(l=10, r=10, t=40, b=10))
        else:
            fig_corr = _empty_fig("No hay suficientes variables para correlación")

        return fig_heat, fig_dual, stats_table, csv_href, fig_corr
