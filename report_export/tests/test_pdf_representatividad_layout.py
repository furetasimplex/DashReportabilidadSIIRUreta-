import io
import unittest

from openpyxl import Workbook, load_workbook

from report_export.callbacks import reportabilidad_cb as cb


class PdfRepresentatividadLayoutTests(unittest.TestCase):
    def _xlsx_muestra(self, sufijo):
        wb = Workbook()
        ws = wb.active
        ws.title = f"01_Jul_26 {sufijo}"
        ws["C56"] = "5.- Detalle turno a turno"
        ws["C122"] = "6.- Gestión sobre representatividad FY27."
        ws.print_area = "A1:M142"
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue()

    def test_todos_los_tipos_conservan_una_sola_pagina_sin_saltos(self):
        for tipo, sufijo in (
            ("quimico", "Quimico"),
            ("fisico", "Fisico"),
            ("srr", "SRR"),
        ):
            with self.subTest(tipo=tipo):
                xlsx, nombre = cb._build_xlsx_pdf_desde_excel(
                    self._xlsx_muestra(sufijo),
                    tipo,
                    "2026-07-31",
                )
                ws = load_workbook(io.BytesIO(xlsx))[nombre]
                self.assertEqual(ws.page_setup.fitToWidth, 1)
                self.assertEqual(ws.page_setup.fitToHeight, 1)
                self.assertEqual(list(ws.row_breaks.brk), [])
                self.assertEqual(str(ws.print_area), "'01_Jul_26 %s'!$A$1:$M$142" % sufijo)

if __name__ == "__main__":
    unittest.main()
