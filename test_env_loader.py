"""Configuration regressions using temporary fixtures, not the real .env."""
import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

root = Path(__file__).resolve().parent
if not (root / 'env_loader.py').is_file():
    root = Path(r'C:\Users\5330\Desktop\HidroNueva\DashReportabilidadSIIR')
sys.path.insert(0, str(root))
import env_loader


class ArranqueEnv(unittest.TestCase):
    def test_loader_independiente_de_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.env'
            path.write_text('LOGIN_DATABASE=offline.dbo.auth_user\nSECRET_KEY=fixture-key\n', encoding='utf-8')
            with patch.object(env_loader, 'ENV_FILE', path), patch.dict(os.environ, {}, clear=True):
                previous = Path.cwd()
                try:
                    os.chdir(root)
                    self.assertTrue(env_loader.load_app_env())
                    self.assertEqual(os.environ['LOGIN_DATABASE'], 'offline.dbo.auth_user')
                    self.assertEqual(set(env_loader.require_app_env('LOGIN_DATABASE', 'SECRET_KEY')),
                                     {'LOGIN_DATABASE', 'SECRET_KEY'})
                finally:
                    os.chdir(previous)

    def test_no_sobrescribe_config_del_proceso(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'fixture.env'
            path.write_text('LOGIN_DATABASE=file.dbo.auth_user\n', encoding='utf-8')
            with patch.object(env_loader, 'ENV_FILE', path), patch.dict(os.environ, {'LOGIN_DATABASE': 'process.dbo.auth_user'}, clear=True):
                env_loader.load_app_env()
                self.assertEqual(os.environ['LOGIN_DATABASE'], 'process.dbo.auth_user')

    def test_error_faltante_no_filtra_valores(self):
        with patch.dict(os.environ, {'SECRET_KEY': 'private-fixture-secret'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'LOGIN_DATABASE') as caught:
                env_loader.require_app_env('LOGIN_DATABASE', 'SECRET_KEY')
            self.assertNotIn('private-fixture-secret', str(caught.exception))

    def test_valores_blancos_fallan_antes_de_auth(self):
        with patch.dict(os.environ, {'LOGIN_DATABASE': '  ', 'SECRET_KEY': ''}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'LOGIN_DATABASE, SECRET_KEY'):
                env_loader.require_app_env('LOGIN_DATABASE', 'SECRET_KEY')


if __name__ == '__main__':
    unittest.main()
