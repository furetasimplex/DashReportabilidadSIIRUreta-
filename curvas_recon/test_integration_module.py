"""Offline tests: this suite must never open a database connection."""
import importlib
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest
import dash
import sqlalchemy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from curvas_recon import db_pipeline, pad_dashboard as dashboard


def test_import_and_shell_are_safe(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Import attempted to instantiate a server or engine')
    with monkeypatch.context() as patches:
        patches.setattr(dash, 'Dash', forbidden)
        patches.setattr(sqlalchemy, 'create_engine', forbidden)
        importlib.reload(db_pipeline)
        importlib.reload(dashboard)
        assert db_pipeline._engine is None
        assert dashboard._DATA_READY is False
        assert dashboard.build_layout().id == 'curvas-recon-root'
    # Restore imported symbols so this test does not poison other suites.
    importlib.reload(db_pipeline)


def test_registration_is_idempotent_and_guarded(monkeypatch):
    monkeypatch.setattr(dashboard, '_DATA_READY', False)
    installed = []
    class Host:
        def callback(self, *args, **kwargs):
            def decorate(fn):
                installed.append(fn)
                return fn
            return decorate
    app = Host()
    dashboard.register_callbacks(app)
    dashboard.register_callbacks(app)
    assert len(installed) == len(dashboard._CALLBACKS)
    assert len({id(fn) for fn in installed}) == len(installed)
    # The removed manual refresh control has no dangling callback.
    assert all(fn.__name__ != 'sync_and_refresh' for fn in installed)
    assert not hasattr(dashboard, 'sync_and_refresh')
    # Registered callbacks still short-circuit before touching data when the
    # module has not completed its normal initialization.
    render_grid = next(fn for fn in installed if fn.__name__ == 'render_recon_grid')
    with pytest.raises(dash.exceptions.PreventUpdate):
        render_grid(None, None, None)


def test_initialize_data_resolves_hydro_schema_without_database(monkeypatch):
    monkeypatch.setattr(dashboard, '_DATA_READY', False)
    load_options = Mock(return_value=([], [], None))
    monkeypatch.setattr(dashboard, '_load_caso_options', load_options)
    assert db_pipeline.HIDRO_SCHEMA
    dashboard.initialize_data()
    load_options.assert_called_once_with()
    assert dashboard._DATA_READY


def test_invalid_anchor_fast_fails_without_full_load_and_closes_progress(monkeypatch):
    from pandas import Timestamp

    case = dict(
        id=10013, run_id=10104, nombre='offline fixture',
        fecha_inicio=Timestamp('2026-10-01'), fecha_fin=Timestamp('2026-10-12'),
        modelo_codigo='hidrometalurgia_125_v2', modelo_version='v2', total_flujos=125,
    )
    monkeypatch.setattr(dashboard, '_caso_by_id', lambda _case_id: case)
    monkeypatch.setattr(dashboard, 'resolve_window',
                        lambda *_args: (Timestamp('2026-10-01'), Timestamp('2026-10-12'), 12))
    monkeypatch.setattr(dashboard, 'load_caso_anchor', Mock(return_value={}))
    ensure = Mock(side_effect=AssertionError('full-data load must not run for invalid anchor'))
    monkeypatch.setattr(dashboard, 'ensure_full_data', ensure)
    result = dashboard.compute_recon(1, 10013)
    assert result[0] is dash.no_update
    assert result[1] is True
    ensure.assert_not_called()
    assert dashboard._progress_snapshot()['active'] is False


def test_failed_lazy_load_is_retryable_and_redacts_driver_error(monkeypatch):
    monkeypatch.setattr(dashboard, '_DATA_READY', False)
    refresh = Mock(side_effect=[RuntimeError('password=SECRET'), ([], [], None)])
    monkeypatch.setattr(dashboard, '_load_caso_options', refresh)
    monkeypatch.setattr(dashboard, '_build_content_layout', lambda: 'loaded')
    _, message, retry_style = dashboard.load_section(0, 0)
    assert 'SECRET' not in str(message)
    assert retry_style['display'] == 'inline-block'
    assert not dashboard._DATA_READY
    content, message, retry_style = dashboard.load_section(1, 1)
    assert content == 'loaded'
    assert message == ''
    assert retry_style['display'] == 'none'
    assert dashboard._DATA_READY
    dashboard.initialize_data()
    assert refresh.call_count == 2


def test_host_engine_is_injectable(monkeypatch):
    engine = Mock()
    monkeypatch.setattr(db_pipeline, '_engine', None)
    db_pipeline.configure_engine(engine)
    assert db_pipeline.get_engine() is engine
    assert db_pipeline.connect() is engine.connect.return_value


def test_schema_check_is_read_only(monkeypatch):
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = 1
    monkeypatch.setattr(db_pipeline, '_engine', engine)
    monkeypatch.setattr(db_pipeline, '_TABLAS_LISTAS', False)
    db_pipeline._ensure_reconciliation_tables()
    sql = [str(call.args[0]).upper() for call in conn.execute.call_args_list]
    assert len(sql) == 5
    assert all(query.startswith('SELECT') for query in sql)
    assert db_pipeline._TABLAS_LISTAS


def test_schema_check_reports_missing_table(monkeypatch):
    engine = MagicMock()
    conn = engine.connect.return_value.__enter__.return_value
    conn.execute.return_value.scalar.return_value = None
    monkeypatch.setattr(db_pipeline, '_engine', engine)
    monkeypatch.setattr(db_pipeline, '_TABLAS_LISTAS', False)
    with pytest.raises(RuntimeError, match='Falta la tabla'):
        db_pipeline._ensure_reconciliation_tables()
    assert not db_pipeline._TABLAS_LISTAS


def test_opening_section_defers_history_and_full_load_is_once(monkeypatch):
    monkeypatch.setattr(dashboard, '_DATA_READY', False)
    monkeypatch.setattr(dashboard, '_FULL_DATA_READY', False)
    cases = Mock(return_value=([], [], None))
    full = Mock()
    monkeypatch.setattr(dashboard, '_load_caso_options', cases)
    monkeypatch.setattr(dashboard, 'refresh_data_caches', full)
    dashboard.initialize_data()
    dashboard.initialize_data()
    cases.assert_called_once()
    full.assert_not_called()
    assert not dashboard._FULL_DATA_READY
    dashboard.ensure_full_data()
    dashboard.ensure_full_data()
    full.assert_called_once_with(bajar_de_nuevo=False)
    dashboard.ensure_full_data(force=True)
    assert full.call_count == 2
    assert full.call_args.kwargs == {'bajar_de_nuevo': True}


def test_layout_has_no_manual_refresh_control_or_freshness_placeholder():
    def component_ids(node):
        if isinstance(node, (list, tuple)):
            return [value for child in node for value in component_ids(child)]
        if not hasattr(node, 'to_plotly_json'):
            return []
        props = node.to_plotly_json().get('props', {})
        found = [props['id']] if props.get('id') else []
        return found + component_ids(props.get('children'))

    ids = component_ids(dashboard.build_layout())
    assert 'curvas-recon-sync-btn' not in ids
    assert 'curvas-recon-freshness' not in ids


def test_failed_full_load_can_be_retried(monkeypatch):
    monkeypatch.setattr(dashboard, '_FULL_DATA_READY', False)
    refresh = Mock(side_effect=[RuntimeError('offline'), None])
    monkeypatch.setattr(dashboard, 'refresh_data_caches', refresh)
    with pytest.raises(RuntimeError):
        dashboard.ensure_full_data()
    assert not dashboard._FULL_DATA_READY
    dashboard.ensure_full_data()
    assert dashboard._FULL_DATA_READY


@pytest.mark.parametrize('volumen,cobre', [(100., 2.), (-100., -2.), (0., 2.)])
def test_inventory_balance_is_visible_without_pile_assignment(volumen, cobre):
    import json
    from plotly.utils import PlotlyJSONEncoder
    data = dict(balance_inventario=dict(volumen_m3=volumen, cobre_t=cobre,
                                       disponible_verificado=False))
    view = dashboard._build_warnings(data)
    rendered = json.dumps(view, cls=PlotlyJSONEncoder, ensure_ascii=False)
    assert 'Balance pendiente de inventario' in rendered
    assert 't Cu' in rendered
    assert 'Disponibilidad física sin verificar' in rendered
    assert 'no se atribuye a la recuperación de las pilas' in rendered
    assert dashboard._build_warnings({}) is None
