"""Hardening 4D3: simulación completa sin SQL ni scripts históricos reales."""
from contextlib import ExitStack, redirect_stdout
import io
import os
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from scripts import validate_trazabilidad_analitos_dev as target


class SafeDefaultTests(unittest.TestCase):
    def run_case(self, args, env=None, rejected=False):
        engine = MagicMock()
        conn = engine.connect.return_value.__enter__.return_value
        raw = conn.connection
        raw.cursor.return_value.nextset.return_value = False
        cache = pd.DataFrame({'Fecha': ['2026-08-01'], 'Turno': ['A'],
                              'Apilado_TMS_Real': [123.5], 'Fecha_Actualizacion': ['ahora']})
        trace = pd.DataFrame({'Valor_Final': [1.5], 'Fuente_Base': ['TM1']})
        events = []
        def guard(actual):
            self.assertIs(actual, conn)
            events.append('guard')
            if rejected:
                raise RuntimeError('DEV no acreditado')
        raw.cursor.return_value.execute.side_effect = lambda *a: events.append('EXEC')
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ, env or {}, clear=True))
            get_engine = stack.enter_context(patch.object(target, 'get_engine', return_value=engine))
            dev_engine = stack.enter_context(patch('monitor_pi_tum.db._engine_dev', return_value=engine))
            stack.enter_context(patch('monitor_pi_tum.db._assert_dev_connection', side_effect=guard))
            stack.enter_context(patch.object(target.pd, 'read_csv', return_value=cache.copy()))
            reads = stack.enter_context(patch.object(target.pd, 'read_sql', side_effect=[cache.copy(), trace]))
            csv = stack.enter_context(patch.object(pd.DataFrame, 'to_csv'))
            compare = stack.enter_context(patch.object(pd.testing, 'assert_frame_equal', wraps=pd.testing.assert_frame_equal))
            output = stack.enter_context(redirect_stdout(io.StringIO()))
            if rejected:
                with self.assertRaisesRegex(RuntimeError, 'DEV no acreditado'):
                    target.main(args)
                reads.assert_not_called()
                csv.assert_not_called()
            else:
                target.main(args)
                self.assertEqual(reads.call_count, 2)
                compare.assert_called_once()
                self.assertEqual(csv.call_count, 2)
                self.assertEqual(csv.call_args_list[0].args[0].name, 'post_cache_20260801_20260809.csv')
                self.assertEqual(csv.call_args_list[1].args[0].name, 'trazabilidad_20260801_20260809.csv')
            return raw, events, output.getvalue(), get_engine.call_count, dev_engine.call_count

    def test_default_read_only(self):
        raw, events, output, _, dev = self.run_case([])
        raw.commit.assert_not_called()
        raw.cursor.assert_not_called()
        self.assertEqual(events, [])
        self.assertEqual(dev, 0)
        self.assertIn('[TRAZABILIDAD] Modo READ-ONLY. No se realizarán escrituras SQL.', output)

    def test_help_no_connection(self):
        with patch.object(target, 'get_engine') as engine, \
             patch.object(target.pd, 'read_csv') as baseline, redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as exc:
                target.main(['--help'])
            self.assertEqual(exc.exception.code, 0)
            engine.assert_not_called()
            baseline.assert_not_called()

    def test_explicit_write_preserves_sql_and_range(self):
        raw, events, output, regular, dev = self.run_case(['--execute-write'])
        self.assertEqual(events, ['guard', 'EXEC'])
        self.assertEqual((regular, dev), (0, 1))
        raw.commit.assert_called_once()
        raw.cursor.return_value.execute.assert_called_once_with(
            'EXEC inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test '
            '@fecha_inicio=?, @fecha_fin=?', target.INI, target.FIN)
        self.assertIn('[TRAZABILIDAD] Modo WRITE DEV autorizado explícitamente.', output)

    def test_environment_read_only_wins(self):
        raw, events, _, _, dev = self.run_case(['--execute-write'], {'TRAZ_READ_ONLY': '1'})
        raw.commit.assert_not_called()
        raw.cursor.assert_not_called()
        self.assertEqual(events, [])
        self.assertEqual(dev, 0)

    def test_unaccredited_dev_never_executes(self):
        raw, events, _, _, _ = self.run_case(['--execute-write'], rejected=True)
        self.assertEqual(events, ['guard'])
        raw.cursor.assert_not_called()
        raw.commit.assert_not_called()

    def test_environment_alone_cannot_authorize_write(self):
        raw, events, _, _, _ = self.run_case([], {'TRAZ_READ_ONLY': '0'})
        raw.commit.assert_not_called()
        self.assertEqual(events, [])


if __name__ == '__main__':
    unittest.main()
