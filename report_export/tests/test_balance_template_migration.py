"""Regresiones del contrato derivado exclusivamente del template (3)."""
import hashlib
from io import BytesIO
from pathlib import Path
import re
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from datetime import date

from report_export.export_to_excel import validate_balance_output_package
from report_export.report_export import BalanceReportError
from report_export.tests import test_balance_official_mtd as fixtures
from scripts.migrate_balance_template_contract import standardize

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
TEMPLATE = Path('reporte/Template_Balance_Planta_Hidrometalurgia.xlsx')


def parts(content):
    with ZipFile(BytesIO(content)) as archive:
        return {n: archive.read(n) for n in archive.namelist()}


def repack(files):
    output = BytesIO()
    with ZipFile(output, 'w') as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return output.getvalue()


class TemplateMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TEMPLATE.read_bytes()
        inputs = fixtures._flows()
        inputs['masa_medida'] = -123
        inputs['ley_cu_medida'] = 2.5
        inputs['fino_cu_medido'] = 7
        with patch.object(fixtures, '_flows', return_value=inputs):
            cls.output = fixtures.BalanceExcelPhase2Tests()._export_for_dates(
                date(2026, 8, 1), date(2026, 8, 23), date(2026, 8, 1)
            )
        cls.before, cls.after = parts(cls.source), parts(cls.output)

    def test_formulas_and_only_authorized_analysis_inputs(self):
        total = 0
        for name, data in self.before.items():
            if not name.startswith('xl/worksheets/') or not name.endswith('.xml'):
                continue
            before, after = ET.fromstring(data), ET.fromstring(self.after[name])
            def formulas(root):
                return {c.attrib['r']: ET.tostring(c.find('m:f', NS))
                        for c in root.findall('.//m:sheetData/m:row/m:c', NS)
                        if c.find('m:f', NS) is not None}
            original = formulas(before)
            self.assertEqual(original, formulas(after), name)
            total += len(original)
        self.assertEqual(total, 2774)
        name = 'xl/worksheets/sheet6.xml'
        def cells(data):
            return {c.attrib['r']: c for c in ET.fromstring(data).findall('.//m:sheetData/m:row/m:c', NS)}
        before, after = cells(self.before[name]), cells(self.after[name])
        protected = 0
        for row in range(4, 124):
            for col in 'G H I K L M O P Q'.split():
                ref = f'{col}{row}'
                self.assertEqual(ET.tostring(before[ref]), ET.tostring(after[ref]), ref)
                self.assertIsNotNone(after[ref].find('m:f', NS))
                protected += 1
            for col, expected in [('D', 5), ('E', 1), ('F', -123), ('J', 2.5), ('N', 7)]:
                self.assertEqual(float(after[f'{col}{row}'].find('m:v', NS).text), expected)
            for col in 'B C'.split():
                self.assertEqual(ET.tostring(before[f'{col}{row}']), ET.tostring(after[f'{col}{row}']))
        self.assertEqual(protected, 1080)
        self.assertEqual(TEMPLATE.read_bytes(), self.source)

    def test_exact_ref_exception_and_validation_bytes(self):
        for content in (self.source, self.output):
            validate_balance_output_package(content)
            self.assertEqual(sum(data.count(b'#REF!') for data in parts(content).values()), 3)
        pattern = rb'<dataValidations\b.*?</dataValidations>'
        for number in (7, 8, 9):
            name = f'xl/worksheets/sheet{number}.xml'
            self.assertEqual(re.search(pattern, self.before[name]).group(),
                             re.search(pattern, self.after[name]).group())

    def test_cosmetic_texts_and_empty_b6(self):
        for files in (self.before, self.after):
            text = files['xl/sharedStrings.xml'].decode('utf-8')
            for old in ('Hidrometalurgía', 'Inventrio', 'Codigo :'):
                self.assertNotIn(old, text)
            self.assertIn('Código:', text)
            self.assertIn('Inventario Cobre Colgado', text)
            self.assertIn('Inventario Cobre colgado', text)
            for number in (7, 8, 9):
                root = ET.fromstring(files[f'xl/worksheets/sheet{number}.xml'])
                cell = root.find('.//m:c[@r="B6"]', NS)
                self.assertEqual(cell.attrib, {'r': 'B6', 's': '607'})
                self.assertEqual(len(cell), 0)

    def test_initial_view_is_resumen_a1_and_other_view_properties_unchanged(self):
        old = ET.fromstring(self.before['xl/workbook.xml']).find('m:bookViews/m:workbookView', NS)
        new = ET.fromstring(self.after['xl/workbook.xml']).find('m:bookViews/m:workbookView', NS)
        expected = dict(old.attrib, activeTab='0', firstSheet='0')
        self.assertEqual(new.attrib, expected)
        selected = []
        for number in range(1, 10):
            part = f'xl/worksheets/sheet{number}.xml'
            old = ET.fromstring(self.before[part]).find('m:sheetViews/m:sheetView', NS)
            new = ET.fromstring(self.after[part]).find('m:sheetViews/m:sheetView', NS)
            expected = dict(old.attrib)
            if number == 1:
                expected.update(tabSelected='1', topLeftCell='A1')
            else:
                expected.pop('tabSelected', None)
            self.assertEqual(new.attrib, expected)
            self.assertEqual([ET.tostring(c) for c in old], [ET.tostring(c) for c in new])
            if new.attrib.get('tabSelected') == '1':
                selected.append(number)
        self.assertEqual(selected, [1])
        self.assertEqual(TEMPLATE.read_bytes(), self.source)

    def test_historical_flow_references(self):
        def formulas(number):
            root = ET.fromstring(self.after[f'xl/worksheets/sheet{number}.xml'])
            return {c.attrib['r']: c.find('m:f', NS).text
                    for c in root.findall('.//m:sheetData/m:row/m:c', NS)
                    if c.find('m:f', NS) is not None}
        for sheet, row, data_row in ((7, 47, 36), (9, 16, 108), (9, 26, 121)):
            found = formulas(sheet)
            for target, source in zip('PQRS', 'DFGI'):
                self.assertEqual(found[f'{target}{row}'], f"'Datos Reconciliados'!{source}{data_row}")
        report = formulas(2)
        self.assertIn("'Datos Reconciliados'!D120", report['E24'])  # F118
        self.assertIn("'Datos Reconciliados'!D122", report['E24'])  # F120
        self.assertIn("'Datos Reconciliados'!D71", report['E56'])   # F69 masa
        self.assertIn("'Datos Reconciliados'!F71", report['F56'])   # F69 fino

    def test_reject_other_ref_locations_and_missing_exception(self):
        name = 'xl/worksheets/sheet7.xml'
        mutations = [
            self.before[name].replace(b'sqref="C11"', b'sqref="C12"'),
            self.before[name].replace(b'<formula1>#REF!</formula1>', b'<formula1>0</formula1>'),
            self.before[name].replace(b'</sheetData>', b'<row r="999"><c r="A999"><f>#REF!</f></c></row></sheetData>'),
            self.before[name].replace(b'</dataValidations>', b'<dataValidation type="list" sqref="D11"><formula1>#REF!</formula1></dataValidation></dataValidations>'),
        ]
        for mutation in mutations:
            files = dict(self.before)
            files[name] = mutation
            with self.subTest(mutation=hashlib.sha256(mutation).hexdigest()):
                with self.assertRaisesRegex(BalanceReportError, '#REF!'):
                    validate_balance_output_package(repack(files))

    def test_visible_spelling_and_drawing_counts(self):
        xdr = '{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}'
        for files in (self.before, self.after):
            for name, data in files.items():
                if name == 'xl/sharedStrings.xml' or (name.startswith('xl/drawings/') and name.endswith('.xml')):
                    for node in ET.fromstring(data).iter():
                        if node.tag.split('}')[-1] == 't':
                            text = node.text or ''
                            self.assertEqual(standardize(text), text, (name, text))
                            self.assertNotIn('tmf Cu', text)
            for number, counts in [(5, (29, 35, 1)), (6, (38, 84, 1)), (7, (11, 11, 1))]:
                name = f'xl/drawings/drawing{number}.xml'
                root = ET.fromstring(files[name])
                self.assertEqual(tuple(len(root.findall('.//' + xdr + k)) for k in ('sp', 'cxnSp', 'pic')), counts)
                self.assertEqual(self.before[name], self.after[name])
