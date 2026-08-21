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
    def test_datos_conciliados_conserva_orden_oficial_y_factor_es_lectura_posterior(self):
        eventos = []
        datos = pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-01")]})
        factor = pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-01")]})

        with (
            patch.object(
                cb, "ctx",
                SimpleNamespace(triggered_id={"type": "report-export-btn", "tipo": "prod"}),
            ),
            patch.object(
                cb, "refrescar_historico_apilado_report",
                side_effect=lambda **_: eventos.append("refrescar_historico"),
            ),
            patch.object(
                cb, "actualizar_datos_conciliados_emision_report",
                side_effect=lambda **_: eventos.append("mantenedor_oficial"),
            ),
            patch.object(
                cb, "actualizar_reporte_turno_cache_emision",
                side_effect=lambda **_: eventos.append("refrescar_cache_turno"),
            ) as refrescar_cache,
            patch.object(
                cb, "fetch_datos_conciliados_emision_report",
                side_effect=lambda **_: eventos.append("leer_datos") or datos,
            ),
            patch.object(
                cb, "fetch_factor_ajuste_camiones_report",
                side_effect=lambda **_: eventos.append("leer_factor") or factor,
            ),
            patch.object(cb.os.path, "isfile", return_value=True),
            patch.object(
                cb, "export_datos_conciliados_to_template",
                side_effect=lambda *_, **kwargs: (
                    eventos.append("exportar") or b"xlsx"
                ),
            ) as exportador,
        ):
            cb.exportar_excel(
                [1], "2026-08-01", "2026-08-01", modo_fecha="rango"
            )

        self.assertEqual(eventos, [
            "refrescar_historico", "refrescar_cache_turno",
            "mantenedor_oficial", "leer_datos",
            "leer_factor", "exportar",
        ])
        self.assertEqual(
            refrescar_cache.call_args.kwargs,
            {
                "start_date": pd.Timestamp("2026-08-01").date(),
                "end_date": pd.Timestamp("2026-08-02").date(),
            },
        )
        self.assertIs(exportador.call_args.kwargs["df_factor_ajuste"], factor)
        self.assertTrue(exportador.call_args.kwargs["rango_personalizado"])
        self.assertIs(exportador.call_args.kwargs["df_resumen_mtd"], datos)

    def test_datos_conciliados_rango_parcial_lee_mtd_desde_dia_uno(self):
        visible = pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-03")]})
        mtd = pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-01")]})

        with (
            patch.object(
                cb, "ctx",
                SimpleNamespace(triggered_id={"type": "report-export-btn", "tipo": "prod"}),
            ),
            patch.object(cb, "refrescar_historico_apilado_report"),
            patch.object(cb, "actualizar_reporte_turno_cache_emision"),
            patch.object(cb, "actualizar_datos_conciliados_emision_report"),
            patch.object(
                cb, "fetch_datos_conciliados_emision_report",
                side_effect=[visible, mtd],
            ) as lector,
            patch.object(
                cb, "fetch_factor_ajuste_camiones_report",
                return_value=pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-03")]}),
            ),
            patch.object(cb.os.path, "isfile", return_value=True),
            patch.object(
                cb, "export_datos_conciliados_to_template", return_value=b"xlsx",
            ) as exportador,
        ):
            cb.exportar_excel(
                [1], "2026-08-03", "2026-08-07", modo_fecha="rango"
            )

        self.assertEqual(lector.call_count, 2)
        self.assertEqual(
            lector.call_args_list[1].kwargs,
            {
                "start_date": pd.Timestamp("2026-08-01").date(),
                "end_date": pd.Timestamp("2026-08-07").date(),
            },
        )
        self.assertIs(exportador.call_args.kwargs["df_resumen_mtd"], mtd)

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
            patch.object(cb, "actualizar_reporte_turno_cache_emision"),
            patch.object(cb, "actualizar_datos_conciliados_emision_report"),
            patch.object(
                cb,
                "fetch_datos_conciliados_emision_report",
                return_value=datos,
            ),
            patch.object(
                cb,
                "fetch_factor_ajuste_camiones_report",
                return_value=pd.DataFrame({"Fecha": [pd.Timestamp("2026-08-01")]}),
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
        self.assertIn("Datos disponibles hasta", contenido)
        self.assertNotIn("Primera fecha incompleta", contenido)
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
