"""Read-only intraturn wet-mass profile from CV008/CV108 counters.

It does not publish, synchronize, or modify SQL data.
The query retains every raw endpoint in the requested operational window and
exposes quality diagnostics so callers can decide which intervals to use.
"""
import re

import numpy as np
import pandas as pd
from sqlalchemy import text

_SQL = """
WITH bounds AS (
    SELECT CAST(:start AS date) AS d0, CAST(:end AS date) AS d1,
           DATEADD(hour, 8, CAST(:start AS datetime2(0))) AS t0,
           DATEADD(hour, 8, DATEADD(day, 1, CAST(:end AS datetime2(0)))) AS t1
), towers AS (
    SELECT tm, counter_col FROM (VALUES
        ('TM1', 'tot_008'), ('TM2', 'tot_108')
    ) v(tm, counter_col)
), anchor AS (
    /* Context only: all tied latest endpoints are kept and flagged below. */
    SELECT t.tm, x.fecha, x.counter_value
    FROM bounds b CROSS JOIN towers t
    CROSS APPLY (
        SELECT TOP (1) WITH TIES fecha,
          CASE t.counter_col WHEN 'tot_008' THEN CAST(tot_008 AS float)
                             ELSE CAST(tot_108 AS float) END AS counter_value
        FROM {schema}.tot_TM
        WHERE fecha IS NOT NULL AND fecha <= b.t0
        ORDER BY fecha DESC
    ) x
), inside_window AS (
    SELECT t.tm, x.fecha,
      CASE t.counter_col WHEN 'tot_008' THEN CAST(x.tot_008 AS float)
                         ELSE CAST(x.tot_108 AS float) END AS counter_value
    FROM bounds b JOIN {schema}.tot_TM x
      ON x.fecha > b.t0 AND x.fecha <= b.t1
    CROSS JOIN towers t
), raw AS (
    SELECT tm, fecha, counter_value FROM anchor
    UNION ALL
    SELECT tm, fecha, counter_value FROM inside_window
), cardinality AS (
    SELECT tm, fecha, COUNT_BIG(*) AS row_count_at_timestamp
    FROM raw GROUP BY tm, fecha
), lagged AS (
    SELECT r.tm, r.fecha, r.counter_value, c.row_count_at_timestamp,
      LAG(r.fecha) OVER(PARTITION BY r.tm ORDER BY r.fecha) AS prev_fecha,
      LAG(r.counter_value) OVER(PARTITION BY r.tm ORDER BY r.fecha) AS prev_counter,
      LAG(c.row_count_at_timestamp) OVER(PARTITION BY r.tm ORDER BY r.fecha) AS prev_row_count
    FROM raw r JOIN cardinality c ON c.tm=r.tm AND c.fecha=r.fecha
), measured AS (
    SELECT l.*,
      DATEDIFF(second, prev_fecha, fecha) AS gap_s,
      CASE WHEN counter_value IS NOT NULL AND prev_counter IS NOT NULL
           THEN counter_value-prev_counter END AS delta_raw,
      DATEADD(microsecond,-1,CAST(fecha AS datetime2(7))) AS bucket_time
    FROM lagged l
), classified AS (
    SELECT m.*,
      CASE
        WHEN row_count_at_timestamp>1 OR COALESCE(prev_row_count,0)>1 THEN 'duplicate'
        WHEN prev_fecha IS NULL THEN 'no_previous'
        WHEN counter_value IS NULL OR prev_counter IS NULL THEN 'null'
        WHEN gap_s<>10 THEN 'gap'
        WHEN delta_raw<0 THEN 'reset'
        WHEN delta_raw>150000 THEN 'large_jump'
        WHEN delta_raw>=0 THEN 'ok'
        ELSE 'null'
      END AS quality
    FROM measured m
)
SELECT
  prev_fecha AS [start],
  fecha AS [end],
  CAST(DATEADD(hour,-8,bucket_time) AS date) AS fecha_op,
  CASE WHEN DATEPART(hour,bucket_time)>=8 AND DATEPART(hour,bucket_time)<20
       THEN 'A' ELSE 'B' END AS turno,
  tm,
  /* Candidate mass is retained for ok and large_jump; callers must mask the latter. */
  CASE WHEN gap_s=10 AND counter_value IS NOT NULL AND prev_counter IS NOT NULL
         AND delta_raw>=0 AND row_count_at_timestamp=1 AND COALESCE(prev_row_count,0)<=1
       THEN delta_raw END AS mass_h,
  delta_raw,
  quality,
  gap_s,
  row_count_at_timestamp,
  COALESCE(prev_row_count,0) AS prev_row_count,
  CAST(CASE WHEN row_count_at_timestamp>1 OR COALESCE(prev_row_count,0)>1 THEN 1 ELSE 0 END AS bit) AS duplicate_flag,
  CAST(CASE WHEN gap_s IS NOT NULL AND gap_s<>10 THEN 1 ELSE 0 END AS bit) AS gap_flag,
  CAST(CASE WHEN counter_value IS NULL OR prev_counter IS NULL THEN 1 ELSE 0 END AS bit) AS null_flag,
  CAST(CASE WHEN delta_raw<0 THEN 1 ELSE 0 END AS bit) AS reset_flag,
  CAST(CASE WHEN delta_raw>150000 THEN 1 ELSE 0 END AS bit) AS large_jump_flag
FROM classified c CROSS JOIN bounds b
WHERE c.fecha>b.t0 AND c.fecha<=b.t1
ORDER BY c.fecha,c.tm;
"""


def load_intraday_profile_legacy(start, end, engine=None):
    """Load raw-counter deltas by conveyor and operational shift.

    ``start`` and ``end`` are inclusive operational dates. An interval is
    (previous tick, endpoint]; endpoints exactly at 08:00/20:00 are assigned
    to the shift that ended there. Every in-window raw endpoint is returned,
    including bad-quality rows. ``mass_h`` is null where a delta is not
    contiguous/usable; large jumps retain their candidate delta but carry a
    ``large_jump`` quality and must be explicitly masked by consumers.
    """
    d0, d1 = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if d1 < d0:
        raise ValueError("end debe ser igual o posterior a start")
    try:
        from . import db_source as dbs
    except ImportError:
        dbs = None
    schema = getattr(dbs, "SCHEMA", "inventar_SpcHidr")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", schema):
        raise ValueError("Esquema hidro inválido")
    query = text(_SQL.format(schema=schema))
    if engine is None:
        if dbs is None:
            raise RuntimeError("Configurar conexión SIIR o entregar engine explícito")
        engine = dbs.get_engine()
    frame = pd.read_sql(query, engine, params={
        "start": d0.date(), "end": d1.date(),
    })
    # Preserve SQL rows and diagnostics; add only stable pandas dtypes.
    for col in ("start", "end", "fecha_op"):
        if col in frame:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    return frame


_COMPACT_SQL = """
WITH bounds AS (
    SELECT DATEADD(hour, 8, CAST(:start AS datetime2(0))) AS t0,
           DATEADD(hour, 8, DATEADD(day, 1, CAST(:end AS datetime2(0)))) AS t1
), anchor AS (
    SELECT x.fecha, CAST(x.tot_008 AS float) AS tot_008,
           CAST(x.tot_108 AS float) AS tot_108
    FROM bounds b
    CROSS APPLY (
        SELECT TOP (1) WITH TIES fecha, tot_008, tot_108
        FROM {schema}.tot_TM
        WHERE fecha IS NOT NULL AND fecha <= b.t0
        ORDER BY fecha DESC
    ) x
), inside_window AS (
    SELECT x.fecha, CAST(x.tot_008 AS float) AS tot_008,
           CAST(x.tot_108 AS float) AS tot_108
    FROM bounds b JOIN {schema}.tot_TM x
      ON x.fecha > b.t0 AND x.fecha <= b.t1
)
SELECT fecha, tot_008, tot_108 FROM anchor
UNION ALL
SELECT fecha, tot_008, tot_108 FROM inside_window
"""

_INTRADAY_COLUMNS = [
    'start', 'end', 'fecha_op', 'turno', 'tm', 'mass_h', 'delta_raw',
    'quality', 'gap_s', 'row_count_at_timestamp', 'prev_row_count',
    'duplicate_flag', 'gap_flag', 'null_flag', 'reset_flag', 'large_jump_flag',
]


def _profile_from_ticks(ticks, start, end):
    """Rebuild the legacy interval contract from compact 10-second counters.

    SQL Server's ``LAG``/quality fields are computed here over the raw tick
    rows. Duplicate rows remain present and invalid; ordering within ties is
    stable only for diagnostics whose legacy SQL ordering was unspecified.
    """
    d0, d1 = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if ticks is None or ticks.empty:
        return pd.DataFrame(columns=_INTRADAY_COLUMNS)
    source = ticks[['fecha', 'tot_008', 'tot_108']].copy()
    source['fecha'] = pd.to_datetime(source.fecha, errors='coerce')
    long = pd.concat([
        source[['fecha', 'tot_008']].rename(columns={'tot_008': 'counter_value'}).assign(tm='TM1'),
        source[['fecha', 'tot_108']].rename(columns={'tot_108': 'counter_value'}).assign(tm='TM2'),
    ], ignore_index=True)
    long['counter_value'] = pd.to_numeric(long.counter_value, errors='coerce').astype('float64')
    long = long.sort_values(['tm', 'fecha'], kind='mergesort').reset_index(drop=True)
    grouped = long.groupby('tm', sort=False, dropna=False)
    long['row_count_at_timestamp'] = long.groupby(['tm', 'fecha'], sort=False, dropna=False).fecha.transform('size').astype('int64')
    long['prev_fecha'] = grouped.fecha.shift()
    long['prev_counter'] = grouped.counter_value.shift()
    long['prev_row_count'] = grouped.row_count_at_timestamp.shift().fillna(0).astype('int64')
    # SQL DATEDIFF(second) counts crossed whole-second boundaries.
    end_floor = long.fecha.dt.floor('s')
    prev_floor = long.prev_fecha.dt.floor('s')
    long['gap_s'] = (end_floor - prev_floor).dt.total_seconds()
    long['delta_raw'] = long.counter_value - long.prev_counter
    long['bucket_time'] = long.fecha - pd.Timedelta(microseconds=1)
    duplicate = long.row_count_at_timestamp.gt(1) | long.prev_row_count.gt(1)
    no_previous = long.prev_fecha.isna()
    has_null = long.counter_value.isna() | long.prev_counter.isna()
    bad_gap = long.gap_s.notna() & long.gap_s.ne(10)
    reset = long.delta_raw.lt(0)
    large = long.delta_raw.gt(150000)
    valid_delta = long.delta_raw.ge(0)
    long['quality'] = np.select(
        [duplicate, no_previous, has_null, bad_gap, reset, large, valid_delta],
        ['duplicate', 'no_previous', 'null', 'gap', 'reset', 'large_jump', 'ok'],
        default='null')
    usable = (long.gap_s.eq(10) & ~has_null & valid_delta
              & long.row_count_at_timestamp.eq(1) & long.prev_row_count.le(1))
    long['mass_h'] = long.delta_raw.where(usable)
    mask = (long.fecha.gt(d0 + pd.Timedelta(hours=8))
            & long.fecha.le(d1 + pd.Timedelta(days=1, hours=8)))
    out = long.loc[mask].copy()
    out['start'] = out.prev_fecha
    out['end'] = out.fecha
    out['fecha_op'] = (out.bucket_time - pd.Timedelta(hours=8)).dt.normalize()
    hour = out.bucket_time.dt.hour
    out['turno'] = np.where(hour.ge(8) & hour.lt(20), 'A', 'B')
    out['duplicate_flag'] = duplicate.loc[mask].astype(bool)
    out['gap_flag'] = (out.gap_s.notna() & out.gap_s.ne(10)).loc[mask].astype(bool)
    out['null_flag'] = has_null.loc[mask].astype(bool)
    out['reset_flag'] = reset.loc[mask].fillna(False).astype(bool)
    out['large_jump_flag'] = large.loc[mask].fillna(False).astype(bool)
    out = out.loc[:, _INTRADAY_COLUMNS]
    out = out.sort_values(['end', 'tm'], kind='mergesort').reset_index(drop=True)
    return out


def load_intraday_profile(start, end, engine=None):
    """Load compact raw counters then rebuild the legacy interval contract.

    Reads one row per source tick and the two conveyor counters only. It keeps
    the same 10-second window, tied anchor rows, interval diagnostics and
    quality rules as ``load_intraday_profile_legacy``.
    """
    d0, d1 = pd.Timestamp(start).normalize(), pd.Timestamp(end).normalize()
    if d1 < d0:
        raise ValueError("end debe ser igual o posterior a start")
    try:
        from . import db_source as dbs
    except ImportError:
        dbs = None
    schema = getattr(dbs, "SCHEMA", "inventar_SpcHidr")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", schema):
        raise ValueError("Esquema hidro inválido")
    query = text(_COMPACT_SQL.format(schema=schema))
    if engine is None:
        if dbs is None:
            raise RuntimeError("Configurar conexión SIIR o entregar engine explícito")
        engine = dbs.get_engine()
    ticks = pd.read_sql(query, engine, params={
        "start": d0.date(), "end": d1.date(),
    })
    return _profile_from_ticks(ticks, d0, d1)
