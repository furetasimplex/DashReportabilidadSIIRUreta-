import json
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
from unittest.mock import patch

from . import db_pipeline


class ModelFlowMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(
            (Path(__file__).parent / 'fixtures' / 'modelo125_run10104.json')
            .read_text(encoding='utf-8')
        )

    def test_case_run_resolves_to_125_catalog_and_expected_codes(self):
        case = self.fixture['caso']
        model = self.fixture['modelo']
        run = self.fixture['run']
        self.assertEqual((case['id'], run['id'], run['caso_id']), (10013, 10104, 10013))
        self.assertEqual(model['codigo'], 'hidrometalurgia_125_v2')
        self.assertEqual(model['version'], 'v2')
        self.assertEqual(self.fixture['total_flujos'], 125)

        mapping, optional = db_pipeline._caso_flows_for_model(
            model['codigo'], model['version'], self.fixture['total_flujos'])
        self.assertEqual(mapping['OXIDOS'], {'riego': ['F70', 'F60', 'F81'], 'pls': ['F44', 'F45']})
        self.assertEqual(mapping['SULFUROS'], {'riego': ['F72', 'F66'], 'pls': ['F47', 'F48', 'F49']})
        configured = {code for flows in mapping.values() for codes in flows.values() for code in codes}
        self.assertIn('F45', configured)
        self.assertIn('F49', configured)
        self.assertNotIn('F50', configured)
        by_code = {row['codigo_flujo']: row for row in self.fixture['flujos_run']}
        self.assertEqual(float(by_code['F45']['fino_cu_medido']), 0.0)
        self.assertEqual(float(by_code['F45']['fino_cu_reconciliado']), 0.0)
        self.assertEqual(optional, set())

    def test_load_casos_carries_catalog_identity_from_case_model_join(self):
        class Result:
            def fetchall(self):
                return [(10013, 'Caso hidrometalurgia oct 2', date(2026, 10, 1),
                         date(2026, 10, 12), 'reconciliado', 10104,
                         'hidrometalurgia_125_v2', 'v2', 125)]

        class Connection:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def execute(self, query, *args):
                self.query = str(query)
                self.params = args
                Connection.last_query = self.query
                Connection.last_params = args
                return Result()

        class Engine:
            def connect(self):
                return Connection()

        with patch.object(db_pipeline, 'get_engine', lambda: Engine()):
            rows = db_pipeline.load_casos()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['modelo_codigo'], 'hidrometalurgia_125_v2')
        self.assertEqual(rows[0]['modelo_version'], 'v2')
        self.assertEqual(rows[0]['total_flujos'], 125)
        sql = Connection.last_query.upper()
        self.assertNotIn('BETWEEN', sql)
        self.assertNotIn('CASO_MIN', sql)
        self.assertNotIn('CASO_MAX', sql)
        self.assertIn('ORDER BY C.FECHA_INICIO DESC, C.ID DESC', sql)
        self.assertIn('RECON_CASO_OFICIAL', sql)
        self.assertIn("R.ESTADO = 'SUCCESS'", sql)
        self.assertIn('RECON_MODELO', sql)
        self.assertEqual(Connection.last_params, ())

    def test_run10104_zero_f60_is_included_and_not_dropped(self):
        by_code = {row['codigo_flujo']: row for row in self.fixture['flujos_run']}
        self.assertEqual(len(by_code), 125)
        self.assertEqual(float(by_code['F60']['masa_medida']), 0.0)
        self.assertEqual(float(by_code['F60']['fino_cu_medido']), 0.0)

        captured = {}
        with patch.object(db_pipeline, '_engine', object()):
            def fake_sql_rows(_engine, _query, params, **_kwargs):
                captured['codes'] = {value for key, value in params.items() if key.startswith('c')}
                return [
                    (code, row['masa_medida'], row['masa_reconciliada'],
                     row['fino_cu_medido'], row['fino_cu_reconciliado'])
                    for code, row in by_code.items() if code in captured['codes']
                ]

            with patch.object(db_pipeline, '_sql_rows', fake_sql_rows):
                anchor = db_pipeline.load_caso_anchor(
                    10104, 'hidrometalurgia_125_v2', 'v2', 125)

        self.assertIn('F60', captured['codes'])
        self.assertEqual(set(anchor), {'OXIDOS', 'SULFUROS'})
        self.assertTrue(db_pipeline.caso_anchor_completo(anchor))
        self.assertGreater(anchor['OXIDOS']['q_riego_medido'], 0)
        self.assertGreater(anchor['SULFUROS']['q_riego_medido'], 0)
        expected_ox_pls = sum(float(by_code[c]['masa_medida']) for c in ('F44', 'F45'))
        expected_su_pls = sum(float(by_code[c]['masa_medida']) for c in ('F47', 'F48', 'F49'))
        self.assertAlmostEqual(anchor['OXIDOS']['q_pls_medido'], expected_ox_pls)
        self.assertAlmostEqual(anchor['SULFUROS']['q_pls_medido'], expected_su_pls)

        for bad_value in (float('nan'), float('inf'), -0.01):
            invalid = deepcopy(anchor)
            invalid['OXIDOS']['fino_riego_recon'] = bad_value
            self.assertFalse(db_pipeline.caso_anchor_completo(invalid))

        # The 125 catalog returns every configured code. A missing ILS row
        # cannot silently become zero just because its measured value can be 0.
        with patch.object(db_pipeline, '_engine', object()):
            missing_sql_rows = lambda _engine, _query, params, **_kwargs: [
                    (code, row['masa_medida'], row['masa_reconciliada'],
                     row['fino_cu_medido'], row['fino_cu_reconciliado'])
                    for code, row in by_code.items()
                    if code in {value for key, value in params.items() if key.startswith('c')}
                    and code != 'F60'
                ]
            with patch.object(db_pipeline, '_sql_rows', missing_sql_rows):
                incomplete = db_pipeline.load_caso_anchor(
                    10104, 'hidrometalurgia_125_v2', 'v2', 125)
        self.assertEqual(set(incomplete), {'SULFUROS'})
        self.assertFalse(db_pipeline.caso_anchor_completo(incomplete))

    def test_missing_new_drain_components_blocks_only_affected_pad(self):
        by_code = {row['codigo_flujo']: row for row in self.fixture['flujos_run']}
        for missing, expected in (('F45', {'SULFUROS'}), ('F49', {'OXIDOS'})):
            with patch.object(db_pipeline, '_engine', object()):
                def fake_sql_rows(_engine, _query, params, **_kwargs):
                    codes = {value for key, value in params.items() if key.startswith('c')}
                    return [
                        (code, row['masa_medida'], row['masa_reconciliada'],
                         row['fino_cu_medido'], row['fino_cu_reconciliado'])
                        for code, row in by_code.items() if code in codes and code != missing
                    ]
                with patch.object(db_pipeline, '_sql_rows', fake_sql_rows):
                    anchor = db_pipeline.load_caso_anchor(10104, 'hidrometalurgia_125_v2', 'v2', 125)
            self.assertEqual(set(anchor), expected)

    def test_zero_denominador_agregado_sigue_bloqueando_ancla(self):
        # Se conserva el control vigente hasta resolver la semántica del ratio
        # oficial cuando el denominator agregado del pad sea cero.
        anchor = {
            pad: {key: 1.0 for key in db_pipeline.CASO_ANCHOR_KEYS}
            for pad in ('OXIDOS', 'SULFUROS')
        }
        anchor['OXIDOS']['q_riego_medido'] = 0.0
        self.assertFalse(db_pipeline.caso_anchor_completo(anchor))

    def test_legacy_and_125_f44_have_version_specific_meanings(self):
        legacy, _ = db_pipeline._caso_flows_for_model('hidrometalurgia_120_completo')
        modern, _ = db_pipeline._caso_flows_for_model('hidrometalurgia_125_v2')
        self.assertIn('F44', legacy['SULFUROS']['riego'])
        self.assertIn('F44', modern['OXIDOS']['pls'])
        with self.assertRaises(ValueError):
            db_pipeline._caso_flows_for_model('unknown_model')
        with self.assertRaises(ValueError):
            db_pipeline._caso_flows_for_model('hidrometalurgia_125_v2', 'v2', 120)


if __name__ == '__main__':
    unittest.main()
