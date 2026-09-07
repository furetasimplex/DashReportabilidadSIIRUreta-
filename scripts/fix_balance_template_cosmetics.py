"""Auditoría y corrección puntual OOXML; no participa en el runtime."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from openpyxl.formula.tokenizer import Tokenizer
from openpyxl.utils.cell import range_boundaries
from report_export.export_to_excel import validate_balance_output_package, _balance_sheet_parts

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
INPUT_HASH = '340B4CFD40B51E8D4E748BD1C2988F5D8BD2BDD68AF5FA13ACE99F513C273302'
PROCESSES = ('Proceso Área Seca', 'Proceso Área Húmeda', 'Proceso Área Cátodos')
FIXES = {
    'Flujos Proceso Hidrometalurgía': 'Flujos Proceso Hidrometalurgia',
    'Inventrio Cobre Colgado': 'Inventario Cobre Colgado',
    'Inventrio Cobre colgado': 'Inventario Cobre colgado',
    'Codigo :': 'Código:',
}


def read_parts(content):
    with ZipFile(io.BytesIO(content)) as z:
        return z.infolist(), {n: z.read(n) for n in z.namelist()}


def audit(content):
    validate_balance_output_package(content)
    _, files = read_parts(content)
    sheets = _balance_sheet_parts(files)
    part_names = {v: k for k, v in sheets.items()}
    strings = [''.join(e.itertext()) for e in ET.fromstring(files['xl/sharedStrings.xml']).findall('m:si', NS)]
    report = {'input_sha256': hashlib.sha256(content).hexdigest().upper(),
              'b6': {}, 'dependencies': [], 'texts': [], 'formula_count': 0}
    for name, part in sheets.items():
        root = ET.fromstring(files[part])
        report['formula_count'] += len(root.findall('.//m:f', NS))
        for cell in root.findall('.//m:sheetData/m:row/m:c', NS):
            if cell.attrib['r'] == 'B6' and name in PROCESSES:
                report['b6'][name] = ET.tostring(cell, encoding='unicode')
            value = cell.find('m:v', NS)
            if cell.attrib.get('t') == 's' and value is not None:
                text = strings[int(value.text)]
                if text in FIXES:
                    report['texts'].append([name, cell.attrib['r'], text, int(value.text)])
    # All calculation, validation, conditional-format, drawing and defined-name formulas.
    for part, data in files.items():
        if not part.endswith('.xml'):
            continue
        root = ET.fromstring(data)
        for node in root.iter():
            if node.tag.split('}')[-1] not in ('f', 'formula', 'formula1', 'formula2', 'definedName') or not node.text:
                continue
            text = node.text
            if re.search(r'\b(INDIRECT|OFFSET|ADDRESS)\s*\(', text, re.I):
                raise ValueError(f'Dependencia dinámica requiere revisión: {part}: {text}')
            for token in Tokenizer('=' + text.lstrip('=')).items:
                if token.subtype != 'RANGE':
                    continue
                value = token.value.replace('$', '')
                sheet, address = value.rsplit('!', 1) if '!' in value else (part_names.get(part), value)
                if sheet:
                    sheet = sheet.strip("'").replace("''", "'")
                if sheet not in PROCESSES:
                    if sheet and ':' in sheet:
                        raise ValueError(f'Referencia 3D requiere revisión: {value}')
                    continue
                try:
                    c1, r1, c2, r2 = range_boundaries(address)
                except ValueError:
                    # Defined names are independently audited above.
                    continue
                if (c1 or 1) <= 2 <= (c2 or 16384) and (r1 or 1) <= 6 <= (r2 or 1048576):
                    report['dependencies'].append({'part': part, 'formula': text, 'reference': value})
    if report['dependencies']:
        raise ValueError(json.dumps(report['dependencies'], ensure_ascii=False))
    return report


def apply(content):
    report = audit(content)
    if report['input_sha256'] != INPUT_HASH:
        raise ValueError('Hash de entrada distinto del template aprobado')
    infos, before = read_parts(content)
    files = dict(before)
    sheets = _balance_sheet_parts(files)
    expected = {
        ('Datos Reconciliados', 'B2', 'Flujos Proceso Hidrometalurgía'),
        ('Datos Reconciliados', 'C110', 'Inventrio Cobre Colgado'),
        ('Análisis Variación-Tolerancias', 'C111', 'Inventrio Cobre colgado'),
    }
    found = {(s, c, t) for s, c, t, _ in report['texts'] if t != 'Codigo :'}
    if found != expected:
        raise ValueError(f'Textos inesperados: {found}')
    code_labels = [(s, c) for s, c, t, _ in report['texts'] if t == 'Codigo :']
    if len(code_labels) != 3 or {s for s, _ in code_labels} != set(PROCESSES):
        raise ValueError(f'Rótulos Código inesperados: {code_labels}')
    xml = files['xl/sharedStrings.xml']
    for before_text, after_text in FIXES.items():
        source = ('<t>' + before_text + '</t>').encode('utf-8')
        target = ('<t>' + after_text + '</t>').encode('utf-8')
        if xml.count(source) != 1:
            raise ValueError(f'Texto no unívoco: {before_text}')
        xml = xml.replace(source, target, 1)
    files['xl/sharedStrings.xml'] = xml
    for sheet in PROCESSES:
        part = sheets[sheet]
        source = b'<c r="B6" s="607" t="e" vm="1"><v>#VALUE!</v></c>'
        if files[part].count(source) != 1:
            raise ValueError(f'Contenido B6 inesperado: {sheet}')
        files[part] = files[part].replace(source, b'<c r="B6" s="607"/>', 1)
    for part in sheets.values():
        for path in ('.//m:f', 'm:mergeCells', 'm:dataValidations'):
            old = [ET.tostring(e) for e in ET.fromstring(before[part]).findall(path, NS)]
            new = [ET.tostring(e) for e in ET.fromstring(files[part]).findall(path, NS)]
            if old != new:
                raise ValueError(f'Estructura o fórmula alterada: {part}: {path}')
    result = io.BytesIO()
    with ZipFile(result, 'w') as z:
        for info in infos:
            z.writestr(info, files[info.filename])
    output = result.getvalue()
    validate_balance_output_package(output)
    report['output_sha256'] = hashlib.sha256(output).hexdigest().upper()
    report['changed_parts'] = [n for n in files if before[n] != files[n]]
    report['formulas_removed'] = 0
    return output, report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('template')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report')
    args = parser.parse_args()
    content = Path(args.template).read_bytes()
    if args.apply:
        output, report = apply(content)
        Path(args.template).write_bytes(output)
    else:
        report = audit(content)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
