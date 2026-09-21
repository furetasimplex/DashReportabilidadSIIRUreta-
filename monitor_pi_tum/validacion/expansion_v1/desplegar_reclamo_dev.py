"""Crea en DEV la cadena paralela de Reclamo CV025."""
from pathlib import Path
from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection

ROOT = Path(__file__).resolve().parent
NAMES = (
    'reclamo.v_cv25_diario_contingencia_test',
    'reclamo.v_preliminar_cv25_contingencia_test',
    'reclamo.v_preliminar_cv25_con_acumulado_contingencia_test',
    'reclamo.v_reclamo_diario_contingencia_test',
    'reclamo.v_diferencia_cv25_contingencia_test',
)

with _engine_dev().begin() as conn:
    _assert_dev_connection(conn)
    for name in NAMES:
        if conn.execute(text('SELECT OBJECT_ID(:n)'), {'n': name}).scalar() is not None:
            raise RuntimeError(f'La vista TEST ya existe: {name}')
    for name in NAMES:
        conn.exec_driver_sql((ROOT / 'ddl' / (name + '.sql')).read_text(encoding='utf-8'))
        print('CREATE', name)
