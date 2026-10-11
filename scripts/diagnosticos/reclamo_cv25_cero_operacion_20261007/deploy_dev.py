"""Apply only the reviewed CV25 view change to the guarded DEV database."""
import json, os, sys
from pathlib import Path
from sqlalchemy import text
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from db_connection import get_engine
BASE=Path(__file__).resolve().parent
if os.getenv('SQLSERVER_DB','').lower()!='inventar_spchidr': raise RuntimeError('DEV only')
before=json.loads((BASE/'snapshot_before.json').read_text(encoding='utf-8'))['objects']['v_cv25_diario']['metadata']['definition']
sql=(BASE/'alter_v_cv25_diario.sql').read_text(encoding='utf-8')
if not sql.startswith('ALTER VIEW [reclamo].[v_cv25_diario]') or sql.count('CERO_OPERACION_CONFIRMADO')!=1:
    raise RuntimeError('Unexpected deployment script')
with get_engine().begin() as c:
    database=c.scalar(text('SELECT DB_NAME()'))
    if database.lower()!='inventar_spchidr': raise RuntimeError('Wrong database')
    current=c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cv25_diario'))"))
    if current!=before: raise RuntimeError('Live definition changed since audit; no DDL applied')
    c.exec_driver_sql(sql)
    after=c.scalar(text("SELECT OBJECT_DEFINITION(OBJECT_ID('reclamo.v_cv25_diario'))"))
    if 'CERO_OPERACION_CONFIRMADO' not in after: raise RuntimeError('Post-DDL definition mismatch')
print('DEV view altered and verified:',database)
