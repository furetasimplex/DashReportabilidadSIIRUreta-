from datetime import date

from . import local_cache, pad_data


class Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, engine):
        self.engine = engine

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.engine.calls.append((str(query), dict(params or {})))
        return Result([self.engine.signature])


class Engine:
    def __init__(self, signature):
        self.signature = signature
        self.calls = []

    def connect(self):
        return Connection(self)


def test_salt_revalida_insert_update_y_reusa_warm_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(local_cache, 'DIR', str(tmp_path))
    monkeypatch.setattr(local_cache, 'ACTIVA', True)
    monkeypatch.setattr(local_cache, '_MEM', {})
    engine = Engine((1, 'r1'))
    query = 'SELECT dato FROM dbo.Recuperaciones_pad WHERE PAD=:pad'
    sig0 = ('rec-primary-v2', 1181, 9001, '2026-10-01', 50)
    sig_insert = ('rec-primary-v2', 1182, 9002, '2026-10-01', 51)
    sig_update = ('rec-primary-v2', 1182, 9002, '2026-10-01', 99)

    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='Recuperaciones_pad',
                                cache_salt=sig0) == [(1, 'r1')]
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='Recuperaciones_pad',
                                cache_salt=sig0) == [(1, 'r1')]
    assert len(engine.calls) == 1

    engine.signature = ('insert', 2)
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='Recuperaciones_pad',
                                cache_salt=sig_insert) == [('insert', 2)]
    engine.signature = ('update', 3)
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='Recuperaciones_pad',
                                cache_salt=sig_update) == [('update', 3)]
    engine.signature = ('wrong-warm', 4)
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='Recuperaciones_pad',
                                cache_salt=sig_update) == [('update', 3)]
    assert len(engine.calls) == 3

    # Calls without salt retain the original key and warm-hit behavior.
    engine.signature = ('other', 5)
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='riego_diario') == [('other', 5)]
    engine.signature = ('other-new', 6)
    assert local_cache.sql_rows(engine, query, {'pad': 'SULFUROS'}, etiqueta='riego_diario') == [('other', 5)]
    assert len(engine.calls) == 4


def test_fingerprint_fresco_y_vacio_determinista(monkeypatch):
    engine = Engine((1181, 9001, date(2026, 10, 1), 77231))
    monkeypatch.setattr(pad_data, 'get_engine', lambda: engine)
    sig = pad_data._primary_source_fingerprint(engine, 'SULFUROS')
    assert sig == ('rec-primary-v2', 1181, 9001, '2026-10-01', 77231)
    assert len(engine.calls) == 1
    sql, params = engine.calls[0]
    assert 'COUNT_BIG' in sql and 'MAX(r.id_rec)' in sql and 'CHECKSUM_AGG' in sql
    assert 'r.Recuperacion_parcela' in sql and params == {'pad': 'SULFUROS'}

    empty = Engine((None, None, None, None))
    assert pad_data._primary_source_fingerprint(empty, 'OXIDOS') == (
        'rec-primary-v2', 0, None, None, None)


def test_pad_loader_aplica_misma_firma_a_las_dos_queries(monkeypatch):
    engine = Engine((1, None, None, None))
    fingerprint = ('rec-primary-v2', 2, 20, '2026-10-01', 88)
    monkeypatch.setattr(pad_data, 'get_engine', lambda: engine)
    monkeypatch.setattr(pad_data, '_primary_source_fingerprint', lambda eng, pad: fingerprint)
    calls = []
    def fake_rows(eng, query, params=None, etiqueta=None, cache_salt=None):
        calls.append((eng, str(query), params, cache_salt))
        if 'MAX(CAST(r.Fecha_drenaje AS DATE))' in str(query):
            return [(25, date(2026, 10, 1))]
        return [(25, date(2026, 10, 1), 12.5)]
    monkeypatch.setattr(pad_data, '_sql_rows', fake_rows)

    data = pad_data.load_sulfuro()
    assert data[25]['values'] == [12.5]
    assert len(calls) == 2
    assert all(call[0] is engine and call[3] == fingerprint for call in calls)
