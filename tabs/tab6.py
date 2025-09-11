import pandas as pd
import numpy as np
from dash import html, dcc, Input, Output, State, callback
from dash import  dash_table
import plotly.graph_objs as go
import plotly.express as px
from db_connection import get_connection
from scipy import stats
from dash import ctx
from datetime import date
import io
import base64
import dash_bootstrap_components as dbc
from dash import Dash
import dash_ag_grid as dag
from tabs.utils_recon import balance_core
from tabs.utils_dash import  get_data_publica_casos, parse_contents

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

def render_tab6():
        return html.Div([
            html.H3("📈 Reconciliador Area Seca", style={"textAlign": "center"}),

            html.Div([
                

               
            ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '10px', 'paddingBottom': '20px', 'alignItems': 'flex-end'}),

            html.Hr(),
            html.H4("Sección 1: Carga Template", style={"textAlign": "left"}),
            html.Div(id="kpi-tab6", style={"display": "flex", "justifyContent": "space-around", "paddingBottom": "20px"}),
            # ===== Sección 1: Carga Template (2 columnas) =====
            dbc.Card([
                dbc.CardHeader(html.H5("Sección 1: Carga Template", className="mb-0")),
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
                                    color="primary", outline=True, className="w-100"
                                ),
                                className="w-100",
                            ),
                            html.Small("Formatos: .xlsx / .xlsm | Hoja: 'Datos bases'", className="text-muted d-block mt-2"),

                            html.Hr(className="my-3"),

                            # Opción B: Cargar directo desde BD
                            dbc.Button(
                                [html.I(className="bi bi-database-down me-2"), "Cargar desde Base de Datos"],
                                id="btn-cargar-db", n_clicks=0,
                                color="secondary", className="w-100"
                            ),
                            html.Small(
                                "Usa el caso activo o parámetros por defecto.",
                                className="text-muted d-block mt-2"
                            ),

                            html.Div(id="msg-carga-grid", className="small text-muted mt-2"),  # mensajes de carga
                        ], md=2, lg=2, xl=2),

                        # --- Columna derecha (≈80%) ---
                        dbc.Col([
                            html.Label("Datos base de entrada a reconciliador (editable)", className="fw-semibold"),
                            dcc.Loading(
                                dag.AgGrid(
                                    id="recon-data-base",
                                    columnDefs=columnsDefs_data_base,
                                    className='ag-theme-balham',
                                    style={"height": "470px", "width": "100%"},
                                ),
                                type="default"
                            )
                        ], md=10, lg=10, xl=10),
                    ], className="g-3 align-items-start"),
                ])
            ], className="mb-4 shadow-sm border-0"),


            html.Hr(),
            html.Br(),
            html.Div(className="w-100"),                # fuerza bloque de ancho completo
            html.Hr(className="my-4"),                  # separador visible
            html.H4("Sección 2: Reconciliador", className="mb-3"),
            html.Div([
        
                    html.Br(),

                    dbc.Row([  # start row Labels
                        dbc.Col([
                            html.H5('Ejecutar reconciliador y revisión de resultados'),
                        ], width={"size": 6, "offset": 0}),
                    ]),

                    html.Br(),

                    dbc.Row([  # start row Labels
                        dbc.Col([
                            dbc.Button('Ejecutar', id='btn-recon', n_clicks=0, style=dict_style_boton_2),
                            html.Label(id='btn-recon-msg', children=' ', style={'font-size': 12}),
                        ], width={"size": 2, "offset": 1}),
                    ]),

                    html.Br(),

                    dbc.Row([  # start row Labels
                        dbc.Col([
                            dag.AgGrid(
                                id="recon-resultados",
                                columnDefs = columnsDefs_resultados,
                                className = 'ag-theme-balham',
                                csvExportParams={"fileName": "resultados_reconciliados.csv"},
                                #style={"height": "470px", "width": "100%"}
                            )
                        ],  width={"size": 10, "offset": 0}),
                       
                        dbc.Col([
                                dbc.Button('Publicar Datos', id='btn-publica-casos', n_clicks=0, style=dict_style_boton_2),
                                html.Label(id='btn-pub-msg_caso', children=' ', style={'font-size': 12}),
                            ], width={"size": 2, "offset": 0}),
                    ]),

                    html.Br(),

                    dbc.Row([  # start row Labels
                        dbc.Col([
                            dag.AgGrid(
                                id="recon-desbalances",
                                columnDefs = columnsDefs_desbalances,
                                className = 'ag-theme-balham',
                                #style={"height": "470px", "width": "100%"}
                            )
                        ],  width={"size": 10, "offset": 0}),
                        html.Br(),
                        dbc.Col([
                            dbc.Button('Descargar ', id='btn-recon-csv', n_clicks=0, style=dict_style_boton_2),
                        ],  width={"size": 2, "offset": 0}),
                        dcc.Download(id="descargar-excel"),
                        html.Br(),
                        
                    ]),

                    html.Br(),
                    ]),

            ],  className="pt-3"), # Esta es la línea que marca el final del Div principal

        

       

def register_tab6_callbacks(app):
    
    
    @app.callback(
        Output('recon-resultados', 'rowData'),
        Output('recon-desbalances','rowData'),
        Input('btn-recon', 'n_clicks'),
        Input('recon-data-base','rowData'),
        #Input('recon-tolerancias', 'rowData'),
        #Input('recon-elementos','value'), 
        #prevent_initial_call=True,
    )
    def get_recon(n_clicks, data_base):

        #print(componentes)

        if data_base is not None  and ctx.triggered_id == 'btn-recon':
            # print('#####################')
            # print(type(componentes))
            #print(data_base)

            #componentes = ['Cu', 'Mo'] #Lista obtenida por pantalla de selección de items en Dash
            lista_rows = []
            lista_columns = []
            lista_data = []

            #mediciones = pd.read_excel(path, sheet_name="Datos bases", skiprows=0).iloc[0:39,:]
            df_mediciones_all = pd.DataFrame(data_base).sort_values('id_flujo').iloc[0:25,:] 
            #print(df_mediciones_all)
            error = pd.DataFrame(df_mediciones_all[['Tolerancia', 'Tolerancia_cu']]).astype(float)/100 
            #print(error)
            df_mediciones_all['id_flujo'] = pd.to_numeric( df_mediciones_all['id_flujo'], errors='coerce' )
            df_mediciones_all.sort_values('id_flujo', inplace=True)
            #print(df_mediciones_all)
            #columnas_componentes = ['FLujo']
            #print(columnas_componentes)
            #mediciones= pd.DataFrame(data_base).sort_values('id_flujo').iloc[:,3:4].to_numpy()
            #print(mediciones)
            df = pd.DataFrame(data_base).sort_values('id_flujo')
            df['Cu'] = df[['Cu']].astype(float)/100 
            mediciones = df[['Flujo', 'Cu']].to_numpy()


            #Ejecutar Reconciliador
            resultados, des_recon,des_ini = balance_core(mediciones,error)
        
            des_ini.rename(columns={0:'Area', 'Desbalance masa':'Desbalance masa_Ini'}, inplace=True)
            des_recon.rename(columns={0:'Area'}, inplace=True)
            df_des = des_ini.merge(des_recon, how='left', on='Area') 
            

            #Consolidar resultado con datos iniciales para comparar
            df_mediciones_all.rename(columns={'Flujo':'Masa Medida','nombre_flujo':'Flujo', 'codigo_flujo':'Codigo'  }, inplace=True)
            
            #out_cols_1 = [f'Ley {elemento} Medida' for elemento in componentes]
            #out_cols_2 = [f'Ley {elemento} recon'  for elemento in componentes]

            df_out = resultados.merge(df_mediciones_all, how='left', on='Flujo')
            #print(df_out)
            #df_out = df_out[['Codigo','Flujo', 'Masa Medida', 'Masa recon','Tolerancia']]

            #df_out['Diferencia'] = df_out['Masa Medida']-df_out['Masa recon']
            #df_out['Porcentaje Ajuste'] = df_out['Diferencia']/df_out['Masa Medida']*100



            #print(df_out.head())

            return df_out.round(4).to_dict('records'), df_des.round(4).to_dict('records')
        
        else:
            return [] , []

    @app.callback(
        Output("descargar-excel", "data"),
        Input("btn-recon-csv", "n_clicks"),
        State("recon-resultados", "rowData"),
        prevent_initial_call=True
    )
    def generar_excel(n_clicks, rec_caso):
        if not rec_caso:
            print("⚠️ No hay datos en rowData")
            return False

        df_rec = pd.DataFrame(rec_caso)
        print("📥 Generando Excel...")

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df_rec.to_excel(writer, index=False, sheet_name="Datos")
        buffer.seek(0)

        return dcc.send_bytes(buffer.read(), filename="reconciliacion.xlsx")
    """ @callback(
        Output("recon-resultados", "exportDataAsExcel"),
        Input("btn-recon-csv", "n_clicks"),
    )
    def export_data_as_csv(n_clicks):
        if n_clicks:
            print('Presione boton y retorne True')
            return True
        return False """

    @app.callback(
        Output("recon-desbalances", "exportDataAsCsv"),
        Input("btn-desbal-csv", "n_clicks"),
        prevent_initial_call=True
    )
    def export_data_as_csv(n_clicks):
        print('Exportando nodos')
        if n_clicks:
            print('Presione boton y retorne True')
            return True
        return False
    @app.callback(
        Output('recon-data-base', 'rowData'),
        Output('msg-carga-grid', 'children'),
        Input('data-base-upload', 'contents'),
        Input('data-base-upload', 'filename'),
        Input('btn-cargar-db', 'n_clicks'),
        State('recon-shared', 'data'),           # opcional: caso_id compartido entre subtabs
        prevent_initial_call=True
    )
    def cargar_grid(contents, filename, n_db, shared):
        trig = ctx.triggered_id
        try:
            # === Opción A: desde Template Excel ===
            if trig == 'data-base-upload' and contents:
                content_type, content_string = contents.split(',')
                decoded = base64.b64decode(content_string)
                df = pd.read_excel(io.BytesIO(decoded), sheet_name='Datos bases')

                # Asegura columnas mínimas requeridas por tu grid
                cols = ['id_flujo','codigo_flujo','nombre_flujo','Flujo','Cu','FCu','Tolerancia','Tolerancia_cu']
                faltantes = [c for c in cols if c not in df.columns]
                if faltantes:
                    return [], f"❌ Faltan columnas en el Excel: {faltantes}"

                return df[cols].round(4).to_dict('records'), f"✅ Template cargado: {filename}"

            # === Opción B: desde Base de Datos ===
            if trig == 'btn-cargar-db' and n_db:
                caso_id = (shared or {}).get("caso_id")  # puede ser None
                df_db = _fetch_grid_from_db(caso_id)     # función helper abajo

                if df_db is None or df_db.empty:
                    return [], "⚠️ Sin datos desde BD (revisa filtros/consultas)."

                # Ordena y asegura columnas
                cols = ['id_flujo','codigo_flujo','nombre_flujo','Flujo','Cu','FCu','Tolerancia','Tolerancia_cu']
                df_db = df_db.reindex(columns=cols)
                return df_db.round(4).to_dict('records'), f"✅ Datos cargados desde BD (caso_id={caso_id})"

            # Nada que hacer
            return dash.no_update, dash.no_update

        except Exception as e:
            return [], f"❌ Error cargando datos: {e}"
    @app.callback(
        Output('btn-pub-msg_caso', 'children'),
        Input('btn-publica-casos', 'n_clicks'),       # único Input
        State('recon-data-base', 'rowData'),
        State('recon-resultados', 'rowData'),
        State('recon-shared', 'data'),
        prevent_initial_call=True
    )
    def get_publica_casos(n_clicks, med_cas, rec_caso, shared):
        if not n_clicks:
            return no_update
        try:
            nrows = get_data_publica_casos(med_cas, rec_caso, shared)
            return f"✅ Publicado correctamente ({nrows} filas)."
        except Exception as e:
            return f"❌ Error al publicar: {e}"  

