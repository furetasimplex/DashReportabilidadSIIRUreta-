# ==============================================================================
# tabs/tab6.py
# TAB 6 – PRECONTROL DESBALANCE (GRILLA) + HISTÓRICOS (BD)
# ------------------------------------------------------------------------------
# Fuente de verdad PRE-reconciliación: grilla activa (recon-data-base.rowData)
# Comparación histórica: tablas guardadas (ej: inventar_SpcHidr.bm_desbalance_nodo)
# + Histórico por flujo usando Data_balance_rec + casos_balance
# ==============================================================================

import pandas as pd
import numpy as np

from dash import html, dcc
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from sqlalchemy import text

from tabs.tab6_base import render_tab6_base, register_tab6_base_callbacks
from db_connection import get_engine

# ------------------------------------------------------------------------------
# AG Grid (si existe en tu proyecto)
# ------------------------------------------------------------------------------
try:
    import dash_ag_grid as dag
    HAS_AGGRID = True
except Exception:
    from dash import dash_table
    HAS_AGGRID = False


# ==============================================================================
# Engine global (una sola fuente)
# ==============================================================================
ENGINE = get_engine()  # SQLAlchemy engine o None

columnsDefs_resultados =  [
        {'field': 'Codigo'         , 'maxWidth': 100},
        {'field': 'Flujo'         , 'maxWidth': 450},
        {'field': 'Masa medida'    , 'maxWidth': 120},
        {'field': 'Masa recon'   , 'maxWidth': 120},
        {'field': 'Error masa'  , 'maxWidth': 120},
        {'field': 'Ley medida Cu' , 'maxWidth': 120},
        {'field': 'Ley recon Cu'  , 'maxWidth': 120},
        {'field': 'Error ley Cu'  , 'maxWidth': 120},
        ]
columnsDefs_desbalances =  [
        {'field': 'Area', 'maxWidth': 200, 'editable': False},
        {'field': 'Desbalance masa inicial', 'maxWidth': 140, 'editable': False},
        {'field': 'Desbalance masa', 'maxWidth': 140, 'editable': False},
        {'field': 'Desbalance fino inicial Cu', 'maxWidth': 140, 'editable': False},
        {'field': 'Desbalance fino Cu', 'maxWidth': 140, 'editable': False},
        ]
# ==============================================================================
# Helpers DB y utilitarios
# ==============================================================================
def _read_sql(engine, sql_text, params=None):
    """
    Lectura robusta para SQL Server + pyodbc usando SQLAlchemy.
    - sql_text: string SQL (puede tener :params)
    - params: dict params
    """
    if engine is None:
        return pd.DataFrame()

    stmt = text(sql_text)
    with engine.connect() as cn:
        return pd.read_sql(stmt, cn, params=params or {})


def _safe_float(x, default=0.0):
    try:
        v = float(x)
        if np.isnan(v):
            return default
        return v
    except Exception:
        return default


def _get_caso_id(shared):
    if not shared:
        return None
    return shared.get("caso_id") or shared.get("id_caso") or shared.get("id_caso_activo")


def _get_periodo_caso(engine, caso_id):
    """
    Obtiene fecha_ini (inicio) y fecha (fin) del caso.
    """
    df = _read_sql(
        engine,
        """
        SELECT TOP 1
            fecha_ini AS fi,
            fecha     AS ff,
            modelo    AS modelo
        FROM inventar_SpcHidr.casos_balance
        WHERE caso_id = :c
        ORDER BY fecha DESC
        """,
        {"c": caso_id},
    )
    if df.empty:
        return None, None, None

    fi = pd.to_datetime(df["fi"].iloc[0]).date() if pd.notna(df["fi"].iloc[0]) else None
    ff = pd.to_datetime(df["ff"].iloc[0]).date() if pd.notna(df["ff"].iloc[0]) else None
    modelo = int(df["modelo"].iloc[0]) if pd.notna(df["modelo"].iloc[0]) else None

    if fi and ff and fi > ff:
        fi, ff = ff, fi

    return fi, ff, modelo


def _get_topologia(engine, caso_id):
    """
    Topología del modelo para el caso: id_flujo -> nodo_salida/nodo_entrada (códigos)
    """
    df = pd.read_sql(
        """
        SELECT
            fm.Id_flujo,
            fm.Flujos AS codigo_flujo,
            ns.codigo_nodo AS nodo_salida,
            nl.codigo_nodo AS nodo_entrada,
            ns.nombre_nodo AS nombre_salida,
            nl.nombre_nodo AS nombre_entrada
        FROM inventar_SpcHidr.flujo_modelos fm
        JOIN inventar_SpcHidr.nodos ns ON ns.id_nodo = fm.n_salida
        JOIN inventar_SpcHidr.nodos nl ON nl.id_nodo = fm.n_llegada
        WHERE fm.modelo = 3
          AND fm.activo = 1
        """,
        engine
    )
    return df


# ==============================================================================
# 1) PRECONTROL: DESBALANCE POR NODO DESDE GRILLA ACTIVA
# ==============================================================================
def precontrol_desbalance_nodo_desde_grilla(engine, grid_rows, caso_id):
    """
    PRE-reconciliación.
    - Usa SOLO la grilla activa (rowData) como valores (masa/ley).
    - Usa BD solo para topología (flujo_modelos + nodos).
    Retorna DF por nodo con:
      entradas/salidas (masa, fino Cu), Δ y %.
    """
    if not grid_rows:
        return pd.DataFrame()

    dfg = pd.DataFrame(grid_rows)

    # Requeridos mínimos
    if "id_flujo" not in dfg.columns:
        return pd.DataFrame()

    # Normalización columnas esperadas en tu grilla
    # Masa: en tu grilla se llama "Flujo"
    # Ley:  "Cu" (en %)
    dfg["id_flujo"] = pd.to_numeric(dfg["id_flujo"], errors="coerce")
    dfg["masa"] = pd.to_numeric(dfg.get("Flujo", 0), errors="coerce").fillna(0.0)
    dfg["cu_pct"] = pd.to_numeric(dfg.get("Cu", 0), errors="coerce").fillna(0.0)

    # fino cu
    if "FCu" in dfg.columns:
        dfg["fino_cu"] = pd.to_numeric(dfg["FCu"], errors="coerce")
        dfg["fino_cu"] = dfg["fino_cu"].fillna(dfg["masa"] * dfg["cu_pct"] / 100.0)
    else:
        dfg["fino_cu"] = dfg["masa"] * dfg["cu_pct"] / 100.0

    topo = _get_topologia(engine, caso_id)
    if topo.empty:
        return pd.DataFrame()

    df = dfg.merge(topo, left_on="id_flujo", right_on="Id_flujo", how="inner")
    if df.empty:
        return pd.DataFrame()

    # Movimientos por nodo
    entradas = df[["nombre_entrada", "masa", "fino_cu"]].rename(columns={"nombre_entrada": "nodo"})
    entradas["tipo"] = "ENTRADA"

    salidas = df[["nombre_salida", "masa", "fino_cu"]].rename(columns={"nombre_salida": "nodo"})
    salidas["tipo"] = "SALIDA"

    mov = pd.concat([entradas, salidas], ignore_index=True)

    agg = (
        mov.groupby(["nodo", "tipo"], as_index=False)
        .agg(masa=("masa", "sum"), fino_cu=("fino_cu", "sum"))
    )

    piv = agg.pivot_table(index="nodo", columns="tipo", values=["masa", "fino_cu"], fill_value=0)
    piv.columns = [f"{v}_{k}".lower() for v, k in piv.columns]
    piv = piv.reset_index()

    # Completar columnas si faltan (si nodo solo tiene entrada/salida)
    for c in ["masa_entrada", "masa_salida", "fino_cu_entrada", "fino_cu_salida"]:
        if c not in piv.columns:
            piv[c] = 0.0

    piv["desb_masa"] = piv["masa_entrada"] - piv["masa_salida"]
    piv["desb_fino_cu"] = piv["fino_cu_entrada"] - piv["fino_cu_salida"]

    piv["desb_masa_pct"] = np.where(
        piv["masa_entrada"] != 0, 100 * piv["desb_masa"] / piv["masa_entrada"], 0.0
    )
    piv["desb_cu_pct"] = np.where(
        piv["fino_cu_entrada"] != 0, 100 * piv["desb_fino_cu"] / piv["fino_cu_entrada"], 0.0
    )

    # Redondeos para presentación
    piv = piv.sort_values("nodo")
    piv["masa_entrada"] = piv["masa_entrada"].round(3)
    piv["masa_salida"] = piv["masa_salida"].round(3)
    piv["desb_masa"] = piv["desb_masa"].round(3)
    piv["desb_masa_pct"] = piv["desb_masa_pct"].round(3)

    piv["fino_cu_entrada"] = piv["fino_cu_entrada"].round(4)
    piv["fino_cu_salida"] = piv["fino_cu_salida"].round(4)
    piv["desb_fino_cu"] = piv["desb_fino_cu"].round(4)
    piv["desb_cu_pct"] = piv["desb_cu_pct"].round(3)

    return piv

    # -------------------------
    # Cálculo por nodo
    # -------------------------
    rows = []

    for nodo in pd.unique(df[["n_salida", "n_llegada"]].values.ravel()):
        entradas = df[df["n_llegada"] == nodo]
        salidas  = df[df["n_salida"] == nodo]

        masa_in  = entradas["Masa_medida"].sum()
        masa_out = salidas["Masa_medida"].sum()

        fino_in  = (entradas["Masa_medida"] * entradas["Ley_medida_Cu"] / 100).sum()
        fino_out = (salidas["Masa_medida"] * salidas["Ley_medida_Cu"] / 100).sum()

        rows.append({
            "Nodo": nodo,
            "Entrada_masa": masa_in,
            "Salida_masa": masa_out,
            "Desbalance_masa": masa_in - masa_out,
            "Entrada_fino": fino_in,
            "Salida_fino": fino_out,
            "Desbalance_fino": fino_in - fino_out
        })

    return pd.DataFrame(rows)



def fig_precontrol_nodo(df):
    if df is None or df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=[
            "Entradas vs Salidas por Nodo (Masa)",
            "Desbalances por Nodo (Δ Masa y Δ Fino Cu)"
        ],
        vertical_spacing=0.12
    )

    fig.add_trace(go.Bar(x=df["nodo"], y=df["masa_entrada"], name="Entrada (masa)"), row=1, col=1)
    fig.add_trace(go.Bar(x=df["nodo"], y=df["masa_salida"], name="Salida (masa)"), row=1, col=1)

    fig.add_trace(go.Bar(x=df["nodo"], y=df["desb_masa"], name="Δ Masa"), row=2, col=1)
    fig.add_trace(
        go.Scatter(x=df["nodo"], y=df["desb_fino_cu"], mode="lines+markers", name="Δ Fino Cu"),
        row=2, col=1
    )

    fig.update_layout(
        template="plotly_white",
        height=650,
        barmode="group",
        legend=dict(orientation="h", y=1.12)
    )
    return fig


# ==============================================================================
# 2) HISTÓRICO POR NODO (BOXPLOT) + OVERLAY ACTUAL
# ==============================================================================
def query_hist_desb_nodo(engine, fecha_ini, fecha_fin, var="masa_pct"):
    """
    Obtiene histórico desde inventar_SpcHidr.bm_desbalance_nodo.
    """
    col = {
        "masa_pct": "desb_masa_pct",
        "cu_pct": "desb_cu_pct",
        "masa_abs": "desb_masa_final",
        "cu_abs": "desb_cu_final",
    }.get(var, "desb_masa_pct")

    df = _read_sql(
        engine,
        f"""
        SELECT
            fecha_fin_periodo AS Fecha,
            nombre_nodo       AS Nodo,
            CAST({col} AS FLOAT) AS Valor
        FROM inventar_SpcHidr.bm_desbalance_nodo
        WHERE fecha_fin_periodo BETWEEN :fi AND :ff
        """,
        {"fi": fecha_ini, "ff": fecha_fin},
    )
    return df


def fig_boxplot_hist_nodo(df_hist, df_actual, var_label):
    fig = go.Figure()

    if df_hist is not None and not df_hist.empty:
        for nodo in sorted(df_hist["Nodo"].unique()):
            s = df_hist.loc[df_hist["Nodo"] == nodo, "Valor"]
            fig.add_trace(go.Box(y=s, name=str(nodo), boxpoints=False))

    if df_actual is not None and not df_actual.empty:
        fig.add_trace(
            go.Scatter(
                x=df_actual["nodo"],
                y=df_actual["valor_actual"],
                mode="markers+lines",
                name="Actual (grilla)"
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=520,
        title=f"Histórico por Nodo (Boxplot) + Valor actual (grilla) – {var_label}",
        xaxis_title="Nodo",
        yaxis_title=var_label,
        legend=dict(orientation="h", y=1.12)
    )
    return fig


# ==============================================================================
# 3) HISTÓRICO POR FLUJO (BOXPLOT) + OVERLAY ACTUAL
# ==============================================================================
def query_hist_flujo(engine, fecha_ini, fecha_fin, id_flujo, var="masa"):
    col = {
        "masa": "Masa_recon",
        "cu": "Ley_recon_Cu",
        "fcu": "(Masa_recon*Ley_recon_Cu/100.0)"
    }.get(var, "Masa_recon")

    df = _read_sql(
        engine,
        f"""
        SELECT
            cb.fecha AS Fecha,
            dbr.id_flujo AS id_flujo,
            CAST({col} AS FLOAT) AS Valor
        FROM inventar_SpcHidr.Data_balance_rec dbr
        JOIN inventar_SpcHidr.casos_balance cb
            ON cb.caso_id = dbr.caso_id
        WHERE cb.fecha BETWEEN :fi AND :ff
          AND dbr.id_flujo = :idf
        """,
        {"fi": fecha_ini, "ff": fecha_fin, "idf": int(id_flujo)},
    )
    return df


def fig_boxplot_hist_flujo(df_hist, valor_actual, var_label, flujo_label):
    fig = go.Figure()

    if df_hist is not None and not df_hist.empty:
        fig.add_trace(go.Box(y=df_hist["Valor"], name=f"Histórico ({flujo_label})", boxpoints="outliers"))

    if valor_actual is not None:
        fig.add_trace(
            go.Scatter(
                x=[f"Actual ({flujo_label})"],
                y=[valor_actual],
                mode="markers",
                name="Actual (grilla)"
            )
        )

    fig.update_layout(
        template="plotly_white",
        height=420,
        title=f"Histórico Flujo (Boxplot) + Actual (grilla) – {var_label}",
        yaxis_title=var_label,
        legend=dict(orientation="h", y=1.12)
    )
    return fig


# ==============================================================================
# UI helpers
# ==============================================================================
def _grid_component(id_, columns, rowdata=None, height=260):
    if HAS_AGGRID:
        return dag.AgGrid(
            id=id_,
            columnDefs=columns,
            rowData=rowdata or [],
            defaultColDef={
                "sortable": True,
                "filter": True,
                "resizable": True,
                "floatingFilter": True
            },
            dashGridOptions={
                "pagination": True,
                "paginationPageSize": 25
            },
            style={"height": f"{height}px", "width": "100%"}
        )
    else:
        return dash_table.DataTable(
            id=id_,
            columns=[{"name": c.get("headerName", c["field"]), "id": c["field"]} for c in columns],
            data=rowdata or [],
            page_size=25,
            style_table={"overflowX": "auto", "height": f"{height}px", "overflowY": "auto"},
            style_cell={"fontSize": 12, "padding": "6px", "whiteSpace": "normal"},
        )


COLS_PRE_NODO = [
    {"field": "nodo", "headerName": "Nodo"},
    {"field": "masa_entrada", "headerName": "Masa Entrada"},
    {"field": "masa_salida", "headerName": "Masa Salida"},
    {"field": "desb_masa", "headerName": "Δ Masa"},
    {"field": "desb_masa_pct", "headerName": "% Δ Masa"},
    {"field": "fino_cu_entrada", "headerName": "Fino Cu Entrada"},
    {"field": "fino_cu_salida", "headerName": "Fino Cu Salida"},
    {"field": "desb_fino_cu", "headerName": "Δ Fino Cu"},
    {"field": "desb_cu_pct", "headerName": "% Δ Fino Cu"},
]

COLS_HIST_NODO = [
    {"field": "Fecha", "headerName": "Fecha"},
    {"field": "Nodo", "headerName": "Nodo"},
    {"field": "Valor", "headerName": "Valor"},
]

COLS_HIST_FLUJO = [
    {"field": "Fecha", "headerName": "Fecha"},
    {"field": "id_flujo", "headerName": "id_flujo"},
    {"field": "Valor", "headerName": "Valor"},
]


# ==============================================================================
# LAYOUT TAB 6
# ==============================================================================
layout = html.Div(
    style={"padding": "10px"},
    children=[
        # ----------------------------------------------------------------------
        # SECCIÓN 0: tu UI base (grilla + botones originales)
        # ----------------------------------------------------------------------
        render_tab6_base(),

        # ----------------------------------------------------------------------
        # SECCIÓN 1: PRECONTROL
        # ----------------------------------------------------------------------
        html.Div(
            style={
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "padding": "12px",
                "marginBottom": "12px",
                "background": "white"
            },
            children=[
                html.H4("1) Precontrol: Desbalances iniciales por Nodo (desde grilla activa)"),
                html.Div(
                    style={"display": "flex", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                    children=[
                        html.Button("Graficar desbalances iniciales", id="btn-graf-desb-ini", n_clicks=0),
                        html.Div(id="msg-precontrol", style={"fontSize": "12px", "color": "#374151"})
                    ]
                ),
                html.Div(style={"height": "10px"}),
                dcc.Graph(id="graf-desbalances-ini", figure=go.Figure()),
                html.Div(style={"height": "10px"}),
                html.H5("Resumen numérico por Nodo (Entradas / Salidas / Δ / %)"),
                _grid_component("tabla-precontrol-nodo", COLS_PRE_NODO, [], height=300)
            ]
        ),

        # ----------------------------------------------------------------------
        # SECCIÓN 2: HISTÓRICO POR NODO
        # ----------------------------------------------------------------------
        html.Div(
            style={
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "padding": "12px",
                "marginBottom": "12px",
                "background": "white"
            },
            children=[
                html.H4("2) Histórico por Nodo: Boxplot (BD) + valor actual (grilla)"),
                html.Div(
                    style={"display": "flex", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                    children=[
                        dcc.DatePickerRange(
                            id="hist-fechas",
                            display_format="YYYY-MM-DD",
                            minimum_nights=0
                        ),
                        dcc.Dropdown(
                            id="hist-var",
                            options=[
                                {"label": "% Δ Masa", "value": "masa_pct"},
                                {"label": "% Δ Fino Cu", "value": "cu_pct"},
                                {"label": "Δ Masa (abs)", "value": "masa_abs"},
                                {"label": "Δ Fino Cu (abs)", "value": "cu_abs"},
                            ],
                            value="masa_pct",
                            clearable=False,
                            style={"width": "220px"}
                        ),
                        html.Button("Consultar histórico", id="btn-hist-buscar", n_clicks=0),
                        html.Div(id="msg-hist-nodo", style={"fontSize": "12px", "color": "#374151"})
                    ]
                ),
                html.Div(style={"height": "10px"}),
                dcc.Graph(id="hist-graf", figure=go.Figure()),
                html.Div(style={"height": "10px"}),
                html.H5("Detalle histórico (tabla)"),
                _grid_component("hist-tabla", COLS_HIST_NODO, [], height=260)
            ]
        ),

        # ----------------------------------------------------------------------
        # SECCIÓN 3: HISTÓRICO POR FLUJO
        # ----------------------------------------------------------------------
        html.Div(
            style={
                "border": "1px solid #e5e7eb",
                "borderRadius": "10px",
                "padding": "12px",
                "background": "white"
            },
            children=[
                html.H4("3) Histórico por Flujo: Boxplot (BD) + valor actual (grilla)"),
                html.Div(
                    style={"display": "flex", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                    children=[
                        dcc.DatePickerRange(
                            id="flow-hist-fechas",
                            display_format="YYYY-MM-DD",
                            minimum_nights=0
                        ),
                        dcc.Dropdown(
                            id="flow-hist-var",
                            options=[
                                {"label": "Masa (t)", "value": "masa"},
                                {"label": "Ley Cu (%)", "value": "cu"},
                                {"label": "Fino Cu (tCu)", "value": "fcu"},
                            ],
                            value="masa",
                            clearable=False,
                            style={"width": "200px"}
                        ),
                        dcc.Dropdown(
                            id="flow-hist-flujo",
                            options=[],
                            placeholder="Seleccionar flujo (id_flujo)",
                            style={"width": "260px"}
                        ),
                        html.Button("Consultar histórico flujo", id="btn-flow-hist-buscar", n_clicks=0),
                        html.Div(id="msg-hist-flujo", style={"fontSize": "12px", "color": "#374151"})
                    ]
                ),
                html.Div(style={"height": "10px"}),
                dcc.Graph(id="flow-hist-graf", figure=go.Figure()),
                html.Div(style={"height": "10px"}),
                html.H5("Detalle histórico por flujo (tabla)"),
                _grid_component("flow-hist-tabla", COLS_HIST_FLUJO, [], height=240)
            ]
        ),
    ]
)


# ==============================================================================
# CALLBACKS
# ==============================================================================
def register_callbacks(app):
    # Mantiene TODOS los callbacks y UI previa del tab6_base
    register_tab6_base_callbacks(app)

    # --------------------------------------------------------------------------
    # Init fechas sugeridas (desde caso)
    # --------------------------------------------------------------------------
    @app.callback(
        Output("hist-fechas", "start_date"),
        Output("hist-fechas", "end_date"),
        Output("flow-hist-fechas", "start_date"),
        Output("flow-hist-fechas", "end_date"),
        Input("active-case", "data"),
        prevent_initial_call=False
    )
    def init_fechas(shared):
        caso_id = _get_caso_id(shared)
        if not caso_id or ENGINE is None:
            return None, None, None, None

        fi, ff, _modelo = _get_periodo_caso(ENGINE, caso_id)
        if not ff:
            return None, None, None, None

        start_hist = (pd.to_datetime(ff) - pd.Timedelta(days=30)).date()
        return str(start_hist), str(ff), str(start_hist), str(ff)

    # --------------------------------------------------------------------------
    # Dropdown flujos (según modelo del caso)
    # --------------------------------------------------------------------------
    @app.callback(
        Output("flow-hist-flujo", "options"),
        Input("active-case", "data"),
        prevent_initial_call=False
    )
    def cargar_flujos(shared):
        caso_id = _get_caso_id(shared)
        if not caso_id or ENGINE is None:
            return []

        _fi, _ff, modelo_id = _get_periodo_caso(ENGINE, caso_id)
        topo = _get_topologia(ENGINE, modelo_id)
        if topo.empty:
            return []

        topo = topo.drop_duplicates(subset=["Id_flujo", "codigo_flujo"]).sort_values("Id_flujo")
        return [{"label": f"{int(r.Id_flujo)} – {r.codigo_flujo}", "value": int(r.Id_flujo)}
                for r in topo.itertuples(index=False)]

    # --------------------------------------------------------------------------
    # PRECONTROL: gráfico + tabla
    # --------------------------------------------------------------------------
    @app.callback(
        Output("graf-desbalances-ini", "figure"),
        Output("tabla-precontrol-nodo", "rowData" if HAS_AGGRID else "data"),
        Output("msg-precontrol", "children"),
        Input("btn-graf-desb-ini", "n_clicks"),
        State("recon-data-base", "rowData"),
        State("active-case", "data"),
        prevent_initial_call=True
    )
    def cb_precontrol(n_clicks, grid_rows, shared):
        if not n_clicks:
            raise PreventUpdate

        if ENGINE is None:
            return go.Figure(), [], "❌ No hay conexión a BD (ENGINE=None). Revisa .env / ENTORNO."

        caso_id = _get_caso_id(shared)
        if not caso_id:
            return go.Figure(), [], "⚠️ No hay caso activo."

        if not grid_rows:
            return go.Figure(), [], "⚠️ La grilla no tiene datos cargados."

        _fi, _ff, modelo_id = _get_periodo_caso(ENGINE, caso_id)
        if modelo_id is None:
            return go.Figure(), [], "⚠️ No se pudo obtener el modelo del caso (casos_balance.modelo)."

        df = precontrol_desbalance_nodo_desde_grilla(ENGINE, grid_rows, modelo_id)
        if df.empty:
            return go.Figure(), [], "⚠️ No se pudo calcular desbalances (sin topología o sin match id_flujo)."

        fig = fig_precontrol_nodo(df)
        return fig, df.to_dict("records"), "✅ Precontrol ejecutado correctamente."

    # --------------------------------------------------------------------------
    # HISTÓRICO NODO: boxplot + overlay actual
    # --------------------------------------------------------------------------
    @app.callback(
        Output("hist-graf", "figure"),
        Output("hist-tabla", "rowData" if HAS_AGGRID else "data"),
        Output("msg-hist-nodo", "children"),
        Input("btn-hist-buscar", "n_clicks"),
        State("hist-fechas", "start_date"),
        State("hist-fechas", "end_date"),
        State("hist-var", "value"),
        State("recon-data-base", "rowData"),
        State("active-case", "data"),
        prevent_initial_call=True
    )
    def cb_hist_nodo(n, start_date, end_date, var, grid_rows, shared):
        if not n:
            raise PreventUpdate

        if ENGINE is None:
            return go.Figure(), [], "❌ No hay conexión a BD (ENGINE=None)."

        caso_id = _get_caso_id(shared)
        if not caso_id:
            return go.Figure(), [], "⚠️ No hay caso activo."

        if not start_date or not end_date:
            return go.Figure(), [], "⚠️ Selecciona rango de fechas."

        _fi, _ff, modelo_id = _get_periodo_caso(ENGINE, caso_id)
        if modelo_id is None:
            return go.Figure(), [], "⚠️ No se pudo obtener el modelo del caso."

        # 1) histórico BD
        df_hist = query_hist_desb_nodo(ENGINE, start_date, end_date, var=var)

        # 2) actual desde grilla (precontrol)
        df_pre = precontrol_desbalance_nodo_desde_grilla(ENGINE, grid_rows or [], modelo_id)

        if df_pre.empty:
            df_actual = pd.DataFrame(columns=["nodo", "valor_actual"])
        else:
            col_actual = {
                "masa_pct": "desb_masa_pct",
                "cu_pct": "desb_cu_pct",
                "masa_abs": "desb_masa",
                "cu_abs": "desb_fino_cu",
            }.get(var, "desb_masa_pct")
            df_actual = df_pre[["nodo", col_actual]].rename(columns={col_actual: "valor_actual"})

        label = {
            "masa_pct": "% Δ Masa",
            "cu_pct": "% Δ Fino Cu",
            "masa_abs": "Δ Masa",
            "cu_abs": "Δ Fino Cu",
        }.get(var, "% Δ Masa")

        fig = fig_boxplot_hist_nodo(df_hist, df_actual, label)

        rows = df_hist.sort_values(["Nodo", "Fecha"]).to_dict("records") if not df_hist.empty else []
        msg = f"✅ Histórico nodo: {len(rows)} registros ({start_date} → {end_date})."
        if df_hist.empty:
            msg += " (sin datos en bm_desbalance_nodo para ese periodo)"
        return fig, rows, msg

    # --------------------------------------------------------------------------
    # HISTÓRICO FLUJO: boxplot + overlay actual
    # --------------------------------------------------------------------------
    @app.callback(
        Output("flow-hist-graf", "figure"),
        Output("flow-hist-tabla", "rowData" if HAS_AGGRID else "data"),
        Output("msg-hist-flujo", "children"),
        Input("btn-flow-hist-buscar", "n_clicks"),
        State("flow-hist-fechas", "start_date"),
        State("flow-hist-fechas", "end_date"),
        State("flow-hist-var", "value"),
        State("flow-hist-flujo", "value"),
        State("recon-data-base", "rowData"),
        prevent_initial_call=True
    )
    def cb_hist_flujo(n, start_date, end_date, var, id_flujo, grid_rows):
        if not n:
            raise PreventUpdate

        if ENGINE is None:
            return go.Figure(), [], "❌ No hay conexión a BD (ENGINE=None)."

        if not start_date or not end_date:
            return go.Figure(), [], "⚠️ Selecciona rango de fechas."
        if not id_flujo:
            return go.Figure(), [], "⚠️ Selecciona un flujo."

        df_hist = query_hist_flujo(ENGINE, start_date, end_date, int(id_flujo), var=var)

        # valor actual desde grilla
        df = pd.DataFrame(grid_rows or [])
        valor_actual = None
        if not df.empty and "id_flujo" in df.columns:
            df["id_flujo"] = pd.to_numeric(df["id_flujo"], errors="coerce")
            row = df[df["id_flujo"] == int(id_flujo)]
            if not row.empty:
                masa = _safe_float(row.iloc[0].get("Flujo", 0.0))
                cu = _safe_float(row.iloc[0].get("Cu", 0.0))
                if var == "masa":
                    valor_actual = masa
                elif var == "cu":
                    valor_actual = cu
                else:
                    valor_actual = masa * cu / 100.0

        var_label = {"masa": "Masa (t)", "cu": "Ley Cu (%)", "fcu": "Fino Cu (tCu)"}[var]
        flujo_label = f"id_flujo {id_flujo}"

        fig = fig_boxplot_hist_flujo(df_hist, valor_actual, var_label, flujo_label)

        rows = df_hist.sort_values("Fecha").to_dict("records") if not df_hist.empty else []
        msg = f"✅ Histórico flujo: {len(rows)} registros ({start_date} → {end_date})."
        if df_hist.empty:
            msg += " (sin datos históricos para ese flujo/periodo)"
        if valor_actual is None:
            msg += " | ⚠️ No se encontró valor actual en grilla para ese flujo."
        return fig, rows, msg


# ==============================================================================
# API esperada por tab_recon_container
# ==============================================================================
def render_tab6():
    return layout


def register_tab6_callbacks(app):
    register_callbacks(app)
