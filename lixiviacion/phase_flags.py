"""Flags aislados y fijados a la conexión DEV respaldada; fuera de DEV siempre OFF."""
import hashlib
import json
import os
from pathlib import Path
from sqlalchemy import text
NAMES=('ENABLE_PHASE_MODEL_V2','ENABLE_PHASE_ALERTS',
       'ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ','ENABLE_OPERATIONAL_PHASE_OVERRIDES_WRITE')
CONFIG=Path(__file__).with_name('phase_flags_dev.json')
def config():
    try:
        return json.loads(CONFIG.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        return {}
def connection_fingerprint():
    values=(os.getenv('SQLSERVER_HOST','').strip().lower(),os.getenv('SQLSERVER_PORT','1433'),os.getenv('SQLSERVER_DB','').strip().lower())
    return hashlib.sha256('|'.join(values).encode()).hexdigest()
def is_dev():
    c=config()
    return os.getenv('SQLSERVER_DB','').lower()=='inventar_spchidr' and c.get('dev_connection_sha256')==connection_fingerprint()
def enabled(name):
    if name not in NAMES or config().get('force_legacy') is True or not is_dev():
        return False
    value=os.getenv(name)
    return value.strip().lower() in ('true','1','yes','on') if value is not None else config().get(name) is True

def guard_connection(conn):
    if not is_dev():
        raise PermissionError('La función operacional nueva solo está disponible en DEV.')
    row=conn.execute(text("SELECT DB_NAME() db,CAST(SERVERPROPERTY('ServerName') AS nvarchar(128)) servidor")).mappings().one()
    server_hash=hashlib.sha256(row['servidor'].lower().encode()).hexdigest()
    if row['db'].lower()!='inventar_spchidr' or server_hash!=config().get('dev_server_sha256'):
        raise PermissionError('La conexión no corresponde al entorno DEV autorizado.')
