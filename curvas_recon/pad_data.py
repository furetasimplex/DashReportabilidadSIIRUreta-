#!/usr/bin/env python3
"""
pad_data.py — Carga de curvas de recuperacion por parcela (PAD Oxido / PAD Sulfuro)
=====================================================================================
Fuente: DB online (SQL Server, ver db_pipeline.py), esquema de db_schema.sql,
tabla primaria Recuperaciones_pad. No se usa la consolidada
lectura_recuperacion: puede ir atrasada y en agosto de 2026 asignó las lecturas
de Óxidos a la parcela siguiente. Sin Excel, sin DB local.

load_oxido/load_sulfuro aceptan start_date/end_date opcionales para acotar la
lectura a un rango de fechas (ej. seleccion del datepicker del dashboard) —
sin argumentos, traen el historico completo (necesario para split_into_cycles).
"""
import os
from datetime import date

from sqlalchemy import text

from .db_pipeline import get_engine, SCHEMA
from .local_cache import sql_rows as _sql_rows   # cache local, ver local_cache.py

# Conservados para report_builder.py y compatibilidad con el flujo anterior.
XLSX_PATH = os.getenv('PAD_XLSX_PATH', 'Reporte_Recuperaciones 31 de Agosto 2025.xlsx')
OX_SHEET = os.getenv('PAD_OX_SHEET', 'Rec Ox 2')
SU_SHEET = os.getenv('PAD_SU_SHEET', 'Rec Sulfuro 2')


def classify_status(dates: list, global_last_date) -> str:
    """Clasifica el estado de una parcela segun su ultima fecha con dato."""
    if not dates:
        return 'sin_datos'
    if global_last_date is not None and max(dates) == global_last_date:
        return 'activa'
    return 'inactiva'


def _as_date(v):
    return v.date() if hasattr(v, 'date') else v


def _primary_source_fingerprint(engine, pad):
    """Firma fresca de Recuperaciones_pad para invalidar solo esta fuente.

    COUNT/MAX detectan inserciones y backfills; CHECKSUM_AGG incluye el valor
    medido para detectar updates que no cambian cantidad ni fecha maxima.
    Esta lectura es directa, intencionalmente fuera de la propia cache.
    """
    query = text(f"""
        SELECT COUNT_BIG(1), MAX(r.id_rec),
               MAX(CAST(r.Fecha_drenaje AS DATE)),
               CHECKSUM_AGG(BINARY_CHECKSUM(
                   r.id_rec, r.Parcela, CAST(r.Fecha_drenaje AS DATE),
                   r.Recuperacion_parcela))
        FROM {SCHEMA}.Recuperaciones_pad AS r
        WHERE r.PAD = :pad AND r.Recuperacion_parcela IS NOT NULL
    """)
    with engine.connect() as conn:
        row = conn.execute(query, {"pad": pad}).fetchone()
    if row is None:
        values = (0, None, None, None)
    else:
        values = tuple(row)
        if not values or values[0] is None:
            values = (0, None, None, None)
    count, max_id, max_date, checksum = values
    max_date = max_date.isoformat() if hasattr(max_date, 'isoformat') else max_date
    return ('rec-primary-v2', int(count or 0), max_id, max_date, checksum)


# Descartes ya avisados en este proceso: (material, detalle). Ver el print.
_AVISADOS = set()


def _load_material(material_nombre: str, max_parcela: int,
                    start_date=None, end_date=None) -> dict:
    """
    Lee Recuperaciones_pad para todas las parcelas de `material_nombre`
    desde la fuente primaria, opcionalmente acotado a [start_date, end_date].
    Retorna {numero_parcela: dict(dates=[...], values=[...], status=...)}.
    """
    where_range = ""
    pad = {'OXIDO': 'OXIDOS', 'SULFURO': 'SULFUROS'}[material_nombre]
    params = {"pad": pad}
    if start_date is not None:
        where_range += " AND r.Fecha_drenaje >= :start_date"
        params["start_date"] = start_date
    if end_date is not None:
        where_range += " AND r.Fecha_drenaje <= :end_date"
        params["end_date"] = end_date

    query = f"""
        SELECT TRY_CAST(r.Parcela AS INT) AS numero,
               CAST(r.Fecha_drenaje AS DATE) AS fecha,
               r.Recuperacion_parcela AS valor_pct
        FROM {SCHEMA}.Recuperaciones_pad r
        WHERE r.PAD = :pad AND r.Recuperacion_parcela IS NOT NULL {where_range}
        ORDER BY numero, fecha
    """
    last_date_query = f"""
        SELECT TRY_CAST(r.Parcela AS INT) AS numero,
               MAX(CAST(r.Fecha_drenaje AS DATE)) AS fecha
        FROM {SCHEMA}.Recuperaciones_pad r
        WHERE r.PAD = :pad AND r.Recuperacion_parcela IS NOT NULL
        GROUP BY TRY_CAST(r.Parcela AS INT)
    """
    engine = get_engine()
    source_salt = _primary_source_fingerprint(engine, pad)
    rows = _sql_rows(engine, text(query), params, cache_salt=source_salt)
    last_dates = _sql_rows(engine, text(last_date_query), {"pad": pad},
                            cache_salt=source_salt)

    global_last_date = max((_as_date(d) for _, d in last_dates if d is not None), default=None)

    # `valor_pct` es una recuperacion en %, asi que un valor de 46235 no es
    # dato: es un numero de serie de fecha de Excel (46235 = 2026-08-01) que
    # entro por la columna equivocada en la carga de `Recuperaciones_pad`.
    # Verificado en 2026-08 para OXIDOS/P01 (23 filas de agosto, 46235..46257).
    # Una sola lectura asi rompe `split_into_cycles` (caida > RESET_DROP al dia
    # siguiente = campana nueva falsa) y ensucia toda la curva de la pila, por
    # eso se descartan aca en vez de arrastrarlas. El tope es holgado a
    # proposito: hay parcelas con recuperacion historica sobre 100 % (P10, P14,
    # P17 llegan a 113 %) y esas SI son dato.
    #
    # El piso en 0 atrapa otra cosa: OXIDOS/P09 trae ocho lecturas de -0,006 a
    # -0,018 %, o sea recuperacion cero con signo negativo. No son un error de
    # columna sino ruido: los mismos dos pares de valores se repiten en cuatro
    # campanas distintas (2021-01, 2022-05, 2023-07, 2024-12), patron de dato
    # sintetico, no de medicion. Da igual el origen -- una recuperacion
    # negativa no existe y `split_into_cycles` la lee como caida.
    VALOR_MAX = 200.0
    raw = {}
    descartados = {}
    for numero, fecha, valor in rows:
        if numero is None or not (1 <= int(numero) <= max_parcela):
            continue
        v = float(valor)
        if not (0.0 <= v <= VALOR_MAX):
            descartados[numero] = descartados.get(numero, 0) + 1
            continue
        d = _as_date(fecha)
        raw.setdefault(numero, ([], []))
        raw[numero][0].append(d)
        raw[numero][1].append(v)
    # El aviso va UNA vez por proceso y por conjunto de descartes. La query si
    # esta cacheada (`_sql_rows`), pero el filtro y el print corren enteros en
    # cada llamada, y el dashboard llama `load_oxido` una vez por callback: el
    # mismo mensaje salia diez veces seguidas y tapaba el resto del log. La
    # clave incluye el detalle, asi que si aparece un descarte NUEVO se vuelve
    # a avisar.
    if descartados:
        clave = (material_nombre, tuple(sorted(descartados.items())))
        if clave not in _AVISADOS:
            _AVISADOS.add(clave)
            print('[pad_data] %s: %d lectura(s) de recuperacion fuera de rango '
                  '(0..%g %%) descartadas: %s'
                  % (material_nombre, sum(descartados.values()), VALOR_MAX,
                     ', '.join('P%02d=%d' % (n, c) for n, c in sorted(descartados.items()))))

    out = {}
    for p in range(1, max_parcela + 1):
        dates, values = raw.get(p, ([], []))
        out[p] = dict(dates=dates, values=values, status=classify_status(dates, global_last_date))
    return out


def load_oxido(start_date: date = None, end_date: date = None) -> dict:
    return _load_material('OXIDO', max_parcela=32, start_date=start_date, end_date=end_date)


def load_sulfuro(start_date: date = None, end_date: date = None) -> dict:
    return _load_material('SULFURO', max_parcela=28, start_date=start_date, end_date=end_date)
