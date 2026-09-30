import inspect
import unittest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
from flask import Flask, session
from dash._callback_context import context_value
from dash._utils import AttributeDict
from . import db, limites_camiones_panel as ui, factor_camiones_panel as panel


def historial():
    return pd.DataFrame([dict(flota=f,valor=v,vigencia_desde=date(2026,7,1),vigencia_hasta=None,
        activo=True,motivo='Inicial',usuario_registro='operador',fecha_registro=date(2026,7,1)) for f,v in [('KOM',380),('CAT',265)]])


class LimitesTests(unittest.TestCase):
    def setUp(self):
        self.app=Flask(__name__)
        self.app.secret_key='test-only'

    def test_validaciones(self):
        valid=dict(flota='KOM',valor=380,vigencia_desde='2026-09-20',motivo='Cambio',usuario='especialista')
        for field,value in [('flota',None),('flota','XXX'),('valor',0),('valor',-1),('valor','NaN'),('valor',float('inf')),
                            ('vigencia_desde',None),('motivo','   '),('usuario',None),('valor','1.0000001')]:
            with self.subTest(field=field,value=value), self.assertRaises(ValueError):
                db.validar_limite_factor(**{**valid,field:value})

    def test_vigencias_presentacion(self):
        row=historial().iloc[0].to_dict()
        row['vigencia_hasta']=date(2026,10,5)
        self.assertEqual(ui.estado_vigencia(row,date(2026,10,4)),'VIGENTE')
        self.assertEqual(ui.estado_vigencia(row,date(2026,10,5)),'HISTÓRICO')
        row['vigencia_desde']=date(2026,10,5)
        row['vigencia_hasta']=None
        self.assertEqual(ui.estado_vigencia(row,date(2026,10,4)),'FUTURO')
        h=historial()
        h.loc[0,'vigencia_hasta']=date(2026,10,5)
        output=str(ui.mostrar_historial(h,date(2026,9,28)))
        self.assertIn('Hasta 04-10-2026',output)
        self.assertIn('Hasta nuevo aviso',output)
        self.assertEqual(ui.numero(None),'—')
        self.assertEqual(ui.numero(43547),'43.547,00')

    def test_confirmacion_y_usuario_no_manipulable(self):
        with self.app.test_request_context(), patch.object(db,'obtener_limites_factor_vigentes',return_value=historial()), patch.object(db,'registrar_limite_factor') as write:
            session['user']='operador_real'
            token,description,retro=ui.preparar_confirmacion('KOM',350,(date.today()+timedelta(days=30)).isoformat(),'Cambio futuro')
            self.assertFalse(retro)
            self.assertIn('CAMBIO PROGRAMADO',str(description))
            write.assert_not_called()
            self.assertFalse(ui.habilitar_confirmacion(token,False)[0])
            write.return_value=dict(Fecha_Inicio_Afectada=date.today()+timedelta(days=30),Fecha_Fin_Afectada=date.today(),Es_Retroactivo=False)
            result=ui.confirmar_registro(token,False)
            self.assertIn('PROGRAMADO',str(result))
            self.assertEqual(write.call_args.kwargs['usuario'],'operador_real')
            self.assertEqual(write.call_count,1)
            with self.assertRaises(ValueError): ui.confirmar_registro(token,False)
            self.assertEqual(write.call_count,1)

    def test_retroactivo_y_hoy(self):
        with self.app.test_request_context(), patch.object(db,'obtener_limites_factor_vigentes',return_value=historial()), patch.object(db,'registrar_limite_factor') as write:
            session['user']='especialista'
            day=(date.today()-timedelta(days=5)).isoformat()
            token,description,retro=ui.preparar_confirmacion('KOM',350,day,'Retroactivo')
            self.assertTrue(retro)
            self.assertIn('CAMBIO RETROACTIVO',str(description))
            self.assertTrue(ui.habilitar_confirmacion(token,False)[0])
            with self.assertRaises(ValueError): ui.confirmar_registro(token,False)
            write.assert_not_called()
            token,_,_=ui.preparar_confirmacion('KOM',350,day,'Retroactivo')
            write.return_value=dict(Fecha_Inicio_Afectada=day,Fecha_Fin_Afectada=date.today(),Es_Retroactivo=True)
            self.assertIn('PENDIENTE DE REPROCESO',str(ui.confirmar_registro(token,True)))
            _,description,retro=ui.preparar_confirmacion('CAT',250,date.today().isoformat(),'Hoy')
            self.assertFalse(retro)
            self.assertIn('CAMBIO VIGENTE DESDE HOY',str(description))

    def test_sin_usuario_y_token_invalido(self):
        with self.app.test_request_context(), patch.object(db,'registrar_limite_factor') as write:
            with self.assertRaises(ValueError): ui.preparar_confirmacion('KOM',350,'2026-09-20','Motivo')
            with self.assertRaises(ValueError): ui.confirmar_registro('inventado',True)
            write.assert_not_called()

    def test_refresco_configuracion_y_futuro(self):
        h=historial()
        future=h.iloc[[0]].copy()
        future['valor']=350
        future['vigencia_desde']=date.today()+timedelta(days=30)
        with patch.object(db,'obtener_historial_limites_factor',return_value=pd.concat([h,future])), patch.object(db,'obtener_limites_factor_vigentes',return_value=h) as resolve, patch.object(db,'obtener_pendientes_limites_factor',return_value=pd.DataFrame()), patch.object(db,'obtener_factor_camiones') as factor:
            cards,next_changes,_,_,_=ui.refrescar_configuracion(date.today().isoformat(),1)
            self.assertIn('380,00',str(cards)); self.assertIn('265,00',str(cards))
            self.assertNotIn('350,00',str(cards)); self.assertIn('350,00',str(next_changes))
            factor.assert_not_called()
            resolve.assert_called_once_with(date.today().isoformat())

    def test_db_unico_exec_guard_y_sin_reproceso(self):
        engine=MagicMock()
        conn=engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.mappings.return_value.one.return_value={'Es_Retroactivo':True}
        with patch.object(db,'_engine_dev',return_value=engine), patch.object(db,'_assert_dev_connection') as guard:
            db.registrar_limite_factor('KOM',350,'2026-09-20','Cambio','autenticado')
            guard.assert_called_once_with(conn)
            self.assertEqual(conn.execute.call_count,1)
            query=str(conn.execute.call_args.args[0])
            self.assertIn('EXEC inventar_SpcHidr.sp_registrar_limite_factor_camiones_vigencia_test',query)
            for word in ('INSERT','UPDATE','DELETE','sp_mantiene','sp_factor_ajuste','publicar'):
                self.assertNotIn(word,query)
        with patch.object(db,'_engine_dev',return_value=engine), patch.object(db,'_assert_dev_connection',side_effect=RuntimeError('guard')):
            conn.execute.reset_mock()
            with self.assertRaises(RuntimeError): db.registrar_limite_factor('KOM',350,'2026-09-20','Cambio','autenticado')
            conn.execute.assert_not_called()

    def test_detalle_persistido_vs_configuracion(self):
        fila=dict(Fecha='2026-09-22',Limite_KOM_TMH_Viaje=380,Limite_CAT_TMH_Viaje=265,
                  Carga_KOM_TMH_Viaje_Sin_Ajuste=463.56,Factor_Ajuste_Calculado=None)
        token=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-limites-pendientes-datos.data'}]))
        try:
            detail=panel.actualizar_detalle([fila],None,[dict(Fecha='2026-09-22',flota='KOM',limite_configurado=350,limite_utilizado=380)])
            output=str(detail)
            for fragment in ('22-09-2026','380,00','265,00','350,00','PENDIENTE DE REPROCESO','EXCEDE LÍMITE','—','Balance de Chancado','Trazabilidad Técnica'):
                self.assertIn(fragment,output)
            self.assertEqual(fila['Limite_KOM_TMH_Viaje'],380)
        finally: context_value.reset(token)

    def test_callback_confirmar_refresca_solo_version(self):
        with self.app.test_request_context(), patch.object(db,'obtener_limites_factor_vigentes',return_value=historial()), patch.object(db,'registrar_limite_factor',return_value=dict(Fecha_Inicio_Afectada='2026-09-20',Fecha_Fin_Afectada='2026-09-22')) as write:
            session['user']='especialista'
            token,_,_=ui.preparar_confirmacion('KOM',350,'2026-09-20','Motivo')
            context=context_value.set(AttributeDict(triggered_inputs=[{'prop_id':'pitum-limites-confirmar.n_clicks'}]))
            try:
                result=ui.gestionar(1,0,1,'CAT',999,'2026-09-21','modificado',token,True,0)
                self.assertEqual(result[-1],1)
                self.assertEqual(write.call_args.kwargs['flota'],'KOM')
                self.assertEqual(write.call_args.kwargs['valor'],'350')
            finally: context_value.reset(context)

    def test_pendientes_compara_limites_en_decimal(self):
        engine=MagicMock()
        conn=engine.connect.return_value.__enter__.return_value
        with patch.object(db,'_engine_dev',return_value=engine), patch.object(
                db.pd,'read_sql',return_value=pd.DataFrame()) as read:
            db.obtener_pendientes_limites_factor()
            sql=str(read.call_args.args[0])
            self.assertIn('decimal(18,6)',sql.lower())
            self.assertNotIn('CAST(p.valor AS float)',sql)

    def test_token_invalido_no_consume_confirmacion_vigente(self):
        with self.app.test_request_context(), patch.object(
                db,'obtener_limites_factor_vigentes',return_value=historial()), patch.object(
                db,'registrar_limite_factor',return_value=dict(
                    Fecha_Inicio_Afectada=date.today()+timedelta(days=30),
                    Fecha_Fin_Afectada=date.today())) as write:
            session['user']='especialista'
            token,_,_=ui.preparar_confirmacion(
                'KOM',350,(date.today()+timedelta(days=30)).isoformat(),'Cambio futuro')
            with self.assertRaisesRegex(ValueError,'confirmación no está vigente'):
                ui.confirmar_registro('token-obsoleto',False)
            self.assertEqual(session['pitum_limites_confirmacion']['token'],token)
            ui.confirmar_registro(token,False)
            self.assertEqual(write.call_count,1)

    def test_confirmacion_obsoleta_se_rechaza_si_cambio_configuracion(self):
        original=historial()
        changed=historial()
        changed.loc[changed.flota=='KOM','valor']=360
        with self.app.test_request_context(), patch.object(
                db,'obtener_limites_factor_vigentes',side_effect=[original,changed]), patch.object(
                db,'registrar_limite_factor') as write:
            session['user']='especialista'
            token,_,_=ui.preparar_confirmacion(
                'KOM',350,(date.today()+timedelta(days=30)).isoformat(),'Cambio futuro')
            with self.assertRaisesRegex(ValueError,'configuración cambió desde la revisión'):
                ui.confirmar_registro(token,False)
            write.assert_not_called()


    def test_error_controlado(self):
        self.assertIn('Ya existe',ui.mensaje_error(RuntimeError('SQL 51015 secret')))
        self.assertNotIn('secret',ui.mensaje_error(RuntimeError('SQL secret stack trace')))


if __name__=='__main__': unittest.main()
