
import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc

import tabs.tab_import_mov as tab_mov
import tabs.tab_import_datos_filtrados as tab_datos
import tabs.tab_import_apilado as tab_apilado
import tabs.tab_importar_leyes as tab_leyes_granulo
import tabs.tab_importar_recuperaciones as tab_recuperacion
import tabs.tab_importar_reclamo_camiones as tab_reclamos
import tabs.tab_importar_representatividad as tab_representatividad
import tabs.tab_importar_NIR as tab_nir_pdf
import tabs.tab_importar_pesos_torre as tab_pesos_torre


dash.register_page(__name__, path="/importar_datos", name="Importar Datos")

layout = html.Div([
    dbc.CardHeader(html.H4("Módulo de Importación de Datos", className="p-2")),
    
    # NIVEL 1: Categorías principales
    dbc.Tabs(
        id='tabs-categorias-padre',
        active_tab='cat-balance',
        className="mb-2",
        children=[
            dbc.Tab(label='BALANCE METALÚRGICO', tab_id='cat-balance'),
            dbc.Tab(label='DATOS COMPLEMENTARIOS', tab_id='cat-complementarios'),
        ],
    ),
    
    # Contenedor para las sub-pestañas dinámicas
    html.Div(id='container-subtabs-importacion'),
    
    # Contenedor para el contenido de carga final
    html.Div(id='content-subtab-importacion', className="mt-3")
])
def register_callbacks(app):
    # Mantener los registros actuales
    tab_datos.register_callbacks(app)
    tab_mov.register_callbacks(app)
    tab_apilado.register_callbacks(app)
    tab_leyes_granulo.register_callbacks(app)
    tab_recuperacion.register_callbacks(app)
    tab_reclamos.register_callbacks(app)
    tab_representatividad.register_callbacks(app)
    tab_nir_pdf.register_callbacks(app)

    # CALLBACK PARA FILTRAR SUB-PESTAÑAS
    @app.callback(
        Output('container-subtabs-importacion', 'children'),
        Input('tabs-categorias-padre', 'active_tab')
    )
    def render_subtabs(categoria):
        if categoria == 'cat-balance':
            # Aquí quedan los 6 actuales
            return dbc.Tabs(
                id='tabs-importacion',
                active_tab='tab-datos-filtrados',
                children=[
                    dbc.Tab(label='Datos Planta (datos_filtrados)', tab_id='tab-datos-filtrados'),
                    dbc.Tab(label='Movimientos Mina (mov_cam)', tab_id='tab-mov-cam'),
                    dbc.Tab(label='Apilado y Rotopala', tab_id='tab-apilado'),
                    dbc.Tab(label='Leyes y Granulometría', tab_id='tab-importar-leyes-granulo'),
                    dbc.Tab(label='Reporte Recuperaciones', tab_id='tab-importar-recuperacion'),
                    dbc.Tab(label='Reclamo Camiones', tab_id='tab-reclamos'),
                ],
            )
        else: # cat-complementarios
            return dbc.Tabs(
                id='tabs-importacion',
                active_tab='tab-representatividad', # Define cuál inicia activa
                children=[
                    # Aquí agregamos el nuevo tab
                    dbc.Tab(label='Representatividad Torres', tab_id='tab-representatividad'),
                    dbc.Tab(label='NIR (PDF)', tab_id='tab-nir-pdf'),
                    dbc.Tab(label='Pesos Torre (Complementarios)', tab_id='tab-pesos-torre'),
                    # Puedes dejar el placeholder si quieres agregar más cosas luego
                    # dbc.Tab(label='Futura Importación', tab_id='tab-otra-data'),
                ],
            )

    # CALLBACK PARA MOSTRAR CONTENIDO
    @app.callback(
        Output('content-subtab-importacion', 'children'),
        Input('tabs-importacion', 'active_tab')
    )
    def render_content(subtab):
        if subtab == 'tab-datos-filtrados': return tab_datos.layout
        elif subtab == 'tab-mov-cam': return tab_mov.layout
        elif subtab == 'tab-apilado': return tab_apilado.layout
        elif subtab == 'tab-importar-leyes-granulo': return tab_leyes_granulo.layout
        elif subtab == 'tab-importar-recuperacion': return tab_recuperacion.layout
        elif subtab == 'tab-reclamos': return tab_reclamos.layout
        elif subtab == 'tab-representatividad': return tab_representatividad.layout
        elif subtab == 'tab-nir-pdf': return tab_nir_pdf.layout
        
        # Conexión correcta
        elif subtab == 'tab-pesos-torre': return tab_pesos_torre.layout
        
        return html.Div("Seleccione una opción válida")
