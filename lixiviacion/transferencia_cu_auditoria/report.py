"""Consolida evidencia local; no consulta SQL."""
import hashlib
import json
from decimal import Decimal
from pathlib import Path
from .audit import P, save


def run():
    r=json.loads((P/'resultados.json').read_text(encoding='utf-8'))
    references=[]
    for p in Path('.').rglob('*'):
        if not p.is_file() or p.suffix.lower() not in ('.py','.json','.md','.csv','.sql','.txt'): continue
        if any(x in p.parts for x in ('.git','venv','node_modules','__pycache__','transferencia_cu_auditoria')): continue
        try: content=p.read_text(encoding='utf-8-sig')
        except (UnicodeError,OSError): continue
        matches=[{'line':i,'text':line[:800]} for i,line in enumerate(content.splitlines(),1)
                 if any(n in line for n in ('30136.22181133','30.136,221811330','6801.723817085','23334.497994245'))]
        if matches: references.append({'file':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'matches':matches})
    baseline={'references':references,'level':'D enriquecido: total global y totales por PAD; no serie por fecha',
              'full_rows':False,'date_pad_series':False,'date_series':False,'sql_definition_bound_to_baseline':False,
              'v2_hash_bound_to_baseline':False,'reconstruct_total_from_PAD':True,
              'later_evidence':'diagnostico_auditoria/resultados.json (05-10-2026) ya suma 30395.260628596; contiene 7 ejemplos, no snapshot completo del baseline.',
              'excluded':'Catálogos SQL, hashes de filas/figuras y conteos dias_pad no son datasets históricos reconstruibles. Candidato V2 local no ejecutado no acredita definición instalada.'}
    save('baseline_evidence.json',baseline)
    delta=Decimal(r['delta_global'])
    breakdown={'global_delta_t':str(delta),'pad_contributions':r['pad_comparison'],
               'pad_allocation_explained_pct':'100','causal_explanation_proven_pct':'0',
               'causal_unresolved_t':str(delta),'flow_effect':None,'drainage_effect':None,'raffinate_effect':None,'coverage_effect':None,
               'reason':'No hay observaciones del baseline por fecha/parcela ni definiciones vinculadas inequívocamente a su ejecución. No se atribuye el delta a datos o SQL.',
               'rounding_current':r['rounding_live_only']}
    save('cause_breakdown.json',breakdown)
    # Los 7 ejemplos de la auditoría posterior se comparan separadamente: no son el baseline solicitado.
    old=json.loads(Path('lixiviacion/diagnostico_auditoria/resultados.json').read_text(encoding='utf-8'))
    live=json.loads((P/'live_snapshot.json').read_text(encoding='utf-8'))
    index={(x['fecha'],x['pad_id'],x['parcela_id']):x for x in live}
    fields=['flujo_m3_d','cu_drenaje_gl','cu_refino_gl','delta_cu_gl','transferencia_cu_t_d']
    checks=[]
    for x in old['cases']:
        y=index[(x['fecha'],x['pad_id'],x['parcela_id'])]
        equal=all((x[c] is None and y[c] is None) or (x[c] is not None and y[c] is not None and Decimal(x[c])==Decimal(y[c])) for c in fields)
        checks.append({'fecha':x['fecha'],'pad_id':x['pad_id'],'parcela_id':x['parcela_id'],'equal':equal})
    save('later_sample_comparison.json',checks)
    protected=json.loads((P/'protected_hashes.json').read_text(encoding='utf-8'))
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in protected.items())
    print('Historical references:',len(references),'Later seven sample equal:',all(x['equal'] for x in checks))
    print('PAD shares:',[(x['pad_id'],str(Decimal(x['delta_transferencia'])/delta*100)) for x in r['pad_comparison']])


if __name__=='__main__':run()
