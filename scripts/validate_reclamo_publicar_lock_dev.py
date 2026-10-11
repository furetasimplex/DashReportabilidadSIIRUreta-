"""Manual DEV F4D1. --execute-rollback obligatorio. Nunca confirma publicación.

Ejecutar desde raíz: python scripts/validate_reclamo_publicar_lock_dev.py
--execute-rollback [--output evidencia_nueva.json]. No ejecutado automáticamente.
Verifica timeout (~10 s), estado durante DC, SENTINEL, restauración y liberación.
Requiere validate_reclamo_publicar_factor_dev.py del mismo directorio.
"""
import argparse
from contextlib import contextmanager
import json
from pathlib import Path
import sys
from time import monotonic
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class Sentinel(Exception):
    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-rollback', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT / 'scripts/diagnosticos/reclamo_publicar_lock_dev.json')
    args = parser.parse_args()
    if not args.execute_rollback:
        parser.error('Falta --execute-rollback; no se ha conectado a SQL.')
    if args.output.exists():
        parser.error('No se sobrescribe evidencia; use otro --output.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as output:
        evidence = {'checks': {}}
        engine = None
        listening = False
        try:
            sys.path.insert(0, str(ROOT))
            from sqlalchemy import text, event
            from monitor_pi_tum.db import _engine_dev, _assert_dev_connection, _adquirir_lock_contingencia
            from reclamo import db
            from scripts import validate_reclamo_publicar_factor_dev as helper
            engine = _engine_dev()
            event.listen(engine, 'commit', helper.no_commit)
            listening = True

            def capture(conn):
                return {'tablas': helper.snapshot(conn, text),
                        'identities': helper.identity_snapshot(conn, text)}

            class ProbeConnection:
                def __init__(self, conn, case):
                    self.conn, self.case = conn, case

                def execute(self, sql, params=None):
                    if 'sp_getapplock' in str(sql):
                        self.case['spid_lock'] = helper.state(self.conn, text)['spid']
                        return self.conn.execute(sql)
                    if 'sp_mantiene_datos_conciliados_emision_test' not in str(sql):
                        raise RuntimeError('Operación no contemplada por el diagnóstico.')
                    self.case['dc_invocado'] = True
                    self.case['antes'] = capture(self.conn)
                    self.case['estado_antes_dc'] = helper.state(self.conn, text)
                    helper.require_transaction(self.case['estado_antes_dc'])
                    # Intercepta solo para consumir completamente resultados/errores.
                    # El SQL y parámetros enviados son exactamente los de publicar().
                    statement = str(sql)
                    for name in ('desde', 'hasta', 'dias'):
                        statement = statement.replace(':' + name, '?')
                    cursor = self.conn.connection.driver_connection.cursor()
                    try:
                        cursor.execute(statement, params['desde'], params['hasta'], params['dias'])
                        while True:
                            if cursor.description:
                                cursor.fetchall()
                            if not cursor.nextset():
                                break
                    finally:
                        cursor.close()
                    self.case['dentro'] = capture(self.conn)
                    self.case['estado_despues_dc'] = helper.state(self.conn, text)
                    helper.require_transaction(self.case['estado_despues_dc'])
                    raise Sentinel('SENTINEL_DESPUES_EXEC_ANTES_COMMIT')

            class ProbeEngine:
                def __init__(self, case):
                    self.case = case

                @contextmanager
                def begin(self):
                    with engine.connect() as conn:
                        try:
                            with helper.rollback_only(conn):
                                _assert_dev_connection(conn)
                                yield ProbeConnection(conn, self.case)
                        finally:
                            # SELECT posterior inicia otra transacción de lectura;
                            # también se revierte explícitamente.
                            with helper.rollback_only(conn):
                                self.case['estado_tras_rollback'] = helper.state(conn, text)

            # A: una sesión mantiene el lock mientras publicar usa otra.
            case = evidence['contencion'] = {}
            with engine.connect() as holder:
                with helper.rollback_only(holder):
                    _assert_dev_connection(holder)
                    _adquirir_lock_contingencia(holder)
                    helper.inspect_contract(holder, text)
                    case['holder'] = helper.state(holder, text)
                    baseline = capture(holder)
                    start = monotonic()
                    try:
                        with patch.object(db, 'get_engine', return_value=ProbeEngine(case)):
                            db.publicar('2026-09-10', '2026-09-10')
                    except RuntimeError as exc:
                        case['error'] = str(exc)
                    else:
                        raise RuntimeError('Publicar no rechazó la contención.')
                    case['segundos'] = monotonic() - start
                    evidence['checks']['timeout_sin_dc'] = (
                        9 <= case['segundos'] <= 20 and not case.get('dc_invocado', False)
                        and case.get('error') == 'No se pudo adquirir el bloqueo global para publicar Reclamo.'
                        and case.get('spid_lock') != case['holder']['spid'])
                    evidence['checks']['contencion_sin_cambios'] = capture(holder) == baseline
            if not all(evidence['checks'].values()):
                raise RuntimeError('Falló la prueba de contención; no continuar.')

            # B/C: la implementación real adquiere el lock y ejecuta DC.
            case = evidence['sin_contencion'] = {}
            try:
                with patch.object(db, 'get_engine', return_value=ProbeEngine(case)):
                    db.publicar('2026-09-10', '2026-09-10')
            except Sentinel as exc:
                case['sentinel'] = str(exc)
            finally:
                with engine.connect() as verify:
                    with helper.rollback_only(verify):
                        _assert_dev_connection(verify)
                        _adquirir_lock_contingencia(verify)
                        case['despues_rollback'] = capture(verify)
                        evidence['checks']['restauracion_exacta'] = case.get('antes') == case['despues_rollback']
            evidence['checks']['sentinel'] = 'sentinel' in case
            evidence['checks']['misma_sesion'] = (
                case['spid_lock'] == case['estado_antes_dc']['spid'] == case['estado_despues_dc']['spid'])
            evidence['checks']['estado_transaccional'] = all(
                (case[key]['trancount'], case[key]['xact_state'], case[key]['lock_global']) == (1, 1, 'Exclusive')
                for key in ('estado_antes_dc', 'estado_despues_dc'))
            evidence['checks']['lock_liberado'] = case['estado_tras_rollback']['lock_global'] == 'NoLock'
            if not all(evidence['checks'].values()):
                raise RuntimeError('Uno o más checks fallaron; revisar evidencia.')
        except BaseException as exc:
            evidence['error'] = repr(exc)
        finally:
            if listening:
                event.remove(engine, 'commit', helper.no_commit)
            json.dump(evidence, output, ensure_ascii=False, indent=2)
    print(json.dumps({'checks': evidence['checks'], 'error': evidence.get('error'),
                      'evidencia': str(args.output)}, ensure_ascii=False, indent=2))
    if 'error' in evidence:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
