"""Read-only intraturn wet-mass profile from CV008/CV108 counters.

It does not publish, synchronize, or modify SQL data.
The query retains every raw endpoint in the requested operational window and
exposes quality diagnostics so callers can decide which intervals to use.
"""
import re

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


def load_intraday_profile(start, end, engine=None):
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
