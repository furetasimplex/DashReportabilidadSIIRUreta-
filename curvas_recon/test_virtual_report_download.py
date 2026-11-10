"""Real in-memory download path: browser groups and physical-sheet invariance."""
import base64
from copy import deepcopy
from io import BytesIO

import pytest
from openpyxl import load_workbook

from . import pad_dashboard as dashboard, report_metodo as report
from .test_reporte_curvas import export_case, no_sql, report_doc


def test_download_exports_each_local_group_without_double_counting(export_case, monkeypatch):
    data, case = export_case
    doc = report_doc()
    for pad in doc['pads'].values():
        for pile in pad['pilas']:
            pile.update(ini=pad['desde'], tms=1000.0, rl_curve=[0.1, 0.2, 0.3])
    baseline_doc = deepcopy(doc)
    monkeypatch.setattr(report, 'construir_doc', lambda *a, **kw: doc)
    _, plain = dashboard.generate_week_report(1, data, case['id'])
    groups = [dict(id='mix', name='Mixto', members=['rox-P01', 'rsu-P02']),
              dict(id='ox', name='OX', members=['rox-P01', 'rox-P02'])]
    status, download = dashboard.generate_week_report(2, data, case['id'], groups)
    assert download is not None, str(status)
    original = load_workbook(BytesIO(base64.b64decode(plain['content'])))
    virtual = load_workbook(BytesIO(base64.b64decode(download['content'])))
    assert doc == baseline_doc
    assert virtual.sheetnames == original.sheetnames
    for sheet in original:
        # Original physical cells remain unchanged; extra columns are overlays.
        for row in sheet:
            for cell in row:
                assert virtual[sheet.title].cell(cell.row, cell.column).value == cell.value
    assert original['Rec Ox'].max_column == 33
    assert original['Rec Sulfuro'].max_column == 29
    assert virtual['Rec Ox'].cell(9,34).value == 'Σ Mixto [OX+SU]'
    assert virtual['Rec Ox'].cell(9,35).value == 'Σ OX'
    assert virtual['Rec Sulfuro'].cell(10,30).value == 'Σ Mixto [OX+SU]'
    assert virtual['Rec Ox'].cell(12,34).value == pytest.approx(3.0)
    assert virtual['Rec Ox'].cell(4,34).value == pytest.approx(6.0)
    def _title(ch):
        return ''.join(r.t for p in ch.title.tx.rich.p for r in p.r)
    for name, nvirt in (('Curvas Ox', 'Σ OX'), ('Curvas Sulfuro', None)):
        charts = virtual[name]._charts
        virt = [c for c in charts if _title(c) == 'Grupos virtuales']
        assert len(virt) == 1
        titles = [s.tx.v for s in virt[0].series]
        if nvirt:
            assert titles[-2:] == ['Σ Mixto [OX+SU]', 'Σ OX']
        assert all(not str(t).startswith('P') for t in titles)
    # Virtual sums are not appended to production and its physical totals.
    assert list(original['Prod Oxidos'].values) == list(virtual['Prod Oxidos'].values)


def test_download_reports_unknown_member_and_preserves_saved_run(export_case):
    data, case = export_case
    groups = [dict(id='bad', name='Obsoleto', members=['rox-P01', 'rsu-P99'])]
    status, download = dashboard.generate_week_report(1, data, case['id'], groups)
    assert download is None
    assert 'rsu-P99' in str(status)
    assert dashboard._load_recon_raw(data['raw_token'], case['id'])[0]
