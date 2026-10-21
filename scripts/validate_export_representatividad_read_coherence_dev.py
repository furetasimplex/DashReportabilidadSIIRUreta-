"""F4B3C manual DEV: prepare/read real, rollback y release de ambos locks."""
import argparse
from contextlib import contextmanager, ExitStack
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch

# Inventario F4C: scripts/validate_representatividad_atomicity_dev.py.
TABLES = ('Control_Apilado_TMH_v2_test', 'Historico_Apilado_Diario',
          'Control_Factor_Ajuste_Camiones_v2_test', 'Clays_CuFe',
          'Clays_CuFe_trazabilidad', 'reporte_turno_cache_emision_test',
          'trazabilidad_analitos_tm_emision_test', 'Resumen_Intervalo_TotTM',
          'representatividad_torres_resultado', 'BD_Ton')
# Inspección local: auditorias/archivo/report_export/exports/fase4c/manual_dev.json (antes/después).
# Política de avance de Clays auditada posteriormente en F4B3A.
ALLOWED_IDENTITIES = {'Clays_CuFe_trazabilidad.id_trazabilidad'}
FETCHES = ('fetch_representatividad_torres_report', 'fetch_pesos_representatividad_report',
           'fetch_bd_ton_report', 'fetch_estado_apilado_turno_representatividad',
           'fetch_gestion_representatividad_fy', 'fetch_reporte_torre_oficial_detalle')
PROCS = ('sp_mantiene_apilado_tmh_v2_test', 'sp_refrescar_historico_apilado_test',
         'sp_mantiene_factor_ajuste_camiones_v2_test', 'sp_refrescar_clays_cufe',
         'sp_actualizar_reporte_turno_cache_emision_test', 'sp_calcular_resumen_intervalo_tottm',
         'sp_refrescar_representatividad_torres', 'sp_sincronizar_bd_ton')
GLOBAL = 'SIIR_CONTINGENCIA_PI_APILADO'
MONTHLY = 'rep_torres_refresco:2026-09'


class Sentinel(Exception):
    pass


class FetchFailure(Exception):
    pass


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-rollback', action='store_true')
    parser.add_argument('--editor', action='store_true', help='Paquete editor; default paquete oficial Excel/PDF')
    parser.add_argument('--fail-fetch', type=int, help='Ordinal de fetch real; evidencia registra fallback si existe')
    parser.add_argument('--output', type=Path, default=Path('auditorias/archivo/scripts/diagnosticos/fase4b3c/manual_dev.json'))
    args = parser.parse_args(argv)
    if not args.execute_rollback:
        print('SAFE: no se conecta ni escribe. Requiere --execute-rollback.')
        return 0
    if args.fail_fetch is not None and args.fail_fetch < 1:
        parser.error('--fail-fetch debe ser positivo')
    if args.output.exists():
        parser.error('La evidencia ya existe; use otro --output.')

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from sqlalchemy import event, text
    from monitor_pi_tum.db import _engine_dev, _assert_dev_connection
    from report_export import report_export as repo
    from scripts.validate_reclamo_publicar_factor_dev import encode

    engine = _engine_dev()
    evidence = {'status': 'FAIL', 'periodo': ['2026-09-01','2026-09-30'],
                'editor': args.editor, 'fail_fetch': args.fail_fetch, 'stages': []}
    ready, acquired, finished = threading.Event(), threading.Event(), threading.Event()
    other, frames = {}, []
    thread = None
    count = 0
    dirty = set()
    original_owner = repo._transaccion_representatividad
    original_lock = repo._adquirir_lock_refresco_turno
    original_cutoff = repo.fetch_fecha_corte_operacional_representatividad

    def state(conn):
        return dict(conn.execute(text('''SELECT @@SPID spid, @@TRANCOUNT trancount,
            XACT_STATE() xact_state,
            APPLOCK_MODE('public', :global_name, 'Transaction') lock_global,
            APPLOCK_MODE('public', :monthly, 'Session') lock_monthly'''),
            {'global_name': GLOBAL, 'monthly': MONTHLY}).mappings().one())

    def stage(conn, name, **extra):
        st = state(conn)
        if (st['trancount'], st['xact_state'], st['lock_global'], st['lock_monthly']) != (1,1,'Exclusive','Exclusive'):
            raise RuntimeError(f'Contrato perdido en {name}: {st}')
        if evidence.setdefault('exporter_spid', st['spid']) != st['spid']:
            raise RuntimeError('Cambio de SPID')
        item = dict(st, stage=name, **extra)
        evidence['stages'].append(item)
        return item

    def snapshot(conn):
        result = {}
        for table in TABLES:
            rows = conn.execute(text(f'SELECT * FROM inventar_SpcHidr.[{table}]'))
            columns = list(rows.keys())
            values = sorted(json.dumps([encode(v) for v in row],sort_keys=True) for row in rows)
            result[table] = {'columns':columns, 'count':len(values),
                             'sha256':hashlib.sha256(json.dumps(values).encode()).hexdigest()}
        return result

    def identities(conn):
        rows = conn.execute(text('''SELECT OBJECT_NAME(object_id) tabla, name columna,
            TRY_CONVERT(bigint,last_value) ultimo FROM sys.identity_columns
            WHERE OBJECT_SCHEMA_NAME(object_id)='inventar_SpcHidr' ''')).mappings()
        result = {f"{r['tabla']}.{r['columna']}":r['ultimo'] for r in rows if r['tabla'] in TABLES}
        if set(result) != ALLOWED_IDENTITIES:
            raise RuntimeError(f'IDENTITY inesperada: {result}; no se ejecutará reseed')
        return result

    def locked(conn):
        original_lock(conn)
        stage(conn,'global adquirido')
        if 'baseline' not in evidence:
            evidence['identity_before'] = identities(conn)
            evidence['baseline'] = snapshot(conn)

    def cutoff(*a, **kw):
        stage(kw['conn'], 'fetch_fecha_corte_operacional_representatividad')
        return original_cutoff(*a, **kw)

    def trace(conn, cursor, statement, parameters, context, executemany):
        name = next((p for p in PROCS if p in statement.lower() and 'EXEC' in statement.upper()),None)
        if name:
            dirty.add(id(conn))
            stage(conn,name,parameters=parameters)

    def forbid_commit(conn):
        if id(conn) in dirty:
            raise RuntimeError('COMMIT de datos prohibido: rollback-only')

    class GuardedEngine:
        @contextmanager
        def connect(self):
            with engine.connect() as conn:
                _assert_dev_connection(conn)
                conn.rollback()
                event.listen(conn,'before_cursor_execute',trace)
                event.listen(conn,'commit',forbid_commit)
                event.listen(conn,'rollback',lambda c: dirty.discard(id(c)))
                try:
                    yield conn
                finally:
                    if not conn.invalidated:
                        released = state(conn)
                        evidence['before_pool'] = released
                        conn.rollback()
                        if released['lock_monthly'] != 'NoLock' or released['lock_global'] != 'NoLock':
                            conn.invalidate()
                            raise RuntimeError('Lock retenido al devolver la conexión; invalidada')

    @contextmanager
    def rollback_owner(end_date):
        with original_owner(end_date) as conn:
            yield conn
            expected = set(FETCHES[2:] if args.editor else FETCHES)
            seen = {s['stage'] for s in evidence['stages']}
            if not expected <= seen or not set(PROCS) <= seen:
                raise RuntimeError('Faltan SP/fuentes esperadas en la evidencia')
            stage(conn,'todos los DataFrames materializados')
            raise Sentinel('SENTINEL antes de COMMIT')

    def competing_session():
        with engine.connect() as conn:
            owns_monthly = False
            try:
                _assert_dev_connection(conn)
                other['spid'] = conn.execute(text('SELECT @@SPID')).scalar_one()
                ready.set()
                for resource, owner in ((GLOBAL,'Transaction'),(MONTHLY,'Session')):
                    rc = conn.execute(text('''DECLARE @r int;
                        EXEC @r=sys.sp_getapplock @Resource=:resource,@LockOwner=:owner,
                            @LockMode='Exclusive',@LockTimeout=60000; SELECT @r;'''),
                        {'resource':resource,'owner':owner}).scalar_one()
                    if rc < 0:
                        raise RuntimeError(f'Contención rc={rc}, recurso={resource}')
                    if owner == 'Session':
                        owns_monthly = True
                    other[owner] = 'Exclusive'
                acquired.set()
            except BaseException as exc:
                other['error'] = repr(exc)
                ready.set()
            finally:
                try:
                    if owns_monthly:
                        conn.execute(text(repo.SQL_RELEASEAPPLOCK_REFRESCO_REP),{'recurso':MONTHLY})
                        if state(conn)['lock_monthly'] != 'NoLock':
                            raise RuntimeError('Contendiente no liberó mensual')
                    conn.rollback()
                except BaseException as exc:
                    conn.invalidate()
                    other['error'] = repr(exc)
                finished.set()

    def wrap(name, original):
        def fetch(*a, **kw):
            nonlocal count, thread
            conn = kw['conn']
            count += 1
            item = stage(conn,name,ordinal=count,args=a,kwargs={k:v for k,v in kw.items() if k!='conn'})
            if count == 1:
                thread = threading.Thread(target=competing_session,daemon=True)
                thread.start()
                if not ready.wait(10) or 'error' in other:
                    raise RuntimeError(f'Contendiente no inició: {other}')
                deadline = time.monotonic()+10
                while time.monotonic()<deadline:
                    wait = conn.execute(text('''SELECT blocking_session_id,wait_type FROM sys.dm_exec_requests
                        WHERE session_id=:spid'''),{'spid':other['spid']}).mappings().first()
                    if wait and wait['blocking_session_id']==item['spid'] and str(wait['wait_type']).startswith('LCK_M_'):
                        evidence['second_waiting']=dict(wait)
                        break
                    if acquired.wait(.1):
                        raise RuntimeError('Contendiente adquirió antes de rollback')
                else:
                    raise RuntimeError('No se acreditó contención DMV')
            if acquired.is_set():
                raise RuntimeError('Locks liberados durante lecturas')
            if count == args.fail_fetch:
                raise FetchFailure(f'Fallo deliberado lectura {count}')
            frame=original(*a,**kw)
            stage(conn,name+' completado',rows=len(frame))
            frames.append(frame)
            return frame
        return fetch

    try:
        with ExitStack() as stack:
            stack.enter_context(patch.object(repo,'_get_engine',return_value=GuardedEngine()))
            stack.enter_context(patch.object(repo,'_transaccion_representatividad',rollback_owner))
            stack.enter_context(patch.object(repo,'_adquirir_lock_refresco_turno',locked))
            stack.enter_context(patch.object(repo,'fetch_fecha_corte_operacional_representatividad',cutoff))
            for name in FETCHES:
                stack.enter_context(patch.object(repo,name,wrap(name,getattr(repo,name))))
            try:
                if args.editor:
                    repo.preparar_paquete_editor_representatividad(date(2026,9,1),date(2026,9,30))
                else:
                    repo.armar_paquete_reporte_torre_oficial(date(2026,9,1),date(2026,9,30))
                raise RuntimeError('Retorno sin SENTINEL')
            except Sentinel:
                if args.fail_fetch:
                    raise RuntimeError('No se alcanzó el ordinal de fallo solicitado')
                released=evidence['before_pool']
                if released['lock_global']!='NoLock' or released['lock_monthly']!='NoLock':
                    raise RuntimeError('Constructor todavía bajo locks')
                evidence['simulated_constructor_after_release']={'rows':[len(f) for f in frames]}
            except FetchFailure:
                evidence['no_artifact_on_error']=True
        if not finished.wait(10) or not acquired.is_set() or 'error' in other:
            raise RuntimeError(f'Contendiente no terminó correctamente: {other}')
        # Snapshot posterior estable respecto de writers F4: mismo orden mensual/global.
        with engine.connect() as conn:
            try:
                _assert_dev_connection(conn)
                rc=conn.execute(text(repo.SQL_GETAPPLOCK_REFRESCO_REP),{'recurso':MONTHLY,'timeout':10000}).scalar()
                if rc is None or rc<0:
                    raise RuntimeError('No se adquirió mensual para snapshot posterior')
                original_lock(conn)
                evidence['after']=snapshot(conn)
                evidence['identity_after']=identities(conn)
            finally:
                try:
                    conn.execute(text(repo.SQL_RELEASEAPPLOCK_REFRESCO_REP),{'recurso':MONTHLY})
                    if state(conn)['lock_monthly']!='NoLock':
                        raise RuntimeError('Release posterior falló')
                    conn.rollback()
                except BaseException:
                    conn.invalidate()
                    raise
        if evidence['baseline']!=evidence['after']:
            raise RuntimeError('Filas/columnas/count/hash no restaurados')
        evidence['identity_delta']={}
        for name in ALLOWED_IDENTITIES:
            before,after=evidence['identity_before'][name],evidence['identity_after'][name]
            if before is not None and (after is None or after<before):
                raise RuntimeError('IDENTITY retrocedió/desapareció')
            evidence['identity_delta'][name]=None if after is None else after-(before or 0)
        evidence['status']='PASS'
    except BaseException as exc:
        evidence['error']=repr(exc)
    finally:
        if thread:
            thread.join(timeout=10)
        evidence['second_session']=other
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(evidence,indent=2,default=encode),encoding='utf-8')
    print(evidence['status'],args.output)
    return 0 if evidence['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
