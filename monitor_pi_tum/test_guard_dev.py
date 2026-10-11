"""Guard de escritura DEV, sin acceso a SQL real."""
import unittest
from unittest.mock import MagicMock, patch

from . import db


class GuardDevTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict('os.environ', SIIR_DEV_SQLSERVER_HOST='VPS-5347319-X')
        self.env.start()
        self.addCleanup(self.env.stop)

    def conexion(self, base='inventar_SpcHidr', servidor='VPS-5347319-X', maquina='VPS-5347319-X'):
        conn = MagicMock()
        conn.execute.return_value.mappings.return_value.one.return_value = {
            'database_name': base, 'server_name': servidor, 'machine_name': maquina}
        return conn

    def test_identidad_dev_correcta(self):
        conn = self.conexion()
        db._assert_dev_connection(conn)
        self.assertIn('SERVERPROPERTY', str(conn.execute.call_args.args[0]))

    def test_servidor_incorrecto_bloquea(self):
        with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
            db._assert_dev_connection(self.conexion(servidor='OTRO', maquina='OTRO'))

    def test_base_incorrecta_bloquea(self):
        with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
            db._assert_dev_connection(self.conexion(base='OTRA'))

    def test_configuracion_ausente_bloquea_sin_sql(self):
        conn = self.conexion()
        with patch.dict('os.environ', {'SIIR_DEV_SQLSERVER_HOST': ''}):
            with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
                db._assert_dev_connection(conn)
        conn.execute.assert_not_called()

    def test_error_de_identidad_bloquea(self):
        conn = self.conexion()
        conn.execute.side_effect = RuntimeError('sin identidad')
        with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
            db._assert_dev_connection(conn)

    def test_guard_usa_la_misma_conexion_antes_de_escribir(self):
        conn = self.conexion(servidor='OTRO', maquina='OTRO')
        engine = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        with patch.object(db, '_engine_dev', return_value=engine):
            with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
                db.registrar_contingencia_rango('2026-09-15', 'A', '2026-09-15', 'B',
                                                'CAIDA_PI', 'prueba', 'usuario')
        engine.begin.assert_called_once()
        self.assertEqual(conn.execute.call_count, 1)
        self.assertIn('SERVERPROPERTY', str(conn.execute.call_args.args[0]))

    def test_guard_puntual_bloquea_antes_del_sp(self):
        conn = self.conexion(base='OTRA')
        engine = MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        with patch.object(db, '_engine_dev', return_value=engine):
            with self.assertRaisesRegex(RuntimeError, 'bloqueada'):
                db.registrar_contingencia('2026-09-15', 'A', 'ACTIVAR_CONTINGENCIA',
                                         'CAIDA_PI', 'prueba', 'usuario')
        self.assertEqual(conn.execute.call_count, 1)
        self.assertIn('SERVERPROPERTY', str(conn.execute.call_args.args[0]))


if __name__ == '__main__':
    unittest.main()
