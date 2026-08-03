import io
import unittest
from datetime import date
from unittest.mock import patch

import pandas as pd
from openpyxl import Workbook, load_workbook

from report_export import report_export as repo
from report_export.callbacks import reportabilidad_cb as cb


def _pesos_muestra():
    return pd.DataFrame(
        {
            "Fecha": [pd.Timestamp("2026-08-01"), pd.Timestamp("2026-08-01")],
            "Turno": [" A ", "A"],
            "Torre": ["t1", "T2"],
            "Horas_Reales": [12.0, None],
            "Factor_Masa": [1.5, None],
            "Fraccion_Muestreo": [0.2, None],
            "PesoTeo_Quimico": [12.40243704, 4.0],
            "PesoReal_Quimico": [3.5, 0.0],
            "Representatividad_Quimica": [0.282202602, 0.0],
            "PesoTeo_Fisico": [40.1255316, 5.0],
            "PesoReal_Fisico": [15.28, None],
            "Representatividad_Fisica": [0.380804924, None],
            "Estado_Evaluacion": ["EVALUABLE", "EVALUABLE"],
            "nombre_archivo": ["pesos.xlsx", None],
            "fecha_carga": [pd.Timestamp("2026-08-03 14:25:30"), pd.NaT],
        }
    )


class TrazabilidadPesosTests(unittest.TestCase):
    def test_snapshot_declara_bloque_pesos_turno(self):
        self.assertIn("pesos_turno", repo.RTO_SNAPSHOT_BLOQUES)

    def test_dataframe_vacio_no_crea_hoja(self):
        wb = Workbook()
        wb.active.title = "Existente"
        cb._agregar_hoja_trazabilidad_pesos(wb, pd.DataFrame())
        self.assertEqual(wb.sheetnames, ["Existente"])

    def test_datos_crean_hoja_final_con_ceros_null_y_porcentajes(self):
        wb = Workbook()
        wb.active.title = "Existente"
        cb._agregar_hoja_trazabilidad_pesos(wb, _pesos_muestra())
        self.assertEqual(wb.sheetnames, ["Existente", "Trazabilidad Pesos"])
        ws = wb["Trazabilidad Pesos"]
        self.assertEqual(ws.max_column, 15)
        self.assertEqual(ws["E3"].value, 0.0)
        self.assertEqual(ws["H3"].value, None)
        self.assertEqual(ws["I3"].value, None)
        self.assertIsInstance(ws["F2"].value, float)
        self.assertEqual(ws["F2"].number_format, "0.0%")
        self.assertEqual(ws["I3"].number_format, "0.0%")

    def test_duplicados_generan_runtime_error(self):
        df = pd.concat([_pesos_muestra().iloc[[0]], _pesos_muestra().iloc[[0]]])
        with self.assertRaisesRegex(RuntimeError, "Llaves duplicadas"):
            repo.validar_pesos_representatividad(df)

    def test_snapshot_nuevo_conserva_fecha_carga_y_null(self):
        original = _pesos_muestra()
        recuperado = repo._snapshot_json_a_dataframe(
            repo._dataframe_a_snapshot_json(original)
        )
        self.assertEqual(recuperado.loc[0, "fecha_carga"], original.loc[0, "fecha_carga"])
        self.assertTrue(pd.isna(recuperado.loc[1, "PesoReal_Fisico"]))
        self.assertEqual(recuperado.loc[1, "PesoReal_Quimico"], 0.0)
        self.assertAlmostEqual(
            recuperado.loc[0, "PesoTeo_Quimico"],
            original.loc[0, "PesoTeo_Quimico"],
            places=12,
        )

    def test_snapshot_antiguo_pasa_dataframe_vacio_al_exportador(self):
        paquete = {
            "rep_torres": pd.DataFrame(), "bd_ton_fy": pd.DataFrame(),
            "bd_ton_mes": pd.DataFrame(), "turno_mes": pd.DataFrame(),
            "gestion_fy_quimico": pd.DataFrame(),
            "gestion_fy_fisico": pd.DataFrame(),
        }
        with patch.object(cb, "_export_representatividad_torres_to_excel", return_value=b"ok") as exportar:
            self.assertEqual(cb._export_representatividad_desde_paquete(paquete), b"ok")
        self.assertTrue(exportar.call_args.kwargs["df_pesos_turno"].empty)

    def test_pdf_selecciona_por_nombre_y_excluye_trazabilidad(self):
        for tipo, sufijo in (("quimico", "Quimico"), ("fisico", "Fisico"), ("srr", "SRR")):
            wb = Workbook()
            wb.active.title = f"01_Ago_26 {sufijo}"
            wb.create_sheet("Trazabilidad Pesos")
            salida = io.BytesIO()
            wb.save(salida)
            filtrado, nombre = cb._build_xlsx_pdf_desde_excel(salida.getvalue(), tipo, date(2026, 8, 3))
            resultado = load_workbook(io.BytesIO(filtrado))
            self.assertEqual(resultado.sheetnames, [nombre])
            self.assertNotIn("Trazabilidad Pesos", resultado.sheetnames)


if __name__ == "__main__":
    unittest.main()
