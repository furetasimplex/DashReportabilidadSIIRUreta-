CREATE   VIEW inventar_SpcHidr.v_reporte_srr_excel_exacto
AS
WITH srr AS
(
    SELECT
        Fecha,
        Turno,
        Torre,
        Ton_Real,
        Horas_Reales,
        TPH_Real,
        Factor_Masa,
        ts_toma_muestra,
        PesoReal_Quimico,
        PesoReal_Fisico,
        PesoTeo_Quimico,
        PesoTeo_Fisico
    FROM inventar_SpcHidr.v_base_turno_torre_excel
    WHERE Torre IN ('T3', 'TM3', 'SRR')  -- dejamos robusto por si hay variaciones
),
pvt AS
(
    SELECT
        Fecha,

        /* =========================
           Apilado SRR (Ton_Real)
           ========================= */
        SUM(CASE WHEN Turno = 'A' THEN ISNULL(Ton_Real, 0.0) ELSE 0.0 END) AS Apilado_SRR_TA,
        SUM(CASE WHEN Turno = 'B' THEN ISNULL(Ton_Real, 0.0) ELSE 0.0 END) AS Apilado_SRR_TB,
        SUM(ISNULL(Ton_Real, 0.0))                                         AS Apilado_SRR_Dia,

        /* =========================
           Horas Operación T3
           ========================= */
        SUM(CASE WHEN Turno = 'A' THEN ISNULL(Horas_Reales, 0.0) ELSE 0.0 END) AS Horas_Operacion_T3_TA,
        SUM(CASE WHEN Turno = 'B' THEN ISNULL(Horas_Reales, 0.0) ELSE 0.0 END) AS Horas_Operacion_T3_TB,

        /* =========================
           TPH Tambor 3 (ya viene calculado)
           Blindaje: si HE<=0 o Ton<=0 => 0
           ========================= */
        CASE
            WHEN SUM(CASE WHEN Turno='A' THEN ISNULL(Horas_Reales,0.0) ELSE 0.0 END) <= 0
              OR SUM(CASE WHEN Turno='A' THEN ISNULL(Ton_Real,0.0) ELSE 0.0 END) <= 0
            THEN 0.0
            ELSE MAX(CASE WHEN Turno='A' THEN ISNULL(TPH_Real,0.0) END)
        END AS TPH_Tambor_3_TA,

        CASE
            WHEN SUM(CASE WHEN Turno='B' THEN ISNULL(Horas_Reales,0.0) ELSE 0.0 END) <= 0
              OR SUM(CASE WHEN Turno='B' THEN ISNULL(Ton_Real,0.0) ELSE 0.0 END) <= 0
            THEN 0.0
            ELSE MAX(CASE WHEN Turno='B' THEN ISNULL(TPH_Real,0.0) END)
        END AS TPH_Tambor_3_TB,

        /* =========================
           Factor Masa Teórica (ya viene calculado)
           ========================= */
        MAX(CASE WHEN Turno='A' THEN ISNULL(Factor_Masa, 0.0) END) AS Factor_Masa_Teorica_T3_TA,
        MAX(CASE WHEN Turno='B' THEN ISNULL(Factor_Masa, 0.0) END) AS Factor_Masa_Teorica_T3_TB,

        /* =========================
           Horario toma de muestra
           ========================= */
        MAX(CASE WHEN Turno='A' THEN ts_toma_muestra END) AS Horario_Toma_Muestra_Turno_A,
        MAX(CASE WHEN Turno='B' THEN ts_toma_muestra END) AS Horario_Toma_Muestra_Turno_B,

        /* =========================
           Pesos reales
           ========================= */
        MAX(CASE WHEN Turno='A' THEN ISNULL(PesoReal_Quimico, 0.0) END) AS Peso_Muestra_Real_TM3_TA_Quimico,
        MAX(CASE WHEN Turno='A' THEN ISNULL(PesoReal_Fisico,  0.0) END) AS Peso_Muestra_Real_TM3_TA_Fisico,
        MAX(CASE WHEN Turno='B' THEN ISNULL(PesoReal_Quimico, 0.0) END) AS Peso_Muestra_Real_TM3_TB_Quimico,
        MAX(CASE WHEN Turno='B' THEN ISNULL(PesoReal_Fisico,  0.0) END) AS Peso_Muestra_Real_TM3_TB_Fisico,

        /* =========================
           Pesos teóricos
           ========================= */
        MAX(CASE WHEN Turno='A' THEN ISNULL(PesoTeo_Quimico, 0.0) END) AS Peso_Muestra_Teorica_TM3_TA_Quimico,
        MAX(CASE WHEN Turno='A' THEN ISNULL(PesoTeo_Fisico,  0.0) END) AS Peso_Muestra_Teorica_TM3_TA_Fisico,
        MAX(CASE WHEN Turno='B' THEN ISNULL(PesoTeo_Quimico, 0.0) END) AS Peso_Muestra_Teorica_TM3_TB_Quimico,
        MAX(CASE WHEN Turno='B' THEN ISNULL(PesoTeo_Fisico,  0.0) END) AS Peso_Muestra_Teorica_TM3_TB_Fisico

    FROM srr
    GROUP BY Fecha
)
SELECT
    /* Dia */
    Fecha AS Dia,

    /* Apilado SRR */
    ISNULL(Apilado_SRR_TA, 0.0)  AS Apilado_SRR_TA,
    ISNULL(Apilado_SRR_TB, 0.0)  AS Apilado_SRR_TB,
    ISNULL(Apilado_SRR_Dia, 0.0) AS Apilado_SRR_Dia,

    /* Horas Operación */
    ISNULL(Horas_Operacion_T3_TA, 0.0) AS Horas_Operacion_T3_TA,
    ISNULL(Horas_Operacion_T3_TB, 0.0) AS Horas_Operacion_T3_TB,

    /* TPH Tambor 3 */
    ISNULL(TPH_Tambor_3_TA, 0.0) AS TPH_Tambor_3_TA,
    ISNULL(TPH_Tambor_3_TB, 0.0) AS TPH_Tambor_3_TB,

    /* Factor Masa Teórica */
    ISNULL(Factor_Masa_Teorica_T3_TA, 0.0) AS Factor_Masa_Teorica_T3_TA,
    ISNULL(Factor_Masa_Teorica_T3_TB, 0.0) AS Factor_Masa_Teorica_T3_TB,

    /* Horarios toma de muestra */
    Horario_Toma_Muestra_Turno_A,
    Horario_Toma_Muestra_Turno_B,

    /* Pesos reales */
    ISNULL(Peso_Muestra_Real_TM3_TA_Quimico, 0.0) AS Peso_Muestra_Real_TM3_TA_Quimico,
    ISNULL(Peso_Muestra_Real_TM3_TA_Fisico,  0.0) AS Peso_Muestra_Real_TM3_TA_Fisico,
    ISNULL(Peso_Muestra_Real_TM3_TB_Quimico, 0.0) AS Peso_Muestra_Real_TM3_TB_Quimico,
    ISNULL(Peso_Muestra_Real_TM3_TB_Fisico,  0.0) AS Peso_Muestra_Real_TM3_TB_Fisico,

    /* Pesos teóricos */
    ISNULL(Peso_Muestra_Teorica_TM3_TA_Quimico, 0.0) AS Peso_Muestra_Teorica_TM3_TA_Quimico,
    ISNULL(Peso_Muestra_Teorica_TM3_TA_Fisico,  0.0) AS Peso_Muestra_Teorica_TM3_TA_Fisico,
    ISNULL(Peso_Muestra_Teorica_TM3_TB_Quimico, 0.0) AS Peso_Muestra_Teorica_TM3_TB_Quimico,
    ISNULL(Peso_Muestra_Teorica_TM3_TB_Fisico,  0.0) AS Peso_Muestra_Teorica_TM3_TB_Fisico,

    /* Representatividad (NUMÉRICA, 0–100) */
    Fecha AS Dia_Representatividad,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TA_Quimico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TA_Quimico,0)=0
        THEN NULL
        ELSE 100.0 * ISNULL(Peso_Muestra_Real_TM3_TA_Quimico,0) / NULLIF(ISNULL(Peso_Muestra_Teorica_TM3_TA_Quimico,0),0)
    END AS Representatividad_TM3_Turno_A_Quimico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TA_Fisico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TA_Fisico,0)=0
        THEN NULL
        ELSE 100.0 * ISNULL(Peso_Muestra_Real_TM3_TA_Fisico,0) / NULLIF(ISNULL(Peso_Muestra_Teorica_TM3_TA_Fisico,0),0)
    END AS Representatividad_TM3_Turno_A_Fisico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TB_Quimico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TB_Quimico,0)=0
        THEN NULL
        ELSE 100.0 * ISNULL(Peso_Muestra_Real_TM3_TB_Quimico,0) / NULLIF(ISNULL(Peso_Muestra_Teorica_TM3_TB_Quimico,0),0)
    END AS Representatividad_TM3_Turno_B_Quimico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TB_Fisico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TB_Fisico,0)=0
        THEN NULL
        ELSE 100.0 * ISNULL(Peso_Muestra_Real_TM3_TB_Fisico,0) / NULLIF(ISNULL(Peso_Muestra_Teorica_TM3_TB_Fisico,0),0)
    END AS Representatividad_TM3_Turno_B_Fisico,

    /* Límite fijo */
    CAST(75.0 AS float) AS Limite_Representatividad,

    /* Estado textual (exacto): “Tambor detenido” cuando Real=0 y Teo=0 */
    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TA_Quimico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TA_Quimico,0)=0
        THEN 'Tambor detenido'
        ELSE NULL
    END AS Estado_TM3_Turno_A_Quimico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TA_Fisico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TA_Fisico,0)=0
        THEN 'Tambor detenido'
        ELSE NULL
    END AS Estado_TM3_Turno_A_Fisico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TB_Quimico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TB_Quimico,0)=0
        THEN 'Tambor detenido'
        ELSE NULL
    END AS Estado_TM3_Turno_B_Quimico,

    CASE
        WHEN ISNULL(Peso_Muestra_Real_TM3_TB_Fisico,0)=0 AND ISNULL(Peso_Muestra_Teorica_TM3_TB_Fisico,0)=0
        THEN 'Tambor detenido'
        ELSE NULL
    END AS Estado_TM3_Turno_B_Fisico

FROM pvt;
