"""Activación abierta, rango cerrado y cierre vigente sin SQL real."""
from datetime import date
import unittest
from unittest.mock import patch

import pandas as pd
from flask import Flask, session

from . import db, gestion
from .test_gestion import estado, preview, trigger


class ModalidadesTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'modalidades-test'

    def test_abierta_registra_solo_activar_y_tum_faltante(self):
        frame = preview(tum=False).assign(fecha_operacional='2026-09-17', turno='A')
        with self.app.test_request_context('/'), \
             patch.object(db, 'obtener_estado_actual', return_value=estado(False)), \
             patch.object(db, 'obtener_ultimo_periodo_materializable', return_value=(date(2026,9,17),'A')), \
             patch.object(db, 'obtener_preview_rango', return_value=frame), \
             patch.object(db, 'registrar_contingencia', return_value=dict(
                 inicio=date(2026,9,17),fin=date(2026,9,17),pendientes_tum=list(db.EQUIPOS))) as puntual, \
             patch.object(db, 'registrar_contingencia_rango') as rango:
            session['user'] = 'especialista'
            with trigger('pitum-gestion-activar'):
                abierto = gestion.gestionar(1,0,0,0,'2026-09-17','A',None,None)
            self.assertTrue(abierto[0])
            self.assertEqual(abierto[13], 'ABIERTA')
            self.assertEqual(abierto[11:13], ('2026-09-17','A'))
            self.assertEqual(gestion.estilo_modalidad('ABIERTA',True,'2026-09-17','A')[2:],
                             (None,None))
            self.assertEqual(gestion.estilo_modalidad('RANGO_CERRADO',True,'2026-09-17','A')[2:],
                             ('2026-09-17','A'))
            puntual.assert_not_called()
            contenido, validado = gestion.previsualizar_rango(
                '2026-09-17','A',None,None,True,{'display':'block'},'ABIERTA')
            self.assertIn('Hasta nuevo aviso', str(contenido))
            self.assertIn('Pendiente de TUM', str(contenido))
            self.assertNotIn('Vuelve a PI desde', str(contenido))
            self.assertFalse(gestion.confirmar_deshabilitado(True,'CAIDA_PI',{'display':'block'},
                None,'2026-09-17','A',None,None,validado,'ABIERTA') )
            with trigger('pitum-gestion-guardar'):
                guardado = gestion.gestionar(1,0,0,1,'2026-09-17','A','CAIDA_PI',None,
                    '2026-09-17','A',None,None,validado,'ABIERTA')
            self.assertFalse(guardado[0])
            puntual.assert_called_once_with('2026-09-17','A','ACTIVAR_CONTINGENCIA',
                                            'CAIDA_PI',None,'especialista',0)
            rango.assert_not_called()
            self.assertIn('Permanecerá activa',str(guardado[5]))

    def test_rango_cerrado_conserva_cierre_siguiente(self):
        self.assertEqual(db.turno_siguiente('2026-09-11','B'),(date(2026,9,12),'A'))
        with self.app.test_request_context('/'), \
             patch.object(db,'obtener_estado_actual',return_value=estado(False)), \
             patch.object(db,'obtener_ultimo_periodo_materializable',return_value=(date(2026,9,17),'B')), \
             patch.object(db,'registrar_contingencia_rango',return_value=dict(
                 inicio=date(2026,9,7),fin=date(2026,9,11),fecha_cierre=date(2026,9,12),
                 turno_cierre='A',pendientes_tum=[])) as rango, \
             patch.object(db,'registrar_contingencia') as puntual:
            session['user']='especialista'
            with trigger('pitum-gestion-activar'):
                gestion.gestionar(1,0,0,0,'2026-09-07','B',None,None)
            validado={'periodo':['2026-09-07','B','2026-09-11','B']}
            with trigger('pitum-gestion-guardar'):
                resultado=gestion.gestionar(1,0,0,1,'2026-09-07','B','CAIDA_PI',None,
                    '2026-09-07','B','2026-09-11','B',validado,'RANGO_CERRADO')
            rango.assert_called_once_with('2026-09-07','B','2026-09-11','B',
                                           'CAIDA_PI',None,'especialista')
            puntual.assert_not_called()
            self.assertIn('12-09-2026',str(resultado[5]))

    def test_botones_dependen_del_vigente_y_no_del_historico(self):
        for vigente,historico in [(True,False),(False,True)]:
            with self.subTest(vigente=vigente), self.app.test_request_context('/'), \
                 patch.object(db,'obtener_estado_actual',return_value=estado(vigente)), \
                 patch.object(db,'obtener_estado_contingencia',return_value=estado(historico)), \
                 patch.object(db,'obtener_preview_turno',return_value=preview()), \
                 patch.object(db,'obtener_historial_contingencias',return_value=pd.DataFrame()), \
                 patch.object(db,'obtener_apilado',return_value=pd.DataFrame()):
                session['user']='especialista'
                result=gestion.cargar('2026-09-10','A',None,0,'pitum-gestion')
                self.assertEqual(result[4]['display'],'none' if vigente else 'inline-block')
                self.assertEqual(result[5]['display'],'inline-block' if vigente else 'none')

    def test_cierre_usa_primer_turno_pi_y_rechaza_anterior(self):
        vigente=estado(True)
        vigente['fecha_accion_vigente']=date(2026,9,17)
        with self.app.test_request_context('/'), \
             patch.object(db,'obtener_estado_actual',return_value=vigente), \
             patch.object(db,'obtener_ultimo_periodo_materializable',return_value=(date(2026,9,18),'B')), \
             patch.object(db,'registrar_contingencia',return_value=dict(
                 inicio=date(2026,9,17),fin=date(2026,9,18),pendientes_tum=[])) as escribir:
            session['user']='especialista'
            with trigger('pitum-gestion-cerrar'):
                abierto=gestion.gestionar(0,1,0,0,'2026-09-10','A',None,None)
            self.assertEqual(abierto[15:17],('2026-09-18','B'))
            self.assertFalse(gestion.confirmar_deshabilitado(True,None,{'display':'none'},
                None,None,None,None,None,None,'ABIERTA','2026-09-18','B',['2026-09-17','A']))
            with trigger('pitum-gestion-guardar'):
                rechazado=gestion.gestionar(0,1,0,1,None,None,None,None,
                    modalidad='ABIERTA',cierre_fecha='2026-09-16',cierre_turno='B')
            self.assertIn('anterior',str(rechazado[9]))
            escribir.assert_not_called()
            with trigger('pitum-gestion-guardar'):
                cerrado=gestion.gestionar(0,1,0,1,None,None,None,None,
                    modalidad='ABIERTA',cierre_fecha='2026-09-18',cierre_turno='B')
            escribir.assert_called_once_with('2026-09-18','B','CERRAR_CONTINGENCIA',
                                             None,None,'especialista',7)
            self.assertIn('18-09-2026 · Turno B',str(cerrado[5]))

    def test_cierre_bloquea_cambio_concurrente(self):
        vigente=estado(True)
        vigente['fecha_accion_vigente']=date(2026,9,17)
        with self.app.test_request_context('/'), \
             patch.object(db,'obtener_ultimo_periodo_materializable',return_value=(date(2026,9,18),'B')), \
             patch.object(db,'registrar_contingencia') as escribir:
            session['user']='especialista'
            with patch.object(db,'obtener_estado_actual',return_value=vigente), \
                 trigger('pitum-gestion-cerrar'):
                gestion.gestionar(0,1,0,0,'2026-09-10','A',None,None)
            cambiado=dict(vigente, accion_vigente_id=8)
            with patch.object(db,'obtener_estado_actual',return_value=cambiado), \
                 trigger('pitum-gestion-guardar'):
                respuesta=gestion.gestionar(0,1,0,1,None,None,None,None,
                    modalidad='ABIERTA',cierre_fecha='2026-09-18',cierre_turno='B')
            self.assertIn('El estado cambió',str(respuesta[9]))
            escribir.assert_not_called()

    def test_inicio_futuro_bloqueado_sin_escritura(self):
        with self.app.test_request_context('/'), \
             patch.object(db,'obtener_estado_actual',return_value=estado(False)), \
             patch.object(db,'obtener_ultimo_periodo_materializable',return_value=(date(2026,9,16),'B')), \
             patch.object(db,'registrar_contingencia') as escribir:
            session['user']='especialista'
            with trigger('pitum-gestion-activar'):
                respuesta=gestion.gestionar(1,0,0,0,'2026-09-17','A',None,None)
            self.assertIn('no materializable',str(respuesta[9]))
            escribir.assert_not_called()

    def test_fin_de_rango_no_supera_periodo_materializable(self):
        with patch.object(db,'obtener_ultimo_periodo_materializable',
                          return_value=(date(2026,9,16),'B')), \
             patch.object(db,'obtener_preview_rango') as consultar:
            contenido,validado=gestion.previsualizar_rango(
                '2026-09-15','A','2026-09-17','A',True,{'display':'block'},'RANGO_CERRADO')
            self.assertIn('último período materializable',str(contenido))
            self.assertIsNone(validado)
            consultar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
