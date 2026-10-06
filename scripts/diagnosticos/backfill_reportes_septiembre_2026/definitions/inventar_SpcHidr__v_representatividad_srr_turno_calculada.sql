CREATE   VIEW
    inventar_SpcHidr.v_representatividad_srr_turno_calculada
AS

WITH base AS
(
    SELECT
        Fecha =
            CAST(r.Fecha AS date),

        Turno =
            CAST(r.Turno AS varchar(1)),

        Torre =
            CAST('SRR' AS varchar(10)),

        r.Ton_Real,
        r.Horas_Reales,
        r.TPH_Real,
        r.Factor_Masa,
        r.ts_ini,
        r.ts_fin,

        e.Apilado_TMH_Base,
        e.Flag_Apilado_Valido,
        e.Turno_Evaluable,

        Fecha_Registro_Peso =
            pr.Fecha,

        pr.PesoReal_Quimico,
        pr.PesoReal_Fisico,

        pt.Fraccion_Muestreo,
        pt.PesoBase_Quimico_12h,
        pt.PesoBase_Fisico_12h,
        pt.PesoTeo_Quimico,
        pt.PesoTeo_Fisico

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r

    LEFT JOIN
        inventar_SpcHidr.v_estado_apilado_turno_representatividad AS e
        ON  e.Fecha = r.Fecha
        AND e.Turno = r.Turno

    LEFT JOIN
        inventar_SpcHidr.v_peso_real_torre_turno_excel AS pr
        ON  pr.Fecha = r.Fecha
        AND pr.Turno = r.Turno
        AND pr.Torre = r.Torre

    LEFT JOIN
        inventar_SpcHidr.v_peso_teorico_turno_torre_excel AS pt
        ON  pt.Fecha = r.Fecha
        AND pt.Turno = r.Turno
        AND pt.Torre = r.Torre

    WHERE r.Torre = 'SRR'
),

clasificacion AS
(
    SELECT
        *,

        Estado_SRR =
            CASE
                WHEN Turno_Evaluable IS NULL
                    THEN 'SIN_ESTADO_EVALUABILIDAD'

                WHEN Turno_Evaluable = 0
                    THEN 'NO_EVALUABLE'

                WHEN COALESCE(Ton_Real, 0) <= 0
                  OR COALESCE(Horas_Reales, 0) <= 0
                  OR COALESCE(PesoTeo_Quimico, 0) <= 0
                  OR COALESCE(PesoTeo_Fisico, 0) <= 0
                    THEN 'EVALUABLE_SIN_FLUJO_SRR'

                WHEN Fecha_Registro_Peso IS NULL
                    THEN 'EVALUABLE_SIN_REGISTRO_PESO_REAL'

                WHEN PesoReal_Quimico < 0
                  OR PesoReal_Fisico < 0
                    THEN 'EVALUABLE_PESO_REAL_INVALIDO'

                WHEN COALESCE(PesoReal_Quimico, 0) <= 0
                 AND COALESCE(PesoReal_Fisico, 0) <= 0
                    THEN 'EVALUABLE_SIN_MUESTRA'

                WHEN COALESCE(PesoReal_Quimico, 0) <= 0
                  OR COALESCE(PesoReal_Fisico, 0) <= 0
                    THEN 'EVALUABLE_MUESTRA_PARCIAL'

                ELSE 'EVALUABLE_CON_MUESTRA'
            END

    FROM base
),

ratios AS
(
    SELECT
        *,

        Representatividad_Quimica =
            CAST
            (
                CASE
                    WHEN Turno_Evaluable IS NULL
                        THEN NULL

                    WHEN Turno_Evaluable = 0
                        THEN NULL

                    WHEN COALESCE(Ton_Real, 0) <= 0
                      OR COALESCE(Horas_Reales, 0) <= 0
                      OR COALESCE(PesoTeo_Quimico, 0) <= 0
                        THEN NULL

                    WHEN Fecha_Registro_Peso IS NULL
                        THEN NULL

                    WHEN PesoReal_Quimico < 0
                        THEN NULL

                    WHEN
                        COALESCE(PesoReal_Quimico, 0)
                        / NULLIF(PesoTeo_Quimico, 0) >= 1
                        THEN 1.0

                    ELSE
                        COALESCE(PesoReal_Quimico, 0)
                        / NULLIF(PesoTeo_Quimico, 0)
                END
                AS decimal(18,10)
            ),

        Representatividad_Fisica =
            CAST
            (
                CASE
                    WHEN Turno_Evaluable IS NULL
                        THEN NULL

                    WHEN Turno_Evaluable = 0
                        THEN NULL

                    WHEN COALESCE(Ton_Real, 0) <= 0
                      OR COALESCE(Horas_Reales, 0) <= 0
                      OR COALESCE(PesoTeo_Fisico, 0) <= 0
                        THEN NULL

                    WHEN Fecha_Registro_Peso IS NULL
                        THEN NULL

                    WHEN PesoReal_Fisico < 0
                        THEN NULL

                    WHEN
                        COALESCE(PesoReal_Fisico, 0)
                        / NULLIF(PesoTeo_Fisico, 0) >= 1
                        THEN 1.0

                    ELSE
                        COALESCE(PesoReal_Fisico, 0)
                        / NULLIF(PesoTeo_Fisico, 0)
                END
                AS decimal(18,10)
            )

    FROM clasificacion
)

SELECT
    Fecha,
    Turno,
    Torre,

    Ton_Real,
    Horas_Reales,
    TPH_Real,
    Factor_Masa,
    ts_ini,
    ts_fin,

    Apilado_TMH_Base,
    Flag_Apilado_Valido,
    Turno_Evaluable,

    PesoReal_Quimico,
    PesoReal_Fisico,

    Fraccion_Muestreo,
    PesoBase_Quimico_12h,
    PesoBase_Fisico_12h,
    PesoTeo_Quimico,
    PesoTeo_Fisico,

    Representatividad_Quimica,
    Representatividad_Fisica,

    Muestra_Quimica_Representativa =
        CAST
        (
            CASE
                WHEN Representatividad_Quimica IS NULL
                    THEN NULL

                WHEN Representatividad_Quimica >= 0.75
                    THEN 1

                ELSE 0
            END
            AS bit
        ),

    Muestra_Fisica_Representativa =
        CAST
        (
            CASE
                WHEN Representatividad_Fisica IS NULL
                    THEN NULL

                WHEN Representatividad_Fisica >= 0.75
                    THEN 1

                ELSE 0
            END
            AS bit
        ),

    Estado_SRR

FROM ratios;
