"""Regresiones portables del módulo, sin SQL ni archivos de datos externos."""
import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash import Dash
from . import panel


def sample(projected=False):
    days = pd.to_datetime(['2026-08-01', '2026-08-03'])
    st = pd.DataFrame([dict(pad_id=pad, campana=7, modulo=1, fecha=day,
                           vol_diario=1000, masa_total=1800)
                       for pad in [1, 2] for day in days])
    it = pd.DataFrame([dict(pad_id=pad, campana=7, modulo=1, act_ini=days[0],
        real_ini=days[0], real_fin=days[-1],
        proy_ini=days[0] if projected else pd.NaT,
        proy_fin=days[0]+pd.Timedelta(days=2) if projected else pd.NaT,
        rho_proy=1.8) for pad in [1, 2]])
    return dict(shift_table=st, itinerario=it, ventana=(days[0], days[-1]))


class IntegrationModule(unittest.TestCase):
    def test_import_montaje_y_registro_no_abren_sql(self):
        with patch('sqlalchemy.engine.Engine.connect', side_effect=AssertionError('SQL prohibido')), \
             patch('pyodbc.connect', side_effect=AssertionError('ODBC prohibido')):
            importlib.reload(panel)
            tree = panel.build_layout()
            self.assertEqual(tree.className, 'reconstitucion-shell')
            app = Dash(__name__, suppress_callback_exceptions=True)
            panel.register_callbacks(app)
            count = len(app.callback_map)
            panel.register_callbacks(app)
            self.assertEqual(len(app.callback_map), count)
            self.assertEqual(count, 6)

    def test_gantt_no_repite_identidades_ni_rellena_dias_vacios(self):
        res = sample()
        fig = panel.fig_gantt(res)
        self.assertEqual(len(fig.data), 1)
        obs = fig.data[0].customdata
        self.assertEqual(len(obs), len(res['shift_table']))
        self.assertEqual(len(obs), len({tuple(d[:4]) for d in obs}))
        self.assertNotIn('02-08-2026', [d[3] for d in obs])
        self.assertEqual(sum(d[4] for d in obs), res['shift_table'].vol_diario.sum())
        self.assertEqual(sum(d[5] for d in obs), res['shift_table'].masa_total.sum())
        self.assertEqual(fig.data[0].marker.color.lower(), '#e86d1f')

    def test_medicion_y_proyeccion_carriles_distintos(self):
        fig = panel.fig_gantt(sample(projected=True))
        self.assertEqual(len(fig.data), 2)
        self.assertFalse(set(fig.data[0].y) & set(fig.data[1].y))
        self.assertEqual(fig.data[1].marker.color.lower(), '#3b82f6')
        self.assertFalse(fig.layout.shapes)

    def test_css_encapsulado(self):
        css = (Path(__file__).resolve().parents[1]/'assets/reconstitucion.css').read_text(encoding='utf-8')
        self.assertIn('var(--siir-orange', css)
        self.assertTrue(all(rule.strip().startswith('.reconstitucion-shell')
                            for rule in css.splitlines() if rule.strip() and not rule.startswith('@media')))

    def test_loader_error_no_expone_secretos_y_permite_reintento(self):
        calls = []
        def loader(**kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise RuntimeError('SECRET_FIXTURE_ONLY')
            res = sample()
            res['masa'] = pd.DataFrame({'caso_id': [1], 'reporte_run_id': ['uuid1']})
            return res
        app = Dash(__name__, suppress_callback_exceptions=True)
        panel.register_callbacks(app, loader=loader)
        fn = next(v['callback'].__wrapped__ for k, v in app.callback_map.items()
                  if 'reconstitucion-token.data' in k)
        cases = [dict(id=1, nombre='Primero', run_id=11, fecha_inicio='2026-08-01', fecha_fin='2026-08-03')]
        failed = fn(1, 1, cases)
        self.assertNotIn('SECRET', failed[-1])
        loaded = fn(2, 1, cases)
        self.assertIn('Carga finalizada', loaded[-1])
        self.assertEqual(loaded[-2], 'all')
        self.assertIn(loaded[0], panel._results)


if __name__ == '__main__':
    unittest.main()
