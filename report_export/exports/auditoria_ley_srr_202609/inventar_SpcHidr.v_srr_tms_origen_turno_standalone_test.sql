

CREATE   VIEW
[inventar_SpcHidr].[v_srr_tms_origen_turno_standalone_test]
AS

/* ============================================================
   1. FECHA + TURNO NACEN DESDE APILADO PRE-FACTOR

   Ya NO dependen de reporte_turno_cache_emision_test.
   ============================================================ */

WITH turnos_prefactor AS
(
    SELECT
        CAST(d.Fecha AS date) AS Fecha,

        CAST('A' AS varchar(1))
            COLLATE DATABASE_DEFAULT AS Turno,

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

        CAST('B' AS varchar(1))
            COLLATE DATABASE_DEFAULT AS Turno,

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


/* ============================================================
   2. IMP POR FECHA + TURNO

   Misma lógica vigente:
   - normalización TA/A -> A
   - TB/B -> B
   - Es_SRR = 1 para SRR
   - Ton > 0
   ============================================================ */

imp_origen_turno AS
(
    SELECT
        CAST(i.Fecha AS date) AS Fecha,

        CASE
            WHEN i.Turno IN ('TA', 'A')
                THEN 'A'

            WHEN i.Turno IN ('TB', 'B')
                THEN 'B'

            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT AS Turno,

        CAST(
            SUM(
                CASE
                    WHEN ISNULL(i.Es_SRR, 0) = 1
                        THEN ISNULL(i.Ton, 0)
                    ELSE 0
                END
            )
            AS decimal(38,10)
        ) AS Ton_SRR_IMP,

        CAST(
            SUM(ISNULL(i.Ton, 0))
            AS decimal(38,10)
        ) AS Ton_IMP_Total

    FROM
        DEV_SIIR.hidro.v_imp_chancado_normalizado AS i

    INNER JOIN turnos_prefactor AS tp
        ON tp.Fecha = CAST(i.Fecha AS date)

       AND tp.Turno =
           CASE
               WHEN i.Turno IN ('TA', 'A')
                   THEN 'A'

               WHEN i.Turno IN ('TB', 'B')
                   THEN 'B'

               ELSE i.Turno
           END COLLATE DATABASE_DEFAULT

    WHERE ISNULL(i.Ton, 0) > 0

    GROUP BY
        CAST(i.Fecha AS date),

        CASE
            WHEN i.Turno IN ('TA', 'A')
                THEN 'A'

            WHEN i.Turno IN ('TB', 'B')
                THEN 'B'

            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT
),


/* ============================================================
   3. RESOLUCIÓN DE ORIGEN

   MISMA prioridad de la vista vigente.
   ============================================================ */

origen_base AS
(
    SELECT
        tp.Fecha,
        tp.Turno,

        tp.Apilado_TMS_Referencia_Cap,

        CAST(
            ISNULL(p.Ton_Stock_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Stock_Oficial,

        CAST(
            ISNULL(p.Ton_Mina_Camiones, 0)
            AS decimal(38,10)
        ) AS Ton_Mina_Oficial,

        CAST(
            ISNULL(p.Ton_SRR, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_Oficial,

        CAST(
            ISNULL(i.Ton_SRR_IMP, 0)
            AS decimal(38,10)
        ) AS Ton_SRR_IMP,

        CAST(
            ISNULL(i.Ton_IMP_Total, 0)
            AS decimal(38,10)
        ) AS Ton_IMP_Total,

        c.Fuente_Dato,

        CASE
            /* -----------------------------------------------
               Prioridad 1: OFICIAL
               ----------------------------------------------- */
            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0
                THEN 'OFICIAL'

            /* -----------------------------------------------
               Prioridad 2: IMP
               ----------------------------------------------- */
            WHEN
                UPPER(
                    LTRIM(
                        RTRIM(
                            ISNULL(c.Fuente_Dato, '')
                        )
                    )
                ) = 'IMP'

                AND ISNULL(i.Ton_IMP_Total, 0) > 0
                THEN 'IMP'

            /* -----------------------------------------------
               Sin origen
               ----------------------------------------------- */
            ELSE 'SIN_ORIGEN'
        END AS Fuente_SRR

    FROM turnos_prefactor AS tp

    LEFT JOIN
        inventar_SpcHidr.v_apilado_base_mina_stock_srr AS p

        ON p.Fecha = tp.Fecha

       AND UPPER(LTRIM(RTRIM(p.Turno)))
           COLLATE DATABASE_DEFAULT
           = tp.Turno


    LEFT JOIN imp_origen_turno AS i

        ON i.Fecha = tp.Fecha
       AND i.Turno = tp.Turno


    LEFT JOIN
        inventar_SpcHidr.v_conciliacion_chancado_v2 AS c

        ON c.Fecha = tp.Fecha

       AND UPPER(LTRIM(RTRIM(c.Turno)))
           COLLATE DATABASE_DEFAULT
           = tp.Turno
),


/* ============================================================
   4. TONELAJE SRR FÍSICO DE ORIGEN
   ============================================================ */

origen_raw AS
(
    SELECT
        b.*,

        CAST(
            CASE
                WHEN b.Fuente_SRR = 'OFICIAL'
                    THEN b.Ton_SRR_Oficial

                WHEN b.Fuente_SRR = 'IMP'
                    THEN b.Ton_SRR_IMP

                ELSE 0
            END
            AS decimal(38,10)
        ) AS Ton_SRR_Origen_Raw

    FROM origen_base AS b
)


/* ============================================================
   5. RESULTADO FINAL
   ============================================================ */

SELECT
    Fecha,
    Turno,

    Fuente_SRR,

    Ton_SRR_Oficial,
    Ton_SRR_IMP,
    Ton_SRR_Origen_Raw,


    /* --------------------------------------------------------
       SRR utilizado después del CAP físico
       -------------------------------------------------------- */

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


    /* --------------------------------------------------------
       Flag cap
       -------------------------------------------------------- */

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


    /* --------------------------------------------------------
       Validez
       -------------------------------------------------------- */

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


    /* --------------------------------------------------------
       Estado
       -------------------------------------------------------- */

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


    /* --------------------------------------------------------
       Compatibilidad:
       en esta vista standalone Apilado_TMS_Real representa la
       masa física PRE-FACTOR usada para el cap.

       También se expone con nombre explícito.
       -------------------------------------------------------- */

    CAST(
        Apilado_TMS_Referencia_Cap
        AS decimal(38,10)
    ) AS Apilado_TMS_Real,

    CAST(
        Apilado_TMS_Referencia_Cap
        AS decimal(38,10)
    ) AS Apilado_TMS_Referencia_Cap,


    Ton_Stock_Oficial,
    Ton_Mina_Oficial,
    Ton_IMP_Total,

    Fuente_Dato AS Fuente_Dato_Conciliacion

FROM origen_raw;
