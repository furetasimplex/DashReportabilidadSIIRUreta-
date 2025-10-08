# tabs/tab2.py
import pandas as pd
from dash import html, dcc, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objs as go
from db_connection import get_connection

# ---------------------------
# Layout
# ---------------------------
def render_tab2():
    # Rango de fechas desde BD
    conn = get_connection()
    fechas_df = pd.read_sql(
        "SELECT MIN(Fecha) as min_fecha, MAX(Fecha) as max_fecha FROM inventar_SpcHidr.Datos_conciliados_of",
        conn
    )
    conn.close()

    min_fecha = fechas_df['min_fecha'][0]
    max_fecha = fechas_df['max_fecha'][0]

    return html.Div([
        # Título
        dbc.Alert(
            [html.I(className="bi bi-collection me-2"), "Análisis de Datos Conciliados"],
            color="primary", className="mb-3"
        ),

        # Filtros principales (rango + actualizar)
        dbc.Card([
            dbc.CardHeader(html.H5("Rango de fechas", className="mb-0")),
            dbc.CardBody(
                dbc.Row([
                    dbc.Col(
                        html.Div([
            html.Label("Seleccionar fecha: ", style={'marginLeft': '10px', 'marginRight': '10px'}),
            dcc.DatePickerRange(
                id='fecha-rango-tab2',
                min_date_allowed=min_fecha,
                max_date_allowed=max_fecha,
                start_date=min_fecha,
                end_date=max_fecha,
                display_format='YYYY-MM-DD'
            ),
        ], style={'display': 'flex', 'alignItems': 'center'}),
                        
                        md=6, lg=4
                    ),
                    dbc.Col(
                        dbc.Button(
                            [html.I(className="bi bi-arrow-repeat me-2"), "Actualizar"],
                            id="actualizar-tab2", n_clicks=0, color="primary",
                            className="mt-2 mt-md-0"
                        ),
                        md=3, lg=2
                    ),
                ], className="g-3")
            ),
        ], className="mb-4 shadow-sm border-0"),

        # Controles secundarios
        dbc.Card([
            dbc.CardHeader(html.H5("Controles de análisis", className="mb-0")),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Variables a comparar (distribución)", className="fw-semibold"),
                        dcc.Dropdown(id="var-tab2", multi=True),
                    ], md=6, lg=6),
                    dbc.Col([
                        html.Label("Variable secundaria (dispersión)", className="fw-semibold"),
                        dcc.Dropdown(id="var2-tab2", multi=False),
                    ], md=6, lg=6),
                ], className="g-3"),

                html.Hr(),

                html.Label("Agregación temporal", className="fw-semibold"),
                dbc.RadioItems(
                    id="agg-tab2",
                    options=[
                        {"label": "Semanal", "value": "semana"},
                        {"label": "Mensual", "value": "mes"}
                    ],
                    value="semana",
                    inline=True,
                ),
            ]),
        ], className="mb-4 shadow-sm border-0"),

        # KPIs
        dbc.Card([
            dbc.CardHeader(html.H6("KPIs", className="mb-0")),
            dbc.CardBody(html.Div(id="kpis-tab2"))
        ], className="mb-4 shadow-sm border-0"),

        # Gráficos fila 1
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H6("Tendencia temporal", className="mb-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="graf-linea-tab2"), type="default"))
                ], className="shadow-sm border-0"),
                md=12, lg=6, className="mb-3"
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H6("Relación cruzada", className="mb-0")),
                    dbc.CardBody(dcc.Loading(dcc.Graph(id="graf-disp-tab2"), type="default"))
                ], className="shadow-sm border-0"),
                md=12, lg=6, className="mb-3"
            ),
        ], className="g-3"),

        # Gráficos fila 2
        dbc.Row([
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H6("Correlación entre variables", className="mb-0")),
                    dbc.CardBody([ # <-- El CardBody envuelve a ambos
                        dcc.Loading(dcc.Graph(id="graf-heatmap-tab2"), type="default"),
                        
                        # El botón va DENTRO del CardBody, después del gráfico
                        dbc.Button(
                            [html.I(className="bi bi-arrows-fullscreen me-2"), "Ver a pantalla completa"],
                            id="btn-full-heatmap-tab2",
                            color="secondary",
                            outline=True,
                            className="mt-2"
                        ),
                    ])
                ], className="shadow-sm border-0"),
                md=12, lg=6, className="mb-3"
            ),
            dbc.Col(
                dbc.Card([
                    dbc.CardHeader(html.H6("Distribución comparada", className="mb-0")),
                    dbc.CardBody(
                        dcc.Loading(dcc.Graph(id="graf-hist-tab2"), type="default")
                    )
                ], className="shadow-sm border-0"),
                md=12, lg=6, className="mb-3"
            ),
        ], className="g-3"),
            

        # Tabla
        dbc.Card([
            dbc.CardHeader(html.H6("Estadísticas descriptivas", className="mb-0")),
            dbc.CardBody(html.Div(id="tabla-descriptiva-tab2"))
        ], className="mb-4 shadow-sm border-0"),
        dbc.Modal(
            id="modal-heatmap-tab2",
            is_open=False,
            fullscreen=True,
            scrollable=True,
            children=[
                dbc.ModalHeader(dbc.ModalTitle("Gráfico: Correlación entre variables")),
                dbc.ModalBody(
                    dcc.Loading(
                        # Un dcc.Graph para mostrar la figura en el modal
                        dcc.Graph(id="graf-heatmap-modal-tab2", style={"height": "85vh"})
                    )
                ),
                dbc.ModalFooter(
                    dbc.Button("Cerrar", id="close-modal-heatmap-tab2", className="ms-auto")
                ),
            ]
        )
    ])


# ---------------------------
# Callbacks
# ---------------------------
def register_tab2_callbacks(app):
    @app.callback(
        [
            Output("graf-linea-tab2", "figure"),
            Output("graf-disp-tab2", "figure"),
            Output("graf-heatmap-tab2", "figure"),
            Output("graf-hist-tab2", "figure"),
            Output("tabla-descriptiva-tab2", "children"),
            Output("kpis-tab2", "children")
        ],
        [
            Input("actualizar-tab2", "n_clicks"),
            Input("agg-tab2", "value"),
            Input("fecha-rango-tab2", "start_date"),
            Input("fecha-rango-tab2", "end_date"),
            Input("var-tab2", "value"),
            Input("var2-tab2", "value")
        ]
    )
    def actualizar_tab2(n_clicks, agg, fecha_inicio, fecha_fin, var_list, var2):
        # Leer datos
        conn = get_connection()
        query = f"""
            SELECT * FROM inventar_SpcHidr.Datos_conciliados_of
            WHERE Fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        """
        df = pd.read_sql(query, conn)
        conn.close()

        # Preparación
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        df['Semana'] = df['Fecha'].dt.isocalendar().week
        df['Año'] = df['Fecha'].dt.year
        df['Mes'] = df['Fecha'].dt.month

        # Si no hay variables seleccionadas, devolver placeholders
        if not var_list:
            empty = go.Figure()
            empty.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
            return empty, empty, empty, empty, html.Div(), html.Div()

        group_col = "Semana" if agg == "semana" else "Mes"

        # Tendencia temporal
        fig_linea = go.Figure()
        for var in var_list:
            if var not in df.columns:
                continue
            df_group = df.groupby(["Año", group_col])[var].mean().reset_index()
            df_group["Periodo"] = df_group["Año"].astype(str) + "-" + df_group[group_col].astype(str)
            fig_linea.add_trace(go.Scatter(
                x=df_group["Periodo"], y=df_group[var], mode='lines+markers', name=var
            ))
        fig_linea.update_layout(template="plotly_white", xaxis_tickangle=-45,
                               margin=dict(l=10, r=10, t=10, b=10))

        # Dispersión con tendencia
        if var2 and var2 in df.columns and var_list[0] in df.columns:
            fig_disp = px.scatter(df, x=var_list[0], y=var2, trendline="ols",
                                  template="plotly_white")
            fig_disp.update_layout(margin=dict(l=10, r=10, t=10, b=10))
        else:
            fig_disp = go.Figure().update_layout(template="plotly_white",
                                                 margin=dict(l=10, r=10, t=10, b=10))

        # Heatmap de correlación
        corr = df.select_dtypes(include='number').corr()
        fig_heat = px.imshow(corr, text_auto=True, aspect="auto",
                             template="plotly_white")
        fig_heat.update_layout(margin=dict(l=10, r=10, t=10, b=10))

        # Histograma comparado
        fig_hist = go.Figure()
        for var in var_list:
            if var in df.columns:
                fig_hist.add_trace(go.Histogram(x=df[var], name=var, opacity=0.55))
        fig_hist.update_layout(barmode='overlay', template="plotly_white",
                               margin=dict(l=10, r=10, t=10, b=10))

        # Tabla descriptiva
        desc_df = df[var_list].describe().round(2).transpose().reset_index()
        desc_df.rename(columns={'index': 'Variable'}, inplace=True)
        tabla = dbc.Table.from_dataframe(
            desc_df, striped=True, bordered=False, hover=True, size="sm",
            class_name="mb-0 text-center"
        )

        # KPIs (para la primera variable seleccionada)
        kpi_var = var_list[0]
        media = df[kpi_var].mean()
        maximo = df[kpi_var].max()
        minimo = df[kpi_var].min()

        kpis = dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Promedio", className="small text-muted"),
                html.H4(f"{media:,.2f}", className="mb-0"),
                html.Div(kpi_var, className="small")
            ]), className="shadow-sm border-0"), md=4, lg=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Máximo", className="small text-muted"),
                html.H4(f"{maximo:,.2f}", className="mb-0"),
                html.Div(kpi_var, className="small")
            ]), className="shadow-sm border-0"), md=4, lg=3),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.Div("Mínimo", className="small text-muted"),
                html.H4(f"{minimo:,.2f}", className="mb-0"),
                html.Div(kpi_var, className="small")
            ]), className="shadow-sm border-0"), md=4, lg=3),
        ], className="g-3")

        return fig_linea, fig_disp, fig_heat, fig_hist, tabla, kpis

    @app.callback(
        [
            Output("var-tab2", "options"),
            Output("var2-tab2", "options"),
            Output("var-tab2", "value")
        ],
        [Input("actualizar-tab2", "n_clicks")],
        [
            State("fecha-rango-tab2", "start_date"),
            State("fecha-rango-tab2", "end_date")
        ]
    )

    def actualizar_dropdowns(n_clicks, fecha_inicio, fecha_fin):
        conn = get_connection()
        query = f"""
            SELECT * FROM inventar_SpcHidr.Datos_conciliados_of
            WHERE Fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        """
        df = pd.read_sql(query, conn)
        conn.close()

        variables = df.select_dtypes(include='number').columns.tolist()
        options = [{"label": v, "value": v} for v in variables]
        default_vars = [variables[0]] if variables else []

        return options, options, default_vars
    
    @app.callback(
        Output("modal-heatmap-tab2", "is_open"),
        Output("graf-heatmap-modal-tab2", "figure"),
        Input("btn-full-heatmap-tab2", "n_clicks"),
        Input("close-modal-heatmap-tab2", "n_clicks"),
        State("modal-heatmap-tab2", "is_open"),
        State("graf-heatmap-tab2", "figure"), # Estado para obtener la figura actual
        prevent_initial_call=True
    )
    def toggle_heatmap_modal(n_open, n_close, is_open, figure):
        triggered_id = ctx.triggered_id

        if triggered_id == "btn-full-heatmap-tab2":
            # Si se hace clic en abrir, abre el modal y pasa la figura del gráfico
            return True, figure
        
        if triggered_id == "close-modal-heatmap-tab2":
            # Si se hace clic en cerrar, cierra el modal sin actualizar la figura
            return False, no_update

        # Comportamiento por defecto
        return is_open, no_update
    
