"""Regresiones portables del módulo, sin SQL ni archivos de datos externos."""
import importlib
import unittest
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from dash import Dash
APP = Path(__file__).resolve().parents[1]
if str(APP) not in sys.path:
    sys.path.insert(0, str(APP))
try:
    from . import panel
except ImportError:
    from reconstitucion import panel


def sample(with_timeline=False):
    days = pd.to_datetime(['2026-08-01', '2026-08-03'])
    st = pd.DataFrame([dict(pad_id=pad, campana=7, modulo=1, fecha=day,
                           vol_diario=1000, masa_total=1800)
                       for pad in [1, 2] for day in days])
    it = pd.DataFrame([dict(pad_id=pad, campana=7, modulo=1, fecha=days[0],
        start=days[0]+pd.Timedelta(hours=8), end=days[0]+pd.Timedelta(hours=14),
        mass_h=500., mass_dry=900., origen='TMH observado',
        resolucion='totalizadores_10s_validados_con_TMH_turno')
        for pad in [1, 2]]) if with_timeline else pd.DataFrame()
    return dict(shift_table=st, module_timeline=it,
                itinerario=it, ventana=(days[0], days[-1]))


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
            self.assertEqual(count, 7)

    def test_gantt_sin_horario_no_inventa_barras_de_medicion(self):
        fig = panel.fig_gantt(sample())
        self.assertEqual(len(fig.data), 0)
        self.assertEqual(fig.layout.title.text, 'Sin modulos para esta seleccion')

    def test_gantt_tiene_solo_horario_azul_y_turnos_reales(self):
        fig = panel.fig_gantt(sample(with_timeline=True))
        self.assertEqual(len(fig.data), 1)
        bar = fig.data[0]
        self.assertEqual(bar.name, 'Horario reconstruido')
        self.assertEqual(bar.marker.color.lower(), '#3b82f6')
        self.assertEqual(len(bar.x), 2)
        self.assertEqual(len(set(bar.y)), 2)
        self.assertTrue(all('| ' not in label for label in bar.y))
        self.assertTrue(all('TB' not in label for label in bar.y))
        self.assertFalse(fig.layout.shapes)

    def test_css_encapsulado(self):
        root = APP if not (Path(__file__).resolve().parents[1]/'assets').exists() else Path(__file__).resolve().parents[1]
        css = (root/'assets/reconstitucion.css').read_text(encoding='utf-8')
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
