"""Read-only helpers for stored reconciled history before a selected Case.

This module is intentionally independent of the app/DB layer. It never reads
measured series as a fallback and keeps uncovered dates as gaps.
"""
from __future__ import annotations

from collections import OrderedDict
import csv
from datetime import date, datetime, timedelta
import hashlib
import json
from typing import Iterable, Mapping
from pathlib import Path


def _date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def reconciled_increment_tcu(row: Mapping) -> float | None:
    """Convert one persisted daily row to net Cu tonnes.

    q is m3/h; Cu concentrations are g/L. At zero q the contribution is
    exactly zero even when the concentration is undefined. Missing values at
    positive q remain None.
    """
    try:
        if row.get("q") is None:
            return None
        q_riego = float(row["q"])
        q_pls_raw = row.get("q_pls")
        if q_pls_raw is None:
            return None
        q_pls = float(q_pls_raw)
        if q_riego == 0 and q_pls == 0:
            return 0.0
        cu_drena = row.get("cu_drena")
        cu_riego = row.get("cu_riego")
        if (q_pls != 0 and cu_drena is None) or (q_riego != 0 and cu_riego is None):
            return None
        return 24.0 / 1000.0 * (
            (q_pls * float(cu_drena) if q_pls != 0 else 0.0)
            - (q_riego * float(cu_riego) if q_riego != 0 else 0.0)
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def normalize_history_rows(rows: Iterable[Mapping], window_start,
                           official_cases: Mapping[int, Mapping] | None = None):
    """Normalize eligible daily rows and deduplicate overlapping run tails.

    If ``official_cases`` is provided, rows must reference a currently
    official Case with matching 125-flow model metadata and a date covered by
    that Case. The reconciliation table does not store solver_run_id, so this
    validation cannot prove which official solver run produced the row.
    """
    cutoff = _date(window_start)
    selected = {}
    for source in rows:
        row = dict(source)
        day = _date(row.get("date", row.get("fecha")))
        if day >= cutoff:
            continue
        case_id = row.get("caso_id")
        if official_cases is not None:
            if case_id is None or int(case_id) not in official_cases:
                continue
            case = official_cases[int(case_id)]
            if (case.get("modelo_codigo") != "hidrometalurgia_125_v2"
                    or case.get("modelo_version") != "v2"
                    or int(case.get("total_flujos") or 0) != 125
                    or day < _date(case["fecha_inicio"])
                    or day > _date(case["fecha_fin"])):
                continue
        pad = str(row.get("label") or row.get("pad") or "").upper()
        pile = str(row.get("parcela_nombre") or row.get("parcela") or "").upper()
        if not pad or not pile:
            continue
        row.update(date=day, label=pad, parcela=pile,
                   increment_tcu=reconciled_increment_tcu(row),
                   source="Histórico reconciliado guardado")
        key = (pad, pile, day)
        previous = selected.get(key)
        # A persisted run may contain the prior campaign's last operational
        # day. Keep the row from the later week, matching the app's policy.
        if (previous is None
                or (_date(row["semana_lunes"]), int(row.get("run_id") or 0))
                > (_date(previous["semana_lunes"]), int(previous.get("run_id") or 0))):
            selected[key] = row
    return sorted(selected.values(), key=lambda r: (r["label"], r["parcela"], r["date"]))


def calendar_rows(rows: Iterable[Mapping], label: str, pile: str,
                  start, end):
    """Return one date row per calendar day; uncovered days stay explicit gaps."""
    start_day, end_day = _date(start), _date(end)
    by_date = { _date(r["date"]): r for r in rows
                if str(r.get("label", "")).upper() == label.upper()
                and str(r.get("parcela", "")).upper() == pile.upper() }
    result = []
    day = start_day
    while day <= end_day:
        row = by_date.get(day)
        result.append({
            "date": day,
            "reconciled_increment_tcu": row.get("increment_tcu") if row else None,
            "source": row.get("source") if row else None,
            "caso_id": row.get("caso_id") if row else None,
            "run_id": row.get("run_id") if row else None,
            "gap": row is None or row.get("increment_tcu") is None,
        })
        day += timedelta(days=1)
    return result


def load_validated_official_history(fixture_path, window_start):
    """Load the compact, audited official-reconciliation fixture pre-Case.

    Fixture rows are already campaign recovery percentages (not increments).
    The adjacent manifest pins fixture/source hashes and the 1,180/1,180
    SIIR-vs-official validation cohort. Oct 1 belongs to the selected Case and
    is therefore excluded when the window starts on that date.
    """
    path = Path(fixture_path)
    manifest_path = path.with_name("historico_oficial_validado_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "validated_fixture" or manifest.get("fixture") != path.name:
        raise ValueError("Official-history fixture manifest does not match the fixture")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != manifest.get("fixture_sha256"):
        raise ValueError("Official-history fixture hash mismatch")
    cutoff = _date(window_start)
    rows = []
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            day = _date(row["date"])
            if day >= cutoff:
                continue
            rows.append({
                "date": day, "label": row["pad"].upper(),
                "parcela": row["pile"].upper(),
                "value_pct": float(row["value_pct"]),
                "campaign": int(row["campaign"]),
                "source": "Histórico reconciliado oficial",
                "source_sheet": row["source_sheet"],
                "source_row": int(row["source_row"]),
                "source_column": int(row["source_column"]),
            })
    return rows


def official_history_calendar(rows: Iterable[Mapping], label: str, pile: str,
                              start, end):
    """Expand validated official values to calendar dates, preserving gaps."""
    start_day, end_day = _date(start), _date(end)
    by_date = { _date(r["date"]): r for r in rows
                if str(r.get("label", "")).upper() == label.upper()
                and str(r.get("parcela", "")).upper() == pile.upper() }
    result = []
    day = start_day
    while day <= end_day:
        row = by_date.get(day)
        result.append({
            "date": day,
            "value_pct": row.get("value_pct") if row else None,
            "source": row.get("source") if row else None,
            "campaign": row.get("campaign") if row else None,
            "gap": row is None,
        })
        day += timedelta(days=1)
    return result


def build_readonly_query(recon_schema: str, hidro_schema: str):
    """Build one batch SELECT; caller supplies validated schema identifiers."""
    import re
    from sqlalchemy import text

    for schema in (recon_schema, hidro_schema):
        if not re.fullmatch(r"[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)?", schema):
            raise ValueError("Invalid SQL schema identifier")
    sql = f"""
    WITH official_cases AS (
        SELECT c.id AS caso_id, c.fecha_inicio, c.fecha_fin,
               m.codigo AS modelo_codigo, m.version AS modelo_version,
               m.total_flujos, o.solver_run_id
        FROM {hidro_schema}.recon_caso c
        JOIN {hidro_schema}.recon_caso_oficial o ON o.caso_id = c.id
        JOIN {hidro_schema}.recon_solver_run sr
          ON sr.id = o.solver_run_id AND sr.caso_id = c.id
        JOIN {hidro_schema}.recon_modelo m ON m.id = c.modelo_id
        WHERE sr.estado = 'success'
          AND m.codigo = 'hidrometalurgia_125_v2'
          AND m.version = 'v2' AND m.total_flujos = 125
    ), eligible_runs AS (
        SELECT rr.id, rr.semana_lunes, rr.semana_fin, rr.caso_id,
               rr.converged,
               ROW_NUMBER() OVER (
                   PARTITION BY rr.caso_id, rr.semana_lunes
                   ORDER BY rr.id DESC
               ) AS run_rank
        FROM {recon_schema}.reconciliacion_run rr
        JOIN official_cases c ON c.caso_id = rr.caso_id
        WHERE rr.converged = 1
    )
    SELECT r.semana_lunes, r.semana_fin, r.caso_id, r.id AS run_id,
           r.converged, d.dia_offset,
           DATEADD(day, d.dia_offset, r.semana_lunes) AS date,
           d.material_id, d.label, d.parcela_nombre,
           d.fdrena, d.q, d.q_pls, d.cu_drena, d.cu_riego,
           c.fecha_inicio AS case_start, c.fecha_fin AS case_end,
           c.solver_run_id
    FROM {recon_schema}.reconciliacion_detalle_dia d
    JOIN {recon_schema}.reconciliacion_run r ON r.id = d.run_id
    JOIN eligible_runs er ON er.id = r.id AND er.run_rank = 1
    JOIN official_cases c ON c.caso_id = r.caso_id
    WHERE r.converged = 1
      AND DATEADD(day, d.dia_offset, r.semana_lunes) < :window_start
      AND DATEADD(day, d.dia_offset, r.semana_lunes) >= c.fecha_inicio
      AND DATEADD(day, d.dia_offset, r.semana_lunes) <= c.fecha_fin
      AND d.label IN ('OXIDOS', 'SULFUROS')
    ORDER BY [date], d.label, d.parcela_nombre
    """
    return text(sql)


class HistoryReader:
    """Batch reader with a small process-local cache keyed by Case window."""

    def __init__(self):
        self._cache = OrderedDict()

    def load(self, engine, recon_schema: str, hidro_schema: str,
             cache_token, window_start):
        start_day = _date(window_start)
        key = (id(engine), str(cache_token), start_day, recon_schema, hidro_schema)
        if key not in self._cache:
            query = build_readonly_query(recon_schema, hidro_schema)
            with engine.connect() as conn:
                raw = conn.execute(query, {"window_start": start_day}).mappings().all()
            self._cache[key] = normalize_history_rows(raw, start_day, official_cases=None)
            self._cache.move_to_end(key)
            while len(self._cache) > 8:
                self._cache.popitem(last=False)
        else:
            self._cache.move_to_end(key)
        return list(self._cache[key])

    def clear(self, cache_token=None):
        if cache_token is None:
            self._cache.clear()
        else:
            token = str(cache_token)
            for key in list(self._cache):
                if key[1] == token:
                    self._cache.pop(key, None)
