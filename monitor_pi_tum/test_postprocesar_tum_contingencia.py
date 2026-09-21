"""Contrato del postproceso independiente, sin conexiones reales."""
from datetime import date
import unittest
from unittest.mock import MagicMock, patch

from . import postprocesar_tum_contingencia as post


class Resultado:
    def __init__(self, *, first=None, all_rows=None, scalar=None):
        self._first, self._all, self._scalar = first, all_rows or [], scalar

    def mappings(self):
        return self

    def first(self):
        return self._first

    def all(self):
        return self._all

    def scalar_one_or_none(self):
        return self._scalar

    def scalar(self):
        return self._scalar


def conexion(*, estado='committed', template=post.TEMPLATE, cambios=(), contingencia=()):
    conn = MagicMock()
    bajo = set(contingencia)
    def ejecutar(sql, params=None):
        sql = str(sql)
        if 'sp_getapplock' in sql:
            return Resultado(scalar=0)
        if 'import_batch' in sql:
            return Resultado(first=None if estado is None else
                             {'id':params['batch_id'],'estado':estado,'template_code':template})
        if 'import_row_history' in sql:
            return Resultado(all_rows=[dict(fecha_operacional=f,turno=t,equipo_codigo=e)
                                       for f,t,e in cambios])
        if 'v_contingencia_pi_estado_turno_test' in sql:
            return Resultado(scalar=(params['fecha'],params['turno']) in bajo)
        if 'v_contingencia_totalizador_resuelto_operacional_test' in sql:
            return Resultado(all_rows=[])
        if 'Control_Apilado_TMH_v2_test' in sql:
            return Resultado(first={'Fecha':params['fecha']})
        raise AssertionError(sql)
    conn.execute.side_effect = ejecutar
    return conn


class PostprocesarTumTests(unittest.TestCase):
    def test_commit_lock_antes_del_plan_y_hasta_salida_transaccional(self):
        eventos = []
        conn, engine = MagicMock(), MagicMock()
        contexto = engine.begin.return_value
        contexto.__enter__.side_effect = lambda: eventos.append('begin') or conn
        contexto.__exit__.side_effect = lambda *args: eventos.append('salida') or False
        conn.execute.side_effect = lambda sql: eventos.append('lock') or Resultado(scalar=0)
        dia = date(2026, 9, 10)
        plan = post.Plan(150, 'committed', post.TEMPLATE, 1, (), (), (), (dia,))
        def planificar(c, batch):
            self.assertEqual(eventos, ['begin', 'guard', 'lock'])
            self.assertIs(c, conn)
            self.assertEqual(batch, 150)
            eventos.append('planificar')
            return plan
        with patch.object(post.db, '_assert_dev_connection', side_effect=lambda c: eventos.append('guard')) as guard, \
             patch.object(post, 'planificar', side_effect=planificar), \
             patch.object(post.db, 'reprocesar_apilado', side_effect=lambda *a: eventos.append('reprocesar')) as reproceso, \
             patch.object(post, 'verificar_resultado', side_effect=lambda *a: eventos.append('verificar') or (['resuelto'], ['apilado'])) as verificar:
            resultado = post.ejecutar(150, True, engine)
        self.assertEqual(eventos, ['begin', 'guard', 'lock', 'planificar', 'reprocesar', 'verificar', 'salida'])
        self.assertEqual(resultado, (plan, ['resuelto'], ['apilado']))
        guard.assert_called_once_with(conn)
        reproceso.assert_called_once_with(conn, dia, dia)
        verificar.assert_called_once_with(conn, plan)
        contexto.__exit__.assert_called_once_with(None, None, None)
        engine.begin.assert_called_once_with()
        engine.connect.assert_not_called()
        conn.commit.assert_not_called()
        conn.rollback.assert_not_called()
        # El helper real no abre conexiones, no libera el lock ni confirma.
        conn.execute.assert_called_once()
        sql = str(conn.execute.call_args.args[0])
        for contrato in ("@Resource='SIIR_CONTINGENCIA_PI_APILADO'", "@LockMode='Exclusive'",
                         "@LockOwner='Transaction'", '@LockTimeout=10000'):
            self.assertIn(contrato, sql)
        self.assertNotIn('sp_releaseapplock', sql)

    def test_lock_rechazado_impide_plan_y_reproceso_sin_reintentar(self):
        for rc in (-1, -2, -3, -999, None):
            with self.subTest(resultado_lock=rc):
                conn, engine = MagicMock(), MagicMock()
                engine.begin.return_value.__enter__.return_value = conn
                conn.execute.return_value = Resultado(scalar=rc)
                with patch.object(post.db, '_assert_dev_connection'), \
                     patch.object(post, 'planificar') as planificar, \
                     patch.object(post.db, 'reprocesar_apilado') as reproceso, \
                     patch.object(post, 'verificar_resultado') as verificar:
                    with self.assertRaisesRegex(ValueError, 'Hay otra acción en proceso') as error:
                        post.ejecutar(150, True, engine)
                planificar.assert_not_called()
                reproceso.assert_not_called()
                verificar.assert_not_called()
                conn.execute.assert_called_once()
                engine.begin.assert_called_once()
                salida = engine.begin.return_value.__exit__.call_args.args
                self.assertIs(salida[0], ValueError)
                self.assertIs(salida[1], error.exception)

    def test_error_sql_del_lock_se_propaga_sin_planificar(self):
        conn, engine = MagicMock(), MagicMock()
        engine.begin.return_value.__enter__.return_value = conn
        error = RuntimeError('error SQL adquiriendo lock')
        conn.execute.side_effect = error
        with patch.object(post.db, '_assert_dev_connection'), \
             patch.object(post, 'planificar') as planificar, \
             patch.object(post.db, 'reprocesar_apilado') as reproceso:
            with self.assertRaises(RuntimeError) as capturado:
                post.ejecutar(150, True, engine)
        self.assertIs(capturado.exception, error)
        self.assertIs(engine.begin.return_value.__exit__.call_args.args[1], error)
        planificar.assert_not_called()
        reproceso.assert_not_called()

    def test_dry_run_no_adquiere_lock_y_conserva_plan(self):
        conn = conexion(cambios=[('2026-09-10', 'A', 'PRINCIPAL_CV008')],
                        contingencia={(date(2026, 9, 10), 'A')})
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = conn
        esperado = post.planificar(conn, 150)
        conn.reset_mock()
        with patch.object(post.db, '_assert_dev_connection'), \
             patch.object(post.db, '_adquirir_lock_contingencia') as lock, \
             patch.object(post.db, 'reprocesar_apilado') as reproceso:
            self.assertEqual(post.ejecutar(150, False, engine), (esperado, [], []))
        lock.assert_not_called()
        reproceso.assert_not_called()
        engine.begin.assert_not_called()
        self.assertTrue(all(str(c.args[0]).lstrip().startswith('SELECT') for c in conn.execute.call_args_list))

    def test_helper_admite_lock_inmediato_o_tras_esperar(self):
        for rc in (0, 1):
            with self.subTest(resultado_lock=rc):
                conn = MagicMock()
                conn.execute.return_value = Resultado(scalar=rc)
                post.db._adquirir_lock_contingencia(conn)
                conn.execute.assert_called_once()

    def test_batch_inexistente_y_no_committed_bloquean(self):
        for estado in (None,'error','preview'):
            with self.subTest(estado=estado), self.assertRaises(ValueError):
                post.planificar(conexion(estado=estado),150)

    def test_otro_template_y_seca_sin_cambios(self):
        for template in ('informe_tum_srr',post.TEMPLATE):
            plan=post.planificar(conexion(template=template),150)
            self.assertEqual(plan.fechas,())
            self.assertEqual(plan.cambios,0)

    def test_cruce_y_fechas_distintas(self):
        cambios=[('2026-09-10','A','PRINCIPAL_CV008'),
                 ('2026-09-11','A','PRINCIPAL_CV008'),
                 ('2026-09-11','B','PRINCIPAL_CV108'),
                 ('2026-09-12','A','PRINCIPAL_CV008')]
        bajo={(date(2026,9,10),'A'),(date(2026,9,11),'A'),(date(2026,9,11),'B')}
        plan=post.planificar(conexion(cambios=cambios,contingencia=bajo),150)
        self.assertEqual(plan.cambios,4)
        self.assertEqual(plan.fechas,(date(2026,9,10),date(2026,9,11)))
        self.assertEqual(plan.fuera,((date(2026,9,12),'A'),))
        self.assertEqual(post.agrupar_fechas(plan.fechas),((date(2026,9,10),date(2026,9,11)),))

    def test_siete_senales_solo_principales_reprocesan_apilado(self):
        cambios=[('2026-09-10','A',equipo) for equipo in post.db.EQUIPOS]
        bajo={(date(2026,9,10),'A')}
        plan=post.planificar(conexion(cambios=cambios,contingencia=bajo),150)
        self.assertEqual(len(plan.bajo_equipo),7)
        self.assertEqual(plan.fechas,(date(2026,9,10),))
        for template,equipo in [('informe_tum_srr','SRR_CV001'),
                                ('informe_tum_ripios','RIPIOS_CV025')]:
            solo=post.planificar(conexion(template=template,
                cambios=[('2026-09-10','A',equipo)],contingencia=bajo),150)
            self.assertEqual(solo.cambios,1)
            self.assertEqual(solo.fechas,())
            self.assertEqual(solo.bajo_equipo,((date(2026,9,10),'A',equipo),))

    def test_dry_run_y_fuera_de_contingencia_no_reprocesan(self):
        conn=conexion(cambios=[('2026-09-12','A','PRINCIPAL_CV008')])
        engine=MagicMock()
        engine.connect.return_value.__enter__.return_value=conn
        engine.begin.return_value.__enter__.return_value=conn
        with patch.object(post.db,'_assert_dev_connection') as guard, \
             patch.object(post.db,'reprocesar_apilado') as reproceso:
            plan,_,_=post.ejecutar(150,False,engine)
            self.assertEqual(plan.fechas,())
            engine.begin.assert_not_called()
            guard.assert_called_once_with(conn)
            plan,_,_=post.ejecutar(150,True,engine)
            self.assertEqual(plan.fechas,())
            reproceso.assert_not_called()

    def test_commit_repetido_recalcula_sin_acciones(self):
        conn=conexion(cambios=[('2026-09-10','A','PRINCIPAL_CV008'),
                              ('2026-09-11','A','PRINCIPAL_CV108'),
                              ('2026-09-11','B','PRINCIPAL_CV008')],
                      contingencia={(date(2026,9,10),'A'),(date(2026,9,11),'A'),(date(2026,9,11),'B')})
        engine=MagicMock()
        engine.begin.return_value.__enter__.return_value=conn
        with patch.object(post.db,'_assert_dev_connection') as guard, \
             patch.object(post.db,'reprocesar_apilado') as reproceso:
            for _ in range(2):
                plan,_,apilado=post.ejecutar(150,True,engine)
                self.assertEqual(len(apilado),2)
                self.assertEqual(plan.fechas,(date(2026,9,10),date(2026,9,11)))
            self.assertEqual(reproceso.call_count,2)
            for call in reproceso.call_args_list:
                self.assertEqual(call.args,(conn,date(2026,9,10),date(2026,9,11)))
            self.assertEqual(guard.call_count,2)
        self.assertFalse(any('sp_registrar_contingencia_pi_test' in str(c.args[0])
                             for c in conn.execute.call_args_list))

    def test_fallo_revierte_postproceso_y_guard_bloquea(self):
        conn=conexion(cambios=[('2026-09-10','A','PRINCIPAL_CV008')],
                      contingencia={(date(2026,9,10),'A')})
        engine=MagicMock()
        engine.begin.return_value.__enter__.return_value=conn
        # Un contexto real simulado propaga la excepción y registra el rollback.
        with patch.object(post.db,'_assert_dev_connection'), \
             patch.object(post.db,'reprocesar_apilado',side_effect=RuntimeError('SP falla')):
            with self.assertRaisesRegex(RuntimeError,'SP falla'):
                post.ejecutar(150,True,engine)
            self.assertIs(engine.begin.return_value.__exit__.call_args.args[0],RuntimeError)
        with patch.object(post.db,'_assert_dev_connection',side_effect=RuntimeError('DEV inválido')), \
             patch.object(post.db,'reprocesar_apilado') as reproceso:
            with self.assertRaisesRegex(RuntimeError,'DEV inválido'):
                post.ejecutar(150,True,engine)
            reproceso.assert_not_called()


if __name__ == '__main__':
    unittest.main()
