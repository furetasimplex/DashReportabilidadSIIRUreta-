"""Historic measured recovery traces and per-run chart memoization; no SQL."""
from datetime import date

import plotly.graph_objects as go
import pytest
import pandas as pd
from sqlalchemy.engine import Engine

from . import pad_dashboard as dashboard


@pytest.fixture(autouse=True)
def isolated_chart_cache(monkeypatch):
    def forbidden_sql(*args, **kwargs):
        raise AssertionError('SQL is forbidden in this regression test')
    monkeypatch.setattr(Engine, 'connect', forbidden_sql)
    monkeypatch.setattr(dashboard, '_load_recovery_history', lambda *args: ([], ''))
    with dashboard._PILA_FIGURE_CACHE_LOCK:
        dashboard._PILA_FIGURE_CACHE.clear()
    yield
    with dashboard._PILA_FIGURE_CACHE_LOCK:
        dashboard._PILA_FIGURE_CACHE.clear()


def test_recovery_chart_keeps_only_campaign_active_in_case(monkeypatch):
    campaigns = [
        {'dates': [date(2026, 8, 1), date(2026, 8, 10)], 'values': [12.5, 17.0]},
        {'dates': [date(2026, 10, 1), date(2026, 10, 12)], 'values': [0.4, 1.8]},
        {'dates': [date(2026, 10, 15), date(2026, 10, 20)], 'values': [0.2, 2.0]},
    ]
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: campaigns})
    ops = pd.date_range('2026-08-01', '2026-10-12', freq='D')
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({
        'P13': ops,
    }, {}))
    monkeypatch.setattr(dashboard, '_reconstructed_campaign_series', lambda *args, **kwargs: {
        'xs': [], 'ys': [], 'sources': [], 'cu_tf': None, 'capped': False,
    })

    fig = dashboard._build_recovery_chart(
        'rox-P13', date(2026, 10, 1), date(2026, 10, 12))

    assert len(fig.data) == 1
    # A reset in October supersedes the older cycle within the same operational
    # group; the later October 15 trace starts after the Case and is absent.
    assert fig.data[0].x[0] == pd.Timestamp('2026-10-01')
    assert fig.data[0].x[-1] == pd.Timestamp('2026-10-12')
    assert fig.data[0].y[0] == 0.4 and fig.data[0].y[-1] == 1.8


def test_case_spanning_cycle_change_keeps_both_full_traces(monkeypatch):
    first = {'dates': [date(2026, 9, 1), date(2026, 9, 30)], 'values': [12.5, 17.0]}
    second = {'dates': [date(2026, 10, 1), date(2026, 10, 5)], 'values': [0.4, 1.8]}
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [first, second]})
    ops = pd.DatetimeIndex([pd.Timestamp('2026-09-01'), pd.Timestamp('2026-09-30'),
                            pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-05')])
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({'P13': ops}, {}))
    selected = dashboard._measured_cycles_active_in_window(
        'OXIDOS', 13, date(2026, 9, 30), date(2026, 10, 1))
    assert selected == [first, second]


def test_activity_gap_over_30_days_does_not_reuse_closed_measured_campaign(monkeypatch):
    import pandas as pd

    old = {'dates': [date(2026, 8, 1), date(2026, 8, 31)], 'values': [12.5, 17.0]}
    future = {'dates': [date(2026, 10, 20), date(2026, 10, 25)], 'values': [0.2, 2.0]}
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [old, future]})
    # New operations in October are separated from August by >30 days;
    # August data cannot be attributed to this new campaign.
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({
        'P13': pd.DatetimeIndex([pd.Timestamp('2026-08-31'), pd.Timestamp('2026-10-05'),
                                    pd.Timestamp('2026-10-10')]),
    }, {}))
    selected = dashboard._measured_cycles_active_in_window(
        'OXIDOS', 13, date(2026, 10, 5), date(2026, 10, 10))
    assert selected == []


def test_campaign_start_after_case_is_not_shown_and_cache_is_case_scoped(monkeypatch):
    import pandas as pd

    cycles = [
        {'dates': [date(2026, 8, 1), date(2026, 8, 31)], 'values': [12.5, 17.0]},
        {'dates': [date(2026, 10, 15), date(2026, 10, 20)], 'values': [0.2, 2.0]},
    ]
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: cycles})
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({
        'P13': pd.DatetimeIndex([pd.Timestamp('2026-10-15'), pd.Timestamp('2026-10-20')]),
    }, {}))
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'ini_aporte': pd.Timestamp('2026-10-15')}}})
    assert dashboard._measured_cycles_active_in_window(
        'OXIDOS', 13, date(2026, 10, 1), date(2026, 10, 12)) == []

    case = {'id': 10013, 'run_id': 10104, 'modelo_codigo': 'hidrometalurgia_125_v2',
            'modelo_version': 'v2', 'total_flujos': 125}
    monkeypatch.setattr(dashboard, 'CASOS', [case])
    data = {'caso_id': 10013, 'caso_run_id': 10104, 'raw_token': 'same-run',
            'week_start': '2026-10-01', 'week_end': '2026-10-12'}
    key_case = dashboard._pila_chart_cache_key(
        data, 'rox-P13', 10013, date(2026, 10, 1), date(2026, 10, 12))
    key_other_window = dashboard._pila_chart_cache_key(
        {**data, 'week_start': '2026-09-01', 'week_end': '2026-09-12'},
        'rox-P13', 10013, date(2026, 9, 1), date(2026, 9, 12))
    assert key_case != key_other_window


def test_inactive_case_does_not_show_old_reconstructed_campaign(monkeypatch):
    import pandas as pd

    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({}, {}))
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-08-01')}}})
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': pd.DataFrame({'P13': [1.0]}, index=[pd.Timestamp('2026-08-01')]),
        'cu_riego': pd.Series([1.0], index=[pd.Timestamp('2026-08-01')]),
        'drena_cu': pd.DataFrame({'P13': [10.0]}, index=[pd.Timestamp('2026-08-01')]),
    })
    fig = dashboard._build_recovery_chart(
        'rox-P13', date(2026, 10, 1), date(2026, 10, 12))
    assert len(fig.data) == 0


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
    assert by_day[pd.Timestamp('2026-09-01')] is None
    assert by_day[pd.Timestamp('2026-09-04')] is None
    assert by_day[pd.Timestamp('2026-09-05')] is None
    assert by_day[pd.Timestamp('2026-09-06')] is None
    assert by_day[pd.Timestamp('2026-09-30')] is None
    assert by_day[pd.Timestamp('2026-10-01')] is None
    assert by_day[pd.Timestamp('2026-10-02')] is None
    assert rs['sources'][1] == 'Sin histórico reconciliado'
    assert rs['sources'][-1] == 'Reconciliado del Caso'
    assert report_metodo.net_recovery_increment(1, 10, 1) == pytest.approx(0.204)
    assert report_metodo.net_recovery_increment(1, None, 1) is None


def test_reconstructed_reads_top_level_case_daily_rows_and_keeps_missing_rows_gaps(monkeypatch):
    dates = pd.date_range('2026-09-01', '2026-10-03', freq='D')
    riego = pd.DataFrame({'P13': 1.0}, index=dates)
    cu_riego = pd.Series(1.0, index=dates)
    drena = pd.DataFrame({'P13': 10.0}, index=dates)
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-08-31')}}})
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', pd.Timestamp('2026-10-03'))
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [
        {'dates': [date(2026, 8, 31)], 'values': [40.0]},
    ]})
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': riego, 'cu_riego': cu_riego, 'drena_cu': drena,
    })
    raw = {'caso': {'id': 10013, 'run_id': 10145},
           'ws': pd.Timestamp('2026-10-01'), 'we': pd.Timestamp('2026-10-03'),
           'res': {'daily': [
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 1),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': 100.0, 'fino_riego_final': 50.0,
                'q_riego_medido': 1.0, 'q_pls_medido': 1.0,
                'cu_riego_medido': 1.0, 'cu_pls_medido': 10.0},
               # Another pile and a date outside the Case cannot leak in.
               {'label': 'OXIDOS', 'parcela': 'P14', 'date': date(2026, 10, 2),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': 999.0, 'fino_riego_final': 0.0,
                'q_riego_medido': 1.0, 'q_pls_medido': 1.0,
                'cu_riego_medido': 1.0, 'cu_pls_medido': 1.0},
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 2),
                'q_riego_final': 0.0, 'q_pls_final': 0.0,
                'fino_pls_final': None, 'fino_riego_final': None,
                'q_riego_medido': 0.0, 'q_pls_medido': 0.0,
                'cu_riego_medido': None, 'cu_pls_medido': None},
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 4),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': 999.0, 'fino_riego_final': 0.0,
                'q_riego_medido': 1.0, 'q_pls_medido': 1.0,
                'cu_riego_medido': 1.0, 'cu_pls_medido': 1.0},
           ]}}
    rs = dashboard._reconstructed_campaign_series(
        'OXIDOS', 13, pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-03'), raw)
    by_day = dict(zip(rs['xs'], rs['ys']))
    source_by_day = dict(zip(rs['xs'], rs['sources']))
    assert by_day[pd.Timestamp('2026-10-01')] == pytest.approx(40.732)
    assert source_by_day[pd.Timestamp('2026-10-01')] == 'Reconciliado del Caso'
    measured_by_day = dict(zip(rs['xs'], rs['measured_ys']))
    assert measured_by_day[pd.Timestamp('2026-10-01')] == pytest.approx(40.6336)
    assert by_day[pd.Timestamp('2026-10-02')] == pytest.approx(40.732)
    assert by_day[pd.Timestamp('2026-10-03')] is None
    assert source_by_day[pd.Timestamp('2026-10-02')] == 'Reconciliado del Caso'
    assert measured_by_day[pd.Timestamp('2026-10-02')] == pytest.approx(40.6336)

    # The UI preserves a separate measured trace and breaks at unsupported days.
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({
        'P13': pd.date_range('2026-08-31', '2026-10-02', freq='D'),
    }, {}))
    ui_raw = {**raw, 'we': pd.Timestamp('2026-10-02')}
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (ui_raw, None))
    fig = dashboard._build_recovery_chart('rox-P13', pd.Timestamp('2026-10-01'),
                                           pd.Timestamp('2026-10-02'),
                                           data={'raw_token': 'x', 'caso_id': 10013,
                                                 'caso_run_id': 10145}, caso_id=10013)
    assert len(fig.data) == 3
    assert [trace.name for trace in fig.data] == [
        'Recuperación medida', 'Curva reconciliada histórica', 'Recuperación reconciliada']
    assert list(fig.data[0].x) == [pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02')]
    assert list(fig.data[2].x) == [pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02')]
    assert fig.layout.title.text.endswith('medido / reconciliado')
    assert 'reconstruido' not in fig.to_json().lower()
    assert 'proxy' not in fig.to_json().lower()
    assert fig.data[2].y[0] == pytest.approx(40.732)
    assert fig.data[2].y[1] == pytest.approx(40.732)

    # A stale raw run is rejected and the operational measured series remains.
    stale = {**raw, 'caso': {'id': 10013, 'run_id': 99999}}
    monkeypatch.setattr(dashboard, '_load_recon_raw', lambda *args: (stale, None))
    stale_fig = dashboard._build_recovery_chart(
        'rox-P13', pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'),
        data={'raw_token': 'stale', 'caso_id': 10013, 'caso_run_id': 10104},
        caso_id=10013)
    assert len(stale_fig.data) == 2
    assert stale_fig.data[1].name == 'Curva reconciliada histórica'
    assert stale_fig.data[0].name == 'Recuperación medida'


def test_operational_curve_renders_without_any_measured_recovery(monkeypatch):
    import pandas as pd

    dates = pd.date_range('2026-08-01', '2026-10-02', freq='D')
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-08-01')}}})
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', pd.Timestamp('2026-10-02'))
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({'P13': dates}, {}))
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': pd.DataFrame({'P13': 1.0}, index=dates),
        'cu_riego': pd.Series(1.0, index=dates),
        'drena_cu': pd.DataFrame({'P13': 10.0}, index=dates),
    })
    fig = dashboard._build_recovery_chart(
        'rox-P13', pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'))
    assert len(fig.data) == 1
    assert fig.data[0].name == 'Recuperación medida'
    assert len(fig.data[0].x) == 2
    assert fig.data[0].x[0] == pd.Timestamp('2026-10-01')
    assert fig.data[0].x[-1] == pd.Timestamp('2026-10-02')
    assert fig.data[0].y[-1] == pytest.approx(63 * 0.0204)
    assert 'reconstruido' not in fig.to_json().lower()
    assert 'proxy' not in fig.to_json().lower()


def test_case_chart_separates_historical_reconciled_case_and_post_case(monkeypatch):
    import pandas as pd

    days = [pd.Timestamp(value) for value in (
        '2026-09-30', '2026-10-01', '2026-10-02', '2026-10-03')]
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({
        'P13': pd.DatetimeIndex(days[1:3]),
    }, {}))
    monkeypatch.setattr(dashboard, '_reconstructed_campaign_series', lambda *args, **kwargs: {
        'xs': days,
        'ys': [1.0, 2.0, None, 4.0],
        'sources': ['Histórico reconciliado guardado', 'Reconciliado del Caso',
                    'Reconciliado del Caso', 'Medido'],
        'cu_tf': None, 'capped': False,
    })
    fig = dashboard._build_recovery_chart(
        'rox-P13', days[1], days[2])

    assert len(fig.data) == 3
    history, blue, after = fig.data
    assert history.name == 'Curva reconciliada histórica'
    assert list(history.x) == days[:2]
    assert list(history.y) == [1.0, 2.0]
    assert list(blue.x) == days[1:3]
    assert list(blue.y) == [2.0, None]
    assert blue.name == 'Recuperación reconciliada'
    assert blue.line.color == '#2a78d6'
    assert after.name == 'Medido (fuera del Caso)'
    assert list(after.x) == days[2:]
    assert list(after.y) == [None, 4.0]


def test_persisted_history_gaps_require_a_new_observed_anchor(monkeypatch):
    rows = [
        {'date': date(2026, 9, 1), 'increment_tcu': 2.0},
        {'date': date(2026, 9, 3), 'increment_tcu': 3.0},
        {'date': date(2026, 9, 4), 'increment_tcu': 4.0},
    ]
    anchors = [{'dates': [date(2026, 8, 31), date(2026, 9, 3)],
                'values': [40.0, 50.0]}]
    points, baseline, _official_days = dashboard._historical_recovery_values(
        'OXIDOS', 13, date(2026, 8, 1), date(2026, 9, 5), 1000.0,
        anchors, rows, [])
    assert points[pd.Timestamp('2026-09-01')] == pytest.approx(40.2)
    assert points[pd.Timestamp('2026-09-02')] is None
    # A dated primary reading is retained in the visible historical curve;
    # persisted Sep 4 still resumes from the same numerical anchor.
    assert points[pd.Timestamp('2026-09-03')] == pytest.approx(50.0)
    assert points[pd.Timestamp('2026-09-04')] == pytest.approx(50.4)
    assert baseline == pytest.approx(504.0)


def test_case_reconciled_cumulative_stays_missing_after_unknown_increment(monkeypatch):
    dates = pd.date_range('2026-09-01', '2026-10-03', freq='D')
    riego = pd.DataFrame({'P13': 1.0}, index=dates)
    cu_riego = pd.Series(1.0, index=dates)
    drena = pd.DataFrame({'P13': 10.0}, index=dates)
    drena.loc[pd.Timestamp('2026-10-02'), 'P13'] = float('nan')
    monkeypatch.setattr(dashboard, 'WIP_META', {'OXIDOS': {
        'P13': {'CuTf': 1000.0, 'ini_aporte': pd.Timestamp('2026-09-01')}}})
    monkeypatch.setattr(dashboard, 'JOINT_DATA_CUTOFF', pd.Timestamp('2026-10-03'))
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {13: [
        {'dates': [date(2026, 9, 1)], 'values': [40.0]},
    ]})
    monkeypatch.setattr(dashboard, '_load_material_window', lambda *args: {
        'riego': riego, 'cu_riego': cu_riego, 'drena_cu': drena,
    })
    raw = {'caso': {'id': 10013, 'run_id': 10400},
           'ws': pd.Timestamp('2026-10-01'), 'we': pd.Timestamp('2026-10-03'),
           'res': {'daily': [
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 1),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': 2.0, 'fino_riego_final': 1.0},
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 2),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': None, 'fino_riego_final': None},
               {'label': 'OXIDOS', 'parcela': 'P13', 'date': date(2026, 10, 3),
                'q_riego_final': 1.0, 'q_pls_final': 1.0,
                'fino_pls_final': 2.0, 'fino_riego_final': 1.0},
           ]}}
    rs = dashboard._reconstructed_campaign_series(
        'OXIDOS', 13, pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-03'), raw)
    by_day = dict(zip(rs['xs'], rs['ys']))
    assert by_day[pd.Timestamp('2026-10-01')] == pytest.approx(40.594)
    assert by_day[pd.Timestamp('2026-10-02')] is None
    assert by_day[pd.Timestamp('2026-10-03')] is None


def test_single_day_case_trace_stays_visible(monkeypatch):
    import pandas as pd

    day = pd.Timestamp('2026-10-01')
    monkeypatch.setattr(dashboard, 'CYCLES_OX', {})
    monkeypatch.setattr(dashboard, '_fechas_actividad', lambda label: ({'P13': [day]}, {}))
    monkeypatch.setattr(dashboard, '_reconstructed_campaign_series', lambda *args, **kwargs: {
        'xs': [day], 'ys': [12.0], 'sources': ['Medido'],
        'cu_tf': None, 'capped': False,
    })
    fig = dashboard._build_recovery_chart('rox-P13', day, day)
    assert len(fig.data) == 1
    assert list(fig.data[0].x) == [day]
    assert list(fig.data[0].y) == [12.0]
    assert fig.data[0].mode == 'lines+markers'
    assert fig.data[0].marker.size == 5
