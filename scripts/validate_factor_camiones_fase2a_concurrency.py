"""Dos sesiones DEV: registro serializado, ambas operaciones terminan en ROLLBACK."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
import threading
import time

from sqlalchemy import text
from monitor_pi_tum.db import _engine_dev,_assert_dev_connection
from scripts.factor_camiones_fase2a import register,params,AUDIT,CONTROL,VIEW,rows,save,ROOT


def main():
    engine=_engine_dev()
    effective=date.today()+timedelta(days=400)
    ready=threading.Event()
    state={}
    with engine.connect() as first:
        _assert_dev_connection(first)
        before=params(first)
        control,view=rows(first,CONTROL),rows(first,VIEW)
        audit=[dict(r) for r in first.execute(text('SELECT * FROM '+AUDIT+' ORDER BY id')).mappings()]
        register(first,'KOM',350,effective)

        def second():
            with engine.connect() as conn:
                try:
                    _assert_dev_connection(conn)
                    state['spid']=conn.execute(text('SELECT @@SPID')).scalar_one()
                    ready.set()
                    state['resultado']=register(conn,'KOM',365,effective)
                finally:
                    conn.rollback()

        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(second)
            try:
                assert ready.wait(10), 'Segunda conexión no disponible'
                waiting=False
                until=time.monotonic()+8
                while time.monotonic()<until:
                    locks=first.execute(text("SELECT resource_type,request_status FROM sys.dm_tran_locks WHERE request_session_id=:s AND resource_type='APPLICATION'"),{'s':state['spid']}).all()
                    if any(r.request_status=='WAIT' for r in locks):
                        waiting=True
                        break
                    time.sleep(.05)
                assert waiting and not future.done(), 'No se observó serialización por applock'
                state['applock_espera_observada']=True
            finally:
                first.rollback()
            future.result(timeout=20)
        assert state['resultado']['Valor_Anterior']==380
        assert state['resultado']['Valor_Nuevo']==365
        assert params(first)==before
        assert rows(first,CONTROL)==control and rows(first,VIEW)==view
        assert [dict(r) for r in first.execute(text('SELECT * FROM '+AUDIT+' ORDER BY id')).mappings()]==audit
        state['rollback_ambas_sesiones_sin_filas_residuales']=True
        save(ROOT/'concurrencia.json',state)
        print('Concurrencia OK: espera APPLICATION observada; ambas transacciones revertidas, histórico y seed intactos.')


if __name__=='__main__':
    main()
