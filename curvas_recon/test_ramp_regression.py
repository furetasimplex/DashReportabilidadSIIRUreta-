"""Regresiones locales de rampa y reparto, sin acceder a SQL Server.

Se cargan las funciones de producción mediante AST para evitar inicializar
la conexión y los cargadores del módulo completo. No se sustituye el cálculo.
Ejecutar: python -B -m unittest test_ramp_regression -v
"""
import ast
from pathlib import Path
import unittest

import numpy as np
import pandas as pd
import ramp_curve


def motor_local():
    nombres = {
        '_ramp_factor', '_solve_meseta', '_distribute_daily_pile',
        '_split_fino', '_resembrar_fino_pila', '_repartir_residuo_rampa',
        '_absorber_piso_rampa', 'limpiar_estado_rampa',
    }
    tree = ast.parse(Path(__file__).with_name('recon_engine.py').read_text(encoding='utf-8'))
    ns = dict(pd=pd, np=np, ramp_curve=ramp_curve, _RAMP_ESTADO={},
              RAMP_INITIAL_DEFAULT=.1, RAMP_ALPHA_DEFAULT=ramp_curve.RAMP_ALPHA,
              DIAS_RAMPA=ramp_curve.DIAS_RAMPA, FDRENA_MAX=.95,
              FDRENA_RECON_MAX=.99)

    def resolve_window(start, end=None):
        start = pd.Timestamp(start)
        end = pd.Timestamp(end) if end is not None else start + pd.Timedelta(days=6)
        return start, end, (end - start).days + 1

    ns['resolve_window'] = resolve_window
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in nombres]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'recon_engine.py', 'exec'), ns)
    return ns


class RampaEntreVentanas(unittest.TestCase):
    def setUp(self):
        self.motor = motor_local()
        self.inicio = pd.Timestamp('2026-08-01')
        dates = pd.date_range(self.inicio, periods=42)
        self.mat = dict(riego=pd.DataFrame({'P01': 100.}, index=dates),
                        cu_riego=pd.Series(1., index=dates),
                        drena_cu=pd.DataFrame({'P01': 2.}, index=dates))

    def ventana(self, primero, ultimo, ratio):
        start = self.inicio + pd.Timedelta(days=primero - 1)
        end = self.inicio + pd.Timedelta(days=ultimo - 1)
        n = ultimo - primero + 1
        row = dict(dia_ciclo=ultimo, d_riego=0., q_pls_final=ratio*n*100,
                   fino_riego_final=n*100., fino_pls_final=ratio*n*200.)
        days = self.motor['_distribute_daily_pile'](
            'SULFUROS', 'P01', start, self.mat, row, .99, [], week_end=end,
            ini_ciclo=self.inicio if primero == 1 else None, ini_campana=self.inicio)
        return row, days

    def test_repetir_no_reinicia_y_no_usa_futuro(self):
        _, a = self.ventana(1, 7, .4)
        b, days = self.ventana(7, 13, .6)
        repeated, again = self.ventana(7, 13, .6)
        self.assertEqual(b['ramp_modo'], 'continuacion')
        self.assertEqual(repeated['ramp_modo'], 'continuacion')
        self.assertEqual(days, again)
        self.assertAlmostEqual(a[-1]['ramp_factor'], days[0]['ramp_factor'])
        self.ventana(13, 19, .7)
        _, after_future = self.ventana(7, 13, .6)
        self.assertEqual(days, after_future)

    def test_rampa_sigue_durante_30_dias_desde_inicio_real(self):
        prev = None
        for primero, ultimo, ratio in [(1, 7, .4), (7, 13, .6),
                                      (13, 19, .7), (19, 25, .8), (25, 31, .9)]:
            row, days = self.ventana(primero, ultimo, ratio)
            self.assertTrue(row['en_rampa'])
            self.assertEqual(days[0]['dia_rampa'], primero)
            if prev is not None:
                self.assertEqual(row['ramp_modo'], 'continuacion')
                self.assertAlmostEqual(prev, days[0]['ramp_factor'])
            prev = days[-1]['ramp_factor']
            self.assertTrue(all(0 <= d['ramp_factor'] <= .99 for d in days))
        row, _ = self.ventana(32, 38, .9)
        self.assertFalse(row['en_rampa'])

    def test_cambiar_semana_anterior_invalida_sucesoras(self):
        self.ventana(1, 7, .4)
        self.ventana(7, 13, .6)
        self.ventana(13, 19, .7)
        self.ventana(1, 7, .3)
        history = next(iter(self.motor['_RAMP_ESTADO'].values()))
        self.assertEqual(list(history), [self.inicio])


class RepartoProtegeRampa(unittest.TestCase):
    def setUp(self):
        self.motor = motor_local()

    def pila(self, name, daily, target, rampa, residual=0.):
        return dict(label='SULFUROS', parcela=name, q_pls_final=target,
                    fino_pls_final=target*2, q_pls_medido=190.,
                    ramp_residuo=residual, en_rampa=rampa,
                    daily=[dict(q_riego_final=100., q_riego_medido=100.,
                                q_pls_final=q, fino_pls_medido=190.) for q in daily])

    def test_sobrante_no_toca_otra_pila_en_rampa(self):
        donor = self.pila('P01', [49.5, 56.77], 181., True, 74.73)
        other = self.pila('P02', [90., 91.], 181., True)
        inventory = self.motor['_repartir_residuo_rampa'](
            [donor, other], {'SULFUROS': .99}, [])
        self.assertEqual([d['q_pls_final'] for d in other['daily']], [90., 91.])
        self.assertAlmostEqual(inventory['SULFUROS'][0], 74.73)

    def test_receptora_respeta_techo_diario_y_cierre_con_inventario(self):
        donor = self.pila('P01', [49.5, 56.77], 181., True, 74.73)
        mature = self.pila('P02', [90., 91.], 181., False)
        inventory = self.motor['_repartir_residuo_rampa'](
            [donor, mature], {'SULFUROS': .99}, [])
        self.assertTrue(all(d['q_pls_final'] <= 99+1e-10 for d in mature['daily']))
        total = sum(sum(d['q_pls_final'] for d in p['daily']) for p in [donor, mature])
        self.assertAlmostEqual(total+inventory['SULFUROS'][0], 362.)
        for p in [donor, mature]:
            self.assertAlmostEqual(sum(d['q_pls_final'] for d in p['daily']), p['q_pls_final'])
            self.assertAlmostEqual(sum(d['q_pls_final']*d['cu_pls_recon'] for d in p['daily']), p['fino_pls_final'])

    def test_receptora_sin_pls_distribuye_en_dias_con_riego(self):
        donor = self.pila('P01', [49.5, 56.77], 181., True, 74.73)
        mature = self.pila('P02', [0., 0.], 0., False)
        inventory = self.motor['_repartir_residuo_rampa'](
            [donor, mature], {'SULFUROS': .99}, [])
        self.assertEqual(inventory, {})
        self.assertAlmostEqual(sum(d['q_pls_final'] for d in mature['daily']), 74.73)

    def test_piso_no_reduce_otra_rampa(self):
        excess = self.pila('P01', [70., 70.], 100., True, -40.)
        ramp = self.pila('P02', [90., 91.], 181., True)
        mature = self.pila('P03', [80., 80.], 160., False)
        self.motor['_repartir_residuo_rampa']([excess, ramp, mature], {'SULFUROS': .99}, [])
        self.assertEqual([d['q_pls_final'] for d in ramp['daily']], [90., 91.])
        self.assertAlmostEqual(mature['q_pls_final'], 120.)


if __name__ == '__main__':
    unittest.main()
