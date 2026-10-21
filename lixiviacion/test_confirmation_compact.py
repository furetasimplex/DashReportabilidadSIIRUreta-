"""Confirmación compacta: misma evidencia, detalle, permisos y acciones."""
import copy,json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from dash.exceptions import PreventUpdate
from . import phase_panel,map_panel
from .test_map import text_content
from .test_ux_governance import row,components,preview


def test_minimum_context_without_diagnostic_duplication():
    r=row();before=copy.deepcopy(r)
    content=phase_panel.confirmation_summary(r,{'decision':0});text=text_content(content)
    for value in ['Fase automática actual','Riego continuo','Condición actual','Sin información suficiente del día',
                  'Alerta','Información de riego incompleta','Modelo anterior','Ver detalle operacional']:
        assert value in text
    for value in ['Caudal real','Último riego real','Primer riego reconocido','Cu++ drenaje','Último Cu++ positivo',
                  'Primer aporte reconocido','Días sin riego confirmados','Indicador químico','Módulos e hitos']:
        assert value not in text
    assert not any(type(c).__name__=='Table' for c in components(content))
    assert r==before


def test_preview_keeps_identity_date_and_full_unmodified_evidence():
    r=row();p=preview();p.update(context_token='original');p['row']=r
    selected={k:r[k] for k in ('pad_id','parcela_id','campana_id')}
    with patch.object(phase_panel.phase_flags,'enabled',return_value=True),patch.object(phase_panel.phase_db,'preview',return_value=p),patch.object(phase_panel.phase_db,'history',return_value=([],[])),patch.object(phase_panel.phase_db,'_actor',return_value='qa'),patch.object(phase_panel.phase_db,'clean',side_effect=lambda x:dict(x)),patch.object(phase_panel,'detail',side_effect=AssertionError('No duplicar drawer')):
        result=phase_panel.preview_admin(selected,r['fecha'],0)
    for value in ['Óxidos','Parcela 24','Campaña 18','15-10-2026']:assert value in text_content(result[1])
    assert result[2]['row']==r and result[2]['context_token']=='original'
    assert 'Sin confirmaciones registradas' in text_content(result[5])


def test_mixed_has_count_and_link_without_module_table():
    r=dict(row(),fase_calculada_modelo='MIXTO',fase_final='MIXTO',condicion_dia='PAUSA_HIDRAULICA',
           detalle_modulos=json.dumps([{'modulo_id':3},{'modulo_id':4}]))
    content=phase_panel.confirmation_summary(r,{'decision':0})
    for value in ['Mixto','Pausa hidráulica','Módulos con situaciones diferentes: 2','Ver módulos e hitos']:
        assert value in text_content(content)
    assert not any(type(c).__name__=='Table' for c in components(content))


def test_prior_sample_message_is_kept_in_compact_context():
    r=dict(row(),proxy_previo_riego=1)
    assert 'Existe una muestra anterior al primer riego reconocido; no se utiliza para iniciar Riego continuo.' in text_content(phase_panel.confirmation_summary(r,{'decision':0}))


@pytest.mark.parametrize('status',['VIGENTE','CONTRADICHO','APARTADO_ESTRUCTURA'])
def test_real_active_confirmation_is_summarized_and_automatic_phase_stays_automatic(status):
    r=dict(row(),override_id=8,override_status=status,fase_administrativa='DRENAJE_RESIDUAL',
           fase_final='DRENAJE_RESIDUAL',override_desde='2026-10-12',usuario_creacion='qa',motivo_texto='Decisión fixture')
    text=text_content(phase_panel.confirmation_summary(r,{'decision':8}))
    for value in ['Fase automática actual Riego continuo','Confirmación vigente','Drenaje residual','12-10-2026','qa','Decisión fixture']:assert value in text
    if status=='CONTRADICHO':assert 'Se detectó riego posterior' in text and 'Evidencia:' in text


def test_inactive_confirmation_is_not_described_as_current():
    r=dict(row(),override_id=8,override_status='CERRADO_MANUAL')
    assert 'Confirmación vigente' not in text_content(phase_panel.confirmation_summary(r,{'decision':8}))


@pytest.mark.parametrize('section',['overview','modules'])
def test_links_reuse_same_drawer_and_preserve_admin_context(section):
    p=preview();p['row']['fecha']='2026-10-12'
    selected={k:p['row'][k] for k in ('pad_id','parcela_id','campana_id')};before=copy.deepcopy((p,selected))
    with patch.object(map_panel,'ctx',SimpleNamespace(triggered_id={'type':'lix-phase-open-detail','section':section})),patch.object(map_panel.phase_db,'clean',side_effect=lambda x:dict(x)),patch.object(phase_panel,'detail',return_value='same drawer') as detail:
        assert map_panel.open_detail([], '2026-10-15',None,'lix-map-tab',None,[1],p,selected,'2026-10-12')==(True,'same drawer')
    detail.assert_called_once_with(p['row']);assert (p,selected)==before


@pytest.mark.parametrize('change',[{'campana_id':999},{'pad_id':2},{'parcela_id':999},{'fecha':'2026-10-14'}])
def test_stale_context_does_not_open_a_different_campaign_or_date(change):
    p=preview();selected={k:p['row'][k] for k in ('pad_id','parcela_id','campana_id')};p['row'].update(change)
    with patch.object(map_panel,'ctx',SimpleNamespace(triggered_id={'type':'lix-phase-open-detail','section':'overview'})):
        with pytest.raises(PreventUpdate):map_panel.open_detail([], '2026-10-15',None,'lix-map-tab',None,[1],p,selected,'2026-10-15')


def test_history_keeps_administrative_data_without_wide_tables():
    decisions=[dict(version=2,fase_administrativa='ESPERA_RECLAMO',fecha_desde='2026-10-12',
                    fecha_creacion='2026-10-12T12:00:00',usuario_creacion='qa',motivo_texto='Motivo anterior',
                    fecha_fin_drenaje_referencia='2026-10-11',ultima_ley_cu_pp_al_confirmar=.62)]
    events=[dict(tipo_evento='DECISION_RECTIFICADA',fecha_efectiva='2026-10-12',fecha_registro='2026-10-12T12:01:00',actor='qa',motivo='Ajuste documentado')]
    content=phase_panel.history_table(decisions,events)
    for value in ['Versión 2','Espera de reclamo','Motivo anterior','11-10-2026','0,620','Decisión rectificada','Ajuste documentado']:assert value in text_content(content)
    assert not any(type(c).__name__=='Table' for c in components(content))


def test_full_drawer_still_has_all_diagnostic_sections():
    content=text_content(phase_panel.detail(row()))
    for value in ['Fase estructural','Fase calculada','Origen','Días sin riego confirmados','Caudal real','Último riego real',
                  'Primer riego reconocido','Cu++ drenaje','Último Cu++ positivo','Primer aporte reconocido','Modelo anterior','Módulos e hitos']:assert value in content
