"""La suite unitaria no puede abrir conexiones, ni durante la colección."""
from unittest.mock import patch

import pytest

_attempts = []
_guards = []


def _deny_sql(*args, **kwargs):
    _attempts.append('SQL REAL NO PERMITIDO EN UNIT TEST')
    raise AssertionError(_attempts[-1])


def pytest_configure(config):
    # Antes de importar módulos de test: protege aliases y motores ya creados.
    for target in ('sqlalchemy.engine.Engine.connect',
                   'sqlalchemy.engine.Engine.raw_connection',
                   'sqlalchemy.pool.Pool.connect', 'pyodbc.connect'):
        guard = patch(target, side_effect=_deny_sql)
        guard.start()
        _guards.append(guard)


@pytest.fixture(autouse=True)
def no_sql_real(request):
    start = len(_attempts)
    yield
    # También falla si la aplicación captura el AssertionError y retorna UI.
    assert len(_attempts) == start, 'SQL REAL NO PERMITIDO EN UNIT TEST (intento interceptado)'


def pytest_unconfigure(config):
    for guard in reversed(_guards):
        guard.stop()
    _guards.clear()


def pytest_collection_finish(session):
    if _attempts:
        raise pytest.UsageError('SQL REAL NO PERMITIDO EN UNIT TEST durante colección')
