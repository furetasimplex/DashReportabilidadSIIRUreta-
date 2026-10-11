"""Contrato F4D1 sin conexiones SQL reales."""
from contextlib import contextmanager
import unittest
from unittest.mock import MagicMock, patch
from reclamo import db


class PublicarTests(unittest.TestCase):
    def exercise(self, rc, failure=None, days=7):
        events = []
        conn = MagicMock()
        def execute(sql, params=None):
            events.append((str(sql), params))
            if 'sp_getapplock' in str(sql):
                result = MagicMock()
                result.scalar.return_value = rc
                return result
            if failure:
                raise failure
        conn.execute.side_effect = execute
        @contextmanager
        def begin():
            events.append('BEGIN')
            try:
                yield conn
            except BaseException:
                events.append('ROLLBACK')
                raise
            else:
                events.append('COMMIT_CONTEXT')
        engine = MagicMock()
        engine.begin.side_effect = begin
        with patch.object(db, 'get_engine', return_value=engine):
            try:
                result = db.publicar('2026-09-10', '2026-09-10', days)
            except Exception as exc:
                result = exc
        engine.begin.assert_called_once()
        conn.commit.assert_not_called()
        conn.begin.assert_not_called()
        return result, events

    def test_success_order_connection_contract_and_parameters(self):
        for rc in (0, 1, 2):
            for days in (7, 0, 3):
                with self.subTest(rc=rc, days=days):
                    result, events = self.exercise(rc, days=days)
                    self.assertEqual(events[0], 'BEGIN')
                    self.assertEqual(events[-1], 'COMMIT_CONTEXT')
                    self.assertEqual(len(events), 4)
                    lock, sp = events[1], events[2]
                    for token in ("'SIIR_CONTINGENCIA_PI_APILADO'", "'Exclusive'",
                                  "'Transaction'", '10000'):
                        self.assertIn(token, lock[0])
                    self.assertIn('sp_mantiene_datos_conciliados_emision_test', sp[0])
                    self.assertNotIn('RefrescarFactor', sp[0])
                    self.assertNotIn('releaseapplock', lock[0] + sp[0])
                    self.assertEqual(sp[1], {'desde': '2026-09-10', 'hasta': '2026-09-10', 'dias': days})
                    self.assertEqual(result, 'Dato conciliado publicado para 2026-09-10 a 2026-09-10.')

    def test_lock_failure_rolls_back_without_dc(self):
        for rc in (None, -1, -2, -3, -999):
            with self.subTest(rc=rc):
                result, events = self.exercise(rc)
                self.assertIsInstance(result, RuntimeError)
                self.assertEqual(len(events), 3)
                self.assertEqual(events[-1], 'ROLLBACK')

    def test_sp_error_propagates_and_rolls_back(self):
        failure = ValueError('fallo SQL')
        result, events = self.exercise(0, failure)
        self.assertIs(result, failure)
        self.assertEqual(events[-1], 'ROLLBACK')

    def test_default_seven_days(self):
        import inspect
        self.assertEqual(inspect.signature(db.publicar).parameters['dias_reproceso'].default, 7)


if __name__ == '__main__':
    unittest.main()
