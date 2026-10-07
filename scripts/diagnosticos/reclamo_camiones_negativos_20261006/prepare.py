"""Prepare the minimal ALTER and exact rollback from the read-only DEV snapshot."""
import json
import re
from pathlib import Path

BASE=Path(__file__).resolve().parent
snapshot=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
definition=next(r['definition'] for r in snapshot['results']['definitions'] if r['name']=='v_cuadratura_modulo')
needle="""            SELECT MAX(c.m3_camiones_acum)
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = mb.[campaña_id] AND c.modulo_id = mb.modulo_id"""
replacement="""            SELECT TOP (1) c.m3_camiones_acum
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = mb.[campaña_id] AND c.modulo_id = mb.modulo_id
            ORDER BY c.fecha DESC"""
if definition.count(needle)!=1:
    raise RuntimeError('Expected exact MAX expression absent or ambiguous')
def alter(sql):
    changed,n=re.subn(r'\bCREATE\s+VIEW\s+\[reclamo\]\.\[v_cuadratura_modulo\]',
                      'ALTER VIEW [reclamo].[v_cuadratura_modulo]',sql,count=1,flags=re.I)
    if n!=1: raise RuntimeError('CREATE VIEW header absent')
    return changed.rstrip()+'\n'
(BASE/'definicion_before.sql').write_text(definition.rstrip()+'\n',encoding='utf-8')
(BASE/'alter_v_cuadratura_modulo.sql').write_text(alter(definition.replace(needle,replacement)),encoding='utf-8')
(BASE/'rollback.sql').write_text(alter(definition),encoding='utf-8')
print('Prepared exact source definition, one-expression ALTER, and rollback')
