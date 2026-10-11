from contextlib import contextmanager
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from . import map_db, map_panel
from .test_map import fixture_rows, text_content


def test_parameterized_module_helper():
    calls=[]
    class Conn:
        def execute(self,sql,params):
            calls.append((str(sql),params))
            return SimpleNamespace(mappings=lambda: [])
    @contextmanager
    def connection(): yield Conn()
    with patch.object(map_db,'_connection',connection):
        assert map_db.fetch_modulos_parcela('2026-09-10',2,33)==[]
    sql,params=calls[0]
    assert params=={'fecha':date(2026,9,10),'pad_id':2,'parcela_id':33}
    assert len(calls)==1 and '2026' not in sql
    assert ':fecha, :pad_id, :parcela_id' in sql
    assert 'fn_estado_operacional_modulo_diario(' in sql
    assert 'COALESCE(secuencia_carguio, 999999), nombre_modulo' in sql
    assert 'riego' not in sql and 'drenaje' not in sql


@pytest.mark.parametrize('names,states,labels',[
    ([57,58],['REPOSO_PRE_RECLAMO']*2,['Espera de reclamo']*2),
    ([33,34],['CONFORMADO_PRE_RIEGO','APILADO'],['Conformado / espera de riego','Apilado']),
    ([1,2,3,4,5],['RECLAMADO']*4+['RECLAMO'],['Reclamado']*4+['Reclamo']),
])
def test_real_names_and_labels(names,states,labels):
    r=fixture_rows()[0]
    r.update(fase_visual='MIXTO',estado_operacional='MIXTO',modulos_total=len(names),estados_distintos=2,
             composicion_modulos='ORIGINAL INTACTO')
    modules=[dict(nombre_modulo=n,modulo_id=n+1000,estado_modulo=s) for n,s in zip(names,states)]
    output=text_content(map_panel.detail(r,modules))
    for n,label in zip(names,labels):
        assert f'M{n}' in output and label in output
        assert f'M{n+1000}' not in output
    assert 'Composición' not in output
    assert 'Inconsistencia' not in output
    assert r['composicion_modulos']=='ORIGINAL INTACTO'


def test_empty_and_mismatch_no_fabrication():
    row=dict(modulos_total=2)
    empty=text_content(map_panel.modules_table(row,[]))
    assert 'Sin detalle de módulos disponible.' in empty and 'Inconsistencia' in empty
    one=text_content(map_panel.modules_table(row,[dict(nombre_modulo=57,estado_modulo='REPOSO_PRE_RECLAMO')]))
    assert 'Inconsistencia' in one and 'M57' in one and 'M58' not in one


def test_fetch_only_click_and_failure_does_not_break_drawer():
    row=fixture_rows()[0]
    row.update(fase_visual='NO_EVALUABLE',modulos_total=2)
    data={'fecha':'2026-09-10','rows':[row]}
    for trigger in ('lix-map-date','lix-map-pad','lix-map-data','lix-tabs'):
        with patch.object(map_panel,'ctx',SimpleNamespace(triggered_id=trigger)), patch.object(map_db,'fetch_modulos_parcela') as fetch:
            assert map_panel.open_detail([1],'2026-09-10',None,'lix-map-tab',data)==(False,None)
            fetch.assert_not_called()
    with patch.object(map_panel,'ctx',SimpleNamespace(triggered_id={'type':'lix-parcel','pad':1,'parcel':1})), \
         patch.object(map_db,'fetch_modulos_parcela',side_effect=RuntimeError('unavailable')) as fetch:
        opened,content=map_panel.open_detail([1],'2026-09-10',None,'lix-map-tab',data)
        assert opened and 'No fue posible cargar el detalle de módulos.' in text_content(content)
        fetch.assert_called_once_with('2026-09-10',1,1)
    assert 'modules' not in data and len(data['rows'])==1
