"""Dos niveles accesibles sin modificar metadata ni reglas de descarga."""
import json
from report_export.callbacks import reportabilidad_cb as cb
from report_export.tests.test_balance_interfaz import status
from report_export.layouts.reportabilidad_page import _report_card

def test_detalle_principal_y_avanzado_cerrados_independientes():
    raw={'solver_converged':False,'officializable':False,'warning_message':'Advertencia técnica original',
         'solver_mode':'hidrometalurgia_125','persisted_results':125,'dato_futuro':{'valor':None}}
    s=status(solver_metadata_json=json.dumps(raw),observacion_solver='Otra observación original')
    before=dict(s)
    detail=cb._balance_solver_detail(s).children[1]
    assert detail.open is False
    fields=detail.children[2]
    assert [item.children[0].children for item in fields.children]==['Estado registrado','solver_converged','officializable','Advertencia técnica']
    advanced=detail.children[3]
    assert advanced.open is False
    assert advanced.children[0].children=='Mostrar metadatos avanzados'
    labels=[item.children[0].children for item in advanced.children[1].children]
    assert labels==['Observación disponible','solver_mode','persisted_results','dato_futuro']
    assert s==before and json.loads(s['solver_metadata_json'])==raw

def test_selector_altura_compacta_con_mismos_ids():
    def walk(c):
        if isinstance(c,list):
            for item in c:yield from walk(item)
        elif hasattr(c,'to_plotly_json'):
            yield c
            yield from walk(getattr(c,'children',None))
    selector=next(c for c in walk(_report_card('Balance Semanal','Descripción','balance')) if getattr(c,'id',None)=='report-balance-caso')
    assert selector.optionHeight==38 and selector.maxHeight==240
    assert not selector.clearable and selector.className=='rp-balance-selector'
