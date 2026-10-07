"""Prepare shared Chancado reportable expression before downstream SRR law."""
import difflib
import re
from pathlib import Path

BASE=Path(__file__).resolve().parent
old=(BASE/'dependency_before.sql').read_text(encoding='utf-8')
gate='''CASE
                WHEN aj.Apilado_TMS_Reporte = 0
                 AND aj.Sal_TMH_Dia = 0
                 AND aj.SRR_TMS_Dia = 0
                    THEN 0
                ELSE aj.Chancado_TMS_Reporte
            END AS Chancado_TMS_Real,'''
join='LEFT JOIN [inventar_SpcHidr].[v_ajuste_camiones_emision_test] aj ON aj.Fecha = f.Fecha'
if old.count(gate)!=1 or old.count(join)!=1:
    raise RuntimeError('Expected current gate or official source JOIN absent')
new=old.replace(gate,'ch.Chancado_TMS_Real,')
new=new.replace('WHEN aj.Chancado_TMS_Reporte IS NULL THEN NULL',
                'WHEN ch.Chancado_TMS_Real IS NULL THEN NULL')
new=new.replace('lms.Ley_CuT_Mina_Stock * aj.Chancado_TMS_Reporte',
                'lms.Ley_CuT_Mina_Stock * ch.Chancado_TMS_Real')
new=new.replace(join,join+'''
        CROSS APPLY
        (
            SELECT CASE
                WHEN aj.Apilado_TMS_Reporte = 0
                 AND aj.Sal_TMH_Dia = 0
                 AND aj.SRR_TMS_Dia = 0
                    THEN 0
                ELSE aj.Chancado_TMS_Reporte
            END AS Chancado_TMS_Real
        ) ch''')
if new.count('aj.Chancado_TMS_Reporte')!=1 or new.count('ch.Chancado_TMS_Real')!=3:
    raise RuntimeError('Unmodified downstream Chancado reference')
def alter(value):
    value,n=re.subn(r'\bCREATE\s+PROCEDURE\s+\[inventar_SpcHidr\]\.\[sp_mantiene_datos_conciliados_emision_test\]',
                    'ALTER PROCEDURE [inventar_SpcHidr].[sp_mantiene_datos_conciliados_emision_test]',value,count=1,flags=re.I)
    if n!=1: raise RuntimeError('Unexpected procedure header')
    return value.rstrip()+'\n'
new=alter(new)
rollback=alter(old)
(BASE/'alter_dependency_srr.sql').write_text(new,encoding='utf-8')
(BASE/'rollback_dependency_srr.sql').write_text(rollback,encoding='utf-8')
(BASE/'diff_dependency_srr.patch').write_text(''.join(difflib.unified_diff(
    rollback.splitlines(keepends=True),new.splitlines(keepends=True),
    fromfile='rollback_dependency_srr.sql',tofile='alter_dependency_srr.sql')),encoding='utf-8')
print('Prepared shared gate; SRR input source is aj.SRR_TMS_Dia')
