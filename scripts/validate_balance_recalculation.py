"""Regresión real de Casos 21/24 usando exclusivamente las lecturas existentes."""
from datetime import date
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from openpyxl import load_workbook
from report_export.balance_contract import build_balance_report_identity
from report_export.balance_service import build_balance_official_report
from report_export.export_to_excel import export_balance_reconciliacion_to_template

TEMPLATE = Path('reporte/Template_Balance_Planta_Hidrometalurgia.xlsx')
EXPORTS = Path('auditorias/archivo/report_export/exports')
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def equal_number(actual, expected):
    if expected is None or math.isnan(float(expected)):
        assert actual is None
    else:
        assert actual is not None and math.isclose(float(actual), float(expected), rel_tol=1e-12, abs_tol=1e-10), (actual, expected)


def validate_case(case_id, run_id, days):
    period, accumulated, meta = build_balance_official_report(case_id)
    assert int(meta['solver_run_id']) == run_id
    identity = build_balance_report_identity(meta)
    assert identity['fecha_inicio'] == date(2026, 8, 1)
    assert identity['fecha_fin'] == date(2026, 8, days)
    output = EXPORTS / identity['filename']
    previous = load_workbook(output, data_only=False) if case_id == 24 and output.exists() else None
    raw = export_balance_reconciliacion_to_template(period, accumulated, meta, str(TEMPLATE))
    wb = load_workbook(BytesIO(raw), data_only=False)
    data = wb['Datos Reconciliados']
    assert data['L3'].value == data['L4'].value == days
    period = period.set_index('codigo_flujo')
    accumulated = accumulated.set_index('codigo_flujo')
    for index in range(1, 121):
        code = f'F{index}'
        row = index + 2
        assert data[f'B{row}'].value == code
        for col, field in [('D', 'masa_reconciliada'), ('E', 'ley_cu_reconciliada'), ('F', 'fino_cu_reconciliado')]:
            equal_number(data[f'{col}{row}'].value, period.loc[code, field])
        for col, field in [('G', 'masa_reconciliada_acumulada'), ('H', 'ley_cu_reconciliada_acumulada'), ('I', 'fino_cu_reconciliado_acumulado')]:
            equal_number(data[f'{col}{row}'].value, accumulated.loc[code, field])
        equal_number(data[f'D{row}'].value, data[f'G{row}'].value)
        equal_number(data[f'F{row}'].value, data[f'I{row}'].value)
        analysis = wb['Análisis Variación-Tolerancias']
        for col, field in [('D', 'tolerancia_masa'), ('E', 'tolerancia_ley'), ('F', 'masa_medida'), ('J', 'ley_cu_medida'), ('N', 'fino_cu_medido')]:
            equal_number(analysis[f'{col}{index+3}'].value, period.loc[code, field])
    if case_id == 21:
        equal_number(data['D3'].value, 253003.6957)
        equal_number(data['F3'].value, 2203.433327)
    if previous:
        for sheet in previous:
            for row in sheet:
                for cell in row:
                    assert cell.value == wb[sheet.title][cell.coordinate].value, (sheet.title, cell.coordinate)
        previous.close()
    formula_count = 0
    with ZipFile(BytesIO(raw)) as archive, ZipFile(TEMPLATE) as template:
        assert len(archive.namelist()) == 66
        for part in archive.namelist():
            if part.startswith(('xl/drawings/', 'xl/media/')):
                # Period boxes have dynamic dates; process drawings and all media/rels are identical.
                if part not in [f'xl/drawings/drawing{i}.xml' for i in (1, 2, 3)]:
                    assert archive.read(part) == template.read(part)
            if not (part.startswith('xl/worksheets/') and part.endswith('.xml')):
                continue
            root = ET.fromstring(archive.read(part))
            original = ET.fromstring(template.read(part))
            assert [ET.tostring(f) for f in root.findall('.//m:f', NS)] == [ET.tostring(f) for f in original.findall('.//m:f', NS)]
            for cell in root.findall('.//m:c', NS):
                if cell.find('m:f', NS) is not None:
                    formula_count += 1
                    assert cell.find('m:v', NS) is None
    assert formula_count == 2774
    output.write_bytes(raw)
    report = {'case_id': case_id, 'run_id': run_id, 'days': days,
              'file': str(output), 'f1_mass': data['D3'].value, 'f1_fine': data['F3'].value,
              'formulas': formula_count, 'formula_caches_remaining': 0,
              'matches_official_inputs': True, 'previous_case24_values_unchanged': bool(previous)}
    wb.close()
    return report


if __name__ == '__main__':
    before = TEMPLATE.read_bytes()
    results = [validate_case(21, 149, 8), validate_case(24, 147, 23)]
    assert TEMPLATE.read_bytes() == before
    report = {'template_sha256': hashlib.sha256(before).hexdigest().upper(), 'cases': results}
    Path('report_export/docs/balance_recalculation_cases.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
