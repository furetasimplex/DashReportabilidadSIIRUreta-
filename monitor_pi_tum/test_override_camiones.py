"""Pruebas de 2B.1 sin conexiones ni cambios SQL."""
import unittest
from datetime import date,timedelta
from unittest.mock import patch,MagicMock

from flask import Flask,session
from dash._callback_context import context_value
from dash._utils import AttributeDict
from . import db,override_camiones_panel as ui,factor_camiones_panel as panel
from .test_factor_camiones import datos


class OverrideTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__); self.app.secret_key='unit-test'

    def test_payload(self):
        p=dict(fecha_desde='2026-09-07',fecha_hasta='2026-09-08',modo='FORZADO_1',motivo=' Motivo ',usuario=' tester ')
        self.assertEqual(db.validar_override_factor(**p)['motivo'],'Motivo')
        for k,v in [('fecha_desde','no'),('fecha_hasta',None),('fecha_desde','2026-09-09'),
                    ('modo','otro'),('motivo',' '),('motivo','x'*1001),('usuario',''),('usuario','x'*129)]:
            with self.subTest(field=k),self.assertRaises(ValueError): db.validar_override_factor(**{**p,k:v})

    def test_preparar_sin_escritura_y_retroactivo(self):
        with self.app.test_request_context(),patch.object(db,'obtener_version_override_rango',return_value=7),patch.object(db,'registrar_override_factor') as write:
            session['user']='especialista'
            for mode in ('FORZADO_1','AUTOMATICO'):
                token,description,retro=ui.preparar_confirmacion('2026-09-07','2026-09-07',mode,'Prueba')
                self.assertTrue(retro); self.assertIn('CAMBIO RETROACTIVO',str(description))
                self.assertEqual(session[ui.SESSION_KEY]['modo'],mode)
                self.assertEqual(session[ui.SESSION_KEY]['version_esperada'],7)
                self.assertTrue(ui.habilitar_confirmacion(token,False)[0])
                with self.assertRaises(ValueError): ui.confirmar_registro(token,False)
            write.assert_not_called()

    def test_futuro_hoy_y_token(self):
        with self.app.test_request_context(),patch.object(db,'obtener_version_override_rango',return_value=None),patch.object(db,'registrar_override_factor',return_value={}) as write:
            session['user']='especialista'
            future=(date.today()+timedelta(days=2)).isoformat()
            token,description,retro=ui.preparar_confirmacion(future,future,'FORZADO_1','Prueba')
            self.assertFalse(retro); self.assertIn('CAMBIO PROGRAMADO',str(description))
            self.assertFalse(ui.habilitar_confirmacion(token,False)[0])
            ui.confirmar_registro(token,False)
            self.assertNotIn(ui.SESSION_KEY,session)
            self.assertEqual(write.call_args.kwargs['usuario'],'especialista')
            with self.assertRaises(ValueError): ui.confirmar_registro(token,False)
            self.assertEqual(write.call_count,1)
            _,description,_=ui.preparar_confirmacion(date.today().isoformat(),date.today().isoformat(),'AUTOMATICO','Hoy')
            self.assertIn('CAMBIO VIGENTE DESDE HOY',str(description))

    def test_preparacion_fallida_y_sin_usuario(self):
        with self.app.test_request_context(),patch.object(db,'obtener_version_override_rango',side_effect=RuntimeError('private')):
            session['user']='especialista'; session[ui.SESSION_KEY]={'token':'anterior'}
            with self.assertRaises(RuntimeError): ui.preparar_confirmacion('2026-09-07','2026-09-07','FORZADO_1','Motivo')
            self.assertNotIn(ui.SESSION_KEY,session)
            session.pop('user')
            with self.assertRaises(ValueError): ui.preparar_confirmacion('2026-09-07','2026-09-07','FORZADO_1','Motivo')
            with self.assertRaises(ValueError): ui.confirmar_registro('fake',True)

    def test_concurrencia_guard_y_unica_escritura(self):
        engine=MagicMock(); conn=engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.scalar.return_value=0
        conn.execute.return_value.mappings.return_value.one.return_value={'Id_Override':9}
        args=('2026-09-07','2026-09-07','FORZADO_1','Motivo','especialista')
        with patch.object(db,'_engine_dev',return_value=engine),patch.object(db,'_assert_dev_connection') as guard,patch.object(db,'_version_override_rango',return_value=8):
            with self.assertRaisesRegex(ValueError,'historial cambió'): db.registrar_override_factor(*args,version_esperada=7)
            self.assertEqual(conn.execute.call_count,1)
            guard.assert_called_once_with(conn)
        conn.execute.reset_mock()
        with patch.object(db,'_engine_dev',return_value=engine),patch.object(db,'_assert_dev_connection'),patch.object(db,'_version_override_rango',return_value=8):
            self.assertEqual(db.registrar_override_factor(*args,version_esperada=8),{'Id_Override':9})
            queries=' '.join(str(c.args[0]) for c in conn.execute.call_args_list)
            self.assertIn('sp_getapplock',queries)
            self.assertIn('SIIR_FACTOR_CAMIONES_OVERRIDE_2B',queries)
            self.assertIn('sp_registrar_override_factor_camiones_test',queries)
            for word in ('INSERT ','UPDATE ','DELETE ','sp_mantiene','sp_factor_ajuste','publicar'):
                self.assertNotIn(word,queries)
        conn.execute.reset_mock()
        with patch.object(db,'_engine_dev',return_value=engine),patch.object(db,'_assert_dev_connection',side_effect=RuntimeError('guard')):
            with self.assertRaises(RuntimeError): db.registrar_override_factor(*args,version_esperada=8)
            conn.execute.assert_not_called()

    def test_version_solapamiento(self):
        conn=MagicMock()
        db._version_override_rango(conn,date(2026,9,7),date(2026,9,8),True)
        query=str(conn.execute.call_args.args[0])
        self.assertIn('MAX(id_override)',query)
        self.assertIn('fecha_desde<=:hasta AND fecha_hasta>=:desde',query)
        self.assertIn('UPDLOCK,HOLDLOCK',query)

    def test_respuesta_sp(self):
        p=dict(Modo='FORZADO_1',Fecha_Desde='2026-09-07',Fecha_Hasta='2026-09-07',
               Fecha_Inicio_Materializada_Afectada='2026-09-07',Fecha_Fin_Materializada_Afectada='2026-09-07')
        self.assertIn('PENDIENTE DE REPROCESO',str(ui.presentar_resultado({**p,'Afecta_Fechas_Materializadas':True})))
        self.assertIn('PROGRAMADO',str(ui.presentar_resultado({**p,'Afecta_Fechas_Materializadas':False})))
        self.assertNotIn('private',ui.mensaje_error(RuntimeError('private stack trace')))

    def test_grafico_detalle_y_respaldo(self):
        frame=datos().iloc[:1].copy()
        frame['Factor_Aplicacion_Automatica']=frame['Factor_Ajuste_Calculado']
        frame['Factor_Aplicacion_Reportes']=1.
        frame['Modo_Aplicacion']='FORZADO_1'
        frame['Flag_Factor_Ajuste_Valido']=1
        frame['Regla_Aplicacion']='FORZADO_1_USUARIO'
        frame['Regla_Aplicacion_Automatica']='APLICA_AJUSTE_VALIDADO'
        with patch.object(db,'obtener_factor_camiones',return_value=frame) as read:
            fig,records,_=panel.actualizar_factor('2026-09-07','2026-09-07',0,1)
            read.assert_called_once()
        self.assertEqual(len(fig.data),6)
        self.assertEqual(fig.data[5].name,'FORZADO_1')
        self.assertEqual(fig.data[3].y[0],frame.iloc[0]['Factor_Ajuste_Calculado'])
        self.assertEqual(fig.data[4].y[0],1)
        self.assertEqual(fig.layout.shapes[-1].type,'rect')
        self.assertEqual(fig.layout.shapes[-1].layer,'below')
        self.assertEqual(fig.data[0].customdata[0][8],'FORZADO_1')
        self.assertFalse(panel.es_respaldo(records[0]))
        self.assertTrue(panel.es_respaldo({**records[0],'Regla_Aplicacion_Automatica':'FALLBACK_SIN_DATOS_CAMIONES'}))
        detail=str(panel.detalle_dia(records))
        for label in ('Factor calculado','Factor automático','Factor aplicado','Modo de aplicación','FORZADO_1','ID control manual','—'):
            self.assertIn(label,detail)

    def test_callback_modos_y_cancelacion(self):
        with self.app.test_request_context(),patch.object(db,'obtener_version_override_rango',return_value=None),patch.object(db,'registrar_override_factor') as write:
            session['user']='especialista'
            for action,mode in [('forzar','FORZADO_1'),('automatico','AUTOMATICO')]:
                context=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':ui.PREFIX+action+'.n_clicks'}]))
                try:
                    result=ui.gestionar(1,1,0,0,'2026-09-07','2026-09-07','Motivo',None,False,0)
                    self.assertTrue(result[0]); self.assertEqual(session[ui.SESSION_KEY]['modo'],mode)
                finally: context_value.reset(context)
            context=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':ui.PREFIX+'cancelar.n_clicks'}]))
            try:
                result=ui.gestionar(1,1,1,0,None,None,None,None,False,0)
                self.assertFalse(result[0]); self.assertNotIn(ui.SESSION_KEY,session)
            finally: context_value.reset(context)
            write.assert_not_called()


if __name__=='__main__': unittest.main()
