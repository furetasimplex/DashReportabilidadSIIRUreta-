"""Tablas del informe a partir de evidencia local, sin SQL."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import median

P=Path(__file__).parent


def run():
    data=json.loads((P/'mediciones.json').read_text())
    groups=defaultdict(list)
    for m in data:
        if not m['with_statistics_xml']: groups[m['label']].append(m)
    lines=['# Mediciones observadas','',
           '| Consulta | Primera s | Segunda s | Tercera s | Min / mediana / max s | Filas | CPU ejecución ms (1/2/3) | Elapsed SQL ms (1/2/3) | Lecturas lógicas (1/2/3) |',
           '|---|---:|---:|---:|---|---|---|---|---|']
    for label,ms in groups.items():
        times=[m['client_seconds'] for m in ms]
        first=[f'{v:.3f}' for v in times]+['—']*(3-len(times))
        cpu='/'.join(str(m['time_messages'][-1]['cpu_ms']) if m['time_messages'] else 'NA' for m in ms)
        elapsed='/'.join(str(m['time_messages'][-1]['elapsed_ms']) if m['time_messages'] else 'NA' for m in ms)
        reads='/'.join(str(sum(x['logical_reads'] for x in m['io'])) for m in ms)
        lines.append(f"| {label} | {' | '.join(first[:3])} | {min(times):.3f} / {median(times):.3f} / {max(times):.3f} | {','.join(str(m['rows']) for m in ms)} | {cpu} | {elapsed} | {reads} |")
    lines+=['','## IO por objeto — primera ejecución observada de 102 días','',
            '| Caso | Objeto | Scan count | Logical reads | Physical reads | Read-ahead reads |',
            '|---|---|---:|---:|---:|---:|']
    for label in ('timeline_102d_ox_p1','timeline_102d_sulf_p7'):
        if label not in groups: continue
        totals=defaultdict(lambda:defaultdict(int))
        for io in groups[label][0]['io']:
            for k in ('scan_count','logical_reads','physical_reads','read_ahead_reads'): totals[io['object']][k]+=io[k]
        for obj,vals in sorted(totals.items(),key=lambda x:x[1]['logical_reads'],reverse=True):
            lines.append(f"| {label} | {obj} | {vals['scan_count']} | {vals['logical_reads']} | {vals['physical_reads']} | {vals['read_ahead_reads']} |")
    (P/'mediciones_tablas.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':run()
