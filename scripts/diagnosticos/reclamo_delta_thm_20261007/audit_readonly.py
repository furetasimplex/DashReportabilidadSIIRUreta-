"""Read-only DEV snapshot of THM source and Reclamo truck rows, campaign 10."""
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
queries={
 'source': "SELECT * FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario WHERE campaña_id=10 ORDER BY modulo_id,fecha",
 'reclamo': "SELECT * FROM reclamo.camiones_reclamo WHERE campaña_id=10 ORDER BY modulo_id,fecha",
 'acumulado': "SELECT * FROM reclamo.v_camiones_acumulado WHERE campaña_id=10 ORDER BY modulo_id,fecha",
 'modules': "SELECT campaña_id,pad_id,modulo_id,modulo_numero,m3_camiones_previo FROM reclamo.modulo_congelado WHERE campaña_id=10 AND pad_id=2 ORDER BY modulo_id",
 'source_columns': "SELECT c.name,c.column_id FROM sys.columns c WHERE c.object_id=OBJECT_ID('inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario') ORDER BY c.column_id",
 'reclamo_columns': "SELECT c.name,c.column_id FROM sys.columns c WHERE c.object_id=OBJECT_ID('reclamo.camiones_reclamo') ORDER BY c.column_id",
 'sync_definition': "SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.sp_sincronizar_desde_etl')) AS definition",
 'sync_runs': "SELECT TOP (20) * FROM reclamo.log_ejecucion WHERE procedimiento='reclamo.sp_sincronizar_desde_etl' ORDER BY ejecucion_id DESC",
 'sep30_log': "SELECT TOP (100) * FROM reclamo.log_sincronizacion WHERE tabla_destino='camiones_reclamo' AND fecha_dato='2026-09-30' AND [campaña_id]=10 AND modulo_id IN (81,87,89,90) ORDER BY ejecucion_id DESC",
}
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name,SYSDATETIME() observed_at')).mappings().one())
    if ident['database_name'].lower()!='inventar_spchidr': raise RuntimeError('Wrong database')
    results={k:[dict(r) for r in conn.execute(text(q)).mappings()] for k,q in queries.items()}
(BASE/'snapshot.json').write_text(json.dumps({'identity':ident,'results':results},ensure_ascii=False,default=str,indent=2),encoding='utf-8')
print(ident,{k:len(v) for k,v in results.items()})
