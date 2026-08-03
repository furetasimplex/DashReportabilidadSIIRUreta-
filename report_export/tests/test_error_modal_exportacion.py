import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

from report_export.callbacks import reportabilidad_cb as cb
from report_export.export_to_excel import (
    COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS,
    DependenciaDatosExportError,
    _obtener_fecha_corte_resumen_datos_conciliados,
)


class ErrorModalExportacionTests(unittest.TestCase):
    def test_dependencia_datos_abre_modal_con_contexto_ux(self):
        error = DependenciaDatosExportError(
            "Datos Conciliados incompletos",
            fecha=pd.Timestamp("2026-08-01"),
            campos=["Apilado_TMS_Plan", "Ley_CuT_Plan"],
        )
        datos = pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-01")]})

        with (
            patch.object(
                cb,
                "ctx",
                SimpleNamespace(
                    triggered_id={"type": "report-export-btn", "tipo": "prod"}
                ),
            ),
            patch.object(cb, "refrescar_historico_apilado_report"),
            patch.object(cb, "actualizar_datos_conciliados_emision_report"),
            patch.object(
                cb,
                "fetch_datos_conciliados_emision_report",
                return_value=datos,
            ),
            patch.object(cb.os.path, "isfile", return_value=True),
            patch.object(
                cb,
                "export_datos_conciliados_to_template",
                side_effect=error,
            ),
        ):
            resultado = cb.exportar_excel([1], "2026-08-01", "2026-08-31")

        self.assertEqual(len(resultado), 5)
        self.assertTrue(resultado[3])
        contenido = repr(resultado[4])
        self.assertIn("01-08-2026", contenido)
        self.assertIn("Plan de apilado", contenido)
        self.assertIn("Ley de cobre plan", contenido)
        self.assertNotIn("Apilado_TMS_Plan", contenido)
        self.assertNotIn("Traceback", contenido)

    def test_cerrar_modal(self):
        self.assertFalse(cb.cerrar_modal_error_exportacion(1))

    def test_validacion_entrega_fecha_y_campos_estructurados(self):
        fila = {campo: None for campo in COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS}
        fila["Fecha"] = pd.Timestamp("2026-08-01")
        with self.assertRaises(DependenciaDatosExportError) as captura:
            _obtener_fecha_corte_resumen_datos_conciliados(pd.DataFrame([fila]))

        self.assertEqual(captura.exception.fecha, pd.Timestamp("2026-08-01"))
        self.assertIn("Apilado_TMS_Plan", captura.exception.campos)


if __name__ == "__main__":
    unittest.main()
