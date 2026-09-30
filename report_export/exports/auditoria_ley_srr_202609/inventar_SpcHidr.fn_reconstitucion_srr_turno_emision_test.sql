CREATE   FUNCTION
[inventar_SpcHidr].[fn_reconstitucion_srr_turno_emision_test]
(
    @fecha_inicio date,
    @fecha_fin    date
)
RETURNS TABLE
AS
RETURN
(
    SELECT
        r.Fecha,
        t.Turno,

        /* =====================================================
           MASA SRR POR TURNO
           Fuente oficial de emisión
           ===================================================== */
        CASE
            WHEN t.Turno = 'A'
                THEN a.SRR_TMS_Turno_A

            WHEN t.Turno = 'B'
                THEN a.SRR_TMS_Turno_B

            ELSE NULL
        END AS SRR_TMS_Turno,

        a.SRR_TMS_Dia,

        /* =====================================================
           LEYES SRR RECONSTITUIDAS
           MISMA LEY DIARIA PARA A Y B
           ===================================================== */
        r.CuT_SRR_Reconst
            AS CuT_SRR,

        r.CuS_SRR_Reconst
            AS CuS_SRR,

        r.CO3_SRR_Reconst
            AS CO3_SRR,

        r.Malla100_SRR_Reconst
            AS Malla100_SRR,

        /* =====================================================
           SRR DIRECTO MB
           ===================================================== */
        r.ClayBeta_SRR_MB
            AS ClayBeta_SRR,

        r.Recuperacion_SRR_MB
            AS Recuperacion_SRR,

        /* =====================================================
           FUENTES
           ===================================================== */
        CAST(
            CASE
                WHEN r.CuT_SRR_Reconst IS NULL
                    THEN NULL
                ELSE 'RECONSTITUCION_DIARIA'
            END
            AS varchar(40)
        ) AS Fuente_CuT_SRR,

        CAST(
            CASE
                WHEN r.CuS_SRR_Reconst IS NULL
                    THEN NULL
                ELSE 'RECONSTITUCION_DIARIA'
            END
            AS varchar(40)
        ) AS Fuente_CuS_SRR,

        CAST(
            CASE
                WHEN r.CO3_SRR_Reconst IS NULL
                    THEN NULL
                ELSE 'RECONSTITUCION_DIARIA'
            END
            AS varchar(40)
        ) AS Fuente_CO3_SRR,

        CAST(
            CASE
                WHEN r.Malla100_SRR_Reconst IS NULL
                    THEN NULL
                ELSE 'RECONSTITUCION_DIARIA'
            END
            AS varchar(40)
        ) AS Fuente_Malla100_SRR,

        CAST(
            CASE
                WHEN r.ClayBeta_SRR_MB IS NULL
                    THEN NULL
                ELSE 'MB_SRR_DIRECTO'
            END
            AS varchar(40)
        ) AS Fuente_ClayBeta_SRR,

        CAST(
            CASE
                WHEN r.Recuperacion_SRR_MB IS NULL
                    THEN NULL
                ELSE 'MB_SRR_DIRECTO'
            END
            AS varchar(40)
        ) AS Fuente_Recuperacion_SRR,

        /* =====================================================
           AUDITORÍA DIARIA
           ===================================================== */
        r.Participacion_SRR,
        r.Factor_Sensibilidad_Reconstitucion,

        r.Delta_CuT_Reconst_MB,
        r.Delta_CuS_Reconst_MB,
        r.Delta_CO3_Reconst_MB,
        r.Delta_M100_Reconst_MB,

        r.Flag_Reconstitucion,
        r.Flag_Sensibilidad

    FROM
        [inventar_SpcHidr].[fn_reconstitucion_srr_emision_test]
        (
            @fecha_inicio,
            @fecha_fin
        ) r

    LEFT JOIN
        [inventar_SpcHidr].[v_ajuste_camiones_emision_test] a
        ON a.Fecha = r.Fecha

    CROSS JOIN
    (
        VALUES
            ('A'),
            ('B')
    ) t(Turno)
);
