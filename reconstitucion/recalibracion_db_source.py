"""Lecturas SELECT-only para la recalibración M&R en staging.

Las consultas usan la conexión y el SCHEMA ya validados por
``reconstitucion.db_source``. El historial se corta explícitamente por fecha;
no se consulta la tabla maestra de campañas, cuyo contenido no acredita una
vigencia histórica. Se cargan todas las campañas de los PAD solicitados para
que el consumidor pueda conservar el reparto global de masa por volumen.
"""
from __future__ import annotations

from datetime import date, datetime
import re
from typing import Any, Iterable, Mapping

from sqlalchemy import text


def _db_source():
    # Import diferido: este archivo es staging y no debe abrir una conexión al
    # importar. La aplicación anfitriona configura db_source antes de usarlo.
    from reconstitucion import db_source
    return db_source


def _schema_parts(schema: str) -> tuple[str, ...]:
    if not isinstance(schema, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?", schema
    ):
        raise ValueError("SCHEMA de SIIR inválido o no validado")
    return tuple(schema.split("."))


def _objects(schema: str) -> tuple[str, str]:
    """Devuelve el esquema base y el esquema reclamo en nombres SQL seguros."""
    parts = _schema_parts(schema)
    base = ".".join(f"[{part}]" for part in parts)
    catalog = f"[{parts[0]}]." if len(parts) == 2 else ""
    reclamo = f"{catalog}[reclamo]"
    return base, reclamo


def scope_campaign_identity(scope: Any) -> tuple[int, int]:
    """Normaliza la identidad técnica (pad_id, campana_id) de un scope.

    Acepta un mapping con ``pad_id`` y ``campana_id``/``campaña_id``, o un
    par posicional. El número visible de campaña no forma parte de la clave.
    """
    pad, campaign, _ = _scope_anchor(scope)
    return pad, campaign


def _scope_anchor(scope: Any) -> tuple[int, int, int | None]:
    if isinstance(scope, Mapping):
        pad = scope.get("pad_id")
        campaign = scope.get("campana_id", scope.get("campaña_id"))
        visible = scope.get("campana", scope.get("campana_visible", scope.get("numero_campana")))
    else:
        try:
            values = tuple(scope)
        except TypeError:
            raise ValueError("scope debe contener pad_id y campana_id") from None
        if len(values) not in (2, 3):
            raise ValueError("scope debe ser (pad_id, campana_id[, campana_visible])")
        pad, campaign = values[:2]
        visible = values[2] if len(values) == 3 else None
    try:
        pad_id, campana_id = int(pad), int(campaign)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("pad_id y campana_id deben ser enteros") from None
    if pad_id <= 0 or campana_id <= 0:
        raise ValueError("pad_id y campana_id deben ser positivos")
    try:
        visible_id = None if visible is None else int(visible)
    except (TypeError, ValueError, OverflowError):
        raise ValueError("campana visible debe ser entera") from None
    return pad_id, campana_id, visible_id


def _cutoff_date(cutoff: Any) -> date:
    if isinstance(cutoff, datetime):
        return cutoff.date()
    if isinstance(cutoff, date):
        return cutoff
    try:
        return date.fromisoformat(str(cutoff)[:10])
    except (TypeError, ValueError):
        raise ValueError("cutoff debe ser una fecha válida") from None


def _read_rows(engine: Any, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        result = connection.execute(text(sql), params)
        return [dict(row) for row in result.mappings().all()]


def load_campaign_history(cutoff, scopes=None, engine=None):
    """Carga historial diario completo hasta ``cutoff`` para los PAD pedidos.

    ``scopes`` identifica campañas requeridas como ``(pad_id, campana_id,
    campana_visible)``. La fecha inicial se ancla a esas identidades exactas;
    desde ella se leen todos los PAD/campañas hasta el corte para conservar
    los pesos globales compartidos. La campaña visible distingue IDs técnicos
    reutilizados. Los consumidores escogen ``(pad_id, campana_id)`` al calibrar.

    Los campos de volumen son los snapshots diarios guardados en
    ``control_apilado_diario``. ``vol_total_est`` queda acotado por la última
    fila disponible al corte y no se reemplaza con el valor actual de otra
    fuente. Devuelve una lista de diccionarios normalizados.
    """
    dbs = _db_source()
    cutoff_day = _cutoff_date(cutoff)
    schema, _ = _objects(dbs.SCHEMA)
    params: dict[str, Any] = {"cutoff": cutoff_day}
    history_bound = ""
    if scopes is not None:
        anchors = sorted(
            {_scope_anchor(scope) for scope in scopes},
            key=lambda row: (row[0], row[1], -1 if row[2] is None else row[2]),
        )
        if not anchors:
            return []
        predicates = []
        for index, (pad_id, campana_id, visible) in enumerate(anchors):
            pad_name, campaign_name = f"anchor_pad_{index}", f"anchor_campaign_{index}"
            params[pad_name], params[campaign_name] = pad_id, campana_id
            clause = f"(anchor.pad_id = :{pad_name} AND anchor.[campaña_id] = :{campaign_name}"
            if visible is not None:
                visible_name = f"anchor_visible_{index}"
                params[visible_name] = visible
                clause += f" AND anchor.[campaña] = :{visible_name}"
            predicates.append(clause + ")")
        history_bound = f"""
            WITH bounds AS (
                SELECT MIN(anchor.fecha) AS fecha_inicio
                FROM {schema}.control_apilado_diario AS anchor
                WHERE anchor.fecha < DATEADD(day, 1, CAST(:cutoff AS date))
                  AND ({' OR '.join(predicates)})
            )
        """

    sql = f"""
        {history_bound}
        SELECT
            CAST(cad.fecha AS date) AS fecha,
            cad.pad_id AS pad_id,
            md.id_parcela AS parcela_id,
            cad.[campaña_id] AS campana_id,
            cad.[campaña] AS campana,
            cad.modulo_id AS modulo_id,
            cad.modulo AS modulo,
            cad.volumen_total_estimado_m3 AS vol_total_est,
            cad.volumen_diario_m3 AS vol_diario,
            cad.volumen_acumulado_final_apilado_m3 AS vol_acum_final,
            cad.avance_porcentaje AS avance,
            cad.altura_promedio_m AS altura_prom,
            cad.promedio_grado AS grado_prom,
            cad.id AS control_id
        FROM {schema}.control_apilado_diario AS cad
        LEFT JOIN {schema}.modulo AS md
            ON md.id_modulo = cad.modulo_id
        {"CROSS JOIN bounds AS b" if scopes is not None else ""}
        WHERE cad.fecha < DATEADD(day, 1, CAST(:cutoff AS date))
          {"AND cad.fecha >= b.fecha_inicio" if scopes is not None else ""}
        ORDER BY cad.pad_id, cad.[campaña_id], cad.modulo_id,
                 cad.fecha, cad.id
    """
    return _read_rows(engine or dbs.get_engine(), sql, params)


def load_fixed_modules(cutoff, scopes=None, engine=None):
    """Lee módulos CONGELADO congelados y cerrados al corte.

    ``tmh_apilado`` procede únicamente de ``disponible_rotopalas`` y se une
    por PAD/campaña_id/modulo_id. Se incluye ``tms_conformado`` para el
    contraste secuencial del adaptador; nunca se convierte a TMH.
    """
    dbs = _db_source()
    cutoff_day = _cutoff_date(cutoff)
    schema, reclamo = _objects(dbs.SCHEMA)
    params: dict[str, Any] = {"cutoff": cutoff_day}
    scope_filter = ""
    source_scope_filter = ""
    if scopes is not None:
        anchors = sorted(
            {_scope_anchor(scope) for scope in scopes},
            key=lambda row: (row[0], row[1], -1 if row[2] is None else row[2]),
        )
        if not anchors:
            return []
        predicates = []
        source_predicates = []
        for index, (pad_id, campana_id, visible) in enumerate(anchors):
            pad_name, campaign_name = f"pad_{index}", f"campaign_{index}"
            params[pad_name], params[campaign_name] = pad_id, campana_id
            identity_clause = f"(vb.pad_id = :{pad_name} AND vb.[campaña_id] = :{campaign_name}"
            predicates.append(identity_clause + ")")
            source_clause = identity_clause
            if visible is not None:
                visible_name = f"visible_{index}"
                params[visible_name] = visible
                source_clause += f" AND dr.[campaña] = :{visible_name}"
            source_predicates.append(source_clause + ")")
        scope_filter = f"AND ({' OR '.join(predicates)})"
        source_scope_filter = f"AND ({' OR '.join(source_predicates)})"
    sql = f"""
        SELECT
            vb.[campaña_id] AS campana_id,
            vb.pad_id AS pad_id,
            vb.parcela_id AS parcela_id,
            vb.modulo_id AS modulo_id,
            vb.modulo_numero AS modulo,
            vb.fecha_congelamiento AS fecha_congelamiento,
            vb.fecha_cierre AS fecha_cierre,
            vb.estado_congelamiento AS estado_congelamiento,
            vb.tms_conformado AS tms_conformado,
            dr.[campaña] AS campana,
            dr.tmh_apilado AS tmh_apilado
        FROM {reclamo}.v_modulo_base AS vb
        LEFT JOIN {schema}.disponible_rotopalas AS dr
            ON dr.[campaña_id] = vb.[campaña_id]
           AND dr.modulo_id = vb.modulo_id
           AND dr.pad_id = vb.pad_id
           {source_scope_filter}
        WHERE vb.estado_congelamiento = 'CONGELADO'
          AND (vb.fecha_congelamiento IS NULL OR
               vb.fecha_congelamiento < DATEADD(day, 1, CAST(:cutoff AS date)))
          AND (vb.fecha_cierre IS NULL OR
               vb.fecha_cierre < DATEADD(day, 1, CAST(:cutoff AS date)))
          {scope_filter}
        ORDER BY vb.pad_id, vb.[campaña_id], vb.modulo_id
    """
    return _read_rows(engine or dbs.get_engine(), sql, params)




def load_conciliado(start, cutoff, engine=None, *, fuente="ver", caso_id=None, caso_inicio=None):
    """Masa conciliada por turno desde ``start`` hasta ``cutoff``.

    ``fuente='ver'`` (por defecto, la oficial del dash) lee Datos_conciliados_of_ver con
    el criterio de ``db_source.load_masa``: dentro de la ventana del Caso
    (``caso_inicio`` en adelante) solo filas con ``caso_id`` = Caso y origen
    'AJUSTE_REPORTE'; antes de la ventana, la version activa y validada de cada fecha
    (la de validacion mas reciente). No mezcla versiones por fecha y no rellena con OF:
    un dia sin fila es ausencia de masa. ``run_id`` de ver es un UUID y no se filtra.

    ``fuente='of'`` lee Datos_conciliados_of: solo para scripts de auditoria y pruebas
    (comparacion con el libro de Excel); el runtime del dash nunca lo usa.

    TMS: ``Apilado_TMS_Real`` es la TMS del dia; ver no trae una TMS por turno
    independiente (la humedad por turno difiere de la implicita del dia por menos de
    0,03 puntos), de modo que el despacho la reparte por turno en proporcion a la TMH.
    """
    if fuente not in ("ver", "of"):
        raise ValueError(f"fuente de masa invalida para esta lectura: {fuente!r}")
    dbs = _db_source()
    schema, _ = _objects(dbs.SCHEMA)
    params = {"start": _cutoff_date(start), "cutoff": _cutoff_date(cutoff)}
    if fuente == "of":
        sql = f"""
        SELECT CAST(Fecha AS date) AS fecha,
               Campana_apilado AS etiqueta,
               Apilado_TMH_turno_A AS tmh_a,
               Apilado_TMH_turno_B AS tmh_b,
               Apilado_TMS_Real AS tms
        FROM {schema}.Datos_conciliados_of
        WHERE Fecha >= CAST(:start AS date)
          AND Fecha < DATEADD(day, 1, CAST(:cutoff AS date))
        ORDER BY Fecha
        """
        return _read_rows(engine or dbs.get_engine(), sql, params)
    if caso_id is None or caso_inicio is None:
        raise ValueError("la fuente ver requiere caso_id y caso_inicio")
    params.update(caso_id=int(caso_id), caso_inicio=_cutoff_date(caso_inicio))
    sql = f"""
        WITH v AS (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY Fecha
                       ORDER BY COALESCE(fecha_validacion, '19000101') DESC,
                                COALESCE(validation_id, 0) DESC) AS rn
            FROM {schema}.{dbs.MASA_VER_TABLE}
            WHERE COALESCE(estado_validacion, 'VALIDADO') = 'VALIDADO'
              AND Apilado_TMS_Real IS NOT NULL
              AND Apilado_TMH_promedio_dia IS NOT NULL
              AND Fecha >= CAST(:start AS date)
              AND Fecha < DATEADD(day, 1, CAST(:cutoff AS date))
              AND ((Fecha >= CAST(:caso_inicio AS date)
                    AND caso_id = :caso_id AND origen = 'AJUSTE_REPORTE')
                OR (Fecha < CAST(:caso_inicio AS date) AND es_activa = 1))
        )
        SELECT CAST(Fecha AS date) AS fecha,
               Campana_apilado AS etiqueta,
               Apilado_TMH_turno_A AS tmh_a,
               Apilado_TMH_turno_B AS tmh_b,
               Apilado_TMS_Real AS tms,
               caso_id AS caso_id
        FROM v
        WHERE rn = 1
        ORDER BY Fecha
    """
    return _read_rows(engine or dbs.get_engine(), sql, params)


def load_masa_fuente(start, cutoff, *, fuente="oficial", caso_id=None, caso_inicio=None, engine=None, inicio=None):
    """Masa por fecha para el reparto, segun el modo. Devuelve (masa, excepciones de fuente).

    'oficial' (por defecto): ver y, antes de la puesta en marcha, el libro del CSV donde ver falta; nunca
    lee OF. 'of': testeo explicito. Cada fila lleva ``fuente`` (VER, LIBRO_EXCEL, OF) para la trazabilidad.
    """
    from . import masa_fuentes
    import pandas as pd
    if fuente not in masa_fuentes.FUENTES_MASA:
        raise ValueError(f"fuente de masa invalida: {fuente!r}")
    vacio = pd.DataFrame(columns=["fecha", "tipo", "tmh", "tms", "detalle"])
    if fuente == "of":
        df = pd.DataFrame(load_conciliado(start, cutoff, engine, fuente="of"))
        df["fuente"] = "OF"
        return df, vacio
    ver = load_conciliado(start, cutoff, engine, fuente="ver", caso_id=caso_id, caso_inicio=caso_inicio)
    return masa_fuentes.combinar_ver_libro(ver, masa_fuentes.load_libros(), start, cutoff, inicio)
