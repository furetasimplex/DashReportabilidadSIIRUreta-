"""Pantalla integrada al sidebar SIIR; sin consultas durante import/layout."""
from dash import dcc, html, dash_table
from dash.dash_table.Format import Format, Scheme
import dash_bootstrap_components as dbc

LABELS = [('fecha', 'Fecha'), ('pad', 'PAD'), ('parcela', 'Parcela'),
          ('campana', 'Campaña'), ('estado', 'Estado'), ('flujo_m3_d', 'Flujo [m³/d]'),
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
        ('campana', 'Campaña', []), ('parcela', 'Parcela', []),
        ('estado', 'Estado asignación', [{'label': x, 'value': x} for x in
         ['CAMPANA_HIDRAULICA', 'FUERA_VENTANA_RIEGO']]),
    ]:
        controls.append(dbc.Col([dbc.Label(label), dcc.Dropdown(id='lix-'+key,
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
    cards = dbc.Row([dbc.Col(dbc.Card(dbc.CardBody([
        html.Div(label, id='lix-label-'+key, className='text-muted'), html.H4('—', id='lix-'+key, className='mb-0')
    ])), md=3, className='mb-3') for key, label in [
        ('kpi-flujo', 'Flujo acumulado [m³]'), ('kpi-cu', 'Transferencia Cu [t Cu]'),
        ('kpi-delta', 'ΔCu promedio parcelas [g/L]'), ('kpi-fuera', 'Registros fuera de ventana')]])
    graph_config = {'displaylogo': False, 'scrollZoom': False}
    return dbc.Container([
        html.H3('Tablero de Lixiviación', className='my-3', style={'color': '#1F4E78'}),
        html.P('Seguimiento físico y químico por PAD, parcela y fecha.', className='text-muted'),
        dbc.Card(dbc.CardBody(dbc.Row(controls)), className='mb-3'),
        html.Div(id='lix-opciones-error'), dcc.Store(id='lix-aplicado'),
        dcc.Loading(html.Div([
            html.Div(id='lix-error'), html.Div(id='lix-resumen', className='text-muted mb-2'), cards,
            dbc.Row([dbc.Col(dbc.Card(dcc.Graph(id='lix-flujo', config=graph_config)), md=6),
                     dbc.Col(dbc.Card(dcc.Graph(id='lix-quimica', config=graph_config)), md=6)], className='mb-3'),
            dbc.Card(dcc.Graph(id='lix-transferencia', config=graph_config), className='mb-3'),
        ])),
        dbc.Card(dbc.CardBody([
            html.H5('Detalle diario'),
            html.P('Vacío = dato no disponible; 0 = valor almacenado. Los filtros de esta tabla solo afectan al detalle. '
                   'Use =, >=, <= o contains y combine con &&.', className='text-muted small'),
            html.Div(id='lix-tabla-error'), html.Div(id='lix-tabla-total', className='small text-muted'),
            dcc.Loading(dash_table.DataTable(id='lix-tabla', columns=columns, data=[],
                page_action='custom', page_current=0, page_size=25, page_count=0,
                sort_action='custom', sort_mode='multi', sort_by=[], filter_action='custom', filter_query='',
                style_table={'overflowX': 'auto'},
                style_cell={'fontFamily': 'Segoe UI, Arial, sans-serif', 'fontSize': '12px',
                            'padding': '6px 10px', 'textAlign': 'right'},
                style_header={'backgroundColor': '#1F4E78', 'color': 'white', 'fontWeight': 600},
                style_data_conditional=[{'if': {'row_index': 'odd'}, 'backgroundColor': '#F2F7FB'}],
                locale_format={'decimal': ',', 'group': '.', 'grouping': [3]},
            )),
        ])),
    ], fluid=True)


def layout():
    from .map_panel import layout as map_layout
    return dbc.Tabs([
        dbc.Tab(map_layout(), label='Mapa operacional de pilas', tab_id='lix-map-tab'),
        dbc.Tab(diagnostic_layout(), label='Diagnóstico', tab_id='lix-diagnostic-tab'),
        dbc.Tab(dbc.Alert('Funcionalidad en desarrollo', color='light', className='m-4'),
                label='Recomendador de Riegos y Drenajes', tab_id='lix-recommender-tab'),
    ], id='lix-tabs', active_tab='lix-map-tab')


from . import callbacks  # noqa: E402,F401 -- decoradores globales, patrón del proyecto
