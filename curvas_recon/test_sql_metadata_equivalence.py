"""Ejecuta SQL local real para contrastar metadatos con las consultas previas."""
import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from . import recon_engine as engine


@pytest.fixture
def local_sources(monkeypatch):
    db = create_engine('sqlite:///:memory:')
    with db.begin() as conn:
        conn.execute(text('CREATE TABLE material (id INTEGER, nombre TEXT)'))
        conn.execute(text('CREATE TABLE parcela (id_parcela INTEGER, nombre TEXT, id_pad INTEGER)'))
        conn.execute(text('INSERT INTO material VALUES (1, :ox), (2, :su)'),
                     {'ox': engine.LABEL_MATERIAL['OXIDOS'], 'su': engine.LABEL_MATERIAL['SULFUROS']})
        conn.execute(text("INSERT INTO parcela VALUES (1,'P01',1),(2,'P02',1),(3,'P03',1),(4,'P04',1),(5,'P01',2)"))
        for table, field in [('riego_diario', 'caudal_m3h'),
                             ('vw_riego_diario_ingest', 'caudal_m3h'),
                             ('drena_cu_diario', 'cu_gl'),
                             ('vw_drena_quimica_ingest', 'cu_gl')]:
            conn.execute(text(f'CREATE TABLE {table} (parcela_id INTEGER, fecha TEXT, {field} REAL)'))
            rows = [dict(p=1, d='2026-09-29 00:00:00', v=2.0),
                    dict(p=1, d='2026-09-30 00:00:00', v=3.0),
                    dict(p=2, d='2026-09-30 00:00:00', v=0.0),
                    dict(p=3, d='2026-09-30 00:00:00', v=None),
                    dict(p=4, d='2026-09-30 00:00:00', v=-1.0),
                    dict(p=5, d='2026-09-28 00:00:00', v=9.0)]
            if 'ingest' in table:
                rows += [dict(p=1, d='2026-09-30 00:00:00', v=7.0),
                         dict(p=1, d='2026-09-30 12:00:00', v=8.0),
                         dict(p=1, d='2026-10-01 00:00:00', v=10.0),
                         dict(p=2, d='2026-09-28 00:00:00', v=1.0)]
            conn.execute(text(f'INSERT INTO {table} VALUES (:p,:d,:v)'), rows)
    calls = []
    def sql_df(db_engine, query, params):
        calls.append(str(query))
        return pd.read_sql_query(query, db_engine, params=params)
    monkeypatch.setattr(engine, 'SCHEMA', 'main')
    monkeypatch.setattr(engine, 'get_engine', lambda: db)
    monkeypatch.setattr(engine, '_sql_df', sql_df)
    monkeypatch.setattr(engine, '_ACTIVIDAD_CACHE', {})
    yield db, calls
    db.dispose()


def test_activity_matches_legacy_sql_with_duplicates_null_zero_and_multiple_pads(local_sources):
    db, calls = local_sources
    expected = []
    for source, ingest, field in [('riego_diario', 'vw_riego_diario_ingest', 'caudal_m3h'),
                                   ('drena_cu_diario', 'vw_drena_quimica_ingest', 'cu_gl')]:
        query = text(f'''SELECT p.nombre AS pila, x.fecha FROM
            (SELECT parcela_id, fecha, {field} FROM {source} UNION
             SELECT parcela_id, fecha, {field} FROM {ingest}) x
            JOIN parcela p ON p.id_parcela=x.parcela_id
            JOIN material m ON m.id=p.id_pad
            WHERE m.nombre=:material AND x.{field}>0''')
        df = pd.read_sql_query(query, db, params={'material': engine.LABEL_MATERIAL['OXIDOS']})
        df['fecha'] = pd.to_datetime(df['fecha']).dt.normalize()
        expected.append({p: pd.DatetimeIndex(g.fecha.drop_duplicates().sort_values())
                         for p, g in df.groupby('pila')})
    actual = engine._fechas_actividad('OXIDOS')
    for observed, control in zip(actual, expected):
        assert observed.keys() == control.keys()
        for pile in control:
            assert observed[pile].equals(control[pile])
    assert len(calls) == 2
    engine._fechas_actividad('OXIDOS')
    assert len(calls) == 2


def test_latest_irrigation_matches_two_legacy_queries_and_exclusive_cut(local_sources):
    db, calls = local_sources
    params = {'material': engine.LABEL_MATERIAL['OXIDOS'], 'before': '2026-10-01 00:00:00'}
    expected = {}
    for source in ('riego_diario', 'vw_riego_diario_ingest'):
        query = text(f'''SELECT p.nombre AS pila, MAX(r.fecha) AS ultima FROM {source} r
            JOIN parcela p ON p.id_parcela=r.parcela_id JOIN material m ON m.id=p.id_pad
            WHERE m.nombre=:material AND p.nombre IN ('P01','P02','P03','P04')
              AND r.fecha<:before AND r.caudal_m3h>0 GROUP BY p.nombre''')
        for row in pd.read_sql_query(query, db, params=params).itertuples():
            date = pd.Timestamp(row.ultima)
            expected[row.pila] = max(expected.get(row.pila, date), date)
    result = engine.ultimo_riego('OXIDOS', ['P01', 'P02', 'P03', 'P04', 'P01'], params['before'])
    assert result == expected == {'P01': pd.Timestamp('2026-09-30 12:00:00'),
                                  'P02': pd.Timestamp('2026-09-28')}
    assert len(calls) == 1
    assert engine.ultimo_riego('OXIDOS', [], params['before']) == {}
    assert len(calls) == 1
