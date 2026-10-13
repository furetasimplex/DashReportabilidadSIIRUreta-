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
    assert len(installed) == len(dashboard._CALLBACKS) == 16
    # Even if another section validates a hidden component, no initial SQL.
    callback = next(fn for fn in installed if fn.__name__ == 'sync_and_refresh')
    with pytest.raises(dash.exceptions.PreventUpdate):
        callback(0)


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


def test_mount_does_not_query_freshness_or_sync(monkeypatch):
    sync, freshness = Mock(), Mock()
    monkeypatch.setattr(dashboard, 'sync_all', sync)
    monkeypatch.setattr(dashboard, 'data_freshness', freshness)
    assert dashboard.sync_and_refresh(0) == (dash.no_update,) * 4
    sync.assert_not_called()
    freshness.assert_not_called()


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
