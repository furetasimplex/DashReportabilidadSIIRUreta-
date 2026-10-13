"""Puente entre el shell SIIR y el dashboard nativo de curvas.

El módulo conserva navegación y autenticación SIIR: aquí solo se obtiene el
árbol Dash embebible y se registran sus callbacks en la aplicación anfitriona.
La función ``layout`` se invoca al abrir la sección, no al importar el shell.
"""

from dash import html

from curvas_recon.pad_dashboard import (
    build_layout as _build_layout,
    register_callbacks as _register_callbacks,
)


def layout():
    """Devuelve la sección sin encabezado ni navegación duplicados."""
    return html.Div(_build_layout(), className="curvas-recon-shell")


def register_callbacks(app):
    """Registra los callbacks del dashboard una vez durante el arranque."""
    _register_callbacks(app)
