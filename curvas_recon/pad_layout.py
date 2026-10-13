#!/usr/bin/env python3
"""pad_layout.py — Componentes Dash del grid trapezoidal de parcelas (PAD)."""
from dash import html

STATUS_COLORS = {
    'activa':    '#2e7d32',
    'inactiva':  '#f9a825',
    'sin_datos': '#bdbdbd',
}
DISABLED_COLOR = '#bdbdbd'
SELECTED_BORDER = '#f57c00'
UNSELECTED_BORDER = '#ced4da'

CLIP_RIGHT = 'polygon(6% 0, 100% 0, 94% 100%, 0 100%)'   # angula el extremo derecho
CLIP_LEFT = 'polygon(0 0, 94% 0, 100% 100%, 6% 100%)'    # angula el extremo izquierdo


def build_cell(pad_id: str, num: int, status: str, selected: list, disabled: bool = False,
               color_map: dict = None, id_type: str = 'curvas-parcela-cell') -> html.Div:
    colors = color_map or STATUS_COLORS
    if disabled:
        return html.Div(
            f'P{num}',
            id=f'curvas-{pad_id}-P{num}-disabled',
            style={
                'backgroundColor': colors.get(status, DISABLED_COLOR),
                'border': f'2px solid {UNSELECTED_BORDER}',
                'color': '#6c757d',
                'textAlign': 'center',
                'padding': '6px 2px',
                'fontSize': '0.72rem',
                'fontWeight': '700',
                'cursor': 'not-allowed',
                'flex': '1',
                'minWidth': '28px',
                'borderRadius': '3px',
                'opacity': '0.5',
            },
        )

    cell_id_str = f'{pad_id}-P{num}'
    is_selected = cell_id_str in (selected or [])
    color = colors.get(status, colors.get('sin_datos', STATUS_COLORS['sin_datos']))
    return html.Div(
        f'P{num}',
        id={'type': id_type, 'pad': pad_id, 'num': num},
        n_clicks=0,
        style={
            'backgroundColor': color,
            'border': f'2px solid {SELECTED_BORDER if is_selected else UNSELECTED_BORDER}',
            'color': '#ffffff',
            'textAlign': 'center',
            'padding': '6px 2px',
            'fontSize': '0.72rem',
            'fontWeight': '700',
            'cursor': 'pointer',
            'flex': '1',
            'minWidth': '28px',
            'borderRadius': '3px',
            'opacity': '1',
        },
    )


def build_row(pad_id: str, order: list, data: dict, selected: list, taper: str = 'right',
              color_map: dict = None, id_type: str = 'curvas-parcela-cell') -> html.Div:
    cells = [
        build_cell(
            pad_id, num,
            data.get(num, {}).get('status', 'sin_datos'),
            selected,
            disabled=data.get(num, {}).get('disabled', False),
            color_map=color_map,
            id_type=id_type,
        )
        for num in order
    ]
    return html.Div(
        cells,
        style={
            'display': 'flex',
            'gap': '2px',
            'clipPath': CLIP_RIGHT if taper == 'right' else CLIP_LEFT,
            'padding': '4px 14px',
        },
    )


def build_pad(pad_id: str, title: str, top_order: list, bottom_order: list,
              data: dict, selected: list, color_map: dict = None, id_type: str = 'curvas-parcela-cell') -> html.Div:
    return html.Div([
        html.H6(title, style={'color': '#f57c00', 'textAlign': 'center', 'marginBottom': '4px'}),
        build_row(pad_id, top_order, data, selected, taper='right', color_map=color_map, id_type=id_type),
        build_row(pad_id, bottom_order, data, selected, taper='left', color_map=color_map, id_type=id_type),
    ], style={'marginBottom': '18px'})


# Mapa de estado para la pestana de reconciliacion MHE (grid coloreado por estado)
# La grilla de Reconciliacion ya no marca transiente vs estado estacionario:
# esa division es interna del motor (define a quien se le reparte la
# correccion de caudal) y no es lo que el operador lee en el pad. Quedan tres
# estados: activa, activa nueva (empezo a regar dentro de la ventana) e
# inactiva.
RECON_STATUS_COLORS = {
    'activa':        '#2E9E5B',   # verde
    'activa_nueva':  '#EA5B0C',   # naranja SIIR
    'inactiva':      '#9CA3AF',   # gris
    'sin_datos':     '#bdbdbd',
}
