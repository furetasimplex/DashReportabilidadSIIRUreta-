from datetime import date
from decimal import Decimal
from unittest.mock import patch
from contextlib import contextmanager
import pytest
from dash import Dash, html
from . import db, panel, callbacks


def test_null_zero_and_transfer_are_not_recomputed():
    rows = [dict(fecha=date(2026,9,1),pad_id=1,flujo=Decimal('10'),drenaje=None,refino=Decimal('0'),transferencia=None),
            dict(fecha=date(2026,9,2),pad_id=1,flujo=Decimal('20'),drenaje=Decimal('0'),refino=None,transferencia=Decimal('17'))]
    flow, chem, cu = callbacks.figures(rows)
    assert list(chem.data[0].y) == [None, 0.0]
    assert list(chem.data[1].y) == [0.0, None]
    assert list(cu.data[0].y) == [None, 17.0]
    assert rows[0]['drenaje'] is None


def test_chemical_labels_and_initial_period():
    rows = [dict(fecha=date(2026, 6, 1), pad_id=1, flujo=1,
                 drenaje=None, refino=0, transferencia=None)]
    chemistry = callbacks.figures(rows)[1]
    assert chemistry.data[0].name.endswith('Cu drenaje promedio [g/L]')
    assert chemistry.data[1].name.endswith('Cu refino promedio [g/L]')
    assert callbacks.delta_label(None) == 'ΔCu promedio parcelas [g/L]'
    assert callbacks.delta_label({'parcela': 1}) == 'ΔCu promedio [g/L]'
    assert 'promedio' not in callbacks.figures(rows, single_parcel=True)[1].data[0].name
    def descendants(component):
        yield component
        children = getattr(component, 'children', [])
        for child in children if isinstance(children, (list, tuple)) else [children]:
            yield from descendants(child)
    picker = next(c for c in descendants(panel.layout()) if getattr(c, 'id', None) == 'lix-fechas')
    assert (picker.start_date, picker.end_date) == ('2026-06-01', '2026-09-10')


def test_filters_parameterized_and_null_campaign_kept():
    w, args = db.where(dict(desde='2026-06-01',hasta='2026-09-10',estado='FUERA_VENTANA_RIEGO'))
    assert 'campana_id =' not in w
    assert args['estado'] == 'FUERA_VENTANA_RIEGO'
    clauses, params = db.table_predicate('{pad} contains "x\'; DROP TABLE t;--"')
    assert 'DROP' not in clauses[0] and 'DROP' in params['tf0']
    with pytest.raises(ValueError):
        db.table_predicate('{password} = 1')
    with pytest.raises(ValueError):
        db.where(dict(desde='2026-09-10',hasta='2026-06-01'))


def test_empty_or_failed_queries_clear_previous_results():
    with patch.object(db, 'overview', return_value=(dict(registros=0,flujo=None,transferencia=None,delta=None,fuera=0), [])):
        result=callbacks.load(1,'2026-06-01','2026-09-10',None,None,None,None)
        assert result[0:3] == ('Sin dato',)*3
    with patch.object(db, 'overview', side_effect=ValueError('Fechas inválidas')):
        result=callbacks.load(1,None,None,None,None,None,None)
        assert result[7] is None and result[0] == '—'


def test_panel_registers_without_connecting():
    with patch.object(db, '_connection', side_effect=AssertionError('Unexpected DB')):
        app=Dash(__name__)
        app.layout=html.Div(panel.layout(),id='subtabs-lixiviacion',style={'display':'none'})
        response=app.server.test_client().get('/_dash-layout')
        assert response.status_code == 200
        assert b'lix-tabla' in response.data
        assert len(app.callback_map) >= 3


def test_table_backend_page_and_injection_protection():
    calls = []
    class Result:
        def scalar_one(self):
            return 60
        def mappings(self):
            return iter([dict(fecha=date(2026,9,1),cu_drenaje_gl=None)])
    class Conn:
        def execute(self, statement, params):
            calls.append((str(statement), dict(params)))
            return Result()
    @contextmanager
    def connect():
        yield Conn()
    with patch.object(db, '_connection', connect):
        rows, count, page = db.detail(dict(desde='2026-06-01',hasta='2026-09-10'),
            page=99, sort_by=[dict(column_id='delta_cu_gl',direction='desc')],
            filter_query='{pad} contains "x\'; DROP TABLE t;--"')
    assert count == 60 and page == 2
    assert calls[1][1]['offset'] == 50 and calls[1][1]['size'] == 25
    assert 'DROP' not in calls[1][0]
    assert 'OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY' in calls[1][0]
    assert rows[0]['cu_drenaje_gl'] is None


def test_sidebar_keeps_all_existing_sections_and_new_one():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    source=ast.parse(Path('layout.py').read_text(encoding='utf-8'))
    toggle=next(n for n in ast.walk(source) if isinstance(n,ast.FunctionDef) and n.name=='toggle_subtabs')
    toggle.decorator_list=[]
    module=ast.fix_missing_locations(ast.Module(body=[toggle],type_ignores=[]))
    context=SimpleNamespace(triggered_id=None)
    namespace={'dash': SimpleNamespace(ctx=context,no_update=object())}
    exec(compile(module,'layout.py','exec'),namespace)
    for i, nav in enumerate(['nav-reportabilidad','nav-reclamo','nav-powerbi','nav-monitor-pitum','nav-lixiviacion']):
        context.triggered_id=nav
        result=namespace['toggle_subtabs'](0,0,0,0,0,0,0,0,None,None)
        assert len(result)==19
        assert [j for j,v in enumerate(result[:5]) if v['display']=='block']==[i]
        assert [j for j,v in enumerate(result[10:18]) if v.endswith(' active')]==[i]
