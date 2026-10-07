"""Read-only post-deploy validation for the minimal cuadratura change."""
import json
import os
import re
import sys
from pathlib import Path
from sqlalchemy import text

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine

BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr':
    raise RuntimeError('DEV database required')
queries={
    'identity': 'SELECT @@SERVERNAME AS server_name,DB_NAME() AS database_name,SYSDATETIME() AS observed_at',
    'latest_vs_max': '''WITH ranked AS (SELECT campaña_id,modulo_id,fecha,m3_camiones_acum,
          MAX(m3_camiones_acum) OVER(PARTITION BY campaña_id,modulo_id) AS max_historico,
          ROW_NUMBER() OVER(PARTITION BY campaña_id,modulo_id ORDER BY fecha DESC) AS rn
          FROM reclamo.v_camiones_acumulado)
          SELECT r.*,q.modulo_numero,q.m3_camiones_sistema,q.m3_camiones_previo,q.m3_camiones_total,
                 q.m3_extraido_total,q.porcentaje_extraido,q.m3_saldo_disponible,q.m3_totales
          FROM ranked r JOIN reclamo.v_cuadratura_modulo q ON q.campaña_id=r.campaña_id AND q.modulo_id=r.modulo_id
          WHERE r.rn=1 ORDER BY r.campaña_id,r.modulo_id''',
    'duplicate_keys': 'SELECT campaña_id,modulo_id,COUNT(*) n FROM reclamo.v_cuadratura_modulo GROUP BY campaña_id,modulo_id HAVING COUNT(*)>1',
    'definition': "SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cuadratura_modulo')) AS definition",
    'negative_rows': 'SELECT fecha,campaña_id,modulo_id,m3_thm,tms_thm FROM reclamo.camiones_reclamo WHERE m3_thm<0 OR tms_thm<0 ORDER BY fecha,modulo_id',
    'accum_references': "SELECT o.name,m.definition FROM sys.objects o JOIN sys.sql_modules m ON m.object_id=o.object_id WHERE SCHEMA_NAME(o.schema_id)='reclamo' AND (m.definition LIKE '%m3_camiones_acum%' OR m.definition LIKE '%tms_camiones_acum%') ORDER BY o.name",
    'etl_source_columns': "SELECT c.name FROM sys.columns c WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario') ORDER BY c.column_id",
    'etl_source_case': "SELECT fecha,campaña_id,modulo_id,campaña,modulo,volumen_diario_m3,volumen_final_reclamado FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario WHERE fecha BETWEEN '2026-10-01' AND '2026-10-04' AND campaña_id=10 AND modulo_id IN (81,87) ORDER BY fecha,modulo_id",
}
with get_engine().connect() as conn:
    data={k:[dict(r) for r in conn.execute(text(q)).mappings()] for k,q in queries.items()}
if data['identity'][0]['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong database')
if data['duplicate_keys']: raise RuntimeError('Duplicate keys')
if 'SELECT TOP (1) c.m3_camiones_acum' not in data['definition'][0]['definition']: raise RuntimeError('Definition mismatch')
bad=[r for r in data['latest_vs_max'] if abs(float(r['m3_camiones_sistema'])-float(r['m3_camiones_acum']))>1e-6
     or abs(float(r['m3_camiones_total'])-float(r['m3_camiones_previo']+r['m3_camiones_acum']))>1e-6]
if bad: raise RuntimeError(f'Unexpected current accumulation: {bad}')
pattern=re.compile(r'\bMAX\s*\(\s*(?:\w+\s*\.\s*)?(?:m3_camiones_acum|tms_camiones_acum)\s*\)',re.I)
data['historical_max_findings']=[{'name':r['name'],'matches':pattern.findall(r['definition'])}
                                 for r in data['accum_references'] if pattern.search(r['definition'])]
(BASE/'post_validation.json').write_text(json.dumps(data,ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print('PASS',data['identity'][0],'latest_modules',len(data['latest_vs_max']),
      'negative_rows',len(data['negative_rows']),'duplicate_keys',len(data['duplicate_keys']))
