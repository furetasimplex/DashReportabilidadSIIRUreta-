"""Pruebas del ensamblado SIIR mediante HTTP local, sin conexión SQL."""
import importlib
import json
import unittest
from unittest.mock import patch

import pandas as pd
from plotly.utils import PlotlyJSONEncoder
from sqlalchemy.engine import Engine


def ids(tree):
    found = []
    if isinstance(tree, dict):
        if 'props' in tree and 'id' in tree['props']:
            value = tree['props']['id']
            found.append(json.dumps(value, sort_keys=True) if isinstance(value, dict) else value)
        for value in tree.values():
            found.extend(ids(value))
    elif isinstance(tree, list):
        for value in tree:
            found.extend(ids(value))
    return found


def fake_data(module, **_):
    module.DATA_OX = module.DATA_SU = {}
    module.CYCLES_OX = module.CYCLES_SU = {}
    module.GLOBAL_MIN_DATE = pd.Timestamp('2026-07-01')
    module.GLOBAL_MAX_DATE = module.JOINT_DATA_CUTOFF = pd.Timestamp('2026-08-23')
    module.MAX_CAMPANAS = 1
    module.CAMPANA_OPTIONS = [{'label': 'Campaña 1', 'value': 1}]
    module.CASOS = [dict(id=1, nombre='Ejemplo local', run_id=1,
                         fecha_inicio=pd.Timestamp('2026-08-01'),
                         fecha_fin=pd.Timestamp('2026-08-08'))]
    module.CASO_OPTIONS = [{'label': '#1 Ejemplo local', 'value': 1}]
    module.DEFAULT_CASO_ID = 1
    module.DEFAULT_WEEK_STR = '2026-08-01'
    module.WIP_META = {'OXIDOS': {}, 'SULFUROS': {}}
    module.REC_META = {'OXIDOS': ({}, {}, {}), 'SULFUROS': ({}, {}, {})}
    module.RAW_CURVES_BY_MATERIAL = {'OXIDOS': {}, 'SULFUROS': {}}
    module.RECON_PRODUCCION = pd.Series(dtype=float)
    module._ACTIVE_OX = module._ACTIVE_SU = set()


class IntegracionSIIR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block = patch.object(Engine, 'connect', side_effect=AssertionError('SQL prohibido en prueba'))
        cls.sql = cls.block.start()
        # Production startup validation stays enabled; only the offline fixture bypasses it.
        import os
        cls.env = patch.dict(os.environ, {'SECRET_KEY': 'offline-fixture',
                                         'LOGIN_DATABASE': 'offline.dbo.auth_user'})
        cls.env.start()
        # Simulate a fresh process even when module tests ran earlier in pytest.
        importlib.reload(importlib.import_module('curvas_recon.pad_dashboard'))
        with patch('env_loader.load_app_env'), patch('db_startup_check.run_startup_db_check'):
            cls.raw_block = patch('pyodbc.connect', side_effect=AssertionError('ODBC prohibido en prueba'))
            cls.raw_sql = cls.raw_block.start()
            cls.host_connection = patch('db_connection.get_connection', return_value=None)
            cls.host_connection.start()
            cls.main = importlib.import_module('main')
        cls.module = importlib.import_module('curvas_recon.pad_dashboard')
        cls.app = cls.main.app
        cls.client = cls.main.server.test_client()
        with cls.client.session_transaction() as session:
            session['user'] = 'prueba-local'
            session['username'] = 'Prueba local'
        cls.app.server.config['TESTING'] = True
        cls.client.get('/_dash-layout')

    @classmethod
    def tearDownClass(cls):
        cls.block.stop()
        cls.env.stop()
        cls.host_connection.stop()
        cls.raw_block.stop()

    def callback(self, output_id, inputs, state=(), changed=None):
        key, meta = next((k, v) for k, v in self.app.callback_map.items()
                         if output_id in k)
        outputs = meta['output']
        if any(item['id'] == 'nav-reconstitucion' for item in meta['inputs']):
            # Alinea el fixture con la firma del menú, incluyendo secciones lazy.
            input_values = {(i['id'], i['property']): i['value'] for i in inputs}
            state_values = {(i['id'], i['property']): i['value'] for i in state}
            inputs = [dict(i, value=input_values.get((i['id'], i['property']), 0))
                      for i in meta['inputs']]
            state = [dict(i, value=state_values.get((i['id'], i['property'])))
                     for i in meta['state']]
        outputs = ([dict(id=o.component_id, property=o.component_property) for o in outputs]
                   if isinstance(outputs, list) else
                   dict(id=outputs.component_id, property=outputs.component_property))
        payload = dict(output=key, outputs=outputs, inputs=inputs, state=list(state),
                       changedPropIds=changed or [])
        response = self.client.post('/_dash-update-component', json=payload)
        self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:400])
        return response.get_json()['response']

    def test_01_inicio_no_consulta_sql_y_conserva_reportabilidad(self):
        self.assertFalse(self.module._DATA_READY)
        response = self.client.get('/_dash-layout')
        all_ids = ids(response.get_json())
        self.assertIn('nav-reportabilidad', all_ids)
        self.assertIn('nav-curvas-recon', all_ids)
        for nav in ('nav-reclamo', 'nav-powerbi', 'nav-monitor-pitum',
                    'nav-lixiviacion', 'nav-polinomio-acido'):
            self.assertIn(nav, all_ids)
        self.assertIn('report-fecha-inicio', all_ids)
        self.assertNotIn('curvas-recon-caso', all_ids)
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_02_autenticacion_sigue_activa(self):
        response = self.main.server.test_client().get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login_page', response.location)

    def test_03_navegacion_monta_solo_shell_y_retorna(self):
        inputs = [dict(id=nav, property='n_clicks', value=int(nav == 'nav-curvas-recon'))
                  for nav in ('nav-reportabilidad', 'nav-reclamo', 'nav-powerbi',
                              'nav-monitor-pitum', 'nav-lixiviacion',
                              'nav-polinomio-acido', 'nav-curvas-recon')]
        state = [dict(id='subtabs-curvas-recon', property='children', value=None)]
        result = self.callback('subtabs-curvas-recon.style', inputs, state,
                               ['nav-curvas-recon.n_clicks'])
        mounted = result['subtabs-curvas-recon']['children']
        self.assertIn('curvas-recon-root', ids(mounted))
        self.assertEqual(result['subtabs-report']['style']['display'], 'none')
        state[0]['value'] = mounted
        inputs[0]['value'] = 1
        result = self.callback('subtabs-curvas-recon.style', inputs, state,
                               ['nav-reportabilidad.n_clicks'])
        self.assertEqual(result['subtabs-report']['style']['display'], 'block')
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_04_carga_dinamica_sin_colisiones(self):
        self.module._DATA_READY = False
        fake_data(self.module)
        with patch.object(self.module, '_load_caso_options',
                          return_value=(self.module.CASOS, self.module.CASO_OPTIONS, self.module.DEFAULT_CASO_ID)):
            result = self.callback('curvas-recon-content.children', [
                dict(id='curvas-recon-load-trigger', property='n_intervals', value=1),
                dict(id='curvas-recon-retry', property='n_clicks', value=0)],
                changed=['curvas-recon-load-trigger.n_intervals'])
        dynamic = ids(result['curvas-recon-content']['children'])
        static = ids(self.client.get('/_dash-layout').get_json())
        self.assertIn('curvas-recon-caso', dynamic)
        self.assertEqual(len(dynamic), len(set(dynamic)))
        self.assertFalse(set(dynamic) & set(static))
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_05_error_generico_y_reintento(self):
        with patch.object(self.module, 'initialize_data', side_effect=RuntimeError('SQL_URL secreto-no-mostrar')):
            result = self.callback('curvas-recon-content.children', [
                dict(id='curvas-recon-load-trigger', property='n_intervals', value=1),
                dict(id='curvas-recon-retry', property='n_clicks', value=1)],
                changed=['curvas-recon-retry.n_clicks'])
        serialized = json.dumps(result, ensure_ascii=False)
        self.assertIn('No se pudieron cargar', serialized)
        self.assertNotIn('secreto-no-mostrar', serialized)
        shell = json.loads(json.dumps(self.module.build_layout(), cls=PlotlyJSONEncoder))
        self.assertIn('curvas-recon-retry', ids(shell))

    def test_06_secciones_actualizadas_siguen_navegables(self):
        mapping = {'reportabilidad': 'report', 'reclamo': 'reclamo',
                   'powerbi': 'powerbi', 'monitor-pitum': 'monitor-pitum',
                   'lixiviacion': 'lixiviacion', 'polinomio-acido': 'polinomio-acido'}
        for section, panel in mapping.items():
            inputs = [dict(id='nav-' + name, property='n_clicks', value=int(name == section))
                      for name in (*mapping, 'curvas-recon')]
            result = self.callback('subtabs-curvas-recon.style', inputs,
                                   [dict(id='subtabs-curvas-recon', property='children', value=None)],
                                   ['nav-' + section + '.n_clicks'])
            self.assertEqual(result['subtabs-' + panel]['style']['display'], 'block')
            self.assertEqual(result['subtabs-curvas-recon']['style']['display'], 'none')
            self.assertEqual(result['nav-' + section]['className'], 'siir-nav-link active')
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_07_registro_idempotente(self):
        count = len(self.app.callback_map)
        self.module.register_callbacks(self.app)
        self.assertEqual(count, len(self.app.callback_map))


    def test_08_consideraciones_abre_y_cierra_sin_sql(self):
        self.module._DATA_READY = True
        inputs = [dict(id='curvas-recon-consideraciones-btn', property='n_clicks', value=1),
                  dict(id='curvas-recon-consideraciones-close', property='n_clicks', value=0)]
        result = self.callback('curvas-recon-consideraciones-modal.is_open', inputs,
                               changed=['curvas-recon-consideraciones-btn.n_clicks'])
        self.assertTrue(result['curvas-recon-consideraciones-modal']['is_open'])
        inputs[1]['value'] = 1
        result = self.callback('curvas-recon-consideraciones-modal.is_open', inputs,
                               changed=['curvas-recon-consideraciones-close.n_clicks'])
        self.assertFalse(result['curvas-recon-consideraciones-modal']['is_open'])
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_09_seleccion_actualiza_solo_graficos_y_bordes(self):
        self.module._DATA_READY = True
        data = dict(caso_id=1, week_start='2026-08-01', week_end='2026-08-08', n_days=8)
        names = ('_build_recovery_chart', '_build_flujo_chart', '_build_pila_chart')
        with patch.object(self.module, 'ensure_full_data'), \
             patch.object(self.module, names[0], return_value={'data': []}), \
             patch.object(self.module, names[1], return_value={'data': []}), \
             patch.object(self.module, names[2], return_value={'data': []}):
            result = self.callback('curvas-recon-chart-rec.figure', [
                dict(id='curvas-recon-store', property='data', value=data),
                dict(id='curvas-recon-pila-store', property='data', value='rox-P23'),
                dict(id='curvas-recon-caso', property='value', value=1)],
                changed=['curvas-recon-pila-store.data'])
        self.assertEqual(set(result), {'curvas-recon-chart-rec', 'curvas-recon-chart-flujo',
                                       'curvas-recon-chart-cus'})
        grid = next(v for k, v in self.app.callback_map.items()
                    if 'curvas-recon-grid-container.children' in k)
        self.assertNotIn('curvas-recon-pila-store', [i['id'] for i in grid['inputs']])
        with patch.object(self.module, '_ACTIVE_OX', {23, 24}):
            styles = self.module.highlight_recon_pila('rox-P23', None, [],
                        {'OXIDOS': {'ss': ['P23', 'P24']}},
                        [dict(pad='rox', num=23), dict(pad='rox', num=24)],
                        [{'backgroundColor': 'green'}, {'backgroundColor': 'orange'}])
        self.assertEqual(styles[0]['border'], '2px solid #f57c00')
        self.assertEqual(styles[1]['border'], '2px solid #ced4da')
        self.assertEqual(styles[0]['backgroundColor'], self.module.RECON_STATUS_COLORS['activa'])
        self.sql.assert_not_called()

    def test_10_carga_global_solo_observa_montaje_y_avisos_en_modal(self):
        shell = self.module.build_layout()
        loading = shell.children[-1]
        self.assertEqual(loading.target_components, {'curvas-recon-content': 'children'})
        fake_data(self.module)
        tree = json.loads(json.dumps(self.module._build_content_layout(), cls=PlotlyJSONEncoder))
        def find(node, target):
            if isinstance(node, dict):
                if node.get('props', {}).get('id') == target:
                    return node
                for value in node.values():
                    found = find(value, target)
                    if found:
                        return found
            elif isinstance(node, list):
                for value in node:
                    found = find(value, target)
                    if found:
                        return found
        modal = find(tree, 'curvas-recon-consideraciones-modal')
        self.assertFalse(modal['props']['is_open'])
        self.assertIn('curvas-recon-warnings', ids(modal))
        self.assertNotIn('curvas-recon-freshness', ids(tree))
        self.assertNotIn('curvas-recon-sync-btn', ids(tree))
        self.assertEqual(ids(tree).count('curvas-recon-warnings'), 1)


    def test_11_calculo_indica_progreso_y_restauracion_en_cliente(self):
        response = self.client.get('/_dash-dependencies')
        self.assertEqual(response.status_code, 200)
        calculation = next(
            item for item in response.get_json()
            if any(i['id'] == 'curvas-recon-btn' for i in item['inputs'])
            and 'curvas-recon-store.data' in str(item['output'])
        )
        # The calculation now updates the result store and error modal together.
        self.assertIn('curvas-recon-error-modal.is_open', str(calculation['output']))
        self.assertIn('curvas-recon-error-body.children', str(calculation['output']))
        # Dash applies runningOff when the request finishes, including failures.
        self.assertEqual(calculation['running'], {
            'running': {'curvas-recon-btn.disabled': True,
                        'curvas-recon-btn.children': 'Calculando\u2026'},
            'runningOff': {'curvas-recon-btn.disabled': False,
                           'curvas-recon-btn.children': 'Ejecutar c\u00e1lculo'},
        })
        self.assertTrue(calculation['prevent_initial_call'])
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_12_reconstitucion_montaje_ida_vuelta_y_preserva_arboles(self):
        def navigate(section, mounted=None):
            return self.callback('subtabs-curvas-recon.style',
                [dict(id='nav-' + section, property='n_clicks', value=1)],
                [dict(id='subtabs-reconstitucion', property='children', value=mounted)],
                ['nav-' + section + '.n_clicks'])
        static_ids = ids(self.client.get('/_dash-layout').get_json())
        self.assertIn('nav-reconstitucion', static_ids)
        self.assertNotIn('reconstitucion-cargar', static_ids)
        opened = navigate('reconstitucion')
        mounted = opened['subtabs-reconstitucion']['children']
        mounted_ids = ids(mounted)
        self.assertIn('reconstitucion-cargar', mounted_ids)
        self.assertIn('reconstitucion-caso', mounted_ids)
        self.assertIn('reconstitucion-actualizar-casos', mounted_ids)
        self.assertEqual(len(mounted_ids), len(set(mounted_ids)))
        self.assertFalse(set(mounted_ids) & set(static_ids))
        self.assertEqual(opened['siir-bc-active']['children'], 'RECONSTITUCIÓN DE MÓDULOS')
        self.assertEqual(opened['nav-reconstitucion']['className'], 'siir-nav-link active')
        self.assertEqual(opened['subtabs-report']['style'], {'display': 'none'})
        returned = navigate('reportabilidad', mounted)
        self.assertEqual(returned['subtabs-report']['style'], {'display': 'block'})
        self.assertEqual(returned['subtabs-reconstitucion']['style'], {'display': 'none'})
        self.assertNotIn('children', returned['subtabs-reconstitucion'])
        reopened = navigate('reconstitucion', mounted)
        self.assertEqual(reopened['subtabs-reconstitucion']['style'], {'display': 'block'})
        self.assertNotIn('children', reopened['subtabs-reconstitucion'])
        curves = navigate('curvas-recon', mounted)
        self.assertIn('curvas-recon-root', ids(curves['subtabs-curvas-recon']['children']))
        self.assertEqual(curves['subtabs-reconstitucion']['style'], {'display': 'none'})
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_13_reconstitucion_registro_esquema_lazy_y_progreso(self):
        from tabs import tab_reconstitucion as bridge
        from reconstitucion import db_source
        count = len(self.app.callback_map)
        bridge.register_callbacks(self.app)
        self.assertEqual(len(self.app.callback_map), count)
        self.assertEqual(db_source.SCHEMA, 'inventar_SpcHidr.inventar_SpcHidr')
        with patch('db_connection.get_engine', return_value='fixture-engine') as provider:
            with patch.object(bridge, '_host_casos') as cases:
                bridge.layout()
                cases.assert_not_called()
            provider.assert_not_called()
            self.assertEqual(db_source.get_engine(), 'fixture-engine')
            provider.assert_called_once_with()
        deps = self.client.get('/_dash-dependencies').get_json()
        loading = next(d for d in deps if 'reconstitucion-token.data' in d['output'])
        self.assertTrue(loading['prevent_initial_call'])
        self.assertEqual(loading['running']['running']['reconstitucion-cargar.children'], 'Calculando…')
        self.assertTrue(loading['running']['running']['reconstitucion-cargar.disabled'])
        self.assertEqual(loading['running']['runningOff']['reconstitucion-cargar.children'], 'Cargar datos')
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

    def test_14_reconstitucion_caso_requerido_y_modal_sin_sql(self):
        result = self.callback('reconstitucion-token.data',
            [dict(id='reconstitucion-cargar', property='n_clicks', value=1)],
            [dict(id='reconstitucion-caso', property='value', value=None),
             dict(id='reconstitucion-casos', property='data', value=None)],
            ['reconstitucion-cargar.n_clicks'])
        self.assertIn('Selecciona un Caso oficial', result['reconstitucion-estado']['children'])
        result = self.callback('reconstitucion-resultados.children', [
            dict(id='reconstitucion-token', property='data', value=None),
            dict(id='reconstitucion-pad-tabs', property='value', value='2'),
            dict(id='reconstitucion-caso', property='value', value=None),
            dict(id='reconstitucion-casos', property='data', value=None)])
        self.assertIsNone(result['reconstitucion-resultados']['children'])
        for action, display in [('reconstitucion-consideraciones', 'flex'), ('reconstitucion-cerrar', 'none')]:
            result = self.callback('reconstitucion-modal.style', [
                dict(id='reconstitucion-consideraciones', property='n_clicks', value=1),
                dict(id='reconstitucion-cerrar', property='n_clicks', value=int(display == 'none'))],
                changed=[action + '.n_clicks'])
            self.assertEqual(result['reconstitucion-modal']['style']['display'], display)
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()


    def test_15_reconstitucion_catalogo_oficial_y_fechas_por_http(self):
        case = dict(id=8, nombre='Caso oficial', fecha_inicio=pd.Timestamp('2026-08-22'),
                    fecha_fin=pd.Timestamp('2026-08-31'), estado='cerrado', run_id=80)
        with patch('curvas_recon.db_pipeline.load_casos', return_value=[case]) as source:
            result = self.callback('reconstitucion-casos.data',
                [dict(id='reconstitucion-iniciar-casos', property='n_intervals', value=1)],
                [dict(id='reconstitucion-caso', property='value', value=None)],
                changed=['reconstitucion-iniciar-casos.n_intervals'])
        source.assert_called_once_with()
        self.assertEqual(result['reconstitucion-caso']['value'], 8)
        catalog = result['reconstitucion-casos']['data']
        self.assertEqual(catalog[0]['run_id'], 80)
        recon_panel = importlib.import_module('reconstitucion.panel')
        layout = json.loads(json.dumps(recon_panel.build_layout(), cls=PlotlyJSONEncoder))
        layout_ids = ids(layout)
        self.assertIn('reconstitucion-caso', layout_ids)
        self.assertIn('reconstitucion-pad-tabs', layout_ids)
        self.assertNotIn('reconstitucion-rango', layout_ids)
        dependencies = self.client.get('/_dash-dependencies').get_json()
        self.assertFalse(any('reconstitucion-rango' in d['output'] or
                             any(i['id'] == 'reconstitucion-rango' for i in d['inputs'])
                             for d in dependencies))
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()


    def test_14_reportes_recon_montaje_lazy_sin_sql(self):
        def navigate(section, mounted=None):
            return self.callback('subtabs-curvas-recon.style',
                [dict(id='nav-' + section, property='n_clicks', value=1)],
                [dict(id='subtabs-reportes-recon', property='children', value=mounted)],
                ['nav-' + section + '.n_clicks'])
        static_ids = ids(self.client.get('/_dash-layout').get_json())
        self.assertIn('nav-reportes-recon', static_ids)
        self.assertNotIn('reportes-recon-generar', static_ids)
        opened = navigate('reportes-recon')
        mounted = opened['subtabs-reportes-recon']['children']
        mounted_ids = ids(mounted)
        self.assertIn('reportes-recon-generar', mounted_ids)
        self.assertEqual(len(mounted_ids), len(set(mounted_ids)))
        self.assertFalse(set(mounted_ids) & set(static_ids))
        self.assertEqual(opened['siir-bc-active']['children'], 'REPORTES DE RECONCILIACIÓN')
        self.assertEqual(opened['nav-reportes-recon']['className'], 'siir-nav-link active')
        self.assertEqual(opened['subtabs-reconstitucion']['style'], {'display': 'none'})
        reopened = navigate('reportes-recon', mounted)
        self.assertNotIn('children', reopened['subtabs-reportes-recon'])
        back = navigate('reportabilidad', mounted)
        self.assertEqual(back['subtabs-reportes-recon']['style'], {'display': 'none'})
        self.sql.assert_not_called()
        self.raw_sql.assert_not_called()

if __name__ == '__main__':
    unittest.main()
