"""Prueba MANUAL DEV: nunca permite confirmar la transacción de refresco.

No se ejecuta al importar. Requiere --execute-rollback. Instrumentación en
memoria; no altera código ni objetos SQL. Ejecutar sin otros writers activos.
"""
import argparse
from contextlib import contextmanager
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import event, text
from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
from report_export import report_export as repo

TABLES = (
    'Control_Apilado_TMH_v2_test', 'Historico_Apilado_Diario',
    'Control_Factor_Ajuste_Camiones_v2_test', 'Clays_CuFe',
    'Clays_CuFe_trazabilidad', 'reporte_turno_cache_emision_test',
    'trazabilidad_analitos_tm_emision_test', 'Resumen_Intervalo_TotTM',
    'representatividad_torres_resultado', 'BD_Ton',
)
PROCS = (
    'sp_mantiene_apilado_tmh_v2_test', 'sp_refrescar_historico_apilado_test',
    'sp_mantiene_factor_ajuste_camiones_v2_test', 'sp_refrescar_clays_cufe',
    'sp_actualizar_reporte_turno_cache_emision_test',
    'sp_calcular_resumen_intervalo_totTM', 'sp_refrescar_representatividad_torres',
    'sp_sincronizar_bd_ton',
)


class SentinelRollback(Exception):
    pass


def estado(conn):
    return dict(conn.execute(text("""SELECT @@SPID spid, @@TRANCOUNT trancount,
        XACT_STATE() xact_state,
        APPLOCK_MODE('public','SIIR_CONTINGENCIA_PI_APILADO','Transaction') lock_global,
        APPLOCK_MODE('public','rep_torres_refresco:2026-09','Session') lock_mensual
    """)).mappings().one())


def snapshot(conn):
    """Hash de TODAS las filas, duplicados incluidos, sin inventar columnas fecha."""
    result = {}
    for name in TABLES:
        query = conn.execute(text('SELECT * FROM inventar_SpcHidr.[' + name + ']'))
        columns = list(query.keys())
        rows = sorted(json.dumps(list(row), default=str, ensure_ascii=True) for row in query)
        canonical = json.dumps([columns, rows], ensure_ascii=True).encode()
        result[name] = {'rows': len(rows), 'sha256': hashlib.sha256(canonical).hexdigest()}
    return result


def identities(conn):
    return [dict(r) for r in conn.execute(text("""SELECT OBJECT_NAME(object_id) tabla,
        name columna, CONVERT(varchar(100),last_value) ultimo
        FROM sys.identity_columns WHERE OBJECT_SCHEMA_NAME(object_id)='inventar_SpcHidr'
        ORDER BY object_id,column_id""")).mappings() if r['tabla'] in TABLES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-rollback', action='store_true')
    parser.add_argument('--date', type=date.fromisoformat, default=date(2026, 9, 10))
    parser.add_argument('--output', type=Path,
                        default=Path('report_export/exports/fase4c/manual_dev.json'))
    args = parser.parse_args()
    if not args.execute_rollback:
        parser.error('Falta --execute-rollback; no se ha conectado a SQL.')
    if args.date != date(2026, 9, 10):
        parser.error('Este protocolo se limita a la fecha validada 2026-09-10.')
    if args.output.exists():
        parser.error('El archivo de evidencia ya existe; use otro --output.')
    engine = _engine_dev()
    evidence = {'fecha': str(args.date), 'etapas': []}
    dirty = set()
    final_called = False

    class GuardedEngine:
        @contextmanager
        def connect(self):
            with engine.connect() as conn:
                _assert_dev_connection(conn)
                conn.rollback()  # termina únicamente la lectura de identidad
                yield conn

    guarded = GuardedEngine()

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        proc = next((p for p in PROCS if p in statement and 'EXEC' in statement.upper()), None)
        if proc:
            dirty.add(id(conn))
            evidence['etapas'].append({'etapa': proc, 'dbapi': id(conn.connection.driver_connection), **estado(conn)})
        elif 'sp_getapplock' in statement:
            evidence['etapas'].append({'etapa': 'lock', 'dbapi': id(conn.connection.driver_connection), **estado(conn)})

    def before_commit(conn):
        if id(conn) in dirty:
            # Segunda barrera si el hook de validación no se alcanzara.
            raise SentinelRollback('FAILSAFE: prohibido confirmar la transaccion de datos')

    def on_rollback(conn):
        dirty.discard(id(conn))

    original = repo._validar_refresco_representatividad

    def final(conn):
        nonlocal final_called
        original(conn)
        final_called = True
        evidence['estado_final_interno'] = estado(conn)
        evidence['etapas'].append({'etapa': 'validacion', 'dbapi': id(conn.connection.driver_connection), **estado(conn)})
        evidence['dentro'] = snapshot(conn)
        raise SentinelRollback('SENTINEL_FASE4C_DESPUES_VALIDACION_ANTES_COMMIT')

    with guarded.connect() as conn:
        evidence['estado_antes'] = estado(conn)
        evidence['antes'] = snapshot(conn)
        evidence['identities_antes'] = identities(conn)
    for name, handler in [('before_cursor_execute', before_execute), ('commit', before_commit),
                          ('rollback', on_rollback)]:
        event.listen(engine, name, handler)
    error = None
    try:
        with patch.object(repo, '_get_engine', return_value=guarded), \
             patch.object(repo, '_validar_refresco_representatividad', side_effect=final):
            repo.refrescar_representatividad_para_exportacion(args.date, args.date)
        error = 'ERROR: el coordinador retorno sin Sentinel'
    except SentinelRollback as exc:
        evidence['sentinel'] = str(exc)
    except BaseException as exc:
        error = repr(exc)
    finally:
        for name, handler in [('before_cursor_execute', before_execute), ('commit', before_commit),
                              ('rollback', on_rollback)]:
            event.remove(engine, name, handler)
        with guarded.connect() as conn:
            evidence['estado_despues'] = estado(conn)
            evidence['despues'] = snapshot(conn)
            evidence['identities_despues'] = identities(conn)
    etapas = [r for r in evidence['etapas'] if r['etapa'] in PROCS]
    evidence['checks'] = {
        'validacion_final_alcanzada': final_called,
        'orden': [r['etapa'] for r in etapas] == list(PROCS),
        'una_sesion': len({r['spid'] for r in evidence['etapas']}) == 1,
        'una_dbapi': len({r['dbapi'] for r in evidence['etapas']}) == 1,
        'global_exclusive_en_todos_los_sp': bool(etapas) and all(r['lock_global'] == 'Exclusive' for r in etapas),
        'mensual_exclusive_en_todos_los_sp': bool(etapas) and all(r['lock_mensual'] == 'Exclusive' for r in etapas),
        'transaccion_externa_unica': bool(etapas) and all(r['trancount'] == 1 and r['xact_state'] == 1 for r in etapas),
        'filas_restauradas': evidence['antes'] == evidence['despues'],
        'identities_iguales': evidence['identities_antes'] == evidence['identities_despues'],
    }
    if error:
        evidence['error'] = error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, default=str, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(evidence['checks'], indent=2))
    print('Evidencia:', args.output)
    if error or not all(evidence['checks'].values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
