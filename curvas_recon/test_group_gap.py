from __future__ import annotations

import ast
import importlib.util
import sys
import types
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

STAGE = Path(__file__).parent
TRANSITION_NAME = "Transici" + chr(243) + "n hist" + chr(243) + "rico / Caso"
HISTORY_LABEL = "Hist" + chr(243) + "rico reconciliado"
SOURCE = STAGE / 'pad_dashboard.py'


def load_function(name, namespace):
    tree = ast.parse(SOURCE.read_text(encoding='utf-8'))
    if name != '_join_recovery_boundary':
        load_function('_join_recovery_boundary', namespace)
    node = next(item for item in tree.body
                if isinstance(item, ast.FunctionDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace[name]


def actual_combiner():
    spec = importlib.util.spec_from_file_location(
        'audit_curve_aggregation', STAGE / 'curve_aggregation.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.combine_recovery_series


def test_reconstructed_series_emits_official_anchor_once_and_keeps_case_cumulative():
    anchor = pd.Timestamp('2026-09-30')
    ws, we = pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02')
    case_rows = []
    for day in (ws, we):
        case_rows.append({
            'label': 'OXIDOS', 'parcela': 'P10', 'date': day,
            'fino_pls_final': 100.0, 'fino_riego_final': 50.0,
            'q_pls_final': 10.0, 'q_riego_final': 10.0,
            'q_pls_medido': 10.0, 'q_riego_medido': 10.0,
            'cu_pls_medido': 0.6, 'cu_riego_medido': 0.4,
        })
    fake_pkg = types.ModuleType('audit_recovery')
    fake_pkg.__path__ = []
    fake_metodo = types.ModuleType('audit_recovery.report_metodo')
    fake_metodo.net_recovery_increment = lambda *_: None
    fake_pkg.report_metodo = fake_metodo
    sys.modules['audit_recovery'] = fake_pkg
    sys.modules['audit_recovery.report_metodo'] = fake_metodo
    index = pd.date_range(ws, we, freq='D')
    namespace = {
        '__package__': 'audit_recovery',
        'pd': pd, 'np': np,
        'WIP_META': {'OXIDOS': {'P10': {'CuTf': 100.0, 'ini_aporte': pd.Timestamp('2026-09-01')}}},
        'JOINT_DATA_CUTOFF': we,
        'cu_tf_toneladas': lambda value: float(value),
        '_measured_cycles': lambda *_: [{'dates': [anchor], 'values': [55.5]}],
        '_load_material_window': lambda *_: {
            'riego': pd.DataFrame(index=index),
            'cu_riego': pd.Series(dtype=float),
            'drena_cu': pd.DataFrame(index=index),
        },
        '_load_recovery_history': lambda *_: ([], None),
        '_load_official_recovery_history': lambda *_: [{
            'date': anchor, 'label': 'OXIDOS', 'parcela': 'P10',
            'value_pct': 55.5,
        }],
        '_historical_recovery_values': lambda *_, **kwargs: (
            {anchor: 55.5}, 55.5, {anchor}, {anchor: 'Histórico reconciliado (oficial)'}),
    }
    reconstruct = load_function('_reconstructed_campaign_series', namespace)
    result = reconstruct('OXIDOS', 10, ws, we,
                        raw={'res': {'daily': case_rows}})
    sep30 = [(value, source) for day, value, source in zip(
        result['xs'], result['ys'], result['sources'])
        if pd.Timestamp(day).normalize() == anchor]
    assert len(sep30) == 1 and sep30[0][0] == 55.5 and sep30[0][1].startswith('Hist') and 'oficial' in sep30[0][1].lower()
    assert np.allclose(result['ys'][-2:], [56.7, 57.9])
    assert result['sources'][-2:] == ['Reconciliado del Caso'] * 2


def build_group_chart(history_dates, history_values):
    group_raw = {'res': {'piles': [
        {'label': 'OXIDOS', 'parcela': 'P10'},
        {'label': 'OXIDOS', 'parcela': 'P11'},
    ]}}
    def member(mid, *_):
        return {
            'id': mid, 'cu_tf_t': 100.0,
            'history_series': {'xs': history_dates, 'ys': history_values,
                               'sources': ['HistÃ³rico reconciliado (oficial)'] * len(history_dates)},
            'reconciled_series': {'xs': [date(2026, 10, 1), date(2026, 10, 2)],
                                  'ys': [52.0, 53.0],
                                  'sources': ['Reconciliado del Caso'] * 2},
            'measured_series': {'xs': [date(2026, 10, 1)], 'ys': [51.9],
                                'sources': ['Medido']},
        }
    namespace = {
        'go': go, 'pd': pd, 'np': np,
        'visible_xaxis_range': lambda *_: None,
        '_store_matches_case': lambda *_: True,
        '_FULL_DATA_READY': True,
        '_add_week_zoom_box': lambda *_: None,
        '_store_window': lambda *_: (pd.Timestamp('2026-10-01'), pd.Timestamp('2026-10-02'), 2),
        '_get_group_raw': lambda *_: group_raw,
        '_combined_member_series': member,
        'combine_recovery_series': actual_combiner(),
        'CHART_SURFACE': '#fff', 'CHART_INK_PRIMARY': '#111',
    }
    build = load_function('_build_combined_recovery_chart', namespace)
    return build({'name': 'F actual', 'members': ['rox-P10', 'rox-P11']}, {}, 10013)


def test_group_chart_joins_adjacent_samples_without_extra_or_dotted_trace():
    fig, warning = build_group_chart(
        [date(2026, 9, 29), date(2026, 9, 30)], [51.0, 51.5])
    assert warning == ''
    assert [t.name for t in fig.data] == ['Curva reconciliada histórica', 'Recuperación reconciliada']   # una sola recuperacion del Caso
    history = next(t for t in fig.data if t.name == 'Curva reconciliada histórica')
    assert list(history.x) == list(pd.date_range('2026-09-29', '2026-10-01'))
    assert list(history.y) == [51.0, 51.5, 52.0]
    assert list(history.customdata)[-1] == [104.0, 200.0]
    assert fig.layout.xaxis.type == 'date'
    assert all(t.line.dash != 'dot' for t in fig.data)


def test_group_chart_does_not_bridge_a_real_gap_or_missing_endpoint():
    for dates, values in [
            ([date(2026, 9, 28), date(2026, 9, 29)], [50.0, 51.0]),
            ([date(2026, 9, 29), date(2026, 9, 30)], [51.0, None])]:
        fig, _ = build_group_chart(dates, values)
        history = next(t for t in fig.data if t.name == 'Curva reconciliada histórica')
        assert len(history.x) == 2
