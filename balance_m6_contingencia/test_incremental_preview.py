"""Referencia incremental: tres escenarios, sin SQL ni persistencia real."""
import json
from pathlib import Path
from unittest.mock import MagicMock,patch
import pytest
from . import service,presentation as ui,panel
from .test_contingencia import row
from .test_presentation import auth,args,source,dump


def flows(value=100.):
    return [dict(Flujo=f'F{i}',Tonelaje=value,Ley_Cu=1.,FCu=value/100) for i in range(1,126)]


def test_case4136_all125_frozen_sql_results():
    path=Path(__file__).resolve().parents[1]/'test_fixtures/contingencia/preview_4136_20261027.json'
    data=json.loads(path.read_text(encoding='utf8'))
    a,b,c=(data[k] for k in ('AUTO','VIGENTE','PROPUESTO'))
    main=service.compare(b,c,'VIGENTE','PROPUESTO')
    assert len(main)==125
    assert [r['Flujo'] for r in main if r['estado']=='CAMBIA']==['F4']
    assert main[3]['delta_Tonelaje']==pytest.approx(-11023.34)
    assert all(before==after for before,after in zip(b,c) if before['Flujo']!='F4')
    residual=lambda rows:rows[8]['Tonelaje']-rows[9]['Tonelaje']-rows[10]['Tonelaje']
    assert residual(a)==pytest.approx(-214361.401543,abs=1e-6)
    assert residual(b)==pytest.approx(-220.321543,abs=1e-6)
    assert residual(c)==residual(b)
    secondary=service.compare(a,b,'AUTO','VIGENTE')
    assert [r['Flujo'] for r in secondary if r['estado']=='CAMBIA']==['F6','F7','F10','F11']
    rendered=dump(ui.impact(main,[dict(delta_TMH=-11306.)],secondary,service.compare(a,c,'AUTO','PROPUESTO')))
    assert all(s in rendered for s in ['1 / 125','Comparación adicional con AUTO técnico','Ver los 125 flujos','11.306,000000','Variación del residual SRR'])


@pytest.mark.parametrize('mode,tum,current,auto,expected',[
    ('TUM',0.,100.,100.,-100.), # cero elegible, sin atribuirlo a planta detenida
    ('TUM',100.,100.,90.,0.), # fuente ya aplicada: ninguna variación
    ('AUTO',20.,20.,80.,60.), # retorno solo de la clave seleccionada
    ('AUTO',20.,80.,80.,0.), # sin decisiones manuales
])
def test_three_scenarios_use_live_locked_values_and_rollback(mode,tum,current,auto,expected):
    r=dict(row(),tum_tmh=tum,valor_vigente=current,valor_auto=auto)
    keys=service.selection([r],[0],mode)
    conn=MagicMock();engine=MagicMock();engine.connect.return_value.__enter__.return_value=conn
    a,b,c=flows(),flows(),flows()
    c[3]['Tonelaje']+=expected
    with patch.object(service,'engine_dev',return_value=engine),patch.object(service.phase_flags,'guard_connection'),patch.object(service,'check_contract'),patch.object(service,'records',return_value=[r]),patch.object(service,'lock_inputs',return_value='B'*64),patch.object(service,'calculate',side_effect=[a,b,c]) as calculate,patch.object(service,'persist') as writer:
        result=service.preview('2026-10-01','2026-10-12',4136,keys)
    assert calculate.call_args_list[0].args==(conn,'2026-10-01','2026-10-12',4136)
    assert calculate.call_args_list[1].kwargs=={'actual':True}
    assert calculate.call_args_list[2].args[-2:]==(keys,True)
    assert result['fuentes_propuestas'][0]['delta_TMH']==expected
    assert sum(r['estado']=='CAMBIA' for r in result['comparacion'])==(expected!=0)
    conn.rollback.assert_called_once();conn.commit.assert_not_called();writer.assert_not_called()


def test_exact_change_is_not_hidden_by_six_decimal_rounding_and_nulls():
    a,b=flows(),flows();b[0]['Tonelaje']+=1e-8;b[1]['Ley_Cu']=None
    rows=service.compare(a,b,'VIGENTE','PROPUESTO')
    assert rows[0]['estado']==rows[1]['estado']=='CAMBIA'
    assert rows[0]['delta_Tonelaje']!=0 and rows[1]['delta_Ley_Cu'] is None


@pytest.mark.parametrize('kind',['duplicate','wrong_code','missing'])
def test_invalid_flow_identity_is_rejected(kind):
    a,b=flows(),flows()
    if kind=='duplicate':b.append(b[0])
    elif kind=='wrong_code':b[-1]['Flujo']='F126'
    else:b.pop()
    with pytest.raises(ValueError,match='125 flujos'):service.compare(a,b)


def test_stale_selected_decision_rejected_before_calculation():
    r=dict(row(),valor_vigente=100.,valor_auto=90.)
    keys=service.selection([r],[0],'AUTO');r['version_m6']+=1
    conn=MagicMock();engine=MagicMock();engine.connect.return_value.__enter__.return_value=conn
    with patch.object(service,'engine_dev',return_value=engine),patch.object(service.phase_flags,'guard_connection'),patch.object(service,'check_contract'),patch.object(service,'records',return_value=[r]),patch.object(service,'lock_inputs',return_value='B'*64),patch.object(service,'calculate') as calculate:
        with pytest.raises(ValueError,match='Cambió una fuente o decisión'):service.preview('2026-10-01','2026-10-12',4136,keys)
    calculate.assert_not_called();conn.rollback.assert_called_once()


def test_changed_unselected_decision_invalidates_confirmation(auth):
    a=args()
    result=dict(comparacion=service.compare(flows(),flows()),huella_entradas='B'*64)
    with patch.object(panel,'ctx') as ctx,patch.object(service,'load_rows',return_value=source()),patch.object(service,'preview',return_value=result),patch.object(service,'persist',side_effect=ValueError('Entradas obsoletas; vuelva a previsualizar.')) as writer:
        ctx.triggered_id='m6ct-preview';a[13]=panel.act(*a)[1];a[14]=['SI']
        ctx.triggered_id='m6ct-guardar';response=panel.act(*a)
    assert response[1] is None and 'vuelva a previsualizar' in dump(response[2])
    assert writer.call_args.args[-1]=='B'*64

