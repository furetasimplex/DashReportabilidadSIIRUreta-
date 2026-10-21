"""Pantalla integrada al sidebar SIIR; sin consultas durante import/layout."""
from dash import dcc, html, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc
from .db import HYDRAULIC_LABELS

LABELS = [('fecha', 'Fecha'), ('pad', 'PAD'), ('parcela', 'Parcela'),
          ('campana', 'Campaña hidráulica'), ('estado', 'Asignación hidráulica'), ('flujo_m3_d', 'Flujo [m³/d]'),
          ('cu_drenaje_gl', 'Cu drenaje [g/L]'), ('cu_refino_gl', 'Cu refino [g/L]'),
          ('delta_cu_gl', 'ΔCu [g/L]'), ('transferencia_cu_t_d', 'Transferencia Cu [t/d]')]


def diagnostic_layout():
    controls = [dbc.Col([
        html.Label('Fecha inicio / Fecha fin', className='d-block'),
        dcc.DatePickerRange(id='lix-fechas', start_date='2026-06-01',
                            end_date='2026-09-10', display_format='DD-MM-YYYY',
                            first_day_of_week=1, minimum_nights=0),
    ], md=4, className='mb-2')]
    for key, label, opts in [
        ('pad', 'PAD', [{'label': 'Óxidos', 'value': 1}, {'label': 'Sulfuros', 'value': 2}]),
        ('campana', 'Campaña hidráulica', []), ('parcela', 'Parcela', []),
        ('estado', 'Asignación hidráulica', [{'label': label, 'value': code}
         for code, label in HYDRAULIC_LABELS.items()]),
    ]:
        assignment_help=('Campaña hidráulica: registro asociado a una campaña hidráulica válida para esa fecha. '
                         'Fuera de ventana hidráulica: registro existente que no puede asociarse a una campaña hidráulica activa para esa fecha.')
        controls.append(dbc.Col([dbc.Label([label,html.Span(' ⓘ',title=assignment_help)] if key=='estado' else label), dcc.Dropdown(id='lix-'+key,
                          options=opts, value=None, placeholder='Todos', clearable=True)],
                          md=4 if key == 'estado' else 2, className='mb-2'))
    controls.append(dbc.Col(dbc.Button('Consultar', id='lix-consultar', n_clicks=0,
                                     color='primary', className='mt-4'), md=2))
    columns = []
    for key, label in LABELS:
        c = {'name': label, 'id': key}
        if key not in ('fecha', 'pad', 'estado'):
            c.update(type='numeric', format=Format(precision=0 if key in ('parcela', 'campana') else 3,
                                                   scheme=Scheme.fixed, group=True))
        columns.append(c)
    help_text = {
        'kpi-flujo': 'Volumen diario equivalente acumulado de las parcelas seleccionadas.',
        'kpi-cu': 'Transferencia neta calculada a partir de flujo y diferencia Cu drenaje-refino.',
        'kpi-delta': 'Promedio simple de registros parcela-día válidos; no ponderado por flujo.',
        'kpi-fuera': 'Registros parcela-día clasificados como Fuera de ventana hidráulica: sin campaña hidráulica activa para esa fecha.',
    }
    cards = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([
        html.Div([html.Span(label, id='lix-label-'+key), html.Span(' ⓘ', title=help_text[key])], className='text-muted'), html.H4('—', id='lix-'+key, className='mb-0')
    ])), md=3, className='mb-3') for key, label in [
        ('kpi-flujo', 'Flujo acumulado [m³]'), ('kpi-cu', 'Transferencia Cu [t Cu]'),
        ('kpi-delta', 'ΔCu promedio parcelas [g/L]'), ('kpi-fuera', 'Registros sin asignación hidráulica')]])
    graph_config = {'displaylogo': False, 'scrollZoom': False}
    return dbc.Container([
        html.H3('Tablero de Lixiviación', className='my-3', style={'color': '#1F4E78'}),
        html.P('Seguimiento físico y químico por PAD, parcela y fecha.', className='text-muted'),
        dbc.Card(dbc.CardBody(dbc.Row(controls)), className='mb-3'),
        html.Div(id='lix-opciones-error'), dcc.Store(id='lix-aplicado'),
        dcc.Loading(html.Div([
            html.Div(id='lix-error'), html.Div(id='lix-resumen', className='text-muted mb-2'), cards,
            dbc.Row([dbc.Col(dbc.Card(dcc.Graph(id='lix-flujo', config=graph_config)), md=6),
                     dbc.Col(dbc.Card([dcc.Graph(id='lix-quimica', config=graph_config),
                         html.P('Promedio simple por fecha y PAD de los registros disponibles de las parcelas seleccionadas; los valores ausentes se excluyen de cada promedio. No ponderado por caudal.',
                                className='lix-diagnostic-method')]), md=6)], className='mb-3'),
            dbc.Card(dcc.Graph(id='lix-transferencia', config=graph_config), className='mb-3'),
        ]),id='lix-diagnostic-analysis'),
        dbc.Card(dbc.CardBody([
            html.H5('Detalle diario'),
            html.P('Vacío = dato no disponible; 0 = valor almacenado. Los filtros de esta tabla solo afectan al detalle. '
                   'Use =, >, >=, < o <=; para buscar texto, use contains («contiene»). Combine condiciones con &&.', className='text-muted small'),
            html.Div(id='lix-tabla-error'), html.Div(id='lix-tabla-total', className='small text-muted'),
            dcc.Loading(dash_table.DataTable(id='lix-tabla', columns=columns, data=[],
                page_action='custom', page_current=0, page_size=25, page_count=0,
                sort_action='custom', sort_mode='multi', sort_by=[], filter_action='custom', filter_query='',
                filter_options={'placeholder_text':'Filtrar...'},
                style_table={'overflowX': 'auto'},
                style_cell={'fontFamily': 'Segoe UI, Arial, sans-serif', 'fontSize': '12px',
                            'padding': '6px 10px', 'textAlign': 'right'},
                style_header={'backgroundColor': '#1F4E78', 'color': 'white', 'fontWeight': 600},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F7FB'}],
                locale_format={'decimal': ',', 'group': '.', 'grouping': [3]},
            )),
        ]),id='lix-diagnostic-daily'),
        html.Details([
            html.Summary([html.Span('Validación puntual del modelo operacional'),html.Small(
                'Herramienta técnica para revisar una parcela/fecha específica y comparar el resultado del modelo V2 con el modelo anterior.')]),
            html.Div([html.P('Aplique los filtros superiores con Consultar y seleccione un caso para revisar el modelo V2. La fecha de validación corresponde al fin del período consultado.',className='small text-muted'),
                html.Div(id='lix-phase-diagnostic'),
                dcc.Loading(html.Div(html.P('Seleccione una parcela para visualizar su estado operacional y evolución.',
                    className='text-muted'),id='lix-operacional',className='mb-3')),
            ],className='lix-diagnostic-advanced-body'),
        ],id='lix-diagnostic-advanced',open=False,className='lix-diagnostic-advanced'),
    ],fluid=True,className='lix-diagnostic-shell')


def layout():
    from .map_panel import layout as map_layout
    return dbc.Tabs([
        dbc.Tab(map_layout(), label='Mapa operacional de pilas', tab_id='lix-map-tab'),
        dbc.Tab(diagnostic_layout(), label='Diagnóstico', tab_id='lix-diagnostic-tab'),
        # Conservado para una etapa futura; fuera de navegación hasta aprobar reglas.
        *([dbc.Tab(dbc.Alert('Funcionalidad en desarrollo', color='light', className='m-4'),
                label='Recomendador de Riegos y Drenajes', tab_id='lix-recommender-tab')]
          if False else []),
    ], id='lix-tabs', active_tab='lix-map-tab')


from . import callbacks  # noqa: E402,F401 -- decoradores globales, patrón del proyecto
