"""Regresión de gestión por acciones, identidad y transacción, sin SQL real."""
from contextlib import contextmanager
from datetime import date
from collections import Counter
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from flask import Flask, session
from dash import Dash, no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict
from . import db, gestion, panel
OBTENER_ESTADO_ACTUAL_REAL = db.obtener_estado_actual

RANGO = ('2026-09-10','B','2026-09-10','B',
         {'periodo':['2026-09-10','B','2026-09-10','B']})


def confirmar_ui(abierto,motivo,estilo,comentario=None):
    return gestion.confirmar_deshabilitado(abierto,motivo,estilo,comentario,*RANGO)


@contextmanager
def trigger(nombre):
    token = context_value.set(AttributeDict(triggered_inputs=[{'prop_id':nombre+'.n_clicks'}]))
    try:
        yield
    finally:
        context_value.reset(token)


def estado(activa=False):
    return dict(contingencia_pi_activa=activa, accion_vigente_id=7 if activa else None,
                fecha_accion_vigente=date(2026,9,10),turno_accion_vigente='A',
                motivo_contingencia='CAIDA_PI',usuario_estado_operacional='especialista',
                fecha_registro_estado_operacional='2026-09-15 10:00')


def preview(tum=True, activa=False):
    return pd.DataFrame([dict(equipo_codigo=e,estado_tecnico_pi='CON_VARIACION',
        valor_pi_final=0, pi_disponible_operacional=1, valor_turno_tum=21774 if tum else None,
        tum_disponible_operacional=int(tum), fuente_resuelta=('TUM' if tum else 'PENDIENTE_TUM') if activa else 'PI',
        valor_final_resuelto=(21774 if tum else None) if activa else 0) for e in db.EQUIPOS])


class GestionTests(unittest.TestCase):
    def test_proyeccion_tabla_compacta_orden_valores_y_estados(self):
        frame=preview()
        frame['tum_disponible_operacional']=frame['tum_disponible_operacional'].astype(object)
        frame.loc[0,'valor_turno_tum']=0
        frame.loc[1,['valor_turno_tum','tum_disponible_operacional']]=[None,False]
        frame.loc[2,['valor_turno_tum','tum_disponible_operacional']]=[None,None]
        original=frame.copy(deep=True)
        for modal in (False,True):
            result=gestion.presentar_preview(frame.iloc[::-1],False,modal=modal)
            tabla=result.children[2]
            self.assertTrue(tabla.responsive)
            self.assertEqual(tabla.size,'sm')
            self.assertEqual([c.children for c in tabla.children[0].children.children],
                             ['Equipo','Fuente si activa','Valor TUM','Estado esperado'])
            filas=[[c.children for c in r.children] for r in tabla.children[1].children]
            self.assertEqual(len(filas),7)
            self.assertEqual([r[0] for r in filas],
                             ['CV006','CV008','CV108','SRR CV001','SRR CV002','SRR CV003','CV025'])
            self.assertEqual([r[1] for r in filas],['TUM']*7)
            self.assertEqual(filas[0][2:],['0 t','Resuelto'])
            self.assertEqual(filas[1][2:],['—','Pendiente de TUM'])
            self.assertEqual(filas[2][2:],['—','Sin información'])
            self.assertEqual(filas[3][2:],['21.774 t','Resuelto'])
            self.assertNotIn('Si activa la contingencia',str(gestion.presentar_preview(frame,True,modal=modal)))
        pd.testing.assert_frame_equal(frame,original)

    @staticmethod
    def _fila(tabla, equipo='CV008'):
        return next(row.children for row in tabla.children[1].children
                    if isinstance(row.children, list)
                    and row.children[0].children == equipo)
    def setUp(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'prueba-local'
        for nombre, valor in [('_ultimo_periodo_materializable',(date(2026,9,17),'B')),
                              ('obtener_ultimo_periodo_materializable',(date(2026,9,17),'B')),
                              ('obtener_estado_actual',estado(False))]:
            p=patch.object(db,nombre,return_value=valor)
            p.start()
            self.addCleanup(p.stop)

    def test_normal_y_activa_siete_equipos(self):
        for activa in (False,True):
            with self.subTest(activa=activa), self.app.test_request_context('/'), \
                 patch.object(db,'obtener_estado_contingencia',return_value=estado(activa)), \
                 patch.object(db,'obtener_estado_actual',return_value=estado(activa)), \
                 patch.object(db,'obtener_preview_turno',return_value=preview(activa=activa)), \
                 patch.object(db,'obtener_historial_contingencias',return_value=pd.DataFrame()), \
                 patch.object(db,'obtener_apilado',return_value=pd.DataFrame()):
                session['user']='especialista'
                result=gestion.cargar('2026-09-10','A',None,0,'pitum-gestion')
                self.assertIn('Contingencia PI activa' if activa else 'Sin contingencia declarada',str(result[0]))
                self.assertEqual(result[0].children[0].title,'CONTINGENCIA_PI' if activa else 'NORMAL_PI')
                self.assertNotIn('NORMAL PI',str(result[0]))
                self.assertEqual(result[3].children,'Sin apilado materializado para esta fecha.')
                self.assertFalse(result[6])
                self.assertIn('CV008',str(result[1]))
                self.assertNotIn('PRINCIPAL_CV008',str(result[1]))
                self.assertIn('SRR_CV001',str(result[1]))
                self.assertIn('RIPIOS_CV025',str(result[1]))
                self.assertEqual(result[4]['display'],'none' if activa else 'inline-block')

    def test_confirmacion_usuario_y_fecha_congelada(self):
        for accion,activo,boton in [('ACTIVAR_CONTINGENCIA',False,'activar'),('CERRAR_CONTINGENCIA',True,'cerrar')]:
            with self.subTest(accion=accion), self.app.test_request_context('/'), \
                 patch.object(db,'obtener_estado_contingencia',return_value=estado(activo)), \
                 patch.object(db,'obtener_estado_actual',return_value=estado(activo)), \
                 patch.object(db,'obtener_preview_turno',return_value=preview(activa=activo)), \
                 patch.object(db,'registrar_contingencia_rango',return_value=dict(inicio='2026-09-10',fin='2026-09-10',pendientes_tum=[])) as escribir_rango, \
                 patch.object(db,'registrar_contingencia',return_value=dict(id=1,inicio='2026-09-10',fin='2026-09-15',pendientes_tum=[])) as escribir:
                session['user']='real'
                session['username']='ignorar'
                with trigger('pitum-gestion-'+boton):
                    opened=gestion.gestionar(1,1,0,0,'2026-09-10','B','OTRO','antiguo')
                self.assertTrue(opened[0])
                self.assertIsNone(opened[8])  # No inventa motivo
                self.assertTrue(confirmar_ui(opened[0],opened[8],opened[3]))
                if activo:
                    self.assertIn('2026-09-10',str(opened[18]))
                else:
                    self.assertEqual(opened[11:13],('2026-09-10','B'))
                escribir.assert_not_called()
                with trigger('pitum-gestion-guardar'):
                    saved=gestion.gestionar(1,1,0,1,'2026-10-01','A','CAIDA_PI','comentario',*RANGO,
                        'RANGO_CERRADO','2026-09-17','B')
                self.assertFalse(saved[0])
                if activo:
                    escribir.assert_called_once_with('2026-09-17','B',accion,None,'comentario','real',7)
                    escribir_rango.assert_not_called()
                else:
                    escribir_rango.assert_called_once_with(*RANGO[:4],'CAIDA_PI','comentario','real')
                    escribir.assert_not_called()
                self.assertNotIn('pitum_confirmacion',session)

    def test_sin_usuario_ni_confirmacion_no_escribe(self):
        with self.app.test_request_context('/'), patch.object(db,'registrar_contingencia') as escribir, trigger('pitum-gestion-guardar'):
            session['username']='historico'
            result=gestion.gestionar(0,0,0,1,'2026-09-10','A','CAIDA_PI',None)
            self.assertEqual(result[5].children,gestion.SIN_USUARIO)
            session['user']='real'
            result=gestion.gestionar(0,0,0,1,'2026-09-10','A','CAIDA_PI',None)
            self.assertIn('Abra la confirmación',str(result[5]))
            escribir.assert_not_called()

    def test_tum_ausente_advierte_sin_bloquear(self):
        result=gestion.presentar_preview(preview(tum=False),False)
        self.assertEqual(result.children[-1].children[1].children,gestion.ALERTA_TUM)
        self.assertIn('Pendiente de TUM',str(result))
        self.assertEqual(self._fila(result.children[0])[4].children,'—')
        with self.app.test_request_context('/'), trigger('pitum-gestion-guardar'), \
             patch.object(db,'registrar_contingencia_rango',return_value=dict(id=1,inicio='2026-09-10',fin='2026-09-15',pendientes_tum=list(db.EQUIPOS))) as escribir:
            session['user']='real'
            session['pitum_confirmacion']=dict(fecha='2026-09-10',turno='A',accion='ACTIVAR_CONTINGENCIA',usuario='real',esperada=0)
            result=gestion.gestionar(0,0,0,1,None,None,'CAIDA_PI',None,*RANGO)
            escribir.assert_called_once()
            self.assertIn('pendientes de Informe TUM',str(result[5]))

    def test_cutover_motivo_y_usuario_antes_de_conectar(self):
        with patch.object(db,'_engine_dev') as engine:
            for fecha,motivo,usuario in [('2026-08-31','CAIDA_PI','real'),('2026-09-10',None,'real'),('2026-09-10','OTRO','')]:
                with self.assertRaises(ValueError):
                    db.registrar_contingencia(fecha,'A','ACTIVAR_CONTINGENCIA',motivo,None,usuario)
            engine.assert_not_called()

    def test_una_transaccion_y_rollback_al_fallar_reproceso(self):
        for falla in (False,True):
            with self.subTest(falla=falla):
                engine=MagicMock()
                conn=engine.begin.return_value.__enter__.return_value
                conn.execute.return_value.scalar.return_value=0
                conn.execute.return_value.mappings.return_value.one.return_value={'id':8}
                with patch.object(db,'_engine_dev',return_value=engine), \
                     patch.object(db,'_assert_dev_connection'), \
                     patch.object(db,'_estado',return_value=estado(False)), \
                     patch.object(db,'_ultima_fecha_materializable',return_value=date(2026,9,15)), \
                     patch.object(db,'_preview',return_value=preview(True,True)), \
                     patch.object(db,'reprocesar_apilado',side_effect=RuntimeError('fallo') if falla else None) as reproceso:
                    if falla:
                        with self.assertRaises(RuntimeError):
                            db.registrar_contingencia('2026-09-10','A','ACTIVAR_CONTINGENCIA','CAIDA_PI',None,'real')
                        self.assertIs(engine.begin.return_value.__exit__.call_args.args[0],RuntimeError)
                    else:
                        result=db.registrar_contingencia('2026-09-10','A','ACTIVAR_CONTINGENCIA','CAIDA_PI',None,'real')
                        self.assertEqual(result['id'],8)
                        self.assertIsNone(engine.begin.return_value.__exit__.call_args.args[0])
                    reproceso.assert_called_once_with(conn,date(2026,9,10),date(2026,9,15))
                    self.assertIn('sp_registrar_contingencia_pi_test',str(conn.execute.call_args_list[-1].args[0]))

    def test_cierre_reprocesa_desde_activacion_y_motivo_null(self):
        conn=MagicMock()
        conn.execute.return_value.scalar.return_value=0
        conn.execute.return_value.mappings.return_value.one.return_value={'id':9}
        with patch.object(db,'_estado',return_value=estado(True)), \
             patch.object(db,'_assert_dev_connection'), \
             patch.object(db,'_ultima_fecha_materializable',return_value=date(2026,9,15)), \
             patch.object(db,'_preview',return_value=preview()), patch.object(db,'reprocesar_apilado') as reproceso:
            db._registrar_y_reprocesar(conn,'2026-09-12','B','CERRAR_CONTINGENCIA','IGNORAR',None,'real',7)
            reproceso.assert_called_once_with(conn,date(2026,9,10),date(2026,9,15))
            self.assertIsNone(conn.execute.call_args_list[-1].args[1]['motivo'])

    def test_transicion_repetida_o_cambio_concurrente_no_inserta(self):
        conn=MagicMock()
        conn.execute.return_value.scalar.return_value=0
        with patch.object(db,'_estado',return_value=estado(True)), patch.object(db,'_assert_dev_connection'), patch.object(db,'reprocesar_apilado') as reproceso:
            with self.assertRaises(ValueError):
                db._registrar_y_reprocesar(conn,'2026-09-10','A','ACTIVAR_CONTINGENCIA','OTRO',None,'real',0)
            reproceso.assert_not_called()
            self.assertEqual(conn.execute.call_count,1)  # solo applock

    def test_historial_solo_lectura_y_orden(self):
        engine=MagicMock()
        with patch.object(db,'_engine_dev',return_value=engine),patch.object(db.pd,'read_sql',return_value=pd.DataFrame()) as read:
            db.obtener_historial_contingencias()
            sql=str(read.call_args.args[0])
            self.assertIn('ORDER BY fecha_registro DESC,id DESC',sql)
            self.assertNotIn('UPDATE',sql)
        table=gestion._tabla(pd.DataFrame([{'accion':'ACTIVAR_CONTINGENCIA'}]),[('accion','Acción')])
        self.assertFalse(table.editable)
        self.assertFalse(table.row_deletable)

    def test_error_controlado_y_refresco(self):
        with self.app.test_request_context('/'), trigger('pitum-gestion-guardar'), \
             patch.object(db,'registrar_contingencia_rango',side_effect=RuntimeError('detalle SQL privado')):
            session['user']='real'
            session['pitum_confirmacion']=dict(fecha='2026-09-10',turno='A',accion='ACTIVAR_CONTINGENCIA',usuario='real',esperada=0)
            with self.assertLogs(gestion.log,level='ERROR'):
                result=gestion.gestionar(0,0,0,1,None,None,'OTRO',None,*RANGO)
            self.assertNotIn('detalle SQL',str(result))
            self.assertIsNot(result[6],no_update)

    def test_dash_http_e_ids_outputs(self):
        app=Dash(__name__,suppress_callback_exceptions=True)
        app.layout=panel.layout()
        client=app.server.test_client()
        response=client.get('/_dash-layout')
        self.assertEqual(response.status_code,200)
        ids=[]
        def recorrer(node):
            if isinstance(node,list):
                for item in node:
                    recorrer(item)
            elif isinstance(node,dict):
                props=node.get('props',{})
                if 'id' in props:
                    ids.append(props['id'])
                recorrer(props.get('children'))
        recorrer(response.get_json())
        self.assertEqual([k for k,n in Counter(ids).items() if n>1],[])
        self.assertIn('Consulta de período',str(response.get_json()))
        self.assertIn('Este selector solo consulta información',str(response.get_json()))
        self.assertIn('El rango seleccionado define los turnos',str(response.get_json()))
        self.assertNotIn("'label': 'Operativo'",str(response.get_json()))
        self.assertIn('Monitoreo Correas Área Seca',str(response.get_json()))
        outputs=[]
        for item in app._callback_list:
            parts=item['output'].strip('.').split('...')
            outputs.extend(p for p in parts if p.startswith('pitum-'))
        self.assertEqual([k for k,n in Counter(outputs).items() if n>1],[])
        guardar=next(item for item in app._callback_list if 'pitum-gestion-modal.is_open' in item['output'])
        self.assertTrue(guardar['running']['running']['pitum-gestion-acciones.disabled'])
        self.assertFalse(guardar['running']['runningOff']['pitum-gestion-acciones.disabled'])
        # Un único escritor por propiedad, incluyendo outputs temporales de running.
        temporales=[key for item in app._callback_list
                    for key in item.get('running',{}).get('running',{}) if key.startswith('pitum-')]
        self.assertEqual([k for k,n in Counter(outputs+temporales).items() if n>1],[])
        frame=preview()
        with patch.object(db,'registrar_contingencia_rango') as escribir_rango, \
             patch.object(db,'registrar_contingencia') as escribir, \
             patch.object(db,'obtener_estado_contingencia',return_value=estado()), \
             patch.object(db,'obtener_estado_actual',return_value=estado()), \
             patch.object(db,'obtener_preview_turno',return_value=frame), \
             patch.object(db,'obtener_historial_contingencias',return_value=pd.DataFrame()), \
             patch.object(db,'obtener_apilado',return_value=pd.DataFrame()):
            key=next(k for k in app.callback_map if 'pitum-gestion-estado.children' in k)
            outs=[dict(id=o.component_id,property=o.component_property) for o in app.callback_map[key]['output']]
            response=client.post('/_dash-update-component',json={'output':key,'outputs':outs,'inputs':[
                dict(id='pitum-gestion-fecha',property='date',value='2026-09-10'),
                dict(id='pitum-gestion-turno',property='value',value='A'),
                dict(id='pitum-gestion-version',property='data',value=None),
                dict(id='pitum-gestion-refrescar',property='n_clicks',value=0),
                dict(id='pitum-tabs',property='active_tab',value='pitum-gestion')],
                'state':[],'changedPropIds':['pitum-tabs.active_tab']})
            self.assertEqual(response.status_code,200,response.get_data(as_text=True))

        app.server.secret_key='prueba-ui'
        with client.session_transaction() as sesion:
            sesion['user']='especialista'
        for motivo,oculto,esperado in [(None,False,True),('',False,True),
                ('INVALIDO',False,True),*[(m,False,m=='OTRO') for m in db.MOTIVOS],(None,True,True)]:
            with self.subTest(motivo=motivo,cierre=oculto):
                response=client.post('/_dash-update-component',json={
                    'output':'pitum-gestion-guardar.disabled',
                    'outputs':dict(id='pitum-gestion-guardar',property='disabled'),
                    'inputs':[
                        dict(id='pitum-gestion-modal',property='is_open',value=True),
                        dict(id='pitum-gestion-motivo',property='value',value=motivo),
                        dict(id='pitum-gestion-motivo-bloque',property='style',value={'display':'none' if oculto else 'block'}),
                        dict(id='pitum-gestion-comentario',property='value',value=None),
                        dict(id='pitum-rango-inicio',property='date',value=RANGO[0]),
                        dict(id='pitum-rango-turno-inicio',property='value',value=RANGO[1]),
                        dict(id='pitum-rango-fin',property='date',value=RANGO[2]),
                        dict(id='pitum-rango-turno-fin',property='value',value=RANGO[3]),
                        dict(id='pitum-rango-validado',property='data',value=RANGO[4]),
                        dict(id='pitum-modalidad',property='value',value='RANGO_CERRADO'),
                        dict(id='pitum-cierre-fecha',property='date',value=None),
                        dict(id='pitum-cierre-turno',property='value',value='A')],
                    'state':[dict(id='pitum-gestion-cierre-desde',property='data',value=None)],
                    'changedPropIds':['pitum-gestion-motivo.value']})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.get_json()['response']['pitum-gestion-guardar']['disabled'],esperado)

        key=next(k for k in app.callback_map if 'pitum-rango-preview.children' in k)
        outs=[dict(id=o.component_id,property=o.component_property) for o in app.callback_map[key]['output']]
        with patch.object(db,'obtener_preview_rango',return_value=pd.DataFrame()):
            response=client.post('/_dash-update-component',json={
                'output':key,'outputs':outs,'inputs':[
                    dict(id='pitum-rango-inicio',property='date',value='2026-09-15'),
                    dict(id='pitum-rango-turno-inicio',property='value',value='A'),
                    dict(id='pitum-rango-fin',property='date',value='2026-09-17'),
                    dict(id='pitum-rango-turno-fin',property='value',value='B'),
                    dict(id='pitum-gestion-modal',property='is_open',value=True),
                    dict(id='pitum-rango-bloque',property='style',value={'display':'block'}),
                    dict(id='pitum-modalidad',property='value',value='RANGO_CERRADO')],
                'state':[],'changedPropIds':['pitum-rango-fin.date']})
            self.assertEqual(response.status_code,200,response.get_data(as_text=True))
            escribir_rango.assert_not_called()
            escribir.assert_not_called()
            self.assertIn('Turnos afectados: 6',response.get_data(as_text=True))
            self.assertEqual(response.get_json()['response']['pitum-rango-validado']['data']['periodo'],
                             ['2026-09-15','A','2026-09-17','B'])

    def test_confirmacion_muestra_tum_faltante_sin_bloquear(self):
        with self.app.test_request_context('/'), trigger('pitum-gestion-activar'), \
             patch.object(db,'obtener_estado_contingencia',return_value=estado()), \
             patch.object(db,'obtener_preview_rango',return_value=preview(tum=False).assign(fecha_operacional='2026-09-10',turno='A')):
            session['user']='especialista'
            result=gestion.gestionar(1,0,0,0,'2026-09-10','A',None,None)
            self.assertTrue(result[0])
            contenido,validado=gestion.previsualizar_rango('2026-09-10','A','2026-09-10','A',True,{'display':'block'})
            self.assertIn('La contingencia puede registrarse',str(contenido))
            self.assertIn('CV008',str(contenido))
            self.assertIn('CV108',str(contenido))
            self.assertIsNotNone(validado)

    def test_validacion_visible_dentro_del_modal(self):
        with self.app.test_request_context('/'), trigger('pitum-gestion-guardar'), \
             patch.object(db,'_engine_dev') as engine:
            session['user']='especialista'
            session['pitum_confirmacion']=dict(fecha='2026-09-10',turno='A',
                accion='ACTIVAR_CONTINGENCIA',usuario='especialista',esperada=0)
            result=gestion.gestionar(1,0,0,1,'2026-09-10','A',None,None,*RANGO)
            self.assertIn('Seleccione el motivo',str(result[9]))
            engine.assert_not_called()

    def test_estado_vigente_separado_del_preview_historico(self):
        with self.app.test_request_context('/'), \
             patch.object(db,'obtener_estado_contingencia',return_value=estado(True)), \
             patch.object(db,'obtener_estado_actual',return_value=estado(False)), \
             patch.object(db,'obtener_preview_turno',return_value=preview(activa=True)), \
             patch.object(db,'obtener_historial_contingencias',return_value=pd.DataFrame()), \
             patch.object(db,'obtener_apilado',return_value=pd.DataFrame()):
            session['user']='especialista'
            result=gestion.cargar('2026-09-10','A',None,0,'pitum-gestion')
            self.assertIn('Contingencia PI activa',str(result[0]))
            self.assertIn('Sin contingencia declarada',str(result[8]))

    def test_estado_actual_usa_orden_operacional_sql(self):
        engine=MagicMock()
        conn=engine.connect.return_value.__enter__.return_value
        conn.execute.return_value.mappings.return_value.one.side_effect=[{'fecha':date(2026,9,16),'turno':'A'},estado()]
        with patch.object(db,'_engine_dev',return_value=engine), \
             patch.object(db,'obtener_estado_actual',OBTENER_ESTADO_ACTUAL_REAL):
            db.obtener_estado_actual()
        sql=str(conn.execute.call_args.args[0])
        self.assertIn('ORDER BY fecha_operacional DESC, turno DESC, fecha_registro DESC, id DESC',sql)
        self.assertEqual(conn.execute.call_args.args[1]['fecha'],date(2026,9,16))
        self.assertEqual(conn.execute.call_args.args[1]['turno'],'A')

    @patch.object(gestion,'_usuario',return_value='especialista')
    def test_modal_controles_motivos_y_usuario_solo_lectura(self, usuario):
        componentes={}
        def recorrer(node):
            if isinstance(node,(list,tuple)):
                for child in node:
                    recorrer(child)
            elif hasattr(node,'to_plotly_json'):
                if getattr(node,'id',None):
                    componentes[node.id]=node
                recorrer(getattr(node,'children',None))
        recorrer(gestion.layout())
        self.assertTrue(componentes['pitum-gestion-guardar'].disabled)
        self.assertEqual([button.id for button in componentes['pitum-gestion-acciones'].children],
                         ['pitum-gestion-cancelar','pitum-gestion-guardar'])
        self.assertEqual(componentes['pitum-gestion-modal'].size,'lg')
        self.assertTrue(componentes['pitum-gestion-modal'].scrollable)
        self.assertEqual(componentes['pitum-gestion-usuario'].to_plotly_json()['type'],'Strong')
        self.assertEqual(componentes['pitum-gestion-motivo'].options,[
            dict(value='CAIDA_PI',label='Caída PI System'),
            dict(value='MANTENCION',label='Mantención'),
            dict(value='COMUNICACIONES',label='Comunicaciones'),
            dict(value='SERVIDOR',label='Servidor'),dict(value='OTRO',label='Otro')])
        self.assertTrue(confirmar_ui(False,'OTRO',{'display':'block'}))
        self.assertTrue(confirmar_ui(True,None,{'display':'block'}))
        self.assertTrue(confirmar_ui(True,None,{'display':'none'}))

    def test_tonelajes_presentacion_sin_perder_cero_null_o_decimales(self):
        from decimal import Decimal
        for valor,esperado in [(21774,'21.774 t'),(19688.0,'19.688 t'),
                (19130,'19.130 t'),(0,'0 t'),(None,'—'),(float('nan'),'—'),
                (Decimal('1234.5600'),'1.234,56 t'),(Decimal('0.0001'),'0,0001 t')]:
            with self.subTest(valor=valor):
                self.assertEqual(gestion.formato_tonelaje(valor),esperado)

    @patch.object(gestion,'_usuario',return_value='especialista')
    def test_descripciones_exactas_y_comentario_obligatorio_solo_otro(self, usuario):
        esperadas = {
            'CAIDA_PI': 'Indisponibilidad general o pérdida de datos desde PI System.',
            'MANTENCION': 'Intervención planificada o conocida que afecta la disponibilidad o confiabilidad del dato.',
            'COMUNICACIONES': 'Falla de transmisión, enlace o red entre la fuente operacional y PI.',
            'SERVIDOR': 'Falla o indisponibilidad identificada en un servidor o servicio asociado.',
            'OTRO': 'Causa distinta a las anteriores. Debe especificarse en el comentario.',
        }
        self.assertEqual(set(esperadas),set(db.MOTIVOS))
        for motivo,descripcion in esperadas.items():
            with self.subTest(motivo=motivo):
                ayuda,label,required=gestion.ayuda_motivo(motivo,{'display':'block'})
                self.assertEqual(ayuda,descripcion)
                self.assertEqual(required,motivo=='OTRO')
                self.assertEqual(label,'Comentario (obligatorio)' if required else 'Comentario (opcional)')
                for vacio in (None,'','  ','\n\t'):
                    self.assertEqual(confirmar_ui(True,motivo,{'display':'block'},vacio),required)
                self.assertFalse(confirmar_ui(True,motivo,{'display':'block'},' Causa informada '))

    @patch.object(gestion,'_usuario',return_value='especialista')
    def test_ayuda_se_limpia_y_cierre_no_exige_comentario(self, usuario):
        for motivo in (None,'INVALIDO'):
            self.assertEqual(gestion.ayuda_motivo(motivo,{'display':'block'}),('', 'Comentario (opcional)',False))
        self.assertEqual(gestion.ayuda_motivo('OTRO',{'display':'none'}),('', 'Comentario (opcional)',False))
        self.assertTrue(confirmar_ui(True,'OTRO',{'display':'none'},None))
        self.assertTrue(confirmar_ui(False,'OTRO',{'display':'block'},'Causa'))

    @patch.object(gestion,'_usuario',return_value='especialista')
    def test_preview_modal_amigable_sin_mutar_datos_ni_bloquear_por_tum(self, usuario):
        frame=preview()
        frame.loc[frame.equipo_codigo=='PRINCIPAL_CV008','valor_turno_tum']=None
        frame['tum_disponible_operacional']=frame['tum_disponible_operacional'].astype(bool)
        frame.loc[frame.equipo_codigo=='PRINCIPAL_CV008','tum_disponible_operacional']=False
        original=frame.copy(deep=True)
        result=gestion.presentar_preview(frame,False,modal=True)
        pd.testing.assert_frame_equal(frame,original)
        tabla=result.children[0]
        self.assertTrue(tabla.responsive)
        self.assertEqual([th.children for th in tabla.children[0].children.children],
                         ['Equipo','Estado PI','PI','PI disponible','TUM','TUM disponible'])
        fila=self._fila(tabla)
        self.assertEqual(fila[0].children,'CV008')
        self.assertEqual(fila[1].children.children,'Con variación')
        self.assertEqual(fila[1].children.title,'CON_VARIACION')
        self.assertEqual(fila[2].children,'0 t')
        self.assertEqual(fila[3].children.children,'Sí')
        self.assertEqual(fila[4].children,'—')
        self.assertEqual(fila[5].children.children,'No')
        self.assertIn('Pendiente de TUM',str(result))
        self.assertIn('Fuente si activa',str(result))
        self.assertIn('21.774 t',str(result))
        self.assertNotIn('PRINCIPAL_',str(result))
        self.assertFalse(confirmar_ui(True,'CAIDA_PI',{'display':'block'}))

    def test_indicaciones_condicionales_sin_espacio_residual(self):
        self.assertEqual(gestion.indicaciones_motivo(None,{},None),
                         ({'display':'block'},{'display':'none'}))
        for motivo in db.MOTIVOS:
            for comentario in (None,'','  ','causa identificada'):
                with self.subTest(motivo=motivo,comentario=comentario):
                    seleccion,causa=gestion.indicaciones_motivo(motivo,{},comentario)
                    self.assertEqual(seleccion,{'display':'none'})
                    esperado=motivo=='OTRO' and not (comentario or '').strip()
                    self.assertEqual(causa,{'display':'block' if esperado else 'none'})
        self.assertEqual(gestion.indicaciones_motivo('OTRO',{'display':'none'},None),
                         ({'display':'none'},{'display':'none'}))

    def test_confirmar_bloqueado_sin_usuario_de_sesion(self):
        with self.app.test_request_context('/'):
            for usuario in (None,'','  '):
                session['user']=usuario
                self.assertTrue(confirmar_ui(True,'CAIDA_PI',{},None))
                self.assertTrue(confirmar_ui(True,'OTRO',{},'Causa'))
                self.assertTrue(confirmar_ui(True,None,{'display':'none'},None))
            session['user']='especialista'
            self.assertFalse(confirmar_ui(True,'CAIDA_PI',{},None))

    def test_formato_principal_modal_estados_y_null_apilado(self):
        for codigo,etiqueta in [
                ('CON_VARIACION','Con variación'),
                ('SIN_CAMBIO_TURNO_COMPLETO','Sin cambio · turno completo'),
                ('SIN_CAMBIO_CON_COBERTURA_PARCIAL','Sin cambio · cobertura parcial'),
                ('SIN_PI','Sin PI'),('CODIGO_DESCONOCIDO','CODIGO_DESCONOCIDO')]:
            frame=preview(tum=False,activa=True)
            frame['estado_tecnico_pi']=codigo
            original=frame.copy(deep=True)
            for modal in (False,True):
                tabla=gestion.presentar_preview(frame,True,modal=modal).children[0]
                celdas=self._fila(tabla)
                self.assertEqual(celdas[1].children.children,etiqueta)
                self.assertEqual(celdas[1].children.title,codigo)
                self.assertEqual(celdas[4].children,'—')
                if not modal:
                    self.assertEqual(celdas[7].children,'—')
            pd.testing.assert_frame_equal(frame,original)
        frame=pd.DataFrame([{'CV008':None,'CV108':0,'Total_turno':21774}])
        original=frame.copy(deep=True)
        tabla=gestion._tabla(frame,[(c,c) for c in frame.columns],tonelajes=tuple(frame.columns))
        self.assertEqual(tabla.data,[{'CV008':'—','CV108':'0 t','Total_turno':'21.774 t'}])
        pd.testing.assert_frame_equal(frame,original)

    def test_disponibilidad_tres_estados_sin_inferir_desde_contingencia(self):
        for valor,esperado in [(True,'Sí'),(False,'No'),(1,'Sí'),(0,'No'),
                               (None,'—'),(pd.NA,'—'),(float('nan'),'—')]:
            for activa in (False,True):
                for modal in (False,True):
                    with self.subTest(valor=valor,activa=activa,modal=modal):
                        frame=preview(activa=activa).assign(pi_disponible_operacional=valor,
                                                          tum_disponible_operacional=valor)
                        result=gestion.presentar_preview(frame,activa,modal=modal)
                        fila=self._fila(result.children[0])
                        for indice in (3,5):
                            contenido=fila[indice].children
                            visible=contenido if isinstance(contenido,str) else contenido.children
                            self.assertEqual(visible,esperado)
                            self.assertNotIn('— —',visible)

    def test_sin_filas_muestra_un_guion_por_celda_y_no_inventa_no(self):
        for modal in (False,True):
            result=gestion.presentar_preview(pd.DataFrame(),False,modal=modal)
            filas=result.children[0].children[1].children
            filas=[fila for fila in filas if isinstance(fila.children,list)]
            self.assertEqual(len(filas),7)
            for fila,equipo in zip(filas,db.EQUIPOS):
                self.assertEqual(fila.children[0].children,equipo.replace('PRINCIPAL_',''))
                for indice in (2,3,4,5):
                    self.assertEqual(fila.children[indice].children,'—')
            self.assertIn('Sin información',str(result))
            self.assertIn('Sin información TUM: CHANCADOR_CV006, CV008, CV108',str(result))
            self.assertIn('Sin información',str(result))
            self.assertNotIn('Pendiente de TUM',str(result))
            self.assertNotIn('— —',str(result))
            self.assertEqual(result.children[-1].color,'warning')

    def test_etiquetas_operacionales_no_certifican_salud_pi(self):
        for activa,codigo,etiqueta in [(False,'NORMAL_PI','Sin contingencia declarada'),
                                      (True,'CONTINGENCIA_PI','Contingencia PI activa')]:
            componente=gestion._etiqueta_estado_operacional(activa)
            self.assertEqual(componente.children,etiqueta)
            self.assertEqual(componente.title,codigo)

    def test_preview_distingue_fuente_y_estado_sin_terminos_internos(self):
        for tum in (False,True):
            for modal in (False,True):
                frame=preview(tum=tum,activa=True)
                original=frame.copy(deep=True)
                result=gestion.presentar_preview(frame,False,modal=modal)
                texto=str(result)
                if tum:
                    self.assertIn('Fuente si activa',texto)
                    self.assertIn('21.774 t',texto)
                    self.assertNotIn('Estado esperado: TUM',texto)
                    self.assertIn('Durante la contingencia, el Informe TUM se utilizará como fuente operacional.',texto)
                else:
                    self.assertIn('Pendiente de TUM',texto)
                    self.assertIn('Pendiente de TUM',texto)
                    self.assertIn('Cuando el TUM sea cargado',texto)
                for interno in ('PENDIENTE_TUM','PENDIENTE_PI','resolver SQL','resolvedor SQL'):
                    self.assertNotIn(interno,texto)
                pd.testing.assert_frame_equal(frame,original)

    def test_tabla_separa_fuente_de_estado_de_resolucion(self):
        for codigo,fuente,estado_visible in [
                ('PI','PI','Resuelto'),('TUM','TUM','Resuelto'),
                ('PENDIENTE_PI','—','Pendiente de PI'),
                ('PENDIENTE_TUM','—','Pendiente de TUM'),(None,'—','Sin información'),(pd.NA,'—','Sin información')]:
            frame=preview().assign(fuente_resuelta=codigo)
            original=frame.copy(deep=True)
            result=gestion.presentar_preview(frame,True)
            celdas=self._fila(result.children[0])
            self.assertEqual(celdas[6].children,fuente)
            self.assertEqual(celdas[8].children,estado_visible)
            self.assertNotIn('PENDIENTE_',str(result))
            pd.testing.assert_frame_equal(frame,original)

    def test_cuatro_escenarios_disponibilidad_y_resolucion(self):
        casos = [
            (True,True,'PI','PI','Resuelto','Fuente si activa',None),
            (True,False,'PI','PI','Resuelto','Pendiente de TUM','Informe TUM no disponible'),
            (False,False,'PENDIENTE_PI','—','Pendiente de PI','Pendiente de TUM','Informe TUM no disponible'),
            (None,None,None,'—','Sin información','Sin información','Sin información TUM para el período seleccionado'),
        ]
        for pi,tum,codigo,fuente,resolucion,proyeccion,alerta in casos:
            for modal in (False,True):
                with self.subTest(pi=pi,tum=tum,modal=modal):
                    frame=preview().assign(pi_disponible_operacional=pi,tum_disponible_operacional=tum,
                        fuente_resuelta=codigo,valor_pi_final=0 if pi else None,
                        valor_turno_tum=21774 if tum else None,valor_final_resuelto=0 if pi else None)
                    original=frame.copy(deep=True)
                    result=gestion.presentar_preview(frame,False,modal=modal)
                    fila=self._fila(result.children[0])
                    for indice,valor in [(3,pi),(5,tum)]:
                        celda=fila[indice].children
                        self.assertEqual(celda if isinstance(celda,str) else celda.children,
                                         '—' if valor is None else 'Sí' if valor else 'No')
                    if not modal:
                        self.assertEqual(fila[6].children,fuente)
                        self.assertEqual(fila[8].children,resolucion)
                        self.assertEqual(fila[7].children,'0 t' if pi else '—')
                    self.assertIn(proyeccion,str(result))
                    if alerta:
                        self.assertEqual(result.children[-1].children[0].children,alerta)
                    else:
                        self.assertIn('21.774 t',str(result))
                    for prohibido in ('PENDIENTE_PI','PENDIENTE_TUM','— —','No —'):
                        self.assertNotIn(prohibido,str(result))
                    pd.testing.assert_frame_equal(frame,original)

    def test_tum_mixto_no_y_sin_informacion_tienen_alertas_separadas(self):
        frame=preview(tum=False)
        frame['tum_disponible_operacional']=pd.Series([True] * len(frame),dtype=object)
        frame.loc[frame.equipo_codigo=='PRINCIPAL_CV008','tum_disponible_operacional']=False
        frame.loc[frame.equipo_codigo=='PRINCIPAL_CV108','tum_disponible_operacional']=None
        for modal in (False,True):
            result=gestion.presentar_preview(frame,False,modal=modal)
            alertas=[c for c in result.children if c.__class__.__name__=='Alert']
            self.assertEqual(len(alertas),2)
            self.assertEqual(alertas[0].children[-1].children,'Sin TUM: CV008')
            self.assertEqual(alertas[1].children[-1].children,'Sin información TUM: CV108')
            self.assertIn('Pendiente de TUM',str(result))
            self.assertIn('Sin información',str(result))


if __name__=='__main__':
    unittest.main()
