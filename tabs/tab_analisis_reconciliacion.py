from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import pandas as pd
import numpy as np
import plotly.express as px
from dash import dash_table

from db_connection import get_connection


# ============================================================
# DB UTIL
# ============================================================
def run_query(query: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    try:
        return pd.read_sql(query, conn, params=params)
    finally:
        conn.close()


# ============================================================
# HELPERS: SELECT ALL
# ============================================================
def normalize_casos(casos):
    if not casos:
        return []
    if "__ALL__" in casos:
        df = run_query("""
            SELECT DISTINCT cb.caso_id
            FROM inventar_SpcHidr.casos_balance cb
            INNER JOIN inventar_SpcHidr.Data_balance_rec dbr
                ON dbr.caso_id = cb.caso_id
        """)
        return df["caso_id"].dropna().tolist()
    return casos


def normalize_flujos(flujos, casos, fi, ff):
    if not flujos:
        return []
    if "__ALL_FLOWS__" in flujos:
        casos = normalize_casos(casos)
        if not casos or not fi or not ff:
            return []
        ph = ",".join("?" for _ in casos)
        df = run_query(
            f"""
            SELECT DISTINCT Flujo
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph})
              AND fecha_bm BETWEEN ? AND ?
            ORDER BY Flujo
            """,
            casos + [fi, ff]
        )
        return df["Flujo"].dropna().tolist()
    return flujos


# ============================================================
# CONTROL ESTADÍSTICO: SERIE ÚNICA POR FLUJO (NO por caso)
# ============================================================
def control_temporal_por_flujo(df: pd.DataFrame, tipo: str, lam: float = 0.2, L: float = 3.0) -> pd.DataFrame:
    """
    df: debe incluir columnas caso_id, fecha_bm, Flujo y variables.
    Construye control por flujo concatenando en el tiempo (casos solo filtran).
    """
    if df.empty:
        return df

    # Selección de variable
    if tipo == "masa":
        med, rec, tol_col = "Masa_medida", "Masa_recon", "Tolerancia"
    else:
        med, rec, tol_col = "Ley_medida_Cu", "Ley_recon_Cu", "Tolerancia_cu"

    df = df.copy()
    df["fecha_bm"] = pd.to_datetime(df["fecha_bm"], errors="coerce")
    df[med] = pd.to_numeric(df[med], errors="coerce")
    df[rec] = pd.to_numeric(df[rec], errors="coerce")
    df[tol_col] = pd.to_numeric(df[tol_col], errors="coerce")

    # z = (rec - med)/med
    df["z"] = np.where(df[med] != 0, (df[rec] - df[med]) / df[med], np.nan)

    # Orden SOLO por tiempo (por flujo)
    df = df.sort_values(["Flujo", "fecha_bm"]).copy()

    out = []
    for flujo, g in df.groupby("Flujo", sort=False):
        g = g.sort_values("fecha_bm").copy()
        z = g["z"].astype(float).fillna(0.0)

        # sigma: std(z) o proxy por tolerancia
        sigma = float(z.std(ddof=0)) if z.notna().sum() >= 3 else 0.0
        tol_pct = float((g[tol_col].dropna().mean() or 0.0) / 100.0)
        sigma = max(sigma, tol_pct / 3 if tol_pct > 0 else 0.001)

        # CUSUM parámetros
        k = 0.5 * sigma

        c_pos, c_neg = 0.0, 0.0
        cusum_p, cusum_n = [], []
        for v in z.to_numpy():
            c_pos = max(0.0, c_pos + (v - k))
            c_neg = min(0.0, c_neg + (v + k))
            cusum_p.append(c_pos)
            cusum_n.append(c_neg)

        # EWMA
        arr = z.to_numpy()
        ew = arr[0] if len(arr) else 0.0
        ewma = []
        for v in arr:
            ew = lam * v + (1 - lam) * ew
            ewma.append(ew)

        ewma_lim = L * sigma * np.sqrt(lam / (2 - lam))

        g["cusum_pos"] = cusum_p
        g["cusum_neg"] = cusum_n
        g["ewma"] = ewma
        g["ewma_lim"] = ewma_lim

        out.append(g)

    return pd.concat(out, ignore_index=True)


def semaforo_por_caso(df_ctrl: pd.DataFrame, lam: float, L: float) -> list[dict]:
    """
    Semáforo agregado por caso usando el último registro por flujo/caso.
    Nota: Control temporal se calcula por flujo concatenado; aquí sólo agregamos por caso con los datos disponibles.
    """
    if df_ctrl.empty:
        return []

    # Último por caso_id y flujo (según fecha)
    last = (
        df_ctrl.sort_values("fecha_bm")
              .groupby(["caso_id", "Flujo"], as_index=False)
              .tail(1)
    )

    rows = []
    for caso, g in last.groupby("caso_id", sort=False):
        n = len(g)

        # CRIT: EWMA supera límite o CUSUM muy alto (proxy)
        crit = int((g["ewma"].abs() > g["ewma_lim"]).sum())

        # WARN: EWMA sobre 70% del límite
        warn = int((g["ewma"].abs() > 0.7 * g["ewma_lim"]).sum())

        if crit > 0:
            estado = "CRITICO"
        elif warn / max(n, 1) >= 0.30:
            estado = "WARNING"
        else:
            estado = "OK"

        rows.append({
            "caso_id": caso,
            "estado": estado,
            "n_flujos": n,
            "warning": warn,
            "criticos": crit
        })

    # Orden por fecha más reciente del caso (no por id)
    ult = df_ctrl.groupby("caso_id")["fecha_bm"].max().reset_index().rename(columns={"fecha_bm": "fecha_ult"})
    out = pd.DataFrame(rows).merge(ult, on="caso_id", how="left").sort_values("fecha_ult", ascending=False)
    out = out.drop(columns=["fecha_ult"])
    return out.to_dict("records")


# ============================================================
# LAYOUT
# ============================================================
def render_tab_analisis_reconciliacion():

    def graph_card(title: str, graph_id: str, btn_id: str):
        return dbc.Card(
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.H6(title, className="fw-bold mb-0"), md=10),
                    dbc.Col(dbc.Button("⛶", id=btn_id, size="sm", color="secondary"), md=2, className="text-end"),
                ], className="mb-2"),
                dcc.Graph(id=graph_id),
            ]),
            className="shadow-sm mb-3"
        )

    return dbc.Container(
        fluid=True,
        children=[
            html.H4("📊 Estadística de Reconciliación", className="fw-bold text-primary"),

            # -----------------------------
            # CONTROLES (globales)
            # -----------------------------
            dbc.Card(
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Casos"),
                            dcc.Dropdown(
                                id="stat-sel-caso",
                                multi=True,
                                placeholder="Seleccione uno o más casos"
                            )
                        ], md=4),

                        dbc.Col([
                            dbc.Label("Flujos"),
                            dcc.Dropdown(
                                id="stat-sel-flujo",
                                multi=True,
                                placeholder="Seleccione uno o más flujos"
                            )
                        ], md=4),

                        dbc.Col([
                            dbc.Label("Variable"),
                            dcc.Dropdown(
                                id="stat-sel-tipo-variable",
                                options=[
                                    {"label": "Masa", "value": "masa"},
                                    {"label": "Ley Cu", "value": "ley"},
                                ],
                                value="masa",
                                clearable=False
                            )
                        ], md=2),

                        dbc.Col([
                            dbc.Label("Rango fechas"),
                            dcc.DatePickerRange(
                                id="stat-date-range",
                                display_format="YYYY-MM-DD",
                                minimum_nights=0
                            )
                        ], md=2),
                    ], className="g-2"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("λ (EWMA)"),
                            dcc.Input(
                                id="stat-lambda",
                                type="number",
                                value=0.2, min=0.05, max=0.5, step=0.05,
                                style={"width": "100%"}
                            )
                        ], md=2),

                        dbc.Col([
                            dbc.Label("L (límites)"),
                            dcc.Input(
                                id="stat-L",
                                type="number",
                                value=3.0, min=2.0, max=4.0, step=0.5,
                                style={"width": "100%"}
                            )
                        ], md=2),

                        dbc.Col([
                            html.Div(className="mt-4 text-muted small",
                                     children="Tip: usa 'TODOS' y baja con scroll para ver todos los flujos.")
                        ], md=8),
                    ], className="g-2 mt-2"),
                ]),
                className="shadow-sm mb-4"
            ),

            # ======================================================
            # SECCIÓN 1: ERRORES MEDIOS (REINCORPORADO)
            # ======================================================
            dbc.Card(
                dbc.CardBody([
                    html.H5("1️⃣ Errores medios (% ajuste) y tolerancias", className="fw-bold"),
                    graph_card("Boxplot de Error (%) por Flujo", "stat-g-box-errores", "btn-full-box"),
                    graph_card("Promedio Error (%) vs Tolerancia (%) por Flujo", "stat-g-barras-tolerancia", "btn-full-barras"),
                ]),
                className="shadow-sm mb-4"
            ),

            # ======================================================
            # SECCIÓN 2: CONTROL TEMPORAL (lo que ya funciona)
            # ======================================================
            dbc.Card(
                dbc.CardBody([
                    html.H5("2️⃣ Control temporal (Cartilla + CUSUM + EWMA)", className="fw-bold"),
                    graph_card("Cartilla: Medido vs Reconciliado (serie única por flujo)", "g-cartilla", "btn-full-cartilla"),
                    graph_card("CUSUM (facet por flujo)", "g-cusum", "btn-full-cusum"),
                    graph_card("EWMA (facet por flujo)", "g-ewma", "btn-full-ewma"),

                    html.H6("🚦 Semáforo agregado por caso", className="fw-bold mt-2"),
                    dash_table.DataTable(
                        id="tabla-semaforo",
                        columns=[
                            {"name": "caso_id", "id": "caso_id"},
                            {"name": "estado", "id": "estado"},
                            {"name": "n_flujos", "id": "n_flujos"},
                            {"name": "warning", "id": "warning"},
                            {"name": "criticos", "id": "criticos"},
                        ],
                        data=[],
                        page_size=10,
                        style_table={"overflowX": "auto"},
                        style_cell={"fontFamily": "Arial", "fontSize": 12, "padding": "6px"},
                        style_header={"fontWeight": "bold"},
                        style_data_conditional=[
                            {"if": {"filter_query": '{estado} = "OK"', "column_id": "estado"},
                             "color": "white", "backgroundColor": "#2E7D32"},
                            {"if": {"filter_query": '{estado} = "WARNING"', "column_id": "estado"},
                             "color": "black", "backgroundColor": "#F9A825"},
                            {"if": {"filter_query": '{estado} = "CRITICO"', "column_id": "estado"},
                             "color": "white", "backgroundColor": "#C62828"},
                        ]
                    ),
                ]),
                className="shadow-sm"
            ),

            # ======================================================
            # MODAL FULLSCREEN (pantalla completa)
            # ======================================================
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="modal-title-full")),
                    dbc.ModalBody(dcc.Graph(id="graph-fullscreen", style={"height": "80vh"})),
                ],
                id="modal-fullscreen",
                size="xl",
                is_open=False,
                scrollable=True,
            ),
        ]
    )


# ============================================================
# CALLBACKS
# ============================================================
def register_analisis_reconciliacion_callbacks(app):

    # --------------------------------------------------------
    # Opciones de casos (con TODOS)
    # --------------------------------------------------------
    @app.callback(
        Output("stat-sel-caso", "options"),
        Input("stat-sel-tipo-variable", "value")
    )
    def load_cases(_):
        df = run_query("""
            SELECT
                cb.caso_id,
                cb.nombre_caso,
                MAX(dbr.fecha_bm) AS fecha_ultima
            FROM inventar_SpcHidr.casos_balance cb
            INNER JOIN inventar_SpcHidr.Data_balance_rec dbr
                ON dbr.caso_id = cb.caso_id
            GROUP BY cb.caso_id, cb.nombre_caso
            ORDER BY MAX(dbr.fecha_bm) DESC
        """)

        opts = [{"label": "🟢 TODOS LOS CASOS", "value": "__ALL__"}]
        opts += [{"label": f"{r['nombre_caso']} ({r['fecha_ultima']})", "value": r["caso_id"]} for _, r in df.iterrows()]
        return opts


    # --------------------------------------------------------
    # Inicializar rango fechas MIN/MAX real según casos
    # --------------------------------------------------------
    @app.callback(
        [Output("stat-date-range", "min_date_allowed"),
         Output("stat-date-range", "max_date_allowed"),
         Output("stat-date-range", "start_date"),
         Output("stat-date-range", "end_date")],
        Input("stat-sel-caso", "value"),
    )
    def init_dates(casos):
        casos = normalize_casos(casos)
        if not casos:
            return [None] * 4

        ph = ",".join("?" for _ in casos)
        df = run_query(
            f"""
            SELECT MIN(fecha_bm) fi, MAX(fecha_bm) ff
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph})
            """,
            casos
        )
        fi, ff = df.loc[0, "fi"], df.loc[0, "ff"]
        return fi, ff, fi, ff


    # --------------------------------------------------------
    # Opciones flujos (con TODOS)
    # --------------------------------------------------------
    @app.callback(
        Output("stat-sel-flujo", "options"),
        Input("stat-sel-caso", "value"),
        Input("stat-date-range", "start_date"),
        Input("stat-date-range", "end_date"),
    )
    def load_flows(casos, fi, ff):
        casos = normalize_casos(casos)
        if not casos or not fi or not ff:
            return []

        ph = ",".join("?" for _ in casos)
        df = run_query(
            f"""
            SELECT DISTINCT Flujo
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph})
              AND fecha_bm BETWEEN ? AND ?
            ORDER BY Flujo
            """,
            casos + [fi, ff]
        )

        opts = [{"label": "🟢 TODOS LOS FLUJOS", "value": "__ALL_FLOWS__"}]
        opts += [{"label": f, "value": f} for f in df["Flujo"].dropna().tolist()]
        return opts


    # --------------------------------------------------------
    # Sección 1: Boxplot errores medios
    # --------------------------------------------------------
    @app.callback(
        Output("stat-g-box-errores", "figure"),
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-sel-tipo-variable", "value"),
        Input("stat-date-range", "start_date"),
        Input("stat-date-range", "end_date"),
    )
    def fig_box_errores(casos, flujos, tipo, fi, ff):
        casos = normalize_casos(casos)
        if not casos or not flujos or not fi or not ff:
            return {}

        flujos = normalize_flujos(flujos, casos, fi, ff)
        if not flujos:
            return {}

        ph_c = ",".join("?" for _ in casos)
        ph_f = ",".join("?" for _ in flujos)

        df = run_query(
            f"""
            SELECT caso_id, fecha_bm, Flujo, Error_masa, Error_ley_Cu, Tolerancia, Tolerancia_cu
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph_c})
              AND Flujo IN ({ph_f})
              AND fecha_bm BETWEEN ? AND ?
            ORDER BY fecha_bm
            """,
            casos + flujos + [fi, ff]
        )

        y = "Error_masa" if tipo == "masa" else "Error_ley_Cu"
        df[y] = pd.to_numeric(df[y], errors="coerce")

        fig = px.box(
            df,
            x="Flujo",
            y=y,
            points="outliers",
            title="Distribución de Error (%) por flujo (agregado en el rango de fechas)"
        )
        fig.update_layout(yaxis_title="Error (%)", hovermode="x unified")
        return fig


    # --------------------------------------------------------
    # Sección 1: Barras error medio vs tolerancia (por flujo)
    # --------------------------------------------------------
    @app.callback(
        Output("stat-g-barras-tolerancia", "figure"),
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-sel-tipo-variable", "value"),
        Input("stat-date-range", "start_date"),
        Input("stat-date-range", "end_date"),
    )
    def fig_barras_tolerancia(casos, flujos, tipo, fi, ff):
        casos = normalize_casos(casos)
        if not casos or not flujos or not fi or not ff:
            return {}

        flujos = normalize_flujos(flujos, casos, fi, ff)
        if not flujos:
            return {}

        ph_c = ",".join("?" for _ in casos)
        ph_f = ",".join("?" for _ in flujos)

        df = run_query(
            f"""
            SELECT caso_id, fecha_bm, Flujo, Error_masa, Error_ley_Cu, Tolerancia, Tolerancia_cu
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph_c})
              AND Flujo IN ({ph_f})
              AND fecha_bm BETWEEN ? AND ?
            ORDER BY fecha_bm
            """,
            casos + flujos + [fi, ff]
        )

        if tipo == "masa":
            err_col = "Error_masa"
            tol_col = "Tolerancia"
            title = "Error medio Masa (%) vs Tolerancia (%)"
        else:
            err_col = "Error_ley_Cu"
            tol_col = "Tolerancia_cu"
            title = "Error medio Ley Cu (%) vs Tolerancia (%)"

        df[err_col] = pd.to_numeric(df[err_col], errors="coerce")
        df[tol_col] = pd.to_numeric(df[tol_col], errors="coerce")

        agg = (
            df.groupby("Flujo", as_index=False)
              .agg(err_mean=(err_col, "mean"), tol_mean=(tol_col, "mean"))
        )
        agg["cumple"] = agg["err_mean"].abs() <= agg["tol_mean"]

        fig = px.bar(
            agg,
            x="Flujo",
            y="err_mean",
            color="cumple",
            title=title
        )
        fig.update_layout(yaxis_title="Error medio (%)", hovermode="x unified")
        return fig


    # --------------------------------------------------------
    # Sección 2: Control temporal (cartilla + cusum + ewma + semáforo)
    # --------------------------------------------------------
    @app.callback(
        [
            Output("g-cartilla", "figure"),
            Output("g-cusum", "figure"),
            Output("g-ewma", "figure"),
            Output("tabla-semaforo", "data"),
        ],
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-sel-tipo-variable", "value"),
        Input("stat-date-range", "start_date"),
        Input("stat-date-range", "end_date"),
        Input("stat-lambda", "value"),
        Input("stat-L", "value"),
    )
    def update_control_temporal(casos, flujos, tipo, fi, ff, lam, L):
        casos = normalize_casos(casos)
        if not casos or not flujos or not fi or not ff:
            return {}, {}, {}, []

        flujos = normalize_flujos(flujos, casos, fi, ff)
        if not flujos:
            return {}, {}, {}, []

        lam = float(lam or 0.2)
        L = float(L or 3.0)

        ph_c = ",".join("?" for _ in casos)
        ph_f = ",".join("?" for _ in flujos)

        df = run_query(
            f"""
            SELECT
                caso_id,
                fecha_bm,
                Flujo,
                Masa_medida, Masa_recon, Tolerancia,
                Ley_medida_Cu, Ley_recon_Cu, Tolerancia_cu
            FROM inventar_SpcHidr.Data_balance_rec
            WHERE caso_id IN ({ph_c})
              AND Flujo IN ({ph_f})
              AND fecha_bm BETWEEN ? AND ?
            ORDER BY fecha_bm
            """,
            casos + flujos + [fi, ff]
        )

        if df.empty:
            return {}, {}, {}, []

        # CARTILLA (NO series por caso, solo facet por flujo)
        if tipo == "masa":
            y_med, y_rec = "Masa_medida", "Masa_recon"
            ylabel = "Masa"
        else:
            y_med, y_rec = "Ley_medida_Cu", "Ley_recon_Cu"
            ylabel = "Ley Cu"

        fig_cart = px.line(
            df,
            x="fecha_bm",
            y=[y_med, y_rec],
            facet_row="Flujo",
            markers=True,
            title="Cartilla de Control – Serie temporal por flujo (casos solo filtran)"
        )
        fig_cart.update_layout(height=max(450, 260 * df["Flujo"].nunique()), yaxis_title=ylabel, hovermode="x unified")

        # Control estadístico
        df_ctrl = control_temporal_por_flujo(df, tipo=tipo, lam=lam, L=L)

        fig_cusum = px.line(
            df_ctrl,
            x="fecha_bm",
            y=["cusum_pos", "cusum_neg"],
            facet_row="Flujo",
            title="CUSUM por flujo (serie temporal)"
        )
        fig_cusum.update_layout(height=max(450, 260 * df_ctrl["Flujo"].nunique()), hovermode="x unified")

        fig_ewma = px.line(
            df_ctrl,
            x="fecha_bm",
            y="ewma",
            facet_row="Flujo",
            title="EWMA por flujo (serie temporal)"
        )
        fig_ewma.update_layout(height=max(450, 260 * df_ctrl["Flujo"].nunique()), hovermode="x unified")

        # Límites EWMA (±)
        fig_ewma.add_scatter(
            x=df_ctrl["fecha_bm"], y=df_ctrl["ewma_lim"],
            mode="lines", line=dict(dash="dot", color="red"),
            name="+Límite"
        )
        fig_ewma.add_scatter(
            x=df_ctrl["fecha_bm"], y=-df_ctrl["ewma_lim"],
            mode="lines", line=dict(dash="dot", color="red"),
            name="-Límite"
        )

        sem = semaforo_por_caso(df_ctrl, lam=lam, L=L)
        return fig_cart, fig_cusum, fig_ewma, sem


    # --------------------------------------------------------
    # FULLSCREEN: abre el gráfico clickeado en modal
    # --------------------------------------------------------
    @app.callback(
        [Output("modal-fullscreen", "is_open"),
         Output("graph-fullscreen", "figure"),
         Output("modal-title-full", "children")],
        [
            Input("btn-full-box", "n_clicks"),
            Input("btn-full-barras", "n_clicks"),
            Input("btn-full-cartilla", "n_clicks"),
            Input("btn-full-cusum", "n_clicks"),
            Input("btn-full-ewma", "n_clicks"),
        ],
        [
            State("stat-g-box-errores", "figure"),
            State("stat-g-barras-tolerancia", "figure"),
            State("g-cartilla", "figure"),
            State("g-cusum", "figure"),
            State("g-ewma", "figure"),
            State("modal-fullscreen", "is_open"),
        ],
        prevent_initial_call=True
    )
    def fullscreen(n1, n2, n3, n4, n5, fig_box, fig_bar, fig_cart, fig_cusum, fig_ewma, is_open):
        trig = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else None

        title_map = {
            "btn-full-box": "Boxplot Error (%) – Pantalla completa",
            "btn-full-barras": "Error medio vs Tolerancia – Pantalla completa",
            "btn-full-cartilla": "Cartilla – Pantalla completa",
            "btn-full-cusum": "CUSUM – Pantalla completa",
            "btn-full-ewma": "EWMA – Pantalla completa",
        }

        fig_map = {
            "btn-full-box": fig_box,
            "btn-full-barras": fig_bar,
            "btn-full-cartilla": fig_cart,
            "btn-full-cusum": fig_cusum,
            "btn-full-ewma": fig_ewma,
        }

        if not trig or trig not in fig_map:
            return is_open, {}, "Vista Pantalla Completa"

        return True, fig_map[trig], title_map.get(trig, "Vista Pantalla Completa")
