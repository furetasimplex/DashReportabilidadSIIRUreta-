import ast
import copy
import json
import uuid
from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

from ajuste_reporte import rep_prod_adjuster as writer
from ajuste_reporte.m6_targets import M6ValidationError, select_solver_model

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def snapshot():
    return json.loads((ROOT/'test_fixtures/ajuste_reporte/m6_10009_10082.json').read_text(encoding='utf8'))


@pytest.fixture(autouse=True)
def no_writes_or_connections(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail('La prueba intento conectar o escribir/publicar')
    monkeypatch.setattr(writer, 'get_engine', forbidden)
    monkeypatch.setattr(writer, 'exec_sql', forbidden)
    monkeypatch.setattr(writer, 'write_staging', forbidden)
    monkeypatch.setattr(pd.DataFrame, 'to_sql', forbidden)


def inputs(snapshot):
    return (pd.DataFrame(snapshot['results']), pd.DataFrame(snapshot['catalog']),
            snapshot['context'], pd.DataFrame(snapshot['daily']), pd.DataFrame(snapshot['rules']))


def prepare(snapshot, **kwargs):
    return writer.prepare_ajuste_m6_125(*inputs(snapshot), **kwargs)


def test_regression_m6_10009_10082(snapshot):
    original = copy.deepcopy(snapshot)
    result = prepare(snapshot)
    data = result['datos']
    assert result['targets']['F08F09_MASA'] == 77148.856848
    assert result['targets']['F08F09_FCU'] == 312.067403
    assert data.SRR_TMS_promedio_dia.sum() == pytest.approx(77148.856848, abs=1e-8)
    assert (data.SRR_TMS_promedio_dia*data.Ley_CuT_Real_srr/100).sum() == pytest.approx(312.067403, abs=1e-8)
    assert data.Apilado_TMS_Real.sum() == pytest.approx(269177.274180, abs=1e-8)
    assert (data.Apilado_TMS_Real*data.Ley_CuT_Real/100).sum() == pytest.approx(1558.784652, abs=1e-8)
    assert len(result['columnas_heredadas']) == 28
    assert len(result['columnas_ajustadas']) == 19
    source = pd.DataFrame(snapshot['daily'])
    pd.testing.assert_frame_equal(data[result['columnas_heredadas']], source[result['columnas_heredadas']])
    assert snapshot == original
    assert result['solver_run_id'] == 10082
    assert isinstance(uuid.UUID(result['run_id']), uuid.UUID)
    assert result['persistido'] is result['publicable'] is False
    codes = {d['codigo'] for d in result['diagnosticos']}
    assert {'CONTRASTE_BRUTO_ASIGNADO','TOTAL_HEREDADO_INCOMPATIBLE','LEY_NULL_SIN_MASA'} <= codes
    diagnostic = next(d for d in result['diagnosticos'] if d['codigo']=='CONTRASTE_BRUTO_ASIGNADO')
    assert diagnostic['diferencia_masa'] == pytest.approx(.04344, abs=1e-8)


@pytest.mark.parametrize('mutation,code', [
    ('missing','FLUJOS_INCOMPLETOS_DUPLICADOS'), ('duplicate','FLUJOS_INCOMPLETOS_DUPLICADOS'),
    ('catalog_duplicate','FLUJOS_INCOMPLETOS_DUPLICADOS'), ('foreign_case','RESULTADOS_OTRO_CASO_RUN'),
    ('foreign_run','RESULTADOS_OTRO_CASO_RUN'), ('foreign_model','CATALOGO_MODELO_INCORRECTO'),
    ('foreign_key','RESULTADO_CATALOGO_INCOHERENTE'), ('null_target','VALOR_AUSENTE'),
    ('infinite_target','VALOR_NO_FINITO'), ('negative_target','OBJETIVO_FISICO_INVALIDO'),
    ('fine_without_mass','OBJETIVO_FISICO_INVALIDO'), ('wrong_legacy','CONTRATO_MODELO_INVALIDO'),
    ('run_case','CASO_RUN_INCOHERENTE'), ('uuid_solver','IDENTIFICADOR_INVALIDO'),
])
def test_bad_solver_contract(snapshot, mutation, code):
    if mutation=='missing':snapshot['results'].pop()
    elif mutation=='duplicate':snapshot['results'][-1]=copy.deepcopy(snapshot['results'][0])
    elif mutation=='catalog_duplicate':snapshot['catalog'][-1]=copy.deepcopy(snapshot['catalog'][0])
    elif mutation=='foreign_case':snapshot['results'][0]['caso_id']=10013
    elif mutation=='foreign_run':snapshot['results'][0]['run_id']=10145
    elif mutation=='foreign_model':snapshot['catalog'][0]['modelo_id']=6
    elif mutation=='foreign_key':snapshot['results'][0]['flujo_modelo_id']=-1
    elif mutation in {'null_target','infinite_target','negative_target','fine_without_mass'}:
        row=next(r for r in snapshot['results'] if r['codigo_flujo']=='F9')
        row['masa_reconciliada']={'null_target':None,'infinite_target':float('inf'),'negative_target':-1,'fine_without_mass':0}[mutation]
    elif mutation=='wrong_legacy':snapshot['context']['legacy_modelo_id']=2
    elif mutation=='run_case':snapshot['context']['run_caso_id']=10013
    elif mutation=='uuid_solver':snapshot['context']['solver_run_id']=str(uuid.uuid4())
    with pytest.raises(M6ValidationError, match=code):prepare(snapshot)


@pytest.mark.parametrize('mutation,code', [
    ('missing_date','COBERTURA_INCOMPLETA'), ('duplicate_date','FECHAS_INVALIDAS_DUPLICADAS'),
    ('invalid_date','FECHAS_INVALIDAS_DUPLICADAS'), ('outside','COBERTURA_INCOMPLETA'),
    ('zero_base','TARGET_SIN_BASE'), ('null_base','VALOR_AUSENTE'),
    ('negative_weight','PERFIL_NEGATIVO'), ('null_weight','VALOR_AUSENTE'),
    ('zero_pair','PAREJA_SIN_BASE'), ('zero_turns','TURNOS_NO_DISTRIBUIBLES'),
    ('grade_missing_with_mass','VALOR_AUSENTE'), ('grade_over_100','LEY_INVALIDA'),
    ('humidity_missing','VALOR_AUSENTE'), ('humidity_invalid','HUMEDAD_INVALIDA'),
    ('rules_order','ORDEN_REGLAS_INVALIDO'),
])
def test_bad_daily_profiles(snapshot, mutation, code):
    if mutation=='missing_date':snapshot['daily'].pop()
    elif mutation=='duplicate_date':snapshot['daily'].append(copy.deepcopy(snapshot['daily'][0]))
    elif mutation=='invalid_date':snapshot['daily'][0]['Fecha']='bad'
    elif mutation=='outside':snapshot['daily'][0]['Fecha']='2026-08-31'
    elif mutation=='zero_base':
        for row in snapshot['daily']:row['Chancado_TMS_Real']=0
    elif mutation=='null_base':snapshot['daily'][0]['Chancado_TMS_Real']=None
    elif mutation=='negative_weight':snapshot['daily'][0]['Sal_turno_A']=-1
    elif mutation=='null_weight':snapshot['daily'][0]['Sal_turno_A']=None
    elif mutation=='zero_pair':
        for row in snapshot['daily']:row['Sal_turno_A']=row['Sal_Turno_B']=0
    elif mutation=='zero_turns':snapshot['daily'][0]['Apilado_TMH_turno_A']=snapshot['daily'][0]['Apilado_TMH_turno_B']=0
    elif mutation=='grade_missing_with_mass':snapshot['daily'][0]['Ley_CuT_Real_srr']=None
    elif mutation=='grade_over_100':snapshot['daily'][0]['Ley_CuT_Real_srr']=101
    elif mutation=='humidity_missing':snapshot['daily'][0]['Humedad_promedio_dia']=None
    elif mutation=='humidity_invalid':snapshot['daily'][0]['Humedad_promedio_dia']=101
    elif mutation=='rules_order':snapshot['rules'].reverse()
    with pytest.raises(M6ValidationError, match=code):prepare(snapshot)


def test_srr_uses_f9_not_branches(snapshot):
    target = writer.build_targets_m6_125(*inputs(snapshot)[:3])
    for row in snapshot['results']:
        if row['codigo_flujo'] in {'F10','F11'}:
            row['masa_reconciliada']=999999;row['fino_cu_reconciliado']=1000
    assert writer.build_targets_m6_125(*inputs(snapshot)[:3]) == target


def test_zero_base_zero_target_compatible(snapshot):
    result=prepare(snapshot)
    assert result['targets']['F22__MASA'] == 0
    assert result['datos'].Camiones_TMS_Reclamo_Oxidos.sum() == 0
    assert result['factores']['factor_Camiones_TMS_Reclamo_Oxidos'] == 1


def test_both_pads_allow_total_block_unobserved_split(snapshot):
    rows={r['codigo_flujo']:r for r in snapshot['results']}
    for field in ['masa_reconciliada','fino_cu_reconciliado']:
        total=rows['F18'][field]+rows['F19'][field]
        rows['F18'][field]=.4*total;rows['F19'][field]=.6*total
    result=prepare(snapshot)
    diagnostic=next(d for d in result['diagnosticos'] if d['codigo']=='DETALLE_PAD_NO_VERIFICABLE')
    assert diagnostic['ambos_PAD_con_target_positivo']
    assert result['datos'].Apilado_TMS_Real.sum() == pytest.approx(269177.274180)
    with pytest.raises(M6ValidationError, match='DETALLE_PAD_NO_DISPONIBLE'):
        prepare(snapshot,require_pad_distribution=True)


def test_post_validation_rejects_lost_mass(snapshot,monkeypatch):
    original=writer.apply_rules
    def broken(data,rules,targets):
        out,factors=original(data,rules,targets)
        if rules.iloc[0]['col_nombre']=='Chancado_TMS_Real':out.loc[out.index[0],'Chancado_TMS_Real']+=10
        return out,factors
    monkeypatch.setattr(writer,'apply_rules',broken)
    with pytest.raises(M6ValidationError,match='NO_CONSERVA_TARGET'):prepare(snapshot)


def test_legacy_120_targets_remain_historical(snapshot,monkeypatch):
    context=dict(snapshot['context'],modelo_id=1,modelo_codigo='hidrometalurgia_120_completo',legacy_modelo_id=1,total_flujos=120)
    assert select_solver_model(context)=='legacy_120'
    frame=pd.DataFrame([dict(codigo_flujo=f'F{i}',masa_reconciliada=float(i),fino_cu_reconciliado=i/100) for i in range(1,121)])
    monkeypatch.setattr(writer,'get_solver_model_context',lambda *a:context)
    monkeypatch.setattr(writer,'read_sql_df',lambda *a,**kw:frame)
    engine=Mock();engine.begin.side_effect=AssertionError('No persistir')
    actual=writer.build_targets_from_solver_nuevo(engine,10009,10082,persist=False)
    assert actual==pytest.approx({'F3':3.,'F10F11_MASA':21.,'F14F15_MASA':29.,'F14F15_FCU':.29,
                    'F19__MASA':19.,'F18__MASA':18.,'F21__MASA':21.,'F22__MASA':22.,
                    'F08F09_MASA':17.,'F08F09_FCU':.17,'F08F09_LEY_CU':1.})
    engine.begin.assert_not_called()


def test_m6_dispatch_no_persistence(snapshot,monkeypatch):
    frame,catalog,context,*_=inputs(snapshot)
    engine=Mock();engine.begin.side_effect=AssertionError('No persistir')
    monkeypatch.setattr(writer,'get_solver_model_context',lambda *a:context)
    monkeypatch.setattr(writer,'_read_m6_result_catalog',lambda *a:(frame,catalog))
    with pytest.raises(M6ValidationError,match='PERSISTENCIA_M6_BLOQUEADA'):
        writer.build_targets_from_solver_nuevo(engine,10009,10082)
    assert writer.build_targets_from_solver_nuevo(engine,10009,10082,persist=False)['F08F09_MASA']==77148.856848
    monkeypatch.setattr(writer,'get_engine',lambda:engine)
    with pytest.raises(M6ValidationError,match='PERSISTENCIA_M6_BLOQUEADA'):
        writer.run_ajuste_reporte_prod_solver_nuevo(10009)
    preview=Mock(return_value={'modo':'prueba_sin_persistencia','publicable':False})
    monkeypatch.setattr(writer,'preview_m6_from_solver',preview)
    assert not writer.run_ajuste_reporte_prod_solver_nuevo(10009,dry_run=True)['publicable']
    preview.assert_called_once_with(engine,10009,10082)
    engine.begin.assert_not_called()


def test_m6_publication_remains_blocked(monkeypatch):
    engine=Mock();engine.begin.side_effect=AssertionError('No publicar')
    monkeypatch.setattr(writer,'get_engine',lambda:engine)
    monkeypatch.setattr(writer,'read_sql_df',lambda *a,**kw:pd.DataFrame([{'codigo':'hidrometalurgia_125_v2'}]))
    with pytest.raises(M6ValidationError,match='PUBLICACION_M6_BLOQUEADA'):
        writer.publicar_run_oficial(10009,str(uuid.uuid4()),'prueba')
    engine.begin.assert_not_called()


def test_rejects_daily_copper_loss_even_if_period_total_is_same(snapshot,monkeypatch):
    original=writer.apply_rules
    def broken(data,rules,targets):
        out,factors=original(data,rules,targets)
        if rules.iloc[0]['tipo_regla']=='DERIVED_SAFE_RATIO':
            out.loc[out.index[0],'Cobre_fino_Apilado_Real']+=1
            out.loc[out.index[4],'Cobre_fino_Apilado_Real']-=1
        return out,factors
    monkeypatch.setattr(writer,'apply_rules',broken)
    with pytest.raises(M6ValidationError,match='diario'):prepare(snapshot)


def test_inherited_change_is_rejected(snapshot,monkeypatch):
    original=writer.apply_rules
    def broken(data,rules,targets):
        out,factors=original(data,rules,targets)
        if rules.iloc[0]['tipo_regla']=='DERIVED_SAFE_RATIO':out['Camiones_TMS_total']+=1
        return out,factors
    monkeypatch.setattr(writer,'apply_rules',broken)
    with pytest.raises(M6ValidationError,match='HEREDADA_ALTERADA'):prepare(snapshot)


def test_null_inherited_total_is_preserved_and_diagnosed(snapshot):
    snapshot['daily'][0]['Camiones_TMS_total']=None
    result=prepare(snapshot)
    assert pd.isna(result['datos'].iloc[0]['Camiones_TMS_total'])
    assert any(d['codigo']=='NULL_HEREDADO_CONSERVADO' and d['columna']=='Camiones_TMS_total' for d in result['diagnosticos'])


def test_existing_srr_zero_fine_fallback_is_explicit(snapshot):
    for row in snapshot['daily']:row['Ley_CuT_Real_srr']=0
    result=prepare(snapshot)
    assert any(d['codigo']=='FINOS_BASE_CERO' for d in result['diagnosticos'])
    data=result['datos']
    assert (data.SRR_TMS_promedio_dia*data.Ley_CuT_Real_srr/100).sum()==pytest.approx(312.067403,abs=1e-8)


def test_no_rule_may_start_adjusting_an_inherited_column(snapshot):
    snapshot['rules'].append(dict(regla_id=999,orden_calculo=100,tipo_regla='DERIVED',col_nombre='Camiones_TMS_total',
                                 formula_py='Camiones_TMS_Reclamo_Oxidos+Camiones_TMS_Reclamo_Sulfuros',params_json=None,target_code=None))
    with pytest.raises(M6ValidationError,match='HEREDADA_NO_AUTORIZADA'):prepare(snapshot)


def test_model_context_reader_requires_coherent_case_run(snapshot,monkeypatch):
    context=copy.deepcopy(snapshot['context']);context['run_caso_id']=10013
    def select_only(engine,sql,params):
        assert sql.lstrip().startswith('SELECT')
        assert params=={'caso_id':10009,'solver_run_id':10082}
        return pd.DataFrame([context])
    monkeypatch.setattr(writer,'read_sql_df',select_only)
    with pytest.raises(M6ValidationError,match='CASO_RUN_INCOHERENTE'):
        writer.get_solver_model_context(Mock(),10009,10082)


def test_adjustment_uuid_is_not_solver_run(snapshot):
    with pytest.raises(M6ValidationError,match='UUID_AJUSTE_INVALIDO'):
        prepare(snapshot,adjustment_run_id=10082)
