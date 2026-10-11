"""Mapa por parcela: estados SQL exactos y fases exclusivamente visuales."""
from collections import Counter
import re
import logging
from datetime import date
from dash import ALL, Input, Output, State, callback, ctx, dcc, html
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from . import map_db
from .callbacks import serial, alert
from .map_states import FASES, ESTADOS, CALIDAD, fase_visual, actividad

PADS = {1: 'Óxidos', 2: 'Sulfuros'}
log = logging.getLogger(__name__)


def state(row):
    return FASES[row['fase_visual']]


def visible_rows(data, pad):
    return [r for r in (data or {}).get('rows',[]) if pad is None or r['pad_id']==pad]


def legend(rows):
    counts = Counter(r['fase_visual'] for r in rows)
    return [html.Div([html.Span(className='lix-legend-swatch '+css),
                     html.Span(label), html.Strong(str(counts[phase]))])
            for phase,(label,css) in FASES.items()]


def map_blocks(rows):
    blocks = []
    for pad in (1, 2):
        parcels = [r for r in rows if r['pad_id'] == pad]
        if not parcels:
            continue
        half = (len(parcels)+1)//2
        upper, lower = parcels[:half], list(reversed(parcels[half:]))
        def lane(items, bottom=False):
            return html.Div([html.Button([
                html.Span(f"P{r['numero_parcela']}", className='lix-parcel-label'),
                html.Span(className='lix-parcel-cell'),
            ], id={'type': 'lix-parcel', 'pad': pad, 'parcel': r['parcela_id']},
                n_clicks=0, className='lix-parcel '+state(r)[1],
                title=f"P{r['numero_parcela']} · {state(r)[0]} · {ESTADOS[r['estado_operacional']][1]}",
                **{'aria-label': f"{PADS[pad]} P{r['numero_parcela']}: {ESTADOS[r['estado_operacional']][1]}", 'aria-pressed': 'false'}) for r in items],
                className='lix-lane'+(' bottom' if bottom else ''),
                style={'gridTemplateColumns': f'repeat({half}, minmax(34px, 1fr))'})
        blocks.append(html.Section([
            html.Div([html.H4('Parcelas '+PADS[pad]), html.Span(f'{len(parcels)} parcelas · Vista por parcela')],
                     className='lix-map-heading'),
            html.Div([lane(upper), lane(lower, True)], className='lix-map-scroll'),
        ], className='lix-map-block'))
    return blocks


def layout():
    return html.Div([
        html.Div([html.H3('Mapa operacional de pilas'),
                  html.P('Fotografía diaria por parcela · estado operacional', className='text-muted')]),
        dbc.Card(dbc.CardBody(dbc.Row([
            dbc.Col([dbc.Label('Fecha operacional'), html.Div(dcc.DatePickerSingle(
                id='lix-map-date', date='2026-09-10', display_format='DD-MM-YYYY', first_day_of_week=1))], md=4),
            dbc.Col([dbc.Label('PAD'), dcc.Dropdown(id='lix-map-pad', value=None,
                options=[{'label':v,'value':k} for k,v in PADS.items()], placeholder='Ambos PAD', clearable=True)], md=4),
            dbc.Col(html.P('Seleccione una parcela para revisar su detalle.', className='text-muted mt-4'), md=4),
        ])), className='mb-3'),
        dcc.Store(id='lix-map-data'), html.Div(id='lix-map-error'),
        dcc.Loading(html.Div(id='lix-map-blocks')),
        html.Div(legend([]), id='lix-map-legend', className='lix-map-legend'),
        html.P('El color agrupa la fase operacional. Seleccione una parcela para revisar su condición exacta y actividad del día.',
               className='small text-muted mt-2'),
        dbc.Offcanvas(html.Div(id='lix-map-detail'), title='Detalle operacional',
                      id='lix-map-modal', is_open=False, placement='end',
                      backdrop=False, scrollable=True, className='lix-detail-drawer',
                      style={'width': '400px', 'maxWidth': '100vw'}),
    ], className='lix-operational')


@callback(Output('lix-map-data','data'), Output('lix-map-error','children'),
          Input('lix-map-date','date'),
          Input('lix-tabs','active_tab'), Input('subtabs-lixiviacion','style'))
def load_map(day, tab, style):
    if tab != 'lix-map-tab' or not style or style.get('display') == 'none':
        raise PreventUpdate
    try:
        rows = map_db.snapshot(day)
        data = [{**{k: serial(v) for k,v in r.items()}, 'fase_visual':fase_visual(r['estado_operacional'])} for r in rows]
        return {'fecha':day,'rows':data}, None
    except Exception as exc:
        return None, alert(exc)


@callback(Output('lix-map-blocks','children'), Output('lix-map-legend','children'),
          Input('lix-map-data','data'), Input('lix-map-pad','value'))
def render_map(data, pad):
    rows = visible_rows(data, pad)
    return map_blocks(rows), legend(rows)


def composition_table(raw):
    """Formatear una copia del texto SQL sin modificar el Store ni sumar módulos."""
    parsed = []
    for part in (raw or '').split('|'):
        match = re.fullmatch(r'\s*([A-Z_]+)\s*=\s*(\d+)\s*', part)
        if not match or match[1] not in ESTADOS:
            return html.P('Composición no disponible.', className='small text-muted mb-0')
        parsed.append((ESTADOS[match[1]][1], match[2]))
    return html.Table([
        html.Thead(html.Tr([html.Th('Estado', scope='col'), html.Th('Módulos', scope='col')])),
        html.Tbody([html.Tr([html.Td(label),html.Td(count)]) for label,count in parsed]),
    ], className='table table-sm mb-0 lix-composition-table')


def modules_table(row, modules, failed=False):
    if failed:
        return html.P('No fue posible cargar el detalle de módulos.', className='small text-muted mb-0')
    modules = modules if modules is not None else []
    children = []
    if len(modules) != row.get('modulos_total'):
        children.append(html.P(f"Inconsistencia: {len(modules)} módulos devueltos; "
                               f"{row.get('modulos_total', '—')} considerados en la parcela.",
                               className='small text-muted'))
    if not modules:
        children.append(html.P('Sin detalle de módulos disponible.', className='small text-muted mb-0'))
    else:
        children.append(html.Table([
            html.Thead(html.Tr([html.Th('Módulo'),html.Th('Estado')])),
            html.Tbody([html.Tr([
                html.Td('—' if m.get('nombre_modulo') is None else f"M{m['nombre_modulo']}"),
                html.Td(ESTADOS.get(m.get('estado_modulo'),(None,'Estado no disponible'))[1]),
            ]) for m in modules]),
        ], className='table table-sm mb-0 lix-module-table'))
    return html.Div(children)


def detail(row, modules=None, module_failed=False):
    def display_date(value):
        return None if value is None else date.fromisoformat(str(value)[:10]).strftime('%d-%m-%Y')
    def dates(items):
        return [(label, display_date(row.get(key))) for key, label in items]
    sections = [
        ('Identificación', [('PAD',row['nombre_pad']), ('Parcela',f"P{row['numero_parcela']}"),
                            ('Campaña',row.get('numero_campana')), ('Fecha',display_date(row['fecha']))]),
        ('Estado', ([('Fase operacional',state(row)[0]),
                     ('Condición actual',ESTADOS[row['estado_operacional']][1])]
                    if row['fase_visual']=='CICLO_HIDRAULICO' else
                    [('Estado operacional',ESTADOS[row['estado_operacional']][1])])),
        ('Módulos considerados', []),
    ]
    if (module_failed or not modules or len(modules)!=row.get('modulos_total')) and row.get('estados_distintos') is not None and row['estados_distintos'] > 1:
        sections.append(('Composición', []))
    sections.extend([
        ('Actividad del día', [('Riego hoy',actividad(row.get('tiene_dato_riego'),row.get('riego_activo'))),
                              ('Drenaje hoy',actividad(row.get('tiene_dato_drenaje'),row.get('drenaje_activo')))]),
        ('Hitos', dates([('fecha_ini_carguio','Inicio de apilado'),
                        ('fecha_conformado','Último módulo conformado'),
                        ('fecha_primer_riego','Primer riego'),
                        ('fecha_ultima_actividad_riego','Último riego registrado en campaña'),
                        ('fecha_ini_drenaje','Primer drenaje'),
                        ('fecha_ultima_actividad_drenaje','Último drenaje registrado en campaña'),
                        ('fecha_ini_reclamo','Primer módulo en reclamo'),
                        ('fecha_fin_reclamo','Último término de reclamo observado')])),
        ('Calidad', [('Calidad de información',CALIDAD.get(row.get('calidad_estado'),row.get('calidad_estado')))]),
    ])
    return html.Div([html.Section([
        html.H6(f"Módulos considerados · {row['modulos_total'] if row.get('modulos_total') is not None else '—'}" if title=='Módulos considerados' else title),
        modules_table(row,modules,module_failed) if title=='Módulos considerados' else
        composition_table(row.get('composicion_modulos')) if title=='Composición' else
        html.Dl([html.Div([html.Dt(label),html.Dd('—' if value is None else str(value))])
                 for label,value in fields], className='lix-detail-grid'),
        html.P('Los extremos de campaña pueden ser posteriores a la fecha operacional seleccionada.',
               className='small text-muted mt-3 mb-0') if title=='Hitos' else None,
    ], className='lix-detail-section') for title,fields in sections])


@callback(Output({'type':'lix-parcel','pad':ALL,'parcel':ALL},'className'),
          Output({'type':'lix-parcel','pad':ALL,'parcel':ALL},'aria-pressed'),
          Input({'type':'lix-parcel','pad':ALL,'parcel':ALL},'n_clicks'),
          Input('lix-map-date','date'), Input('lix-map-pad','value'),
          Input('lix-tabs','active_tab'), Input('lix-map-data','data'),
          State({'type':'lix-parcel','pad':ALL,'parcel':ALL},'id'),
          State({'type':'lix-parcel','pad':ALL,'parcel':ALL},'className'), prevent_initial_call=True)
def highlight_selection(clicks, day, pad, tab, data, identities, classes):
    """Presentación solamente: borde de selección sin alterar la categoría base."""
    trigger = ctx.triggered_id
    selected = [isinstance(trigger,dict) and identity == trigger and bool(click)
                for identity,click in zip(identities,clicks)]
    return ([base.replace(' selected','')+(' selected' if active else '')
             for base,active in zip(classes,selected)], ['true' if active else 'false' for active in selected])


@callback(Output('lix-map-modal','is_open'), Output('lix-map-detail','children'),
          Input({'type':'lix-parcel','pad':ALL,'parcel':ALL},'n_clicks'),
          Input('lix-map-date','date'), Input('lix-map-pad','value'), Input('lix-tabs','active_tab'),
          Input('lix-map-data','data'), prevent_initial_call=True)
def open_detail(clicks, day, pad, tab, data):
    trigger = ctx.triggered_id
    if not isinstance(trigger, dict) or not any(clicks or []) or not data or data['fecha'] != day:
        return False, None
    row = next((r for r in data['rows'] if r['pad_id']==trigger['pad'] and r['parcela_id']==trigger['parcel']), None)
    if row is None:
        return False, None
    try:
        modules = map_db.fetch_modulos_parcela(day, row['pad_id'], row['parcela_id'])
    except Exception as exc:
        log.warning('Detalle de módulos no disponible (%s).', type(exc).__name__)
        return True, detail(row, module_failed=True)
    return True, detail(row, modules=modules)
