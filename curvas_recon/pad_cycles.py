#!/usr/bin/env python3
"""pad_cycles.py — Segmentacion del historico de recuperacion en campanas (ciclos)."""

GAP_DAYS = 7
RESET_DROP = 15
RESET_MAX_VALUE = 20


def split_into_cycles(dates: list, values: list, global_last_date) -> list:
    """
    Corta (dates, values) en campanas. Nueva campana quando, entre lecturas
    consecutivas: hay un hueco > GAP_DAYS dias, o el valor cae mas de
    RESET_DROP puntos y queda bajo RESET_MAX_VALUE (reinicio de lixiviacion).

    Solo la ULTIMA campana de la lista evalua 'finished' contra
    global_last_date; toda campana anterior queda finished=True (ya fue
    superada por una campana posterior, sin importar la distancia de fechas).
    """
    if not dates:
        return []

    raw_cycles = []
    cur_dates = [dates[0]]
    cur_values = [values[0]]

    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days > GAP_DAYS
        reset = values[i] < values[i - 1] - RESET_DROP and values[i] < RESET_MAX_VALUE
        if gap or reset:
            raw_cycles.append((cur_dates, cur_values))
            cur_dates = [dates[i]]
            cur_values = [values[i]]
        else:
            cur_dates.append(dates[i])
            cur_values.append(values[i])
    raw_cycles.append((cur_dates, cur_values))

    cycles = []
    last_index = len(raw_cycles) - 1
    for idx, (c_dates, c_values) in enumerate(raw_cycles):
        end_date = c_dates[-1]
        if idx < last_index:
            finished = True
        elif global_last_date is None:
            finished = True
        else:
            finished = (global_last_date - end_date).days > GAP_DAYS
        cycles.append(dict(
            dates=c_dates, values=c_values,
            start_date=c_dates[0], end_date=end_date,
            finished=finished,
        ))
    return cycles
