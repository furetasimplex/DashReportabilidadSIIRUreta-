"""Lecturas SELECT-only para la reconstitucion por densidad recalibrada.

Fuentes de la seccion 4 de docs/METODOLOGIA_RECONSTITUCION_DENSIDAD_RECALIBRADA.md
que no leen ya ``db_source`` ni ``modelo_flujos``:

    * nacimiento de las campanas (control_apilado_diario);
    * identidad fisica del modulo y parcela (``<SIIR>.modulo``);
    * modulos fijados: ``reclamo.v_modulo_base`` (estado CONGELADO) y
      ``<SIIR>.disponible_rotopalas`` (TMH fijada directa).

Nunca ejecuta SP, escrituras ni publicaciones. La conexion es la inyectada en
``db_source.configure``. Las pruebas reemplazan estas funciones por mocks.

El perfil de TMH/humedad de la historia se lee con ``modelo_flujos.load_profile``
(mismo SELECT que la ventana del Caso) y el volumen con ``db_source.load_apilado``.
"""
from __future__ import annotations

import re

import pandas as pd
from sqlalchemy import text

from . import db_source as dbs

SCHEMA_RECLAMO = "reclamo"
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?")


def _ids(values):
    ids = sorted({int(v) for v in values if pd.notna(v)})
    return ", ".join(str(i) for i in ids)


def load_nacimientos(start, end, engine=None):
    """Primer dia con volumen de cada campana tecnica activa en [start, end].

    Devuelve ``pad_id, campana_id, nacimiento``. La historia de asignacion
    arranca ahi (seccion 5), no al inicio del Caso."""
    sql = text(f"""
        SELECT a.pad_id, a.[campaña_id] AS campana_id,
               MIN(a.fecha) AS nacimiento
        FROM {dbs.SCHEMA}.control_apilado_diario a
        WHERE a.volumen_diario_m3 > 0 AND a.fecha < DATEADD(day, 1, :end)
          AND a.[campaña_id] IN (
              SELECT DISTINCT b.[campaña_id]
              FROM {dbs.SCHEMA}.control_apilado_diario b
              WHERE b.volumen_diario_m3 > 0
                AND b.fecha >= :start AND b.fecha < DATEADD(day, 1, :end))
        GROUP BY a.pad_id, a.[campaña_id]
    """)
    df = pd.read_sql(sql, engine or dbs.get_engine(), params={
        "start": pd.Timestamp(start).date(), "end": pd.Timestamp(end).date()})
    df["nacimiento"] = pd.to_datetime(df["nacimiento"]).dt.normalize()
    return df


def load_modulos(engine=None):
    """Catalogo fisico ``<SIIR>.modulo``: modulo_id, numero visible y parcela."""
    df = pd.read_sql(text(f"""
        SELECT m.id_modulo AS modulo_id, m.numero AS modulo_numero,
               m.id_parcela AS parcela_id
        FROM {dbs.SCHEMA}.modulo m
    """), engine or dbs.get_engine())
    return df


def load_modulos_fijados(campana_ids, engine=None):
    """Modulos CONGELADOS de las campanas dadas, con su TMH fijada directa.

    ``tmh_fijada`` sale de ``disponible_rotopalas.tmh_apilado`` (TMH directa
    atribuible a la misma identidad campana_id + modulo_id + pad_id). Un
    ``tms_conformado`` sin TMH no equivale a conocer la TMH (seccion 7): queda
    ``tmh_fijada`` nula y el modulo se trata como ajustable con advertencia.
    El filtro por fecha de corte se aplica despues, en memoria."""
    ids = _ids(campana_ids)
    cols = ["campana_id", "pad_id", "parcela_id", "modulo_id", "modulo_numero",
            "fecha_conformacion", "fecha_congelamiento", "tms_conformado",
            "estado_congelamiento", "tmh_fijada"]
    if not ids:
        return pd.DataFrame(columns=cols)
    df = pd.read_sql(text(f"""
        SELECT mb.[campaña_id] AS campana_id, mb.pad_id, mb.parcela_id,
               mb.modulo_id, mb.modulo_numero, mb.fecha_conformacion,
               mb.fecha_congelamiento, mb.tms_conformado,
               mb.estado_congelamiento, dr.tmh_apilado AS tmh_fijada
        FROM {SCHEMA_RECLAMO}.v_modulo_base mb
        LEFT JOIN {dbs.SCHEMA}.disponible_rotopalas dr
          ON dr.[campaña_id] = mb.[campaña_id] AND dr.modulo_id = mb.modulo_id
         AND dr.pad_id = mb.pad_id
        WHERE mb.estado_congelamiento = 'CONGELADO'
          AND mb.[campaña_id] IN ({ids})
    """), engine or dbs.get_engine())
    for c in ("fecha_conformacion", "fecha_congelamiento"):
        df[c] = pd.to_datetime(df[c], errors="coerce").dt.normalize()
    return df[cols]
