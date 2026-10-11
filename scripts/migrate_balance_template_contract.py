"""Adopción única del template (3); nunca se ejecuta durante la exportación."""
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

INPUT_SHA256 = 'f1b7e6073a386c3f26df1d55ae858acbefc041b190a0ac72b3bf8adffac64a44'
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
CORRECTIONS = {
    'Periodo': 'Período', 'periodo': 'período', 'Dias': 'Días', 'dias': 'días',
    'Variacion': 'Variación', 'Produccion': 'Producción',
    'Lixiviacion': 'Lixiviación', 'Sulfúros': 'Sulfuros', 'Pisicinas': 'Piscinas',
    'Cátodica': 'Catódica', 'Catodica': 'Catódica', 'catodica': 'catódica',
    'Cátodico': 'Catódico', 'catodo': 'cátodo', 'Perdidas': 'Pérdidas',
    'Acido Súlfurico': 'Ácido Sulfúrico', 'Acido Sulfurico': 'Ácido Sulfúrico',
    'acido sulfúrico': 'ácido sulfúrico', 'Macro Proceso': 'Macroproceso',
}


def standardize(text):
    for before, after in CORRECTIONS.items():
        text = re.sub(r'(?<!\w)' + re.escape(before) + r'(?!\w)', after, text)
    return text


def adopt(source, destination):
    from report_export.export_to_excel import (
        validate_balance_output_package, _balance_update_period_textbox,
    )
    raw = Path(source).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == INPUT_SHA256, 'Hash de entrada inesperado'
    validate_balance_output_package(raw)
    with ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        files = {i.filename: archive.read(i) for i in infos}
        assert len(infos) == len(files) == 66
        assert archive.testzip() is None
    for name, data in files.items():
        if name.endswith(('.xml', '.rels')):
            ET.fromstring(data)
    assert not any('externalLink' in n for n in files)
    formulas = {n: [ET.tostring(f) for f in ET.fromstring(data).findall('.//m:f', NS)]
                for n, data in files.items() if n.startswith('xl/worksheets/') and n.endswith('.xml')}
    assert sum(map(len, formulas.values())) == 2774
    assert len(formulas['xl/worksheets/sheet6.xml']) == 1080
    changes = []
    patched = dict(files)
    # Only text-node contents in shared strings, inline strings and DrawingML.
    for name, data in files.items():
        if name == 'xl/sharedStrings.xml':
            pattern = rb'(<t(?:\s[^>]*)?>)(.*?)(</t>)'
        elif name.startswith('xl/drawings/drawing') and name.endswith('.xml'):
            pattern = rb'(<a:t(?:\s[^>]*)?>)(.*?)(</a:t>)'
        else:
            continue
        def replace(match):
            before = html.unescape(match[2].decode('utf-8'))
            after = standardize(before)
            if before == after:
                return match[0]
            changes.append({'part': name, 'before': before, 'after': after})
            return match[1] + html.escape(after, quote=False).encode('utf-8') + match[3]
        patched[name] = re.sub(pattern, replace, data, flags=re.DOTALL)
    for number in (1, 2, 3):
        name = f'xl/drawings/drawing{number}.xml'
        normalized = _balance_update_period_textbox(
            patched[name], 'Período: 01 al 23 de Agosto 2026.'
        )
        if normalized != patched[name]:
            changes.append({'part': name, 'before': 'Espaciado del cuadro de período',
                            'after': 'Período: 01 al 23 de Agosto 2026.'})
        patched[name] = normalized
    for name, expected in formulas.items():
        assert [ET.tostring(f) for f in ET.fromstring(patched[name]).findall('.//m:f', NS)] == expected
        # All worksheet bytes, including the three validations, remain identical.
        assert patched[name] == files[name]
    out = io.BytesIO()
    with ZipFile(out, 'w') as archive:
        for info in infos:
            archive.writestr(info, patched[info.filename])
    result = out.getvalue()
    validate_balance_output_package(result)
    with ZipFile(io.BytesIO(result)) as archive:
        assert archive.testzip() is None
        for name in archive.namelist():
            if name.endswith(('.xml', '.rels')):
                ET.fromstring(archive.read(name))
    Path(destination).write_bytes(result)
    return {'source': str(source), 'input_sha256': INPUT_SHA256,
            'output_sha256': hashlib.sha256(result).hexdigest().upper(),
            'formulas': 2774, 'analysis_formulas': 1080,
            'changed_parts': [n for n in files if files[n] != patched[n]], 'corrections': changes}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('source')
    parser.add_argument('destination')
    parser.add_argument('audit')
    args = parser.parse_args()
    report = adopt(args.source, args.destination)
    Path(args.audit).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(report['output_sha256'])
    print('Textos corregidos:', len(report['corrections']))
