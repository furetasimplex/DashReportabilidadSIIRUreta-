"""Presentación M6: no abre conexiones ni redondea datos de cálculo."""
from dash import html,dcc,dash_table
from dash.dash_table.Format import Format,Scheme,Group
import dash_bootstrap_components as dbc
from .build_sql import EQUIPOS

LABELS=dict(zip(EQUIPOS,EQUIPOS))
LABELS.update(SRR_CV001='SRR — CV001',SRR_CV002='SRR — CV002',SRR_CV003='SRR — CV003',CHANCADOR_CV006='Chancador — CV006',PRINCIPAL_CV008='Principal TM1 — CV008',PRINCIPAL_CV108='Principal TM2 — CV108')
FIELDS=[('fecha_operacional','Fecha'),('turno','Turno'),('correa','Correa'),('pi_tmh','PI (TMH)'),('tum_tmh','TUM (TMH)'),('diferencia','Diferencia (TMH)'),('calidad_pi','Estado PI'),('fuente_auto','Fuente AUTO'),('modo_visible','Modo · Fuente'),('fuente_m6','Fuente aplicada al balance'),('valor_m6','TMH aplicado al balance'),('valor_auto','Tonelaje AUTO (TMH)'),('diferencia_tms','Diferencia (TMS)'),('motivo_m6','Motivo de la decisión'),('version_m6','Versión'),('huella_m6','Huella'),('equipo_codigo','Código original'),('tum_disponible','Disponibilidad TUM')]
FIELDS.append(('modo_m6','Selección original'))
# Los campos técnicos permanecen en los datos, no en el selector/columnas operacionales.
AUDIT_ONLY={'version_m6','huella_m6','equipo_codigo'}
OPERATIONAL_FIELDS=[(key,label) for key,label in FIELDS if key not in AUDIT_ONLY]
EXTRA=['valor_auto','tum_disponible','motivo_m6','modo_m6','diferencia_tms']
NUMERIC={'pi_tmh','tum_tmh','diferencia','valor_m6','valor_auto','diferencia_tms','version_m6'}
HEADINGS={'Tonelaje_AUTO':'Tonelaje AUTO','Tonelaje_M6':'Tonelaje propuesto','delta_Tonelaje':'Diferencia tonelaje','Ley_Cu_AUTO':'Ley Cu AUTO (%)','Ley_Cu_M6':'Ley Cu propuesta (%)','delta_Ley_Cu':'Diferencia ley Cu','FCu_AUTO':'Cu fino AUTO','FCu_M6':'Cu fino propuesto','delta_FCu':'Diferencia Cu fino','estado':'Comparación','fecha_operacional':'Fecha operacional','turno':'Turno','equipo_codigo':'Correa','modo':'Acción','version':'Versión','usuario':'Usuario','fecha_registro':'Fecha y hora','motivo':'Motivo','vigente':'Estado','solicitud_id':'Solicitud','comentario':'Comentario','id':'ID','delta_TMH':'Diferencia TMH'}
HEADINGS.update(pi_tmh='PI (TMH)',tum_tmh='TUM (TMH)',valor_auto='AUTO (TMH)',modo_propuesto='Acción propuesta',valor_propuesto='TMH propuesto')
HEADINGS.update(valor_vigente='TMH vigente')
for _suffix,_label in [('VIGENTE','vigente'),('PROPUESTO','propuesto')]:
    HEADINGS.update({f'Tonelaje_{_suffix}':f'Tonelaje {_label}',f'Ley_Cu_{_suffix}':f'Ley Cu {"propuesta" if _suffix=="PROPUESTO" else _label} (%)',f'FCu_{_suffix}':f'Cu fino {_label}'})

def number(v,n=2):
    return '—' if v is None else f'{v:,.{n}f}'.translate(str.maketrans(',.','.,'))

def row_id(r):return '|'.join(str(r[k]) for k in ('fecha_operacional','turno','equipo_codigo'))

def decorate(rows):
    return [{**r,'id':row_id(r),'correa':LABELS.get(r['equipo_codigo'],r['equipo_codigo']),
             'modo_visible':('MANUAL' if r.get('modo_m6')=='TUM' else 'AUTO')+' · '+str(r.get('fuente_m6','—'))} for r in rows]

def columns(fields,rows=()):
    def numeric(k):
        return k in NUMERIC or any(isinstance(r.get(k),(float,int)) and not isinstance(r.get(k),bool) for r in rows)
    return [dict(id=k,name=label,type='numeric' if numeric(k) else 'text',**({'format':Format(precision=2,scheme=Scheme.fixed,group=Group.yes,groups=3,decimal_delimiter=',',group_delimiter='.')} if numeric(k) else {})) for k,label in fields]

def tooltips(rows):
    return [{k:{'value':number(v,6) if isinstance(v,(int,float)) and not isinstance(v,bool) else ('—' if v is None else str(v)),'type':'text'} for k,v in r.items()} for r in rows]

TABLE_STYLE=dict(style_table={'overflowX':'auto','maxWidth':'100%'},style_cell={'fontFamily':'Inter, sans-serif','fontSize':14,'padding':'11px 12px','minWidth':95,'maxWidth':250,'whiteSpace':'normal','textAlign':'left'},style_header={'backgroundColor':'#F5F6FA','fontWeight':600,'whiteSpace':'normal'},style_data_conditional=[{'if':{'row_index':'odd'},'backgroundColor':'#FAFBFC'},{'if':{'filter_query':'{modo_m6} = "TUM"'},'backgroundColor':'#FFF5EA'},{'if':{'state':'selected'},'backgroundColor':'#FFF0DF','border':'1px solid #E86D1F'}])

def table(rows,fields=None,**kwargs):
    if not rows:return html.P('Sin registros para mostrar.',className='m6ct-muted')
    fields=fields or [(k,HEADINGS.get(k,k)) for k in rows[0]]
    return dash_table.DataTable(data=rows,columns=columns(fields,rows),page_size=12,sort_action='native',filter_action='native',tooltip_data=tooltips(rows),tooltip_duration=None,**TABLE_STYLE,**kwargs)

def metric(label,value):
    return html.Div([html.Span(label,className='m6ct-metric-label'),html.Strong(value)],className='m6ct-metric')

def section(title,children,**kwargs):
    return html.Section([html.H4(title),*children],className='m6ct-card',**kwargs)

def query_button(loading=False):
    return [dbc.Spinner(size='sm',color='light',spinner_style={'marginRight':'8px'}),
            html.Span('Consultando...')] if loading else 'Consultar'

def layout():
    return html.Div([
        html.Header([html.Div('BALANCE DE MASA · DEV',className='m6ct-eyebrow'),html.H3('Contingencia de Correas — Balance de Masa'),html.P('Consulta las fuentes PI y TUM, evalúa diferencias y administra sustituciones manuales por correa, fecha y turno'),html.P('Las decisiones modifican exclusivamente la fuente de entrada del Balance de Masa. No alteran Reportabilidad SIIR ni los datos originales',className='m6ct-scope'),html.Details([html.Summary('Cómo funciona AUTO técnico'),html.P('AUTO evalúa la calidad PI/TUM independientemente de FUERA_SERVICIO. AUTO · TUM es una elección técnica; MANUAL · TUM identifica una sustitución explícita. Las decisiones son globales por correa, fecha y turno.')])]),
        section('Consultar fuentes',[
            html.Div([html.Div([html.Label('Período operacional'),dcc.DatePickerRange(id='m6ct-periodo',start_date='2026-10-01',end_date='2026-10-12',display_format='DD-MM-YYYY',min_date_allowed='2026-09-01',minimum_nights=0)]),html.Div([html.Label('Turno inicial',htmlFor='m6ct-ti'),dcc.Dropdown(['A','B'],'A',id='m6ct-ti',clearable=False)]),html.Div([html.Label('Turno final',htmlFor='m6ct-tf'),dcc.Dropdown(['A','B'],'B',id='m6ct-tf',clearable=False)])],className='m6ct-query-grid'),
            html.Label('Correas a consultar',htmlFor='m6ct-equipos'),dcc.Dropdown([{'label':LABELS[e],'value':e} for e in EQUIPOS],list(EQUIPOS),multi=True,id='m6ct-equipos'),dbc.Button(query_button(),id='m6ct-cargar',color='primary',className='mt-3'),
            html.Div('Consultando fuentes PI/TUM...',id='m6ct-consultando',style={'display':'none'},className='mt-2',role='status'),
            html.Div(id='m6ct-carga-estado',className='mt-2',role='status'),
        ]),
        section('Diagnóstico PI/TUM',[
            dcc.Loading([
            html.Div(id='m6ct-resumen',className='m6ct-metrics'),
            dbc.Checklist(id='m6ct-solo-manuales',options=[{'label':'Mostrar solo decisiones manuales','value':'SI'}],value=[]),html.P('Filtre cada columna por correa, fecha, turno, fuente, modo o diferencia. Los filtros conservan las marcas; el resumen avisa de las selecciones ocultas.',className='m6ct-muted'),
            html.Details([html.Summary('Información adicional de fuentes'),dcc.Checklist(id='m6ct-columnas',options=[{'label':dict(FIELDS)[k],'value':k} for k in EXTRA],value=[],className='m6ct-column-options'),
                html.Small('Diferencia (TMS) expresa la diferencia TUM–PI en masa seca, con la conversión de humedad vigente. La simulación muestra el impacto incremental respecto de la configuración vigente.',className='m6ct-muted')]),
            dcc.Store(id='m6ct-raw'),dash_table.DataTable(id='m6ct-fuentes',columns=columns(OPERATIONAL_FIELDS),hidden_columns=EXTRA,data=[],row_selectable='multi',selected_rows=[],selected_row_ids=[],page_size=12,sort_action='native',filter_action='native',tooltip_duration=None,**TABLE_STYLE),
            ],id='m6ct-query-loading',type='circle',color='#E86D1F',display='hide',show_initially=False,fullscreen=False),
        ]),
        dcc.Store(id='m6ct-action-busy',data=False),dcc.Store(id='m6ct-action-kind',data='preview'),
        html.Fieldset([
        section('Administrar selección de fuente',[
            html.Div([dbc.Button('Marcar registros consultados',id='m6ct-todos',color='secondary',outline=True),dbc.Button('Quitar marcas',id='m6ct-ninguno',color='secondary',outline=True)],className='m6ct-actions'),html.P('Marcar registros consultados incluye todos los resultados cargados, también los ocultos por los filtros. Quitar marcas no borra decisiones guardadas.',className='m6ct-muted'),html.Div(id='m6ct-seleccion',role='status'),html.Label('Acción',htmlFor='m6ct-modo'),dcc.RadioItems([{'label':' Sustituir por TUM','value':'TUM'},{'label':' Volver a AUTO','value':'AUTO'}],'TUM',id='m6ct-modo',inline=True,className='m6ct-actions'),
            html.Label('Motivo de la decisión (obligatorio)',htmlFor='m6ct-motivo'),dbc.Input(id='m6ct-motivo',maxLength=500),html.Label('Comentario adicional (opcional)',htmlFor='m6ct-comentario'),dbc.Textarea(id='m6ct-comentario',maxLength=1000),
            html.Label('Caso para simular impacto',htmlFor='m6ct-caso'),dcc.Dropdown(id='m6ct-caso',options=[],placeholder='Sin caso · fuentes operacionales',clearable=True),html.P('Opcional. El caso solo determina los aportes manuales incluidos en la simulación. La decisión PI/TUM se guarda por correa, fecha y turno y se aplica a todos los casos que utilizan esta configuración de fuentes.',className='m6ct-muted'),
            dbc.Button([html.Span('Previsualizar impacto sin guardar',id='m6ct-preview-idle'),
                html.Span([dbc.Spinner(size='sm',color='light',spinner_style={'marginRight':'8px'}),'Previsualizando...'],
                    id='m6ct-preview-busy',style={'display':'none'})],id='m6ct-preview',color='primary'),
            html.Div(id='m6ct-action-progress',style={'display':'none'},className='mt-2',role='status'),
        ]),
        section('Previsualización del balance',[
            html.P('La previsualización no guarda decisiones ni recalcula resultados reconciliados.',className='m6ct-scope'),html.P('Configuración vigente → Configuración propuesta: impacto incremental de la selección, conservando las decisiones vigentes no seleccionadas.',className='m6ct-muted'),dcc.Loading(html.Div(id='m6ct-impacto',children=html.P('Seleccione registros e indique un motivo para simular.',className='m6ct-muted')),type='circle',color='#E86D1F',show_initially=False,fullscreen=False),dcc.Store(id='m6ct-token'),dcc.Store(id='m6ct-refresh'),
            dbc.Checklist(options=[{'label':'Confirmo guardar únicamente estas decisiones de fuente; no recalcula ni oficializa resultados.','value':'SI'}],value=[],id='m6ct-confirmacion'),dbc.Button('Confirmar decisiones',id='m6ct-guardar',color='warning',className='mt-3'),html.Div(id='m6ct-estado',role='status'),
        ]),
        ],id='m6ct-action-controls',disabled=False,style={'minWidth':0,'border':0,'padding':0,'margin':0}),
        section('Historial de decisiones de fuente',[dcc.Loading(html.Div(id='m6ct-historial',children=html.P('Consulte un período para cargar el historial.',className='m6ct-muted')))]),
    ],className='m6ct-shell')

def impact(comparison,source_preview,auto_vigente=None,auto_propuesto=None):
    comp={r['Flujo']:r for r in comparison}
    baseline,target=('VIGENTE','PROPUESTO') if 'Tonelaje_VIGENTE' in comparison[0] else ('AUTO','M6')
    def residual(s):return comp['F9']['Tonelaje_'+s]-comp['F10']['Tonelaje_'+s]-comp['F11']['Tonelaje_'+s]
    changed=[r for r in comparison if r['estado']=='CAMBIA']
    delta=[r['delta_TMH'] for r in source_preview]
    total=number(sum(delta),6) if all(v is not None for v in delta) else 'No disponible'
    fields=[('Flujo','Flujo')]+[(k,HEADINGS[k]) for k in (f'Tonelaje_{baseline}',f'Tonelaje_{target}','delta_Tonelaje',f'Ley_Cu_{baseline}',f'Ley_Cu_{target}','delta_FCu')]
    result=[html.Div([metric('Decisiones propuestas',str(len(source_preview))),metric('Diferencia seleccionada respecto de vigente (TMH)',total),metric('Flujos con variación / total de flujos',f'{len(changed)} / {len(comparison)}'),metric('Residual SRR vigente (TMS)',number(residual(baseline),6)),metric('Residual SRR propuesto (TMS)',number(residual(target),6)),metric('Variación del residual SRR (TMS)',number(residual(target)-residual(baseline),6)),metric('Variación F5 · inventario del silo (TMS)',number(comp['F5']['delta_Tonelaje'],6))],className='m6ct-metrics'),html.P('Residual SRR = F9 − F10 − F11. El residual no certifica el cierre físico del balance. Todas las variaciones principales corresponden a vigente → propuesta.',className='m6ct-muted'),html.H5('Flujos con variación · vigente → propuesta'),table(changed,fields),html.Details([html.Summary('Ver los 125 flujos'),table(comparison)]),html.Details([html.Summary('Selecciones por equipo y turno · diferencia respecto de vigente'),table(source_preview)]),html.P('Impacto en el inventario del silo: F5 se informa arriba; todos los flujos y magnitudes permanecen disponibles.',className='m6ct-muted')]
    if auto_vigente is not None and auto_propuesto is not None:
        def reference(rows,suffix):
            lookup={r['Flujo']:r for r in rows}
            return lookup['F9']['Tonelaje_'+suffix]-lookup['F10']['Tonelaje_'+suffix]-lookup['F11']['Tonelaje_'+suffix]
        result.append(html.Details([html.Summary('Comparación adicional con AUTO técnico'),html.P('AUTO técnico no incorpora decisiones manuales. AUTO → vigente y AUTO → propuesto muestran el efecto acumulado de decisiones existentes y propuestas; no representan exclusivamente el impacto de la nueva selección.',className='m6ct-muted'),metric('Residual SRR AUTO (TMS)',number(reference(auto_vigente,'AUTO'),6)),html.H5('AUTO → Vigente'),table(auto_vigente),html.H5('AUTO → Propuesto'),table(auto_propuesto)]))
    return result
