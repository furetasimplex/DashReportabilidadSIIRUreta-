from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

from db_connection import get_connection


# ============================================================
# LAYOUT DEL TAB
# ============================================================
def render_tab_analisis_reconciliacion():
    """
    Layout del TAB:
    4 Estadística Reconciliación
    """

    return dbc.Container(
        fluid=True,
        children=[

            html.H4(
                "📊 Estadística de Reconciliación",
                className="text-primary fw-bold mb-3"
            ),

            dbc.Card(
                dbc.CardBody(
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Balance (bm_id)"),
                            dcc.Dropdown(
                                id="stat-sel-balance",
                                placeholder="Seleccione balance"
                            )
                        ], md=4),

                        dbc.Col([
                            dbc.Label("Tipo de variable"),
                            dcc.Dropdown(
                                id="stat-sel-tipo-variable",
                                options=[
                                    {"label": "Masa", "value": "masa"},
                                    {"label": "Ley Cu", "value": "ley"}
                                ],
                                value="masa",
                                clearable=False
                            )
                        ], md=4),
                    ])
                ),
                className="mb-4 shadow-sm"
            ),

            dbc.Tabs([

                dbc.Tab(
                    label="Distribución de Errores",
                    children=[
                        dcc.Graph(id="stat-g-box-ajuste")
                    ]
                ),

                dbc.Tab(
                    label="Tendencia Temporal",
                    children=[
                        dcc.Graph(id="stat-g-tendencia-ajuste")
                    ]
                ),

                dbc.Tab(
                    label="Error vs Tolerancia",
                    children=[
                        dcc.Graph(id="stat-g-barras-tolerancia")
                    ]
                ),

            ])
        ]
    )


# ============================================================
# CALLBACKS DEL TAB
# ============================================================
def register_analisis_reconciliacion_callbacks(app):

    BASE_QUERY = """
    SELECT
        bm_id            AS id_balance,
        caso_id,
        fecha_bm         AS fecha_balance,
        Flujo            AS flujo,

        Masa_medida,
        Masa_recon,
        Error_masa       AS error_masa_pct,
        Tolerancia       AS tol_masa_pct,

        Ley_medida_Cu,
        Ley_recon_Cu,
        Error_ley_Cu     AS error_ley_cu_pct,
        Tolerancia_cu    AS tol_ley_cu_pct
    FROM inventar_SpcHidr.Data_balance_rec
    """

    def run_query(query, params=None):
        conn = get_connection()
        try:
            return pd.read_sql(query, conn, params=params)
        finally:
            conn.close()

    # ----------------------------------
    # Cargar balances disponibles
    # ----------------------------------
    @app.callback(
        Output("stat-sel-balance", "options"),
        Input("stat-sel-tipo-variable", "value")
    )
    def cargar_balances(_):
        df = run_query(
            "SELECT DISTINCT bm_id FROM inventar_SpcHidr.Data_balance_rec"
        )
        return [
            {"label": str(x), "value": x}
            for x in sorted(df["bm_id"].dropna().unique())
        ]

    # ----------------------------------
    # Boxplot de errores
    # ----------------------------------
    @app.callback(
        Output("stat-g-box-ajuste", "figure"),
        Input("stat-sel-tipo-variable", "value")
    )
    def boxplot_error(tipo):

        df = run_query(BASE_QUERY)

        if tipo == "masa":
            y = "error_masa_pct"
            title = "Distribución del Error de Masa (%)"
        else:
            y = "error_ley_cu_pct"
            title = "Distribución del Error de Ley Cu (%)"

        fig = px.box(
            df,
            x="flujo",
            y=y,
            title=title
        )
        fig.update_layout(yaxis_title="Error (%)")

        return fig

    # ----------------------------------
    # Tendencia temporal
    # ----------------------------------
    @app.callback(
        Output("stat-g-tendencia-ajuste", "figure"),
        Input("stat-sel-tipo-variable", "value")
    )
    def tendencia_error(tipo):

        df = run_query(BASE_QUERY)

        if tipo == "masa":
            y = "error_masa_pct"
            ylab = "Error masa promedio (%)"
        else:
            y = "error_ley_cu_pct"
            ylab = "Error ley Cu promedio (%)"

        df_agg = (
            df.groupby("fecha_balance")[y]
              .mean()
              .reset_index()
        )

        fig = px.line(
            df_agg,
            x="fecha_balance",
            y=y,
            title="Tendencia Temporal del Error Promedio"
        )
        fig.update_layout(yaxis_title=ylab)

        return fig

    # ----------------------------------
    # Error vs tolerancia por balance
    # ----------------------------------
    @app.callback(
        Output("stat-g-barras-tolerancia", "figure"),
        Input("stat-sel-balance", "value"),
        Input("stat-sel-tipo-variable", "value")
    )
    def barras_tolerancia(bm_id, tipo):

        if not bm_id:
            return {}

        df = run_query(
            BASE_QUERY + " WHERE bm_id = ?",
            params=[bm_id]
        )

        if tipo == "masa":
            y = "error_masa_pct"
            tol = df["tol_masa_pct"].mean()
            title = f"Error de Masa vs Tolerancia – Balance {bm_id}"
        else:
            y = "error_ley_cu_pct"
            tol = df["tol_ley_cu_pct"].mean()
            title = f"Error de Ley Cu vs Tolerancia – Balance {bm_id}"

        fig = px.bar(
            df,
            x="flujo",
            y=y,
            title=title
        )

        fig.add_hline(
            y=tol,
            line_dash="dash",
            annotation_text=f"Tolerancia promedio = {tol:.2f} %"
        )

        fig.update_layout(yaxis_title="Error (%)")

        return fig
