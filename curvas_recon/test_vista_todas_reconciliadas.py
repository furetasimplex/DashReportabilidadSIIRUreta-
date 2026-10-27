import importlib.util
import pathlib
import unittest

import pandas as pd

from . import vista_todas_reconciliadas as vista


class VistaTodasReconciliadasTests(unittest.TestCase):
    def setUp(self):
        with vista._LOCK:
            vista._CACHE.clear()
        self.store = {'caso_id': 5, 'caso_run_id': 17, 'raw_token': 't1',
                      'week_start': '2026-01-08', 'week_end': '2026-01-10'}
        self.raw = {'caso': {'id': 5, 'run_id': 17}, 'res': {'piles': [
            {'label': 'OXIDOS', 'parcela': 1}, {'label': 'OXIDOS', 'parcela': 1},
            {'label': 'SULFUROS', 'parcela': 2}, {'label': 'VIRTUAL', 'parcela': 9}]}}

    def test_stale_store_rejected_before_data_load(self):
        calls = []
        result, msg = vista.build_dataset({**self.store, 'caso_run_id': 16}, 5,
            get_raw=lambda *_: calls.append('raw'), ensure_full_data=lambda: calls.append('full'),
            wip_meta={}, reconstruct=lambda *a, **k: {}, load_material=lambda *a: {})
        self.assertIsNone(result)
        self.assertIn('válidos', msg)
        self.assertEqual(calls, ['raw'])

    def test_shared_pad_material_loaded_once_and_virtual_dropped(self):
        frames = {'OXIDOS': pd.DataFrame({'P01': [1, 0]}, index=pd.date_range('2026-01-01', periods=2)),
                  'SULFUROS': pd.DataFrame({'P02': [1, 1]}, index=pd.date_range('2026-01-01', periods=2))}
        calls = []
        def load(label, start, end):
            calls.append((label, start, end))
            return {'riego': frames.get(label, pd.DataFrame())}
        def reconstruct(label, num, ws, we, **kwargs):
            self.assertIs(kwargs['raw'], self.raw)
            self.assertIsNotNone(kwargs['material'])
            return {'xs': [pd.Timestamp('2026-01-01'), pd.Timestamp('2026-01-08')],
                    'ys': [10, 20], 'sources': ['Histórico reconciliado', 'Reconciliado del Caso']}
        dataset, msg = vista.build_dataset(self.store, 5, get_raw=lambda *_: self.raw,
            ensure_full_data=lambda: None, wip_meta={'OXIDOS': {'P01': {'ini_aporte': '2026-01-01'}},
                'SULFUROS': {'P02': {'ini_aporte': '2026-01-01'}}},
            reconstruct=reconstruct, load_material=load)
        self.assertEqual(msg, '')
        self.assertEqual([len(dataset['groups'][x]) for x in ('OXIDOS', 'SULFUROS')], [1, 1])
        self.assertEqual(len(calls), 2)
        self.assertEqual(dataset['groups']['OXIDOS'][0]['start'], pd.Timestamp('2026-01-01'))

    def test_slider_bounds_filter_only_selected_pad_and_reconciled_sources(self):
        end = pd.Timestamp('2026-01-10')
        dataset = {'case_end': end, 'groups': {
            'OXIDOS': [{'num': 1, 'start': pd.Timestamp('2026-01-01'),
                'xs': [pd.Timestamp('2026-01-01'), pd.Timestamp('2026-01-05'), end],
                'ys': [10, None, 20], 'sources': ['Histórico reconciliado', '', 'Reconciliado del Caso']}],
            'SULFUROS': [{'num': 2, 'start': pd.Timestamp('2026-01-06'),
                'xs': [pd.Timestamp('2026-01-06'), end], 'ys': [30, 40],
                'sources': ['Histórico reconciliado', 'Reconciliado del Caso']} ]}}
        ox = vista.make_figure(dataset, 'OXIDOS', [0, 9])
        su = vista.make_figure(dataset, 'SULFUROS', [0, 4])
        self.assertEqual(list(ox.data[0].x), [0, 4, 9])
        self.assertEqual(list(ox.data[0].y), [10, None, 20])
        self.assertEqual(list(su.data[0].x), [0, 4])
        self.assertEqual(list(su.data[0].y), [30, 40])
        self.assertIn('primer riego', ox.layout.xaxis.title.text)

    def test_json_roundtrip_store_identity(self):
        import json
        payload = {'identity': vista.store_identity(self.store, 5)}
        restored = json.loads(json.dumps(payload))
        self.assertEqual(tuple(restored['identity']), vista.store_identity(self.store, 5))


if __name__ == '__main__':
    unittest.main()
