"""Compara el paquete completo antes/después: solo admite los cambios autorizados."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from scripts.fix_balance_template_cosmetics import read_parts, FIXES, NS
from report_export.export_to_excel import validate_balance_output_package


def compare_values(before_path, after_path):
    from openpyxl import load_workbook
    before = load_workbook(before_path, data_only=False)
    after = load_workbook(after_path, data_only=False)
    assert before.sheetnames == after.sheetnames
    count = 0
    changes = []
    for sheet in before.sheetnames:
        for row in before[sheet]:
            for cell in row:
                new = after[sheet][cell.coordinate]
                if cell.data_type == 'f':
                    assert cell.value == new.value, (sheet, cell.coordinate)
                    count += 1
                if cell.value != new.value:
                    assert (cell.value in FIXES and FIXES[cell.value] == new.value) or (
                        sheet.startswith('Proceso Área ') and cell.coordinate == 'B6'
                        and cell.value == '#VALUE!' and new.value is None
                    ), (sheet, cell.coordinate, cell.value, new.value)
                    changes.append([sheet, cell.coordinate, cell.value, new.value])
    assert count == 2774
    validate_balance_output_package(Path(after_path).read_bytes())
    before.close()
    after.close()
    return {'formula_count': count, 'business_formulas_changed': 0,
            'numeric_values_changed': 0, 'changes': changes,
            'comparison': 'Valores y fórmulas; copia anterior guardada por Excel con 67 partes, salida final 66'}


def compare(before_path, after_path):
    _, before = read_parts(Path(before_path).read_bytes())
    content = Path(after_path).read_bytes()
    _, after = read_parts(content)
    validate_balance_output_package(content)
    assert before.keys() == after.keys() and len(after) == 66
    expected = dict(before)
    for old, new in FIXES.items():
        source, target = f'<t>{old}</t>'.encode(), f'<t>{new}</t>'.encode()
        assert expected['xl/sharedStrings.xml'].count(source) == 1
        expected['xl/sharedStrings.xml'] = expected['xl/sharedStrings.xml'].replace(source, target)
    for number in (7, 8, 9):
        part = f'xl/worksheets/sheet{number}.xml'
        source = b'<c r="B6" s="607" t="e" vm="1"><v>#VALUE!</v></c>'
        assert expected[part].count(source) == 1
        expected[part] = expected[part].replace(source, b'<c r="B6" s="607"/>')
    for part in before:
        assert after[part] == expected[part], f'Cambio no autorizado: {part}'
    formulas = sum(len(ET.fromstring(data).findall('.//m:f', NS))
                   for part, data in after.items() if part.startswith('xl/worksheets/') and part.endswith('.xml'))
    assert formulas == 2774
    return {'before': str(before_path), 'after': str(after_path), 'parts': 66,
            'formula_count': formulas, 'business_formulas_changed': 0,
            'data_values_changed': 0, 'drawingml_changed': 0,
            'authorized_ref_errors': 3,
            'changed_parts': [n for n in before if before[n] != after[n]]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('report')
    parser.add_argument('--values', action='store_true')
    args = parser.parse_args()
    result = (compare_values if args.values else compare)(args.before, args.after)
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
