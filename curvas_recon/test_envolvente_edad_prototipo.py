"""Experimento offline: limita el dial de la rampa real, sin recortar resultados.

La envolvente lineal 10% día 1 -> 99% día 30 es SOLO una hipótesis de prueba.
No se importa SQL ni se modifica el motor productivo.
"""
import unittest
from curvas_recon import ramp_curve as ramp


def techo(dia, cap=.99):
    if dia is None or dia < 1:
        return 0.
    return min(cap, .10 + (cap - .10) * (dia - 1) / 29.)


def ajustar_acotado(q, dc, target, cap=.99, f0=None, n0=None, alpha=ramp.RAMP_ALPHA):
    """Prototype: restrict feasible t BEFORE solving weekly volume."""
    if len(q) != len(dc) or any(x < 0 for x in q):
        raise ValueError('Entradas inválidas')
    cont = f0 is not None and n0 is not None
    if (f0 is None) != (n0 is None):
        raise ValueError('Estado incompleto')
    active = [i for i, (qi, n) in enumerate(zip(q, dc)) if qi > 0 and n is not None and n >= 1]
    if cont and any(dc[i] < n0 for i in active):
        raise ValueError('Ventana anterior al estado heredado')

    def curva(t):
        if cont:
            fs = ramp.factores_desde(dc, cap*t, f0, n0, alpha)
        else:
            m, ini, a = ramp.parametros(t, cap, alpha)
            fs = ramp.factores(dc, m, ini, a)
        return [fs[i] if i in active else 0. for i in range(len(q))]

    def factible(t):
        fs = curva(t)
        return all(fs[i] <= techo(dc[i], cap) + 1e-12 for i in active)

    low = ramp.tension_minima(f0, cap) if cont else 0.
    if not factible(low):
        raise ValueError('Estado heredado supera el techo por edad; requiere recalcular antecedentes')
    lo, hi = low, 1.
    for _ in range(90):
        mid = (lo+hi)/2
        if factible(mid):
            lo = mid
        else:
            hi = mid
    tmax = lo
    area = lambda t: sum(qi*fi for qi, fi in zip(q, curva(t)))
    amin, amax = area(low), area(tmax)
    status = 'piso' if target < amin - 1e-9 else 'infactible' if target > amax + 1e-9 else 'ok'
    lo, hi = low, tmax
    bounded = min(max(target, amin), amax)
    for _ in range(90):
        mid = (lo+hi)/2
        if area(mid) < bounded:
            lo = mid
        else:
            hi = mid
    t = (lo+hi)/2
    fs = curva(t)
    m, ini, a = (cap*t, f0, alpha) if cont else ramp.parametros(t, cap, alpha)
    delivered = sum(qi*fi for qi, fi in zip(q, fs))
    return dict(factores=fs, entregado=delivered, residuo=target-delivered,
                status=status, tension=t, alpha=a, meseta=m,
                f_fin=fs[active[-1]] if active else f0,
                n_fin=dc[active[-1]] if active else n0)


class EnvolventeEdad(unittest.TestCase):
    def verify(self, result, q, dc, target):
        active = [f for f, qi, n in zip(result['factores'], q, dc) if qi > 0 and n is not None and n >= 1]
        self.assertTrue(all(a <= b+1e-9 for a, b in zip(active, active[1:])))
        self.assertTrue(all(f <= techo(n)+1e-9 for f, n in zip(result['factores'], dc)))
        self.assertAlmostEqual(result['entregado']+result['residuo'], target, places=8)

    def test_01_semana_joven_alta_demanda(self):
        q, dc = [100.]*7, list(range(1, 8))
        old = ramp.ajustar(q, dc, .95*sum(q), .99)
        new = ajustar_acotado(q, dc, .95*sum(q))
        self.assertGreater(old['factores'][-1], techo(7))
        self.verify(new, q, dc, .95*sum(q))
        self.assertEqual(new['status'], 'infactible')
        self.assertGreater(new['residuo'], 0.)

    def test_02_continuidad_cinco_ventanas(self):
        prev = None
        for start, end in ((1,7),(8,14),(15,21),(22,28),(29,35)):
            dc = list(range(start,end+1)); q = [100.]*len(dc)
            kw = dict(f0=prev['f_fin'], n0=prev['n_fin'], alpha=prev['alpha']) if prev else {}
            r = ajustar_acotado(q, dc, .95*sum(q), **kw)
            self.verify(r, q, dc, .95*sum(q))
            if prev:
                self.assertGreaterEqual(r['factores'][0]+1e-9, prev['f_fin'])
                inherited = ramp.factores_desde([prev['n_fin']], r['meseta'], prev['f_fin'], prev['n_fin'], prev['alpha'])[0]
                self.assertAlmostEqual(inherited, prev['f_fin'])
            prev = r

    def test_03_borde_compartido_y_repeticion(self):
        first = ajustar_acotado([100.]*7, list(range(1,8)), 650.)
        kw = dict(f0=first['f_fin'], n0=7, alpha=first['alpha'])
        a = ajustar_acotado([100.]*8, list(range(7,15)), 740., **kw)
        b = ajustar_acotado([100.]*8, list(range(7,15)), 740., **kw)
        self.assertEqual(a, b)
        self.assertAlmostEqual(a['factores'][0], first['f_fin'])
        self.verify(a, [100.]*8, list(range(7,15)), 740.)

    def test_04_objetivo_factible_cierra(self):
        r = ajustar_acotado([100.]*7, list(range(1,8)), 80.)
        self.assertEqual(r['status'], 'ok')
        self.assertAlmostEqual(r['residuo'], 0., places=8)

    def test_05_sin_riego_y_dias_previos(self):
        q, dc = [0.,100.,0.,100.], [None,1,2,3]
        r = ajustar_acotado(q, dc, 100.)
        self.assertEqual(r['factores'][0], 0.)
        self.assertEqual(r['factores'][2], 0.)
        self.verify(r, q, dc, 100.)

    def test_06_estado_antiguo_incompatible_no_se_recorta(self):
        with self.assertRaisesRegex(ValueError, 'recalcular antecedentes'):
            ajustar_acotado([100.]*7, list(range(8,15)), 600., f0=.8, n0=7)

    def test_07_objetivo_bajo_declara_residuo_negativo(self):
        r = ajustar_acotado([100.]*7, list(range(15,22)), 1., f0=.2, n0=14)
        self.assertEqual(r['status'], 'piso')
        self.assertLess(r['residuo'], 0.)
        self.verify(r, [100.]*7, list(range(15,22)), 1.)

    def test_08_regimen_misma_curva_del_motor(self):
        q, dc = [100.]*7, list(range(31,38))
        kw = dict(f0=.8, n0=30, alpha=ramp.RAMP_ALPHA)
        old = ramp.ajustar(q, dc, .85*sum(q), .99, **kw)
        new = ajustar_acotado(q, dc, .85*sum(q), **kw)
        for a,b in zip(old['factores'], new['factores']):
            self.assertAlmostEqual(a,b,places=9)

    def test_09_sin_capacidad_residuo_explicito(self):
        r = ajustar_acotado([0.]*7, list(range(1,8)), 40.)
        self.assertEqual(r['entregado'], 0.)
        self.assertEqual(r['residuo'], 40.)


def resumen():
    rows = []
    old_prev = new_prev = None
    for start,end in ((1,7),(8,14),(15,21),(22,28),(29,35)):
        dc = list(range(start,end+1)); q = [100.]*len(dc); target = .95*sum(q)
        oldkw = dict(f0=old_prev['f_fin'], n0=old_prev['n_fin'], alpha=old_prev['alpha']) if old_prev else {}
        newkw = dict(f0=new_prev['f_fin'], n0=new_prev['n_fin'], alpha=new_prev['alpha']) if new_prev else {}
        old = ramp.ajustar(q, dc, target, .99, **oldkw)
        new = ajustar_acotado(q, dc, target, **newkw)
        rows.append(f'| {start}–{end} | {old["f_fin"]:.1%} | {new["f_fin"]:.1%} | {techo(end):.1%} | {new["residuo"]:.2f} |')
        old_prev,new_prev = old,new
    return '\n'.join(rows)


if __name__ == '__main__':
    unittest.main()
