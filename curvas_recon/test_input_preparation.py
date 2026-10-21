"""Offline concurrency and equivalence tests for input_preparation."""

from datetime import date
from threading import Barrier, Lock
import time

import pandas as pd
import pytest

from input_preparation import prepare_recon_inputs


def _metadata(label):
    return {
        'wip': {label: 'wip'}, 'rec_curves': {label: 'curves'},
        'max_rec': 7, 'ciclo_d': {label: 'cycles'},
    }


def test_preparation_runs_independent_loads_concurrently_and_preserves_payloads():
    labels = ('OXIDOS', 'SULFUROS')
    start, end = date(2026, 9, 1), date(2026, 10, 12)
    expected = {}
    calls = []
    gate = Barrier(4)
    lock = Lock()
    active = maximum_active = 0

    def enter_job():
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        gate.wait(timeout=3)
        time.sleep(0.005)
        with lock:
            active -= 1

    def loader_for(key):
        def loader(label, got_start, got_end):
            assert (got_start, got_end) == (start, end)
            with lock:
                calls.append((label, key, got_start, got_end))
            enter_job()
            return expected[(label, key)]
        return loader

    for label in labels:
        ix = pd.date_range(start, end, freq='D')
        expected[(label, 'riego')] = pd.DataFrame(
            {'P01': pd.Series(range(len(ix)), index=ix, dtype='float64')}, index=ix)
        expected[(label, 'cu_riego')] = pd.Series(
            [0.75] * len(ix), index=ix, dtype='float64', name='cu_riego')
        expected[(label, 'drena_cu')] = pd.DataFrame(
            {'P01': pd.Series([2.5] * len(ix), index=ix, dtype='float64')}, index=ix)

    activity_calls = []
    def activity_loader(label):
        activity_calls.append(label)
        enter_job()
        return ({'P01': pd.DatetimeIndex([pd.Timestamp(start)])},
                {'P01': pd.DatetimeIndex([pd.Timestamp(end)])})

    materials, activity = prepare_recon_inputs(
        labels, start, end, {label: _metadata(label) for label in labels},
        {key: loader_for(key) for key in ('riego', 'cu_riego', 'drena_cu')},
        activity_loader=activity_loader,
    )

    assert len(calls) == 6
    assert len(activity_calls) == 2
    assert maximum_active == 4
    for label in labels:
        assert set(materials[label]) == {
            'wip', 'rec_curves', 'max_rec', 'ciclo_d', 'riego', 'cu_riego', 'drena_cu'}
        metadata = _metadata(label)
        for key in ('wip', 'rec_curves', 'max_rec', 'ciclo_d'):
            assert materials[label][key] == metadata[key]
        for key in ('riego', 'cu_riego', 'drena_cu'):
            actual, original = materials[label][key], expected[(label, key)]
            assert type(actual) is type(original)
            assert actual.index.equals(original.index)
            assert actual.equals(original)
            if isinstance(actual, pd.DataFrame):
                assert actual.dtypes.equals(original.dtypes)
            else:
                assert actual.dtype == original.dtype and actual.name == original.name
        assert set(activity[label][0]) == {'P01'}
        assert activity[label][0]['P01'].equals(pd.DatetimeIndex([pd.Timestamp(start)]))
        assert activity[label][1]['P01'].equals(pd.DatetimeIndex([pd.Timestamp(end)]))


def test_load_errors_propagate_with_context_and_do_not_return_partial_state():
    def okay(label, start, end):
        return pd.DataFrame({'P01': [1.0]}, index=pd.DatetimeIndex([start]))

    def broken(label, start, end):
        if label == 'OXIDOS':
            raise OSError('fixture read failure')
        return okay(label, start, end)

    loaders = {'riego': okay, 'cu_riego': broken, 'drena_cu': okay}
    with pytest.raises(RuntimeError, match='cu_riego for OXIDOS') as error:
        prepare_recon_inputs(
            ('OXIDOS', 'SULFUROS'), date(2026, 10, 1), date(2026, 10, 12),
            {label: _metadata(label) for label in ('OXIDOS', 'SULFUROS')}, loaders)
    assert isinstance(error.value.__cause__, OSError)


def test_metadata_passes_through_without_loader_queries_and_validates_before_submit():
    calls = []
    def loader(label, start, end):
        calls.append((label, start, end))
        return pd.DataFrame()

    metadata = _metadata('OXIDOS')
    materials, activities = prepare_recon_inputs(
        ('OXIDOS',), date(2026, 1, 1), date(2026, 1, 2), {'OXIDOS': metadata},
        {key: loader for key in ('riego', 'cu_riego', 'drena_cu')})
    assert activities == {}
    assert all(materials['OXIDOS'][key] is metadata[key]
               for key in ('wip', 'rec_curves', 'max_rec', 'ciclo_d'))
    assert len(calls) == 3
    with pytest.raises(KeyError, match='max_rec'):
        prepare_recon_inputs(('OXIDOS',), date(2026, 1, 1), date(2026, 1, 2),
                             {'OXIDOS': {'wip': {}, 'rec_curves': {}, 'ciclo_d': {}}},
                             {key: loader for key in ('riego', 'cu_riego', 'drena_cu')})
    assert len(calls) == 3
