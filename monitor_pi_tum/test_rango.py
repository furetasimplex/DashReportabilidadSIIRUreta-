"""Rangos inclusivos y atomicidad; sin conexiones a DEV/PROD."""
from datetime import date
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from flask import Flask, session

from . import db, gestion
from .test_gestion import trigger


class RangoTests(unittest.TestCase):
    def setUp(self):
        for nombre in ('_ultimo_periodo_materializable','obtener_ultimo_periodo_materializable'):
            p=patch.object(db,nombre,return_value=(date(2026,9,30),'B'))
            p.start()
            self.addCleanup(p.stop)

    def test_expansion_y_cierre(self):
        casos = [
            ('2026-09-15','A','2026-09-15','A',[(15,'A')],(15,'B')),
            ('2026-09-15','A','2026-09-15','B',[(15,'A'),(15,'B')],(16,'A')),
            ('2026-09-15','A','2026-09-17','B',[(15,'A'),(15,'B'),(16,'A'),(16,'B'),(17,'A'),(17,'B')],(18,'A')),
            ('2026-09-15','B','2026-09-16','A',[(15,'B'),(16,'A')],(16,'B')),
        ]
        for inicio,ti,fin,tf,esperado,cierre in casos:
            with self.subTest(inicio=inicio,ti=ti,fin=fin,tf=tf):
                self.assertEqual(db.expandir_turnos(inicio,ti,fin,tf),[(date(2026,9,d),t) for d,t in esperado])
                self.assertEqual(db.turno_siguiente(fin,tf),(date(2026,9,cierre[0]),cierre[1]))

    def test_invalidos_y_usuario_antes_de_conectar(self):
        with patch.object(db,'_engine_dev') as engine:
            for args in [('2026-09-17','B','2026-09-17','A'),
                         ('2026-08-31','A','2026-09-01','B'),
                         (None,'A','2026-09-15','B'),('2026-09-15','C','2026-09-15','B')]:
                with self.assertRaises(ValueError):
                    db.registrar_contingencia_rango(*args,'CAIDA_PI',None,'real')
            with self.assertRaisesRegex(ValueError,'período final'):
                db.validar_rango('2026-09-17','B','2026-09-17','A')
            for usuario in (None,'','  '):
                with self.assertRaises(ValueError):
                    db.registrar_contingencia_rango('2026-09-15','A','2026-09-15','B','OTRO','causa',usuario)
            for comentario in (None,'',' \n '):
                with self.assertRaises(ValueError):
                    db.registrar_contingencia_rango('2026-09-15','A','2026-09-15','B','OTRO',comentario,'real')
            engine.assert_not_called()

    def test_query_solapamiento_con_eventos_reales_en_memoria(self):
        # Ejecuta el SELECT de producción (ROW_NUMBER/LEAD) sobre SQLite en memoria.
        # Los hints de bloqueo exclusivos de SQL Server se prueban en la transacción.
        conn=sqlite3.connect(':memory:')
        self.addCleanup(conn.close)
        conn.execute("ATTACH DATABASE ':memory:' AS inventar_SpcHidr")
        conn.execute('''CREATE TABLE inventar_SpcHidr.contingencia_pi_accion_test
            (id INTEGER,fecha_operacional TEXT,turno TEXT,accion TEXT,fecha_registro TEXT)''')
        tabla='inventar_SpcHidr.contingencia_pi_accion_test'
        def execute(sql,params):
            row=conn.execute(str(sql),{k:str(v) if isinstance(v,date) else v for k,v in params.items()}).fetchone()
            return SimpleNamespace(scalar=lambda:row[0])
        adapter=SimpleNamespace(execute=execute)
        escenarios = [
            ([],False),
            ([(10,'A','ACTIVAR_CONTINGENCIA'),(12,'B','CERRAR_CONTINGENCIA')],False),
            ([(14,'A','ACTIVAR_CONTINGENCIA')],True),
            ([(16,'A','ACTIVAR_CONTINGENCIA'),(17,'B','CERRAR_CONTINGENCIA')],True),
            ([(10,'A','ACTIVAR_CONTINGENCIA'),(20,'B','CERRAR_CONTINGENCIA')],True),
            ([(10,'A','ACTIVAR_CONTINGENCIA'),(15,'A','CERRAR_CONTINGENCIA')],False),
            ([(18,'A','ACTIVAR_CONTINGENCIA')],True), # Cierre coincide con otro inicio.
            ([(18,'B','ACTIVAR_CONTINGENCIA')],False),
            # Un cierre interior, incluso con activación supersedida, truncaría el rango nuevo.
            ([(16,'A','ACTIVAR_CONTINGENCIA'),(16,'A','CERRAR_CONTINGENCIA')],True),
        ]
        for eventos,rechazar in escenarios:
            conn.execute(f'DELETE FROM {tabla}')
            for i,(dia,turno,accion) in enumerate(eventos):
                conn.execute(f'INSERT INTO {tabla} VALUES (?,?,?,?,?)',
                    (i,f'2026-09-{dia:02}',turno,accion,'2026-09-16 12:00'))
            with self.subTest(eventos=eventos):
                if rechazar:
                    with self.assertRaises(ValueError):
                        db._validar_solapamiento(adapter,date(2026,9,15),'A',date(2026,9,17),'B')
                else:
                    db._validar_solapamiento(adapter,date(2026,9,15),'A',date(2026,9,17),'B')

    def test_dos_eventos_un_reproceso_y_rollback_en_cualquier_fallo(self):
        for falla in (None,'activar','cerrar','reproceso'):
            engine=MagicMock()
            conn=engine.begin.return_value.__enter__.return_value
            escritos=[]
            def execute(sql,params=None):
                sql=str(sql)
                if 'sp_getapplock' in sql:
                    return SimpleNamespace(scalar=lambda:0)
                if 'WITH (UPDLOCK, HOLDLOCK)' in sql:
                    return SimpleNamespace(scalar=lambda:0)
                self.assertIn('sp_registrar_contingencia_pi_test',sql)
                escritos.append(params)
                if falla==('activar' if len(escritos)==1 else 'cerrar'):
                    raise RuntimeError('fallo simulado')
                result=MagicMock()
                result.mappings.return_value.one.return_value={'id':len(escritos)}
                return result
            conn.execute.side_effect=execute
            with self.subTest(falla=falla),patch.object(db,'_engine_dev',return_value=engine), \
                 patch.object(db,'_assert_dev_connection'), \
                 patch.object(db,'reprocesar_apilado',side_effect=RuntimeError('fallo reproceso') if falla=='reproceso' else None) as reproceso, \
                 patch.object(db,'_preview_rango',return_value=pd.DataFrame(columns=['fuente_resuelta','equipo_codigo'])):
                def guardar():
                    return db.registrar_contingencia_rango('2026-09-15','A','2026-09-17','B','CAIDA_PI','nota','real')
                if falla:
                    with self.assertRaises(RuntimeError):
                        guardar()
                    self.assertIs(engine.begin.return_value.__exit__.call_args.args[0],RuntimeError)
                else:
                    result=guardar()
                    self.assertIsNone(engine.begin.return_value.__exit__.call_args.args[0])
                    self.assertEqual(result['ids'],[1,2])
                if falla in (None,'reproceso'):
                    self.assertEqual(len(escritos),2)
                    self.assertEqual(escritos[0]['accion'],'ACTIVAR_CONTINGENCIA')
                    self.assertEqual((escritos[1]['fecha'],escritos[1]['turno']),(date(2026,9,18),'A'))
                    self.assertEqual(escritos[1]['accion'],'CERRAR_CONTINGENCIA')
                    self.assertIsNone(escritos[1]['motivo'])
                    self.assertEqual([p['usuario'] for p in escritos],['real','real'])
                    reproceso.assert_called_once_with(conn,date(2026,9,15),date(2026,9,17))
                else:
                    reproceso.assert_not_called()

    def test_preview_rango_faltantes_y_null_no_bloquean(self):
        frame=pd.DataFrame([dict(fecha_operacional='2026-09-15',turno='A',equipo_codigo=e,
            tum_disponible_operacional=True) for e in db.EQUIPOS]+[
            dict(fecha_operacional='2026-09-15',turno='B',equipo_codigo=db.EQUIPOS[0],tum_disponible_operacional=False)])
        args=('2026-09-15','A','2026-09-17','B')
        with patch.object(db,'obtener_preview_rango',return_value=frame),patch.object(gestion,'_usuario',return_value='real'):
            contenido,validado=gestion.previsualizar_rango(*args,True,{'display':'block'})
            self.assertIn('Turnos afectados: 6',str(contenido))
            self.assertIn('Período seleccionado: 15-09-2026 A → 17-09-2026 B',str(contenido))
            self.assertIn('Está por declarar una contingencia PI para 6 turnos',str(contenido))
            self.assertIn('5 de 6 turnos no poseen TUM disponible',str(contenido))
            tabla=next(c for c in contenido.children if c.__class__.__name__=='DataTable')
            self.assertEqual([(row['fecha'],row['turno']) for row in tabla.data],
                [('15-09-2026','A'),('15-09-2026','B'),('16-09-2026','A'),
                 ('16-09-2026','B'),('17-09-2026','A'),('17-09-2026','B')])
            self.assertEqual(tabla.data[0]['resultado'],'TUM')
            self.assertEqual(tabla.data[1]['CHANCADOR_CV006'],'No')
            self.assertEqual(tabla.data[1]['PRINCIPAL_CV108'],'—')
            self.assertEqual(tabla.data[2]['informacion'],'Sin información TUM')
            self.assertIn('La contingencia puede registrarse',str(contenido))
            self.assertFalse(gestion.confirmar_deshabilitado(True,'CAIDA_PI',{},None,*args,validado))
            self.assertTrue(gestion.confirmar_deshabilitado(True,'CAIDA_PI',{},None,
                args[0],args[1],'2026-09-18','B',validado))

    def test_consulta_unica_parametrizada_siete_equipos(self):
        engine=MagicMock()
        with patch.object(db,'_engine_dev',return_value=engine),patch.object(db,'_validar_solapamiento'), \
             patch.object(db.pd,'read_sql',return_value=pd.DataFrame()) as read:
            db.obtener_preview_rango('2026-09-15','B','2026-09-17','A')
        self.assertEqual(read.call_count,1)
        self.assertIn("'CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108'",str(read.call_args.args[0]))
        self.assertIn("'RIPIOS_CV025'",str(read.call_args.args[0]))
        self.assertEqual(read.call_args.kwargs['params'],dict(inicio=date(2026,9,15),turno_inicio='B',fin=date(2026,9,17),turno_fin='A'))

    def test_solapamiento_transaccional_no_escribe_y_preview_bloquea(self):
        engine=MagicMock()
        conn=engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.scalar.return_value=0
        mensaje='El rango seleccionado se superpone con una contingencia PI ya registrada.'
        with patch.object(db,'_engine_dev',return_value=engine), \
             patch.object(db,'_assert_dev_connection'), \
             patch.object(db,'_validar_solapamiento',side_effect=ValueError(mensaje)), \
             patch.object(db,'reprocesar_apilado') as reproceso:
            with self.assertRaisesRegex(ValueError,'superpone'):
                db.registrar_contingencia_rango('2026-09-15','A','2026-09-17','B','OTRO','causa','real')
            self.assertEqual(conn.execute.call_count,1) # Solo lock, sin eventos.
            reproceso.assert_not_called()
        with patch.object(db,'obtener_preview_rango',side_effect=ValueError(mensaje)):
            contenido,validado=gestion.previsualizar_rango('2026-09-15','A','2026-09-17','B',True,{})
            self.assertEqual(contenido.children,mensaje)
            self.assertIsNone(validado)

    def test_guardado_rechaza_sesion_ausente_y_preview_obsoleto(self):
        app=Flask(__name__)
        app.secret_key='prueba'
        with app.test_request_context('/'),trigger('pitum-gestion-guardar'), \
             patch.object(db,'registrar_contingencia_rango') as guardar:
            args=('2026-09-15','A','2026-09-17','B')
            result=gestion.gestionar(0,0,0,1,None,None,'OTRO','causa',*args,{'periodo':list(args)})
            self.assertIn(gestion.SIN_USUARIO,str(result[5]))
            session['user']='real'
            session['pitum_confirmacion']={'accion':'ACTIVAR_CONTINGENCIA','usuario':'real'}
            result=gestion.gestionar(0,0,0,1,None,None,'OTRO','causa',*args,None)
            self.assertIn('Revise el preview',str(result[5]))
            guardar.assert_not_called()


if __name__ == '__main__':
    unittest.main()
