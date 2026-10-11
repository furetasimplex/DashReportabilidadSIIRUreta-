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
                cache = before[ref].find('m:v', NS)
                if cache is not None:
                    before[ref].remove(cache)
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
            if number == 1:
                old.find('m:selection', NS).attrib.update(activeCell='A1', sqref='A1')
            self.assertEqual([ET.tostring(c) for c in old], [ET.tostring(c) for c in new])
            if new.attrib.get('tabSelected') == '1':
                selected.append(number)
        self.assertEqual(selected, [1])
        self.assertEqual(TEMPLATE.read_bytes(), self.source)

    def test_calcpr_and_all_formula_caches_removed_only(self):
        before_calc = ET.fromstring(self.before['xl/workbook.xml']).find('m:calcPr', NS)
        after_calc = ET.fromstring(self.after['xl/workbook.xml']).find('m:calcPr', NS)
        self.assertEqual(after_calc.attrib, dict(before_calc.attrib,
                         calcMode='auto', fullCalcOnLoad='1', forceFullCalc='1'))
        formulas = 0
        for part, data in self.after.items():
            if not part.startswith('xl/worksheets/') or not part.endswith('.xml'):
                continue
            for cell in ET.fromstring(data).findall('.//m:sheetData/m:row/m:c', NS):
                if cell.find('m:f', NS) is not None:
                    formulas += 1
                    self.assertIsNone(cell.find('m:v', NS), (part, cell.attrib['r']))
        self.assertEqual(formulas, 2774)
        for number, ref in ((1, 'E12'), (2, 'F15'), (6, 'G4'), (6, 'K4'), (6, 'O4')):
            cell = ET.fromstring(self.after[f'xl/worksheets/sheet{number}.xml']).find(f'.//m:c[@r="{ref}"]', NS)
            self.assertIsNotNone(cell.find('m:f', NS))
            self.assertIsNone(cell.find('m:v', NS))

    def test_formula_nodes_and_calcchain_preserved_byte_for_byte(self):
        pattern = rb'<f\b[^>]*?(?:/>|>.*?</f>)'
        count = 0
        for part, original in self.before.items():
            if not part.startswith('xl/worksheets/') or not part.endswith('.xml'):
                continue
            # Pair each raw formula with its cell so relocation cannot pass.
            def raw_formulas(data):
                return {
                    re.search(rb'\br="([^"]+)"', cell).group(1): re.search(pattern, cell, re.DOTALL).group()
                    for cell in re.findall(rb'<c\b[^>]*?(?:/>|>.*?</c>)', data, re.DOTALL)
                    if re.search(pattern, cell, re.DOTALL)
                }
            before = raw_formulas(original)
            self.assertEqual(before, raw_formulas(self.after[part]), part)
            count += len(before)
        self.assertEqual(count, 2774)
        for part in ('xl/calcChain.xml', 'xl/metadata.xml', 'xl/_rels/workbook.xml.rels'):
            self.assertEqual(self.before.get(part), self.after.get(part), part)

    def test_accumulated_process_headers_case18_and_case24(self):
        from openpyxl import load_workbook
        from report_export.export_to_excel import export_balance_reconciliacion_to_template
        for case, run, start, end, month in (
            (18, 113, date(2026, 7, 8), date(2026, 7, 15), 'Julio'),
            (24, 147, date(2026, 8, 1), date(2026, 8, 23), 'Agosto'),
        ):
            period = fixtures._flows()
            accumulated = period[['codigo_flujo']].copy()
            accumulated['masa_reconciliada_acumulada'] = 300
            accumulated['ley_cu_reconciliada_acumulada'] = 2
            accumulated['fino_cu_reconciliado_acumulado'] = 6
            meta = fixtures._metadata(case, run, start, end)
            meta.update(fecha_inicio_acumulado=end.replace(day=1), fecha_fin_acumulado=end,
                        mtd_fecha_fin=end)
            output = export_balance_reconciliacion_to_template(period, accumulated, meta, str(TEMPLATE))
            wb = load_workbook(BytesIO(output))
            for sheet, coord in [('Proceso Área Seca', 'R14'), ('Proceso Área Húmeda', 'W17'),
                                 ('Proceso Área Húmeda', 'W105'), ('Proceso Área Cátodos', 'R14')]:
                self.assertEqual(wb[sheet][coord].value, f'Acumulado al {end.day:02d} de {month}')
            for sheet, coord in [('Proceso Área Seca', 'P14'), ('Proceso Área Húmeda', 'U17'),
                                 ('Proceso Área Húmeda', 'U105'), ('Proceso Área Cátodos', 'P14')]:
                self.assertEqual(wb[sheet][coord].value, f'Período {start.day:02d} al {end.day:02d} de {month}')
            wb.close()

    def test_accumulated_label_uses_mtd_metadata_not_case_end(self):
        from openpyxl import load_workbook
        from report_export.export_to_excel import _balance_update_authorized_visible_metadata
        wb = load_workbook(TEMPLATE)
        meta = fixtures._metadata(18, 113, date(2026, 7, 8), date(2026, 7, 15))
        meta.update(fecha_inicio_acumulado=date(2026, 7, 1), fecha_fin_acumulado=date(2026, 7, 15),
                    mtd_fecha_fin=date(2026, 6, 9))
        # Formatter-only test: differing dates deliberately distinguish the data source.
        _balance_update_authorized_visible_metadata(wb, meta, date(2026, 7, 8), date(2026, 7, 15))
        self.assertEqual(wb['Proceso Área Seca']['R14'].value, 'Acumulado al 09 de Junio')
        wb.close()

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
