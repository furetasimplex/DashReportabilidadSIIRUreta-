"""Production functions via AST: no module imports, SQL, credentials or writes."""
import ast
from pathlib import Path
import unittest


def motor_local():
    source = Path(__file__).with_name('recon_engine.py').read_text(encoding='utf-8')
    names = {'_split_fino', '_resembrar_fino_pila', '_repartir_residuo_rampa',
             '_absorber_piso_rampa'}
    nodes = [node for node in ast.parse(source).body
             if isinstance(node, ast.FunctionDef) and node.name in names]
    ns = {'FDRENA_RECON_MAX': .99}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'recon_engine.py', 'exec'), ns)
    return ns


def pila(name, q, f, delivered=None, rampa=False, protected=False, residual=0., q_riego=300.):
    delivered = q if delivered is None else delivered
    return dict(label='SULFUROS', parcela=name, q_pls_final=q,
                fino_pls_final=f, q_pls_medido=q, en_rampa=rampa,
                transition_protected=protected, ramp_residuo=residual,
                daily=[dict(q_riego_final=q_riego, q_riego_medido=q_riego,
                            q_pls_final=delivered, fino_pls_medido=f,
                            fino_pls_final=f, cu_pls_recon=f/delivered if delivered else None)])


class ConservacionCu(unittest.TestCase):
    def setUp(self):
        self.motor = motor_local()

    def aplicar(self, piles):
        q_target = sum(p['q_pls_final'] for p in piles)
        f_target = sum(p['fino_pls_final'] for p in piles)
        warnings = []
        inventory = self.motor['_repartir_residuo_rampa'](piles, {'SULFUROS': .99}, warnings)
        iq, iff = inventory.get('SULFUROS', (0., 0.))
        self.assertAlmostEqual(sum(p['q_pls_final'] for p in piles) + iq, q_target, places=8)
        self.assertAlmostEqual(sum(p['fino_pls_final'] for p in piles) + iff, f_target, places=8)
        for p in piles:
            self.assertGreaterEqual(p['q_pls_final'], 0)
            self.assertGreaterEqual(p['fino_pls_final'], 0)
            self.assertAlmostEqual(sum(d['q_pls_final'] for d in p['daily']), p['q_pls_final'])
            self.assertAlmostEqual(sum(d['fino_pls_final'] or 0 for d in p['daily']), p['fino_pls_final'])
            for d in p['daily']:
                self.assertGreaterEqual(d['q_pls_final'], 0)
                self.assertGreaterEqual(d['fino_pls_final'] or 0, 0)
                if d['q_pls_final'] > 0:
                    self.assertAlmostEqual(d['q_pls_final']*d['cu_pls_recon'], d['fino_pls_final'] or 0)
                else:
                    self.assertEqual(d['fino_pls_final'] or 0, 0)
        return inventory, warnings

    def test_piso_alta_ley_no_crea_cu(self):
        floor = pila('P23', 100., 1000., 110., True, residual=-10.)
        mature = pila('P07', 200., 200.)
        inv, _ = self.aplicar([floor, mature])
        self.assertEqual(inv, {})
        self.assertAlmostEqual(mature['q_pls_final'], 190.)
        self.assertAlmostEqual(mature['fino_pls_final'], 100.)
        self.assertAlmostEqual(mature['devuelve_piso_rampa_f'], 100.)

    def test_piso_baja_ley_no_pierde_cu(self):
        floor = pila('P23', 100., 100., 110., True, residual=-10.)
        mature = pila('P07', 200., 2000.)
        inv, _ = self.aplicar([floor, mature])
        self.assertEqual(inv, {})
        self.assertAlmostEqual(mature['fino_pls_final'], 1990.)

    def test_falta_cu_declara_termino_negativo(self):
        floor = pila('P23', 100., 1000., 110., True, residual=-10.)
        mature = pila('P07', 200., 50.)
        inv, warnings = self.aplicar([floor, mature])
        self.assertAlmostEqual(inv['SULFUROS'][0], 0.)
        self.assertAlmostEqual(inv['SULFUROS'][1], -50.)
        self.assertEqual(mature['fino_pls_final'], 0.)
        self.assertTrue(any('no demuestra' in warning for warning in warnings))

    def test_falta_caudad_y_cu_declara_ambos_con_signo(self):
        floor = pila('P23', 100., 100., 400., True, residual=-300., q_riego=500.)
        mature = pila('P07', 200., 100.)
        inv, _ = self.aplicar([floor, mature])
        self.assertEqual(inv['SULFUROS'], (-100., -200.))

    def test_sin_caudad_no_publica_cu_sin_transporte(self):
        floor = pila('P23', 100., 10., 200., True, residual=-100.)
        mature = pila('P07', 100., 100.)
        inv, _ = self.aplicar([floor, mature])
        self.assertEqual(inv['SULFUROS'], (0., 90.))
        self.assertEqual(mature['fino_pls_final'], 0.)

    def test_sin_receptora_no_oculta_piso(self):
        floor = pila('P23', 100., 100., 110., True, residual=-10.)
        inv, _ = self.aplicar([floor])
        self.assertAlmostEqual(inv['SULFUROS'][0], -10.)
        self.assertAlmostEqual(inv['SULFUROS'][1], -10.)

    def test_piso_y_residuo_positivo_simultaneos(self):
        floor = pila('P23', 100., 1000., 110., True, residual=-10.)
        donor = pila('P02', 100., 100., 80., True, residual=20.)
        mature = pila('P07', 200., 200.)
        inv, _ = self.aplicar([floor, donor, mature])
        self.assertEqual(inv, {})
        self.assertAlmostEqual(mature['q_pls_final'], 210.)
        self.assertAlmostEqual(mature['fino_pls_final'], 120.)

    def test_residuos_firmados_no_se_sobrescriben(self):
        floor = pila('P23', 100., 1000., 110., True, residual=-10.)
        donor = pila('P02', 100., 100., 80., True, residual=20.)
        inv, _ = self.aplicar([floor, donor])
        self.assertAlmostEqual(inv['SULFUROS'][0], 10.)
        self.assertAlmostEqual(inv['SULFUROS'][1], -80.)

    def test_cola_protegida_no_es_receptora_ni_donante_del_piso(self):
        floor = pila('P23', 100., 100., 110., True, residual=-10.)
        tail = pila('P02', 100., 100., protected=True)
        inv, _ = self.aplicar([floor, tail])
        self.assertAlmostEqual(inv['SULFUROS'][0], -10.)
        self.assertEqual(tail['q_pls_final'], 100.)
        donor = pila('P01', 100., 100., 80., True, residual=20.)
        inv, _ = self.aplicar([donor, tail])
        self.assertAlmostEqual(inv['SULFUROS'][0], 20.)
        self.assertEqual(tail['q_pls_final'], 100.)

    def test_objetivo_cero_no_inventa_concentracion_para_el_piso(self):
        floor = pila('P23', 0., 0., 10., True, residual=-10.)
        mature = pila('P07', 100., 100.)
        inv, _ = self.aplicar([floor, mature])
        self.assertEqual(inv, {})
        self.assertEqual(floor['fino_pls_final'], 0.)
        self.assertEqual(mature['fino_pls_final'], 100.)


if __name__ == '__main__':
    unittest.main()
