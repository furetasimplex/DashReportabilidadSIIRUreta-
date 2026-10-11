CREATE   VIEW
    inventar_SpcHidr.v_contingencia_pi_estado_turno_test
AS

/* ================================================================
   ESTADO DE CONTINGENCIA PI POR TURNO - DEV

   Alcance operacional:
       >= 01-09-2026

   Antes de esa fecha:
       esta capa NO participa.
       Se mantiene íntegramente la metodología histórica existente.
================================================================ */

WITH Turnos AS
(
    SELECT DISTINCT
        r.fecha_operacional,
        r.turno

    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno
        AS r

    WHERE r.fecha_operacional >= '2026-09-01'


    UNION


    SELECT DISTINCT
        a.fecha_operacional,
        a.turno

    FROM inventar_SpcHidr.contingencia_pi_accion_test
        AS a

    WHERE a.fecha_operacional >= '2026-09-01'
)

SELECT
    t.fecha_operacional,
    t.turno,

    CAST
    (
        CASE
            WHEN ult.accion = 'ACTIVAR_CONTINGENCIA'
                THEN 1
            ELSE 0
        END
        AS bit
    ) AS contingencia_pi_activa,

    CASE
        WHEN ult.accion = 'ACTIVAR_CONTINGENCIA'
            THEN 'CONTINGENCIA_PI'
        ELSE 'NORMAL_PI'
    END AS estado_fuente,

    ult.id AS accion_vigente_id,
    ult.accion AS accion_vigente,

    CASE
        WHEN ult.accion = 'ACTIVAR_CONTINGENCIA'
            THEN ult.motivo
        ELSE NULL
    END AS motivo_contingencia,

    ult.comentario AS comentario_ultima_accion,
    ult.usuario AS usuario_ultima_accion,
    ult.fecha_registro AS fecha_registro_ultima_accion,

    ult.fecha_operacional AS fecha_accion_vigente,
    ult.turno AS turno_accion_vigente

FROM Turnos AS t

OUTER APPLY
(
    SELECT TOP (1)
        a.id,
        a.fecha_operacional,
        a.turno,
        a.accion,
        a.motivo,
        a.comentario,
        a.usuario,
        a.fecha_registro

    FROM inventar_SpcHidr.contingencia_pi_accion_test AS a

    WHERE a.fecha_operacional >= '2026-09-01'

      AND
      (
            a.fecha_operacional < t.fecha_operacional

            OR

            (
                a.fecha_operacional = t.fecha_operacional

                AND
                CASE
                    WHEN a.turno = 'A' THEN 1
                    ELSE 2
                END
                <=
                CASE
                    WHEN t.turno = 'A' THEN 1
                    ELSE 2
                END
            )
      )

    ORDER BY
        a.fecha_operacional DESC,

        CASE
            WHEN a.turno = 'A' THEN 1
            ELSE 2
        END DESC,

        a.fecha_registro DESC,
        a.id DESC

) AS ult;
