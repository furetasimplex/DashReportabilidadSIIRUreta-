"""Inicialización de fecha sin modificar el contrato ni las reglas del mapa."""
from contextlib import contextmanager
from datetime import date
from unittest.mock import patch
import pytest
from dash.exceptions import PreventUpdate
from . import map_db, map_panel


def test_layout_does_not_query_or_embed_a_fixed_date():
    def find(component):
        if getattr(component, 'id', None) == 'lix-map-date':
            return component
        children = getattr(component, 'children', [])
        for child in children if isinstance(children, list) else [children]:
            result = find(child)
            if result is not None:
                return result
    with patch.object(map_db, '_connection', side_effect=AssertionError('Consulta durante layout')):
        assert find(map_panel.layout()).date is None


@pytest.mark.parametrize('latest', ['2026-10-01', '2026-10-06'])
def test_initial_date_follows_current_source(latest):
    with patch.object(map_db, 'latest_operational_date', return_value=latest) as fetch:
        assert map_panel.initialize_date('lix-map-tab', {'display':'block'}, None) == (latest, None)
        fetch.assert_called_once_with()


@pytest.mark.parametrize('tab,style,selected', [
    ('lix-diagnostic-tab', {'display':'block'}, None),
    ('lix-map-tab', {'display':'none'}, None),
    ('lix-map-tab', None, None),
    ('lix-map-tab', {'display':'block'}, '2026-09-15'),
])
def test_no_query_when_hidden_or_user_date_selected(tab, style, selected):
    with patch.object(map_db, 'latest_operational_date', side_effect=AssertionError('Consulta no esperada')):
        with pytest.raises(PreventUpdate):
            map_panel.initialize_date(tab, style, selected)


@pytest.mark.parametrize('failure', [None, RuntimeError('Sin conexión')])
def test_no_invented_date_when_empty_or_error(failure):
    with patch.object(map_db, 'latest_operational_date', return_value=None, side_effect=failure):
        selected, message = map_panel.initialize_date('lix-map-tab', {'display':'block'}, None)
        assert selected is None and message is not None
    with patch.object(map_db, 'snapshot', side_effect=AssertionError('Consulta sin fecha')):
        assert map_panel.load_map(None, 'lix-map-tab', {'display':'block'}) == (None, None)


@pytest.mark.parametrize('latest', [date(2026,10,1), None])
def test_latest_date_parameterized_read_only_query(latest):
    calls = []
    class Result:
        def scalar_one(self): return latest
    class Connection:
        def execute(self, statement, params):
            calls.append((str(statement), params))
            return Result()
    @contextmanager
    def connection(): yield Connection()
    with patch.object(map_db, '_connection', connection):
        assert map_db.latest_operational_date() == (latest.isoformat() if latest else None)
    assert len(calls) == 1
    sql, params = calls[0]
    assert isinstance(params['hasta'], date) and ':hasta' in sql
    assert 'MAX(fecha)' in sql and '2026-' not in sql
    assert all(word not in sql.upper() for word in ['UPDATE ', 'INSERT ', 'DELETE ', 'ALTER ', 'CREATE '])
