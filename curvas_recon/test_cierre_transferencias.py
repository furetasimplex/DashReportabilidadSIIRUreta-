"""Regression checks for absolute 125-flow net Cu closure, without SQL."""
import json
import unittest
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from . import db_pipeline, recon_engine as E


class NetTransferTargetTests(unittest.TestCase):
    def test_model125_adapter_keeps_components_and_reads_absolute_F25_F29(self):
        fixture = json.loads(
            (Path(__file__).parent / 'fixtures' / 'modelo125_run10104.json')
            .read_text(encoding='utf-8'))
        by_code = {r['codigo_flujo']: r for r in fixture['flujos_run']}
        captured = {}

        def read_rows(_engine, _query, params, **_kwargs):
            captured['codes'] = {v for k, v in params.items() if k.startswith('c')}
            return [(code, row['masa_medida'], row['masa_reconciliada'],
                     row['fino_cu_medido'], row['fino_cu_reconciliado'])
                    for code, row in by_code.items() if code in captured['codes']]

        with patch.object(db_pipeline, '_engine', object()), \
                patch.object(db_pipeline, '_sql_rows', read_rows):
            anchor = db_pipeline.load_caso_anchor(
                10104, 'hidrometalurgia_125_v2', 'v2', 125)

        self.assertTrue({'F70', 'F60', 'F81', 'F44', 'F45',
                         'F72', 'F66', 'F47', 'F48', 'F49', 'F25', 'F29'}
                        .issubset(captured['codes']))
        self.assertEqual(anchor['OXIDOS']['net_cu_target_flow'], 'F25')
        self.assertEqual(anchor['SULFUROS']['net_cu_target_flow'], 'F29')
        self.assertEqual(anchor['OXIDOS']['net_cu_target_t'],
                         float(by_code['F25']['fino_cu_reconciliado']))
        self.assertEqual(anchor['SULFUROS']['net_cu_target_t'],
                         float(by_code['F29']['fino_cu_reconciliado']))
        # F29's authoritative target remains distinct from the component net.
        component_net = sum(float(by_code[c]['fino_cu_reconciliado'])
                            for c in ('F47', 'F48', 'F49')) - sum(
                                float(by_code[c]['fino_cu_reconciliado'])
                                for c in ('F72', 'F66'))
        self.assertNotAlmostEqual(anchor['SULFUROS']['net_cu_target_t'],
                                  component_net)
        self.assertEqual(db_pipeline.diagnose_caso_anchor(anchor), [])

    def test_legacy_120_mapping_remains_component_only(self):
        mapping, _ = db_pipeline._caso_flows_for_model(
            'hidrometalurgia_120_completo', 'v1', 120)
        self.assertEqual(mapping, db_pipeline.CASO_FLUJOS_120)
        legacy = {pad: {key: 1.0 for key in db_pipeline.CASO_ANCHOR_KEYS}
                  for pad in ('OXIDOS', 'SULFUROS')}
        self.assertEqual(db_pipeline.diagnose_caso_anchor(legacy), [])

    def test_missing_or_nonfinite_125_net_target_invalidates_anchor(self):
        anchor = {pad: {key: 1.0 for key in db_pipeline.CASO_ANCHOR_KEYS}
                  for pad in ('OXIDOS', 'SULFUROS')}
        for pad, flow in (('OXIDOS', 'F25'), ('SULFUROS', 'F29')):
            anchor[pad].update(net_cu_target_flow=flow, net_cu_target_t=1.0)
        self.assertEqual(db_pipeline.diagnose_caso_anchor(anchor), [])
        for bad in (None, float('nan'), float('inf')):
            invalid = deepcopy(anchor)
            invalid['SULFUROS']['net_cu_target_t'] = bad
            self.assertTrue(db_pipeline.diagnose_caso_anchor(invalid))

    def test_reconcile_real_daily_path_closes_two_pads_at_varied_durations(self):
        start = pd.Timestamp('2026-10-01')
        net_targets = {'OXIDOS': 2.5, 'SULFUROS': -0.2}
        for n_days in (1, 7, 12):
            E.limpiar_estado_rampa()
            end = start + pd.Timedelta(days=n_days - 1)
            dates = pd.date_range(start, end, freq='D')
            materials = {}
            for label in ('OXIDOS', 'SULFUROS'):
                materials[label] = {
                    'wip': {}, 'rec_curves': {}, 'max_rec': {}, 'ciclo_d': {},
                    'riego': pd.DataFrame({'P01': 100.0}, index=dates),
                    'cu_riego': pd.Series(1.0, index=dates),
                    'drena_cu': pd.DataFrame({'P01': 2.0}, index=dates),
                }
            anchor = {}
            for label, target in net_targets.items():
                q_riego = n_days * 100.0
                q_pls = q_riego * E.FDRENA_MAX
                anchor[label] = {
                    'q_riego_medido': q_riego, 'q_riego_recon': q_riego * 1.02,
                    'q_pls_medido': q_pls, 'q_pls_recon': q_pls * 1.01,
                    'fino_riego_medido': q_riego,
                    'fino_riego_recon': q_riego * 1.03,
                    'fino_pls_medido': q_pls * 2.0,
                    'fino_pls_recon': q_pls * 1.98,
                    'net_cu_target_t': target,
                    'net_cu_target_flow': 'F25' if label == 'OXIDOS' else 'F29',
                }

            def classify(_start, _wip, _curves, _max_rec, _cycle, **_kwargs):
                return ['P01'], [], [], {'P01': 100}, {'P01': 1.0}

            def campaign(label, _end):
                return {'P01': start - pd.Timedelta(days=100)}

            with patch.object(E, 'classify_piles', side_effect=classify), \
                    patch.object(E, 'inicio_campana', side_effect=campaign), \
                    patch.object(E, 'arranque_en_ventana', return_value={}), \
                    patch.object(E, '_campaign_asof', return_value=100):
                result = E.reconcile_flowsheet(
                    start, materials, force_all_active=True, week_end=end,
                    anchor=anchor)

            self.assertEqual(set(result['net_cu_by_label']), set(net_targets))
            for label, target in net_targets.items():
                rows = [d for d in result['daily'] if d['label'] == label]
                actual = E._daily_net_cu_t(rows)
                self.assertAlmostEqual(actual, target, places=9)
                self.assertAlmostEqual(result['net_cu_by_label'][label]['target_t'], target)
                self.assertAlmostEqual(result['net_cu_by_label'][label]['daily_t'], target,
                                       places=9)
                for d in rows:
                    self.assertLessEqual(d['q_pls_final'], d['q_riego_final'] * .99 + 1e-8)
                    if d['q_pls_final'] > 0:
                        self.assertAlmostEqual(d['q_pls_final'] * d['cu_pls_recon'],
                                               d['fino_pls_final'], places=8)

    def test_flujos_globales_sin_cambio_no_mueven_ninguna_pila(self):
        """Si el global reconciliado = medido, el pad queda en lo medido aunque el neto de las pilas no sea F25."""
        start = pd.Timestamp('2026-10-01')
        dates = pd.date_range(start, periods=3, freq='D')
        materials = {'OXIDOS': {
            'wip': {}, 'rec_curves': {}, 'max_rec': {}, 'ciclo_d': {},
            'riego': pd.DataFrame({'P01': 100.0, 'P02': 50.0}, index=dates),
            'cu_riego': pd.Series(0.3, index=dates),
            'drena_cu': pd.DataFrame({'P01': 2.0, 'P02': 1.0}, index=dates),
        }}
        q_riego = 3 * 150.0
        q_pls = q_riego * E.FDRENA_MAX
        anchor = {'OXIDOS': {
            'q_riego_medido': q_riego, 'q_riego_recon': q_riego * 1.0005,
            'q_pls_medido': q_pls, 'q_pls_recon': q_pls,
            'fino_riego_medido': 100.0, 'fino_riego_recon': 100.0,
            'fino_pls_medido': 257.0, 'fino_pls_recon': 257.0,
            'net_cu_target_t': 157.0, 'net_cu_target_flow': 'F25',     # el neto de las pilas es otro
        }}
        self.assertTrue(E._anchor_unchanged(anchor['OXIDOS']))
        changed = {'OXIDOS': dict(anchor['OXIDOS'], fino_pls_recon=260.0, net_cu_target_t=160.0)}
        self.assertFalse(E._anchor_unchanged(changed['OXIDOS']))

        def classify(_start, _wip, _curves, _max_rec, _cycle, **_kwargs):
            return ['P01', 'P02'], [], [], {'P01': 100, 'P02': 100}, {'P01': 1.0, 'P02': 1.0}

        E.limpiar_estado_rampa()
        end = dates[-1]
        with patch.object(E, 'classify_piles', side_effect=classify), \
                patch.object(E, 'inicio_campana', return_value={'P01': start - pd.Timedelta(days=100),
                                                              'P02': start - pd.Timedelta(days=100)}), \
                patch.object(E, 'arranque_en_ventana', return_value={}), \
                patch.object(E, '_campaign_asof', return_value=100):
            result = E.reconcile_flowsheet(start, materials, force_all_active=True, week_end=end,
                                           anchor=dict(anchor, OXIDOS=anchor['OXIDOS']))
        self.assertAlmostEqual(result['delta_recon_riego'], 0.0, places=9)
        self.assertAlmostEqual(result['delta_recon_pls'], 0.0, places=9)
        self.assertAlmostEqual(result['delta_fino_riego'], 0.0, places=9)
        self.assertAlmostEqual(result['delta_fino_pls'], 0.0, places=9)
        self.assertTrue(result['daily'])
        measured = {'P01': (100.0, 2.0), 'P02': (50.0, 1.0)}
        for d in result['daily']:
            q, cu_pls = measured[d['parcela'] if 'parcela' in d else d['pile']]
            self.assertAlmostEqual(d['q_riego_final'], q, places=7)
            self.assertAlmostEqual(d['cu_riego_recon'], 0.3, places=7)
            self.assertAlmostEqual(d['q_pls_final'], E.FDRENA_MAX * q, places=7)
            self.assertAlmostEqual(d['cu_pls_recon'], cu_pls, places=7)

    def test_negative_target_cannot_require_negative_pls_fine(self):
        self.assertAlmostEqual(E._pls_fine_target_for_net(-0.01, 50.0),
                               50.0 - 0.01 / 0.024)
        for bad_net, fine_riego in ((-2.0, 1.0), (float('nan'), 1.0),
                                    (1.0, float('inf'))):
            with self.assertRaises(ValueError):
                E._pls_fine_target_for_net(bad_net, fine_riego)

    def test_infeasible_daily_result_raises_instead_of_returning_success(self):
        start = pd.Timestamp('2026-10-01')
        dates = pd.DatetimeIndex([start])
        materials = {'OXIDOS': {
            'wip': {}, 'rec_curves': {}, 'max_rec': {}, 'ciclo_d': {},
            'riego': pd.DataFrame({'P01': [100.0]}, index=dates),
            'cu_riego': pd.Series([1.0], index=dates),
            'drena_cu': pd.DataFrame({'P01': [2.0]}, index=dates),
        }}
        anchor = {'OXIDOS': {
            'q_riego_medido': 100.0, 'q_riego_recon': 100.0,
            'q_pls_medido': 95.0, 'q_pls_recon': 95.0,
            'fino_riego_medido': 100.0, 'fino_riego_recon': 100.0,
            'fino_pls_medido': 190.0, 'fino_pls_recon': 190.0,
            'net_cu_target_t': 1.0, 'net_cu_target_flow': 'F25',
        }}

        def classify(_start, _wip, _curves, _max_rec, _cycle, **_kwargs):
            return ['P01'], ['P01'], [], {'P01': 1}, {'P01': 1.0}

        with patch.object(E, 'classify_piles', side_effect=classify), \
                patch.object(E, 'inicio_campana', return_value={'P01': start}), \
                patch.object(E, 'arranque_en_ventana', return_value={}), \
                patch.object(E, '_campaign_asof', return_value=1), \
                patch.object(E, '_build_piles', return_value=([], [], [], set(), {})):
            with self.assertRaisesRegex(RuntimeError, 'No se puede construir una curva diaria'):
                E.reconcile_flowsheet(start, materials, force_all_active=True,
                                      week_end=start, anchor=anchor)

if __name__ == '__main__':
    unittest.main()
