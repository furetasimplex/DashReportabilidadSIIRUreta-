import copy,json
from unittest.mock import Mock
import pytest
from dash import html
from plotly.utils import PlotlyJSONEncoder
from . import irrigation_modules_panel as panel, irrigation_modules_model as model
from .test_irrigation_modules_db import snapshot

def text(c):return json.dumps(c,cls=PlotlyJSONEncoder,ensure_ascii=False)

def test_reference_vs_manual_distinct_and_zero_unknown():
    s=snapshot();s['referencia']=dict(fuente='Balance Diario (QA en memoria)',estado_referencia='VALIDA',cantidad_modulos_referencia=3,
        sugeridos=model.reference_preview(s['roster'],3)['sugeridos'],observacion=None,estructura_actual=True)
    original=copy.deepcopy(s)
    rendered=text(panel.detail(s));assert 'Sin confirmación modular' in rendered and 'M132' in rendered
    assert s==original
    s['vigente']=dict(estado_modular='SELECCION_CONOCIDA',cantidad_confirmada=3)
    s['seleccion']=[dict(nombre_modulo_snapshot=x,modulo_id=i) for i,x in [(195,'M131'),(197,'M133'),(198,'M134')]]
    rendered=text(panel.detail(s));assert all(x in rendered for x in ('3 de 5','M132','M134','Confirmación operacional'))
    s['vigente'].update(estado_modular='NINGUN_MODULO',cantidad_confirmada=0);s['seleccion']=[]
    assert '0 de 5' in text(panel.detail(s))
    s['vigente'].update(estado_modular='SIN_INFORMACION',cantidad_confirmada=None)
    assert 'Sin información de módulos en riego.' in text(panel.detail(s))

def test_readonly_controls_and_actions_do_not_require_phase():
    s=snapshot();rendered=text(panel.editor(s,False,[]))
    assert 'Solo lectura' in rendered and 'Confirmar módulos' not in rendered
    assert all(f'"id": "{control}"' not in rendered for control in ('imr-state','imr-selection','imr-motive','imr-confirm','imr-rectify','imr-close','imr-form'))
    assert 'Confirmar fase' not in rendered and 'Resolver contradicción' not in rendered
    count,confirm,rectify,close=panel.availability('SELECCION_CONOCIDA',[195],'motivo',{'snapshot':s,'can_write':False})
    assert confirm and rectify and close
    assert panel.availability('SELECCION_CONOCIDA',[195],'motivo',{'snapshot':s,'can_write':True})[1] is False

def test_history_reconstructs_names_from_snapshot():
    row=dict(version=1,estado_modular='SELECCION_CONOCIDA',fecha_efectiva='2026-10-19',cantidad_confirmada=1,
        usuario='admin_qa',created_at='2026-10-27',justificacion='Primera confirmación',referencia_snapshot_json=None,
        detalle=[dict(nombre_modulo_snapshot='M131 histórico',modulo_id=195,seleccionado=True)],eventos=[])
    assert 'M131 histórico' in text(panel.history_cards([row]))

def test_stale_visible(monkeypatch):
    from types import SimpleNamespace
    s=snapshot();monkeypatch.setattr(panel,'ctx',SimpleNamespace(triggered_id='imr-confirm'))
    monkeypatch.setattr(panel.db,'confirm_modules',Mock(side_effect=model.StaleContextError(model.STALE_MESSAGE)))
    message,_=panel.submit(1,0,0,{'snapshot':s},'key','SELECCION_CONOCIDA',[195],'motivo',0)
    assert model.STALE_MESSAGE in text(message)


def test_historical_denominator_and_readonly_options():
    s=snapshot();s['roster']['total']=6
    s['vigente']=dict(estado_modular='SELECCION_CONOCIDA',cantidad_confirmada=3,total_modulos_snapshot=5)
    assert '3 de 5 módulos' in text(panel.detail(s))
    assert all(x['disabled'] for x in panel.selection_options('SELECCION_CONOCIDA',{'snapshot':s,'can_write':False}))
    assert all(x['disabled'] for x in panel.selection_options('SIN_INFORMACION',{'snapshot':s,'can_write':True}))


def test_layout_is_pure_and_drawer_insert_does_not_change_phase(monkeypatch):
    from . import map_panel
    from .test_ux_governance import row
    monkeypatch.setattr(panel.db,'modular_snapshot',Mock(side_effect=AssertionError('Layout no consulta SQL')))
    panel.layout()
    monkeypatch.setattr(panel,'load_detail',lambda _:panel.detail(snapshot()))
    r=row();before=copy.deepcopy(r)
    component=map_panel._detail_with_modules(r)
    headings=[]
    for section in component.children:
        children=getattr(section,'children',None)
        if isinstance(children,list) and children and type(children[0]).__name__=='H6':headings.append(children[0].children)
    assert headings.index('Condición')+1==headings.index('MÓDULOS EN RIEGO')
    assert headings.index('MÓDULOS EN RIEGO')+1==headings.index('Riego')
    assert r==before


def test_invalid_roster_never_enables_confirmation():
    s=snapshot();s['roster'].update(campana_id=None,total=None,estado_roster='SIN_CAMPANA')
    rendered=text(panel.editor(s,True,[]));assert 'Sin información' in rendered
    count,confirm,rectify,close=panel.availability('NINGUN_MODULO',[],'motivo',dict(snapshot=s,can_write=True))
    assert 'no resuelto' in count and confirm and rectify and close


@pytest.mark.parametrize('confirmed',[False,True])
def test_unknown_never_shows_zero_operational_or_disabled_form(confirmed):
    s=snapshot();s['roster']['miembros']=s['roster']['miembros'][:2];s['roster']['total']=2
    if confirmed:s['vigente']=dict(estado_modular='SIN_INFORMACION',cantidad_confirmada=None)
    for allowed in (False,True):
        before=copy.deepcopy(s);rendered=text(panel.editor(s,allowed,[]))
        assert 'Sin información de módulos en riego.' in rendered
        assert '0 de 2' not in rendered
        assert 'Módulos disponibles en la parcela:' in rendered
        assert s==before


def test_count_requires_an_explicit_form_state():
    preview={'snapshot':snapshot(),'can_write':True}
    count,*_=panel.availability(None,[],'',preview)
    assert '0 de 5' not in count
    assert panel.availability('SELECCION_CONOCIDA',[],'',preview)[0]=='0 de 5 módulos seleccionados'
    assert '0 de 5 módulos en riego' in panel.availability('NINGUN_MODULO',[],'',preview)[0]
    assert 'pendiente de guardar' in panel.availability('NINGUN_MODULO',[],'',preview)[0]
    assert '0 de 5' not in panel.availability('SIN_INFORMACION',[],'',preview)[0]


def test_authorized_editor_complete_and_separate_from_operational_summary():
    s=snapshot();rendered=text(panel.editor(s,True,[]))
    for control in ('imr-form','imr-state','imr-selection','imr-motive','imr-confirm','imr-rectify','imr-close'):
        assert control in rendered
    assert 'Editar decisión modular' in rendered
    assert '0 de 5 módulos en riego' not in text(panel.detail(s))


def test_reference_zero_is_not_zero_confirmation():
    s=snapshot();s['referencia']=dict(fuente='Balance Diario',estado_referencia='VALIDA',cantidad_modulos_referencia=0,sugeridos=[])
    rendered=text(panel.editor(s,False,[]))
    assert '0 de 5 módulos' in rendered and 'Sin confirmación modular' in rendered
    assert '0 de 5 módulos en riego' not in rendered
    assert 'Ningún módulo confirmado en riego.' not in rendered


def test_distinct_blocks_and_confirmation_metadata_preserve_snapshot():
    s=snapshot();s['referencia']=dict(fuente='Balance Diario',estado_referencia='VALIDA',cantidad_modulos_referencia=3,
        sugeridos=model.reference_preview(s['roster'],3)['sugeridos'])
    s['vigente']=dict(estado_modular='SELECCION_CONOCIDA',cantidad_confirmada=3,usuario='Usuario QA',
        fecha_efectiva='2026-10-19',justificacion='Verificado en terreno')
    s['seleccion']=[dict(nombre_modulo_snapshot=x,modulo_id=i) for i,x in [(195,'M131'),(197,'M133'),(198,'M134')]]
    before=copy.deepcopy(s);rendered=text(panel.editor(s,False,[]))
    assert all(x in rendered for x in ('REFERENCIA OPERACIONAL','CONFIRMACIÓN MODULAR','Confirmado:',
        'M132','M134','Usuario QA','19-10-2026','Verificado en terreno'))
    assert 'M134' not in text(panel._reference(s))
    assert s==before


def test_zero_confirmation_has_explicit_operational_label():
    s=snapshot();s['vigente']=dict(estado_modular='NINGUN_MODULO',cantidad_confirmada=0)
    rendered=text(panel.editor(s,False,[]))
    assert '0 de 5 módulos en riego' in rendered
    assert 'Ningún módulo confirmado en riego.' in rendered


def test_absent_reference_is_hidden_without_changing_support():
    s=snapshot();assert panel._reference(s) is None
    rendered=text(panel.editor(s,False,[]))
    assert 'REFERENCIA OPERACIONAL' not in rendered and 'Sin referencia' not in rendered
    assert 'Sin confirmación modular' in rendered and 'M135' in rendered
    assert '0 de 5' not in rendered


def test_confirmation_is_first_and_documents_existing_evidence():
    s=snapshot();s['referencia']=dict(fuente='Referencia futura persistida',estado_referencia='VALIDA',cantidad_modulos_referencia=0,sugeridos=[])
    s['vigente']=dict(estado_modular='NINGUN_MODULO',cantidad_confirmada=0,version=2,
        fecha_efectiva='2026-10-19',justificacion='Balance Diario de Pilas 19-10-2026',
        observacion='Observación preexistente',evidencia_usuario='Evidencia textual existente')
    rendered=text(panel.detail(s))
    assert rendered.index('CONFIRMACIÓN MODULAR')<rendered.index('REFERENCIA OPERACIONAL')
    for label in ('Versión: 2','Motivo / fuente:','Observación preexistente','Evidencia textual existente'):
        assert label in rendered


@pytest.mark.parametrize('active',[False,True])
def test_action_gates_preserve_manual_workflow(active):
    s=snapshot({'id_confirmacion':1} if active else None);p=dict(snapshot=s,can_write=True)
    assert panel.availability('SELECCION_CONOCIDA',[195],'',p)[1:]==(True,True,True)
    assert panel.availability('SELECCION_CONOCIDA',[195],'Fuente libre, sin adjunto',p)[1:]==(active,not active,not active)
    assert panel.availability('SELECCION_CONOCIDA',[],'Fuente',p)[1:]==(True,True,not active)
    for state in ('NINGUN_MODULO','SIN_INFORMACION'):
        assert panel.availability(state,[],'Fuente',p)[1:]==(active,not active,not active)
    assert 'Indique la fuente o motivo de la decisión.' in text(panel.editor(snapshot(),True,[]))


def test_history_keeps_superseded_and_closed_versions_without_empty_reference():
    base=dict(campana_id=10,estado_modular='SELECCION_CONOCIDA',fecha_efectiva='2026-10-19',cantidad_confirmada=3,
        usuario='QA en memoria',created_at='2026-10-27',justificacion='Fuente manual',referencia_snapshot_json=None,
        detalle=[dict(nombre_modulo_snapshot=n,modulo_id=i,seleccionado=True) for i,n in [(195,'M131'),(196,'M132'),(197,'M133')]],eventos=[])
    v1=dict(base,version=1);v2=copy.deepcopy(dict(base,version=2))
    v2['detalle'][1].update(nombre_modulo_snapshot='M134',modulo_id=198)
    history=[v2,v1];before=copy.deepcopy(history)
    rendered=text(panel.history_cards(history))
    assert 'Supersedida' in rendered and 'Vigente' in rendered and 'M132' in rendered and 'M134' in rendered
    assert 'Sin referencia' not in rendered and history==before
    v2['eventos']=[dict(tipo_evento='CERRAR')]
    assert 'Cerrada' in text(panel.history_cards(history))
    closed=snapshot();assert 'Sin confirmación modular' in text(panel.detail(closed))
    assert 'M135' in text(panel.detail(closed))
