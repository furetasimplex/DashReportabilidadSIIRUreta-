"""Pruebas sin conexiones reales para el diagnóstico manual de F4D1."""
from copy import deepcopy
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

from scripts import validate_reclamo_publicar_factor_dev as diag


def sample():
    result = {}
    for table in diag.TABLES:
        row = {'Fecha': '2026-09-10', 'Valor': 12, 'Fecha_Calculo': 'antes'}
        if table == diag.TABLES[1]:
            row['Turno'] = 'A'
        result[table] = {'columns': list(row), 'rows': [row]}
    return result


class DiagnosticTests(unittest.TestCase):
    def test_no_flag_does_not_import_database(self):
        code = """
import sys
from scripts.validate_reclamo_publicar_factor_dev import main
try:
    main([])
except SystemExit as exc:
    assert exc.code == 2
    assert 'db_connection' not in sys.modules
    assert 'monitor_pi_tum.db' not in sys.modules
else:
    raise AssertionError('Debió rechazar ejecución')
"""
        result = subprocess.run([sys.executable, '-c', code], cwd=diag.ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('No se ha conectado a SQL', result.stderr)

    def test_timestamps_are_separate_and_decimal_exact(self):
        from decimal import Decimal
        a, b = sample(), sample()
        b[diag.TABLES[0]]['rows'][0]['Fecha_Calculo'] = 'despues'
        audit = {t: ['Fecha_Calculo'] for t in diag.TABLES}
        self.assertTrue(diag.differences(a, b)[diag.TABLES[0]]['cambios'])
        self.assertFalse(diag.differences(a, b, audit)[diag.TABLES[0]]['cambios'])
        self.assertEqual(diag.encode(Decimal('0.9983502509529375001')),
                         {'decimal': '0.9983502509529375001'})
        b[diag.TABLES[0]]['rows'][0]['Valor'] = 13
        changes = diag.differences(a, b, audit)[diag.TABLES[0]]
        self.assertEqual(changes['columnas_diferentes'], ['Valor'])
        self.assertEqual(changes['cambios'][0]['A'], 12)
        self.assertEqual(changes['cambios'][0]['B'], 13)

    def test_insert_delete_and_duplicate_keys(self):
        a, b = sample(), sample()
        b[diag.TABLES[2]]['rows'] = []
        self.assertTrue(diag.differences(a, b)[diag.TABLES[2]]['cambios'])
        self.assertTrue(diag.differences(b, a)[diag.TABLES[2]]['cambios'])
        a[diag.TABLES[0]]['rows'] *= 2
        with self.assertRaises(ValueError):
            diag.differences(a, b)

    def test_classification(self):
        for args, expected in [((False, False), 'REFRESCO_FACTOR_REDUNDANTE'),
                               ((True, True), 'FACTOR_PREVIO_NO_EQUIVALENTE'),
                               ((True, False), 'FACTOR_ESCRITURA_NO_NECESARIA_PARA_PUBLICAR'),
                               ((False, True), 'REVISAR_MANUALMENTE'),
                               ((False, False, False), 'REVISAR_MANUALMENTE')]:
            with self.subTest(args=args):
                self.assertEqual(diag.classify(*args), expected)

    def test_rollback_on_success_and_failure(self):
        for fail in (False, True):
            conn = MagicMock()
            try:
                with diag.rollback_only(conn):
                    if fail:
                        raise ValueError('fallo')
            except ValueError:
                pass
            conn.begin.return_value.rollback.assert_called_once()
            conn.commit.assert_not_called()
            conn.begin.return_value.commit.assert_not_called()
        conn.begin.return_value.rollback.side_effect = RuntimeError('rollback falló')
        with self.assertRaises(RuntimeError):
            with diag.rollback_only(conn):
                pass
        conn.invalidate.assert_called_once()
        with self.assertRaises(RuntimeError):
            diag.no_commit(conn)

    def test_run_restores_both_cases_and_passes_explicit_flags(self):
        engine = MagicMock()
        initial = sample()
        a = deepcopy(initial)
        a[diag.TABLES[0]]['rows'][0]['Fecha_Calculo'] = 'nuevo'
        evidence = {}
        state = {'spid': 42, 'trancount': 1, 'xact_state': 1, 'lock_global': 'Exclusive'}
        with patch.object(diag, 'snapshot', side_effect=[initial, a, initial, initial, initial, initial]), \
             patch.object(diag, 'identity_snapshot', return_value=[]), \
             patch.object(diag, 'inspect_contract', return_value=({}, {t: ['Fecha_Calculo'] for t in diag.TABLES})), \
             patch.object(diag, 'state', return_value=state), \
             patch.object(diag, 'execute_sp') as execute:
            diag.run(engine, MagicMock(), MagicMock(), lambda x: x, evidence)
        self.assertEqual([call.args[1] for call in execute.call_args_list], [1, 0])
        self.assertEqual(evidence['clasificacion'], 'REFRESCO_FACTOR_REDUNDANTE')
        self.assertTrue(all(c['restauracion_exacta'] for c in evidence['casos'].values()))

    def test_sp_error_verifies_rollback_and_does_not_run_b(self):
        engine, evidence = MagicMock(), {}
        state = {'spid': 42, 'trancount': 1, 'xact_state': 1, 'lock_global': 'Exclusive'}
        with patch.object(diag, 'snapshot', return_value=sample()) as capture, \
             patch.object(diag, 'identity_snapshot', return_value=[]), \
             patch.object(diag, 'inspect_contract', return_value=({}, {})), \
             patch.object(diag, 'state', return_value=state), \
             patch.object(diag, 'execute_sp', side_effect=RuntimeError('SP falló')):
            with self.assertRaisesRegex(RuntimeError, 'SP falló'):
                diag.run(engine, MagicMock(), MagicMock(), lambda x: x, evidence)
        self.assertEqual(capture.call_count, 2)
        self.assertTrue(evidence['casos']['A']['restauracion_exacta'])
        self.assertNotIn('B', evidence['casos'])

    def test_different_baseline_prevents_b(self):
        engine, evidence = MagicMock(), {}
        original, changed = sample(), sample()
        changed[diag.TABLES[0]]['rows'][0]['Valor'] = 999
        state = {'spid': 42, 'trancount': 1, 'xact_state': 1, 'lock_global': 'Exclusive'}
        with patch.object(diag, 'snapshot', side_effect=[original, original, original, changed, changed]), \
             patch.object(diag, 'identity_snapshot', return_value=[]), \
             patch.object(diag, 'inspect_contract', return_value=({}, {})), \
             patch.object(diag, 'state', return_value=state), \
             patch.object(diag, 'execute_sp') as execute:
            with self.assertRaisesRegex(RuntimeError, 'Baseline distinto'):
                diag.run(engine, MagicMock(), MagicMock(), lambda x: x, evidence)
        execute.assert_called_once()


if __name__ == '__main__':
    unittest.main()
