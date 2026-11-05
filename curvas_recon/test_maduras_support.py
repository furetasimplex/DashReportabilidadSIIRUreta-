"""Datos sinteticos compartidos por las pruebas de "maduras fijas, nuevas moviles".

Sin pruebas propias. ``pile_rows`` fabrica filas diarias en el contrato del
nucleo; ``expected_target`` calcula el Cu neto desde los flujos crudos por una
via independiente del metodo (balance Q x Cu), para verificar el cierre.
"""
from datetime import date, timedelta

DAY = timedelta(days=1)


def d(value):
    return value if isinstance(value, date) else date.fromisoformat(value)


def pile_rows(pad, pile, *, birth, start, end, campaign=11, cu_tf=1000.0,
              pct_per_day=0.05, rec0=10.0, first_row=None, q=100.0, cu_riego=0.4,
              cu_drenaje=2.0, qd=80.0, obs_delta=0.02):
    """Filas diarias de una cohorte: historia, baseline y ventana del Caso.

    ``first_row``: primer dia con fila (por defecto 3 dias antes del Caso o el
    nacimiento, lo que ocurra primero). Recuperacion oficial lineal; la
    observada difiere ``obs_delta`` dentro de la ventana para que una madura
    pruebe que conserva la observada y no la oficial.
    """
    start, end, birth = d(start), d(end), d(birth)
    first = d(first_row) if first_row else min(start - 3 * DAY, birth)
    rows, day, i = [], first, 0
    while day <= end:
        official = rec0 + pct_per_day * i
        row = dict(pad=pad, pile=pile, campaign=campaign, date=day.isoformat(),
                   official_pct=official,
                   observed_pct=official + (obs_delta if day >= start else 0.0),
                   cu_apilado_t=cu_tf, first_irrigation=birth.isoformat(),
                   observation_source='Recuperaciones_pad (primary)')
        if start <= day <= end and day >= birth:
            k = (day - start).days % 3
            row.update(q_riego_m3h=q + k, cu_riego_gL=cu_riego, cu_drenaje_gL=cu_drenaje + 0.1 * k,
                       profile_q_drenaje_m3h=qd + k,
                       drainage_profile_source='saved allocation run 1; modeled/reconciled, not measured')
        rows.append(row)
        day += DAY
        i += 1
    return rows


def expected_target(rows, start, end, lam):
    """Cu neto (t) que entrega el PAD con factor ``lam``, calculado aparte."""
    start, end = d(start), d(end)
    groups = {}
    for r in rows:
        groups.setdefault((r['pile'], r['campaign']), {})[d(r['date'])] = r
    total = 0.0
    for group in groups.values():
        any_row = next(iter(group.values()))
        birth, cu = d(any_row['first_irrigation']), any_row['cu_apilado_t']
        age = (end - birth).days
        active = max(start, birth)
        base = group[active - DAY]['official_pct'] if (active - DAY) in group else 0.0
        if age > 30:
            total += cu * (group[end]['observed_pct'] - base) / 100
        elif age == 30:
            total += cu * (group[end]['official_pct'] - base) / 100
        else:
            day = active
            while day <= end:
                r = group[day]
                total += .024 * (lam * r['profile_q_drenaje_m3h'] * r['cu_drenaje_gL']
                                 - r['q_riego_m3h'] * r['cu_riego_gL'])
                day += DAY
    return total


def mixed_pad(pad='SULFUROS', start='2026-09-01', end='2026-09-07'):
    """3 maduras, 1 frontera (30 d), 2 nuevas (una nace a mitad de ventana)."""
    rows = []
    rows += pile_rows(pad, 'P01', birth='2025-10-01', start=start, end=end, cu_tf=5000, rec0=60)
    rows += pile_rows(pad, 'P02', birth='2025-12-15', start=start, end=end, cu_tf=4000, rec0=50)
    rows += pile_rows(pad, 'P03', birth='2026-04-01', start=start, end=end, cu_tf=3000, rec0=40)
    rows += pile_rows(pad, 'P04', birth='2026-08-08', start=start, end=end, cu_tf=2500, rec0=20)  # edad 30
    rows += pile_rows(pad, 'P05', birth='2026-08-20', start=start, end=end, cu_tf=2000, rec0=8)   # 18 d
    rows += pile_rows(pad, 'P06', birth='2026-09-04', start=start, end=end, cu_tf=1800, rec0=0.0,
                      first_row='2026-09-04', pct_per_day=0.1)                                    # nace en ventana
    return rows
