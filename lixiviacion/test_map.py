from datetime import date
from contextlib import contextmanager
from unittest.mock import patch
import pytest
from dash.exceptions import PreventUpdate
from . import map_db, map_panel, callbacks
from .map_states import fase_visual, actividad


def fixture_rows():
    return [{**dict.fromkeys(map_db.FIELDS), 'fecha':date(2026,9,10), 'pad_id':pad,
             'parcela_id':n+(32 if pad==2 else 0), 'numero_parcela':n,
             'nombre_pad':map_panel.PADS[pad], 'estado_operacional':'SIN_INFORMACION'}
            for pad,count in ((1,32),(2,28)) for n in range(1,count+1)]


@pytest.mark.parametrize('states,phase',[
    (['APILADO'],'APILADO'), (['CONFORMADO_PRE_RIEGO'],'CONFORMADO_PRE_RIEGO'),
    (['RIEGO','RIEGO_DRENAJE','DRENAJE_CON_RIEGO_PAUSADO','PAUSA_HIDRAULICA','DRENAJE_RESIDUAL'],'CICLO_HIDRAULICO'),
    (['REPOSO_PRE_RECLAMO'],'ESPERA_RECLAMO'), (['RECLAMO'],'RECLAMO'),
    (['RECLAMADO'],'RECLAMADO'), (['MIXTO'],'MIXTO'),
    (['SIN_INFORMACION','SIN_COBERTURA_HIDRAULICA','SIN_CLASIFICAR'],'NO_EVALUABLE'),
])
def test_phase_mapping(states,phase):
    assert all(fase_visual(state)==phase for state in states)


@pytest.mark.parametrize('has,active,expected',[(1,1,'Sí'),(1,0,'No'),(1,None,'Sin dato'),
    (None,0,'Sin dato'),(None,1,'Sin dato'),(None,None,'Sin dato'),(0,0,'Sin dato')])
def test_activity_null_not_false(has,active,expected):
    assert actividad(has,active)==expected


def test_daily_contract_duplicates_and_missing_rows_rejected():
    rows=fixture_rows()
    assert len(map_db.validate_snapshot(rows,'2026-09-10'))==60
    for bad in (rows[:-1],rows+[rows[0]], [dict(r,fecha=date(2026,9,11)) for r in rows],
                [dict(rows[0],numero_parcela=99)]+rows[1:]):
        with pytest.raises(ValueError):
            map_db.validate_snapshot(bad,'2026-09-10')


def test_one_parameterized_query_and_local_pad_filter():
    calls=[]
    class Result:
        def mappings(self): return fixture_rows()
    class Conn:
        def execute(self,sql,params):
            calls.append((str(sql),params))
            return Result()
    @contextmanager
    def connect(): yield Conn()
    with patch.object(map_db,'_connection',connect):
        rows=map_db.snapshot('2026-09-10')
    assert len(calls)==1
    assert calls[0][1]=={'fecha':date(2026,9,10)}
    assert '2026' not in calls[0][0]
    assert 'fn_estado_operacional_parcela_diario(:fecha)' in calls[0][0]
    assert 'vw_tablero' not in calls[0][0] and 'JOIN' not in calls[0][0]
    assert [len(map_panel.visible_rows({'rows':rows},p)) for p in (None,1,2)]==[60,32,28]


def test_store_retains_exact_state_composition_and_geometry():
    rows=fixture_rows()
    rows[16].update(estado_operacional='MIXTO',estados_distintos=2,modulos_total=2,
                    composicion_modulos='APILADO = 1 | CONFORMADO_PRE_RIEGO = 1')
    with patch.object(map_db,'snapshot',return_value=rows):
        data,error=map_panel.load_map('2026-09-10','lix-map-tab',{'display':'block'})
    assert error is None
    r=data['rows'][16]
    assert r['fase_visual']==r['estado_operacional']=='MIXTO'
    assert r['composicion_modulos']==rows[16]['composicion_modulos']
    assert 'fase_visual' not in rows[16]
    blocks,_=map_panel.render_map(data,None)
    def ids(block): return [[b.id['parcel'] for b in lane.children] for lane in block.children[1].children]
    assert ids(blocks[0])==[list(range(1,17)),list(range(32,16,-1))]
    assert ids(blocks[1])==[list(range(33,47)),list(range(60,46,-1))]


def text_content(component):
    if component is None: return ''
    if isinstance(component,(str,int)): return str(component)
    children=component if isinstance(component,list) else getattr(component,'children',[])
    return ' '.join(text_content(c) for c in (children if isinstance(children,list) else [children]))


def test_drawer_exact_state_phase_dates_and_nulls():
    r=fixture_rows()[0]
    r.update(estado_operacional='DRENAJE_CON_RIEGO_PAUSADO',fase_visual='CICLO_HIDRAULICO')
    rendered=text_content(map_panel.detail(r))
    for value in ('Ciclo hidráulico','Drenaje con riego pausado','10-09-2026','Sin dato','—',
                  'Último módulo conformado','Último término de reclamo observado'):
        assert value in rendered
    r.update(estado_operacional='MIXTO',fase_visual='MIXTO',estados_distintos=2,
             composicion_modulos='RECLAMADO = 4 | RECLAMO = 1')
    rendered=text_content(map_panel.detail(r))
    assert 'Reclamado 4' in rendered and 'Reclamo 1' in rendered
    assert 'RECLAMADO' not in rendered and rendered.count('Mixto')==1
    assert r['composicion_modulos']=='RECLAMADO = 4 | RECLAMO = 1'


@pytest.mark.parametrize('code',['APILADO','CONFORMADO_PRE_RIEGO','REPOSO_PRE_RECLAMO','RECLAMO','RECLAMADO','MIXTO'])
def test_nonhydraulic_no_redundancy(code):
    r=fixture_rows()[0]
    r.update(estado_operacional=code,fase_visual=fase_visual(code))
    rendered=text_content(map_panel.detail(r))
    assert 'Estado operacional' in rendered
    assert 'Fase operacional' not in rendered and 'Condición actual' not in rendered


def test_new_labels_note_future_date_and_friendly_composition():
    r=fixture_rows()[0]
    r.update(estado_operacional='RIEGO_DRENAJE',fase_visual='CICLO_HIDRAULICO',
             fecha_ultima_actividad_riego=date(2026,9,27))
    rendered=text_content(map_panel.detail(r))
    for value in ['Fase operacional','Condición actual','Riego + drenaje','27-09-2026',
                  'Último riego registrado en campaña','Último drenaje registrado en campaña',
                  'Los extremos de campaña pueden ser posteriores a la fecha operacional seleccionada.']:
        assert value in rendered
    raw='APILADO = 1 | CONFORMADO_PRE_RIEGO = 1'
    rendered=text_content(map_panel.composition_table(raw))
    assert 'Apilado 1' in rendered and 'Conformado / espera de riego 1' in rendered
    assert 'CONFORMADO_PRE_RIEGO' not in rendered


def test_tab_order_and_ids_preserved():
    from .panel import layout
    tabs=layout()
    assert [t.tab_id for t in tabs.children]==['lix-map-tab','lix-diagnostic-tab']
    assert tabs.active_tab=='lix-map-tab'


def test_hidden_and_error_paths():
    with patch.object(map_db,'snapshot',side_effect=AssertionError('DB')):
        with pytest.raises(PreventUpdate):
            map_panel.load_map('2026-09-10','lix-diagnostic-tab',{'display':'block'})
    with patch.object(callbacks.db,'options',side_effect=AssertionError('DB')):
        with pytest.raises(PreventUpdate):
            callbacks.options({'display':'block'},'2026-06-01','2026-09-10',None,None,None,None,'lix-map-tab')
    with patch.object(map_db,'snapshot',side_effect=ValueError('Duplicados')):
        data,error=map_panel.load_map('2026-09-10','lix-map-tab',{'display':'block'})
    assert data is None and error is not None
    assert map_panel.render_map(data,None)[0]==[]
