"""Consolida evidencia local; no conecta a SQL ni cambia runtime."""
import hashlib
import json
from pathlib import Path

P = Path(__file__).parent


def run():
    before = json.loads((P / 'runtime_before.json').read_text(encoding='utf-8'))
    changed = [name for name, digest in before.items()
               if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest]
    assert set(changed) == {'lixiviacion\\db.py', 'lixiviacion\\test_diagnostic_operational.py'}, changed
    visual = json.loads((P / 'visual/review.json').read_text(encoding='utf-8'))
    smoke = json.loads((P / 'smoke.json').read_text(encoding='utf-8'))
    assert visual['passed'] and smoke['passed']
    plans = json.loads((P / 'planes_analizados.json').read_text(encoding='utf-8'))
    summary = []
    for p in plans:
        opposite = 'sulfuro' if 'p1_1' in p['file'] else 'oxido'
        for s in p['statements']:
            ops = [o for o in s['operators'] if any(opposite in obj.get('Table', '') for obj in o['objects'])]
            assert ops and all(o['ActualExecutions'] == 0 and o['ActualRowsRead'] == 0 for o in ops)
            summary.append({'file': p['file'], 'opposite_family_zero_executions': True,
                            'opposite_nodes': len(ops), 'dop': s['query_plan']['DegreeOfParallelism'],
                            'warnings': s['Warnings'], 'optimizer_abort': s['attributes'].get('StatementOptmEarlyAbortReason')})
    result = {'changed_existing_files': changed, 'other_recorded_runtime_files_unchanged': True,
              'smoke_pass': True, 'chrome_pass': True, 'plans': summary,
              'note': 'functional stage hash changed only because tests were edited while comparison ran; db.py was guarded by original SHA before integration.'}
    (P / 'integrity_final.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    run()
