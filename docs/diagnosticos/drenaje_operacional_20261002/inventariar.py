"""Auditoria local reproducible. No importa la app ni abre conexiones SQL."""
from pathlib import Path
import csv
import json
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
TERMS = ['v_drena_oxido_unpivot', 'v_drena_sulfuro_unpivot',
         'drena_concentrados_oxido', 'drena_concentrados_sulfuro',
         'fecha_ini_drenaje', 'fecha_fin_drenaje', 'sp_flujo_riego_drenaje',
         'v_drena_oxido_operacional', 'v_drena_sulfuro_operacional']
pattern = re.compile('|'.join(map(re.escape, TERMS)), re.I)
files = subprocess.check_output(['rg', '--files', '--hidden', '--no-ignore', '-g', '!.git/**',
    '-g', '!venv/**', '-g', '!.venv/**', '-g', '!**/node_modules/**',
    '-g', '!**/__pycache__/**', '-g', '!**/.pytest_cache/**', '.'],
    cwd=ROOT, text=True, encoding='utf-8').splitlines()
rows = []
for name in files:
    p = ROOT / name
    if OUT in p.resolve().parents or p.suffix.lower() not in {
        '.py', '.sql', '.md', '.txt', '.json', '.csv', '.js', '.html', '.yaml', '.yml'}:
        continue
    raw = p.read_bytes()
    try:
        content = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')
    except UnicodeError:
        content = raw.decode('cp1252', errors='replace')
    for n, line in enumerate(content.splitlines(), 1):
        for term in sorted(set(m.group(0).lower() for m in pattern.finditer(line))):
            rows.append([p.relative_to(ROOT).as_posix(), n, term])
with (OUT / 'inventario_referencias.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['archivo', 'linea', 'referencia']); w.writerows(rows)

objects = []
for rel in ['report_export/exports/auditoria_ley_srr_202609/catalogo.json',
            'report_export/exports/diagnostico_fase4/catalogo_dev.json']:
    for obj in json.loads((ROOT / rel).read_text(encoding='utf-8-sig')):
        definition = obj.get('definition') or ''
        matches = sorted(set(m.group(0).lower() for m in pattern.finditer(definition)))
        if matches:
            objects.append([rel, obj.get('esquema'), obj.get('name', obj.get('nombre')),
                            '; '.join(matches)])
with (OUT / 'inventario_objetos_catalogados.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f); w.writerow(['catalogo_historico', 'esquema', 'objeto', 'referencias']); w.writerows(objects)
print(f'{len(rows)} referencias en {len(set(r[0] for r in rows))} archivos; {len(objects)} objetos/versiones catalogados.')
