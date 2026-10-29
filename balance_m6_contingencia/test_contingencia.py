"""Contratos sin SQL: alcance, validación y fronteras de confirmación."""
from pathlib import Path
from unittest.mock import patch
import pytest
from dash import Dash
from flask import Flask
from . import service,panel
from .build_sql import EQUIPOS,build,A,V,alter_definition

def row(**kw):
    return dict(fecha_operacional='2026-10-04',turno='A',equipo_codigo='SRR_CV003',tum_disponible=True,tum_tmh=6897,valor_auto=32768,version_m6=0,huella_m6='A'*64,**kw)

def test_scope_and_single_selection():
    assert len(EQUIPOS)==6 and not any('CV025' in x for x in EQUIPOS)
    r=[row(),{**row(),'equipo_codigo':'SRR_CV002'}]
    out=service.selection(r,[0],'TUM')
    assert len(out)==1 and out[0]['equipo_codigo']=='SRR_CV003'
    assert service.selection(r,[1],'AUTO')[0]['modo']=='AUTO'

@pytest.mark.parametrize('value,available',[(None,True),(-1,True),(10,False)])
def test_invalid_tum_is_not_effective(value,available):
    with pytest.raises(ValueError,match='TUM no disponible'):service.selection([{**row(),'tum_tmh':value,'tum_disponible':available}],[0],'TUM')

def test_tum_zero_is_valid_and_no_automatic_global_action():
    assert service.selection([{**row(),'tum_tmh':0}],[0],'TUM')
    with pytest.raises(ValueError):service.selection([row()],[],'TUM')

def test_case_period_and_equipment_boundaries():
    with pytest.raises(ValueError):service.period('2026-10-01','B','2026-10-01','A',list(EQUIPOS))
    with pytest.raises(ValueError):service.period('2026-10-01','A','2026-10-12','B',['RIPIOS_CV025'])
    assert service.period('2026-10-01','A','2026-10-12','B',['SRR_CV002'])

def test_no_sql_at_layout_mount_and_unique_ids():
    with patch.object(service,'engine_dev',side_effect=AssertionError('SQL al montar')),patch('lixiviacion.phase_flags.is_dev',return_value=True):
        tree=panel.layout()
    ids=[]
    def visit(x):
        if isinstance(x,(list,tuple)):
            for y in x:visit(y)
        elif hasattr(x,'to_plotly_json'):
            if getattr(x,'id',None):ids.append(x.id)
            visit(getattr(x,'children',None))
    visit(tree)
    assert len(ids)==len(set(ids)) and all(x.startswith('m6ct-') for x in ids)
    assert len(panel.EXAMPLE)==9 and all('CV001' not in x[2] for x in panel.EXAMPLE)

def test_confirmation_is_bound_to_form_and_selection():
    args=['2026-10-01','A','2026-10-12','B',list(EQUIPOS),4136,[row()],[0],'TUM','Revisado','']
    original=panel.signature(*args)
    args[8]='AUTO';assert panel.signature(*args)!=original
    args[8]='TUM';args[7]=[];assert panel.signature(*args)!=original

def test_sql_minimal_diff_and_retains_ecc_correction(tmp_path):
    p=Path(__file__).resolve().parents[1]/'auditorias/balance_masa_modelo_6/contingencia_manual_m6'
    source=(p/'sp_m6_antes.sql').read_text(encoding='utf8') if (p/'sp_m6_antes.sql').exists() else f'''CREATE PROCEDURE [inventar_SpcHidr].[sp_calcular_balance_flujos_modelo6_v2]
@fecha_inicio date,@fecha_fin date,@caso_id int=NULL,@debug bit = 0 AS BEGIN
    DECLARE @ff_mas_1 date = DATEADD(day,1,@fecha_fin);
SELECT 'ep_ecc1_gl ep_ecc2_gl';SELECT * FROM {A}; SELECT * FROM {A}; END;'''
    (tmp_path/'sp_m6_antes.sql').write_text(source,encoding='utf8');build(tmp_path)
    altered=(tmp_path/'03_alter_m6.sql').read_text(encoding='utf8')
    assert altered==alter_definition(source.replace(A,V)) and source.count(A)==2
    assert 'ep_ecc1_gl' in altered and 'ep_ecc2_gl' in altered
    assert 'contingencia_pi_accion_test' not in altered
    assert '51109' in (tmp_path/'02_crear_capa_m6.sql').read_text(encoding='utf8')

def test_ui_cannot_persist_without_confirmation_or_with_changed_form():
    server=Flask(__name__);server.secret_key='unit-test-only'
    with server.test_request_context('/'):
        from flask import session
        session['user']='tester'
        # Missing confirmation is checked before any persistence call.
        with patch.object(service,'period'),patch.object(service,'persist',side_effect=AssertionError('persist called')),patch.object(panel,'ctx') as context:
            context.triggered_id='m6ct-guardar'
            result=panel.act(None,1,'2026-10-01','A','2026-10-12','B',list(EQUIPOS),4136,[row()],[0],'TUM','motivo','',None,[])
            assert result[1] is None
            assert 'confirmación' in str(result[2])
            result=panel.act(None,1,'2026-10-01','A','2026-10-12','B',list(EQUIPOS),4136,[row()],[0],'TUM','motivo','',None,['SI'])
            assert 'Preview vencido' in str(result[2])

def test_nine_rows_preview_then_explicit_confirmation_without_sql():
    server=Flask(__name__);server.secret_key='test-only'
    source=[{**row(),'fecha_operacional':d,'turno':t,'equipo_codigo':e,'pi_tmh':32768} for d,t,e in sorted(panel.EXAMPLE)]
    a=[dict(Flujo=f'F{i}',Tonelaje=100.0,Ley_Cu=1.0,FCu=1.0) for i in range(1,126)]
    b=[dict(r) for r in a];b[9]['Tonelaje']=90.0
    comparison=service.compare(a,b)
    with server.test_request_context('/'):
        from flask import session
        session['user']='tester'
        with patch.object(service,'load_rows',return_value=source),patch.object(service,'preview',return_value={'comparacion':comparison,'huella_entradas':'B'*64}),patch.object(service,'persist') as persist,patch.object(panel,'ctx') as context:
            args=[1,None,'2026-10-01','A','2026-10-12','B',list(EQUIPOS),4136,source,list(range(9)),'TUM','Motivo revisado','',None,[]]
            context.triggered_id='m6ct-preview'
            rendered,token,_,confirmation=panel.act(*args)
            persist.assert_not_called();assert token and confirmation==[]
            from plotly.utils import PlotlyJSONEncoder
            import json
            assert 'Impacto en el inventario del silo' in json.dumps(rendered,cls=PlotlyJSONEncoder)
            context.triggered_id='m6ct-guardar';args[13]=token;args[14]=['SI']
            result=panel.act(*args)
            persist.assert_called_once();assert len(persist.call_args.args[0])==9
            assert persist.call_args.args[5]=='B'*64
            assert all(k['equipo_codigo']!='SRR_CV001' for k in persist.call_args.args[0])
            assert result[1] is None and result[3]==[]

def test_host_navigation_callback_has_matching_inputs_and_outputs():
    import ast
    source=Path(__file__).resolve().parents[1]/'layout.py'
    tree=ast.parse(source.read_text(encoding='utf8'))
    fn=next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name=='toggle_subtabs')
    decorator=fn.decorator_list[0]
    calls=[x for x in decorator.args if isinstance(x,ast.Call)]
    input_count=sum(isinstance(x.func,ast.Name) and x.func.id in ('Input','State') for x in calls)
    output_count=sum(isinstance(x.func,ast.Name) and x.func.id=='Output' for x in calls)
    assert len(fn.args.args)==input_count
    result=next(x.value for x in ast.walk(fn) if isinstance(x,ast.Return) and isinstance(x.value,ast.Tuple))
    assert len(result.elts)==output_count
    assert 'nav-balance-m6' in source.read_text(encoding='utf8')

def test_generated_auto_has_original_technical_quality_and_no_operational_override():
    from .build_sql import AUTO
    source=(Path(__file__).parent/'sql/auto_tecnico.sql').read_text(encoding='utf8')
    assert AUTO in source and 'estado_equipo_turno' not in source and 'FUERA_SERVICIO' not in source
    assert 'SIN_CAMBIO' not in source or "THEN 'TUM'" in source
    assert 'FRONTERAS_COMPLETAS' in source and 'CON_VARIACION_COBERTURA_PARCIAL' in source

def test_regenerating_an_installed_m6_preserves_its_source_and_rollback(tmp_path):
    source='''CREATE PROCEDURE [inventar_SpcHidr].[sp_calcular_balance_flujos_modelo6_v2]
@fecha_inicio date,@fecha_fin date,@caso_id int=NULL,@debug bit = 0 AS BEGIN
    DECLARE @ff_mas_1 date = DATEADD(day,1,@fecha_fin);
SELECT * FROM SOURCE; SELECT * FROM SOURCE; END;'''.replace('SOURCE',V)
    (tmp_path/'sp_m6_antes.sql').write_text(source,encoding='utf8')
    result=build(tmp_path)
    assert result['cambios_fuente']==0
    assert 'ALTER PROCEDURE' not in (tmp_path/'03_alter_m6.sql').read_text(encoding='utf8')
    rollback=(tmp_path/'09_rollback_m6.sql').read_text(encoding='utf8')
    assert rollback.count(V)==2 and A not in rollback

def test_persistence_requires_full_preview_guard_before_any_sql():
    with patch.object(service,'engine_dev',side_effect=AssertionError('No conectar sin preview')):
        with pytest.raises(ValueError,match='Preview válido'):
            service.persist([], '00000000-0000-0000-0000-000000000001','tester','motivo','',None)

def test_preview_locks_three_calculations_and_releases_on_failure():
    from unittest.mock import MagicMock
    connection=MagicMock();engine=MagicMock();engine.connect.return_value.__enter__.return_value=connection
    r=row();r.update(pi_tmh=32768)
    keys=service.selection([r],[0],'TUM')
    current=[{**r,'valor_vigente':100.,'valor_auto':100.}]
    order=[]
    with patch.object(service,'engine_dev',return_value=engine),patch.object(service.phase_flags,'guard_connection'),patch.object(service,'check_contract'),patch.object(service,'records',return_value=current),patch.object(service,'lock_inputs',side_effect=lambda c,*args:order.append('verify' if args else 'lock') or 'B'*64),patch.object(service,'calculate',side_effect=lambda *args,**kwargs:order.append('calculate') or []),patch.object(service,'compare',return_value=[]):
        out=service.preview('2026-10-01','2026-10-12',4136,keys)
    assert out['huella_entradas']=='B'*64 and order==['lock','calculate','calculate','calculate','verify']
    connection.rollback.assert_called_once()
    order=[];connection.reset_mock()
    with patch.object(service,'engine_dev',return_value=engine),patch.object(service.phase_flags,'guard_connection'),patch.object(service,'check_contract'),patch.object(service,'lock_inputs',side_effect=ValueError('Entrada modificada')),patch.object(service,'calculate') as calc:
        with pytest.raises(ValueError):service.preview('2026-10-01','2026-10-12',4136,keys)
        calc.assert_not_called()
    connection.rollback.assert_called_once()
