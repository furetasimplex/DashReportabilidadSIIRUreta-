"""Separación de la fase no determinada y la condición diaria sin cobertura."""
import copy
from . import phase_model as model,phase_panel,map_panel
from .test_ux_governance import row
from .test_map import text_content


def undetermined():
    return dict(row(),parcela_id=999,numero_parcela=99,campana_id=None,numero_campana=None,
        fase_final='NO_EVALUABLE',fase_calculada_modelo='NO_EVALUABLE',
        condicion_dia='SIN_COBERTURA',origen_fase_final='AUTOMATICO',model_v2=True)


def test_legend_preserves_phase_code_count_order_and_color():
    rows=[undetermined(),dict(undetermined(),fase_final='RIEGO_CONTINUO')]
    before=copy.deepcopy(rows);legend=map_panel.legend(rows)
    keys=[key for key in model.PHASES if key!='SIN_COBERTURA']
    item=legend[keys.index('NO_EVALUABLE')]
    assert text_content(item).strip()=='Fase no determinada 1'
    assert item.children[0].className=='lix-legend-swatch missing'
    assert len(legend)==len(keys) and keys[-1]=='NO_EVALUABLE'
    assert rows==before


def test_drawer_and_confirmation_distinguish_phase_from_daily_condition():
    r=undetermined();before=copy.deepcopy(r)
    for component in (phase_panel.detail(r),phase_panel.confirmation_summary(r,{'decision':0})):
        text=text_content(component)
        assert 'Fase no determinada' in text
        assert 'Sin información suficiente del día' in text
        assert 'Sin información suficiente' not in text.replace('Sin información suficiente del día','')
    assert r==before


def test_tooltip_map_and_diagnostic_use_same_structural_label():
    r=undetermined();before=copy.deepcopy(r)
    tooltip=phase_panel.tooltip(r)
    assert 'Fase: Fase no determinada' in tooltip
    assert 'Condición: Sin información suficiente del día' in tooltip
    assert map_panel.state(r)==('Fase no determinada','missing')
    assert 'Fase no determinada' in text_content(phase_panel.diagnostic_case('0',[r]))
    assert r==before


def test_classifier_keeps_internal_values_and_daily_condition_catalog():
    result=model.calculate('2026-10-19',[],[],[])
    assert result['fase_final']==result['fase_calculada_modelo']=='NO_EVALUABLE'
    assert result['condicion_dia']=='SIN_COBERTURA'
    assert model.CONDITIONS['SIN_COBERTURA']=='Sin información suficiente del día'
    assert 'Fase no determinada' not in result.values()
    assert model.label(result['fase_final'])=='Fase no determinada'
    assert model.label(result['condicion_dia'],model.CONDITIONS)=='Sin información suficiente del día'
