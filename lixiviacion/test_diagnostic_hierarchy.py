"""Jerarquía de Diagnóstico sin alterar consultas, métricas o figuras."""
from unittest.mock import patch
from . import panel,phase_panel,phase_db
from .test_ux_governance import components,row
from .test_map import text_content


def test_analysis_then_daily_then_technical_section_closed_by_default():
    layout=panel.diagnostic_layout();nodes=list(components(layout))
    ids=[getattr(n,'id',None) for n in nodes]
    assert ids.index('lix-consultar')<ids.index('lix-kpi-flujo')<ids.index('lix-flujo')<ids.index('lix-tabla')<ids.index('lix-diagnostic-advanced')
    assert layout.children[-1].id=='lix-diagnostic-advanced'
    technical=next(n for n in nodes if getattr(n,'id',None)=='lix-diagnostic-advanced')
    assert technical.open is False
    children_ids=[getattr(n,'id',None) for n in components(technical)]
    assert 'lix-phase-diagnostic' in children_ids and 'lix-operacional' in children_ids
    assert 'lix-kpi-flujo' not in children_ids and 'lix-tabla' not in children_ids
    summary=text_content(technical.children[0])
    assert 'Validación puntual del modelo operacional' in summary and 'Herramienta técnica' in summary


def test_filter_texts_and_methodology_are_explicit_without_new_syntax():
    layout=panel.diagnostic_layout();nodes=list(components(layout));text=text_content(layout)
    table=next(n for n in nodes if getattr(n,'id',None)=='lix-tabla')
    assert table.filter_options=={'placeholder_text':'Filtrar...'}
    assert table.filter_action=='custom' and table.filter_query==''
    assert 'contains («contiene»)' in text and 'Combine condiciones con &&' in text
    assert 'No ponderado por caudal' in text and 'valores ausentes se excluyen' in text
    assert 'Registros sin asignación hidráulica' in text
    hints=' '.join(str(getattr(n,'title','')) for n in nodes)
    assert 'Campaña hidráulica: registro asociado' in hints and 'Fuera de ventana hidráulica: registro existente' in hints


def test_point_validation_requires_explicit_selection_and_preserves_rows():
    r=dict(row(),estado_operacional_SQL_original='SIN_COBERTURA',fase_visual_legacy=None,
        fase_administrativa=None,origen_fase_final='AUTOMATICO',dias_sin_riego_confirmados=None,
        fecha_primer_riego_reconocido=None,fecha_primer_cu_pp_valido=None,fecha_ultimo_riego_real=None,
        fecha_ultima_ley_cu_pp=None,proxy_previo_riego=0,transicion_mismo_dia=0,version_modelo='v2',version_alerta='v2')
    with patch.object(phase_db,'snapshot',return_value=[r]) as snapshot,patch.object(phase_panel.phase_flags,'enabled',return_value=True):
        card=phase_panel.diagnostic({'hasta':'2026-10-15'})
    snapshot.assert_called_once_with('2026-10-15')
    nodes=list(components(card))
    selector=next(n for n in nodes if getattr(n,'id',None)=='lix-v2-diagnostic-case')
    assert selector.value is None and selector.clearable is True and len(selector.options)==1
    assert next(n for n in nodes if getattr(n,'id',None)=='lix-v2-diagnostic-rows').data==[r]
    with patch.object(phase_panel,'detail',side_effect=AssertionError('No abrir automáticamente')):
        assert phase_panel.diagnostic_case(None,[r]) is None


def test_selected_case_compares_models_and_full_detail_is_expandable():
    r=dict(row(),fase_visual_legacy='NO_EVALUABLE',estado_operacional_SQL_original='SIN_COBERTURA')
    content=phase_panel.diagnostic_case('0',[r]);text=text_content(content)
    assert 'Resultado calculado: Riego continuo' in text and 'Modelo anterior:' in text
    details=next(n for n in components(content) if type(n).__name__=='Details')
    assert details.open is False and 'Ver detalle operacional completo' in text_content(details)
    assert 'Cu++ drenaje' in text_content(details) and 'Módulos e hitos' in text_content(details)
