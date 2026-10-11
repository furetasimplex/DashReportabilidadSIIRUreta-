"""Prepare a minimal ALTER VIEW and rollback from the captured live definition."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
data=json.loads((BASE/'snapshot_before.json').read_text(encoding='utf-8'))
objects=data['objects']
def norm(s): return s.replace('\r\n','\n').replace('\r','\n').strip()+'\n'
before=norm(objects['v_cv25_diario']['metadata']['definition'])
if before.count('CREATE VIEW [reclamo].[v_cv25_diario]')!=1:
    raise RuntimeError('Unexpected live CV25 definition')
all_before=[]
for name in ('v_cv25_diario','v_preliminar_cv25','v_reclamo_diario'):
    all_before.append('-- reclamo.'+name+'\n'+norm(objects[name]['metadata']['definition']))
(BASE/'definicion_before.sql').write_text('\nGO\n\n'.join(all_before),encoding='utf-8')
rollback=before.replace('CREATE VIEW [reclamo].[v_cv25_diario]',
                        'ALTER VIEW [reclamo].[v_cv25_diario]',1)
(BASE/'rollback.sql').write_text(rollback,encoding='utf-8')

new=rollback
old_case='''        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE'''
def replacement(roto):
    return f'''        WHEN COALESCE(hr.horas_r{roto}, 0) = 0
         AND COALESCE(cv.horas_con_dato_r{roto}, 0) > 0
            THEN 0

        WHEN COALESCE(hr.horas_r{roto}, 0) = 0
         AND COALESCE(cv.horas_con_dato_r{roto}, 0) = 0
            THEN NULL

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE'''
if new.count(old_case)!=2: raise RuntimeError('Unexpected TMS CASE count')
parts=new.split(old_case)
new=parts[0]+replacement(1)+parts[1]+replacement(2)+parts[2]
old_flag='''        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE' '''.rstrip()
new_flag='''        WHEN COALESCE(hr.horas_total, 0) = 0
         AND (
             (COALESCE(hr.horas_r1, 0) = 0 AND COALESCE(cv.horas_con_dato_r1, 0) > 0)
             OR (COALESCE(hr.horas_r2, 0) = 0 AND COALESCE(cv.horas_con_dato_r2, 0) > 0)
         )
            THEN 'CERO_OPERACION_CONFIRMADO'

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE' '''.rstrip()
if new.count(old_flag)!=1: raise RuntimeError('Unexpected flag CASE')
new=new.replace(old_flag,new_flag,1)
old_comment='''    -- Si CV025 > 0 pero no hay horas:
    -- no podemos repartir el tonelaje.'''
new_comment='''    -- Con cobertura de corriente y cero horas: cero confirmado.
    -- Sin cobertura y cero horas: no inferir cero.'''
if new.count(old_comment)!=1: raise RuntimeError('Unexpected comment')
new=new.replace(old_comment,new_comment,1)
(BASE/'alter_v_cv25_diario.sql').write_text(new,encoding='utf-8')
print('prepared',len(before),len(new))
