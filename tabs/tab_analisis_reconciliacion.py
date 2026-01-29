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
# CONSTANTES / TOKENS
# ============================================================
ALL_CASES = "__ALL__"
ALL_FLOWS = "__ALL_FLOWS__"


# ============================================================
# HELPERS
# ============================================================
def safe_date_str(x):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    try:
        return pd.to_datetime(x).strftime("%Y-%m-%d")
    except Exception:
        return str(x)


def normalize_casos(casos):
    if not casos:
        return []
    if ALL_CASES in casos:
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
    if ALL_FLOWS in flujos:
        casos = normalize_casos(casos)
        if not casos or not fi or not ff:
            return []
        ph = ",".join("?" for _ in casos)
        df = run_query(
            f"""
            SELECT DISTINCT dbr.Flujo
            FROM inventar_SpcHidr.Data_balance_rec dbr
            WHERE dbr.caso_id IN ({ph})
              AND dbr.fecha_bm BETWEEN ? AND ?
            ORDER BY dbr.Flujo
            """,
            casos + [fi, ff]
        )
        return df["Flujo"].dropna().tolist()
    return flujos


# ============================================================
# CONTROL TEMPORAL (serie única por flujo; casos solo filtran)
# ============================================================
def control_temporal_por_flujo(df, tipo, lam=0.2, L=3.0):
    if df.empty:
        return df

    if tipo == "masa":
        med, rec, tol_col = "Masa_medida", "Masa_recon", "Tolerancia"
    else:
        med, rec, tol_col = "Ley_medida_Cu", "Ley_recon_Cu", "Tolerancia_cu"

    df = df.copy()
    df["fecha_bm"] = pd.to_datetime(df["fecha_bm"], errors="coerce")
    df = df.dropna(subset=["fecha_bm", "Flujo"])

    for c in [med, rec, tol_col]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df["z"] = np.where(df[med] != 0, (df[rec] - df[med]) / df[med], 0.0)
    df = df.sort_values(["Flujo", "fecha_bm"]).copy()

    out = []
    for flujo, g in df.groupby("Flujo", sort=False):
        g = g.sort_values("fecha_bm").copy()
        z = g["z"].fillna(0.0).to_numpy()

        sigma = float(np.std(z)) if len(z) >= 3 else 0.0
        tol_pct = float((g[tol_col].dropna().mean() or 0.0) / 100.0)
        sigma = max(sigma, (tol_pct / 3) if tol_pct > 0 else 0.001)

        # CUSUM
        k = 0.5 * sigma
        cpos, cneg = 0.0, 0.0
        cp, cn = [], []
        for v in z:
            cpos = max(0.0, cpos + (v - k))
            cneg = min(0.0, cneg + (v + k))
            cp.append(cpos)
            cn.append(cneg)

        # EWMA
        ew = z[0] if len(z) else 0.0
        ewma = []
        for v in z:
            ew = lam * v + (1 - lam) * ew
            ewma.append(ew)

        g["cusum_pos"] = cp
        g["cusum_neg"] = cn
        g["ewma"] = ewma
        g["ewma_lim"] = L * sigma * np.sqrt(lam / (2 - lam))

        out.append(g)

    return pd.concat(out, ignore_index=True) if out else df


def semaforo_por_caso(df_ctrl):
    if df_ctrl.empty:
        return []

    last = (
        df_ctrl.sort_values("fecha_bm")
               .groupby(["caso_id", "Flujo"], as_index=False)
               .tail(1)
    )

    rows = []
    for caso, g in last.groupby("caso_id", sort=False):
        crit = int((g["ewma"].abs() > g["ewma_lim"]).sum())
        warn = int((g["ewma"].abs() > 0.7 * g["ewma_lim"]).sum())
        estado = "CRITICO" if crit > 0 else "WARNING" if warn > 0 else "OK"
        rows.append({
            "caso_id": caso,
            "estado": estado,
            "n_flujos": int(len(g)),
            "warning": warn,
            "criticos": crit
        })
    return rows


# ============================================================
# LAYOUT
# ============================================================
def render_tab_analisis_reconciliacion():

    def graph_card(title, graph_id, btn_full_id):
        return dbc.Card(
            dbc.CardBody([
                dbc.Row([
                    dbc.Col(html.H6(title, className="fw-bold mb-2"), md=10),
                    dbc.Col(dbc.Button("⛶", id=btn_full_id, size="sm"), md=2, className="text-end"),
                ], className="g-2"),
                dcc.Graph(id=graph_id),
            ]),
            className="shadow-sm mb-3"
        )

    return dbc.Container(
        fluid=True,
        children=[
            dcc.Store(id="stat-selected-flujo", data=None),

            html.H4("📊 Estadística de Reconciliación", className="fw-bold text-primary"),

            dbc.Row([
                dbc.Col(
                    dbc.Button("🧹 Limpiar selección de flujo",
                               id="btn-clear-flujo",
                               size="sm",
                               color="secondary"),
                    md="auto"
                ),
                dbc.Col(
                    html.Div(id="stat-msg-drill", className="text-muted small mt-2"),
                    md=True
                )
            ], className="mb-2"),

            dbc.Card(
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Casos"),
                            dcc.Dropdown(
                                id="stat-sel-caso",
                                multi=True,
                                placeholder="Seleccione uno o más casos...",
                            )
                        ], md=4),

                        dbc.Col([
                            dbc.Label("Flujos"),
                            dcc.Dropdown(
                                id="stat-sel-flujo",
                                multi=True,
                                placeholder="Seleccione uno o más flujos...",
                            )
                        ], md=4),

                        dbc.Col([
                            dbc.Label("Variable"),
                            dcc.Dropdown(
                                id="stat-sel-tipo",
                                options=[
                                    {"label": "Masa", "value": "masa"},
                                    {"label": "Ley Cu", "value": "ley"},
                                ],
                                value="masa",
                                clearable=False
                            )
                        ], md=2),

                        dbc.Col([
                            dbc.Label("Fechas"),
                            dcc.DatePickerRange(
                                id="stat-fechas",
                                display_format="YYYY-MM-DD",
                                minimum_nights=0
                            )
                        ], md=2),
                    ], className="g-2"),

                    dbc.Row([
                        dbc.Col([
                            dbc.Label("λ (EWMA)"),
                            dcc.Input(id="stat-lambda", type="number",
                                      min=0.05, max=0.5, step=0.05, value=0.2,
                                      style={"width": "100%"})
                        ], md=2),
                        dbc.Col([
                            dbc.Label("L (límites)"),
                            dcc.Input(id="stat-L", type="number",
                                      min=2.0, max=4.0, step=0.5, value=3.0,
                                      style={"width": "100%"})
                        ], md=2),
                        dbc.Col(
                            html.Div("Tip: click en Boxplot/Barras para drill-down al flujo (Cartilla/CUSUM/EWMA).",
                                     className="small text-muted mt-4"),
                            md=8
                        )
                    ], className="g-2 mt-2"),
                ]),
                className="shadow-sm mb-4"
            ),

            html.H5("1️⃣ Errores medios y tolerancias", className="fw-bold"),
            graph_card("Boxplot Error (%) por Flujo + línea del último caso", "stat-box-errores", "btn-full-box"),
            graph_card("Error medio (%) vs Tolerancia (%) por Flujo", "stat-bar-tolerancia", "btn-full-barras"),

            html.H5("2️⃣ Control temporal (Cartilla + CUSUM + EWMA)", className="fw-bold mt-3"),
            graph_card("Cartilla: Medido vs Reconciliado (serie única por flujo)", "stat-cartilla", "btn-full-cartilla"),
            graph_card("CUSUM por flujo", "stat-cusum", "btn-full-cusum"),
            graph_card("EWMA por flujo (con límites)", "stat-ewma", "btn-full-ewma"),

            html.H6("🚦 Semáforo agregado por caso", className="fw-bold mt-3"),
            dash_table.DataTable(
                id="stat-semaforo",
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
            ),

            # ---------- FULLSCREEN MODAL ----------
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle(id="stat-modal-title")),
                    dbc.ModalBody(dcc.Graph(id="stat-modal-graph")),
                    dbc.ModalFooter(
                        dbc.Button("Cerrar", id="stat-close-modal", color="secondary")
                    )
                ],
                id="stat-modal",
                is_open=False,
                size="xl",
                centered=True
            )
        ]
    )


# ============================================================
# CALLBACKS
# ============================================================
def register_analisis_reconciliacion_callbacks(app):

    # ----------------------------
    # Opciones casos (label=nombre_caso + fecha_ultima, value=caso_id)
    # + TODOS
    # ----------------------------
    @app.callback(
        Output("stat-sel-caso", "options"),
        Input("stat-sel-tipo", "value")
    )
    def cargar_casos(_):
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

        opts = [{"label": "🟢 TODOS LOS CASOS", "value": ALL_CASES}]
        for _, r in df.iterrows():
            opts.append({
                "label": f"{r['nombre_caso']} ({safe_date_str(r['fecha_ultima'])})",
                "value": r["caso_id"]
            })
        return opts

    # ----------------------------
    # Inicializar rango fechas según casos (min/max real)
    # ----------------------------
    @app.callback(
        [Output("stat-fechas", "min_date_allowed"),
         Output("stat-fechas", "max_date_allowed"),
         Output("stat-fechas", "start_date"),
         Output("stat-fechas", "end_date")],
        Input("stat-sel-caso", "value"),
    )
    def init_dates(casos):
        casos = normalize_casos(casos)
        if not casos:
            return None, None, None, None

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

    # ----------------------------
    # Opciones flujos según casos + fechas
    # + TODOS
    # ----------------------------
    
    @app.callback(
        Output("stat-sel-flujo", "options"),
        Input("stat-sel-caso", "value"),
        Input("stat-fechas", "start_date"),
        Input("stat-fechas", "end_date"),
    )
    def cargar_flujos(casos, fi, ff):
        casos = normalize_casos(casos)
        if not casos or not fi or not ff:
            return []

        ph = ",".join("?" for _ in casos)
        
        # Consulta optimizada con JOIN
        # Traemos el Flujo (id original) y el Nombre (para mostrar)
        query = f"""
            SELECT DISTINCT 
                dbr.Flujo as id_flujo,
                COALESCE(dic.Nombre, dbr.Flujo) as nombre_flujo
            FROM inventar_SpcHidr.Data_balance_rec dbr
            LEFT JOIN inventar_SpcHidr.Diccionario_Flujos dic
                ON dbr.Flujo = dic.Flujo
            WHERE dbr.caso_id IN ({ph})
              AND dbr.fecha_bm BETWEEN ? AND ?
            ORDER BY nombre_flujo
        """
        
        df = run_query(query, casos + [fi, ff])

        opts = [{"label": "🟢 TODOS LOS FLUJOS", "value": ALL_FLOWS}]
        
        for _, row in df.iterrows():
            # Label = Nombre bonito, Value = ID original (para que los filtros de query_filtered funcionen)
            opts.append({"label": row["nombre_flujo"], "value": row["id_flujo"]})
            
        return opts

    # ----------------------------
    # Drill-down por click (boxplot o barras) + limpiar
    # ----------------------------
    @app.callback(
        Output("stat-selected-flujo", "data"),
        Input("stat-box-errores", "clickData"),
        Input("stat-bar-tolerancia", "clickData"),
        Input("btn-clear-flujo", "n_clicks"),
        prevent_initial_call=True
    )
    def capture_flujo(box_click, bar_click, clear_click):
        if callback_context.triggered_id == "btn-clear-flujo":
            return None
        cd = box_click or bar_click
        if not cd:
            return None
        return cd["points"][0].get("x")

    @app.callback(
        Output("stat-msg-drill", "children"),
        Input("stat-selected-flujo", "data"),
    )
    def drill_label(flujo):
        if not flujo:
            return "Drill-down: sin flujo fijo."
        return f"Drill-down activo: Flujo = {flujo}. (Usa “Limpiar selección” para volver)."

    # ----------------------------
    # Query base filtrada
    # ----------------------------
    def query_filtered(casos, flujos, fi, ff):
        casos = normalize_casos(casos)
        flujos = normalize_flujos(flujos, casos, fi, ff)
        if not casos or not flujos or not fi or not ff:
            return pd.DataFrame()

        ph_c = ",".join("?" for _ in casos)
        ph_f = ",".join("?" for _ in flujos)

        # USAMOS LEFT JOIN PARA TRAER EL NOMBRE
        # COALESCE(dic.Nombre, dbr.Flujo) significa: Si hay nombre en el diccionario, úsalo; 
        # si no (es null), usa el código de flujo original (dbr.Flujo).
        query = f"""
            SELECT
                dbr.bm_id,
                dbr.caso_id,
                dbr.fecha_bm,
                COALESCE(dic.Nombre, dbr.Flujo) as Flujo, -- <--- AQUÍ ESTÁ EL CAMBIO CLAVE
                dbr.Masa_medida, dbr.Masa_recon, dbr.Tolerancia,
                dbr.Ley_medida_Cu, dbr.Ley_recon_Cu, dbr.Tolerancia_cu,
                dbr.Error_masa, dbr.Error_ley_Cu
            FROM inventar_SpcHidr.Data_balance_rec dbr
            LEFT JOIN inventar_SpcHidr.Diccionario_Flujos dic
                ON dbr.Flujo = dic.Flujo
            WHERE dbr.caso_id IN ({ph_c})
            AND dbr.Flujo IN ({ph_f})
            AND dbr.fecha_bm BETWEEN ? AND ?
            ORDER BY dbr.fecha_bm
        """
        
        df = run_query(query, casos + flujos + [fi, ff])
        return df

    # ----------------------------
    # FIG 1: Boxplot + línea último caso por fecha (por flujo)
    # ----------------------------
    @app.callback(
        Output("stat-box-errores", "figure"),
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-sel-tipo", "value"),
        Input("stat-fechas", "start_date"),
        Input("stat-fechas", "end_date"),
    )
    def fig_box(casos, flujos, tipo, fi, ff):
        df = query_filtered(casos, flujos, fi, ff)
        if df.empty:
            return {}

        y = "Error_masa" if tipo == "masa" else "Error_ley_Cu"
        df[y] = pd.to_numeric(df[y], errors="coerce")

        fig = px.box(
            df,
            x="Flujo",
            y=y,
            points="outliers",
            title="Distribución del Error (%) por Flujo"
        )

        # último caso por fecha dentro de la selección (por flujo)
        df_last = (
            df.sort_values("fecha_bm")
              .groupby("Flujo", as_index=False)
              .tail(1)
        ).copy()

        # ordenar flows para trazar línea coherente
        df_last = df_last.sort_values("Flujo")

        fig.add_scatter(
            x=df_last["Flujo"],
            y=df_last[y],
            mode="lines+markers",
            name="Último caso (por fecha)",
            line=dict(color="green", width=1),
            marker=dict(size=5, color="green")
        )

        fig.update_layout(hovermode="x unified", yaxis_title="Error (%)")
        return fig

    # ----------------------------
    # FIG 2: Barras error medio vs tolerancia (clickable para drill)
    # ----------------------------
    @app.callback(
        Output("stat-bar-tolerancia", "figure"),
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-sel-tipo", "value"),
        Input("stat-fechas", "start_date"),
        Input("stat-fechas", "end_date"),
    )
    def fig_barras(casos, flujos, tipo, fi, ff):
        df = query_filtered(casos, flujos, fi, ff)
        if df.empty:
            return {}

        if tipo == "masa":
            err_col, tol_col = "Error_masa", "Tolerancia"
            title = "Error medio Masa (%) vs Tolerancia (%)"
        else:
            err_col, tol_col = "Error_ley_Cu", "Tolerancia_cu"
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
        fig.update_layout(hovermode="x unified", yaxis_title="Error medio (%)")
        return fig

    # ----------------------------
    # FIG 3/4/5: Cartilla + CUSUM + EWMA + Semáforo
    # - Drill-down: si hay flujo seleccionado por click, fija ese flujo
    # ----------------------------
    @app.callback(
        [
            Output("stat-cartilla", "figure"),
            Output("stat-cusum", "figure"),
            Output("stat-ewma", "figure"),
            Output("stat-semaforo", "data"),
        ],
        Input("stat-sel-caso", "value"),
        Input("stat-sel-flujo", "value"),
        Input("stat-selected-flujo", "data"),
        Input("stat-sel-tipo", "value"),
        Input("stat-fechas", "start_date"),
        Input("stat-fechas", "end_date"),
        Input("stat-lambda", "value"),
        Input("stat-L", "value"),
    )
    def fig_control(casos, flujos, flujo_click, tipo, fi, ff, lam, L):
        import plotly.graph_objects as go  # Importamos graph_objects para usar Scattergl

        if not casos or not flujos or not fi or not ff:
            return {}, {}, {}, []

        flujos_eff = [flujo_click] if flujo_click else flujos
        df = query_filtered(casos, flujos_eff, fi, ff)
        if df.empty:
            return {}, {}, {}, []

        lam = float(lam or 0.2)
        L = float(L or 3.0)

        if tipo == "masa":
            y_med, y_rec, ylabel = "Masa_medida", "Masa_recon", "Masa"
        else:
            y_med, y_rec, ylabel = "Ley_medida_Cu", "Ley_recon_Cu", "Ley Cu"

        # Calcular datos de control (CUSUM, EWMA)
        df_ctrl = control_temporal_por_flujo(df, tipo=tipo, lam=lam, L=L)

        # --- FUNCIÓN HELPER PARA CREAR GRÁFICOS WEBGL ---
        def create_webgl_fig(data, x_col, y_cols, title, y_title=None):
            fig = go.Figure()
            # Iterar por flujo para crear líneas independientes
            for flujo, g in data.groupby("Flujo"):
                for y_col in y_cols:
                    # Diferenciar estilo si es medido vs reconciliado o positivo vs negativo
                    line_style = dict(width=1)
                    if "recon" in y_col:
                        line_style["dash"] = "dash"
                    
                    fig.add_trace(go.Scattergl(
                        x=g[x_col],
                        y=g[y_col],
                        mode='lines+markers',
                        name=f"{flujo} - {y_col}",
                        line=line_style,
                        marker=dict(size=4)
                    ))
            
            fig.update_layout(
                title=title,
                yaxis_title=y_title,
                hovermode="x unified",
                template="plotly_white",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            return fig

        # 1. Cartilla (Scattergl)
        fig_cart = go.Figure()
        for flujo, g in df.groupby("Flujo"):
            fig_cart.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g[y_med], mode='lines+markers', name=f"{flujo} Medido",
                line=dict(width=1), marker=dict(size=4)
            ))
            fig_cart.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g[y_rec], mode='lines', name=f"{flujo} Recon",
                line=dict(width=1, dash='dash')
            ))
        fig_cart.update_layout(title="Cartilla – Medido vs Reconciliado", yaxis_title=ylabel, hovermode="x unified")

        # 2. CUSUM (Scattergl)
        fig_cusum = go.Figure()
        for flujo, g in df_ctrl.groupby("Flujo"):
            fig_cusum.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g["cusum_pos"], mode='lines', name=f"{flujo} CUSUM+",
                line=dict(width=1)
            ))
            fig_cusum.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g["cusum_neg"], mode='lines', name=f"{flujo} CUSUM-",
                line=dict(width=1)
            ))
        fig_cusum.update_layout(title="CUSUM por flujo", hovermode="x unified")

        # 3. EWMA (Scattergl)
        fig_ewma = go.Figure()
        for flujo, g in df_ctrl.groupby("Flujo"):
            # Línea EWMA
            fig_ewma.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g["ewma"], mode='lines+markers', name=f"{flujo} EWMA",
                line=dict(width=1), marker=dict(size=4)
            ))
            # Límites (Usamos Scattergl también para consistencia)
            fig_ewma.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=g["ewma_lim"], mode='lines', name=f"{flujo} +Lim",
                line=dict(width=1, dash='dot', color='red'), showlegend=False
            ))
            fig_ewma.add_trace(go.Scattergl(
                x=g["fecha_bm"], y=-g["ewma_lim"], mode='lines', name=f"{flujo} -Lim",
                line=dict(width=1, dash='dot', color='red'), showlegend=False
            ))
        fig_ewma.update_layout(title="EWMA por flujo", hovermode="x unified")

        # Semáforo
        sem = semaforo_por_caso(df_ctrl)
        
        return fig_cart, fig_cusum, fig_ewma, sem
    # ----------------------------
    # FULLSCREEN MODAL (por gráfico)
    # ----------------------------
    @app.callback(
        [Output("stat-modal", "is_open"),
         Output("stat-modal-title", "children"),
         Output("stat-modal-graph", "figure")],
        Input("btn-full-box", "n_clicks"),
        Input("btn-full-barras", "n_clicks"),
        Input("btn-full-cartilla", "n_clicks"),
        Input("btn-full-cusum", "n_clicks"),
        Input("btn-full-ewma", "n_clicks"),
        Input("stat-close-modal", "n_clicks"),
        State("stat-modal", "is_open"),
        State("stat-box-errores", "figure"),
        State("stat-bar-tolerancia", "figure"),
        State("stat-cartilla", "figure"),
        State("stat-cusum", "figure"),
        State("stat-ewma", "figure"),
        prevent_initial_call=True
    )
    def toggle_fullscreen(n1, n2, n3, n4, n5, close, is_open,
                          fig_box, fig_bar, fig_cart, fig_cusum, fig_ewma):
        trig = callback_context.triggered_id
        if trig == "stat-close-modal":
            return False, "", {}

        mapping = {
            "btn-full-box": ("Boxplot Error (%)", fig_box),
            "btn-full-barras": ("Barras Error vs Tolerancia", fig_bar),
            "btn-full-cartilla": ("Cartilla Medido vs Reconciliado", fig_cart),
            "btn-full-cusum": ("CUSUM por flujo", fig_cusum),
            "btn-full-ewma": ("EWMA por flujo", fig_ewma),
        }

        if trig in mapping:
            title, fig = mapping[trig]
            return True, title, fig

        return is_open, "", {}
