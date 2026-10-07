"""
Capa de acceso a datos del dashboard de reclamo.

Todo el SQL vive aqui. Ninguna otra parte de la aplicacion escribe consultas,
de modo que si cambia un nombre de vista solo hay que tocar este archivo.

Conexion: reutiliza db_connection.get_engine() (SQLSERVER_* + ENTORNO en .env).
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from db_connection import get_engine as _app_get_engine

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conexion
# ---------------------------------------------------------------------------

def get_engine() -> Engine:
    """Motor SQLAlchemy compartido con el resto de la app (db_connection)."""
    engine = _app_get_engine()
    if engine is None:
        raise RuntimeError(
            "No se pudo crear el engine SQL Server. "
            "Revise SQLSERVER_* y ENTORNO en .env (ver .env.example)."
        )
    return engine


def _read(sql: str, params: Optional[dict] = None) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


# ---------------------------------------------------------------------------
# Consultas de lectura
# ---------------------------------------------------------------------------

def diferencia_cv25(desde, hasta) -> pd.DataFrame:
    """Contraste diario entre el totalizador CV25 y la topografia.

    Regla R7: CV25 recibe la carga conjunta de ambas rotopalas y no recibe
    camiones, por lo que la comparacion es contra el reclamo de rotopala.
    """
    return _read(
        """
        SELECT fecha, tms_cv25, tmh_cv25, horas_r1, horas_r2, horas_total,
               tms_topografia, tms_preliminar, tms_publicado, tms_camiones,
               modulos_topografia, modulos_preliminar,
               diferencia_topografia_cv25, diferencia_pct, flag_diferencia
        FROM reclamo.v_diferencia_cv25
        WHERE fecha BETWEEN :desde AND :hasta
        ORDER BY fecha
        """,
        {"desde": desde, "hasta": hasta},
    )


def rendimiento(desde, hasta) -> pd.DataFrame:
    """Tasa horaria de tonelaje por rotopala, pesometro contra topografia."""
    return _read(
        """
        SELECT fecha, rotopala_id, rotopala, material,
               horas_operacion, tms_cv25_asignado, tms_topografia,
               rendimiento_pesometro_tms_hr, rendimiento_topografia_tms_hr,
               diferencia_tms, diferencia_pct, flag_cv25,
               CASE WHEN EXISTS (
                   SELECT 1 FROM reclamo.v_reclamo_diario rd
                   WHERE rd.fecha_operacion = r.fecha
                     AND rd.rotopala_id = r.rotopala_id
                     AND rd.fuente_reclamo = 'TOPOGRAFIA'
               ) THEN 1 ELSE 0 END AS tiene_topografia_real
        FROM reclamo.v_rendimiento_rotopala r
        WHERE fecha BETWEEN :desde AND :hasta
        ORDER BY fecha, rotopala_id
        """,
        {"desde": desde, "hasta": hasta},
    )


def cuadratura() -> pd.DataFrame:
    """Estado de extraccion por modulo. Regla R9.

    No lleva filtro de fecha a proposito: la cuadratura es acumulada desde el
    inicio de la campana, no del mes. Incluye los totales en TMS y el
    remanente (tms_saldo_disponible), que es lo que pide el resumen por
    modulo del dashboard.
    """
    return _read(
        """
        SELECT q.[campaña_id] AS campana_id, c.campana, q.pad_id, q.modulo_id, q.modulo_numero,
               rotopala_id, orden_secuencia, estado_secuencia,
               densidad_oficial, tms_conformado,
               m3_totales, m3_camiones_total, m3_rotopala_total, m3_ajustes,
               m3_extraido_total, porcentaje_extraido,
               tms_camiones_total, tms_rotopala_total, tms_extraido_total,
               tms_saldo_disponible,
               m3_excedente, tms_excedente,
               modulo_siguiente_propuesto, flag_cuadratura,
               movimiento.fecha_inicio_movimiento, movimiento.fecha_fin_movimiento
        FROM reclamo.v_cuadratura_modulo q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]) c
        OUTER APPLY (
            SELECT MIN(f.fecha) AS fecha_inicio_movimiento,
                   MAX(f.fecha) AS fecha_fin_movimiento
            FROM (
                SELECT t.fecha_medicion AS fecha
                FROM reclamo.v_topografia_resuelta t
                WHERE t.[campaña_id] = q.[campaña_id]
                  AND t.modulo_id = q.modulo_id
                  AND t.m3_incremento > 0
                UNION ALL
                SELECT cr.fecha
                FROM reclamo.v_camiones_acumulado cr
                WHERE cr.[campaña_id] = q.[campaña_id]
                  AND cr.modulo_id = q.modulo_id
                  AND cr.m3_camiones_dia > 0
                UNION ALL
                SELECT CAST(cr.fecha AS date)
                FROM inventar_SpcHidr.control_reclamo_diario cr
                WHERE cr.[campaña_id] = q.[campaña_id]
                  AND cr.modulo_id = q.modulo_id
                  AND CAST(cr.fecha AS date) < reclamo.fn_fecha_corte()
                  AND cr.volumen_diario_m3 > 0
                  AND q.m3_rotopala_previo > 0
                UNION ALL
                SELECT CAST(crc.fecha AS date)
                FROM inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario crc
                WHERE crc.[campaña_id] = q.[campaña_id]
                  AND crc.modulo_id = q.modulo_id
                  AND CAST(crc.fecha AS date) < reclamo.fn_fecha_corte()
                  AND crc.volumen_diario_m3 > 0
                  AND q.m3_camiones_previo > 0
            ) f
        ) movimiento
        ORDER BY porcentaje_extraido DESC
        """
    )


def estado_proyeccion(pad, hasta) -> pd.DataFrame:
    """Topografía real y proyección vigente de módulos abiertos del PAD."""
    return _read(
        """
        SELECT mb.modulo_id, topo.ultima_topografia,
               p.fecha_operacion AS fecha_preliminar, p.tms_preliminar_dia
        FROM reclamo.v_modulo_base mb
        OUTER APPLY (
            SELECT MAX(t.fecha_medicion) AS ultima_topografia
            FROM reclamo.topografia_avance t
            WHERE t.[campaña_id] = mb.[campaña_id]
              AND t.modulo_id = mb.modulo_id
              AND t.estado = 'VIGENTE'
              AND t.fecha_medicion <= :hasta
        ) topo
        OUTER APPLY (
            SELECT p.fecha_operacion, p.tms_preliminar_dia
            FROM reclamo.v_preliminar_cv25 p
            WHERE p.[campaña_id] = mb.[campaña_id]
              AND p.modulo_id = mb.modulo_id
              AND p.fecha_operacion <= :hasta
        ) p
        WHERE mb.estado_secuencia = 'ABIERTO' AND mb.pad_id = :pad
        """,
        {"pad": pad, "hasta": hasta},
    )


def ventanas_secuencia(pad) -> pd.DataFrame:
    """Ventanas operacionales de módulos congelados, para mensajes del panel."""
    return _read(
        """
        SELECT [campaña_id] AS campana_id, modulo_id, rotopala_id,
               estado_secuencia, fecha_apertura, fecha_cierre
        FROM reclamo.v_modulo_base
        WHERE pad_id = :pad
        """,
        {"pad": pad},
    )


def avance_diario(desde, hasta) -> pd.DataFrame:
    """Reclamo diario por modulo, con su fuente y sus flags.

    Trae por separado el tonelaje DEL DIA de camiones y de rotopala (no solo
    el acumulado), que es la base de la vista mensual tipo Excel: un dia por
    columna, un modulo por fila, camiones y rotopala en tablas separadas.
    """
    return _read(
        """
        SELECT q.fecha_operacion, q.[campaña_id] AS campana_id, c.campana, q.pad_id,
               modulo_id, modulo_numero, rotopala_id,
               tms_conformado, m3_totales, densidad_oficial,
               m3_camiones_dia, tms_camiones_dia,
               m3_camiones_acum, tms_camiones_acum,
               m3_disponible_roto, tms_disponible_roto,
               m3_rotopala_dia, tms_rotopala_dia,
               avance_total_pct, avance_roto_pct, avance_camiones_pct,
               ajuste_m3, ajuste_tms, ajustes_aplicados,
               fuente_reclamo, metodo_calculo, flag_calculo, flag_cuadratura
        FROM reclamo.calculo_diario q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]) c
        WHERE q.fecha_operacion BETWEEN :desde AND :hasta
        ORDER BY fecha_operacion, pad_id, modulo_numero
        """,
        {"desde": desde, "hasta": hasta},
    )


def vista_previa_conciliados(desde, hasta) -> pd.DataFrame:
    """Lo que publicaria sp_mantiene_datos_conciliados_emision_test, sin ejecutarlo.

    reclamo.v_reclamo_para_conciliados es el contrato de consumo exacto del
    PASO 9/10 del SP de mantencion (script 04). Consultarla directamente deja
    ver la cifra final ANTES de correr el SP y sin tocar
    inventar_SpcHidr.Datos_conciliados_of.
    """
    return _read(
        """
        SELECT q.fecha_operacion, q.pad_id, q.[campaña_id] AS campana_id, c.campana,
               modulo_id, modulo_numero, rotopala_id,
               avance_porcentaje, avance_total_porcentaje, avance_camiones_porcentaje,
               tonelaje_reclamado_diario, volumen_diario_m3, tonelaje_camiones_diario,
               tms_disponible_roto, tms_conformado, densidad_oficial,
               fuente_reclamo, metodo_calculo, flag_calculo, ajustes_aplicados
        FROM reclamo.v_reclamo_para_conciliados q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]) c
        WHERE q.fecha_operacion BETWEEN :desde AND :hasta
        ORDER BY fecha_operacion, pad_id, modulo_numero
        """,
        {"desde": desde, "hasta": hasta},
    )


def historial_modulo(campana_id: int, modulo_id: int) -> pd.DataFrame:
    """Historial diario completo de un modulo (todo el rango disponible, sin
    filtro de fecha). Es la base del panel de auditoria puntual de
    Cuadratura por modulo: dia a dia, fuente, metodo, flags y ajustes
    aplicados -- lo mismo que se uso para auditar el modulo 123 a mano."""
    return _read(
        """
        SELECT fecha_operacion, m3_camiones_dia, tms_camiones_dia,
               m3_rotopala_dia, tms_rotopala_dia,
               avance_total_pct, avance_roto_pct, avance_camiones_pct,
               ajuste_m3, ajuste_tms, ajustes_aplicados,
               fuente_reclamo, metodo_calculo, flag_calculo, flag_cuadratura
        FROM reclamo.calculo_diario
        WHERE [campaña_id] = :campana_id AND modulo_id = :modulo_id
        ORDER BY fecha_operacion
        """,
        {"campana_id": campana_id, "modulo_id": modulo_id},
    )


def ajustes(desde, hasta) -> pd.DataFrame:
    """Ajustes manuales del periodo, en cualquier estado."""
    return _read(
        """
        SELECT q.ajuste_id, q.fecha_operacion, q.[campaña_id] AS campana_id, c.campana,
               c.modulo_numero, q.pad_id,
               modulo_id, modulo_destino_id, tipo_ajuste,
               delta_m3, delta_tms, motivo,
               antecedente_tipo, antecedente_ref, estado,
               usuario_solicita, fecha_solicitud,
               usuario_aprueba, fecha_aprobacion, observacion
        FROM reclamo.ajuste_manual q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana, MAX(dr.modulo) AS modulo_numero
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]
                       AND dr.modulo_id = q.modulo_id) c
        WHERE q.fecha_operacion BETWEEN :desde AND :hasta
        ORDER BY fecha_operacion DESC, ajuste_id DESC
        """,
        {"desde": desde, "hasta": hasta},
    )


def modulos_disponibles() -> pd.DataFrame:
    """Modulos congelados, para poblar los desplegables del formulario."""
    return _read(
        """
        SELECT q.[campaña_id] AS campana_id, c.campana, q.pad_id, q.modulo_id, q.modulo_numero,
               tms_conformado, m3_totales, densidad_oficial,
               rotopala_id, orden_secuencia, estado_secuencia
        FROM reclamo.v_modulo_base q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]) c
        ORDER BY pad_id, modulo_numero
        """
    )


def disponible_rotopalas(campana_id=None, pad_id=None, modulo_numero=None,
                          fecha_desde=None, fecha_hasta=None) -> pd.DataFrame:
    """inventar_SpcHidr.disponible_rotopalas -- peso/volumen/densidad por
    modulo. Es la tabla que leen DIRECTO reclamo.sp_congelar_modulo y
    reclamo.sp_auto_congelar_modulos_nuevos: una fila con m3_totales o
    densidad en NULL bloquea el congelamiento automatico (queda como
    ALERTA_SIN_BASE en reclamo.log_automatizacion). Esta seccion del
    dashboard existe para poder completar/corregir esos valores sin
    depender de la carga manual via Excel.

    fecha_desde/fecha_hasta filtran por reclamo.modulo_congelado.
    fecha_conformacion -- la tabla fuente no tiene columna de fecha
    propia, asi que el filtro solo aplica a modulos ya congelados; uno
    que todavia no se congela sigue apareciendo (con fecha en blanco)
    salvo que se filtre explicitamente por fecha.
    """
    filtros = []
    params: dict = {}
    if campana_id is not None:
        filtros.append("dr.[campaña_id] = :campana_id")
        params["campana_id"] = campana_id
    if pad_id is not None:
        filtros.append("dr.pad_id = :pad_id")
        params["pad_id"] = pad_id
    if modulo_numero is not None:
        filtros.append("dr.modulo = :modulo_numero")
        params["modulo_numero"] = modulo_numero
    if fecha_desde is not None:
        filtros.append("mc.fecha_conformacion >= :fecha_desde")
        params["fecha_desde"] = fecha_desde
    if fecha_hasta is not None:
        filtros.append("mc.fecha_conformacion <= :fecha_hasta")
        params["fecha_hasta"] = fecha_hasta
    where = ("WHERE " + " AND ".join(filtros)) if filtros else ""
    return _read(
        f"""
        SELECT dr.id_disponible_rotopalas, dr.pad_id, dr.modulo AS modulo_numero,
               dr.modulo_id, dr.[campaña] AS campana, dr.[campaña_id] AS campana_id,
               dr.tms, dr.m3_totales, dr.densidad,
               dr.m3_apilado, dr.tmh_apilado, dr.remanente_m3, dr.remanente_tms,
               mc.fecha_conformacion, mc.estado AS estado_congelado
        FROM inventar_SpcHidr.disponible_rotopalas dr
        LEFT JOIN reclamo.modulo_congelado mc
            ON mc.[campaña_id] = dr.[campaña_id] AND mc.modulo_id = dr.modulo_id
        {where}
        ORDER BY dr.pad_id, dr.[campaña_id] DESC, dr.modulo
        """,
        params,
    )


def catalogo_modulos(pad_id=None) -> pd.DataFrame:
    """Catalogo completo de modulos (inventar_SpcHidr.modulo + parcela + pad),
    para el desplegable de "insertar nuevo registro" -- incluye modulos que
    todavia no tienen fila en disponible_rotopalas."""
    filtro = "WHERE p.id_pad = :pad_id" if pad_id else ""
    params = {"pad_id": pad_id} if pad_id else {}
    return _read(
        f"""
        SELECT m.id_modulo AS modulo_id, m.numero AS modulo_numero,
               p.id_parcela AS parcela_id, p.numero AS parcela_numero,
               p.id_pad AS pad_id
        FROM inventar_SpcHidr.modulo m
        INNER JOIN inventar_SpcHidr.parcela p ON p.id_parcela = m.id_parcela
        {filtro}
        ORDER BY p.id_pad, m.numero
        """,
        params,
    )


def campanas_disponible_rotopalas() -> pd.DataFrame:
    """Campañas ya presentes en disponible_rotopalas (id + numero visible),
    para poblar los desplegables de filtro e insercion."""
    return _read(
        """
        SELECT DISTINCT dr.[campaña_id] AS campana_id, dr.[campaña] AS campana
        FROM inventar_SpcHidr.disponible_rotopalas dr
        ORDER BY dr.[campaña_id] DESC
        """
    )


def semaforo(desde, hasta) -> pd.DataFrame:
    """Semaforo consolidado. Replica la seccion 9 del script de validacion."""
    return _read(
        """
        SELECT v.orden, v.control, v.severidad, v.hallazgos,
               CASE WHEN v.hallazgos = 0 THEN 'OK'
                    WHEN v.severidad = 'BLOQUEANTE' THEN 'NO PUBLICAR'
                    ELSE 'REVISAR' END AS resultado
        FROM
        (
            SELECT 1 AS orden, 'Modulos con densidad incoherente' AS control,
                   'BLOQUEANTE' AS severidad,
                   (SELECT COUNT(*) FROM reclamo.v_modulo_base
                    WHERE flag_densidad <> 'OK') AS hallazgos
            UNION ALL
            SELECT 2, 'Modulos congelados sin secuencia', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.modulo_congelado mc
                    WHERE mc.estado = 'CONGELADO'
                      AND NOT EXISTS (SELECT 1 FROM reclamo.secuencia_rotopala s
                                      WHERE s.[campaña_id] = mc.[campaña_id]
                                        AND s.modulo_id = mc.modulo_id)
                      -- Mismo criterio A/B de los SP de secuencia (@Siguientes = 5).
                      AND (EXISTS (
                          SELECT 1 FROM inventar_SpcHidr.control_reclamo_diario cr
                          WHERE cr.pad_id = mc.pad_id
                            AND cr.[campaña_id] = mc.[campaña_id]
                            AND cr.modulo_id = mc.modulo_id
                            AND COALESCE(cr.volumen_diario_m3, 0) > 0
                      ) OR (
                          mc.modulo_numero > (
                              SELECT MAX(md.numero)
                              FROM inventar_SpcHidr.control_reclamo_diario cr
                              JOIN inventar_SpcHidr.modulo md ON md.id_modulo = cr.modulo_id
                              WHERE cr.pad_id = mc.pad_id
                                AND cr.[campaña_id] = mc.[campaña_id]
                                AND COALESCE(cr.volumen_diario_m3, 0) > 0
                          )
                          AND mc.modulo_numero <= (
                              SELECT MAX(md.numero) + 5
                              FROM inventar_SpcHidr.control_reclamo_diario cr
                              JOIN inventar_SpcHidr.modulo md ON md.id_modulo = cr.modulo_id
                              WHERE cr.pad_id = mc.pad_id
                                AND cr.[campaña_id] = mc.[campaña_id]
                                AND COALESCE(cr.volumen_diario_m3, 0) > 0
                          )
                      )))
            UNION ALL
            SELECT 3, 'Mas de dos modulos abiertos por rotopala', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM
                    (SELECT s.rotopala_id FROM reclamo.secuencia_rotopala s
                     WHERE s.estado = 'ABIERTO'
                     GROUP BY s.rotopala_id, s.[campaña_id]
                     HAVING COUNT(*) > 2) x)
            UNION ALL
            SELECT 4, 'Cuadratura sobre 100 sin traspaso', 'ADVERTENCIA',
                   (SELECT COUNT(*) FROM reclamo.v_cuadratura_modulo cm
                    WHERE cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'
                      AND NOT EXISTS (SELECT 1 FROM reclamo.ajuste_manual a
                                      WHERE a.[campaña_id] = cm.[campaña_id]
                                        AND a.modulo_id = cm.modulo_id
                                        AND a.tipo_ajuste = 'TRASPASO_MODULO'
                                        AND a.estado = 'APROBADO'))
            UNION ALL
            SELECT 5, 'Ajustes aprobados sin antecedente', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.ajuste_manual a
                    WHERE a.estado = 'APROBADO'
                      AND (a.antecedente_ref IS NULL
                           OR LEN(LTRIM(RTRIM(a.antecedente_ref))) < 10))
            UNION ALL
            SELECT 6, 'Horas de rotopala imposibles', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.rotopala_horas_turno
                    WHERE horas_operacion > 12.5)
            UNION ALL
            SELECT 7, 'Filas con reclamo preliminar CV25', 'ADVERTENCIA',
                   (SELECT COUNT(*) FROM reclamo.calculo_diario
                    WHERE fuente_reclamo = 'PRELIMINAR_CV25'
                      AND fecha_operacion BETWEEN :desde AND :hasta)
            UNION ALL
            SELECT 8, 'Brecha CV25 vs topografia sobre 10 pct', 'ADVERTENCIA',
                   (SELECT COUNT(*) FROM reclamo.v_diferencia_cv25
                    WHERE flag_diferencia = 'BRECHA_SOBRE_10_PCT'
                      AND fecha BETWEEN :desde AND :hasta)
            UNION ALL
            SELECT 9, 'Ajustes propuestos sin resolver', 'ADVERTENCIA',
                   (SELECT COUNT(*) FROM reclamo.ajuste_manual
                    WHERE estado = 'PROPUESTO')
            UNION ALL
            SELECT 10, 'Datos de sincronización omitidos y aún sin congelar', 'BLOQUEANTE',
                   (SELECT COUNT(DISTINCT CAST(l.[campaña_id] AS varchar) + '-' + CAST(l.modulo_id AS varchar))
                    FROM reclamo.log_sincronizacion l
                    WHERE l.accion = 'OMITIDO'
                      AND l.fecha_dato BETWEEN :desde AND :hasta
                      AND NOT EXISTS (SELECT 1 FROM reclamo.modulo_congelado mc
                                      WHERE mc.[campaña_id] = l.[campaña_id] AND mc.modulo_id = l.modulo_id
                                        AND mc.estado = 'CONGELADO'))
            UNION ALL
            SELECT 11, 'Valores cambiados tras sincronizar', 'ADVERTENCIA',
                   (SELECT COUNT(*) FROM reclamo.log_sincronizacion l
                    WHERE l.accion = 'ACTUALIZADO'
                      AND l.fecha_dato BETWEEN :desde AND :hasta)
            UNION ALL
            SELECT 12, 'Alertas de automatizacion sin resolver (30 dias)', 'BLOQUEANTE',
                   (SELECT COUNT(*) FROM reclamo.log_automatizacion
                    WHERE accion LIKE 'ALERTA%'
                      AND fecha_evento >= DATEADD(DAY, -30, SYSDATETIME()))
            UNION ALL
            SELECT 13, 'Modulos con movimiento real y aun sin congelar', 'BLOQUEANTE',
                   (SELECT COUNT(DISTINCT CAST(cr.[campaña_id] AS varchar) + '-' + CAST(cr.modulo_id AS varchar))
                    FROM inventar_SpcHidr.control_reclamo_diario cr
                    WHERE CAST(cr.fecha AS date) >= reclamo.fn_fecha_corte()
                      AND COALESCE(cr.volumen_diario_m3,0) > 0
                      AND NOT EXISTS (SELECT 1 FROM reclamo.modulo_congelado mc
                                      WHERE mc.[campaña_id] = cr.[campaña_id]
                                        AND mc.modulo_id = cr.modulo_id))
            UNION ALL
            SELECT 14, 'Modulos congelados sin linea base (con historial previo real)', 'BLOQUEANTE',
                   (SELECT COUNT(*)
                    FROM reclamo.modulo_congelado mc
                    WHERE mc.estado = 'CONGELADO'
                      AND mc.fecha_linea_base IS NULL
                      AND EXISTS (SELECT 1 FROM inventar_SpcHidr.control_reclamo_diario cr
                                  WHERE cr.[campaña_id] = mc.[campaña_id]
                                    AND cr.modulo_id     = mc.modulo_id
                                    AND CAST(cr.fecha AS date) < reclamo.fn_fecha_corte()
                                    AND COALESCE(cr.volumen_diario_m3,0) > 0))
        ) v
        ORDER BY CASE WHEN v.hallazgos > 0 AND v.severidad = 'BLOQUEANTE'
                      THEN 0 ELSE 1 END, v.orden
        """,
        {"desde": desde, "hasta": hasta},
    )


# ---------------------------------------------------------------------------
# Escritura: unicamente a traves de procedimientos
# ---------------------------------------------------------------------------

def registrar_ajuste(
    fecha_operacion,
    campana_id: int,
    pad_id: int,
    modulo_id: int,
    tipo_ajuste: str,
    motivo: str,
    antecedente_tipo: str,
    antecedente_ref: str,
    delta_m3=None,
    delta_tms=None,
    modulo_destino_id=None,
    observacion=None,
) -> str:
    """Registra un ajuste manual llamando a reclamo.sp_registrar_ajuste_manual.

    El dashboard NO inserta directamente en la tabla: todo pasa por el
    procedimiento, que es el que valida motivo y antecedente y deja el ajuste
    en estado PROPUESTO.
    """
    sql = text(
        """
        EXEC reclamo.sp_registrar_ajuste_manual
             @FechaOperacion  = :fecha,
             @CampañaId       = :campana,
             @PadId           = :pad,
             @ModuloId        = :modulo,
             @TipoAjuste      = :tipo,
             @Motivo          = :motivo,
             @AntecedenteTipo = :ant_tipo,
             @AntecedenteRef  = :ant_ref,
             @DeltaM3         = :dm3,
             @DeltaTms        = :dtms,
             @ModuloDestinoId = :destino,
             @Observacion     = :obs
        """
    )
    params = {
        "fecha": fecha_operacion,
        "campana": campana_id,
        "pad": pad_id,
        "modulo": modulo_id,
        "tipo": tipo_ajuste,
        "motivo": motivo,
        "ant_tipo": antecedente_tipo,
        "ant_ref": antecedente_ref,
        "dm3": delta_m3,
        "dtms": delta_tms,
        "destino": modulo_destino_id,
        "obs": observacion,
    }
    with get_engine().begin() as conn:
        conn.execute(sql, params)
    return "Ajuste registrado como propuesta. No afecta ninguna cifra hasta aprobarse."


def actualizar_disponible_rotopala(
    id_disponible_rotopalas: int,
    tms=None, m3_totales=None, densidad=None,
    m3_apilado=None, tmh_apilado=None, remanente_m3=None, remanente_tms=None,
    observacion=None,
) -> str:
    """Llama a reclamo.sp_actualizar_disponible_rotopala (v2). Solo los
    campos que vengan con valor se actualizan; el resto conserva lo que ya
    tenia. Si no se informa densidad, el SP la recalcula sola desde TMS/
    m3_totales. Si el modulo ya estaba CONGELADO, el SP tambien actualiza
    reclamo.modulo_congelado y deja registro en reclamo.log_sincronizacion
    -- el SELECT final trae propagado_a_modulo_congelado para avisarlo aca."""
    sql = text(
        """
        EXEC reclamo.sp_actualizar_disponible_rotopala
             @IdDisponibleRotopalas = :id,
             @Tms           = :tms,
             @M3Totales     = :m3_totales,
             @Densidad      = :densidad,
             @M3Apilado     = :m3_apilado,
             @TmhApilado    = :tmh_apilado,
             @RemanenteM3   = :remanente_m3,
             @RemanenteTms  = :remanente_tms,
             @Observacion   = :observacion
        """
    )
    params = {
        "id": id_disponible_rotopalas,
        "tms": tms, "m3_totales": m3_totales, "densidad": densidad,
        "m3_apilado": m3_apilado, "tmh_apilado": tmh_apilado,
        "remanente_m3": remanente_m3, "remanente_tms": remanente_tms,
        "observacion": observacion,
    }
    with get_engine().begin() as conn:
        result = conn.execute(sql, params)
        fila = result.fetchone()
    propagado = bool(fila._mapping.get("propagado_a_modulo_congelado")) if fila is not None else False
    msg = f"disponible_rotopalas actualizado (id {id_disponible_rotopalas})."
    if propagado:
        msg += (" El modulo ya estaba CONGELADO: se actualizaron tambien tms_conformado, "
                "m3_totales y densidad_oficial en modulo_congelado, con registro en "
                "reclamo.log_sincronizacion.")
    return msg


def insertar_disponible_rotopala(
    pad_id: int, modulo_id: int, campana_id: int, campana=None,
    tms=None, m3_totales=None, densidad=None,
    m3_apilado=None, tmh_apilado=None, remanente_m3=None, remanente_tms=None,
    observacion=None,
) -> str:
    """Llama a reclamo.sp_insertar_disponible_rotopala (v2). El procedimiento
    rechaza duplicados de (pad_id, modulo_id, campaña_id) -- si ya existe,
    hay que usar actualizar_disponible_rotopala en su lugar. Si no se
    informa densidad, se calcula sola desde TMS/m3_totales."""
    sql = text(
        """
        EXEC reclamo.sp_insertar_disponible_rotopala
             @PadId         = :pad_id,
             @ModuloId      = :modulo_id,
             @CampañaId     = :campana_id,
             @Campaña       = :campana,
             @Tms           = :tms,
             @M3Totales     = :m3_totales,
             @Densidad      = :densidad,
             @M3Apilado     = :m3_apilado,
             @TmhApilado    = :tmh_apilado,
             @RemanenteM3   = :remanente_m3,
             @RemanenteTms  = :remanente_tms,
             @Observacion   = :observacion
        """
    )
    params = {
        "pad_id": pad_id, "modulo_id": modulo_id, "campana_id": campana_id, "campana": campana,
        "tms": tms, "m3_totales": m3_totales, "densidad": densidad,
        "m3_apilado": m3_apilado, "tmh_apilado": tmh_apilado,
        "remanente_m3": remanente_m3, "remanente_tms": remanente_tms,
        "observacion": observacion,
    }
    with get_engine().begin() as conn:
        result = conn.execute(sql, params)
        fila = result.fetchone()
    propagado = bool(fila._mapping.get("propagado_a_modulo_congelado")) if fila is not None else False
    msg = f"disponible_rotopalas: nuevo registro insertado (PAD {pad_id}, modulo_id {modulo_id}, campaña_id {campana_id})."
    if propagado:
        msg += (" El modulo ya estaba CONGELADO: se actualizaron tambien tms_conformado, "
                "m3_totales y densidad_oficial en modulo_congelado, con registro en "
                "reclamo.log_sincronizacion.")
    return msg


def recalcular(desde, hasta, dias_reproceso: int = 7) -> str:
    """Prepara modulos, sincroniza evidencia y luego mantiene la secuencia.

    A: sp_auto_congelar_modulos_nuevos solo prepara modulos, secuencia y
       linea base; no abre ni cierra.
    B: sp_sincronizar_desde_etl incorpora topografia del rango.
    C: sp_auto_mantener_secuencia cierra y abre con evidencia sincronizada.
    D: segundo sync incorpora cualquier modulo habilitado en C.
    E/F: CV25/horas y calculo diario.

    El mantenimiento completo nunca precede al primer sync del rango.
    """
    sql_preparar = text(
        """
        EXEC reclamo.sp_auto_congelar_modulos_nuevos
             @VentanaDias = 90,
             @Siguientes  = 5,
             @SoloPreparar = 1
        """
    )
    sql_mantener = text(
        """
        EXEC reclamo.sp_auto_mantener_secuencia
             @VentanaDias = 90,
             @Siguientes  = 5
        """
    )
    sql_sync = text(
        """
        EXEC reclamo.sp_sincronizar_desde_etl
             @FechaInicio        = :desde,
             @FechaFin            = :hasta,
             @SincronizarApilado  = 0,
             @Confirmar           = 1
        """
    )
    sql_cv25 = text(
        """
        EXEC reclamo.sp_cargar_cv25_horas
             @FechaInicio = :desde,
             @FechaFin    = :hasta
        """
    )
    sql_calc = text(
        """
        EXEC reclamo.sp_calcular_reclamo_diario
             @FechaInicio   = :desde,
             @FechaFin      = :hasta,
             @DiasReproceso = :dias
        """
    )
    sql_resumen_sync = text(
        """
        SELECT TOP (1) filas_afectadas
        FROM reclamo.log_ejecucion
        WHERE procedimiento = 'reclamo.sp_sincronizar_desde_etl'
        ORDER BY ejecucion_id DESC
        """
    )
    with get_engine().begin() as conn:
        filas_sync = 0
        # Fase A: congelar, secuenciar y fijar linea base sin abrir/cerrar.
        conn.execute(sql_preparar)
        # Fase B: incorporar la evidencia del rango a topografia_avance.
        conn.execute(sql_sync, {"desde": desde, "hasta": hasta})
        filas_sync += conn.execute(sql_resumen_sync).scalar() or 0
        # Fase C: cerrar/abrir solo con la evidencia ya sincronizada.
        conn.execute(sql_mantener)
        # Fase D: incorporar cualquier modulo habilitado en la fase C.
        conn.execute(sql_sync, {"desde": desde, "hasta": hasta})
        filas_sync += conn.execute(sql_resumen_sync).scalar() or 0
        conn.execute(sql_cv25, {"desde": desde, "hasta": hasta})
        conn.execute(sql_calc, {"desde": desde, "hasta": hasta, "dias": dias_reproceso})
    resumen_sync = f" ({filas_sync} filas sincronizadas desde el ETL)" if filas_sync else ""
    return f"Reclamo recalculado para {desde} a {hasta}{resumen_sync}."


def publicar(desde, hasta, dias_reproceso: int = 7) -> str:
    """Dispara inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test.

    ESCRIBE EN PRODUCCION (inventar_SpcHidr.Datos_conciliados_of). Se llama
    solo desde el boton "Publicar" del dashboard, que exige confirmacion
    explicita del usuario antes de invocar esta funcion.

    Decision 2026-08-02: se unifica sobre sp_mantiene_datos_conciliados_
    emision_test (version 1.15), que ya incluye la capa de ajustes/factor
    de aplicacion de Chancado (via sp_mantiene_factor_ajuste_camiones_v2_test
    y v_ajuste_camiones_emision_test) y el calculo de Ley_CuT_Real_srr por
    balance residual de cobre fino, ausentes en el SP viejo
    (sp_mantiene_datos_conciliados_of v1.14). Mismo contrato de parametros
    (@FechaInicio, @FechaFin, @DiasReproceso), swap directo. El SP viejo se
    deja sin modificar y sin uso; no se llama mas desde este modulo.
    """
    sql = text(
        """
        EXEC inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
             @FechaInicio   = :desde,
             @FechaFin      = :hasta,
             @DiasReproceso = :dias
        """
    )
    with get_engine().begin() as conn:
        # Mismo contrato F4; local para no acoplar Reclamo a helpers privados
        # de report_export/PI-TUM. Centralizar cuando exista un módulo común.
        rc = conn.execute(text("""
            DECLARE @resultado int;
            EXEC @resultado = sys.sp_getapplock
                @Resource = 'SIIR_CONTINGENCIA_PI_APILADO',
                @LockMode = 'Exclusive',
                @LockOwner = 'Transaction',
                @LockTimeout = 10000;
            SELECT @resultado;
        """)).scalar()
        if rc is None or rc < 0:
            raise RuntimeError("No se pudo adquirir el bloqueo global para publicar Reclamo.")
        conn.execute(sql, {"desde": desde, "hasta": hasta, "dias": dias_reproceso})
    return f"Dato conciliado publicado para {desde} a {hasta}."


def mantener_secuencia(ventana_dias: int = 90, siguientes: int = 5) -> pd.DataFrame:
    """Dispara reclamo.sp_auto_mantener_secuencia.

    Es el reemplazo del EXEC manual: congela los modulos nuevos que aparecen
    en topografia o camiones, cierra los que llegan a 100 % y abre el que
    sigue. El usuario no necesita tocar SQL Server para ninguna de las tres
    cosas. Devuelve la bitacora de la corrida (reclamo.log_automatizacion),
    con las alertas primero.
    """
    log.warning("DEBUG_RECLAMO_MANTENER ventana_dias=%s siguientes=%s", ventana_dias, siguientes)
    sql = text(
        """
        EXEC reclamo.sp_auto_mantener_secuencia
             @VentanaDias = :ventana,
             @Siguientes  = :siguientes
        """
    )
    phase = "GET_ENGINE"
    try:
        engine = get_engine()
        with engine.begin() as conn:
            phase = "DB_IDENTITY"
            identity = conn.exec_driver_sql(
                "SELECT @@SERVERNAME AS server_name, DB_NAME() AS database_name, "
                "SUSER_SNAME() AS login_name"
            ).mappings().one()
            log.warning(
                "DEBUG_RECLAMO_DB server=%s database=%s login=%s",
                identity.get("server_name"), identity.get("database_name"),
                identity.get("login_name"),
            )

            phase = "BEFORE_EXEC"
            log.warning("DEBUG_RECLAMO_BEFORE_EXEC procedure=reclamo.sp_auto_mantener_secuencia")
            result = conn.execute(sql, {"ventana": ventana_dias, "siguientes": siguientes})
            phase = "AFTER_EXEC"
            returns_rows = result.returns_rows
            try:
                result_keys = list(result.keys())
            except Exception as exc:
                result_keys = None
                log.warning("DEBUG_RECLAMO_KEYS_ERROR %s: %s", type(exc).__name__, exc)
            log.warning("DEBUG_RECLAMO_AFTER_EXEC returns_rows=%s keys=%r", returns_rows, result_keys)

            phase = "AFTER_FETCH"
            rows = result.fetchall()
            cols = result.keys()
            log.warning("DEBUG_RECLAMO_AFTER_FETCH rows=%s keys=%r", len(rows), list(cols))
        log.warning("DEBUG_RECLAMO_AFTER_COMMIT procedure=reclamo.sp_auto_mantener_secuencia")
    except Exception:
        log.exception("DEBUG_RECLAMO_EXCEPTION phase=%s traceback follows", phase)
        raise
    df = pd.DataFrame(rows, columns=cols)
    return df.rename(columns={"campaña_id": "campana_id"})


def alertas_automatizacion(dias: int = 30) -> pd.DataFrame:
    """Alertas de automatizacion sin resolver, de los ultimos N dias.

    Son los casos que sp_auto_mantener_secuencia no pudo decidir solo: fin
    de PAD, cambio de campana, falta de base en disponible_rotopalas, o
    limite de dos modulos abiertos alcanzado. Quedan visibles aunque el
    usuario no haya apretado el boton en esta sesion.
    """
    return _read(
        """
        SELECT q.log_id, q.accion, q.pad_id, q.[campaña_id] AS campana_id, c.campana, q.modulo_id,
               modulo_numero, detalle, fecha_evento
        FROM reclamo.log_automatizacion q
        OUTER APPLY (SELECT MAX(dr.[campaña]) AS campana
                     FROM inventar_SpcHidr.disponible_rotopalas dr
                     WHERE dr.[campaña_id] = q.[campaña_id]) c
        WHERE q.accion LIKE 'ALERTA%'
          AND q.fecha_evento >= DATEADD(DAY, -:dias, SYSDATETIME())
        ORDER BY fecha_evento DESC
        """,
        {"dias": dias},
    )
