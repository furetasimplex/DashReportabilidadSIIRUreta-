"""Helpers de evidencia de pruebas; no se importa desde runtime."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from uuid import uuid4

OUT = Path(__file__).with_name('test_evidence')


def write_evidence(category, name, result, *, period, definitions=None):
    if category not in {'CURRENT_SMOKE', 'REGRESSION_TEST', 'STRUCTURAL_TEST', 'HISTORICAL_BASELINE'}:
        raise ValueError(category)
    now = datetime.now(timezone.utc)
    prefix = {'CURRENT_SMOKE':'smoke_current','REGRESSION_TEST':'regression',
              'STRUCTURAL_TEST':'structural','HISTORICAL_BASELINE':'baseline'}[category]
    OUT.mkdir(exist_ok=True)
    path = OUT / f'{prefix}_{name}_{now:%Y%m%dT%H%M%S%fZ}_{uuid4().hex[:8]}.json'
    record = dict(type=category, executed_at=now.isoformat(), environment='DEV', database='inventar_SpcHidr',
                  period=period, definitions=definitions, result=result)
    with path.open('x', encoding='utf-8') as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
        f.write('\n')
    print(path)
    return path


def definition_hashes(conn, objects):
    from sqlalchemy import text
    return {obj: hashlib.sha256(conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:obj))'),
            {'obj':obj}).scalar_one().encode()).hexdigest() for obj in objects}
