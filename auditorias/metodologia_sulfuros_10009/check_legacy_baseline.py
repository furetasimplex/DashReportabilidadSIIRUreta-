"""Compare verified Aug 23 anchor + stored flow increments to prior baseline."""
from pathlib import Path
from collections import defaultdict
import copy,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sulfide_reconciliation import reconcile_sulfides
P=Path(__file__).resolve().parent
meta=json.loads((P/'profile_sources_metadata.json').read_text(encoding='utf8'))
daily=json.loads((P/'campaign11_daily_stacked_cu.json').read_text(encoding='utf8'))
snapshot=json.loads((P/'case10009_select_snapshot.json').read_text(encoding='utf8'))
fixture=json.loads((P.parents[1]/'test_fixtures/caso10009_sulfuros_net_inputs.json').read_text(encoding='utf8'))
official={r['parcela']:r for r in meta['august23'] if r['Campana']==11 and r['recuperacion'] is not None}
groups=defaultdict(list)
for row in daily:
    if row['cu_t'] is not None:groups[row['pile']].append(row)
flow=defaultdict(dict)
for row in snapshot['official']:
    if row['pad']=='SULFUROS' and row['case_id']==8 and '2026-08-24'<=str(row['date'])<='2026-08-31':
        flow[row['pile']][str(row['date'])]=row
rows=copy.deepcopy(fixture['rows']); details=[]
for base in rows:
    if base['date']!='2026-08-31': continue
    n=int(base['pile'][1:]); r=official.get(n); fs=flow.get(base['pile'],{})
    if r is None or len(fs)!=8 or n not in groups:
        details.append({'pile':base['pile'],'status':'missing_anchor_or_history'});continue
    cu23=sum(x['cu_t'] for x in groups[n] if x['date']<='2026-08-23')
    cu31=sum(x['cu_t'] for x in groups[n] if x['date']<='2026-08-31')
    if cu23<=0 or cu31<=0:
        details.append({'pile':base['pile'],'status':'missing_stacked_copper'});continue
    inc=0.0
    incomplete=False
    for f in fs.values():
        if f['q_drenaje_m3h'] is None or f['q_riego_m3h'] is None:
            incomplete=True;break
        if ((f['q_drenaje_m3h'] and f['cu_drenaje_gL'] is None) or
            (f['q_riego_m3h'] and f['cu_riego_gL'] is None)):
            incomplete=True;break
        inc+=.024*(f['q_drenaje_m3h']*(f['cu_drenaje_gL'] or 0)-f['q_riego_m3h']*(f['cu_riego_gL'] or 0))
    if incomplete:
        details.append({'pile':base['pile'],'status':'missing_flow_or_concentration'});continue
    val=100*(r['recuperacion']*cu23/100+inc)/cu31
    details.append({'pile':base['pile'],'status':'reconstructed', 'pct':val,
                    'prior_primary_pct':base['official_pct'], 'difference_pct':val-base['official_pct'],
                    'cu23':cu23,'cu31':cu31})
    base['official_pct']=val
try:
    result,audit=reconcile_sulfides(rows,'2026-09-01','2026-09-07',fixture['target_net_t'])
    summary={'reconstructed':sum(r['status']=='reconstructed' for r in details),
             'unresolved':[r for r in details if r['status']!='reconstructed'],
             'lambda':audit['lambda'], 'target_t':audit['target_net_t'],
             'residual_t':audit['net_residual_t']}
except Exception as exc:
    summary={'reconstructed':sum(r['status']=='reconstructed' for r in details),
             'unresolved':[r for r in details if r['status']!='reconstructed'],
             'error_type':type(exc).__name__,'reason':str(exc)}
(P/'legacy_baseline_diagnostic.json').write_text(json.dumps({'summary':summary,'details':details},indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
