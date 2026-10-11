"""Verifica solo artefactos de auditoria. No usa SQL Server."""
from pathlib import Path
import ast
import json
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
catalog = json.loads((ROOT / 'report_export/exports/auditoria_ley_srr_202609/catalogo.json').read_text(encoding='utf-8-sig'))
definitions = {o['name']: o.get('definition') or '' for o in catalog}
def normalized(s):
    return '\n'.join(line.rstrip() for line in s.splitlines() if line.strip()).strip()
count = 0
for p in HERE.glob('*.snapshot.sql'):
    body = p.read_text(encoding='utf-8').split('\n', 1)[1]
    assert normalized(body) == normalized(definitions[p.name.removesuffix('.snapshot.sql')]), p
    count += 1
for p in HERE.glob('*.py'):
    ast.parse(p.read_text(encoding='utf-8'))
for p in HERE.iterdir():
    if p.is_file() and p.suffix in {'.py', '.sql', '.md'}:
        for n, line in enumerate(p.read_text(encoding='utf-8').splitlines(), 1):
            assert line == line.rstrip(), (p.name, n, 'whitespace final')
report = (HERE / 'INFORME.md').read_text(encoding='utf-8')
for link in re.findall(r'\]\(([^)]+)\)', report):
    assert (HERE / link).exists(), link
for name in ['03_migracion_pendiente.sql', '04_rollback_pendiente.sql']:
    s = (HERE / name).read_text(encoding='utf-8')
    assert '@aprobado bit=0' in s and '@persistir bit=0' in s
    assert 'ROLLBACK TRANSACTION' in s and 'COMPLETAR_DEV' in s
subprocess.run(['git','diff','--check'], cwd=ROOT, check=True)
print(f'OK: {count} snapshots corresponden al catalogo; Python parseable; enlaces, whitespace y bloqueos verificados; git diff --check limpio.')
print('No se valido sintaxis/ejecucion T-SQL en servidor ni se abrieron conexiones.')
