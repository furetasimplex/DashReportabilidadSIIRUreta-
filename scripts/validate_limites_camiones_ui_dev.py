"""Callbacks reales contra DEV; transacción externa y ROLLBACK en cada caso.

Solo el adaptador de conexiones de prueba evita el commit de registrar_limite_factor.
El callback, validaciones, guard DEV y EXEC del SP son los de producción.
"""
from contextlib import contextmanager
from datetime import date,timedelta
from pathlib import Path
from unittest.mock import patch
import json

from flask import Flask,session
from sqlalchemy import text
from dash._callback_context import context_value
from dash._utils import AttributeDict
from monitor_pi_tum import db,limites_camiones_panel as ui,factor_camiones_panel as panel


def read(conn,name):
    return [dict(r) for r in conn.execute(text('SELECT * FROM inventar_SpcHidr.'+name+' ORDER BY 1')).mappings()]


def main():
    app=Flask(__name__); app.secret_key='reversible-test-only'
    evidence={}
    with db._engine_dev().connect() as conn:
        db._assert_dev_connection(conn)
        names=['factor_camiones_parametro_vigencia_test','factor_camiones_parametro_auditoria_test',
               'Control_Factor_Ajuste_Camiones_v2_test','v_ajuste_camiones_emision_test']
        before={name:read(conn,name) for name in names}
        assert len(before[names[0]])==2
        assert {r['flota']:float(r['valor']) for r in before[names[0]]}=={'KOM':380,'CAT':265}
        assert all(r['vigencia_desde']==date(2026,7,1) and r['vigencia_hasta'] is None for r in before[names[0]])
        definition=conn.execute(text("SELECT OBJECT_DEFINITION(OBJECT_ID('inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test'))")).scalar_one()
        assert definition and 'Fecha_Inicio_Afectada' in definition and 'Fecha_Fin_Afectada' in definition
        assert 'sp_mantiene_factor' not in definition and 'sp_factor_ajuste' not in definition
        required={'Humedad_Pct','Sal_TMH_Dia','Delta_Inventario_Chancado_TMS','Limite_KOM_TMH_Viaje','Limite_CAT_TMH_Viaje'}
        assert required <= set(before[names[3]][0])
        evidence['estado_inicial']=before[names[0]]
        conn.rollback()

        class ReversibleEngine:
            @contextmanager
            def connect(self): yield conn
            @contextmanager
            def begin(self): yield conn

        for kind,day in [('futuro',date.today()+timedelta(days=30)),('retroactivo',date(2026,9,20))]:
            try:
                with patch.object(db,'_engine_dev',return_value=ReversibleEngine()),app.test_request_context():
                    session['user']='PRUEBA_UI_REVERSIBLE'
                    token,description,retro=ui.preparar_confirmacion('KOM',350,day.isoformat(),'PRUEBA UI REVERSIBLE SIN REPROCESO')
                    assert read(conn,names[0])==before[names[0]], 'Preparar confirmación escribió'
                    assert ui.habilitar_confirmacion(token,False)[0] == retro
                    context=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-limites-confirmar.n_clicks'}]))
                    try:
                        result=ui.gestionar(1,0,1,'KOM',350,day.isoformat(),'PRUEBA UI REVERSIBLE SIN REPROCESO',token,retro,0)
                    finally: context_value.reset(context)
                    assert result[-1]==1,str(result)
                    current,upcoming,history,notice,pending=ui.refrescar_configuracion(date.today().isoformat(),1)
                    if kind=='futuro':
                        assert '380,00' in str(current) and '350,00' not in str(current)
                        assert '350,00' in str(upcoming)
                        assert 'FUTURO' in str(history)
                        assert 'PROGRAMADO' in str(result[4])
                    else:
                        assert '350,00' in str(current)
                        assert 'PENDIENTE DE REPROCESO' in str(result[4])
                        assert 'PENDIENTE DE REPROCESO' in str(notice)
                        frame=db.obtener_factor_camiones('2026-09-22','2026-09-22')
                        records=panel.preparar_datos(frame)
                        assert records[0]['Limite_KOM_TMH_Viaje']==380
                        context=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-limites-pendientes-datos.data'}]))
                        try: detail=panel.actualizar_detalle(records,None,pending)
                        finally: context_value.reset(context)
                        assert 'PENDIENTE DE REPROCESO' in str(detail)
                        assert '380,00' in str(detail) and '350,00' in str(detail)
                    assert read(conn,names[2])==before[names[2]]
                    assert read(conn,names[3])==before[names[3]]
                    evidence[kind]={'fecha':day,'confirmacion_adicional':retro,'callback_version':result[-1],
                                    'control_y_vista_sin_cambios':True,'resultado':str(result[4])}
            finally:
                conn.rollback()
            assert {name:read(conn,name) for name in names}==before
            conn.rollback()
        evidence['restauracion_exacta_filas']=True
        output=Path('docs/diagnosticos/factor_camiones_fase2a1')
        output.mkdir(parents=True,exist_ok=True)
        (output/'validacion_ui_dev.json').write_text(json.dumps(evidence,default=str,ensure_ascii=False,indent=2),encoding='utf-8')
        print('DEV: callbacks futuro y retroactivo OK. Control V2 y vista intactos; seed 380/265 y auditoría restaurados por ROLLBACK.')


if __name__=='__main__': main()
