from types import SimpleNamespace

import dash
import pandas as pd
import pytest
from sqlalchemy.engine import Engine

from . import pad_dashboard as dashboard


@pytest.fixture
def restored_store(monkeypatch):
    monkeypatch.setattr(dashboard, '_DATA_READY', True)
    monkeypatch.setattr(dashboard, '_FULL_DATA_READY', False)
    monkeypatch.setattr(dashboard, 'REC_META', {})
    monkeypatch.setattr(dashboard, 'WIP_META', {})
    monkeypatch.setattr(dashboard, '_ACTIVE_OX', set())
    monkeypatch.setattr(dashboard, '_ACTIVE_SU', set())
    monkeypatch.setattr(dashboard, 'ctx', SimpleNamespace(triggered_id='curvas-recon-store'))
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (None, None))
    monkeypatch.setattr(Engine, 'connect', lambda *_: pytest.fail('Unexpected SQL in render test'))
    for name in ('load_riego', 'load_cu_riego', 'load_drena_cu'):
        monkeypatch.setattr(dashboard, name, lambda *args, **kwargs: pd.DataFrame())
    return dict(caso_id=10013, week_start='2026-10-01', week_end='2026-10-12',
                SULFUROS=dict(transient=[], ss=[], active=[], wz={}),
                OXIDOS=dict(transient=[], ss=[], active=[], wz={}),
                combined={}, totals={}, warnings=[])


def test_restored_result_initializes_metadata_once(restored_store, monkeypatch):
    calls = []

    def initialize():
        calls.append(True)
        dashboard.REC_META = {label: ([], None, None) for label in ('OXIDOS', 'SULFUROS')}
        dashboard.WIP_META = {label: {} for label in ('OXIDOS', 'SULFUROS')}
        dashboard._FULL_DATA_READY = True

    monkeypatch.setattr(dashboard, 'ensure_full_data', initialize)
    assert len(dashboard.render_recon(restored_store, 'tab-rec', 10013)) == 3
    assert len(dashboard.render_recon(restored_store, 'tab-rec', 10013)) == 3
    assert calls == [True]


def test_rl_tab_does_not_initialize_unrelated_bar_data(restored_store, monkeypatch):
    monkeypatch.setattr(dashboard, 'ctx', SimpleNamespace(triggered_id='curvas-recon-pila-tabs'))
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda: pytest.fail('RL tab must not reload bars'))
    assert dashboard.render_recon(restored_store, 'tab-rl', 10013) == (dash.no_update,) * 3
