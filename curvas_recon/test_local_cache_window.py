import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from . import local_cache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(local_cache, 'DIR', str(tmp_path))
    monkeypatch.setattr(local_cache, 'ACTIVA', True)
    monkeypatch.setattr(local_cache, 'TTL_S', 24 * 3600)
    monkeypatch.setattr(local_cache, '_MEM', {})
    monkeypatch.setattr(local_cache, '_LOCKS', {})
    monkeypatch.setattr(local_cache, '_STATS',
                        {'hits': 0, 'misses': 0, 'segundos_ahorrados': 0.0})
    yield


def _source():
    dates = pd.date_range('2024-01-01', '2026-12-31', freq='D')
    return pd.DataFrame({'fecha': dates, 'cu_gl': range(len(dates))})


def _bounded(source, params):
    dates = pd.to_datetime(source['fecha'])
    mask = pd.Series(True, index=source.index)
    if 'start' in params:
        mask &= dates >= pd.Timestamp(params['start'])
    if 'end' in params:
        mask &= dates <= pd.Timestamp(params['end'])
    return source.loc[mask].copy()


def _legacy_full_then_slice(source, params):
    """Previous @completo behavior, independent of the new sql_df code."""
    full_params = dict(params)
    if 'start' in params:
        full_params['start'] = local_cache.RANGO_INI
    if 'end' in params:
        full_params['end'] = local_cache.RANGO_FIN
    return _bounded(source, params), full_params


def test_effective_query_matches_old_full_range_slice_with_sixty_day_lookback(
        monkeypatch):
    source = _source()
    calls = []

    def fake_read_sql(query, engine, params):
        calls.append(dict(params))
        return _bounded(source, params)

    monkeypatch.setattr(local_cache.pd, 'read_sql', fake_read_sql)
    start = pd.Timestamp('2026-10-01') - pd.Timedelta(days=60)
    end = pd.Timestamp('2026-10-12')
    params = {'material': 'SULFURO', 'start': start, 'end': end}
    query = ('SELECT fecha, cu_gl FROM dbo.cu_riego '
             'WHERE fecha >= :start AND fecha <= :end')

    expected, old_params = _legacy_full_then_slice(source, params)
    actual = local_cache.sql_df(object(), query, params=params)

    assert_frame_equal(actual, expected)
    assert calls == [params]
    assert calls[0] != old_params
    assert calls[0]['start'] == pd.Timestamp('2026-08-02')
    assert calls[0]['end'] == pd.Timestamp('2026-10-12')


def test_overlapping_windows_match_direct_queries_and_have_distinct_keys(
        monkeypatch):
    source = _source()
    calls = []

    def fake_read_sql(query, engine, params):
        calls.append(dict(params))
        return _bounded(source, params)

    monkeypatch.setattr(local_cache.pd, 'read_sql', fake_read_sql)
    query = ('SELECT fecha, cu_gl FROM dbo.drena_cu '
             'WHERE fecha >= :start AND fecha <= :end')
    windows = [
        {'material': 'OXIDO', 'start': pd.Timestamp('2026-08-02'),
         'end': pd.Timestamp('2026-10-12')},
        {'material': 'OXIDO', 'start': pd.Timestamp('2026-08-06'),
         'end': pd.Timestamp('2026-10-16')},
    ]
    results = [local_cache.sql_df(object(), query, params=p) for p in windows]

    assert calls == windows
    for result, params in zip(results, windows):
        assert_frame_equal(result, _bounded(source, params))
    assert_frame_equal(local_cache.sql_df(object(), query, params=windows[1]), results[1])
    assert len(calls) == 2
    assert local_cache.estado()['misses'] == 2
    assert local_cache.estado()['hits'] == 1


def test_hot_window_returns_copy_and_skips_read(monkeypatch):
    source = _source()
    calls = []

    def fake_read_sql(query, engine, params):
        calls.append(dict(params))
        return source.iloc[:3].copy()

    monkeypatch.setattr(local_cache.pd, 'read_sql', fake_read_sql)
    query = 'SELECT fecha, cu_gl FROM dbo.cu_riego WHERE fecha >= :start'
    params = {'material': 'SULFURO', 'start': pd.Timestamp('2026-08-02')}
    first = local_cache.sql_df(object(), query, params=params)
    first.loc[first.index[0], 'cu_gl'] = -999
    second = local_cache.sql_df(object(), query, params=params)

    assert calls == [params]
    assert second.iloc[0]['cu_gl'] == source.iloc[0]['cu_gl']
    assert local_cache.estado()['hits'] == 1


@pytest.mark.parametrize('days', [181, 366, 730])
def test_long_campaign_windows_are_not_truncated(days, monkeypatch):
    source = _source()
    calls = []

    def fake_read_sql(query, engine, params):
        calls.append(dict(params))
        return _bounded(source, params)

    monkeypatch.setattr(local_cache.pd, 'read_sql', fake_read_sql)
    end = pd.Timestamp('2026-10-12')
    start = end - pd.Timedelta(days=days - 1)
    params = {'material': 'SULFURO', 'start': start, 'end': end}
    query = ('SELECT fecha, cu_gl FROM dbo.riego_diario '
             'WHERE fecha >= :start AND fecha <= :end')

    expected, _ = _legacy_full_then_slice(source, params)
    actual = local_cache.sql_df(object(), query, params=params)

    assert_frame_equal(actual, expected)
    assert calls == [params]
    assert len(actual) == days


def test_unbounded_historical_query_keeps_its_full_source(monkeypatch):
    source = _source()
    calls = []

    def fake_read_sql(query, engine, params):
        calls.append(dict(params))
        return source.copy()

    monkeypatch.setattr(local_cache.pd, 'read_sql', fake_read_sql)
    query = 'SELECT fecha, cu_gl FROM dbo.cu_riego WHERE material = :material'
    params = {'material': 'OXIDO'}

    actual = local_cache.sql_df(object(), query, params=params)
    again = local_cache.sql_df(object(), query, params=params)

    assert_frame_equal(actual, source)
    assert_frame_equal(again, source)
    assert calls == [params]
