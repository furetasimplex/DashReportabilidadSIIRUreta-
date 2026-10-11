

CREATE   VIEW
[inventar_SpcHidr].[v_srr_tms_origen_turno_emision_cap_prefactor_test]
AS

WITH Prefactor AS
(
    /* ========================================================
       REFERENCIA FÍSICA PRE-FACTOR POR FECHA + TURNO
       ======================================================== */

    SELECT
        CAST(d.Fecha AS date) AS Fecha,

        CAST('A' AS varchar(1)) AS Turno,

        CAST(
            COALESCE(
                TRY_CONVERT(
                    float,
                    d.TMS_Total_Sin_Sal_Con_SRR_A
                ),
                0.0
            )
            AS decimal(38,10)
        ) AS Apilado_TMS_Referencia_Cap

    FROM
        inventar_SpcHidr
        .v_apilado_tms_sin_sal_con_srr_reporte_test AS d

    UNION ALL

    SELECT
        CAST(d.Fecha AS date) AS Fecha,

        CAST('B' AS varchar(1)) AS Turno,

        CAST(
            COALESCE(
                TRY_CONVERT(
                    float,
                    d.TMS_Total_Sin_Sal_Con_SRR_B
                ),
                0.0
            )
            AS decimal(38,10)
        ) AS Apilado_TMS_Referencia_Cap

    FROM
        inventar_SpcHidr
        .v_apilado_tms_sin_sal_con_srr_reporte_test AS d
),

Base AS
(
    /* ========================================================
       SE CONSERVA LA LÓGICA ACTUAL DE ORIGEN SRR.

       La vista vigente sigue resolviendo:
       - OFICIAL
       - IMP
       - SIN_ORIGEN

       Solo cambiamos la referencia utilizada por el CAP.
       ======================================================== */

    SELECT
        s.Fecha,
        s.Turno,

        s.Fuente_SRR,

        s.Ton_SRR_Oficial,
        s.Ton_SRR_IMP,
        s.Ton_SRR_Origen_Raw,

        /* Post-factor actual:
           se conserva solo para trazabilidad */
        s.Apilado_TMS_Real,

        /* Pre-factor:
           nueva referencia del CAP */
        CAST(
            COALESCE(
                p.Apilado_TMS_Referencia_Cap,
                0
            )
            AS decimal(38,10)
        ) AS Apilado_TMS_Referencia_Cap,

        s.Ton_Stock_Oficial,
        s.Ton_Mina_Oficial,
        s.Ton_IMP_Total,
        s.Fuente_Dato_Conciliacion

    FROM
        inventar_SpcHidr
        .v_srr_tms_origen_turno_emision_test AS s

    LEFT JOIN Prefactor AS p
        ON p.Fecha = s.Fecha
       AND UPPER(LTRIM(RTRIM(p.Turno)))
           = UPPER(LTRIM(RTRIM(s.Turno)))
)

SELECT
    Fecha,
    Turno,

    Fuente_SRR,

    Ton_SRR_Oficial,
    Ton_SRR_IMP,
    Ton_SRR_Origen_Raw,


    /* ========================================================
       SRR UTILIZADO
       ======================================================== */

    CAST(
        CASE
            WHEN Apilado_TMS_Referencia_Cap <= 0
                THEN 0

            WHEN Ton_SRR_Origen_Raw <= 0
                THEN 0

            WHEN Ton_SRR_Origen_Raw
                 > Apilado_TMS_Referencia_Cap
                THEN Apilado_TMS_Referencia_Cap

            ELSE Ton_SRR_Origen_Raw
        END
        AS decimal(38,10)
    ) AS Ton_SRR_Usado_Actual,


    /* ========================================================
       FLAG CAP
       ======================================================== */

    CAST(
        CASE
            WHEN Apilado_TMS_Referencia_Cap > 0
             AND Ton_SRR_Origen_Raw
                 > Apilado_TMS_Referencia_Cap
                THEN 1
            ELSE 0
        END
        AS bit
    ) AS Flag_SRR_Capeado_Por_Apilado,


    /* ========================================================
       FLAG VALIDEZ
       ======================================================== */

    CAST(
        CASE
            WHEN Fuente_SRR <> 'SIN_ORIGEN'
             AND Apilado_TMS_Referencia_Cap > 0
             AND Ton_SRR_Origen_Raw > 0
                THEN 1
            ELSE 0
        END
        AS bit
    ) AS Flag_SRR_Valido,


    /* ========================================================
       ESTADO
       ======================================================== */

    CAST(
        CASE
            WHEN Fuente_SRR = 'SIN_ORIGEN'
                THEN 'SIN_ORIGEN'

            WHEN Apilado_TMS_Referencia_Cap <= 0
                THEN 'SIN_APILADO'

            WHEN Ton_SRR_Origen_Raw <= 0
                THEN 'SIN_SRR_POSITIVO'

            WHEN Ton_SRR_Origen_Raw
                 > Apilado_TMS_Referencia_Cap
                THEN 'OK_CAP_APILADO'

            ELSE 'OK'
        END
        AS varchar(40)
    ) AS Estado_SRR,


    /* Valor histórico/post-factor.
       NO participa del nuevo cap. */
    Apilado_TMS_Real,


    /* Nueva trazabilidad explícita */
    Apilado_TMS_Referencia_Cap,


    Ton_Stock_Oficial,
    Ton_Mina_Oficial,
    Ton_IMP_Total,
    Fuente_Dato_Conciliacion

FROM Base;
