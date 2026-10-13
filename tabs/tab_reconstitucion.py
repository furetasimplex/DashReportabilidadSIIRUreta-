"""Puente de sección lateral SIIR sin consulta SQL al montar."""
from reconstitucion.panel import build_layout, register_callbacks as _register_callbacks, configure

SOURCE_SCHEMA = 'inventar_SpcHidr.inventar_SpcHidr'


def _host_engine():
    """Usa la conexión SIIR únicamente cuando se solicita cargar datos."""
    from db_connection import get_engine
    return get_engine()

def _host_casos():
    from curvas_recon.db_pipeline import load_casos
    return load_casos()


def layout():
    return build_layout()

def register_callbacks(app):
    """Configura la fuente explícita y registra callbacks una sola vez."""
    configure(_host_engine, schema=SOURCE_SCHEMA)
    _register_callbacks(app, case_loader=_host_casos)
