"""Genera tablas y extractos de evidencia locales; sin acceso SQL."""
from collections import defaultdict
import json
from pathlib import Path
from statistics import median
from lixiviacion.diagnostico_performance.analyze import plan

P=Path(__file__).parent


def run():
    checks=json.loads((P/'comparacion_funcional.json').read_text(encoding='utf-8'))
    benchmarks=json.loads((P/'benchmark.json').read_text(encoding='utf-8'))
    old=json.loads((P.parent/'diagnostico_performance'/'resumen.json').read_text(encoding='utf-8'))
    groups=defaultdict(list)
    for m in benchmarks:
        if not m['with_statistics_xml']: groups[m['label']].append(m)
    lines=['# Resultados del candidato','',
           'Comparación exacta, sin normalizar NULL ni composición. Baseline runtime12 + referencia oficial24. Tiempos cliente incluyen execute+fetch.', '',
           '## Equivalencia','',
           '| Caso | Diseño | Filas | Solo baseline | Solo candidato | Diferencias columnas | Reversas baseline/candidato | PASS |',
           '|---|---|---:|---:|---:|---:|---|---|']
    for c in checks:
        lines.append(f"| {c['case']} | {c['candidate']} | {c['candidate_count']} | {c['SOLO_BASELINE']} | {c['SOLO_CANDIDATO']} | {c['DIFERENCIAS_COLUMNAS']} | {len(c['baseline_reversals'])}/{len(c['candidate_reversals'])} | {c['pass']} |")
    lines+=['','## Benchmark (sin XML)','',
            '| Caso | Primera s | Segunda s | Tercera s | Min / mediana / max s | CPU ms 1/2/3 | SQL elapsed ms 1/2/3 | Reads 1/2/3 | Baseline mediana s | Speedup | Reducción IO |',
            '|---|---:|---:|---:|---|---|---|---|---:|---:|---:|']
    summaries=[]
    for label,ms in groups.items():
        times=[m['client_seconds'] for m in ms]
        params=ms[0]['params'];days=(__import__('datetime').date.fromisoformat(params['hasta'])-__import__('datetime').date.fromisoformat(params['desde'])).days+1
        baseline=next(x for x in old if x['label']==f"timeline_{days}d_{'ox_p1' if params['pad_id']==1 else 'sulf_p7'}")
        reads=[sum(i['logical_reads'] for i in m['io']) for m in ms]
        speedup=baseline['median']/median(times);reduction=1-median(reads)/median(baseline['logical_reads'])
        summaries.append({'case':label,'seconds':times,'min':min(times),'median':median(times),'max':max(times),
                          'logical_reads':reads,'baseline_median':baseline['median'],'baseline_reads':median(baseline['logical_reads']),
                          'speedup':speedup,'io_reduction_pct':100*reduction})
        cpu='/'.join(str(m['time_messages'][-1]['cpu_ms']) for m in ms)
        elapsed='/'.join(str(m['time_messages'][-1]['elapsed_ms']) for m in ms)
        lines.append(f"| {label} | {' | '.join(f'{t:.4f}' for t in times)} | {min(times):.4f} / {median(times):.4f} / {max(times):.4f} | {cpu} | {elapsed} | {'/'.join(map(str,reads))} | {baseline['median']:.4f} | {speedup:.2f}x | {100*reduction:.2f}% |")
    (P/'resumen.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
    lines+=['','El speedup usa las medianas runtime de la auditoría previa (12 columnas); el candidato devuelve24. Las referencias actuales por caso se conservan en functional_timings.json. No es comparación aleatorizada simultánea ni SLA de PROD.', '',
            'Las capturas de planes son ejecuciones adicionales; no entran en estas medianas. STATISTICS IO mide accesos a páginas, no páginas únicas. Primera observada no significa caché fría.']
    (P/'resultados.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    plans=[plan(f) for f in sorted((P/'plans').glob('*.sqlplan'))]
    (P/'planes_analizados.json').write_text(json.dumps(plans,indent=2),encoding='utf-8')
    lines=['# Comparación de planes reales','',
           'XML íntegro en plans/. Contadores acumulados; no sumar tiempos inclusivos de padres e hijos.', '',
           '## Referencia baseline runtime (auditoría previa)', '',
           'PlanHash 0x75F647FB677DE496; DOP1; costo9,29993. Nested Loops2 produce6.120 filas y Filter1 devuelve102. '
           'Scans históricos OX ejecutan3.264 veces y SULF2.856 veces; Table Spool15 tiene102 rebinds,0 rewinds. '
           'A102 días:22.166.901 lecturas,42 Nested Loops,6 Hash Match,21 Sort,19 Clustered Index Scan. '
           'Grant11.600KB,usado1.936KB. Sin spills; advertencias optimizer TimeOut/PlanAffectingConvert. '
           'XML en ../diagnostico_performance/plans/. La referencia proyecta12 campos; candidatos24.', '']
    for p in plans:
        lines+=['## '+p['file'],'']
        for s in p['statements']:
            lines+=['```json',json.dumps({k:s[k] for k in ('attributes','query_plan','operator_counts','MemoryGrantInfo','QueryTimeStats','Warnings','WaitStats','MissingIndexes')},indent=2),'```','',
                    '| Nodo | Operador | Est filas/ejec | Filas reales total | Ejecuciones | Real/ejec | Logical reads | Objeto |',
                    '|---:|---|---:|---:|---:|---:|---:|---|']
            for r in s['operators']:
                if r['objects'] or int(r['NodeId'])<8:
                    lines.append(f"| {r['NodeId']} | {r['PhysicalOp']} | {r.get('EstimateRows')} | {r['ActualRows']:g} | {r['ActualExecutions']:g} | {r['actual_rows_per_execution']} | {r['ActualLogicalReads']:g} | {','.join(o.get('Table','') for o in r['objects'])} |")
    (P/'plan_comparison.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__': run()
