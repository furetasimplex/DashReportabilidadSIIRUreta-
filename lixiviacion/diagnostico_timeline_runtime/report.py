"""Tablas de evidencia runtime12; no ejecuta SQL."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from lixiviacion.diagnostico_performance.analyze import plan

P=Path(__file__).parent


def run():
    data=json.loads((P/'benchmark.json').read_text(encoding='utf-8'))
    old=json.loads((P.parent/'diagnostico_performance'/'resumen.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for r in data:
        if not r['with_statistics_xml']:groups[r['label']].append(r)
    rows=[];summary=[]
    for label,rs in groups.items():
        days=int(label.rsplit('_',1)[1][:-1]);pad=rs[0]['params']['pad_id']
        baseline=next(x for x in old if x['label']==f"timeline_{days}d_{'ox_p1' if pad==1 else 'sulf_p7'}")
        values=[r['client_seconds'] for r in rs];reads=[sum(i['logical_reads'] for i in r['io']) for r in rs]
        item={'label':label,'seconds':values,'min':min(values),'median':median(values),'max':max(values),
              'reads':reads,'baseline_seconds':baseline['median'],'baseline_reads':median(baseline['logical_reads']),
              'speedup':baseline['median']/median(values),'io_reduction_pct':100*(1-median(reads)/median(baseline['logical_reads']))}
        summary.append(item)
        rows.append(f"| {label} | {' / '.join(f'{v:.4f}' for v in values)} | {min(values):.4f} / {median(values):.4f} / {max(values):.4f} | {'/'.join(str(r['time_messages'][-1]['cpu_ms']) for r in rs)} | {'/'.join(str(r['time_messages'][-1]['elapsed_ms']) for r in rs)} | {'/'.join(map(str,reads))} | {item['speedup']:.2f}x | {item['io_reduction_pct']:.2f}% |")
    (P/'resumen.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    lines=['# Benchmark del SQL exacto integrado (12 columnas)','',
           '| Caso | Tres observadas s | Min / mediana / max s | CPU ms | Elapsed SQL ms | Logical reads | Speedup | Reducción IO |',
           '|---|---|---|---|---|---|---|---|',*rows,'',
           'Medianas sin XML. Speedup contra baseline12 de la auditoría previa; las ejecuciones anteriores actuales están en functional_timings.json. Sin limpieza de caché. No reutiliza tiempos de candidate24.']
    (P/'benchmark_tablas.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plans=[plan(f) for f in (P/'plans').glob('*.sqlplan')]
    (P/'planes_analizados.json').write_text(json.dumps(plans,indent=2),encoding='utf-8')


if __name__=='__main__':run()
