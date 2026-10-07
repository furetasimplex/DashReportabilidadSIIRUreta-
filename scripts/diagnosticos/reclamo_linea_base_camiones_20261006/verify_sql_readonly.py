"""Independent SQL confirmation of the exact baseline expression for all 26 modules."""
import json
import os
import sys
from pathlib import Path
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV database required')
sql=text('''WITH corte AS (
    SELECT TRY_CAST(valor AS date) AS fecha
    FROM reclamo.configuracion WHERE clave='FECHA_CORTE_SISTEMA'
), previo AS (
    SELECT mc.campaña_id,mc.modulo_id,mc.modulo_numero,mc.m3_camiones_previo,
           c.fecha AS fecha_corte,
           COALESCE((SELECT SUM(COALESCE(src.volumen_diario_m3,0))
                     FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario src
                     WHERE src.campaña_id=mc.campaña_id AND src.modulo_id=mc.modulo_id
                       AND CAST(src.fecha AS date)<c.fecha),0) AS m3_previo_esperado,
           (SELECT COUNT(*) FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario src
            WHERE src.campaña_id=mc.campaña_id AND src.modulo_id=mc.modulo_id
              AND CAST(src.fecha AS date)<c.fecha) AS filas_pre_corte
    FROM reclamo.modulo_congelado mc CROSS JOIN corte c
    WHERE mc.campaña_id=10 AND mc.pad_id=2
)
SELECT * FROM previo ORDER BY modulo_numero''')
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    rows=[dict(r) for r in conn.execute(sql).mappings()]
if ident['database_name'].lower()!='inventar_spchidr' or len(rows)!=26: raise RuntimeError('Wrong target/count')
if any(r['filas_pre_corte']!=0 or abs(float(r['m3_previo_esperado']-r['m3_camiones_previo']))>0.001 for r in rows):
    raise RuntimeError('Baseline mismatch')
(BASE/'sql_verification.json').write_text(json.dumps({'identity':ident,'rows':rows},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,'modules',len(rows),'rows_pre_cut',sum(r['filas_pre_corte'] for r in rows),'differences',0)
