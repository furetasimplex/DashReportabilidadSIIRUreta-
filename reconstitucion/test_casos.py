"""Case/run identity, callbacks and period guards under the timeline API."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash import Dash

APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import panel, db_source as db, engine as e, modelo_flujos as mf
    from .test_integration_module import sample
    from .test_metodologia import masa, apilado
except ImportError:
    from reconstitucion import panel, db_source as db, engine as e, modelo_flujos as mf
    from test_integration_module import sample
    from test_metodologia import masa, apilado


CASES = [dict(id=i, nombre=f"Caso {i}", run_id=10+i,
              fecha_inicio="2026-08-03", fecha_fin="2026-08-09") for i in (1, 2)]


def result(case_id):
    return dict(sample(), masa=pd.DataFrame({"caso_id": [case_id],
                                             "reporte_run_id": ["fixture"]}))


def callbacks(loader=None):
    app = Dash(__name__, suppress_callback_exceptions=True)
    panel.register_callbacks(app, loader=loader, case_loader=lambda: CASES)
    return {k: v["callback"].__wrapped__ for k, v in app.callback_map.items()}


def find(fns, key):
    return next(fn for name, fn in fns.items() if key in name)


class Casos(unittest.TestCase):
    def test_catalogo_y_periodo(self):
        f = callbacks()
        cases, opts, default, _ = find(f, "reconstitucion-casos.data")(1)
        self.assertEqual([o["value"] for o in opts], [1, 2])
        self.assertEqual(default, 1)
        self.assertTrue(all(c["fecha_inicio"] and c["fecha_fin"] for c in cases))
        self.assertFalse(any("reconstitucion-rango" in name for name in f))
        layout = str(panel.build_layout().to_plotly_json())
        self.assertNotIn("reconstitucion-rango", layout)
        self.assertIn("reconstitucion-caso", layout)
        self.assertIn("reconstitucion-pad-tabs", layout)

    def test_caso_invalido_no_muestra_placeholder(self):
        out = find(callbacks(), "reconstitucion-resultados.children")(
            None, "2", None, None)
        self.assertIsNone(out)

    def test_carga_id_periodo(self):
        calls = []
        def loader(**kwargs):
            calls.append(kwargs)
            return result(2)
        loaded = find(callbacks(loader), "reconstitucion-token.data")(1, 2, CASES)
        self.assertEqual(calls, [dict(caso_id=2, fecha_min="2026-08-03",
                                      fecha_max="2026-08-09")])
        self.assertEqual(panel._results[loaded[0]]["caso"], CASES[1])

    def test_respuesta_tardia_otro_caso_y_detalle(self):
        f = callbacks(lambda **kwargs: result(1))
        token = find(f, "reconstitucion-token.data")(1, 1, CASES)[0]
        out = find(f, "reconstitucion-resultados.children")(token, "all", 2, CASES)
        self.assertIsNone(out)
        popup = find(f, "reconstitucion-tabla-popup.children")(
            {"points": [{"customdata": [1, 7, 1, "row-id"]}]}, None, 0, token, "all", 2, CASES)
        self.assertIsNone(popup[0])
        self.assertEqual(popup[1], {"display": "none"})

    def test_mismo_id_otro_run_o_periodo(self):
        f = callbacks(lambda **kwargs: result(1))
        token = find(f, "reconstitucion-token.data")(1, 1, CASES)[0]
        for update in (dict(run_id=99), dict(fecha_fin="2026-08-10")):
            out = find(f, "reconstitucion-resultados.children")(
                token, "all", 1, [dict(CASES[0], **update)])
            self.assertIsNone(out)

    def test_sin_masa_y_otro_caso(self):
        for res in (dict(sample(), masa=pd.DataFrame()), result(2)):
            loaded = find(callbacks(lambda **kwargs: res),
                          "reconstitucion-token.data")(1, 1, CASES)
            self.assertIsNone(loaded[0])
            self.assertIn("No se usan datos de otros Casos", loaded[-1])

    def test_error_catalogo_sin_secretos(self):
        app = Dash(__name__)
        def fail():
            raise RuntimeError("SECRET_FIXTURE")
        panel.register_callbacks(app, case_loader=fail)
        f = {k: v["callback"].__wrapped__ for k, v in app.callback_map.items()}
        out = find(f, "reconstitucion-casos.data")(1)
        self.assertEqual(out[:3], (None, [], None))
        self.assertNotIn("SECRET", out[-1])

    def test_sql_historico_parametrizado(self):
        m = masa(1).drop(columns=["H_op", "H_op_src"]).assign(
            TMH_T1=900, TMH_T2=900, humedad=.1, sal=0, caso_id=1,
            caso=None, reporte_run_id="fixture")
        tor = pd.DataFrame({"fecha": [pd.Timestamp("2026-08-03")],
            "H_op": [10.], "H_torres": [12.], "H_op_T1": [5.], "H_op_T2": [5.]})
        with patch.object(db.pd, "read_sql", side_effect=[m, tor]) as query:
            out = db.load_masa("2026-08-03", "2026-08-09", engine=object(), caso_id=1)
        sql = str(query.call_args_list[0].args[0])
        self.assertIn("caso_id = :caso_id", sql)
        self.assertNotIn("es_activa = 1", sql)
        self.assertNotIn("casos_balance", sql)
        self.assertIn("origen = 'AJUSTE_REPORTE'", sql)
        self.assertIn("COALESCE(estado_validacion, 'VALIDADO')", sql)
        self.assertEqual(query.call_args_list[0].kwargs["params"], {"caso_id": 1})
        self.assertEqual(out.caso_id.tolist(), [1])

    def test_motor_no_recorta_periodo_con_perfil_single_pad(self):
        ap = apilado(7).assign(pad_id=2, campana=12)
        mass = masa(7).assign(caso_id=1)
        profile = pd.DataFrame([
            dict(fecha=day, turno=shift, tm=belt, tmh=100., humedad=0., fuente="TEST")
            for day in pd.date_range("2026-08-03", periods=7)
            for shift in ("A", "B") for belt in ("TM1", "TM2")
        ])
        with patch.object(db, "load_apilado", return_value=ap), \
             patch.object(db, "load_masa", return_value=mass) as load, \
             patch.object(mf, "load_profile", return_value=profile):
            res = e.analyze_db("2026-08-03", "2026-08-09", caso_id=1)
        self.assertEqual(res["ventana"], (pd.Timestamp("2026-08-03"),
                                          pd.Timestamp("2026-08-09")))
        self.assertEqual(load.call_args.kwargs, {"caso_id": 1})
        self.assertEqual(len(res["module_timeline"]), 7)

    def test_caso_sin_masa_no_consulta_volumen_ni_cobertura(self):
        with patch.object(db, "load_masa", return_value=pd.DataFrame()) as mass, \
             patch.object(db, "coverage") as coverage, patch.object(db, "load_apilado") as ap:
            with self.assertRaises(e.MissingCaseMassError):
                e.analyze_db("2026-08-03", "2026-08-09", caso_id=1)
        self.assertEqual(mass.call_args.kwargs, {"caso_id": 1})
        self.assertEqual([str(x.date()) for x in mass.call_args.args],
                         ["2026-08-03", "2026-08-09"])
        coverage.assert_not_called()
        ap.assert_not_called()

    def test_callback_mensaje_caso_sin_masa(self):
        def missing(**kwargs):
            raise e.MissingCaseMassError("detalle interno")
        out = find(callbacks(missing), "reconstitucion-token.data")(1, 1, CASES)
        self.assertIsNone(out[0])
        self.assertIn("no tiene masa publicada", out[-1])
        self.assertNotIn("detalle interno", out[-1])

    def test_masa_vacia_no_consulta_ticks(self):
        with patch.object(db.pd, "read_sql", return_value=pd.DataFrame()) as query:
            out = db.load_masa("2026-08-03", "2026-08-09", engine=object(), caso_id=8)
        self.assertTrue(out.empty)
        self.assertIn("caso_id", out.columns)
        query.assert_called_once()


if __name__ == "__main__":
    unittest.main()
