# tabs/tabreportabilidad.py
from dash import html
import dash_bootstrap_components as dbc

# Layout y callbacks del módulo
from report_export.layouts.reportabilidad_page import layout as layout_reportabilidad
import report_export.callbacks.reportabilidad_cb  # <-- registra los callbacks

def layout():
    # Si usas un contenedor/estilo propio, envuelve el layout del módulo:
    return dbc.Container([
        layout_reportabilidad()
    ], fluid=True)