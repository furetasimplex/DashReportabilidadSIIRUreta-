"""Valida el harness y evidencias locales; no conecta a SQL."""
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from lixiviacion import db
from .run import compare,reversals
from .build import SOURCE

P=Path(__file__).parent


def run():
    row={'fecha':date(2026,9,10),'pad_id':1,'parcela_id':1,'valor':None}
    assert compare([row],[dict(row)])['pass']
    for value in (0,''):
        other=dict(row,valor=value)
        check=compare([row],[other])
        assert not check['pass'] and check['DIFERENCIAS_COLUMNAS']==1
        assert check['SOLO_BASELINE']==check['SOLO_CANDIDATO']==1
    assert not compare([row],[row,row])['pass']
    assert not compare([row],[])['pass']
    seq=[dict(row,campana_id=1,estado_operacional='REPOSO_PRE_RECLAMO'),
         dict(row,fecha=date(2026,9,11),campana_id=1,estado_operacional='RIEGO')]
    assert len(reversals(seq))==1
    seq[1]['campana_id']=2
    assert not reversals(seq)
    for name in ('candidate_generic','candidate_ox','candidate_sulf'):
        sql=(P/(name+'.sql')).read_text(encoding='utf-8')
        clean=re.sub(r'--[^\n]*','',sql)
        assert not re.search(r'\b(CREATE|ALTER|DROP|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|EXEC|DBCC)\b',clean,re.I)
        assert 'fn_estado_operacional_parcela_diario' not in clean
        assert 'INTO ' not in clean.upper()
        assert 'WITHIN GROUP' not in clean.upper()
        if name=='candidate_ox': assert 'sulfuro' not in clean
        if name=='candidate_sulf': assert 'oxido' not in clean
        source=SOURCE.read_text(encoding='utf-8')
        case='CASE'+source.split('    estado_modulo AS')[1].split('            CASE',1)[1].split(' AS estado_modulo',1)[0]
        assert case.replace('@fecha','b.fecha') in sql
    assert (P/'baseline_runtime.sql').read_text(encoding='utf-8')==db.OP_TIMELINE_SQL
    for path in P.glob('runtime_before_*.json'):
        before=json.loads(path.read_text(encoding='utf-8'))
        assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in before.items())
    result={'harness_null_safe':True,'duplicate_detection':True,'terminal_reversals':True,
            'select_only_candidates':True,'literal_state_case':True,'runtime_unchanged':True}
    (P/'validacion_local.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS',result)


if __name__=='__main__': run()
