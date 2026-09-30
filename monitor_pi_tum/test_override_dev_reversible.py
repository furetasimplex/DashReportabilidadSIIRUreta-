"""Prueba explícita DEV: python -m monitor_pi_tum.test_override_dev_reversible.

No se ejecuta por descubrimiento unittest. Toda alta termina en ROLLBACK.
"""
from contextlib import contextmanager
from unittest.mock import patch
import json

from flask import Flask,session
from sqlalchemy import text
from . import db,override_camiones_panel as ui,factor_camiones_panel as panel


def main():
    app=Flask(__name__); app.secret_key='reversible-test-only'
    objects=['factor_camiones_override_aplicacion_test','Control_Factor_Ajuste_Camiones_v2_test',
             'factor_camiones_parametro_vigencia_test','v_ajuste_camiones_emision_test']
    definitions=['sp_factor_ajuste_camiones_test','sp_mantiene_factor_ajuste_camiones_v2_test',
                 'sp_registrar_override_factor_camiones_test','v_ajuste_camiones_emision_test',
                 'sp_registrar_limite_factor_camiones_vigencia_test']
    with db._engine_dev().connect() as conn:
        def snapshot():
            return {name:[dict(r) for r in conn.execute(text('SELECT * FROM inventar_SpcHidr.'+name+' ORDER BY 1')).mappings()] for name in objects}
        def defs():
            return {name:conn.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),{'n':'inventar_SpcHidr.'+name}).scalar() for name in definitions}
        db._assert_dev_connection(conn)
        before=snapshot(); beforedefs=defs()
        conn.rollback()
        class ReversibleEngine:
            @contextmanager
            def connect(self): yield conn
            @contextmanager
            def begin(self): yield conn
        evidence={}
        try:
            with patch.object(db,'_engine_dev',return_value=ReversibleEngine()),app.test_request_context():
                session['user']='PRUEBA_2B1_REVERSIBLE'
                baseline=db.obtener_factor_camiones('2026-09-07','2026-09-07').iloc[0]
                assert abs(baseline.Factor_Ajuste_Calculado-0.819734832992912)<1e-12
                assert baseline.Modo_Aplicacion=='AUTOMATICO'
                for mode in ['FORZADO_1','AUTOMATICO']:
                    token,_,retro=ui.preparar_confirmacion('2026-09-07','2026-09-07',mode,'PRUEBA REVERSIBLE 2B.1')
                    assert retro and ui.habilitar_confirmacion(token,False)[0]
                    result=ui.confirmar_registro(token,True)
                    assert not result['Reproceso_Automatico_Ejecutado']
                    assert 'PENDIENTE DE REPROCESO' in str(ui.presentar_resultado(result))
                    fig,records,_=panel.actualizar_factor('2026-09-07','2026-09-07',0,1)
                    row=records[0]
                    assert abs(row['Factor_Ajuste_Calculado']-baseline.Factor_Ajuste_Calculado)<1e-14
                    assert abs(row['Factor_Aplicacion_Automatica']-baseline.Factor_Aplicacion_Automatica)<1e-14
                    assert row['Modo_Aplicacion']==mode
                    assert row['Factor_Aplicacion_Reportes']==(1 if mode=='FORZADO_1' else row['Factor_Aplicacion_Automatica'])
                    assert any(s.type=='rect' for s in fig.layout.shapes)==(mode=='FORZADO_1')
                    assert mode in str(panel.detalle_dia(records))
                    evidence[mode]={k:row[k] for k in ['Factor_Ajuste_Calculado','Factor_Aplicacion_Automatica','Factor_Aplicacion_Reportes','Modo_Aplicacion','Id_Control_Aplicacion']}
                # Evento intermedio invalida la versión capturada, también en SQL real.
                token,_,_=ui.preparar_confirmacion('2026-09-07','2026-09-07','FORZADO_1','Confirmación a invalidar')
                version=db.obtener_version_override_rango('2026-09-07','2026-09-07')
                db.registrar_override_factor('2026-09-07','2026-09-07','AUTOMATICO','Evento intermedio reversible','PRUEBA_2B1_REVERSIBLE',version)
                try: ui.confirmar_registro(token,True)
                except ValueError as exc: assert 'historial cambió' in str(exc)
                else: raise AssertionError('No rechazó confirmación obsoleta')
                current=snapshot()
                for name in objects[1:3]: assert current[name]==before[name]
                assert len(current[objects[0]])==len(before[objects[0]])+3
        finally:
            conn.rollback()
        assert snapshot()==before
        assert defs()==beforedefs
        evidence['rollback_filas_y_definiciones_identicos']=True
        evidence['confirmacion_obsoleta_rechazada']=True
        print(json.dumps(evidence,ensure_ascii=True,indent=2))


if __name__=='__main__': main()
