from __future__ import annotations

from contextvars import ContextVar
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import time

_TRACE_ID = ContextVar('curvas_recon_perf_trace_id', default=None)
_WRITE_LOCK = threading.Lock()
_LOG_PATH = Path(__file__).resolve().parent.parent / 'auditorias' / 'curvas_recon_performance.jsonl'


def set_trace_id(trace_id):
    return _TRACE_ID.set(str(trace_id) if trace_id else None)


def reset_trace_id(token):
    _TRACE_ID.reset(token)


def record_phase(phase, seconds, *, trace_id=None, **fields):
    """Append local phase timings only; never include SQL text or row contents."""
    trace_id = trace_id or _TRACE_ID.get()
    if not trace_id:
        return False
    record = {
        'ts_utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
        'trace_id': str(trace_id),
        'phase': str(phase),
        'seconds': round(float(seconds), 6),
    }
    for key, value in fields.items():
        if value is None or isinstance(value, (str, int, float, bool)):
            record[str(key)] = value
    try:
        line = json.dumps(record, ensure_ascii=True, separators=(',', ':'), allow_nan=False)
        with _WRITE_LOCK:
            _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _LOG_PATH.open('a', encoding='utf-8', newline='\n') as stream:
                stream.write(line + '\n')
    except Exception:
        # Timing diagnostics must never change calculation behavior.
        return False
    return True


def timed_phase(phase, *, trace_id=None, **fields):
    """Context manager for short callback/render phases."""
    class _Timed:
        def __enter__(self):
            self.started = time.perf_counter()
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            record_phase(phase, time.perf_counter() - self.started,
                         trace_id=trace_id, **fields)
            return False
    return _Timed()


def log_path():
    return _LOG_PATH
