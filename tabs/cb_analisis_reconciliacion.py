from dash import Input, Output
import pandas as pd
import plotly.express as px

# Imports compatibles con python main.py
from tabs.util.metrics_reconciliacion import preparar_metricas
from db_connection import get_connection


# ============================================================
# QUERY BASE
# ============================================================
BASE_QUERY = """
SELECT
    id_balance,
    fecha_balance,
    flujo,
    variable,
    valor_medido,
    valor_reconciliado,
    tolerancia_pct
FROM dbo.bm_resultados_reconciliacion
"""


# ============================================================
# UTILIDAD PARA EJECUTAR QUERIES
# ============================================================
def run_query(query, params=None):
    conn = get_connection()
    try:
        df = pd.read_sql(query, conn, params=params)
    finally:
        conn.close()
    return df


# ============================================================
# REGISTRO DE CALLBACKS DEL TAB ESTADÍSTICA
# ============================================================
def register_callbacks(app):

    # --------------------------------------------------------
    # Cargar balances disponibles
    # --------------------------------------------------------
    @app.callback(
        Output("stat-sel-balance", "options"),
        Input("stat-sel-tipo-variable", "value"),
    )
    def cargar_balances(_):
        df = run_query(
            "SELECT DISTINCT id_balance FROM dbo.bm_resultados_reconciliacion"
        )
        return [
            {"label": str(b), "value": b}
            for b in sorted(df["id_balance"].dropna().unique())
        ]


    # --------------------------------------------------------
    # Boxplot de % de ajuste por flujo
    # --------------------------------------------------------
    @app.callback(
        Output("stat-g-box-ajuste", "figure"),
        Input("stat-sel-tipo-variable", "value"),
    )
    def box_ajuste(tipo_variable):

        df = run_query(BASE_QUERY)
        df = preparar_metricas(df)

        if tipo_variable == "masa":
            df = df[df["variable"].isin(["TMH", "TMS"])]
        else:
            df = df[~df["variable"].isin(["TMH", "TMS"])]

        fig = px.box(
            df,
            x="flujo",
            y="delta_pct",
            color="cumple_tol",
            title="Distribución del % de Ajuste por Flujo",
            labels={
                "delta_pct": "% Ajuste",
                "cumple_tol": "Cumple tolerancia"
            }
        )

        fig.update_layout(
            yaxis_title="% Ajuste",
            xaxis_title="Flujo",
            legend_title="Cumple Tol."
        )

        return fig


    # --------------------------------------------------------
    # Tendencia temporal del ajuste promedio
    # --------------------------------------------------------
    @app.callback(
        Output("stat-g-tendencia-ajuste", "figure"),
        Input("stat-sel-tipo-variable", "value"),
    )
    def tendencia_ajuste(tipo_variable):

        df = run_query(BASE_QUERY)
        df = preparar_metricas(df)

        if tipo_variable == "masa":
            df = df[df["variable"].isin(["TMH", "TMS"])]
        else:
            df = df[~df["variable"].isin(["TMH", "TMS"])]

        df_agg = (
            df.groupby("fecha_balance")
              .agg(delta_pct_mean=("delta_pct", "mean"))
              .reset_index()
        )

        fig = px.line(
            df_agg,
            x="fecha_balance",
            y="delta_pct_mean",
            title="Tendencia Temporal del % de Ajuste Promedio",
            labels={
                "fecha_balance": "Fecha",
                "delta_pct_mean": "% Ajuste promedio"
            }
        )

        fig.update_layout(yaxis_title="% Ajuste promedio")

        return fig


    # --------------------------------------------------------
    # Barras de ajuste vs tolerancia para un balance
    # --------------------------------------------------------
    @app.callback(
        Output("stat-g-barras-tolerancia", "figure"),
        Input("stat-sel-balance", "value"),
    )
    def barras_tolerancia(id_balance):

        if not id_balance:
            return {}

        df = run_query(
            BASE_QUERY + " WHERE id_balance = ?",
            params=[id_balance]
        )

        df = preparar_metricas(df)

        fig = px.bar(
            df,
            x="flujo",
            y="delta_pct",
            color="cumple_tol",
            title=f"Ajustes vs Tolerancia – Balance {id_balance}",
            labels={
                "delta_pct": "% Ajuste",
                "cumple_tol": "Cumple tolerancia"
            }
        )

        fig.update_layout(
            yaxis_title="% Ajuste",
            xaxis_title="Flujo",
            legend_title="Cumple Tol."
        )

        return fig
