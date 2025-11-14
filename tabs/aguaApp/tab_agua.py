import dash_bootstrap_components as dbc
from dash import html, dcc
import dash_ag_grid as dag
import plotly.graph_objs as go
import os
import pandas as pd
import datetime
import string
from tabs.aguaApp.utils.utils_dash import get_nombre_app_agua, local_img_to_html_agua
import cv2
import matplotlib.pyplot as plt
import numpy as np


def create_alphabet_list(n):
    return list(string.ascii_uppercase[:n])


def render_layout_agua():
    project_folder = os.path.dirname(os.path.realpath(__file__))
    assets_folder = os.path.join(project_folder, 'assets')

    nombre_app = get_nombre_app_agua()

    date_now = datetime.datetime.now().replace(minute=0, second=0)
    fecha = date_now.strftime('%Y-%m-%d %H:%M')

    spc_colores = {
        'Cobre': ['#FF9040', '#411720', '#C7410B', '#FFBC8C', '#FFE9D9'],
        'Zinc': ['#001040', '#3B536A', '#00A269', '#00DBB7', '#AAE5E3']
    }

    dict_style_boton = {
        'background': spc_colores['Zinc'][1],
        'color': 'white',
        'border-color': spc_colores['Zinc'][0],
        'border-radius': '10px',
        'width': '100%',
        'fontSize': 13,
        'height': '40px',
        'textAlign': 'center'
    }

    dict_style_boton_2 = {
        'background': '#C0E48C',
        'color': 'black',
        'border-color': '#7EB72B',
        'border-radius': '10px',
        'width': '100%',
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
        {'field': 'Camiones_Cu fino_Ley Mina'},
        {'field': 'Camiones_Mo fino_Ley Mina'}
    ]

    columnsDefs_data_tag = [
        {'field': f, 'maxWidth': 120, 'editable': True}
        for f in [
            'Fini', 'Fend', 'FIT_61209', 'FIT_61206', 'FIT25104', 'WI_01769', 'WI_01769_DACA',
            'LI_12655A', 'LI_12655B', 'LI_06730A', 'LI_06730B', 'FIT_00101', 'FIT_06441',
            'FIT_06451', 'FIT_06511', 'FIT_06521', 'DIT_06440', 'DIT_06450', 'DIT_06510',
            'DIT_06520', 'DIC_06440', 'DIC_06450', 'DIC_06510', 'DIC_06520', 'FI_19705',
            'FI_19509', 'FI_19750', 'FIC_03802', 'FIC_03812', 'FIC_03822', 'FIC_03832',
            'FIC_03842', 'FIC_04050', 'FIT251041', 'FIT_001011', 'FI_195091', 'PI_06761',
            'PI_06771', 'PI_06781', 'PI_06791', 'PI_06801', 'hum_concentrado', 'FFIC_01820',
            'FI_12734'
        ]
    ]

    columnsDefs_data_casos = [
        {'field': 'caso_id', 'maxWidth': 80, 'editable': False},
        {'field': 'fecha_ini', 'maxWidth': 100, 'editable': False},
        {'field': 'fecha', 'maxWidth': 100, 'editable': True},
        {'field': 'nombre_caso', 'maxWidth': 150, 'editable': True},
        {'field': 'modelo', 'maxWidth': 100, 'editable': True},
        {'field': 'comentarios', 'maxWidth': 200, 'editable': True},
    ]

    columnsDefs_hist_caso = columnsDefs_data_casos.copy()

    columnsDefs_data_base = [
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
        {'field': 'CuT', 'maxWidth': 80, 'editable': True},
        {'field': 'Mo', 'maxWidth': 80, 'editable': True},
        {'field': 'TMFCuT', 'maxWidth': 80, 'editable': True},
        {'field': 'TMFMo', 'maxWidth': 80, 'editable': True},
    ]

    columnsDefs_resultados = [
        {'field': 'Codigo', 'maxWidth': 80},
        {'field': 'Flujo', 'maxWidth': 400},
        {'field': 'Masa Medida', 'maxWidth': 120},
        {'field': 'Masa recon', 'maxWidth': 120},
        {'field': 'Diferencia', 'maxWidth': 120},
        {'field': 'Tolerancia', 'maxWidth': 120},
        {'field': 'Porcentaje Ajuste', 'maxWidth': 140},
    ]

    columnsDefs_desbalances = [
        {'field': 'Area', 'maxWidth': 200, 'editable': False},
        {'field': 'Desbalance masa_Ini', 'maxWidth': 140, 'editable': False},
        {'field': 'Desbalance masa', 'maxWidth': 140, 'editable': False},
    ]
    """ 
    # === Header ===
    header = dbc.Container([
        dbc.Row([
            dbc.Col(html.Img(
                src=local_img_to_html_agua(assets_folder, 'logo.png'),
                style={'width': '80%'}
            ), width=2),
            dbc.Col(html.H2(nombre_app), width={"size": 8, "offset": 1}, align="center"),
        ])
    ], fluid=True)
    """
    # === Layout Carga de Caso ===
    layout_carga_caso = html.Div([
        dbc.Row([dbc.Col(html.H5('Parámetros de entrada'), width=4)]),
        dbc.Row([
            dbc.Col(dbc.FormFloating([
                dbc.Input(id='fecha_inicio_caso_agua', type='date', value=datetime.datetime.now().strftime('%Y-%m-%d')),
                dbc.Label("Fecha Inicio")
            ]), width=2),
            dbc.Col(dbc.FormFloating([
                dbc.Input(id='fecha_final_caso_agua', type='date', value=datetime.datetime.now().strftime('%Y-%m-%d')),
                dbc.Label("Fecha Final")
            ]), width=2),
            dbc.Col(dbc.Checklist(
                id="crea_caso_agua",
                options=[{"label": "Crear nuevo Caso", "value": 'Si'}],
                label_checked_style={"color": "green"},
                input_checked_style={"backgroundColor": "green", "borderColor": "black"}
            ), width=2),
            dbc.Col(dbc.FormFloating([
                dbc.Input(id='id_caso_activo_agua', type='int'),
                dbc.Label("Id Caso")
            ]), width=1),
            dbc.Col(dbc.Button('Obtener Datos', id='btn_get_casos_agua', n_clicks=0, style=dict_style_boton_2), width=2)
        ]),
        dbc.Row([
            dbc.Col(dag.AgGrid(
                id="data_casos2_agua",
                columnDefs=columnsDefs_data_casos,
                className='ag-theme-balham',
                style={"height": "100px", "width": "100%"}
            ), width=8),
            dbc.Col(dbc.Button('Guardar Datos', id='btn_save_casos_agua', n_clicks=0, style=dict_style_boton_2), width=2),
        ]),
        html.Br(),
        html.Div([
            html.Label("Valores a Visualizar:"),
            dcc.RadioItems(
                id="agg_tab2_agua",
                options=[
                    {"label": "Medidos ", "value": "Medido"},
                    {"label": "Reconciliado ", "value": "Reconciliado"},
                    {"label": "Tolerancia ", "value": "Tolerancia"}
                ],
                value="Reconciliado"
            )
        ], style={'padding': '10px 0'}),
        dbc.Col(html.Img(id="imagen_balance_agua", style={"width": "80%"}), width=10),
        html.Hr(),
        dbc.Row([dbc.Col(dag.AgGrid(
            id="data_hcas2_agua",
            columnDefs=columnsDefs_hist_caso,
            className='ag-theme-balham'
        ), width=8)])
    ])

    # === Layout TAG ===
    layout_mina_input = html.Div([
        html.Br(),
        dbc.Row([dbc.Col(html.H5('Datos Entrada TAG Concentradora (tabla editable)'), width=4)]),
        html.Br(),
        dbc.Row([
            dbc.Col(dbc.FormFloating([
                dbc.Input(id='fecha_inicio_tag_agua', type='date', value=datetime.datetime.now().strftime('%Y-%m-%d')),
                dbc.Label("Fecha Inicio")
            ]), width=2),
            dbc.Col(dbc.FormFloating([
                dbc.Input(id='fecha_final_tag_agua', type='date', value=datetime.datetime.now().strftime('%Y-%m-%d')),
                dbc.Label("Fecha Final")
            ]), width=2),
        ]),
        html.Br(),
        dbc.Row([dbc.Col(dcc.Upload(
            id='data_tag_upload_agua',
            children='Cargar Excel Datos tag',
            style={'lineHeight': '250%', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
            multiple=False
        ), width=2)]),
        html.Br(),
        dbc.Row([dbc.Col(dag.AgGrid(
            id="data_base_tag_agua",
            columnDefs=columnsDefs_data_tag,
            className='ag-theme-balham'
        ), width=10)]),
        html.Br(),
        dbc.Row([
            dbc.Col(dcc.Dropdown(
                id='box_x_tag_agua',
                options=['Filtro Tag', 'Origen', 'Fecha'],
                value='filtro_tag'
            ), width=2),
            dbc.Col(dcc.Graph(id='fig_tag_box_agua'), width=10),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col(dag.AgGrid(
                id="input_tag_agua",
                columnDefs=columnsDefs_data_input,
                className='ag-theme-balham',
                csvExportParams={"fileName": "Input_tag.csv"}
            ), width=10),
            dbc.Col(dbc.Button('Descargar a csv', id='btn_recon_csv2_agua', n_clicks=0, style=dict_style_boton_2), width=2),
        ]),
    ])

    # === Layout Reconciliador Input ===
    layout_recon_input = html.Div([
        html.Br(),
        dbc.Row([dbc.Col(html.H5('Parámetros de entrada reconciliador (tabla editable)'), width=4)]),
        html.Br(),
        dbc.Row([dbc.Col(dcc.Upload(
            id='data_base_upload_agua',
            children='Cargar Excel Datos Base',
            style={'lineHeight': '250%', 'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px', 'textAlign': 'center'},
            multiple=False
        ), width=2)]),
        html.Br(),
        dbc.Row([dbc.Col(dag.AgGrid(
            id="recon_data_base_agua",
            columnDefs=columnsDefs_data_base,
            className='ag-theme-balham'
        ), width=10)])
    ])

    # === Layout Reconciliador Output ===
    layout_recon_output = html.Div([
        html.Br(),
        dbc.Row([dbc.Col(html.H5('Ejecutar reconciliador y revisión de resultados'), width=6)]),
        html.Br(),
        dbc.Row([
            dbc.Col(dbc.Button('Ejecutar', id='btn_recon_agua', n_clicks=0, style=dict_style_boton_2), width=2),
            dbc.Col(dcc.Download(id="descargar_excel_agua"), width=2),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col(dag.AgGrid(
                id="recon_resultados_agua",
                columnDefs=columnsDefs_resultados,
                className='ag-theme-balham',
                csvExportParams={"fileName": "resultados_reconciliados.csv"}
            ), width=10),
            dbc.Col(dbc.Button('Descargar Excel', id='btn_recon_csv_agua', n_clicks=0, style=dict_style_boton_2), width=2),
            dbc.Col(dbc.Button('Publicar Datos', id='btn_publica_casos_agua', n_clicks=0, style=dict_style_boton_2), width=2),
        ]),
        html.Br(),
        dbc.Row([
            dbc.Col(dag.AgGrid(
                id="recon_desbalances_agua",
                columnDefs=columnsDefs_desbalances,
                className='ag-theme-balham'
            ), width=10),
            dbc.Col(dbc.Button('Descargar CSV', id='btn_desbal_csv_agua', n_clicks=0, style=dict_style_boton_2), width=2),
        ]),
    ])

    return dbc.Container([
        #header,
        html.Hr(),
        dbc.Tabs([
            dbc.Tab(label="1 Crear/Cargar Caso", tab_id="Cargar_caso_agua", children=layout_carga_caso),
            dbc.Tab(label="Carga TAG", tab_id="Tag_agua", children=layout_mina_input),
            dbc.Tab(label="Reconciliador Entrada", tab_id="Recon_input_agua", children=layout_recon_input),
            dbc.Tab(label="Reconciliador Resultados", tab_id="Recon_output_agua", children=layout_recon_output),
        ], id="tabs_agua"),
    ], fluid=True)
