from .flujos_balance import ejecutar_balance_flujos, guardar_balance_en_bd
import pandas as pd
import numpy as np
from dash import html, dcc, Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
from dash import  dash_table
import plotly.graph_objs as go
import plotly.express as px
from plotly.graph_objs import Figure
from db_connection import get_connection
from scipy import stats
from datetime import date
import io
import base64
import dash_bootstrap_components as dbc
from dash import Dash
import dash_ag_grid as dag
from tabs.utils_recon import balance_core
from tabs.utils_dash import  get_data_publica_casos, parse_contents
from sqlalchemy import text
from db_connection import get_engine

ENGINE = get_engine()

dict_style_boton_2 = {
        'background': '#C0E48C', 'color': 'black', 'border-color': '#7EB72B',
        'border-radius': '10px',
        'width': '100%',  # '120px'
        'fontSize': 10,
        'height': '40px',
        'textAlign': 'center'
    }
columnsDefs_data_base =  [
        {'field': 'id_flujo', 'maxWidth': 80, 'editable': False},
        {'field': 'codigo_flujo', 'maxWidth': 100, 'editable': False},
        {'field': 'nombre_flujo', 'maxWidth': 350, 'editable': False},
        {'field': 'Flujo', 'maxWidth': 100, 'editable': True},
        {'field': 'Cu', 'maxWidth': 100, 'editable': True},
        {'field': 'FCu', 'maxWidth': 100, 'editable': True},
        {'field': 'Tolerancia', 'maxWidth': 100, 'editable': True},
        {'field': 'Tolerancia_cu', 'maxWidth': 120, 'editable': True},
        ]
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
# === ColumnDefs: Desbalances Históricos ===
columnsDefs_hist_desb = [
    {"headerName": "Fecha", "field": "Fecha"},
    {"headerName": "Área", "field": "Area"},
    {"headerName": "Desbalance masa", "field": "Desb_masa", "type": "rightAligned"},
    {"headerName": "Desbalance fino Cu", "field": "Desb_fino_cu", "type": "rightAligned"},
]
def render_tab6():
    return html.Div([
        html.H3("📈 Reconciliador Area Seca", style={"textAlign": "center"}),

        html.Div([], style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '10px',
            'paddingBottom': '20px',
            'alignItems': 'flex-end'
        }),

        html.Hr(),
        html.H4("Sección 1: Carga Template", style={"textAlign": "left"}),
        html.Div(
            id="kpi-tab6",
            style={"display": "flex", "justifyContent": "space-around", "paddingBottom": "20px"}
        ),

        # ===== Sección 1: Carga Template (2 columnas) =====
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 1: Carga Template", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f8f9fa", "letterSpacing": "0.06em", "textTransform": "uppercase"}
            ),
            dbc.CardBody([
                dbc.Row([
                    # --- Columna izquierda (≈20%) ---
                    dbc.Col([
                        html.H6('Parámetros de entrada (tabla editable)', className="mb-3"),

                        # Opción A: Template Excel
                        dcc.Upload(
                            id='data-base-upload',
                            children=dbc.Button(
                                [html.I(className="bi bi-cloud-arrow-up me-2"), "Cargar Excel Datos Base"],
                                color="primary", outline=True, className="w-100", size="sm"
                            ),
                            className="w-100",
                        ),
                        html.Small("Formatos: .xlsx / .xlsm | Hoja: 'Datos bases'",
                                className="text-muted d-block mt-2"),

                        html.Hr(className="my-3"),

                        # Opción B: Cargar directo desde BD
                        dbc.Button(
                            [html.I(className="bi bi-database-down me-2"), "Cargar desde Base de Datos"],
                            id="btn-cargar-db", n_clicks=0,
                            color="success", className="w-100", size="sm"
                        ),

                        # Mensaje/estado (se actualiza por callback si aplica)
                        html.Div(id="msg-carga-grid", className="small text-muted mt-2"),

                    ], md=2, lg=2, xl=2),

                    # --- Columna derecha (tabla + gráfico en dos columnas) ---
                    dbc.Col([
                        dbc.Row([
                            # Subcolumna: Tabla (reducida y más densa)
                            dbc.Col([
                                html.Label("Datos base de entrada a reconciliador (editable)", className="fw-semibold"),
                                dcc.Loading(
                                    dag.AgGrid(
                                        id="recon-data-base",
                                        columnDefs=columnsDefs_data_base,
                                        className='ag-theme-balham',
                                        style={"height": "500px", "width": "100%"},
                                        defaultColDef={
                                            "sortable": False,
                                            "filter": False,
                                            "resizable": True,
                                            "minWidth": 90,
                                            "suppressHeaderMenuButton": True
                                        },
                                        dashGridOptions={
                                            "rowHeight": 28,
                                            "headerHeight": 28,
                                            "animateRows": False,
                                            "suppressMenuHide": False,
                                            "ensureDomOrder": True,
                                            "alwaysShowHorizontalScroll": False,
                                             "floatingFilter": False 
                                        }
                                    ),
                                    type="default"
                                )
                            ], md=7, lg=7, xl=7),

                            # Subcolumna: Botón + Gráfico desbalances iniciales
                            dbc.Col([
                                dbc.Card([
                                    dbc.CardHeader(
                                        html.Span([html.I(className="bi bi-graph-up me-2"),
                                                "Desbalances iniciales (a partir de la tabla)"]),
                                        className="py-2",
                                        style={"backgroundColor": "#f8f9fa"}
                                    ),
                                    dbc.CardBody([
                                        dbc.Button(
                                            [html.I(className="bi bi-bar-chart-fill me-2"), "Generar gráfico"],
                                            id="btn-graf-desb-ini",
                                            n_clicks=0,
                                            color="success",
                                            className="w-100 mb-2",
                                            size="sm"
                                        ),
                                        dcc.Loading(
                                            dcc.Graph(
                                                id="graf-desbalances-ini",
                                                config={
                                                    "displaylogo": False,
                                                    "responsive": True,
                                                    "modeBarButtonsToRemove": ["zoom", "select", "lasso2d", "toggleSpikelines"]
                                                },
                                                style={"height": "340px", "width": "100%"}
                                            ),
                                            type="default"
                                        )
                                    ], className="pt-2")
                                ], className="h-100 shadow-sm border-0")
                            ], md=5, lg=5, xl=5),
                        ], className="g-3 align-items-start")
                    ], md=10, lg=10, xl=10),
                ], className="g-3 align-items-start")
            ], className="pt-3 pb-2")
        ], className="mb-3 shadow-sm border-0"),
                    # ——————————————————————  SECCIÓN 2: DESBALANCES HISTÓRICOS  ——————————————————————
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 2: Desbalances históricos", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f8f9fa", "letterSpacing": "0.06em", "textTransform": "uppercase"}
            ),
            dbc.CardBody([
                # Filtros
                dbc.Row([
                    dbc.Col([
                        html.Label("Rango de fechas", className="fw-semibold"),
                        dcc.DatePickerRange(
                            id="hist-fechas",
                            clearable=True,
                            minimum_nights=0,
                            display_format="YYYY-MM-DD"
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Áreas", className="fw-semibold"),
                        dcc.Dropdown(
                            id="hist-areas",
                            options=[{"label": a, "value": a} for a in [
                                "N1","Chancado","Silo","N4","N5","Aglomerado","Apilado Sulfuro",
                                "Apilado Óxido","N9","N10"    # ajusta esta lista a tus áreas reales
                            ]],
                            value=[],
                            multi=True,
                            placeholder="(Opcional) Selecciona áreas"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label(" ", className="d-block"),
                        dbc.Button([html.I(className="bi bi-search me-2"), "Buscar"],
                                id="btn-hist-buscar", n_clicks=0, color="secondary", className="w-100")
                    ], md=2),
                ], className="g-3 align-items-end mb-3"),

                # Gráfico + Tabla
                dbc.Row([
                    dbc.Col([
                        dcc.Loading(
                            dcc.Graph(
                                id="hist-graf",
                                config={"displaylogo": False, "responsive": True},
                                style={"height": "360px", "width": "100%"}
                            ),
                            type="default"
                        )
                    ], md=7),
                    dbc.Col([
                        dcc.Loading(
                            dag.AgGrid(
                                id="hist-tabla",
                                columnDefs=columnsDefs_hist_desb,
                                className='ag-theme-balham',
                                style={"height": "360px", "width": "100%"},
                                defaultColDef={"sortable": True, "filter": True, "resizable": True, "minWidth": 90},
                                dashGridOptions={"rowHeight": 28, "headerHeight": 28, "ensureDomOrder": True}
                            ),
                            type="default"
                        )
                    ], md=5),
                ], className="g-3")
            ], className="pt-3 pb-2")
        ], className="mb-3 shadow-sm border-0"),
    ])

def register_tab6_callbacks(app):
    
    # ==============================================================================
    # CALLBACK #1: CARGAR DATOS (La única y correcta versión de cargar_grid)
    # ==============================================================================
    @app.callback(
        Output('recon-data', 'data', allow_duplicate=True),
        Output('msg-carga-grid', 'children'),
        Input('data-base-upload', 'contents'),
        Input('data-base-upload', 'filename'),
        Input('btn-cargar-db', 'n_clicks'),
        State('active-case', 'data'),
        prevent_initial_call=True
    )
    def cargar_grid(contents, filename, n_db, shared):
        trig = ctx.triggered_id

        # ------------------- Excel -------------------
        if trig == 'data-base-upload' and contents:
            try:
                cols = ['id_flujo','codigo_flujo','nombre_flujo','Flujo','Cu','FCu','Tolerancia','Tolerancia_cu']
                df = pd.read_excel(io.BytesIO(base64.b64decode(contents.split(',')[1])), sheet_name='Datos bases')
                rows = df[cols].round(4).to_dict('records')
                msg  = f"✅ Plantilla cargada desde Excel: {filename}"
                return rows, msg
            except Exception as e:
                return [], f"❌ Error cargando Excel: {e}"

        # ------------------- Base de datos -------------------
        if trig == 'btn-cargar-db' and n_db:
            # shared es State('active-case','data')
            if not (shared and 'caso_id' in shared):
                return [], "❌ No hay un caso activo. Carga un caso primero."

            caso_id = shared.get('caso_id')
            with ENGINE.begin() as eng_conn:
                df_caso = pd.read_sql(
                    text("""
                        SELECT fecha_ini AS fi, fecha AS ff
                        FROM inventar_SpcHidr.casos_balance
                        WHERE caso_id = :c AND modelo = 1
                        LIMIT 1
                    """),
                    eng_conn,
                    params={"c": caso_id}
                )

            fi = pd.to_datetime(df_caso['fi'].iat[0]).date()
            ff = pd.to_datetime(df_caso['ff'].iat[0]).date()
            if fi > ff:
                fi, ff = ff, fi

            df_val = ejecutar_balance_flujos(str(fi), str(ff))
            if df_val.empty:
                return [], "⚠️ El script de balance no devolvió filas."
            guardar_balance_en_bd(df_val, caso_id, str(fi), str(ff), ENGINE, truncate=True)

            try:
                with ENGINE.begin() as eng_conn:
                    df_pl = pd.read_sql(
                        text("""
                            SELECT id AS id_flujo, codigo_flujo, nombre_flujo, Tolerancia, Tolerancia_cu
                            FROM inventar_SpcHidr.plantillas_balance
                            WHERE caso_id = :c
                        """),
                        eng_conn,
                        params={"c": caso_id}
                    )
                if df_pl is None or df_pl.empty:
                    raise ValueError("plantilla vacía")
            except Exception:
                orden = [f"F{i}" for i in range(1, 26)]
                df_pl = pd.DataFrame({
                    "id_flujo": list(range(1, 26)),
                    "codigo_flujo": orden,
                    "nombre_flujo": [f"Flujo {i:02d}" for i in range(1, 26)],
                    "Tolerancia": [1.5,1.5,1.5,1.0,2.0,1.0,1.0,0.5,0.5,0.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,0.5,0.5,2.0,1.5,1.5,0.0,0.0,0.5],
                    "Tolerancia_cu": [2.0,2.0,2.0,3.0,3.0,3.0,3.0,3.0,3.0,3.0,0.0,1.0,1.0,1.0,1.0,1.0,1.0,2.0,2.0,2.0,2.0,2.0,0.0,0.0,2.0]
                })

            with ENGINE.begin() as eng_conn:
                df_res = pd.read_sql(
                    text("""
                        SELECT codigo_flujo, Tonelaje AS Flujo, Cu, FCu
                        FROM inventar_SpcHidr.balances_flujos_resultados
                        WHERE caso_id = :c AND fecha_inicio = :fi AND fecha_fin = :ff
                    """),
                    eng_conn,
                    params={"c": caso_id, "fi": fi, "ff": ff}
                )

            df = df_pl.merge(df_res, on="codigo_flujo", how="left")
            for c in ["Flujo", "Cu"]:
                if c not in df:
                    df[c] = 0.0
            df[["Flujo", "Cu"]] = df[["Flujo", "Cu"]].apply(pd.to_numeric, errors="coerce").fillna(0.0)
            if "FCu" not in df.columns or df["FCu"].isna().any():
                df["FCu"] = (df["Flujo"] * df["Cu"] / 100.0).fillna(0.0)

            orden = [f"F{i}" for i in range(1, 26)]
            df["codigo_flujo"] = pd.Categorical(df["codigo_flujo"], categories=orden, ordered=True)
            df = df.sort_values(["codigo_flujo","id_flujo"]).reset_index(drop=True)

            df["Flujo"] = df["Flujo"].round(3)
            df["Cu"]    = df["Cu"].round(4)
            df["FCu"]   = df["FCu"].round(3)

            cols = ["id_flujo","codigo_flujo","nombre_flujo","Flujo","Cu","FCu","Tolerancia","Tolerancia_cu"]
            for col in cols:
                if col not in df:
                    df[col] = 0

            rows = df[cols].to_dict('records')
            msg  = f"✅ Caso {caso_id}: {fi}→{ff} (guardado y cargado desde BD)"
            return rows, msg

        # ------------------- Fallback -------------------
        return no_update, "⚠️ Sin cambios"
    # ==============================================================================
    # CALLBACK #1B: GRAFICAR DESBALANCES INICIALES (a partir de la tabla)
    # ==============================================================================
    @app.callback(
        Output('graf-desbalances-ini', 'figure'),
        Input('btn-graf-desb-ini', 'n_clicks'),
        State('recon-data-base', 'rowData'),
        prevent_initial_call=True
    )
    def graf_desbalances_iniciales(n_clicks, data_base):
        import plotly.express as px
        from plotly.graph_objs import Figure

        if not n_clicks or not data_base:
            return Figure()

        try:
            # 1) Base desde la grilla (misma normalización que en get_recon)
            dfb = pd.DataFrame(data_base)
            dfb['id_flujo'] = pd.to_numeric(dfb.get('id_flujo', np.arange(1, len(dfb)+1)), errors='coerce')
            dfb.sort_values('id_flujo', inplace=True)

            dfb['Flujo'] = pd.to_numeric(dfb.get('Flujo', 0), errors='coerce').fillna(0.0)
            dfb['Cu']    = pd.to_numeric(dfb.get('Cu', 0),    errors='coerce').fillna(0.0)
            dfb['Tolerancia']    = pd.to_numeric(dfb.get('Tolerancia', 0),    errors='coerce').fillna(0.0)
            dfb['Tolerancia_cu'] = pd.to_numeric(dfb.get('Tolerancia_cu', 0), errors='coerce').fillna(0.0)

            mediciones = np.column_stack([
                dfb['Flujo'].to_numpy(dtype=float),
                (dfb['Cu'] / 100.0).to_numpy(dtype=float),
            ])

            eps = 1e-6
            error_df = pd.DataFrame({
                0: (dfb['Tolerancia']    / 100.0).replace(0.0, eps).to_numpy(dtype=float),
                1: (dfb['Tolerancia_cu'] / 100.0).replace(0.0, eps).to_numpy(dtype=float),
            })

            # 2) Llamada a balance_core para obtener desbalances iniciales (sin usar los reconciliados)
            _, _, des_ini = balance_core(mediciones, error=error_df, fn="Normal")

            # 3) Formateo y gráfico
            des_ini = des_ini.rename(columns={0: 'Area'})
            # Aseguramos nombres consistentes: masa y fino iniciales
            # Si tus columnas son 'Desbalance masa' y 'Desbalance fino Cu', se renombra para claridad
            if 'Desbalance masa' in des_ini.columns:
                des_ini = des_ini.rename(columns={'Desbalance masa': 'Desbalance masa inicial'})
            if 'Desbalance fino Cu' in des_ini.columns:
                des_ini = des_ini.rename(columns={'Desbalance fino Cu': 'Desbalance fino inicial Cu'})

            # Construcción de un DF "largo" para barras agrupadas
            cols_y = []
            if 'Desbalance masa inicial' in des_ini.columns:
                cols_y.append('Desbalance masa inicial')
            if 'Desbalance fino inicial Cu' in des_ini.columns:
                cols_y.append('Desbalance fino inicial Cu')
            if not cols_y:
                # Fallback por si los nombres originales no estaban
                posibles = [c for c in des_ini.columns if 'Desbalance' in c]
                cols_y = posibles[:2] if posibles else []

            df_long = des_ini.melt(id_vars='Area', value_vars=cols_y, var_name='Tipo', value_name='Desbalance')

            fig = px.bar(
                df_long,
                x='Area', y='Desbalance', color='Tipo',
                barmode='group',
                title='Desbalances iniciales por área'
            )
            fig.update_layout(
                legend_title_text='Magnitud',
                xaxis_title='Área',
                yaxis_title='Desbalance',
                bargap=0.25
            )
            fig.update_xaxes(type='category', categoryorder='category ascending')
            return fig

        except Exception as e:
            print(f"❌ Error al graficar desbalances iniciales: {e}")
            return Figure()
        # ==============================================================================
    # CALLBACK: Espeja la grilla de entrada al Store compartido (recon-data)
    # ==============================================================================
    @app.callback(
        Output("recon-data", "data", allow_duplicate=True),
        Input("recon-data-base", "rowData"),
        Input("recon-data-base", "cellValueChanged"),
        State("recon-data-base", "rowData"),
        prevent_initial_call=True           # <— antes estaba False y pisaba el Store con []
    )
    def sync_grid_to_store(rowdata_init, cell_event, rowdata_state):
        trigger = ctx.triggered_id
        if trigger == "recon-data-base.rowData":            # carga/recarga real
            return rowdata_init or []
        if trigger == "recon-data-base.cellValueChanged":   # edición de celda
            return rowdata_state or []
        return no_update
    # ==============================================================================
    # CALLBACK: Consultar y mostrar Desbalances Históricos
    # ==============================================================================
    @app.callback(
        Output("hist-graf", "figure"),
        Output("hist-tabla", "rowData"),
        Input("btn-hist-buscar", "n_clicks"),
        State("hist-fechas", "start_date"),
        State("hist-fechas", "end_date"),
        State("hist-areas", "value"),
        prevent_initial_call=True
    )
    def cargar_desbalances_historicos(n_clicks, f_ini, f_fin, areas):
        if not n_clicks:
            return Figure(), []
        if not (f_ini and f_fin):
            return Figure(), []

        try:
            data = [
                {"Fecha": "2025-01-01", "Area": "Chancado", "Desb_masa": 1000, "Desb_fino_cu": 50},
                {"Fecha": "2025-01-02", "Area": "Silo",      "Desb_masa": -500,  "Desb_fino_cu": -20},
            ]
            df = pd.DataFrame(data)
            if areas:
                df = df[df["Area"].isin(areas)]

            df_fecha = df.groupby("Fecha", as_index=False)[["Desb_masa", "Desb_fino_cu"]].sum()
            df_long  = df_fecha.melt(id_vars="Fecha", value_vars=["Desb_masa", "Desb_fino_cu"],
                                    var_name="Magnitud", value_name="Valor")

            fig = px.line(df_long, x="Fecha", y="Valor", color="Magnitud",
                        title="Desbalances históricos (suma por fecha)")
            fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=48, b=10))

            return fig, df.to_dict("records")

        except Exception as e:
            print(f"❌ Error al cargar desbalances históricos: {e}")
            return Figure(), []
    # ==============================================================================
    # CALLBACK: Al volver a la pestaña "2 Reconciliar", reponer la grilla desde el Store
    # ==============================================================================
    @app.callback(
        Output("recon-data-base", "rowData", allow_duplicate=True),
        Input("recon-subtabs", "active_tab"),
        Input("recon-data", "data"),
        State("recon-data-base", "rowData"),
        prevent_initial_call=True
    )
    def hydrate_grid(active_tab, store_data, current_grid):
        objetivos = {"recon-6", "tab-2-reconciliar", "reconciliar", "tab2"}  # ajusta a tu value real
        # 1) Si estamos en otra pestaña, solo hidratamos si hay cambio en el Store
        if ctx.triggered_id == "recon-subtabs" and active_tab not in objetivos:
            return no_update
        # 2) Si la grilla ya tiene filas y el Store no cambió, evita sobreescribir
        if ctx.triggered_id == "recon-subtabs" and current_grid:
            return no_update
        # 3) Caso general: poblar con lo que haya en el Store
        return store_data or []