"""Crear exclusivamente los cuatro objetos nuevos DEV, sin reemplazar existentes.

Sin --apply solo genera el DDL exacto para revisión. Un fallo revierte el DDL.
"""
import argparse
import json
from pathlib import Path
from sqlalchemy import text
from .inspect_dev import engine_dev, definiciones, NUEVOS
from .operational_sql import ddl_batches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).parent
    batches = ddl_batches()
    ddl = "-- DEV exclusivamente. Ejecutar en inventar_SpcHidr.\n" + '\nGO\n'.join(batches) + '\n'
    (root / 'operacional_dev.sql').write_text(ddl, encoding='utf-8')
    print('DDL:', root / 'operacional_dev.sql')
    if not args.apply:
        return
    before = json.loads((root / 'validacion/objetos_protegidos_antes.json').read_text(encoding='utf-8'))
    with engine_dev().begin() as conn:
        assert conn.execute(text('SELECT DB_NAME()')).scalar() == 'inventar_SpcHidr'
        assert definiciones(conn) == before, 'Los objetos protegidos cambiaron desde la inspección.'
        for name in NUEVOS:
            if conn.execute(text('SELECT OBJECT_ID(:n)'), {'n': 'inventar_SpcHidr.' + name}).scalar() is not None:
                raise RuntimeError('Objeto ya existe; no se reemplaza: ' + name)
        for batch in batches:
            conn.exec_driver_sql(batch)
        assert definiciones(conn) == before
    (root / 'validacion/ddl_ejecutado.sql').write_text(ddl, encoding='utf-8')
    print('Creados y confirmados los cuatro objetos DEV. Objetos protegidos sin cambios.')


if __name__ == '__main__':
    main()
