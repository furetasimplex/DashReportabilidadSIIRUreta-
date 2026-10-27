from datetime import date
from unittest.mock import Mock

import dash
import pandas as pd

from . import pad_dashboard as dashboard


def _case(run_id):
    return dict(id=10013, nombre='fixture', run_id=run_id,
                fecha_inicio=pd.Timestamp('2026-10-01'),
                fecha_fin=pd.Timestamp('2026-10-12'),
                modelo_codigo='hidrometalurgia_125_v2', modelo_version='v2',
                total_flujos=125)


def test_compute_refreshes_official_run_before_loading_anchor(monkeypatch):
    fresh = _case(10145)
    monkeypatch.setattr(dashboard, 'CASOS', dashboard.CASOS)
    monkeypatch.setattr(dashboard, 'CASO_OPTIONS', dashboard.CASO_OPTIONS)
    monkeypatch.setattr(dashboard, 'DEFAULT_CASO_ID', dashboard.DEFAULT_CASO_ID)
    monkeypatch.setattr(dashboard, '_load_caso_options', lambda: ([fresh], [], 10013))
    monkeypatch.setattr(dashboard, 'resolve_window', lambda *_: (
        pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-12'), 12))
    anchor = Mock(return_value={})
    monkeypatch.setattr(dashboard, 'load_caso_anchor', anchor)
    monkeypatch.setattr(dashboard, 'diagnose_caso_anchor', lambda _anchor: ['incompleta'])
    full = Mock(side_effect=AssertionError('invalid anchor must stop before full load'))
    monkeypatch.setattr(dashboard, 'ensure_full_data', full)

    result = dashboard.compute_recon(1, 10013)
    assert result[0] is dash.no_update and result[1] is True
    anchor.assert_called_once_with(10145, 'hidrometalurgia_125_v2', 'v2', 125)
    full.assert_not_called()
    assert dashboard._caso_by_id(10013)['run_id'] == 10145


def test_report_rejects_browser_store_from_old_official_run(monkeypatch):
    fresh = _case(10145)
    monkeypatch.setattr(dashboard, 'CASOS', dashboard.CASOS)
    monkeypatch.setattr(dashboard, 'CASO_OPTIONS', dashboard.CASO_OPTIONS)
    monkeypatch.setattr(dashboard, 'DEFAULT_CASO_ID', dashboard.DEFAULT_CASO_ID)
    monkeypatch.setattr(dashboard, '_load_caso_options', lambda: ([fresh], [], 10013))
    monkeypatch.setattr(dashboard, '_store_matches_case', lambda *_: True)
    raw = Mock(side_effect=AssertionError('must reject before reading old payload'))
    monkeypatch.setattr(dashboard, '_load_recon_raw', raw)
    data = {'caso_id': 10013, 'caso_run_id': 10134}

    status, download = dashboard.generate_week_report(1, data, 10013)
    assert download is None
    assert 'primero' in str(status.children).lower()
    raw.assert_not_called()



def test_refresh_primario_actualiza_cycles_sin_full_reload(monkeypatch):
    fresh_ox = {1: {'dates': [date(2026, 9, 30)], 'values': [65.07]}}
    fresh_su = {21: {'dates': [date(2026, 9, 30)], 'values': [65.07]}}
    monkeypatch.setattr(dashboard, 'DATA_OX', {})
    monkeypatch.setattr(dashboard, 'DATA_SU', {})
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, 'CYCLES_SU', {})
    monkeypatch.setattr(dashboard, 'GLOBAL_MIN_DATE', dashboard.GLOBAL_MIN_DATE)
    monkeypatch.setattr(dashboard, 'GLOBAL_MAX_DATE', dashboard.GLOBAL_MAX_DATE)
    monkeypatch.setattr(dashboard, 'MAX_CAMPANAS', dashboard.MAX_CAMPANAS)
    monkeypatch.setattr(dashboard, 'CAMPANA_OPTIONS', dashboard.CAMPANA_OPTIONS)
    monkeypatch.setattr(dashboard, 'RAW_CURVES_BY_MATERIAL', dashboard.RAW_CURVES_BY_MATERIAL)
    monkeypatch.setattr(dashboard, '_PILA_FIGURE_CACHE', {})
    clear_cache = Mock()
    monkeypatch.setattr(dashboard, 'clear_curve_cache', clear_cache)
    monkeypatch.setattr(dashboard, 'load_oxido', lambda: fresh_ox)
    monkeypatch.setattr(dashboard, 'load_sulfuro', lambda: fresh_su)

    dashboard._refresh_primary_recovery_curves()
    assert dashboard.DATA_OX is fresh_ox and dashboard.DATA_SU is fresh_su
    assert dashboard.CYCLES_OX[1][-1]['values'] == [65.07]
    assert dashboard.CYCLES_SU[21][-1]['values'] == [65.07]
    assert dashboard.RAW_CURVES_BY_MATERIAL == {'OXIDOS': fresh_ox, 'SULFUROS': fresh_su}
    clear_cache.assert_called_once_with()


