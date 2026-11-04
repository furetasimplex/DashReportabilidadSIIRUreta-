"""Control de las pilas contra los flujos globales de un Caso (propuesta, FUERA del dash).

Este modulo no lo importa el dash ni el informe: se usa solo para probar con datos reales.
Compara, por pad y flujo (riego y PLS), la masa y la concentracion ponderada por caudal de
las pilas con las de los flujos globales del run oficial, y calcula la razon de drenaje de las
maduras (que no tienen sensor) a partir de esos mismos flujos.
"""
from __future__ import annotations

FDRENA_BASE = 0.95


def mature_drainage_ratio(anchor, default=FDRENA_BASE):
    """Drenaje de las maduras / riego: razon PLS/riego MEDIDA de los flujos globales del pad.

    Se usa 0.95 si el ancla no la trae o la razon no es creible (fuera de 0.5-1.2)."""
    q_pls, q_riego = (anchor or {}).get('q_pls_medido'), (anchor or {}).get('q_riego_medido')
    if isinstance(q_pls, (int, float)) and isinstance(q_riego, (int, float)) and q_riego > 0:
        ratio = q_pls / q_riego
        if 0.5 <= ratio <= 1.2:
            return float(ratio)
    return default


def global_concentration(fino_t, masa_m3):
    """g/L = 1000 x fino [t] / masa [m3]."""
    if isinstance(fino_t, (int, float)) and isinstance(masa_m3, (int, float)) and masa_m3 > 0:
        return 1000.0 * fino_t / masa_m3
    return None


def flow_control(daily_rows, anchor_by_label, ratio_by_label=None, tolerance=0.05):
    """Una fila por pad y flujo con masa y Cu de las pilas contra el global.

    `daily_rows`: filas diarias del resultado (label, q_riego_final, q_pls_final, cu_riego_recon,
    cu_pls_recon). El PLS de una pila sin dato de drenaje usa `ratio` x riego. `anchor_by_label`:
    {label: {q_riego_recon, fino_riego_recon, q_pls_recon, fino_pls_recon}}. Una diferencia mayor
    que `tolerance` marca 'revisar'; no cambia ningun calculo."""
    ratio_by_label = ratio_by_label or {}
    rows = []
    for label in ('SULFUROS', 'OXIDOS'):
        daily = [d for d in daily_rows if d.get('label') == label]
        goal = (anchor_by_label or {}).get(label) or {}
        ratio = ratio_by_label.get(label, FDRENA_BASE)
        if not daily:
            continue
        for stream, q_key, cu_key, g_q, g_f in (('riego', 'q_riego_final', 'cu_riego_recon', 'q_riego_recon', 'fino_riego_recon'),
                                                ('PLS', 'q_pls_final', 'cu_pls_recon', 'q_pls_recon', 'fino_pls_recon')):
            q = fino = 0.0
            for d in daily:
                flow = d.get(q_key)
                if flow is None and stream == 'PLS':
                    flow = ratio * (d.get('q_riego_final') or 0.0)
                cu = d.get(cu_key)
                if flow and cu is not None:
                    q += flow
                    fino += flow * cu
            mass, conc = q * 24.0, (fino / q if q > 0 else None)
            g_mass = goal.get(g_q)
            g_conc = global_concentration(goal.get(g_f), g_mass)
            rel = lambda a, b: (a - b) / b if a is not None and b else None
            d_mass, d_conc = rel(mass, g_mass), rel(conc, g_conc)
            status = ('sin objetivo global' if d_mass is None or d_conc is None
                      else 'ok' if abs(d_mass) <= tolerance and abs(d_conc) <= tolerance else 'revisar')
            rows.append(dict(pad=label, flujo=stream, masa_pilas_m3=mass, masa_global_m3=g_mass, dif_masa=d_mass,
                             cu_pilas_gL=conc, cu_global_gL=g_conc, dif_cu=d_conc, estado=status))
    return rows
