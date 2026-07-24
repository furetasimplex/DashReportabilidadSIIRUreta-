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

    def test_quimico_y_fisico_saltan_antes_de_seccion_6(self):
        for tipo, sufijo in (("quimico", "Quimico"), ("fisico", "Fisico")):
            with self.subTest(tipo=tipo):
                xlsx, nombre = cb._build_xlsx_pdf_desde_excel(
                    self._xlsx_muestra(sufijo),
                    tipo,
                    "2026-07-31",
                )
                ws = load_workbook(io.BytesIO(xlsx))[nombre]
                self.assertEqual(ws.page_setup.fitToHeight, 0)
                self.assertEqual([salto.id for salto in ws.row_breaks.brk], [121])

    def test_srr_no_agrega_salto_de_seccion_fy(self):
        xlsx, nombre = cb._build_xlsx_pdf_desde_excel(
            self._xlsx_muestra("SRR"),
            "srr",
            "2026-07-31",
        )
        ws = load_workbook(io.BytesIO(xlsx))[nombre]
        self.assertEqual(list(ws.row_breaks.brk), [])


if __name__ == "__main__":
    unittest.main()
