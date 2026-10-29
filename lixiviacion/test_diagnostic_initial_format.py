import copy
import ast
from pathlib import Path
from datetime import date
from decimal import Decimal
from unittest.mock import patch
import pytest
from dash.exceptions import PreventUpdate
from . import panel,callbacks,db
from .test_ux_governance import components
from .test_map import text_content

def rows():
    return [dict(fecha=date(2026,10,19),pad_id=2,flujo=Decimal('0.1'),drenaje=Decimal('0.2'),
        refino=Decimal('0.3'),transferencia=Decimal('-0.0002')),
        dict(fecha=date(2026,10,20),pad_id=2,flujo=Decimal('0.00001'),drenaje=None,
        refino=Decimal('0.3'),transferencia=Decimal('0.000000000000000123'))]

def test_initial_has_no_graphs_or_query_and_blank_kpis():
    with patch.object(db,'overview',side_effect=AssertionError('No consultar')) as query:
        layout=panel.diagnostic_layout()
        nodes=list(components(layout))
        assert not any(type(n).__name__=='Graph' for n in nodes)
        assert panel.INITIAL_MESSAGE in text_content(layout)
        assert all(n.children=='—' for n in nodes if str(getattr(n,'id','')).startswith('lix-kpi-'))
        for clicks in (None,0):
            with pytest.raises(PreventUpdate):callbacks.load(clicks,None,None,None,None,None,None)
        query.assert_not_called()

@pytest.mark.parametrize('parcel,note,title',[(None,panel.CHEMISTRY_MULTI,'Cu drenaje vs refino · promedio por fecha/PAD'),
    (59,panel.CHEMISTRY_SINGLE,'Cu drenaje vs refino · parcela seleccionada')])
def test_applied_selection_controls_note_and_title_without_altering_values(parcel,note,title):
    data=rows();original=copy.deepcopy(data)
    totals=dict(registros=2,flujo=Decimal('0.10001'),transferencia=Decimal('-0.000199999999999877'),delta=Decimal('-0.1'),fuera=2)
    with patch.object(db,'overview',return_value=(totals,data)) as query:
        result=callbacks.load(1,'2026-10-19','2026-10-20',2,None,parcel,'FUERA_VENTANA_RIEGO')
    assert note in text_content(result[4])
    graphs=[n for n in components(result[4]) if type(n).__name__=='Graph']
    assert graphs[1].figure.layout.title.text==title
    assert list(graphs[0].figure.data[0].y)==[0.1,0.00001]
    assert list(graphs[1].figure.data[0].y)==[0.2,None]
    assert list(graphs[2].figure.data[0].y)==[-0.0002,float(data[1]['transferencia'])]
    assert data==original
    query.assert_called_once_with(callbacks.filters('2026-10-19','2026-10-20',2,None,parcel,'FUERA_VENTANA_RIEGO'))
    assert result[:4]==tuple(callbacks.number(totals[k],0 if k=='fuera' else 3) for k in ['flujo','transferencia','delta','fuera'])

def test_transfer_format_is_decimal_and_hover_keeps_physical_unit():
    transfer=callbacks.figures(rows())[2]
    assert transfer.layout.yaxis.tickformat=='.8~r'
    assert transfer.layout.yaxis.showexponent=='none'
    assert '%{y:.8~r} t Cu/d' in transfer.data[0].hovertemplate
    assert transfer.data[0].y[-1]!=0


@pytest.mark.parametrize('parcel',[None,59])
def test_numeric_results_filters_and_graph_values_identical_to_baseline(parcel):
    source=Path(__file__).resolve().parents[1]/'test_fixtures/lixiviacion/diagnostico_fase1/callbacks.py'
    tree=ast.parse(source.read_text(encoding='utf8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('figures','load')]
    for fn in functions:fn.decorator_list=[]
    env=dict(vars(callbacks))
    exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),env)
    totals=dict(registros=2,flujo=Decimal('0.10001'),transferencia=Decimal('-0.000199999999999877'),delta=Decimal('-0.1'),fuera=2)
    data=rows()
    with patch.object(db,'overview',return_value=(totals,data)):
        old=env['load'](1,'2026-10-19','2026-10-20',2,None,parcel,'FUERA_VENTANA_RIEGO')
        new=callbacks.load(1,'2026-10-19','2026-10-20',2,None,parcel,'FUERA_VENTANA_RIEGO')
    assert old[:4]==new[:4] and old[7]==new[5] and old[9]==new[7]
    graphs=[n.figure for n in components(new[4]) if type(n).__name__=='Graph']
    for before,after in zip(old[4:7],graphs):
        assert len(before.data)==len(after.data)
        for a,b in zip(before.data,after.data):
            assert list(a.x)==list(b.x) and list(a.y)==list(b.y) and a.name==b.name
