import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_ag_grid as dag
import plotly.graph_objs as go
import os
import pandas as pd
import datetime
import string 
from tabs.utilsHidro.utils_dash import get_nombre_app_hidro, local_img_to_html_hidro
import cv2
import matplotlib.pyplot as plt
import numpy as np

def create_alphabet_list(n):
    # Using slicing to get the first `n` letters of the alphabet
    return list(string.ascii_uppercase[:n])


def render_layout_hidro():
    project_folder = os.path.dirname(os.path.realpath(__file__))  # path de este archivo
    assets_folder = os.path.join(project_folder, 'assets')

    nombre_app = get_nombre_app_hidro()

    date_now = datetime.datetime.now().replace(minute=0, second=0)
    fecha = date_now.strftime('%Y-%m-%d %H:%M')

    spc_colores = {
        'Cobre': ['#FF9040', '#411720', '#C7410B', '#FFBC8C', '#FFE9D9'],
        # Rojo oscuro, Cobre, Naranja, naranja claro, rosado
        'Zinc': ['#001040', '#3B536A', '#00A269', '#00DBB7', '#AAE5E3']  # Azul , Azul plomo, verde, verde agua, celeste
    }

    dict_style_boton = {
        'background': spc_colores['Zinc'][1],
        'color': 'withe',
        'border-color': spc_colores['Zinc'][0],
        'border-radius': '10px',
        'width': '100%',  # '120px'
        'fontSize': 13,
        'height': '40px',
        'textAlign': 'center'
    }

    dict_style_boton_2 = {
        'background': '#C0E48C', 'color': 'black', 'border-color': '#7EB72B',
        'border-radius': '10px',
        'width': '100%',  # '120px'
        'fontSize': 10,
        'height': '40px',
        'textAlign': 'center'
    }

    #Fecha	Payload	Camiones_TMS	Camiones_Cu fino_Ley Mina	Camiones_Mo fino_Ley Mina	Camiones_Fe fino_Ley Mina	
    #Camiones_Cu%_MinaP11	Camiones_Mo%_MinaP11	Camiones_Fe%_MinaP11
    columnsDefs_mina = [
        {'field': 'Fecha'},
        {'field': 'Payload'},
        {'field': 'Camiones_TMS'},
        {'filed': 'Camiones_Cu fino_Ley Mina'},
        {'filed': 'Camiones_Mo fino_Ley Mina'}
    ]

    columnsDefs_data_tag =  [
        {'field': 'Fini', 'maxWidth': 230, 'editable': True},
        {'field': 'Fend', 'maxWidth': 130, 'editable': True},
        {'field': 'FIT_61209', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_61206', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT25104', 'maxWidth': 100, 'editable': True},
        {'field': 'WI_01769', 'maxWidth': 100, 'editable': True},
        {'field': 'WI_01769_DACA', 'maxWidth': 100, 'editable': True},
        {'field': 'LI_12655A', 'maxWidth': 100, 'editable': True},
        {'field': 'LI_12655B', 'maxWidth': 100, 'editable': True},
        {'field': 'LI_06730A', 'maxWidth': 100, 'editable': True},
        {'field': 'LI_06730B', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_00101', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_06441', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_06451', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_06511', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_06521', 'maxWidth': 100, 'editable': True},
        {'field': 'DIT_06440', 'maxWidth': 100, 'editable': True},
        {'field': 'DIT_06450', 'maxWidth': 100, 'editable': True},
        {'field': 'DIT_06510', 'maxWidth': 100, 'editable': True},
        {'field': 'DIT_06520', 'maxWidth': 100, 'editable': True},
        {'field': 'DIC_06440', 'maxWidth': 100, 'editable': True},
        {'field': 'DIC_06450', 'maxWidth': 100, 'editable': True},
        {'field': 'DIC_06510', 'maxWidth': 100, 'editable': True},
        {'field': 'DIC_06520', 'maxWidth': 100, 'editable': True},	
        {'field': 'FI_19705', 'maxWidth': 100, 'editable': True},
        {'field': 'FI_19509', 'maxWidth': 100, 'editable': True},
        {'field': 'FI_19750', 'maxWidth': 100, 'editable': True},
        {'field': 'FIC_03802', 'maxWidth': 100, 'editable': True},
        {'field': 'FIC_03812', 'maxWidth': 100, 'editable': True},	
        {'field': 'FIC_03822', 'maxWidth': 100, 'editable': True},
        {'field': 'FIC_03832', 'maxWidth': 100, 'editable': True},
        {'field': 'FIC_03842', 'maxWidth': 100, 'editable': True},
        {'field': 'FIC_04050', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT251041', 'maxWidth': 100, 'editable': True},
        {'field': 'FIT_001011', 'maxWidth': 100, 'editable': True},
        {'field': 'FI_195091', 'maxWidth': 100, 'editable': True},
        {'field': 'PI_06761', 'maxWidth': 100, 'editable': True},
        {'field': 'PI_06771', 'maxWidth': 100, 'editable': True},
        {'field': 'PI_06781', 'maxWidth': 100, 'editable': True},
        {'field': 'PI_06791', 'maxWidth': 100, 'editable': True},
        {'field': 'PI_06801', 'maxWidth': 100, 'editable': True},
        {'field': 'hum_concentrado', 'maxWidth': 100, 'editable': True},
        {'field': 'FFIC_01820', 'maxWidth': 100, 'editable': True},
        {'field': 'FI_12734', 'maxWidth': 100, 'editable': True},
        ]
    
    
    columnsDefs_data_casos =  [
        {'field': 'caso_id', 'maxWidth': 80, 'editable': False},
        {'field': 'fecha_ini', 'maxWidth': 100, 'editable': False},
        {'field': 'fecha', 'maxWidth': 100, 'editable': True},
        {'field': 'nombre_caso', 'maxWidth': 150, 'editable': True},
        {'field': 'modelo', 'maxWidth': 100, 'editable': True},
        {'field': 'comentarios', 'maxWidth': 200, 'editable': True},
        ]
    columnsDefs_hist_caso=  [
        {'field': 'caso_id', 'maxWidth': 80, 'editable': False},
        {'field': 'fecha_ini', 'maxWidth': 100, 'editable': False},
        {'field': 'fecha', 'maxWidth': 100, 'editable': True},
        {'field': 'nombre_caso', 'maxWidth': 150, 'editable': True},
        {'field': 'modelo', 'maxWidth': 100, 'editable': True},
        {'field': 'comentarios', 'maxWidth': 200, 'editable': True},
        ]

    columnsDefs_data_base =  [
        {'field': 'id_flujo', 'maxWidth': 80, 'editable': False},
        {'field': 'codigo_flujo', 'maxWidth': 100, 'editable': False},
        {'field': 'nombre_flujo', 'maxWidth': 350, 'editable': False},
        {'field': 'Flujo', 'maxWidth': 100, 'editable': True},
        {'field': 'Tolerancia', 'maxWidth': 100, 'editable': True},
        ]
    
    columnsDefs_data_minestar =  [
        {'field': 'FECHA', 'maxWidth': 100, 'editable': False},
     	{'field': 'HORA_INICIO_CARGA', 'maxWidth': 80, 'editable': False},
        {'field': 'HORA_INICIO_CICLO', 'maxWidth': 80, 'editable': False},
        {'field': 'HORA_FIN_CICLO', 'maxWidth': 80, 'editable': False},
        {'field': 'TURNO', 'maxWidth': 80, 'editable': False},
        {'field': 'FRENTE', 'maxWidth': 80, 'editable': False},
        {'field': 'ORIGEN', 'maxWidth': 80, 'editable': False},
        {'field': 'POLIGONO', 'maxWidth': 80, 'editable': False},
        {'field': 'MATERIAL_BLOQUE', 'maxWidth': 80, 'editable': False},
        {'field': 'MATERIAL_MINESENSE', 'maxWidth': 80, 'editable': False},
        {'field': 'MATERIAL_MINESTAR', 'maxWidth': 80, 'editable': False},
        {'field': 'CAMION', 'maxWidth': 80, 'editable': False},
        {'field': 'EQ._CARGUÍO', 'maxWidth': 80, 'editable': False},
        {'field': 'DESTINO', 'maxWidth': 80, 'editable': False},
        {'field': 'TMH_ORIGINALES', 'maxWidth': 100, 'editable': True},
        {'field': 'TMH_AJUSTADAS', 'maxWidth': 80, 'editable': False},
        {'field': 'Columna1	Columna2', 'maxWidth': 80, 'editable': False},
        {'field': 'CUS', 'maxWidth': 80, 'editable':True},
        {'field': 'CUT', 'maxWidth': 80, 'editable': True},
        {'field': 'MOT', 'maxWidth': 80, 'editable': True},
        {'field': 'NSRCUGC', 'maxWidth': 80, 'editable': True},
        {'field': 'Columna3', 'maxWidth': 80, 'editable': True},
        {'field': 'HORA_INICIO_DESCARGA', 'maxWidth': 80, 'editable': False},
        {'field': 'HORA_FIN_CICLO2', 'maxWidth': 80, 'editable': False},
        {'field': 'X_CARGA', 'maxWidth': 80, 'editable': False},
        {'field': 'Y_CARGA', 'maxWidth': 80, 'editable': False},
        {'field': 'Z_CARGA', 'maxWidth': 80, 'editable': False},
        {'field': 'OID', 'maxWidth': 80, 'editable': False},
        ]

    columnsDefs_data_input =  [
        {'field': 'TMH', 'maxWidth': 100, 'editable': True},
        {'field': 'TMS', 'maxWidth': 80, 'editable': False},
        {'field': 'Hum', 'maxWidth': 80, 'editable': False},
        {'field': 'CuT', 'maxWidth': 80, 'editable':True},
        {'field': 'Mo', 'maxWidth': 80, 'editable': True},
        {'field': 'TMFCuT', 'maxWidth': 80, 'editable': True},
        {'field': 'TMFMo', 'maxWidth': 80, 'editable': True},
        ]

    
    columnsDefs_resultados =  [
        {'field': 'Codigo'         , 'maxWidth': 50},
        {'field': 'Flujo'         , 'maxWidth': 450},
        {'field': 'Masa Medida'    , 'maxWidth': 120},
        {'field': 'Masa recon'   , 'maxWidth': 120},
        {'field': 'Diferencia'  , 'maxWidth': 120},
        {'field': 'Tolerancia' , 'maxWidth': 120},
        {'field': 'Porcentaje Ajuste'  , 'maxWidth': 120},
        ]



    columnsDefs_desbalances =  [
        {'field': 'Area', 'maxWidth': 200, 'editable': False},
        {'field': 'Desbalance masa_Ini', 'maxWidth': 140, 'editable': False},
        {'field': 'Desbalance masa', 'maxWidth': 140, 'editable': False},
        ]

    
    header = dbc.Container([
        dbc.Row(
            [
                dbc.Col(
                    html.Img(
                        src=local_img_to_html_hidro(assets_folder, 'logo.png'), style={'width': '80%'}
                    ),  # align="center",
                    width={'size': 2},
                ),
                dbc.Col(
                    html.H2(nombre_app),
                    width={"size": 8, "offset": 1},
                    align="center",
                ),
            ],
        ),
    ], fluid=True)


    layout_carga_caso = html.Div([
        dbc.Row([  # start row Labels
            dbc.Col([
                html.H5('Parámetros de entrada'),
            ], width={"size": 4, "offset": 0}),
        ]),

        dbc.Row([  # start row Labels
            dbc.Col([
                dbc.FormFloating(
                    [
                        dbc.Input(id='fecha_inicio_caso',type='date', value=datetime.datetime.now().strftime('%Y-%m-%d') ),
                        dbc.Label("Fecha Inicio"),
                    ]),
            ], width={"size": 2, "offset": 0}),
            dbc.Col([
                dbc.FormFloating(
                    [
                        dbc.Input(id='fecha_final_caso',type='date', value=datetime.datetime.now().strftime('%Y-%m-%d') ),
                        dbc.Label("Fecha Final"),
                    ]),
            ], width={"size": 2, "offset": 0}),
            dbc.Col([
                dbc.Checklist(
                    id="crea-caso",
                    options=[
                        {"label": "Crear nuevo Caso", "value": 'Si'},
                    ],
                    #value=[''],
                    label_checked_style={"color": "green"},
                    input_checked_style={
                        "backgroundColor": "green",
                        "borderColor": "black",
                    },
                ),
            ], width={"size": 2, "offset": 0}),
            dbc.Col([
                dbc.FormFloating(
                    [
                        dbc.Input(id='id_caso_activo',type='int' ),
                        dbc.Label("Id Caso"),
                    ]),
            ], width={"size": 1, "offset": 0}),
            dbc.Col([
                dbc.Button('Obtener Datos', id='btn-get-casos', n_clicks=0, style=dict_style_boton_2),
                #html.Label(id='btn-sim-msg', children=' ', style={'font-size': 12}),
            ], width={"size": 2, "offset": 0}),

        ]),
        #html.Br(),
        dbc.Row([  # start row Labels
                dbc.Col([
                    dag.AgGrid(
                        id="data_casos2",
                        columnDefs = columnsDefs_data_casos,
                        className = 'ag-theme-balham',
                        style={"height": "100px", "width": "100%"}
                    )
                ], width={"size": 8, "offset": 0}),
                dbc.Col([
                    dbc.Button('Guardar Datos', id='btn-save-casos', n_clicks=0, style=dict_style_boton_2),
                    html.Label(id='btn-sim-msg_caso', children=' ', style={'font-size': 12}),
                ], width={"size": 2, "offset": 0}),
            html.Br(),
            html.Hr(),
            html.Div([
            html.Label("Valores a Visualizar:"),
            dcc.RadioItems(id="agg-tab2", options=[
                                                    {"label": "Medidos ", "value": "Medido"},
                                                    {"label": "Reconciliado ", "value": "Reconciliado"},
                                                    {"label": "Tolerancia ", "value": "Tolerancia"}
                                                    ], value="Reconciliado", inline=False)
            ], style={'padding': '10px 0'}),
            
             dbc.Col([
            html.Img(id="imagen_balance", style={"width": "80%"}),
            ], width={"size": 10, "offset": 0}),
           html.Br(),
           ]),
            html.Hr(),

        dbc.Row([  # start row Labels
                dbc.Col([
                    dag.AgGrid(
                        id="data_hcas2",
                        columnDefs = columnsDefs_hist_caso,
                        className = 'ag-theme-balham',
                        #style={"height": "470px", "width": "100%"}
                    )
                ],  width={"size": 8, "offset": 0}),
                
        ]),
    ])


    layout_recon_input = html.Div([
        html.Br(),
        dbc.Row([  # start row Labels
            dbc.Col([
                html.H5('Parámetros de entrada reconciliador (tabla editable)'),
            ], width={"size": 4, "offset": 0}),
        ]),
        html.Br(),
        dbc.Row([  # start row Labels
                dbc.Col(
                    [
                        dcc.Upload(
                            id='data-base-upload',
                            children='Cargar Excel Datos Base',
                            style={
                                'lineHeight'  : '250%',#'60px',
                                'borderWidth' : '1px',
                                'borderStyle' : 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                #'margin': '10px'
                            },
                            multiple=False # Allow multiple files to be uploaded
                            ),

                    ], width={'size': 2},
                ),
        ]),
        html.Br(),
        html.Label("Datos base de entrada a reconciliador (editable)"),
        dbc.Row([  # start row Labels
                dbc.Col([
                    dag.AgGrid(
                        id="recon-data-base",
                        columnDefs = columnsDefs_data_base,
                        className = 'ag-theme-balham',
                        #style={"height": "470px", "width": "100%"}
                    )
                ],  width={"size": 10, "offset": 0}),
        ]),
    ])

    layout_mina_input = html.Div([
        html.Br(),
        dbc.Row([  # start row Labels
            dbc.Col([
                html.H5('Datos Entrada TAG Concentradora (tabla editable)'),
            ], width={"size": 4, "offset": 0}),
        ]),
        html.Br(),
        dbc.Row([  # start row Labels
            dbc.Col([
                dbc.FormFloating(
                    [
                        dbc.Input(id='fecha_inicio_tag',type='date', value=datetime.datetime.now().strftime('%Y-%m-%d') ),
                        dbc.Label("Fecha Inicio"),
                    ]),
            ], width={"size": 2, "offset": 0}),
            dbc.Col([
                dbc.FormFloating(
                    [
                        dbc.Input(id='fecha_final_tag',type='date', value=datetime.datetime.now().strftime('%Y-%m-%d') ),
                        dbc.Label("Fecha Final"),
                    ]),
            ], width={"size": 2, "offset": 0}),
        ]),
        html.Br(),
        dbc.Row([  # start row Labels
                dbc.Col(
                    [
                        dcc.Upload(
                            id='data-tag-upload',
                            children='Cargar Excel Datos tag',
                            style={
                                'lineHeight'  : '250%',#'60px',
                                'borderWidth' : '1px',
                                'borderStyle' : 'dashed',
                                'borderRadius': '5px',
                                'textAlign': 'center',
                                #'margin': '10px'
                            },
                            multiple=False # Allow multiple files to be uploaded
                            ),

                    ], width={'size': 2},
                ),
        ]),
        html.Br(),
        html.Label("Datos de entrada TAG (editable)"),
        dbc.Row([  # start row Labels
                dbc.Col([
                    dag.AgGrid(
                        id="data-base-tag",
                        columnDefs = columnsDefs_data_tag,
                        className = 'ag-theme-balham',
                        #style={"height": "470px", "width": "100%"}
                    )
                ],  width={"size": 10, "offset": 0}),
        ]),
        #html.Br(),
        #dcc.Graph(id='fig-minestar'),
        html.Br(),
        dbc.Row([  # start row Labels
             dbc.Col([
                    dcc.Dropdown(
                        id='box-x-tag',
                        options=['Filtro Tag', 'Origen', 'Fecha' ],
                        value='filtro_tag' 
                        )

                ], width={"size": 2, "offset": 0}),
                dbc.Col([
                    dcc.Graph(id='fig_tag_box'),
                ],  width={"size": 10, "offset": 0}),

        ]),
        html.Br(),
        dbc.Row([  # start row Labels
            dbc.Col([
                dag.AgGrid(
                    id="input_tag",
                    columnDefs = columnsDefs_data_input,
                    className = 'ag-theme-balham',
                    csvExportParams={"fileName": "Input_tag.csv"},
                    #style={"height": "470px", "width": "100%"}
                )
            ],  width={"size": 10, "offset": 0}),
            dbc.Col([
                dbc.Button('Descargar a csv', id='btn-recon-csv2', n_clicks=0, style=dict_style_boton_2),
            ],  width={"size": 2, "offset": 0}),
        ]),
        
        #html.Br(),
        
    ])

    layout_recon_output = html.Div([

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
                # Parte del layout que se activa en tab de reconciliación
                html.Div([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button('Descargar a Excel', id='btn-recon-csv', n_clicks=0),
                            html.Label(id='btn-pub-msg_reccaso', children=' ', style={'font-size': 12}),
                        ]),
                    ]),
                    dcc.Download(id="descargar-excel"),  # <--- Este debe estar dentro de la misma pestaña
                ])
            ],  width={"size": 2, "offset": 0}),
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
            dbc.Col([
                dbc.Button('Descargar a csv', id='btn-desbal-csv', n_clicks=0, style=dict_style_boton_2),
            ],  width={"size": 2, "offset": 0}),
        ]),

    ])

    return dbc.Container(  # html.Div(
        [
            dcc.Store(id="store-data-mina"), dcc.Store(id="store-data-planta"),
            header,
            html.Hr(),

            dbc.Tabs(
                [
                    dbc.Tab(id="tab1", label="1 Crear/Cargar Caso"  , tab_id="Cargar_caso" , children=layout_carga_caso),
                    dbc.Tab(id="tab2", label="Carga TAG" , tab_id="minestar", children=layout_mina_input  ),
                    #dbc.Tab(id="tab3", label="Leyes Planta" , tab_id="leyes", children=layout_leyes_planta  ),
                    dbc.Tab(id="tab4", label="Reconciliador Entrada" , tab_id="Recon-input", children=layout_recon_input  ),
                    dbc.Tab(id="tab5", label="Reconciliador Resutlados" , tab_id="Recon-output", children=layout_recon_output  ),
                ],
                id="tabs",
            ),

            
        ], fluid=True,  # style={'padding': 5}
    )