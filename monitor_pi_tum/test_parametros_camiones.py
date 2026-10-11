"""Contrato del nucleo generico; no conecta ni escribe en DEV."""
from decimal import Decimal
from unittest.mock import MagicMock, patch
from datetime import date, timedelta
import unittest

import pandas as pd
from . import db
from . import limites_camiones_panel as ui
from flask import Flask, session


class ParametrosCamionesTests(unittest.TestCase):
    def test_whitelist_no_admite_identificadores_arbitrarios(self):
        for value in (None, '', 'otro', "x]; DROP TABLE x;--", []):
            with self.subTest(value=value), self.assertRaises(ValueError):
                db.validar_parametro_factor(value, 'KOM', 357, '2026-07-01', 'motivo', 'usuario')

    def test_categorias_flotas_y_seis_decimales(self):
        for category in db.PARAMETROS_FACTOR_CAMIONES:
            for fleet in ('KOM', 'CAT'):
                value = db.validar_parametro_factor(category, fleet, '357.123456', '2026-07-01', 'motivo', 'usuario')
                self.assertEqual(value['parametro'], category)
                self.assertEqual(value['flota'], fleet)
                self.assertEqual(value['valor'], Decimal('357.123456'))
                with self.assertRaises(ValueError):
                    db.validar_parametro_factor(category, fleet, '357.1234567', '2026-07-01', 'motivo', 'usuario')

    def test_wrapper_limites_conserva_payload(self):
        result = db.validar_limite_factor('CAT', 265, '2026-07-01', ' motivo ', ' usuario ')
        self.assertNotIn('parametro', result)
        self.assertEqual(result['valor'], Decimal('265'))
        self.assertEqual(result['motivo'], 'motivo')

    def test_pendientes_separan_categoria_y_columna_usada(self):
        engine = MagicMock()
        with patch.object(db, '_engine_dev', return_value=engine), patch.object(
                db.pd, 'read_sql', return_value=pd.DataFrame()) as read:
            for category, metadata in db.PARAMETROS_FACTOR_CAMIONES.items():
                db.obtener_pendientes_parametros_factor(category)
                query = str(read.call_args.args[0])
                self.assertEqual(read.call_args.kwargs['params'], {'parametro': category})
                self.assertIn('p.parametro=:parametro', query)
                self.assertIn('decimal(18,6)', query)
                for column in metadata['columnas']:
                    self.assertIn('v.' + column, query)

    def test_registro_generico_solo_administra_no_reprocesa(self):
        engine = MagicMock()
        conn = engine.begin.return_value.__enter__.return_value
        conn.execute.return_value.mappings.return_value.one.return_value = {'Valor_Nuevo': Decimal('357')}
        with patch.object(db, '_engine_dev', return_value=engine), patch.object(db, '_assert_dev_connection') as guard:
            result = db.registrar_parametro_factor('CARGA_NOMINAL_TMH_VIAJE', 'KOM', 357,
                                                  '2026-08-01', 'motivo', 'usuario')
            guard.assert_called_once_with(conn)
            self.assertEqual(conn.execute.call_count, 1)
            self.assertIn('sp_registrar_parametro_factor_camiones_vigencia_test', str(conn.execute.call_args.args[0]))
            self.assertEqual(conn.execute.call_args.args[1]['parametro'], 'CARGA_NOMINAL_TMH_VIAJE')
            self.assertEqual(result['Valor_Nuevo'], Decimal('357'))

    def test_categoria_invalida_no_abre_conexion(self):
        with patch.object(db, '_engine_dev') as engine:
            with self.assertRaises(ValueError):
                db.registrar_parametro_factor('INVALIDO', 'KOM', 357, '2026-08-01', 'motivo', 'usuario')
            engine.assert_not_called()

    def test_ui_nominal_conserva_categoria_usuario_y_no_registra_al_revisar(self):
        app=Flask(__name__)
        app.secret_key='test'
        h=pd.DataFrame([dict(flota='KOM',valor=357),dict(flota='CAT',valor=236)])
        day=(date.today()+timedelta(days=10)).isoformat()
        with app.test_request_context(), patch.object(db,'obtener_parametros_factor_vigentes',return_value=h) as read, patch.object(db,'registrar_parametro_factor') as write:
            session['user']='operador'
            token,summary,retro=ui.preparar_confirmacion('KOM',356.123456,day,'motivo','CARGA_NOMINAL_TMH_VIAJE')
            self.assertFalse(retro)
            self.assertIn('Carga nominal',str(summary))
            write.assert_not_called()
            write.return_value={'Fecha_Inicio_Afectada':day,'Fecha_Fin_Afectada':date.today()}
            result=ui.confirmar_registro(token,False)
            self.assertIn('PROGRAMADO',str(result))
            self.assertEqual(write.call_args.kwargs['parametro'],'CARGA_NOMINAL_TMH_VIAJE')
            self.assertEqual(write.call_args.kwargs['usuario'],'operador')
            self.assertEqual(write.call_args.kwargs['valor'],'356.123456')
            self.assertEqual(read.call_count,2)

    def test_ui_selector_reutiliza_panel_y_dos_categorias(self):
        layout=str(ui.layout())
        self.assertIn('Parámetros camiones',layout)
        for category in db.PARAMETROS_FACTOR_CAMIONES:
            self.assertIn(category,layout)


if __name__ == '__main__':
    unittest.main()
