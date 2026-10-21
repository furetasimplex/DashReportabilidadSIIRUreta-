"""Regression tests for staged reconciliation persistence helpers."""
from datetime import date
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from curvas_recon.db_pipeline import _insert_rows_batched


class FakeConnection:
    def __init__(self, dialect='mssql'):
        self.dialect = SimpleNamespace(name=dialect)
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((str(statement), params))


def test_sqlserver_batch_limits_and_payload_order():
    columns = ('id', 'label', 'value')
    rows = [{'id': i, 'label': 'Pila ñ' if i == 0 else None,
             'value': None if i == 1 else i + 0.25} for i in range(1001)]
    conn = FakeConnection()

    assert _insert_rows_batched(conn, 'dbo.sample', columns, rows) == 2
    assert [len(params) for _, params in conn.calls] == [1998, 1005]
    assert all(len(params) <= 2000 for _, params in conn.calls)
    assert conn.calls[0][1]['label_0'] == 'Pila ñ'
    assert conn.calls[0][1]['value_1'] is None
    assert conn.calls[1][1]['id_0'] == 666
    assert conn.calls[1][1]['id_334'] == 1000


def test_daily_batch_432_rows_chunks_200_200_32():
    columns = ('run_id', 'material_id', 'label', 'parcela_nombre', 'dia_offset',
               'fdrena', 'q', 'q_pls', 'cu_drena', 'cu_riego')
    rows = [{'run_id': 3, 'material_id': 2, 'label': 'SULFUROS',
             'parcela_nombre': f'P{i}', 'dia_offset': i, 'fdrena': None,
             'q': 0.1, 'q_pls': 0.2, 'cu_drena': 0.3, 'cu_riego': 0.0}
            for i in range(432)]
    conn = FakeConnection()

    assert _insert_rows_batched(conn, 'dbo.daily', columns, rows) == 3
    assert [len(params) for _, params in conn.calls] == [2000, 2000, 320]
    assert [params['parcela_nombre_0'] for _, params in conn.calls] == ['P0', 'P200', 'P400']
    assert conn.calls[-1][1]['parcela_nombre_31'] == 'P431'


@pytest.mark.filterwarnings('ignore:.*default date adapter is deprecated.*:DeprecationWarning')
def test_sqlserver_row_cap_and_database_roundtrip_rollback():
    engine = create_engine('sqlite://')
    with engine.connect() as real_conn:
        real_conn.execute(text('CREATE TABLE sample (id INTEGER, label TEXT, amount REAL, day DATE)'))
        real_conn.commit()

        class SqlServerDialectAdapter:
            dialect = SimpleNamespace(name='mssql')

            @staticmethod
            def execute(statement, params):
                return real_conn.execute(statement, params)

        rows = [{'id': i, 'label': None if i % 2 else 'Pila ñ',
                 'amount': None if i % 3 else -i / 10,
                 'day': date(2026, 10, 12)} for i in range(1001)]
        assert _insert_rows_batched(SqlServerDialectAdapter(), 'sample',
                                    ('id', 'label', 'amount', 'day'), rows) == 3
        actual = real_conn.execute(text(
            'SELECT id, label, amount, day FROM sample ORDER BY id')).all()
        assert len(actual) == len(rows)
        assert tuple(actual[0]) == (0, 'Pila ñ', 0.0, '2026-10-12')
        assert tuple(actual[1]) == (1, None, None, '2026-10-12')
        real_conn.rollback()
        assert real_conn.execute(text('SELECT COUNT(*) FROM sample')).scalar_one() == 0
    engine.dispose()


def test_other_dialect_uses_executemany_and_empty_is_noop():
    conn = FakeConnection('postgresql')
    rows = [{'id': 1, 'label': 'OX'}, {'id': 2, 'label': None}]

    assert _insert_rows_batched(conn, 't', ('id', 'label'), rows) == 1
    assert len(conn.calls) == 1
    sql, params = conn.calls[0]
    assert 'VALUES (:id, :label)' in sql
    assert params == rows
    assert _insert_rows_batched(conn, 't', ('id', 'label'), []) == 0
    assert len(conn.calls) == 1


def test_sqlserver_one_column_row_cap_and_failure_propagation():
    rows = [{'value': i} for i in range(1001)]
    conn = FakeConnection()
    assert _insert_rows_batched(conn, 'dbo.sample', ('value',), rows) == 2
    assert [len(params) for _, params in conn.calls] == [1000, 1]

    class FailingConnection(FakeConnection):
        def execute(self, statement, params):
            raise RuntimeError('synthetic failure')

    with pytest.raises(RuntimeError, match='synthetic failure'):
        _insert_rows_batched(FailingConnection(), 'dbo.sample', ('value',), rows)


def test_perf_trace_package_import_and_metadata_only(monkeypatch, tmp_path):
    from curvas_recon import perf_trace

    target = tmp_path / 'trace.jsonl'
    monkeypatch.setattr(perf_trace, '_LOG_PATH', target)
    token = perf_trace.set_trace_id('batch-test')
    try:
        assert perf_trace.record_phase('save_run.total', 0.25, rows=432)
    finally:
        perf_trace.reset_trace_id(token)
    record = __import__('json').loads(target.read_text(encoding='utf-8'))
    assert record['trace_id'] == 'batch-test'
    assert record['phase'] == 'save_run.total'
    assert record['rows'] == 432
    assert not {'sql', 'password', 'connection_string'} & record.keys()
