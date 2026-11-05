"""Fail-closed adapter for the FROZEN Case 10009 Sulfides source bundle.

This is the regression fixture of the "maduras fijas, nuevas moviles" method:
it supports only the captured Case 10009 bundle and does not query the
database. The generic Case loader (any official Case, Oxides and Sulfides,
SELECT-only) is :mod:`curvas_recon.maduras_inputs`; both share the same
identity-bearing payload contract and validation (``validate_payload``).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
import csv
import json
from pathlib import Path
from typing import Callable, Mapping

from .maduras_inputs import MadurasInputError, validate_payload


_FIXTURE_SHA256 = 'a2946b35e945b9bece6faa2ccd02067da00bfe3a4f2a86652259320f4ac90c6a'
_HISTORY_SHA256 = '9d1bf3d3029e09179c307ffe83a8a95a794cc603c4db3ff5995dda69755bc52c'
_SUPPORTED_CASE = 10009
_SUPPORTED_SOLVER_RUN = 10082
_SUPPORTED_PROFILE_RUN = 2348
_SUPPORTED_START = date(2026, 9, 1)
_SUPPORTED_END = date(2026, 9, 7)


# Alias kept for callers of the original, Sulfides-only loader.
SulfideInputError = MadurasInputError


def _day(value, field):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as exc:
        raise SulfideInputError(f'invalid {field}') from exc


def _target_from_anchor(anchor):
    if not isinstance(anchor, Mapping):
        raise SulfideInputError('official Case anchor is required')
    candidates = [anchor]
    for key in ('SULFUROS', 'sulfuros'):
        if isinstance(anchor.get(key), Mapping):
            candidates.insert(0, anchor[key])
    for candidate in candidates:
        for key in ('net_cu_target_t', 'cu_neto_objetivo_t', 'target_net_t'):
            value = candidate.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
    raise SulfideInputError('anchor has no sulfide net-Cu target')


def _default_fixture_path():
    # This layout is mirrored in the staged patch: sources/curvas_recon and
    # sources/test_fixtures. It will become package-relative when applied.
    return Path(__file__).resolve().parents[1] / 'test_fixtures' / 'caso10009_sulfuros_net_inputs.json'


def _canonical_sha256(raw):
    """SHA-256 over CRLF-normalised bytes.

    The recorded hashes were taken on a Windows checkout (CRLF). A Linux or
    autocrlf checkout holds LF; normalising line endings keeps the integrity
    check about content, not about the checkout's newline convention.
    """
    return hashlib.sha256(raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')).hexdigest()


def _read_fixture(path):
    try:
        raw = Path(path).read_bytes()
    except OSError as exc:
        raise SulfideInputError('captured sulfide input fixture is unavailable') from exc
    if _canonical_sha256(raw) != _FIXTURE_SHA256:
        raise SulfideInputError('captured sulfide input fixture hash mismatch')
    try:
        payload = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SulfideInputError('captured sulfide input fixture is invalid JSON') from exc
    return payload


def _validate_payload(payload, case_id, start, end, target):
    """Frozen-bundle contract: only the captured Case 10009 window is valid."""
    if case_id != _SUPPORTED_CASE or start != _SUPPORTED_START or end != _SUPPORTED_END:
        raise SulfideInputError('no validated source bundle for requested Case/window')
    return validate_payload(
        payload, case_id=_SUPPORTED_CASE, label='SULFUROS', start=start, end=end, target=target,
        expected_ids={'solver_run_id': _SUPPORTED_SOLVER_RUN,
                      'allocation_profile_run_id': _SUPPORTED_PROFILE_RUN})


def load_sulfide_inputs(week_start, week_end, caso_id, anchor, *,
                        source_provider: Callable | None = None,
                        fixture_path=None):
    """Load validated rows for a known Sulfides Case.

    `source_provider` is an injection seam for offline tests or a future
    SELECT-only adapter. It receives named `week_start`, `week_end`,
    `case_id`, and `anchor` arguments and must return the same canonical
    payload as the captured fixture. The default never opens a DB connection.
    """
    start, end = _day(week_start, 'week_start'), _day(week_end, 'week_end')
    try:
        case_id = int(caso_id)
    except (TypeError, ValueError) as exc:
        raise SulfideInputError('invalid case id') from exc
    target = _target_from_anchor(anchor)
    if source_provider is None:
        if fixture_path is not None:
            payload = _read_fixture(fixture_path)
        else:
            payload = _read_fixture(_default_fixture_path())
        if not isinstance(payload.get('metadata'), Mapping):
            raise SulfideInputError('fixture provenance metadata is missing')
        meta = dict(payload['metadata'])
        history_path = Path(fixture_path or _default_fixture_path()).with_name('caso10009_sulfuros_historia_agosto.csv')
        raw_history = history_path.read_bytes()
        if _canonical_sha256(raw_history) != _HISTORY_SHA256:
            raise SulfideInputError('captured August history hash mismatch')
        template = {(r['pile'], int(r['campaign'])): r for r in payload['rows']}
        known = {(r['pile'], int(r['campaign']), r['date']) for r in payload['rows']}
        for history in csv.DictReader(raw_history.decode('utf-8').splitlines()):
            key = (history['pile'], int(history['campaign']))
            if (*key, history['date']) in known:
                continue
            row = {k: template[key][k] for k in ('pad', 'pile', 'campaign', 'cu_apilado_t', 'first_irrigation')}
            row.update(date=history['date'], official_pct=float(history['official_pct']),
                       observed_pct=float(history['observed_pct']),
                       observation_source='captured August primary history; distinct from consolidated readings')
            payload['rows'].append(row)
        meta['august_history_sha256'] = _HISTORY_SHA256
        meta['history_qualification'] = 'Primary August recovery retained; 377 source differences documented.'
        source_ids = {
            'case_id': meta.get('case_id'),
            'solver_run_id': meta.get('solver_run_id'),
            'allocation_profile_run_id': meta.get('allocation_profile_run_id'),
            'fixture_sha256': _FIXTURE_SHA256,
            'august_history_sha256': _HISTORY_SHA256,
            'source_sha256': meta.get('source_sha256'),
            'qualification': meta.get('qualification'),
        }
        payload = {
            'rows': payload.get('rows'), 'target_net_t': payload.get('target_net_t'),
            'target_period_start': _SUPPORTED_START.isoformat(),
            'source_ids': source_ids, 'metadata': meta,
        }
    else:
        payload = source_provider(week_start=start, week_end=end,
                                  case_id=case_id, anchor=anchor)
    return _validate_payload(payload, case_id, start, end, target)
