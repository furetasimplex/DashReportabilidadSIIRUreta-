"""Smoke manual READ ONLY: python -m lixiviacion.smoke_dev. Nunca consulta PROD."""
from decimal import Decimal
import json
import os
from pathlib import Path
from sqlalchemy import text
from . import db


def run():
    if os.getenv('SQLSERVER_DB', '').lower() != 'inventar_spchidr':
        raise RuntimeError('Smoke restringido a la base DEV definida por db_startup_check.py.')
    with db._connection() as conn:
        if conn.execute(text('SELECT DB_NAME()')).scalar_one().lower() != 'inventar_spchidr':
            raise RuntimeError('La conexión no corresponde a DEV.')
    expected = {
        1: (3264, '2908120.161887395403000', '6801.723817085'),
        2: (2856, '9260436.238434241623000', '23334.497994245'),
        None: (6120, '12168556.400321637026000', '30136.221811330'),
    }
    (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion').mkdir(parents=True, exist_ok=True)
    report = {}
    for pad, (count, flow, cu) in expected.items():
        f = dict(desde='2026-06-01', hasta='2026-09-10', pad=pad)
        actual, daily = db.overview(f)
        # Referencia exacta aprobada, sin redondear ni sumar subtotales redondeados.
        differences = {
            'registros': actual['registros']-count,
            'flujo_exacto': str(actual['flujo']-Decimal(flow)) if actual['flujo'] is not None else 'NULL',
            'transferencia_t': str(actual['transferencia']-Decimal(cu)) if actual['transferencia'] is not None else 'NULL',
        }
        passed = differences['registros'] == 0 and all(Decimal(differences[k]) == 0 for k in ('flujo_exacto', 'transferencia_t'))
        report[str(pad)] = dict(actual=actual, diferencias=differences, dias_pad=len(daily), passed=passed)
        if not passed:
            break  # detenerse ante discrepancia; no modificar SQL ni continuar otras pruebas live
    out = (Path(__file__).resolve().parents[1] / 'auditorias/archivo/lixiviacion/SMOKE_DEV.json')
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str)+'\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    if len(report) != 3 or not all(r['passed'] for r in report.values()):
        raise SystemExit('DIFERENCIA: detener investigación funcional; no modificar SQL.')


if __name__ == '__main__':
    run()
