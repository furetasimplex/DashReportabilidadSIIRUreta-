"""Diagnóstico manual A/B de Publicar Reclamo. DEV, sin commits ni publicación."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, time
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TABLES = (
    'Control_Factor_Ajuste_Camiones_v2_test',
    'reporte_turno_cache_emision_test',
    'Datos_conciliados_of',
)
KEYS = {TABLES[0]: ('Fecha',), TABLES[1]: ('Fecha', 'Turno'), TABLES[2]: ('Fecha',)}
# Lista deliberadamente cerrada: no ignorar cualquier columna datetime.
AUDIT_NAMES = {'fecha_calculo', 'fecha_actualizacion'}
PROCS = (
    'sp_mantiene_datos_conciliados_emision_test',
    'sp_mantiene_factor_ajuste_camiones_v2_test',
    'sp_factor_ajuste_camiones_test',
)
SQL_PUBLICAR = '''EXEC inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
    @FechaInicio='2026-09-10', @FechaFin='2026-09-10',
    @DiasReproceso=7, @RefrescarFactor=?;'''


def encode(value):
    """Preserva decimales sin convertirlos a float y distingue NULL de texto."""
    if isinstance(value, Decimal):
        return {'decimal': str(value)}
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, bytes):
        return {'bytes': value.hex()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f'Tipo no soportado en evidencia: {type(value).__name__}')


def differences(before, after, ignore=()):
    """Diferencias exactas por clave; incluye altas, bajas, columnas y valores."""
    result = {}
    for table in TABLES:
        left, right = before[table], after[table]
        def index(rows):
            indexed = {}
            for row in rows:
                key = tuple(row[k] for k in KEYS[table])
                if key in indexed:
                    raise ValueError(f'Clave duplicada en {table}: {key}')
                indexed[key] = row
            return indexed
        a, b = index(left['rows']), index(right['rows'])
        ignored = set(ignore.get(table, ())) if isinstance(ignore, dict) else set(ignore)
        changes = []
        for key in sorted(a.keys() | b.keys(), key=str):
            x, y = a.get(key), b.get(key)
            cols = sorted(set((x or {}).keys()) | set((y or {}).keys()))
            for col in cols:
                if col in ignored:
                    continue
                if x is None or y is None or col not in x or col not in y or x[col] != y[col]:
                    changes.append({'clave': dict(zip(KEYS[table], key)), 'columna': col,
                                    'A': None if x is None else x.get(col),
                                    'B': None if y is None else y.get(col),
                                    'fila_A_existe': x is not None, 'fila_B_existe': y is not None})
        result[table] = {
            'filas_A': len(a), 'filas_B': len(b), 'cambios': changes,
            'columnas_diferentes': sorted({x['columna'] for x in changes}),
            'fechas_diferentes': sorted({x['clave']['Fecha'] for x in changes}),
            'columnas_ignoradas': sorted(ignored),
        }
    return result


def classify(factor_a_changed, dc_different, valid=True):
    if not valid:
        return 'REVISAR_MANUALMENTE'
    if not factor_a_changed and not dc_different:
        return 'REFRESCO_FACTOR_REDUNDANTE'
    if factor_a_changed and dc_different:
        return 'FACTOR_PREVIO_NO_EQUIVALENTE'
    if factor_a_changed and not dc_different:
        return 'FACTOR_ESCRITURA_NO_NECESARIA_PARA_PUBLICAR'
    return 'REVISAR_MANUALMENTE'


@contextmanager
def rollback_only(conn):
    """Nunca usa un context manager que confirme al salir sin excepción."""
    transaction = conn.begin()
    try:
        yield conn
    finally:
        try:
            # También cubre fallos previos al SP o a la captura final.
            if transaction.is_active:
                transaction.rollback()
            else:
                conn.rollback()
        except BaseException:
            conn.invalidate()
            raise


def no_commit(conn):
    raise RuntimeError('COMMIT bloqueado: diagnóstico exclusivamente rollback-only.')


def state(conn, text):
    return dict(conn.execute(text('''SELECT @@SPID AS spid, @@TRANCOUNT AS trancount,
        XACT_STATE() AS xact_state,
        APPLOCK_MODE('public','SIIR_CONTINGENCIA_PI_APILADO','Transaction') AS lock_global
    ''')).mappings().one())


def require_transaction(value):
    if (value['trancount'], value['xact_state'], value['lock_global']) != (1, 1, 'Exclusive'):
        raise RuntimeError(f'Contrato transaccional no satisfecho: {value}')


def snapshot(conn, text):
    result = {}
    for table in TABLES:
        query = conn.execute(text(f'SELECT * FROM inventar_SpcHidr.[{table}]'))
        cols = list(query.keys())
        rows = [{col: encode(value) for col, value in zip(cols, row)} for row in query]
        rows.sort(key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=True))
        result[table] = {'columns': cols, 'rows': rows}
    return result


def identity_snapshot(conn, text):
    rows = conn.execute(text('''SELECT OBJECT_NAME(object_id) AS tabla, name AS columna,
        CONVERT(varchar(100),last_value) AS ultimo FROM sys.identity_columns
        WHERE OBJECT_SCHEMA_NAME(object_id)='inventar_SpcHidr'
        ORDER BY object_id,column_id''')).mappings()
    return [dict(row) for row in rows if row['tabla'] in TABLES]


def inspect_contract(conn, text):
    """Rechaza commits internos y triggers no contemplados antes del diagnóstico."""
    definitions = {}
    for name in PROCS:
        definition = conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:name))'),
                                  {'name': 'inventar_SpcHidr.' + name}).scalar_one()
        if not definition:
            raise RuntimeError(f'Definición no visible: {name}')
        sql = re.sub(r'/\*.*?\*/|--[^\n]*', '', definition, flags=re.S)
        if re.search(r'\bCOMMIT\b', sql, re.I):
            raise RuntimeError(f'COMMIT SQL interno detectado en {name}; requiere revisión.')
        definitions[name] = {'sha256': hashlib.sha256(definition.encode()).hexdigest(),
                             'definition': definition}
    triggers = list(conn.execute(text('''SELECT t.name, OBJECT_NAME(t.parent_id) AS tabla
        FROM sys.triggers t WHERE t.is_disabled=0
        AND OBJECT_SCHEMA_NAME(t.parent_id)='inventar_SpcHidr' ''')).mappings())
    if any(row['tabla'] in TABLES for row in triggers):
        raise RuntimeError('Hay triggers habilitados en las tablas del protocolo; revisar antes de ejecutar.')
    audit = {}
    for table in TABLES:
        columns = conn.execute(text('''SELECT c.name, TYPE_NAME(c.system_type_id) AS tipo
            FROM sys.columns c WHERE c.object_id=OBJECT_ID(:name)'''),
            {'name': 'inventar_SpcHidr.' + table}).mappings()
        audit[table] = [r['name'] for r in columns if r['name'].lower() in AUDIT_NAMES
                        and r['tipo'] in ('date', 'datetime', 'datetime2', 'smalldatetime', 'datetimeoffset')]
    return definitions, audit


def execute_sp(conn, factor):
    # Consumir todos los resultsets para no omitir un error SQL tardío.
    cursor = conn.connection.driver_connection.cursor()
    try:
        cursor.execute(SQL_PUBLICAR, factor)
        while True:
            if cursor.description:
                cursor.fetchall()
            if not cursor.nextset():
                break
    finally:
        cursor.close()


def run(engine, guard, lock, text, evidence):
    baseline = None
    baseline_identity = None
    for label, factor in (('A', 1), ('B', 0)):
        case = evidence.setdefault('casos', {}).setdefault(label, {})
        error = None
        try:
            with engine.connect() as conn:
                with rollback_only(conn):
                    guard(conn)
                    lock(conn)
                    case['estado_antes'] = state(conn, text)
                    require_transaction(case['estado_antes'])
                    definitions, audit = inspect_contract(conn, text)
                    if 'definiciones' not in evidence:
                        evidence['definiciones'], evidence['columnas_auditoria'] = definitions, audit
                    elif definitions != evidence['definiciones'] or audit != evidence['columnas_auditoria']:
                        raise RuntimeError('Cambió el contrato SQL entre A y B.')
                    case['antes'] = snapshot(conn, text)
                    case['identities_antes'] = identity_snapshot(conn, text)
                    if baseline is None:
                        baseline, baseline_identity = case['antes'], case['identities_antes']
                    if case['antes'] != baseline or case['identities_antes'] != baseline_identity:
                        raise RuntimeError('Baseline distinto; no se ejecuta el caso.')
                    execute_sp(conn, factor)
                    case['dentro'] = snapshot(conn, text)
                    case['estado_despues_sp'] = state(conn, text)
                    require_transaction(case['estado_despues_sp'])
                    if case['estado_antes']['spid'] != case['estado_despues_sp']['spid']:
                        raise RuntimeError('Cambió la sesión SQL durante el caso.')
        except BaseException as exc:
            error = exc
            case['error'] = repr(exc)
        finally:
            # Nueva conexión/transacción de verificación, también rollback-only.
            if baseline is not None:
                try:
                    with engine.connect() as conn:
                        with rollback_only(conn):
                            guard(conn)
                            lock(conn)
                            require_transaction(state(conn, text))
                            case['despues_rollback'] = snapshot(conn, text)
                            case['identities_despues'] = identity_snapshot(conn, text)
                    case['restauracion_exacta'] = case['despues_rollback'] == baseline
                    case['identities_restauradas'] = case['identities_despues'] == baseline_identity
                    if not case['restauracion_exacta'] or not case['identities_restauradas']:
                        raise RuntimeError('No se confirmó restauración exacta; detener diagnóstico.')
                except BaseException as verify_error:
                    case['error_verificacion'] = repr(verify_error)
                    if error is None:
                        error = verify_error
        if error is not None:
            raise error
    a, b = evidence['casos']['A']['dentro'], evidence['casos']['B']['dentro']
    audit = evidence['columnas_auditoria']
    evidence['comparaciones'] = {
        'baseline_vs_A_completo': differences(baseline, a),
        'baseline_vs_B_completo': differences(baseline, b),
        'baseline_vs_A_funcional': differences(baseline, a, audit),
        'baseline_vs_B_funcional': differences(baseline, b, audit),
        'A_vs_B_funcional': differences(a, b, audit),
    }
    comparisons = evidence['comparaciones']
    changed = lambda comparison, table: bool(comparisons[comparison][table]['cambios'])
    answers = {
        'factor_A_cambio_funcional': changed('baseline_vs_A_funcional', TABLES[0]),
        'factor_B_cambio_funcional': changed('baseline_vs_B_funcional', TABLES[0]),
        'cache_A_cambio_exacto': changed('baseline_vs_A_completo', TABLES[1]),
        'cache_B_cambio_exacto': changed('baseline_vs_B_completo', TABLES[1]),
        'DC_A_B_identicos_funcionales': not changed('A_vs_B_funcional', TABLES[2]),
    }
    evidence['respuestas'] = answers
    valid = not (answers['factor_B_cambio_funcional'] or answers['cache_A_cambio_exacto']
                 or answers['cache_B_cambio_exacto']
                 or changed('baseline_vs_B_completo', TABLES[0]))
    evidence['clasificacion'] = classify(answers['factor_A_cambio_funcional'],
                                         not answers['DC_A_B_identicos_funcionales'], valid)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-rollback', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'scripts/diagnosticos/reclamo_publicar_factor_dev.json')
    args = parser.parse_args(argv)
    if not args.execute_rollback:
        parser.error('Falta --execute-rollback. No se ha conectado a SQL.')
    if args.output.exists():
        parser.error('La evidencia ya existe; elija otro --output.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Reserva exclusiva antes de conectar: evita una prueba sin salida escribible.
    with args.output.open('x', encoding='utf-8') as output:
        evidence = {'fecha_inicio': '2026-09-10', 'fecha_fin': '2026-09-10',
                    'dias_reproceso': 7, 'captura': 'todas las filas de las tres tablas',
                    'clasificacion': 'REVISAR_MANUALMENTE'}
        engine = None
        listening = False
        failed = False
        try:
            # Importaciones de conexión solo después del consentimiento explícito.
            sys.path.insert(0, str(ROOT))
            from sqlalchemy import event, text
            from monitor_pi_tum.db import _engine_dev, _assert_dev_connection, _adquirir_lock_contingencia
            engine = _engine_dev()
            event.listen(engine, 'commit', no_commit)
            listening = True
            run(engine, _assert_dev_connection, _adquirir_lock_contingencia, text, evidence)
        except BaseException as exc:
            failed = True
            evidence['error'] = repr(exc)
            evidence['clasificacion'] = 'REVISAR_MANUALMENTE'
        finally:
            if listening:
                event.remove(engine, 'commit', no_commit)
            json.dump(evidence, output, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps({'clasificacion': evidence['clasificacion'],
                      'respuestas': evidence.get('respuestas'), 'evidencia': str(args.output)},
                     ensure_ascii=False, indent=2))
    if failed or evidence['clasificacion'] == 'REVISAR_MANUALMENTE':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
