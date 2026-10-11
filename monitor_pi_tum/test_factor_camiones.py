"""Pruebas focalizadas sin escrituras ni dependencias de una BD activa."""
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd
from dash import Dash
from dash._callback import GLOBAL_CALLBACK_LIST, GLOBAL_CALLBACK_MAP
from dash._callback_context import context_value
from dash._utils import AttributeDict

from . import db, factor_camiones_panel as panel


def datos():
    return pd.DataFrame({
        "Fecha": ["2026-09-07", "2026-09-08"],
        "Chancado_TMH_Sin_Ajuste": [100., 200.],
        "Produccion_KOM_TMH": [80., None], "Produccion_CAT_TMH": [40., 60.],
        "KOM_TMH_Corregido": [60., None], "CAT_TMH_Corregido": [30., 50.],
        "Vueltas_KOM": [2., 0.], "Vueltas_CAT": [0., None],
        # Deliberadamente distinto del cociente: detecta recálculos accidentales.
        "Factor_Ajuste_Calculado": [0.8123456789, None],
        "Factor_Aplicacion_Reportes": [0.7654321, 1.],
    })


class FactorCamionesTests(unittest.TestCase):
    def test_respaldo_hover_y_rango(self):
        frame = pd.concat([datos().iloc[[0]]] * 5, ignore_index=True)
        frame["Fecha"] = pd.date_range("2026-09-02", periods=5)
        frame["Factor_Ajuste_Calculado"] = [1., None, 0.8, 0.9, 0.7]
        frame["Factor_Aplicacion_Reportes"] = [1., 1., 0.8, 1., 0.7]
        frame["Flag_Factor_Ajuste_Valido"] = [1, 0, 1, 0, 1]
        frame["Estado_Calculo"] = ["OK", "SIN_DATOS_CAMIONES", "OK", "NO_VALIDO", "REVISAR"]
        frame["Regla_Aplicacion"] = ["APLICA_AJUSTE_VALIDADO", "FALLBACK_SIN_DATOS_CAMIONES",
                                    "APLICA_AJUSTE_VALIDADO", "OTRA", "FALLBACK_INCONSISTENCIA"]
        frame.loc[1, "Produccion_KOM_TMH"] = None
        frame.loc[1, "KOM_TMH_Corregido"] = None
        frame.loc[1, "Chancado_TMH_Sin_Ajuste"] = 0
        with patch.object(db, "obtener_factor_camiones", return_value=frame):
            fig, filas, _ = panel.actualizar_factor("2026-09-01", "2026-09-07", 0)
        self.assertEqual([t.name for t in fig.data[:5]], [
            "Chancado TMH sin ajuste", "Producción de referencia", "Chancado TMH corregido automático",
            "Factor calculado", "Factor aplicado"])
        self.assertEqual(list(fig.data[3].y), [1., None, 0.8, 0.9, 0.7])
        self.assertFalse(fig.data[3].connectgaps)
        self.assertEqual(fig.data[4].y[1], 1.)
        self.assertEqual(list(fig.data[5].x), ["2026-09-03", "2026-09-05", "2026-09-06"])
        self.assertEqual(fig.data[5].marker.symbol, "triangle-up")
        self.assertEqual(list(fig.data[0].customdata[1])[:9], [
            "03-09-2026", "0,00", "—", "—", "—", "1,0000",
            "SIN_DATOS_CAMIONES", "FALLBACK_SIN_DATOS_CAMIONES", "—"])
        self.assertEqual(fig.layout.xaxis.tickformat, "%d-%m")
        self.assertIsNone(fig.layout.xaxis.title.text)
        ticks = pd.to_datetime(fig.layout.xaxis.tickvals)
        self.assertGreaterEqual(ticks.min(), pd.Timestamp("2026-09-01"))
        self.assertLessEqual(ticks.max(), pd.Timestamp("2026-09-07"))
        self.assertEqual(pd.Timestamp(fig.layout.xaxis.range[0]), pd.Timestamp("2026-09-01") - pd.Timedelta(hours=12))
        self.assertEqual(pd.Timestamp(fig.layout.xaxis.range[1]), pd.Timestamp("2026-09-07") + pd.Timedelta(hours=12))
        self.assertIn("03-09-2026", panel.detalle_dia(filas, {"points": [{"x": fig.data[5].x[0]}]}).children[0].children)
        with patch.object(db, "obtener_factor_camiones", return_value=frame.iloc[:1]):
            single, _, _ = panel.actualizar_factor("2026-09-02", "2026-09-02", 0)
        self.assertEqual(len(single.data), 5)
        self.assertEqual(len(single.layout.xaxis.tickvals), 1)

    def test_select_parametrizado_orden_y_validacion(self):
        engine = MagicMock()
        with patch.object(db, "_engine_dev", return_value=engine), patch.object(
                db.pd, "read_sql", return_value=datos().iloc[::-1]) as read:
            result = db.obtener_factor_camiones("2026-09-07", "2026-09-08")
            self.assertTrue(result.Fecha.is_monotonic_increasing)
            self.assertEqual(read.call_args.kwargs["params"],
                             dict(fecha_inicio=date(2026, 9, 7), fecha_fin=date(2026, 9, 8)))
            sql = str(read.call_args.args[0])
            self.assertEqual(sql.strip().split()[0], "SELECT")
            self.assertEqual(sql.count("FROM "), 1)
            self.assertIn("FROM inventar_SpcHidr.v_ajuste_camiones_emision_test", sql)
            for forbidden in ("INSERT", "UPDATE", "DELETE", "MERGE", "EXEC", "CREATE", "ALTER"):
                self.assertNotIn(forbidden, sql.upper().split())
            read.return_value = pd.concat([datos(), datos()])
            with self.assertRaisesRegex(ValueError, "duplicadas"):
                db.obtener_factor_camiones("2026-09-07", "2026-09-08")
        for inicio, fin in [(None, "2026-09-08"), ("x", "x"), ("2026-09-09", "2026-09-08")]:
            with patch.object(db, "get_engine") as connect, self.assertRaises(ValueError):
                db.obtener_factor_camiones(inicio, fin)
            connect.assert_not_called()
        with patch.dict("os.environ", SQLSERVER_DB="inventar_SpcHidr"), patch.object(db, "get_engine", return_value=None):
            with self.assertRaises(RuntimeError):
                db.obtener_factor_camiones("2026-09-07", "2026-09-08")

    def test_factores_nulls_y_click(self):
        with patch.object(db, "obtener_factor_camiones", return_value=datos()):
            fig, filas, alerta = panel.actualizar_factor("2026-09-07", "2026-09-08", 0)
        self.assertEqual(alerta, "")
        self.assertEqual(list(fig.data[3].y), [0.8123456789, None])
        self.assertEqual(list(fig.data[4].y), [0.7654321, 1.])
        self.assertEqual(filas[0]["Carga_KOM_TMH_Viaje_Con_Ajuste"], 30.)
        for campo in panel.DERIVADAS:
            self.assertIsNone(filas[1][campo])
        self.assertIsNone(filas[0]["Carga_CAT_TMH_Viaje_Con_Ajuste"])
        click = {"points": [{"x": "2026-09-08"}]}
        detalle = panel.detalle_dia(filas, click)
        self.assertIn("08-09-2026", detalle.children[0].children)
        self.assertIn("—", str(detalle))
        token = context_value.set(AttributeDict(triggered_inputs=[{"prop_id": "pitum-factor-datos.data"}]))
        try:
            self.assertIn("07-09-2026", panel.actualizar_detalle(filas, click).children[0].children)
        finally:
            context_value.reset(token)

    def test_vacio_error_y_dash(self):
        with patch.object(db, "obtener_factor_camiones", return_value=datos().iloc[:0]):
            _, filas, alerta = panel.actualizar_factor("2026-09-07", "2026-09-08", 0)
        self.assertEqual(filas, [])
        self.assertIn("Sin datos", alerta.children)
        with patch.object(db, "obtener_factor_camiones", side_effect=RuntimeError("privado")), self.assertLogs(panel.log):
            _, filas, alerta = panel.actualizar_factor("2026-09-07", "2026-09-08", 0)
        self.assertNotIn("privado", alerta.children)
        from . import panel as monitor

        # Los callbacks decorados con @dash.callback viven inicialmente en un
        # registro global de Dash. Crear una app de prueba los consume.
        # Preservamos/restauramos ese registro para no contaminar otros tests.
        global_callback_list = list(GLOBAL_CALLBACK_LIST)
        global_callback_map = dict(GLOBAL_CALLBACK_MAP)

        try:
            app = Dash(__name__)
            app.layout = monitor.layout()

            with patch.object(
                db,
                "get_engine",
                side_effect=AssertionError("SQL durante layout"),
            ):
                client = app.server.test_client()

                self.assertEqual(
                    client.get("/_dash-layout").status_code,
                    200,
                )
                self.assertEqual(
                    client.get("/_dash-dependencies").status_code,
                    200,
                )

            outputs = [
                key
                for key in app.callback_map
                if "pitum-factor" in key
            ]
            self.assertEqual(len(outputs), 3)

        finally:
            GLOBAL_CALLBACK_LIST[:] = global_callback_list
            GLOBAL_CALLBACK_MAP.clear()
            GLOBAL_CALLBACK_MAP.update(global_callback_map)


if __name__ == "__main__":
    unittest.main()
