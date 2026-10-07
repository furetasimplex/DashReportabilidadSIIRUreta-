"""Build offline, read-only audit artifacts from the captured DEV snapshot."""
import csv
import json
from collections import defaultdict, Counter
from decimal import Decimal
from pathlib import Path

BASE = Path(__file__).resolve().parent
snap = json.loads((BASE / 'snapshot.json').read_text(encoding='utf-8'))
d = snap['results']
Q = Decimal('0.000001')
EPS = Decimal('0.001')
def dec(x): return Decimal(str(x or 0))
def fmt(x): return str(x.quantize(Q)) if x is not None else ''
def key(r): return (int(r['modulo_id']), r['fecha'][:10])
def write(name, rows, fields):
    with (BASE / name).open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader(); w.writerows(rows)

modules = {int(r['modulo_id']): r for r in d['modules']}
source = defaultdict(list)
for r in d['source']:
    if int(r['modulo_id']) in modules: source[int(r['modulo_id'])].append(r)
src_keys = Counter(key(r) for r in d['source'])
dst_keys = Counter(key(r) for r in d['reclamo'])
view_keys = Counter(key(r) for r in d['acumulado'])
if any(v != 1 for c in (src_keys,dst_keys,view_keys) for v in c.values()):
    raise RuntimeError('Duplicate (module,date) key; resolve before comparing')
dst = {key(r): r for r in d['reclamo']}
view = {key(r): r for r in d['acumulado']}
detail=[]; summary=[]; sep30=[]; totals=defaultdict(Decimal); flags=defaultdict(set)
for mid, rows in sorted(source.items()):
    rows.sort(key=lambda r: r['fecha'])
    prev=None; incons=Decimal(0); carry=Decimal(0); sync=Decimal(0); official=Decimal(0)
    n_incon=n_sync=0
    for i,r in enumerate(rows,1):
        k=key(r); rr=dst.get(k); vv=view.get(k)
        daily=dec(r['volumen_diario_m3']); actual=dec(r['volumen_final_reclamado'])
        delta=actual-prev if prev is not None else None
        delta_diff=delta-daily if delta is not None else None
        start=actual-daily if i==1 else None
        thm=dec(rr['m3_thm']) if rr else Decimal(0)
        off=dec(vv['m3_camiones_dia']) if vv else Decimal(0)
        sync_diff=daily-thm; official_diff=thm-off
        if i==1: carry=start
        else: incons+=delta_diff
        sync+=sync_diff; official+=official_diff
        if i==1 and abs(start)>EPS:
            cls='ARRANQUE_CON_ACUMULADO'; flags[mid].add(cls)
        elif i>1 and abs(delta_diff)>EPS:
            cls='DELTA_INTERNO_INCONSISTENTE'; flags[mid].add(cls); n_incon+=1
        elif abs(sync_diff)>EPS:
            cls='FUENTE_OK_NO_SINCRONIZADA'; flags[mid].add(cls)
        else: cls='OK'
        if abs(sync_diff)>EPS: n_sync+=1
        record=dict(fecha=k[1], campaña_id=10, modulo_id=mid,
            modulo_numero=modules[mid]['modulo_numero'],rn=i,
            volumen_diario_fuente=fmt(daily),acumulado_anterior=fmt(prev),
            acumulado_actual=fmt(actual),delta_acumulado=fmt(delta),
            diferencia_delta=fmt(delta_diff),arrastre_inicial=fmt(start),
            m3_thm_reclamo=fmt(thm) if rr else '',
            diferencia_vs_reclamo=fmt(sync_diff),clasificacion=cls,
            m3_oficial=fmt(off) if vv else '',estado_reclamo=rr['estado'] if rr else '',
            diferencia_thm_vs_oficial=fmt(official_diff))
        if i==1 or (delta_diff is not None and abs(delta_diff)>EPS) or abs(sync_diff)>EPS or abs(official_diff)>EPS:
            detail.append(record)
        if k[1]=='2026-09-30': sep30.append(record)
        prev=actual
    last=rows[-1]; last_view=view.get(key(last))
    system=dec(last_view['m3_camiones_acum']) if last_view else Decimal(0)
    gap=prev-system
    if abs(gap-(carry+incons+sync+official))>Decimal('0.0001'):
        raise RuntimeError(f'Decomposition fails for {mid}: {gap} vs {carry+incons+sync+official}')
    totals['arrastre']+=carry; totals['delta_interno']+=incons
    totals['no_sincronizado']+=sync; totals['thm_vs_oficial']+=official
    totals['brecha']+=gap
    summary.append(dict(modulo_id=mid,modulo_numero=modules[mid]['modulo_numero'],
        primera_fecha=rows[0]['fecha'][:10],ultima_fecha=last['fecha'][:10],
        arrastre_inicial=fmt(carry),cantidad_delta_inconsistente=n_incon,
        suma_diferencias_delta=fmt(incons),cantidad_no_sincronizadas=n_sync,
        suma_diferencias_vs_reclamo=fmt(sync),diferencia_thm_vs_oficial=fmt(official),
        acumulado_final_fuente=fmt(prev),acumulado_final_sistema=fmt(system),
        diferencia_final_fuente_vs_sistema=fmt(gap),clasificaciones='|'.join(sorted(flags[mid])) or 'OK'))

detail_fields=['fecha','campaña_id','modulo_id','modulo_numero','rn','volumen_diario_fuente','acumulado_anterior','acumulado_actual','delta_acumulado','diferencia_delta','arrastre_inicial','m3_thm_reclamo','diferencia_vs_reclamo','clasificacion','m3_oficial','estado_reclamo','diferencia_thm_vs_oficial']
summary_fields=['modulo_id','modulo_numero','primera_fecha','ultima_fecha','arrastre_inicial','cantidad_delta_inconsistente','suma_diferencias_delta','cantidad_no_sincronizadas','suma_diferencias_vs_reclamo','diferencia_thm_vs_oficial','acumulado_final_fuente','acumulado_final_sistema','diferencia_final_fuente_vs_sistema','clasificaciones']
write('detalle_diferencias.csv',detail,detail_fields)
write('resumen_modulos.csv',summary,summary_fields)
write('comparacion_30_09.csv',sep30,detail_fields)
report={'identity':snap['identity'],'counts':{'frozen':len(modules),'with_source':len(source),'source_rows':len(d['source']),'reclamo_rows':len(d['reclamo']),'view_rows':len(d['acumulado']),'detail_rows':len(detail),'sep30_rows':len(sep30),'sep30_unsynced':sum(abs(dec(r['diferencia_vs_reclamo']))>EPS for r in sep30)},'modules_by_flag':{name:sum(name in v for v in flags.values()) for name in ('ARRANQUE_CON_ACUMULADO','DELTA_INTERNO_INCONSISTENTE','FUENTE_OK_NO_SINCRONIZADA')},'totals':{k:fmt(v) for k,v in totals.items()},'sep30_unsynced_rows':[r for r in sep30 if abs(dec(r['diferencia_vs_reclamo']))>EPS],'module_summaries':summary}
(BASE/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ('counts','modules_by_flag','totals','sep30_unsynced_rows')},ensure_ascii=False,indent=2))
