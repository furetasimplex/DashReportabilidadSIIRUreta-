from __future__ import annotations

import ast
from pathlib import Path
from io import BytesIO

import pandas as pd
import pytest
from openpyxl import Workbook, load_workbook

from .virtual_pile_report import build_virtual_groups, write_virtual_sheets


def sample_doc():
    return {
        'end': '2026-10-03',
        'pads': {
            'OXIDOS': {'pilas': [{
                'num': 1, 'ini': '2026-10-01', 'apilado': 10.0, 'tms': 100.0,
                'rec': [2.0, 4.0, 6.0], 'rec_curve': [2.0, 4.0, 6.0],
                'rl_curve': [0.24, 0.24, 0.24], 'vol_riego': 72.0,
            }]},
            'SULFUROS': {'pilas': [{
                'num': 21, 'ini': '2026-10-02', 'apilado': 30.0, 'tms': 200.0,
                'rec': [1.0, 3.0], 'rec_curve': [1.0, 3.0],
                'rl_curve': [0.48, 0.48], 'vol_riego': 96.0,
            }]},
        },
    }


GROUP = {'id': 'g-1', 'name': 'Mixto OX y SU',
         'members': ['rox-P01', 'rsu-P21']}


def test_weighted_daily_series_uses_true_starts_and_cutf_denominator():
    group, = build_virtual_groups(sample_doc(), [GROUP])
    rows = group['rows']
    assert group['total_cutf'] == 40.0
    assert group['total_tms'] == 300.0
    assert [row['date'] for row in rows] == list(pd.date_range('2026-10-01', periods=3))
    # Before SU-P21 starts it contributes zero; its CuTf remains tied to its own campaign.
    assert rows[0]['recovery'] == pytest.approx(5.0)
    assert rows[0]['production'] == pytest.approx(2.0)
    assert rows[1]['recovery'] == pytest.approx(12.5)
    assert rows[1]['production'] == pytest.approx(3.0)
    assert rows[1]['flow'] == pytest.approx(5.0)
    assert rows[1]['rate'] == pytest.approx(0.4)
    assert rows[2]['recovery'] == pytest.approx(22.5)


def test_real_missing_curve_point_stays_blank_without_erasing_individuals():
    doc = sample_doc()
    doc['pads']['OXIDOS']['pilas'][0]['rec_curve'][1] = None
    group, = build_virtual_groups(doc, [GROUP])
    assert group['rows'][1]['recovery'] is None
    assert group['rows'][1]['production'] == pytest.approx(3.0)
    book = Workbook()
    book.active.title = 'Rec Ox'
    book.create_sheet('Prod Oxidos')
    write_virtual_sheets(book, doc, [GROUP])
    assert {'Rec Ox', 'Prod Oxidos', 'Pilas virtuales', 'Virtual 001'} <= set(book.sheetnames)
    assert len(book['Virtual 001']._charts) == 2
    assert book['Virtual 001']['A1'].value == '[Virtual] Mixto OX y SU'
    assert 'OXIDOS' not in str([cell.value for row in book['Virtual 001'].iter_rows()
                                for cell in row if cell.value is not None])
    assert 'SULFUROS' not in str([cell.value for row in book['Virtual 001'].iter_rows()
                                  for cell in row if cell.value is not None])
    stream = BytesIO()
    book.save(stream)
    stream.seek(0)
    reopened = load_workbook(stream)
    assert len(reopened['Virtual 001']._charts) == 2
    assert reopened['Virtual 001']['F7'].value == pytest.approx(0.4)


def test_production_gap_does_not_get_backfilled_as_later_spike_and_missing_display_falls_back():
    doc = sample_doc()
    pile = doc['pads']['OXIDOS']['pilas'][0]
    pile['rec'] = [2.0, None, 6.0]
    pile['rec_curve'] = None
    # Keep the other member's cumulative series complete; use the visible curve
    # fallback for legacy docs without a separate display series.
    group, = build_virtual_groups(doc, [GROUP])
    ox_rows = group['rows']
    assert ox_rows[0]['production'] == pytest.approx(2.0)
    assert ox_rows[1]['production'] is None
    assert ox_rows[2]['production'] is None
    assert ox_rows[1]['recovery'] is None
    assert ox_rows[2]['recovery'] == pytest.approx(22.5)


def test_no_groups_keeps_original_workbook_sheet_set_untouched():
    book = Workbook()
    book.active.title = 'Rec Ox'
    book.create_sheet('Prod Oxidos')
    assert write_virtual_sheets(book, sample_doc(), None) == 0
    assert book.sheetnames == ['Rec Ox', 'Prod Oxidos']


def test_malformed_group_container_fails_instead_of_being_ignored():
    with pytest.raises(ValueError, match='lista válida'):
        build_virtual_groups(sample_doc(), {})


@pytest.mark.parametrize('groups, message', [
    ([GROUP, {**GROUP, 'name': 'duplicado'}], 'duplicado'),
    ([{**GROUP, 'members': ['rox-P01', 'rox-P01']}], 'repetidos'),
    ([{**GROUP, 'members': ['rox-P01', 'rsu-P99']}], 'no activas'),
    ([{**GROUP, 'members': ['rox-P01']}], 'al menos dos'),
])
def test_invalid_groups_fail_loudly(groups, message):
    with pytest.raises(ValueError, match=message):
        build_virtual_groups(sample_doc(), groups)


def test_group_sheet_names_respect_excel_limit_even_for_long_labels():
    group, = build_virtual_groups(sample_doc(), [{**GROUP, 'name': 'x' * 80}])
    book = Workbook()
    write_virtual_sheets(book, sample_doc(), [{**GROUP, 'name': 'x' * 80}])
    assert len(group['sheet_name']) <= 31
    assert len(book['Virtual 001'].title) <= 31
    assert book['Virtual 001']['A1'].value == '[Virtual] ' + 'x' * 80


def test_download_callback_passes_local_groups_without_weakening_case_gates():
    source = Path(__file__).with_name('pad_dashboard.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    callback = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'generate_week_report')
    assert [arg.arg for arg in callback.args.args][-1] == 'groups'
    callback_text = ast.get_source_segment(source, callback)
    assert "State('curvas-grupos-store', 'data')" in source
    assert 'escribir_libro(doc, tmp_path, groups=groups, meta=meta_libro)' in callback_text
    assert "data.get('caso_run_id') != selected_case.get('run_id')" in callback_text
    assert "caso.get('run_id') != data.get('caso_run_id')" in callback_text
    assert 'ws != selected_ws or we != selected_we' in callback_text
