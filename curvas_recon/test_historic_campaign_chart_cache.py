"""Historic measured recovery traces and per-run chart memoization; no SQL."""
from datetime import date

import plotly.graph_objects as go
import pytest
from sqlalchemy.engine import Engine

from . import pad_dashboard as dashboard


@pytest.fixture(autouse=True)
def isolated_chart_cache(monkeypatch):
    def forbidden_sql(*args, **kwargs):
        raise AssertionError('SQL is forbidden in this regression test')
    monkeypatch.setattr(Engine, 'connect', forbidden_sql)
    with dashboard._PILA_FIGURE_CACHE_LOCK:
        dashboard._PILA_FIGURE_CACHE.clear()
    yield
    with dashboard._PILA_FIGURE_CACHE_LOCK:
        dashboard._PILA_FIGURE_CACHE.clear()


def test_recovery_chart_keeps_september_as_separate_measured_campaign(monkeypatch):
    campaigns = [
        {'dates': [date(2026, 9, 3), date(2026, 9, 21)], 'values': [12.5, 17.0]},
        {'dates': [date(2026, 10, 1), date(2026, 10, 12)], 'values': [0.4, 1.8]},
    ]
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: campaigns})
    monkeypatch.setattr(dashboard, 'recovery_series', lambda *args: {
        'cyc': {'dates': campaigns[-1]['dates'], 'values': campaigns[-1]['values']},
        'xs': [], 'ys': [], 'capped': False, 'cu_tf': 100.0,
    })

    fig = dashboard._build_recovery_chart(
        'rox-P13', date(2026, 10, 1), date(2026, 10, 12))

    assert len(fig.data) == 2
    assert list(fig.data[0].x) == campaigns[0]['dates']
    assert list(fig.data[0].y) == campaigns[0]['values']
    assert list(fig.data[1].x) == campaigns[1]['dates']
    assert '2026-09' in str(fig.data[0].x[0])
    assert '03/09/2026' in fig.data[0].name
    assert '21/09/2026' in fig.data[0].name
    assert fig.data[0].name != fig.data[1].name


def test_pile_chart_callback_warm_hit_skips_builders_and_is_run_scoped(monkeypatch):
    case = {'id': 10013, 'run_id': 10104, 'modelo_codigo': 'hidrometalurgia_125_v2',
            'modelo_version': 'v2', 'total_flujos': 125}
    monkeypatch.setattr(dashboard, 'CASOS', [case])
    monkeypatch.setattr(dashboard, 'ensure_full_data', lambda: None)
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [
        {'dates': [date(2026, 9, 3), date(2026, 10, 12)], 'values': [12.5, 17.0]},
    ]})
    calls = []
    figures = [go.Figure(), go.Figure(), go.Figure()]
    builders = ('_build_recovery_chart', '_build_flujo_chart', '_build_pila_chart')
    for name, fig in zip(builders, figures):
        monkeypatch.setattr(dashboard, name, lambda *args, _name=name, _fig=fig: (calls.append(_name), _fig)[1])

    data = {'caso_id': 10013, 'caso_run_id': 10104, 'raw_token': 'opaque-run-a',
            'week_start': '2026-10-01', 'week_end': '2026-10-12'}
    first = dashboard.render_recon_pila_charts(data, 'rox-P13', 10013)
    second = dashboard.render_recon_pila_charts(data, 'rox-P13', 10013)

    assert first == second
    assert calls == list(builders)
    assert dashboard._pila_chart_cache_key(
        {**data, 'raw_token': 'opaque-run-b'}, 'rox-P13', 10013,
        date(2026, 10, 1), date(2026, 10, 12)) != dashboard._pila_chart_cache_key(
        data, 'rox-P13', 10013, date(2026, 10, 1), date(2026, 10, 12))
    assert dashboard._pila_chart_cache_key(
        {**data, 'caso_run_id': 10105}, 'rox-P13', 10013,
        date(2026, 10, 1), date(2026, 10, 12)) is None
    assert dashboard._pila_chart_cache_key(
        {**data, 'week_end': '2026-10-11'}, 'rox-P13', 10013,
        date(2026, 10, 1), date(2026, 10, 11)) != dashboard._pila_chart_cache_key(
        data, 'rox-P13', 10013, date(2026, 10, 1), date(2026, 10, 12))




def test_reconstructed_september_and_case_daily_overlay_with_gaps(monkeypatch):
    import pandas as pd
    from . import report_metodo

    dates = pd.date_range('2026-09-01', '2026-10-02', freq='D')
    riego = pd.DataFrame({'P13': 1.0}, index=dates)
    cu_riego = pd.Series(1.0, index=dates)
    drena = pd.DataFrame({'P13': 10.0}, index=dates)
    # Missing required drain chemistry remains a visible gap, not zero Cu.
    drena.loc[pd.Timestamp('2026-09-05'), 'P13'] = float('nan')
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-08-01')}}})
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', pd.Timestamp('2026-10-02'))
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [
        {'dates': [date(2026, 8, 31)], 'values': [40.0]},
    ]})
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': riego, 'cu_riego': cu_riego, 'drena_cu': drena,
    })
    raw = {'caso': {'id': 10013, 'run_id': 10104},
           'ws': pd.Timestamp('2026-10-01'), 'we': pd.Timestamp('2026-10-02'),
           'res': {'piles': [{
        'label': 'OXIDOS', 'parcela': 'P13', 'daily': [{
            'date': date(2026, 10, 1), 'fino_pls_final': 100.0,
            'fino_riego_final': 50.0,
        }]}
    ]}}
    rs = dashboard._reconstructed_campaign_series(
        'OXIDOS', 13, pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'), raw)
    by_day = dict(zip(rs['xs'], rs['ys']))
    assert by_day[pd.Timestamp('2026-09-01')] == pytest.approx(40.0204)
    assert by_day[pd.Timestamp('2026-09-04')] == pytest.approx(40.0816)
    assert by_day[pd.Timestamp('2026-09-05')] is None
    assert by_day[pd.Timestamp('2026-09-06')] == pytest.approx(40.102)
    assert by_day[pd.Timestamp('2026-09-30')] == pytest.approx(40.5916)
    assert by_day[pd.Timestamp('2026-10-01')] == pytest.approx(40.7116)
    assert by_day[pd.Timestamp('2026-10-02')] is None
    assert rs['sources'][1].startswith('Reconstruido')
    assert rs['sources'][-1] == 'Reconciliado del Caso'
    assert report_metodo.net_recovery_increment(1, 10, 1) == pytest.approx(0.204)
    assert report_metodo.net_recovery_increment(1, None, 1) is None

    # The UI preserves a separate measured trace and breaks at unsupported days.
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (raw, None))
    fig = dashboard._build_recovery_chart('rox-P13', pd.Timestamp('2026-10-01'),
                                           pd.Timestamp('2026-10-02'),
                                           data={'raw_token': 'x', 'caso_id': 10013,
                                                 'caso_run_id': 10104}, caso_id=10013)
    assert len(fig.data) == 2
    assert 'medido' in fig.data[0].name.lower()
    assert fig.data[1].y[list(fig.data[1].x).index(pd.Timestamp('2026-09-01'))] == pytest.approx(40.0204)
    assert fig.data[1].y[list(fig.data[1].x).index(pd.Timestamp('2026-09-05'))] is None
    assert 'proxy 0,95' in fig.data[1].name
    assert fig.data[1].y[list(fig.data[1].x).index(pd.Timestamp('2026-10-01'))] == pytest.approx(40.7116)

    # A stale raw run is rejected and the operational proxy is shown instead.
    stale = {**raw, 'caso': {'id': 10013, 'run_id': 99999}}
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (stale, None))
    stale_fig = dashboard._build_recovery_chart(
        'rox-P13', pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'),
        data={'raw_token': 'stale', 'caso_id': 10013, 'caso_run_id': 10104},
        caso_id=10013)
    stale_idx = list(stale_fig.data[1].x).index(pd.Timestamp('2026-10-01'))
    assert stale_fig.data[1].y[stale_idx] == pytest.approx(40.612)
    assert stale_fig.data[1].customdata[stale_idx].startswith('Reconstruido')


def test_operational_curve_renders_without_any_measured_recovery(monkeypatch):
    import pandas as pd

    dates = pd.date_range('2026-08-01', '2026-10-02', freq='D')
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-08-01')}}})
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', pd.Timestamp('2026-10-02'))
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': pd.DataFrame({'P13': 1.0}, index=dates),
        'cu_riego': pd.Series(1.0, index=dates),
        'drena_cu': pd.DataFrame({'P13': 10.0}, index=dates),
    })
    fig = dashboard._build_recovery_chart(
        'rox-P13', pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'))
    assert len(fig.data) == 1
    assert len(fig.data[0].x) > 60
    assert fig.data[0].y[-1] == pytest.approx(63 * 0.0204)
    assert fig.data[0].customdata[0].startswith('Reconstruido')
