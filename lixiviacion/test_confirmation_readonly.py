"""Presentación del permiso existente; sin cambios de autorización o decisión."""
import copy
from unittest.mock import patch
import pytest
from . import phase_panel,phase_db
from .test_ux_governance import row,components,preview
from .test_map import text_content


@pytest.mark.parametrize('data,disabled',[(None,True),({},True),({'ui_can_write':False},True),
    ({'ui_can_write':True},False),({'ui_can_write':1},True),({'ui_can_write':'true'},True)])
def test_all_six_controls_follow_existing_ui_permission_without_mutating_values(data,disabled):
    before=copy.deepcopy(data)
    with patch.object(phase_db,'_actor',side_effect=AssertionError('No volver a autorizar desde presentación')):
        result=phase_panel.form_editability(data)
    assert result[:6]==(disabled,)*6
    assert ('is-readonly' in result[6]) is disabled
    assert data==before


def test_controls_are_disabled_until_preview_and_keep_empty_defaults():
    controls={getattr(c,'id',None):c for c in components(phase_panel.layout()) if isinstance(getattr(c,'id',None),str)}
    for key in ('choice','effective','reason','motive','observation','reference'):
        assert controls['lix-phase-'+key].disabled is True
    assert controls['lix-phase-choice'].value is None and controls['lix-phase-reason'].value is None


def test_readonly_notice_is_non_error_and_keeps_summary_and_history():
    evidence=preview();evidence['context_token']='token';r=evidence['row']
    selected={k:r[k] for k in ('pad_id','parcela_id','campana_id')}
    with patch.object(phase_panel.phase_flags,'enabled',return_value=True),patch.object(phase_db,'preview',return_value=evidence),patch.object(phase_db,'history',return_value=([],[])),patch.object(phase_db,'_actor',side_effect=PermissionError()),patch.object(phase_db,'clean',side_effect=lambda x:dict(x)):
        result=phase_panel.preview_admin(selected,r['fecha'],0)
    assert result[2]['ui_can_write'] is False
    assert result[2]['row']==r
    assert 'Riego continuo' in text_content(result[4])
    assert 'Sin confirmaciones registradas' in text_content(result[5])
    message=text_content(result[6])
    assert 'Modo solo lectura' in message and 'puede revisar confirmaciones' in message
    assert 'no tiene permiso para registrar cambios' in message
    assert result[6].role=='status'
