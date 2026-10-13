#!/usr/bin/env python3
"""pad_selection.py — Logica pura de seleccion de parcelas (sin Dash)."""


def toggle_selection(current: list, clicked_id: str, compare_mode: bool) -> list:
    """
    Modo unico (compare_mode=False): clic reemplaza la seleccion; clic sobre
    la parcela ya seleccionada la deselecciona (vuelve a lista vacia).
    Modo comparacion (compare_mode=True): clic agrega/quita de la seleccion.
    """
    current = list(current or [])
    if not compare_mode:
        return [] if clicked_id in current else [clicked_id]
    if clicked_id in current:
        return [x for x in current if x != clicked_id]
    return current + [clicked_id]
