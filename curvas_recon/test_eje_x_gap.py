from datetime import date
import ast
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import numpy as np
import plotly.graph_objects as go

from rl_series import (
    aggregate_weighted_rl,
    align_values_to_calendar,
    common_positive_dates,
    visible_xaxis_range,
)


def test_leading_none_does_not_expand_axis_and_zero_is_valid():
    dates = [date(2026, 5, 22), date(2026, 8, 31), date(2026, 9, 1), date(2026, 10, 12)]
    values = [None, None, 0.0, 4.0]
    assert visible_xaxis_range([(dates, values)]) == [
        '2026-09-01T00:00:00', '2026-10-12T00:00:00'
    ]


def test_visible_axis_keeps_internal_gaps_and_exact_endpoints():
    calendar = [date(2026, 9, d) for d in (1, 2, 3, 4, 5)]
    support = {pd.Timestamp('2026-09-01'), pd.Timestamp('2026-09-05')}
    aligned = align_values_to_calendar(
        [date(2026, 9, d) for d in (1, 2, 3, 4, 5)],
        [1.0, 2.0, None, 4.0, 5.0], calendar, support,
    )
    assert aligned == [1.0, None, None, None, 5.0]
    assert visible_xaxis_range([(calendar, aligned)]) == [
        '2026-09-01T00:00:00', '2026-09-05T00:00:00'
    ]


def test_group_rl_does_not_fill_internal_missing_member_flow():
    day1, day2, day3 = (date(2026, 9, d) for d in (1, 2, 3))
    daily = aggregate_weighted_rl(
        {'a': {day1: 1.0, day2: None, day3: 2.0},
         'b': {day1: 1.0, day2: 1.0, day3: 2.0}},
        {'a': 100.0, 'b': 100.0},
    )
    assert daily[day1] == 0.24
    assert daily[day2] is None
    assert daily[day3] == 0.48


def test_single_visible_date_gets_one_day_range_and_empty_series_get_none():
    assert visible_xaxis_range([([date(2026, 9, 1)], [0.0])]) == [
        '2026-09-01T00:00:00', '2026-09-02T00:00:00'
    ]
    assert visible_xaxis_range([([date(2026, 9, 1)], [None])]) is None
    assert visible_xaxis_range([]) is None



def _load_real_builder(name, namespace):
    source = Path(__file__).with_name('pad_dashboard.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    if name != '_join_recovery_boundary':
        _load_real_builder('_join_recovery_boundary', namespace)
    fn = next(node for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(name), 'exec'), namespace)
    return namespace[name]


def test_real_combined_chart_constructor_sets_visible_group_range():
    dates = [date(2026, 5, 22), date(2026, 9, 1), date(2026, 9, 2)]
    namespace = {
        'go': go, 'pd': pd, 'np': np, 'visible_xaxis_range': visible_xaxis_range,
        '_store_matches_case': lambda *_: True, '_FULL_DATA_READY': True,
        '_add_week_zoom_box': lambda *_: None,
        '_store_window': lambda *_: (date(2026, 9, 1), date(2026, 9, 2), None),
        '_get_group_raw': lambda *_: {'res': {'piles': [
            {'label': 'OXIDOS', 'parcela': 1}, {'label': 'OXIDOS', 'parcela': 2}]}},
        '_combined_member_series': lambda mid, *_: {'id': mid, 'cu_tf_t': 10.0},
        'combine_recovery_series': lambda _inputs: {
            'xs': dates, 'ys': [None, 0.0, 2.0],
            'recovered_cu_t': [None, 0.0, 0.2], 'cu_tf_t': [None, 10.0, 10.0]},
        'CHART_SURFACE': '#fff', 'CHART_INK_PRIMARY': '#111',
    }
    build = _load_real_builder('_build_combined_recovery_chart', namespace)
    fig, warning = build({'name': 'F actual', 'members': ['rox-P01', 'rox-P02']}, {}, 1)
    assert warning == ''
    assert list(fig.layout.xaxis.range) == [
        '2026-09-01T00:00:00', '2026-09-02T00:00:00'
    ]
    assert list(fig.data[-1].x) == [pd.Timestamp(d) for d in dates]  # Source calendar remains intact.
    assert list(fig.data[-1].y) == [None, 0.0, 2.0]


def test_real_individual_chart_constructor_skips_leading_none_dates():
    dates = [date(2026, 5, 22), date(2026, 9, 1), date(2026, 9, 2)]
    rs = {
        'xs': dates, 'ys': [None, 0.0, 2.0], 'measured_ys': [None, None, None],
        'sources': ['Hist?rico reconciliado guardado', 'Reconciliado del Caso',
                    'Reconciliado del Caso'], 'capped': False,
        'historical_available': True, 'historical_error': None,
    }
    namespace = {
        'go': go, 'pd': pd, 'np': np, 'visible_xaxis_range': visible_xaxis_range,
        '_PAD_TO_LABEL': {'rox': 'OXIDOS'},
        '_measured_cycles_active_in_window': lambda *_: [],
        '_reconstructed_campaign_series': lambda *_args, **_kw: rs.copy(),
        '_operational_activity_in_window': lambda *_: True,
        '_add_week_zoom_box': lambda *_: None,
        'empty_figure': lambda *_: go.Figure(),
        'CHART_SURFACE': '#fff', 'CHART_INK_PRIMARY': '#111',
    }
    build = _load_real_builder('_build_recovery_chart', namespace)
    fig = build('rox-P01', date(2026, 9, 1), date(2026, 9, 2))
    assert list(fig.layout.xaxis.range) == [
        '2026-09-01T00:00:00', '2026-09-02T00:00:00'
    ]
    assert all(date(2026, 5, 22) not in list(trace.x) for trace in fig.data)
