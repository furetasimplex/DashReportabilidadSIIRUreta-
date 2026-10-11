"""Preparación e integración controlada local; nunca ejecuta SQL."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
from lixiviacion import db
from lixiviacion.diagnostico_performance.audit import hashes

P=Path(__file__).parent
DB=P.parent/'db.py'


def assignment(source):
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='OP_TIMELINE_SQL' for t in n.targets))
    lines=source.splitlines(keepends=True)
    return sum(map(len,lines[:node.lineno-1])),sum(map(len,lines[:node.end_lineno]))


def output_name(expr):
    alias=re.search(r'\s+AS\s+(\w+)\s*$',expr,re.I)
    return alias[1] if alias else expr.strip().rsplit('.',1)[-1]


def expressions(select):
    result=[];start=0;depth=0;quoted=False;i=0
    while i<len(select):
        c=select[i]
        if c=="'":
            if quoted and i+1<len(select) and select[i+1]=="'": i+=2;continue
            quoted=not quoted
        elif not quoted:
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif c==',' and depth==0: result.append(select[start:i].strip());start=i+1
        i+=1
    result.append(select[start:].strip())
    return result


def prepare():
    P.mkdir(exist_ok=True)
    assert not (P/'db_before.py').exists(),'Backup existente; no sobrescribir'
    source=DB.read_text(encoding='utf-8');a,b=assignment(source)
    (P/'db_before.py').write_bytes(DB.read_bytes())
    (P/'OP_TIMELINE_SQL_before.sql').write_text(db.OP_TIMELINE_SQL,encoding='utf-8')
    (P/'assignment_before.txt').write_text(source[a:b],encoding='utf-8')
    (P/'runtime_before.json').write_text(json.dumps(hashes(),indent=2),encoding='utf-8')
    projection=re.search(r'\)\s*SELECT\s+(.*?)\s+FROM fechas d',db.OP_TIMELINE_SQL,re.S)[1]
    fields=[output_name(x) for x in expressions(projection)]
    assert tuple(fields)==db.OP_FIELDS and len(fields)==12
    candidate=(P.parent/'diagnostico_performance_candidate'/'candidate_generic.sql').read_text(encoding='utf-8')
    start=candidate.rindex('\nSELECT d.fecha,')+len('\nSELECT ')
    end=candidate.index('\nFROM dias d',start)
    projected={output_name(expr):expr for expr in expressions(candidate[start:end])}
    runtime=candidate[:start]+',\n    '.join(projected[f] for f in fields)+candidate[end:]
    runtime=runtime.replace('-- PROTOTIPO DEV READ ONLY. No desplegar ni integrar al runtime.',
                            '-- Timeline DEV: candidato genérico validado, contrato runtime original de 12 columnas.')
    (P/'candidate_runtime_12.sql').write_text(runtime,encoding='utf-8')
    contract={'db_before_sha256':hashlib.sha256(DB.read_bytes()).hexdigest(),
              'before_projection':expressions(projection),'fields':fields,
              'candidate_projection':[projected[f] for f in fields],
              'parameters':sorted(set(re.findall(r':(\w+)',db.OP_TIMELINE_SQL))),
              'candidate_sha256':hashlib.sha256(runtime.encode()).hexdigest()}
    (P/'contract.json').write_text(json.dumps(contract,indent=2,ensure_ascii=False),encoding='utf-8')


def edit(rollback=False):
    source=DB.read_text(encoding='utf-8');a,b=assignment(source)
    candidate=(P/'candidate_runtime_12.sql').read_text(encoding='utf-8')
    old=(P/'OP_TIMELINE_SQL_before.sql').read_text(encoding='utf-8')
    if rollback:
        assert db.OP_TIMELINE_SQL==candidate,'El runtime cambió; no sobrescribir otros cambios'
        replacement=(P/'assignment_before.txt').read_text(encoding='utf-8')
    else:
        comparisons=json.loads((P/'comparacion.json').read_text(encoding='utf-8'))
        assert len(comparisons)==37 and all(c['pass'] for c in comparisons)
        assert db.OP_TIMELINE_SQL==old
        assert hashlib.sha256(DB.read_bytes()).hexdigest()==json.loads((P/'contract.json').read_text())['db_before_sha256']
        replacement="OP_TIMELINE_SQL = '''"+candidate+"'''\n"
    updated=source[:a]+replacement+source[b:]
    DB.write_text(updated,encoding='utf-8',newline='')
    diff=''.join(difflib.unified_diff(source.splitlines(keepends=True),updated.splitlines(keepends=True),
                                    fromfile='lixiviacion/db.py (antes)',tofile='lixiviacion/db.py (después)'))
    (P/('rollback.diff' if rollback else 'runtime.diff')).write_text(diff,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','integrate','rollback'])
    action=parser.parse_args().action
    prepare() if action=='prepare' else edit(action=='rollback')
