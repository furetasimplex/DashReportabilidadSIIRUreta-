"""Regresiones portables del mÃ³dulo, sin SQL ni archivos de datos externos."""
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


def walk_components(node):
    out = [node]
    children = getattr(node, 'children', None)
    if isinstance(children, (list, tuple)):
        for child in children:
            out.extend(walk_components(child))
    elif children is not None and not isinstance(children, str):
        out.extend(walk_components(children))
    return out


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

    def test_informe_cachea_calidad_frame_y_xlsx_por_resultado_y_pad(self):
        from io import BytesIO
        calls = {'quality': 0, 'export': 0}
        case = dict(id=741, nombre='caso', run_id=88,
                    fecha_inicio='2026-08-01', fecha_fin='2026-08-03')
        res = sample()
        res.update(caso=case, fuente_modelo={'id': 741, 'run_id': 88},
                   apilado=pd.DataFrame({'pad_id': [2], 'vol_diario': [10]}))
        token = panel.remember(res)
        def quality(*args, **kwargs):
            calls['quality'] += 1
            return pd.DataFrame()
        original = panel.im.exportar_desde_dataframe
        original_prepare = panel.im.preparar_modulos_desde_resultado
        panel.im.preparar_modulos_desde_resultado = lambda *a, **k: pd.DataFrame({'modulo': [1]})
        def export(frame, output, **kwargs):
            calls['export'] += 1
            output.write(b'xlsx fixture')
        panel.im.exportar_desde_dataframe = export
        try:
            app = Dash(__name__, suppress_callback_exceptions=True)
            panel.register_callbacks(app, report_quality_loader=quality,
                                      report_extra_loader=lambda *args: pd.DataFrame())
            from unittest.mock import patch
            engine_patch = patch.object(panel.dbs, 'get_engine', return_value=None)
            engine_patch.start()
            fn = next(v['callback'].__wrapped__ for k, v in app.callback_map.items()
                      if 'reconstitucion-informe-download.data' in k)
            first = fn(1, token, 2, 741, [case])
            second = fn(2, token, 2, 741, [case])
        finally:
            panel.im.exportar_desde_dataframe = original
            panel.im.preparar_modulos_desde_resultado = original_prepare
            engine_patch.stop()
        self.assertEqual(calls, {'quality': 1, 'export': 1})
        self.assertEqual(first[0]['content'], second[0]['content'])

    def test_fuente_extra_fallida_no_cachea_y_permite_reintento(self):
        calls = {"extra": 0, "export": 0}
        case = dict(id=742, nombre="caso", run_id=89,
                    fecha_inicio="2026-08-01", fecha_fin="2026-08-03")
        res = sample()
        res.update(caso=case, fuente_modelo={"id": 742, "run_id": 89},
                   apilado=pd.DataFrame({"pad_id": [2], "vol_diario": [10]}))
        token = panel.remember(res)
        def quality(*args, **kwargs):
            return pd.DataFrame()
        def extras(*args):
            calls["extra"] += 1
            return pd.DataFrame([{"modulo": 1,
                "advertencias_fuentes": "No se pudo consultar movcam; sus atributos quedan sin dato."}])
        def prepare(*args, **kwargs):
            return kwargs["extras"]
        original_export = panel.im.exportar_desde_dataframe
        original_prepare = panel.im.preparar_modulos_desde_resultado
        def export(frame, output, **kwargs):
            calls["export"] += 1
            output.write(b"partial workbook")
        panel.im.exportar_desde_dataframe = export
        panel.im.preparar_modulos_desde_resultado = prepare
        try:
            app = Dash(__name__, suppress_callback_exceptions=True)
            panel.register_callbacks(app, report_quality_loader=quality,
                                     report_extra_loader=extras)
            from unittest.mock import patch
            engine_patch = patch.object(panel.dbs, "get_engine", return_value=None)
            engine_patch.start()
            fn = next(v["callback"].__wrapped__ for k, v in app.callback_map.items()
                      if "reconstitucion-informe-download.data" in k)
            first = fn(1, token, 2, 742, [case])
            second = fn(2, token, 2, 742, [case])
        finally:
            panel.im.exportar_desde_dataframe = original_export
            panel.im.preparar_modulos_desde_resultado = original_prepare
            engine_patch.stop()
        self.assertEqual(calls, {"extra": 2, "export": 2})
        self.assertIn("Hay fuentes sin consultar", first[1])
        self.assertNotIn(2, res.get("_informe_modulos_por_pad", {}))
        self.assertNotIn(2, res.get("_informe_xlsx_por_pad", {}))
        self.assertEqual(first[0]["content"], second[0]["content"])

    def test_gantt_sin_horario_conserva_ventanas_medidas(self):
        fig = panel.fig_gantt(sample())
        self.assertEqual(len(fig.data), 0)
        self.assertIn('Sin horario', fig.layout.title.text)

    def test_gantt_reproduce_dos_carriles_medidos_y_reconstruidos(self):
        fig = panel.fig_gantt(sample(with_timeline=True))
        self.assertEqual(len(fig.data), 1)
        estimated, = fig.data
        self.assertEqual(estimated.name, 'Reconstituido')
        self.assertEqual(estimated.marker.color.lower(), '#3b82f6')
        self.assertEqual(len(estimated.x), 2)
        self.assertEqual(len(set(estimated.y)), 2)
        self.assertEqual(fig.layout.xaxis.tickformat, '%d-%m')
        self.assertTrue(fig.layout.shapes)

    def test_tabs_pad_unicos_y_sin_selectores_dropdown(self):
        tree = panel.build_layout()
        nodes = walk_components(tree)
        ids = {getattr(node, 'id', None) for node in nodes}
        self.assertIn('reconstitucion-pad-tabs', ids)
        self.assertNotIn('reconstitucion-grupo', ids)
        self.assertNotIn('reconstitucion-informe-pad', ids)
        tabs = next(node for node in nodes if getattr(node, 'id', None) == 'reconstitucion-pad-tabs')
        self.assertEqual(tabs.value, '2')
        self.assertEqual([(tab.label, tab.value) for tab in tabs.children], [('\u00d3xidos', '1'), ('Sulfuros', '2')])

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
        self.assertEqual(len(loaded), 2)
        self.assertIn(loaded[0], panel._results)


if __name__ == '__main__':
    unittest.main()



