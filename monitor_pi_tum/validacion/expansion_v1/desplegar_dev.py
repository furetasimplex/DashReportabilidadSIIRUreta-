"""Aplica las variantes TEST en DEV con comprobación de definición y guard DEV."""
import hashlib
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

ROOT = Path(__file__).resolve().parent
NAMES = (
    'inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test',
    'inventar_SpcHidr.v_bd_ton_t12_contingencia_test',
    'inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test',
)


def digest(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def main():
    with _engine_dev().begin() as conn:
        _assert_dev_connection(conn)
        for name in NAMES:
            actual = conn.execute(text('SELECT definition FROM sys.sql_modules WHERE object_id=OBJECT_ID(:n)'),
                                  {'n': name}).scalar()
            esperado = (ROOT / 'backup' / (name + '.sql')).read_bytes().decode('utf-8').replace('\r\r\n', '\n').replace('\r\n', '\n')
            if actual.replace('\r\n', '\n') != esperado:
                raise RuntimeError(f'La definición DEV cambió desde el respaldo: {name}')
        for name in NAMES:
            sql = (ROOT / 'ddl' / (name + '.sql')).read_text(encoding='utf-8')
            conn.exec_driver_sql(sql)
            print('ALTER', name, digest(sql))


if __name__ == '__main__':
    main()
