CREATE   VIEW
    inventar_SpcHidr.v_contingencia_estado_operacional_actual_test
AS

WITH Ranking AS
(
    SELECT
        e.id,
        e.fecha_operacional,
        e.turno,
        e.estado_operacional,
        e.comentario,
        e.usuario,
        e.fecha_registro,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                e.fecha_operacional,
                e.turno

            ORDER BY
                e.fecha_registro DESC,
                e.id DESC
        ) AS rn

    FROM
        inventar_SpcHidr.contingencia_estado_operacional_test
            AS e
)

SELECT
    id,
    fecha_operacional,
    turno,
    estado_operacional,
    comentario,
    usuario,
    fecha_registro

FROM Ranking

WHERE rn = 1;
