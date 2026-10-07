"""Read-only confirmation of SP definition and October rows after guarded rollback."""
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
with get_engine().connect() as conn:
    ident=dict(conn.execute(text('SELECT @@SERVERNAME server_name,DB_NAME() database_name')).mappings().one())
    definition=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test'))")).scalar_one()
    rows=[dict(r) for r in conn.execute(text("SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WHERE Fecha BETWEEN '2026-10-01' AND '2026-10-04' ORDER BY Fecha")).mappings()]
print(ident,'gate_installed',('ch.Chancado_TMS_Real' in definition),
      'rows',[(str(r['Fecha']),r['Chancado_TMS_Real'],r['Camiones_TMS_Reclamo_Sulfuros']) for r in rows])
