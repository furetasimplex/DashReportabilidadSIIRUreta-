CREATE   VIEW inventar_SpcHidr.v_contingencia_apoyo_operacional_turno
AS

SELECT
    Fecha AS fecha_operacional,

    CAST
    (
        CASE
            WHEN Turno = 'TA' THEN 'A'
            WHEN Turno = 'TB' THEN 'B'
            ELSE Turno
        END
        AS char(1)
    ) AS turno,

    CAST(Ton AS decimal(28,6)) AS tonelaje_apoyo,

    CAST(Fuente_Dato AS varchar(20)) AS fuente_apoyo,

    CAST
    (
        CASE
            WHEN Fuente_Dato = 'SIN_DATO'
                THEN 'SIN_INFORMACION'

            WHEN Ton IS NULL
                THEN 'SIN_INFORMACION'

            WHEN Ton > 0
                THEN 'MOVIMIENTO_CONFIRMADO'

            WHEN Ton = 0
                THEN 'SIN_MOVIMIENTO_REPORTADO'

            ELSE 'SIN_INFORMACION'
        END
        AS varchar(30)
    ) AS estado_apoyo

FROM inventar_SpcHidr.v_conciliacion_chancado_v2;
