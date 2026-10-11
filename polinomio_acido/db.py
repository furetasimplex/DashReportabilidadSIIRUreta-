"""Persistencia versionada para la configuracion del polinomio de acido."""
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import text

from db_connection import get_engine

TABLA = "inventar_SpcHidr.dosis_acido_configuracion"
PARAMETROS = (
    ("umbral_mineral", "Umbral mineral", "Umbrales"),
    ("umbral_co3", "Umbral CO3", "Umbrales"),
    ("tasa_minima", "Tasa minima", "Baja solubilidad"),
    ("tasa_base", "Tasa base", "Baja solubilidad"),
    ("factor_co3", "Factor CO3", "Baja solubilidad"),
    ("factor_cus_co3_sobre_025", "Factor CuS", "CO3 sobre umbral"),
    ("tasa_base_co3_sobre_025", "Tasa base", "CO3 sobre umbral"),
    ("factor_co3_co3_sobre_025", "Factor CO3", "CO3 sobre umbral"),
    ("factor_cus_mineral_oxido", "Factor CuS", "Mineral oxido"),
    ("tasa_basal_mineral_oxido", "Tasa basal", "Mineral oxido"),
    ("factor_co3_mineral_oxido", "Factor CO3", "Mineral oxido"),
)
NOMBRES_PARAMETROS = tuple(item[0] for item in PARAMETROS)
ESCALA = Decimal("0.000001")
MAX_DECIMAL_18_6 = Decimal("999999999999.999999")


def _engine():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("No existe una conexion disponible para administrar el polinomio de acido.")
    return engine


def _decimal6(nombre, valor):
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{nombre}: ingrese un numero valido.") from None
    if not numero.is_finite():
        raise ValueError(f"{nombre}: ingrese un numero finito.")
    if numero.as_tuple().exponent < -6:
        raise ValueError(f"{nombre}: use como maximo 6 decimales.")
    if abs(numero) > MAX_DECIMAL_18_6:
        raise ValueError(f"{nombre}: el valor excede DECIMAL(18,6).")
    return numero.quantize(ESCALA)


def validar_configuracion(valores, usuario, comentario=None):
    """Valida el contrato completo; nunca admite configuraciones parciales."""
    if not isinstance(valores, dict):
        raise ValueError("La configuracion debe contener los 11 parametros.")
    faltantes = [nombre for nombre in NOMBRES_PARAMETROS if nombre not in valores]
    if faltantes:
        raise ValueError("Faltan parametros: " + ", ".join(faltantes) + ".")
    normalizados = {nombre: _decimal6(nombre, valores[nombre]) for nombre in NOMBRES_PARAMETROS}
    for nombre in ("umbral_mineral", "umbral_co3"):
        if not Decimal("0") <= normalizados[nombre] <= Decimal("1"):
            raise ValueError(f"{nombre}: el umbral debe estar entre 0 y 1.")
    if not isinstance(usuario, str) or not usuario.strip() or len(usuario.strip()) > 128:
        raise ValueError("Se requiere un usuario autenticado de hasta 128 caracteres.")
    if comentario is not None and not isinstance(comentario, str):
        raise ValueError("El comentario no es valido.")
    comentario = (comentario or "").strip() or None
    if comentario and len(comentario) > 500:
        raise ValueError("El comentario puede tener hasta 500 caracteres.")
    return {**normalizados, "usuario_submit": usuario.strip(), "comentario": comentario}


def obtener_configuracion_vigente():
    with _engine().connect() as conn:
        row = conn.execute(text(f"""
            SELECT TOP (1) configuracion_id, {', '.join(NOMBRES_PARAMETROS)},
                   fecha_submit, usuario_submit, comentario
            FROM {TABLA}
            ORDER BY configuracion_id DESC
        """)).mappings().first()
    return dict(row) if row else None


def obtener_historial():
    with _engine().connect() as conn:
        return pd.read_sql(text(f"""
            SELECT configuracion_id, {', '.join(NOMBRES_PARAMETROS)},
                   fecha_submit, usuario_submit, comentario
            FROM {TABLA}
            ORDER BY configuracion_id DESC
        """), conn)


def insertar_configuracion(valores, usuario, comentario, configuracion_esperada):
    """Inserta una version completa si la version revisada sigue vigente."""
    payload = validar_configuracion(valores, usuario, comentario)
    try:
        esperada = int(configuracion_esperada)
    except (TypeError, ValueError):
        raise ValueError("No existe una version vigente confirmada.") from None
    columnas = ", ".join(NOMBRES_PARAMETROS)
    parametros = ", ".join(f":{nombre}" for nombre in NOMBRES_PARAMETROS)
    with _engine().begin() as conn:
        actual = conn.execute(text(f"""
            SELECT TOP (1) configuracion_id
            FROM {TABLA} WITH (UPDLOCK, HOLDLOCK)
            ORDER BY configuracion_id DESC
        """)).scalar()
        if actual != esperada:
            raise ValueError("La configuracion cambio desde la revision. Actualice y confirme nuevamente.")
        row = conn.execute(text(f"""
            INSERT INTO {TABLA}
                ({columnas}, usuario_submit, comentario)
            OUTPUT INSERTED.configuracion_id, INSERTED.fecha_submit,
                   INSERTED.usuario_submit, INSERTED.comentario
            VALUES ({parametros}, :usuario_submit, :comentario)
        """), payload).mappings().one()
    return dict(row)
