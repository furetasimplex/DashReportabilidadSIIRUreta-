"""Retiro visual DEV sin cambiar evidencia, cálculos o interfaces legacy."""
import copy,json
from plotly.utils import PlotlyJSONEncoder
from unittest.mock import patch
from . import phase_panel,phase_flags,map_panel,panel
from .test_ux_governance import row,components
from .test_map import text_content


def test_dev_drawer_hides_only_legacy_section_without_mutating_row():
    r=dict(row(),fase_visual_legacy='NO_EVALUABLE',estado_operacional_SQL_original='SIN_COBERTURA')
    before=copy.deepcopy(r)
    with patch.object(phase_flags,'is_dev',return_value=True):
        content=phase_panel.detail(r)
    text=text_content(content)
    assert 'Modelo anterior' not in text and 'Estado del modelo anterior' not in text
    for label in ('Fase calculada','Condición diaria','Alerta','Riego','Drenaje','Confirmación','Módulos e hitos'):
        assert label in text
    assert r==before


def test_dev_confirmation_keeps_v2_condition_alert_and_active_decision():
    r=dict(row(),override_id=9,override_status='VIGENTE',fase_administrativa='DRENAJE_RESIDUAL',
        override_desde='2026-10-19',usuario_creacion='Usuario fixture',motivo_texto='Decisión existente')
    before=copy.deepcopy(r)
    with patch.object(phase_flags,'is_dev',return_value=True):
        content=phase_panel.confirmation_summary(r,{'decision':9})
    text=text_content(content)
    assert 'Modelo anterior' not in text
    assert all('modelo anterior' not in str(getattr(n,'title','')).lower() for n in components(content))
    for label in ('Fase automática actual','Riego continuo','Condición actual','Alerta','Confirmación vigente','Decisión existente'):
        assert label in text
    assert r==before


def test_non_dev_preserves_existing_presentation():
    with patch.object(phase_flags,'is_dev',return_value=False):
        assert 'Modelo anterior' in text_content(phase_panel.detail(row()))
        assert 'Modelo anterior' in text_content(phase_panel.confirmation_summary(row(),{'decision':0}))
        assert 'Validación puntual del modelo operacional' in text_content(panel.diagnostic_layout())


def test_dev_qa_closed_preserves_diagnostic_kpis_graphs_and_filters():
    with patch.object(phase_flags,'is_dev',return_value=False):old=panel.diagnostic_layout()
    with patch.object(phase_flags,'is_dev',return_value=True):new=panel.diagnostic_layout()
    old_nodes=list(components(old));new_nodes=list(components(new))
    assert [getattr(n,'id',None) for n in old_nodes]==[getattr(n,'id',None) for n in new_nodes]
    qa=next(n for n in new_nodes if getattr(n,'id',None)=='lix-diagnostic-advanced')
    assert qa.open is False
    assert 'Herramienta técnica QA (opcional)' in text_content(qa.children[0])
    assert 'modelo anterior' not in text_content(qa.children[0]).lower()
    # Únicamente cambia el título/ayuda del contenedor QA.
    new.children[-1].children[0]=old.children[-1].children[0]
    assert json.dumps(new,cls=PlotlyJSONEncoder)==json.dumps(old,cls=PlotlyJSONEncoder)


def test_dev_map_hides_comparison_selector_and_keeps_v2_cells():
    with patch.object(phase_flags,'is_dev',return_value=True),patch.object(phase_flags,'enabled',return_value=True):
        content=map_panel.layout()
        control=next(n for n in components(content) if getattr(n,'id',None)=='lix-map-model-control')
        dropdown=next(n for n in components(content) if getattr(n,'id',None)=='lix-map-view')
        assert control.style=={'display':'none'} and dropdown.value=='v2'
        assert [o['value'] for o in dropdown.options]==['v2']
        style,_,enabled=map_panel.initialize_model('lix-map-tab',{'display':'block'},'v2',True)
        assert style=={'display':'none'} and enabled is True


def test_dev_drawer_keeps_modular_component_in_same_position():
    from .irrigation_modules_panel import detail as modules_detail
    from .test_irrigation_modules_db import snapshot
    with patch.object(phase_flags,'is_dev',return_value=True),patch.object(phase_panel.irrigation_modules_panel,'load_detail',return_value=modules_detail(snapshot())):
        content=map_panel._detail_with_modules(row())
    text=text_content(content)
    assert 'Modelo anterior' not in text and 'MÓDULOS EN RIEGO' in text
    headings=[n.children for n in components(content) if type(n).__name__=='H6']
    assert headings.index('MÓDULOS EN RIEGO')<headings.index('Riego')<headings.index('Drenaje')<headings.index('Confirmación')
