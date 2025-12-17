from .flujos_balance import ejecutar_balance_flujos, guardar_balance_en_bd
import pandas as pd
import numpy as np
from dash import html, dcc, Input, Output, State, callback, ctx, no_update
from dash.exceptions import PreventUpdate
from dash import  dash_table
import plotly.graph_objs as go
import plotly.express as px
from plotly.graph_objs import Figure
from db_connection import get_connection,get_engine
from scipy import stats
from datetime import date
import io
import base64
import dash_bootstrap_components as dbc
from dash import Dash
import dash_ag_grid as dag
from tabs.utils_recon import balance_core, desbalances
from tabs.utils_dash import  get_data_publica_casos, parse_contents
from sqlalchemy import  create_engine, text
from db_connection import get_connection, get_engine

#ENGINE = create_engine("pyodbc + ODBC 18://sa:24gegepeNA@149.50.136.234:1433/inventar_SpcHidr")
conn = get_engine()
dict_style_boton_2 = {
        'background': '#C0E48C', 'color': 'black', 'border-color': '#7EB72B',
        'border-radius': '10px',
        'width': '100%',  # '120px'
        'fontSize': 10,
        'height': '40px',
        'textAlign': 'center'
    }
columnsDefs_data_base =  [
        {'field': 'id_flujo', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'codigo_flujo', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'nombre_flujo', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'Flujo', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'Cu', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'FCu', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'Tolerancia', 'type': 'numericColumn', 'editable': True, 'flex': 1},
        {'field': 'Tolerancia_cu', 'type': 'numericColumn', 'editable': True, 'flex': 1},
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
        html.H4("📈 Reconciliador Area Seca", style={"textAlign": "center"}),

        html.Div([], style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'gap': '10px',
            'paddingBottom': '20px',
            'alignItems': 'flex-end'
        }),

        html.Hr(),
        
        # —————————————————————— SECCIÓN 1: CARGA Y SIMULACIÓN ——————————————————————
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 1: Carga y Cálculo de Desbalances", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#f8f9fa", "textTransform": "uppercase"}
            ),
            dbc.CardBody([
                dbc.Row([
                    # Columna Izquierda: Botones
                    dbc.Col([
                        html.H6('1. Cargar Datos', className="mb-3 fw-bold"),
                        dcc.Upload(
                            id='data-base-upload',
                            children=dbc.Button(
                                [html.I(className="bi bi-cloud-arrow-up me-2"), "Cargar Excel"],
                                color="primary", outline=True, className="w-100 mb-2", size="sm"
                            ),
                            className="w-100",
                        ),
                        dbc.Button(
                            [html.I(className="bi bi-database-down me-2"), "Cargar desde Base de Datos"],
                            id="btn-cargar-db", n_clicks=0,
                            color="success", className="w-100", size="sm"
                        ),
                        html.Div(id="msg-carga-grid", className="small text-muted mt-2"),
                    ], md=2),

                    # Columna Derecha: Tabla Editable
                    dbc.Col([
                        html.Label("2. Datos medidos", className="fw-semibold"),
                        dcc.Loading(
                            dag.AgGrid(
                                id="recon-data-base",
                                columnSize="autoSize",
                                columnDefs=columnsDefs_data_base,
                                className='ag-theme-balham',
                                style={"height": "400px", "width": "100%"},
                                defaultColDef={
                                    "resizable": True,
                                    "minWidth": 120,
                                    "cellStyle": {
                                        "fontSize": "14px",
                                        "textAlign": "right"
                                    },
                                    "headerClass": "ag-header-center"
                                },
                                dashGridOptions={
                                    "rowHeight": 36,
                                    "headerHeight": 36,
                                    "domLayout": "normal"
                                }
                            ),
                            type="default"
                        )
                    ], md=10),
                ], className="mb-4"),

                # Fila inferior: Gráfico de resultados inmediatos
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("3. Desbalances iniciales"),
                            dbc.CardBody([
                                dbc.Button(
                                    [html.I(className="bi bi-save me-2"), "Calcular desbalances iniciales"],
                                    id="btn-graf-desb-ini",
                                    n_clicks=0,
                                    color="danger", # Color rojo/naranja para destacar la acción
                                    className="mb-3"
                                ),
                                dcc.Loading(
                                    dcc.Graph(
                                        id="graf-desbalances-ini",
                                        style={"height": "500px", "width": "100%"} # Gráfico alto
                                    ),
                                    type="default"
                                )
                            ])
                        ])
                    ], width=12)
                ])
            ], className="pt-3 pb-2")
        ], className="mb-4 shadow-sm border-0"),

        # —————————————————————— SECCIÓN 2: HISTÓRICO (MODIFICADA) ——————————————————————
        dbc.Card([
            dbc.CardHeader(
                html.H6("Sección 2: Desbalances Históricos (Base de Datos)", className="mb-0"),
                className="py-2",
                style={"backgroundColor": "#e9ecef", "textTransform": "uppercase"} # Color diferente para distinguir
            ),
            dbc.CardBody([
                # 1. Filtros de Búsqueda
                dbc.Row([
                    dbc.Col([
                        html.Label("Rango de fechas", className="fw-semibold"),
                        dcc.DatePickerRange(id="hist-fechas", display_format="YYYY-MM-DD", clearable=True)
                    ], md=4),
                    dbc.Col([
                        html.Label("Áreas", className="fw-semibold"),
                        dcc.Dropdown(
                            id="hist-areas",
                            options=[{"label": a, "value": a} for a in ["N1","Chancado","Silo","N4","N5","Aglomerado","Apilado Sulfuro","Apilado Óxido","N9","N10"]],
                            multi=True, placeholder="Todas las áreas"
                        )
                    ], md=6),
                    dbc.Col([
                        html.Label(" ", className="d-block"),
                        dbc.Button([html.I(className="bi bi-search me-2"), "Buscar en Historial"],
                                id="btn-hist-buscar", n_clicks=0, color="dark", className="w-100")
                    ], md=2),
                ], className="mb-4 align-items-end"),

                # 2. Visualización Gráfica (Fila Completa)
                dbc.Row([
                    dbc.Col([
                        html.H5("Evolución Gráfica", className="text-muted"),
                        html.Hr(),
                        dcc.Loading(
                            dcc.Graph(
                                id="hist-graf",
                                config={"displaylogo": False},
                                style={"height": "450px", "width": "100%"} # Ancho completo
                            )
                        )
                    ], width=12)
                ], className="mb-5"), # Margen grande abajo

                # 3. Visualización Tabla (Fila Completa Abajo)
                dbc.Row([
                    dbc.Col([
                        html.H5("Detalle Numérico (Tabla)", className="text-muted"),
                        html.Hr(),
                        dcc.Loading(
                            dag.AgGrid(
                                id="hist-tabla",
                                columnDefs=columnsDefs_hist_desb,
                                className='ag-theme-balham',
                                style={"height": "400px", "width": "100%"}, # Tabla ancha y alta
                                defaultColDef={"sortable": True, "filter": True, "resizable": True},
                                dashGridOptions={"rowHeight": 28}
                            )
                        )
                    ], width=12)
                ])

            ])
        ], className="mb-5 shadow-sm border-0"),
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
            with conn.begin() as eng_conn:
                df_caso = pd.read_sql(
                    text("""
                        SELECT TOP 1 fecha_ini AS fi, fecha AS ff
                        FROM inventar_SpcHidr.casos_balance
                        WHERE caso_id = :c AND modelo = 1
                    """),
                    eng_conn,
                    params={"c": caso_id}
                )
            print("Consulta SQL ejecutada correctamente.")
            fi = pd.to_datetime(df_caso['fi'].iat[0]).date()
            ff = pd.to_datetime(df_caso['ff'].iat[0]).date()
            if fi > ff:
                fi, ff = ff, fi

            df_val = ejecutar_balance_flujos(str(fi), str(ff))
            if df_val.empty:
                return [], "⚠️ El script de balance no devolvió filas."
            guardar_balance_en_bd(df_val, caso_id, str(fi), str(ff), conn, truncate=True)

            try:
                with conn.begin() as eng_conn:
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
                    "Tolerancia": [0.5,0.5,0.5,6.6,0.0,7.0,7.0,9.0,9.0,0.0,0.0,4.0,4.0,4.0,4.0,0.0,0.0,5.0,5.0,8.0,5.0,5.0,0.0,0.0,1.0],
                    "Tolerancia_cu": [4.95,5.4,5.0,5.0,0.0,7.0,7.0,5.0,5.0,0.0,0.0,0.5,0.5,5.8,5.8,0.0,0.0,0.0,0.0,6.0,0.0,0.0,0.0,0.0,1.0]
                })

            with conn.begin() as eng_conn:
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
        from plotly.subplots import make_subplots


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
            _, des_df, des_ini = desbalances(mediciones, error=error_df, fn="Normal")
            des_ini = des_df
            # 3) Formateo y gráfico
            des_ini = des_ini.rename(columns={0: 'Nodo'})
            #values_to_select = ['Chancado', 'Silo','N9',"N10"]
            #des_ini = des_ini.loc[des_ini['Nodo'].isin(values_to_select)]

            # Aseguramos nombres consistentes: masa y fino iniciales
            # Si tus columnas son 'Desbalance masa' y 'Desbalance fino Cu', se renombra para claridad
            if 'Desbalance masa inicial' in des_ini.columns:
                des_ini = des_ini.rename(columns={'Desbalance masa': 'Desbalance masa inicial'})
            if 'Desbalance fino inicial Cu' in des_ini.columns:
                des_ini = des_ini.rename(columns={'Desbalance fino Cu': 'Desbalance fino inicial Cu'})
      
            
            fig = make_subplots(rows=2, cols=1)
            df_long = des_ini.melt(id_vars='Nodo', value_vars='Desbalance masa inicial', value_name='Desbalance [Ton]')
            fig.add_trace(go.Bar(
                x=df_long['Nodo'], y=df_long['Desbalance [Ton]'],name="Masa"
            ), row=1, col=1)
      
            df_long = des_ini.melt(id_vars='Nodo', value_vars='Desbalance fino inicial Cu', value_name='Desbalance [Ton]')
            fig.add_trace(go.Bar(
                x=df_long['Nodo'], y=df_long['Desbalance [Ton]'],name="Fino"
            ), row=2, col=1)
       
            fig.update_layout(barmode='stack')

            return fig

        except Exception as e:
            print(f"❌ Error al graficar desbalances iniciales: {e}")
            return Figure()
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
        with conn.begin() as eng_conn:
            df = pd.read_sql(
                text("""
                    SELECT
                        fecha_fin   AS Fecha,
                        area        AS Area,
                        desb_masa   AS Desb_masa,
                        desb_fino_cu AS Desb_fino_cu
                    FROM inventar_SpcHidr.historial_desbalances
                    WHERE fecha_fin BETWEEN :f_ini AND :f_fin
                """),
                eng_conn,
                params={"f_ini": f_ini, "f_fin": f_fin}
            )

        if df.empty:
            return Figure(), []

        if areas:
            df = df[df["Area"].isin(areas)]

        df_fecha = df.groupby("Fecha", as_index=False)[["Desb_masa", "Desb_fino_cu"]].sum()
        df_long = df_fecha.melt(
            id_vars="Fecha",
            value_vars=["Desb_masa", "Desb_fino_cu"],
            var_name="Magnitud",
            value_name="Valor"
        )

        fig = px.line(
            df_long,
            x="Fecha",
            y="Valor",
            color="Magnitud",
            title="Desbalances históricos (suma por fecha)"
        )

        fig.update_layout(template="plotly_white")

        return fig, df.to_dict("records")
    
    @app.callback(
    Output('recon-data', 'data', allow_duplicate=True),
    Input('recon-data-base', 'cellValueChanged'), # <- ÚNICO INPUT
    State('recon-data-base', 'rowData'),
    prevent_initial_call=True
    )
    def guardar_ediciones_en_memoria(celda_editada, todos_los_datos): # <- SOLO DOS ARGUMENTOS
        """
        Este callback se activa después de editar una celda.
        Toma todos los datos de la tabla y los guarda en la memoria.
        """
        # El primer argumento 'celda_editada' no lo usamos, pero es necesario para que el Input funcione.
        # El segundo argumento 'todos_los_datos' es el que nos interesa.
        return todos_los_datos

    # CALLBACK B: Rellena la tabla con los datos que hay en la memoria
    @app.callback(
        Output('recon-data-base', 'rowData'),
        Input('recon-data', 'data')
    )
    def actualizar_tabla_desde_memoria(datos_en_memoria):
        """
        Este callback se asegura de que la tabla visible (recon-data-base)
        siempre muestre lo que está guardado en la memoria ('recon-data').
        Si navegas a otra pestaña y vuelves, este callback restaura tus datos editados.
        """
        if datos_en_memoria is None:
            # Evita que la tabla se borre innecesariamente en la carga inicial
            raise PreventUpdate
        return datos_en_memoria