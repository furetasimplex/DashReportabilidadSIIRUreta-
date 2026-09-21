"""Validación aislada, sin conexiones SQL ni arranque de consultas oficiales."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from collections import Counter
import pandas as pd
from dash import Dash
from dash._callback_context import context_value
from dash._utils import AttributeDict
from . import panel, db


class MonitorTests(unittest.TestCase):
    def test_rango_inclusivo(self):
        engine = MagicMock()
        engine.url.database = "inventar_SpcHidr"
        with patch.dict("os.environ", SQLSERVER_DB="inventar_SpcHidr"), patch.object(db, "get_engine", return_value=engine), patch.object(db.pd, "read_sql") as read:
            db.obtener_tendencia_totalizador("2026-09-13", "2026-09-13", "CV008")
            self.assertEqual(read.call_args.kwargs["params"], dict(fecha_inicio=datetime(2026, 9, 13), fecha_fin=datetime(2026, 9, 14), correa="CV008"))

    def test_prod_bloqueado(self):
        with patch.dict("os.environ", SQLSERVER_DB="inventar_SpcHidr_PROD"), patch.object(db, "get_engine") as engine:
            with self.assertRaises(RuntimeError):
                db.obtener_tendencia_totalizador("2026-09-13", "2026-09-13", "CV008")
            engine.assert_not_called()

    def test_valores_originales_y_estados(self):
        frame = pd.DataFrame(dict(timestamp=pd.date_range("2026-09-13", periods=5, freq="10s"), valor=[100., 100., None, 5., -2.], correa="CV008", fuente="tot_TM", resolucion_segundos=10, tipo_senal="TOTALIZADOR"))
        with patch.object(panel.db, "obtener_tendencia_totalizador", return_value=frame) as consulta:
            result = panel.actualizar_tendencia(1, "2026-09-13", "2026-09-13", "CV008")
            self.assertEqual(result[1:4], ("100.00", "-2.00", "-102.00"))
            self.assertEqual(result[0].data[0].y[0], result[0].data[0].y[1])
            self.assertTrue(pd.isna(result[0].data[0].y[2]))
            self.assertEqual(result[0].data[0].y[-1], -2)
            self.assertFalse(result[0].data[0].connectgaps)
            consulta.return_value = frame.assign(valor=float("nan"))
            self.assertEqual(panel.actualizar_tendencia(1, "2026-09-13", "2026-09-13", "CV008")[1:4], ("—",)*3)
            consulta.return_value = frame.iloc[:0]
            self.assertIn("No existen datos", panel.actualizar_tendencia(1, "2026-09-13", "2026-09-13", "CV008")[-1].children)
            consulta.side_effect = RuntimeError("detalle privado")
            with self.assertLogs(panel.log, level="ERROR"):
                self.assertEqual(panel.actualizar_tendencia(1, "2026-09-13", "2026-09-13", "CV008")[-1].children, "No fue posible consultar la tendencia del totalizador.")

    def test_layout_navegacion(self):
        # Bloquea cualquier conexión durante la importación del layout activo.
        with patch("db_connection.get_engine", return_value=None), patch("db_connection.get_connection", return_value=None):
            import layout
            app = Dash(__name__, suppress_callback_exceptions=True)
            app.layout = layout.create_layout(app)
            layout.register_callbacks(app)
        ids = []
        def recorrer(node):
            if isinstance(node, (tuple, list)):
                for child in node:
                    recorrer(child)
            elif hasattr(node, "to_plotly_json"):
                if getattr(node, "id", None) is not None:
                    ids.append(str(node.id))
                recorrer(getattr(node, "children", None))
        recorrer(app.layout)
        self.assertEqual([i for i, n in Counter(ids).items() if n > 1], [])
        entry = next(v for k, v in app.callback_map.items() if "subtabs-report.style" in k)
        toggle = entry["callback"].__wrapped__
        for idx, nav in enumerate(["nav-reportabilidad", "nav-reclamo", "nav-powerbi", "nav-monitor-pitum"]):
            token = context_value.set(AttributeDict(triggered_inputs=[{"prop_id": nav + ".n_clicks"}]))
            try:
                result = toggle(0, 0, 0, 0)
                self.assertEqual([v["display"] for v in result[:4]], ["block" if i == idx else "none" for i in range(4)])
                self.assertEqual(result[4 + idx], "siir-nav-link active")
            finally:
                context_value.reset(token)
        token = context_value.set(AttributeDict(triggered_inputs=[]))
        try:
            self.assertEqual(toggle(0, 0, 0, 0)[0], {"display": "block"})
        finally:
            context_value.reset(token)


if __name__ == "__main__":
    unittest.main()
