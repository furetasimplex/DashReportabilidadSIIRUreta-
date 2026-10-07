"""Prepare a minimal ALTER and exact rollback from the live DEV definition."""
import json
import re
import difflib
from pathlib import Path

BASE=Path(__file__).resolve().parent
snapshot=json.loads((BASE/'before.json').read_text(encoding='utf-8'))
old=next(r['definition'] for r in snapshot['results']['definitions'] if r['name']=='sp_mantiene_datos_conciliados_emision_test')
needle='aj.Chancado_TMS_Reporte AS Chancado_TMS_Real,'
replacement='''CASE
                WHEN aj.Apilado_TMS_Reporte = 0
                 AND aj.Sal_TMH_Dia = 0
                 AND aj.SRR_TMS_Dia = 0
                    THEN 0
                ELSE aj.Chancado_TMS_Reporte
            END AS Chancado_TMS_Real,'''
if old.count(needle)!=1: raise RuntimeError('Expected final assignment absent or ambiguous')
def alter(sql):
    sql,n=re.subn(r'\bCREATE\s+PROCEDURE\s+\[inventar_SpcHidr\]\.\[sp_mantiene_datos_conciliados_emision_test\]',
                  'ALTER PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_emision_test]',sql,count=1,flags=re.I)
    if n!=1: raise RuntimeError('CREATE PROCEDURE header absent')
    return sql.rstrip()+'\n'
(BASE/'definicion_before.sql').write_text(old.rstrip()+'\n',encoding='utf-8')
(BASE/'alter_sp_mantiene_datos_conciliados_emision_test.sql').write_text(alter(old.replace(needle,replacement)),encoding='utf-8')
(BASE/'rollback.sql').write_text(alter(old),encoding='utf-8')
(BASE/'diff_sql.patch').write_text(''.join(difflib.unified_diff(
    alter(old).splitlines(keepends=True),alter(old.replace(needle,replacement)).splitlines(keepends=True),
    fromfile='rollback.sql',tofile='alter_sp_mantiene_datos_conciliados_emision_test.sql')),
    encoding='utf-8')
print('Prepared one-assignment ALTER and exact rollback')
