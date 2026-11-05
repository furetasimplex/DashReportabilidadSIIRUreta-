from unittest.mock import patch
import pandas as pd
import pytest
from . import engine,db_source,modelo_flujos,wet_profile
from .test_module_timeline_intraturno import make_inputs,make_intraday,build_module_timeline

def setup_case():
    day,ap,_,profile=make_inputs(two_modules=False)
    profile['humedad']=0.;profile['fuente']='TEST'
    ap=ap.assign(vol_acum_final=ap.vol_diario,vol_total_est=ap.vol_diario)
    hours=pd.DataFrame({'fecha':[day],'H_op':[10.]})
    target={2:dict(flujo='F19',masa_medida=100.,masa_reconciliada=100.,fino_cu_medido=.5,fino_cu_reconciliado=.5)}
    case=dict(id=10013,run_id=10145,fecha_inicio=day,fecha_fin=day,
              modelo_codigo='hidrometalurgia_125_v2',modelo_version='v2',total_flujos=125)
    return day,ap,profile,hours,target,case

@pytest.mark.parametrize('missing',['error','empty','none'])
def test_optional_10s_failure_keeps_case_mass_and_declares_ab_fallback(missing):
    day,ap,profile,hours,target,case=setup_case()
    loader=dict(side_effect=RuntimeError('SECRET_CONNECTION_DETAILS')) if missing=='error' else dict(return_value=pd.DataFrame() if missing=='empty' else None)
    with patch.object(modelo_flujos,'load_targets',return_value=target), \
         patch.object(modelo_flujos,'load_profile',return_value=profile), \
         patch.object(modelo_flujos,'load_hours',return_value=hours), \
         patch.object(db_source,'load_apilado',return_value=ap), \
         patch.object(wet_profile,'load_intraday_profile',**loader):
        result=engine.analyze_db(fecha_min=day,fecha_max=day,caso=case,caso_id=case['id'],use_intraday=True,metodo='volumen')
    assert result['shift_table'].masa_total.sum()==pytest.approx(100.)
    assert result['module_timeline'].mass_dry.sum()==pytest.approx(100.)
    assert result['module_timeline'].resolucion.str.startswith('interpolacion_uniforme_12h').all()
    assert result['fuente_modelo']['run_id']==10145
    notices=[str(a) for a in result['avisos']]
    assert any('perfil_intraturno_no_disponible' in a for a in notices)
    assert all('SECRET_CONNECTION_DETAILS' not in a for a in notices)

def test_mandatory_profile_error_is_not_suppressed():
    day,ap,profile,hours,target,case=setup_case()
    with patch.object(modelo_flujos,'load_targets',return_value=target), \
         patch.object(modelo_flujos,'load_profile',side_effect=RuntimeError('MANDATORY_PROFILE')), \
         patch.object(modelo_flujos,'load_hours',return_value=hours), \
         patch.object(db_source,'load_apilado',return_value=ap), \
         patch.object(wet_profile,'load_intraday_profile',side_effect=RuntimeError('OPTIONAL')):
        with pytest.raises(RuntimeError,match='MANDATORY_PROFILE'):
            engine.analyze_db(fecha_min=day,fecha_max=day,caso=case,caso_id=case['id'],use_intraday=True,metodo='volumen')

@pytest.mark.parametrize('damage',['day_missing','gap','reset','null','duplicate','bad_total'])
def test_invalid_intraday_uses_ab_with_unchanged_dry_mass(damage):
    day,ap,st,profile=make_inputs()
    raw=make_intraday(day,profile)
    if damage=='day_missing':raw['fecha_op']=day+pd.Timedelta(days=1)
    elif damage=='bad_total':raw.loc[0,'mass_h']+=1.
    else:raw.loc[0,'quality']=damage
    result=build_module_timeline(ap,st,profile,intraday=raw)
    assert result.resolucion.str.startswith('interpolacion_uniforme_12h').all()
    assert result.mass_dry.sum()==pytest.approx(65.)
    assert result.set_index('modulo').loc[5,'end']==day+pd.Timedelta(hours=14)

def test_zero_shift_stays_zero_without_inventing_a_start_before_b():
    day,ap,st,profile=make_inputs()
    profile.loc[profile.turno.eq('A'),'tmh']=0.
    result=build_module_timeline(ap,st,profile,intraday=None)
    assert result.start.min()==day+pd.Timedelta(hours=20)
    assert result.mass_h.sum()==pytest.approx(20.)
    assert result.mass_dry.sum()==pytest.approx(65.)

def test_without_valid_ab_no_clock_is_invented():
    day,ap,st,profile=make_inputs()
    profile.loc[0,'tmh']=float('nan')
    with pytest.raises(ValueError):build_module_timeline(ap,st,profile,intraday=None)
