"""Metodo "Maduras fijas, nuevas absorben" para Sulfuros, con la salida del metodo existente (sin SQL).

Se apoya en `sulfide_method.reconcile_sulfides` (que entrega el neto observado de las maduras, el perfil de las nuevas y
las filas diarias) y reemplaza el reparto de las pilas por `reconciliacion_pad.reconcile_pad` + `expand_to_days`:
  * las maduras conservan su recuperacion observada (neto diario y acumulado exactos, `reconciled_pct` no se toca);
  * las pilas nuevas (<= 30 dias) absorben el residuo para cerrar F29 y los flujos globales dentro de `banda`;
  * los dias de meses anteriores al Caso quedan intactos (no se emiten ni se modifican).
La salida tiene el mismo formato que `reconcile_sulfides` (mismas columnas de fila), de modo que el resto de la pantalla
no distingue el metodo. Campos que este metodo no produce de la misma forma: `water_by_young` (balance de agua por pila
nueva: no aplica) y la comparacion de concentraciones del metodo anterior (se reemplaza por el resumen del pad).
No hay persistencia: el resultado solo vive en memoria del dash.
"""
from __future__ import annotations

from copy import deepcopy

import pandas as pd

from . import reconciliacion_pad as RP
from . import mensajes_pad as MP

METODO_REPARTO = 'reparto'
METODO_MADURAS_FIJAS = 'maduras_fijas'
ETIQUETAS = {METODO_REPARTO: 'Reparto por aporte', METODO_MADURAS_FIJAS: 'Maduras fijas, nuevas absorben'}
METODO_DEFAULT = METODO_MADURAS_FIJAS


def etiqueta(metodo):
    return ETIQUETAS.get(metodo, ETIQUETAS[METODO_DEFAULT])


class MetodoInfactible(ValueError):
    """El metodo no puede cerrar el pad; `mensajes` explica la causa para el operador."""

    def __init__(self, mensajes):
        self.mensajes = mensajes
        super().__init__(' '.join(f"{m['titulo']}: {m['texto']} {m['accion'] or ''}".strip() for m in mensajes))


def _day(d):
    return pd.Timestamp(d).date().isoformat()


def aplicar_maduras_fijas(result, audit, rows, ws, we, conc_targets, net_target_t, banda=None, tope_drenaje=1.0):
    """Reemplaza el ajuste de `reconcile_sulfides` por el de maduras fijas. Devuelve `(result2, audit2, mensajes)`.

    `result`/`audit`: salida de `reconcile_sulfides` (no se modifican). `conc_targets`: dict con
    `q_riego_m3h_sum`, `q_pls_m3h_sum`, `cu_riego_g_l`, `cu_pls_g_l`. Si el pad no cierra se levanta `MetodoInfactible`."""
    banda = RP.BAND_DEFAULT if banda is None else banda
    s, e = _day(ws), _day(we)
    prev = (pd.Timestamp(ws) - pd.Timedelta(days=1)).date().isoformat()
    if any(conc_targets.get(k) is None for k in ('q_riego_m3h_sum', 'q_pls_m3h_sum', 'cu_riego_g_l', 'cu_pls_g_l')):
        raise MetodoInfactible([MP.mensaje(MP.ERROR, 'Faltan flujos globales del run',
                                           'El run oficial no trae riego, PLS o sus finos del pad de Sulfuros; el método no puede cerrar el pad.',
                                           'Revisar el run oficial del Caso o usar el método «Reparto por aporte».', None, 'Sulfuros')])
    lam = audit['lambda'] if audit.get('lambda') is not None else 1.0
    by = {(r['pile'], _day(r['date'])): r for r in result}
    nets, nets_day = {}, {}
    days = [d.date().isoformat() for d in pd.date_range(s, e)]
    for key in audit['mature']:
        p = key[1]
        cu_tf = by[(p, prev)]['cu_apilado_t']; last = by[(p, prev)]['official_pct']; daily = {}
        for d in days:
            v = by[(p, d)].get('reconciled_pct')
            if v is None:
                continue
            daily[d] = cu_tf * (v - last) / 100; last = v
        nets_day[p] = daily; nets[p] = sum(daily.values())
    # `window_priors` distingue nuevas por la presencia del perfil de drenaje; las maduras no lo llevan (su drenaje es un proxy)
    mature_names = {k[1] for k in audit['mature']}
    rows = [{k: v for k, v in r.items() if k != 'profile_q_drenaje_m3h'} if r['pile'] in mature_names else r for r in rows]
    priors = RP.window_priors(rows, s, lam)
    cierre = RP.closed_days_check(rows, s, e)
    res = RP.reconcile_pad(priors, nets, conc_targets, net_target_t, tolerance=banda, net_tolerance=banda,
                           max_drain_ratio=tope_drenaje, cierre=cierre)
    if res['status'] != 'ok':
        raise MetodoInfactible(MP.mensajes_reconciliacion_pad(res, banda=banda))
    daily = RP.expand_to_days(rows, s, res, nets_day, lam)
    out = deepcopy(result)
    index = {(r['pile'], _day(r['date'])): i for i, r in enumerate(out)}
    young_piles = {p['pile'] for p in res['por_pila'] if p['young']}
    by_pile_day = {}
    for d in daily:
        by_pile_day[(d['pile'], d['date'])] = d
        row = out[index[(d['pile'], d['date'])]]
        row['q_riego_recon_m3h'] = d['q_riego']
        row['cu_riego_recon_gL'] = d['cu_riego']
        row['cu_drenaje_recon_gL'] = d['cu_pls']
        row['fitted_q_drenaje_m3h'] = d['q_pls']
    for pile in young_piles:
        pct = by[(pile, prev)]['official_pct'] or 0.0
        cu_tf = by[(pile, prev)]['cu_apilado_t']
        for day in days:
            i = index[(pile, day)]
            d = by_pile_day.get((pile, day))
            if d is not None:
                pct += 100 * d['net_t'] / cu_tf
            else:                                             # sin riego: sin flujo ni Cu ese dia
                out[i]['fitted_q_drenaje_m3h'] = 0.0
            out[i]['reconciled_pct'] = pct
    curve_net = sum(by[(p, prev)]['cu_apilado_t'] * (out[index[(p, e)]]['reconciled_pct'] - by[(p, prev)]['official_pct']) / 100
                    for p in {k[1] for k in list(audit['mature']) + list(audit['young'])})
    audit2 = dict(audit)
    audit2.update(
        curve_net_t=curve_net, delivered_net_t=curve_net, net_residual_t=float(net_target_t) - curve_net, water_by_young={},
        concentration_match=dict(status='maduras_fijas', motivo=None, banda=banda, diferencia=res['diferencia'], pad=res['pad'], objetivo=res['objetivo']),
        method='maduras fijas, nuevas absorben', metodo=METODO_MADURAS_FIJAS, banda=banda, tope_drenaje=tope_drenaje, cierre=cierre,
        por_pila=[{k: (float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v) for k, v in p.items()} for p in res['por_pila']],
        water_qualification='Metodo maduras fijas: el drenaje de las maduras es un proxy (0,95 x riego) ajustado al neto observado; no es balance de agua medido.')
    recup = {}
    for pile in young_piles:
        end_row = by[(pile, e)]
        off = end_row.get('observed_pct')
        if off is not None:
            recup[pile] = dict(metodo_pct=out[index[(pile, e)]]['reconciled_pct'], oficial_pct=off, cu_apilado_t=by[(pile, prev)]['cu_apilado_t'])
    audit2['recuperaciones_nuevas'] = recup
    msgs = MP.mensajes_reconciliacion_pad(res, banda=banda, recuperaciones=recup, tope_drenaje=tope_drenaje)
    return out, audit2, msgs
