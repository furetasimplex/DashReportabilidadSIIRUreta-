
CREATE   VIEW [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test]
AS
WITH turnos_cache AS
(
    SELECT DISTINCT
        CAST(Fecha AS date) AS Fecha,
        UPPER(LTRIM(RTRIM(Turno))) COLLATE DATABASE_DEFAULT AS Turno
    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
),
imp_origen_turno AS
(
    SELECT
        CAST(i.Fecha AS date) AS Fecha,
        CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT AS Turno,
        CAST(SUM(CASE WHEN ISNULL(i.Es_SRR, 0) = 1
                      THEN ISNULL(i.Ton, 0) ELSE 0 END) AS decimal(38,10)) AS Ton_SRR_IMP,
        CAST(SUM(ISNULL(i.Ton, 0)) AS decimal(38,10)) AS Ton_IMP_Total
    FROM [DEV_SIIR].[hidro].[v_imp_chancado_normalizado] AS i
    INNER JOIN turnos_cache AS tc
      ON tc.Fecha = CAST(i.Fecha AS date)
     AND tc.Turno = CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT
    WHERE ISNULL(i.Ton, 0) > 0
    GROUP BY
        CAST(i.Fecha AS date),
        CASE
            WHEN i.Turno IN ('TA', 'A') THEN 'A'
            WHEN i.Turno IN ('TB', 'B') THEN 'B'
            ELSE i.Turno
        END COLLATE DATABASE_DEFAULT
),
origen_base AS
(
    SELECT
        CAST(r.Fecha AS date) AS Fecha,
        UPPER(LTRIM(RTRIM(r.Turno))) AS Turno,
        CAST(ISNULL(r.Apilado_TMS_Real, 0) AS decimal(38,10)) AS Apilado_TMS_Real,
        CAST(ISNULL(p.Ton_Stock_Camiones, 0) AS decimal(38,10)) AS Ton_Stock_Oficial,
        CAST(ISNULL(p.Ton_Mina_Camiones, 0) AS decimal(38,10)) AS Ton_Mina_Oficial,
        CAST(ISNULL(p.Ton_SRR, 0) AS decimal(38,10)) AS Ton_SRR_Oficial,
        CAST(ISNULL(i.Ton_SRR_IMP, 0) AS decimal(38,10)) AS Ton_SRR_IMP,
        CAST(ISNULL(i.Ton_IMP_Total, 0) AS decimal(38,10)) AS Ton_IMP_Total,
        c.Fuente_Dato,
        CASE
            WHEN ISNULL(p.Ton_Stock_Camiones, 0) > 0
              OR ISNULL(p.Ton_Mina_Camiones, 0) > 0
              OR ISNULL(p.Ton_SRR, 0) > 0 THEN 'OFICIAL'
            WHEN UPPER(LTRIM(RTRIM(ISNULL(c.Fuente_Dato, '')))) = 'IMP'
             AND ISNULL(i.Ton_IMP_Total, 0) > 0 THEN 'IMP'
            ELSE 'SIN_ORIGEN'
        END AS Fuente_SRR
    FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test] AS r
    LEFT JOIN [inventar_SpcHidr].[v_apilado_base_mina_stock_srr] AS p
      ON p.Fecha = CAST(r.Fecha AS date)
     AND p.Turno = UPPER(LTRIM(RTRIM(r.Turno)))
    LEFT JOIN imp_origen_turno AS i
      ON i.Fecha = CAST(r.Fecha AS date)
     AND i.Turno = UPPER(LTRIM(RTRIM(r.Turno))) COLLATE DATABASE_DEFAULT
    LEFT JOIN [inventar_SpcHidr].[v_conciliacion_chancado_v2] AS c
      ON c.Fecha = CAST(r.Fecha AS date)
     AND c.Turno = UPPER(LTRIM(RTRIM(r.Turno)))
),
origen_raw AS
(
    SELECT
        b.*,
        CAST(CASE
            WHEN b.Fuente_SRR = 'OFICIAL' THEN b.Ton_SRR_Oficial
            WHEN b.Fuente_SRR = 'IMP' THEN b.Ton_SRR_IMP
            ELSE 0
        END AS decimal(38,10)) AS Ton_SRR_Origen_Raw
    FROM origen_base AS b
)
SELECT
    Fecha,
    Turno,
    Fuente_SRR,
    Ton_SRR_Oficial,
    Ton_SRR_IMP,
    Ton_SRR_Origen_Raw,
    CAST(CASE
        WHEN Apilado_TMS_Real <= 0 THEN 0
        WHEN Ton_SRR_Origen_Raw <= 0 THEN 0
        WHEN Ton_SRR_Origen_Raw > Apilado_TMS_Real THEN Apilado_TMS_Real
        ELSE Ton_SRR_Origen_Raw
    END AS decimal(38,10)) AS Ton_SRR_Usado_Actual,
    CAST(CASE WHEN Apilado_TMS_Real > 0
                   AND Ton_SRR_Origen_Raw > Apilado_TMS_Real
              THEN 1 ELSE 0 END AS bit) AS Flag_SRR_Capeado_Por_Apilado,
    CAST(CASE WHEN Fuente_SRR <> 'SIN_ORIGEN'
                   AND Apilado_TMS_Real > 0
                   AND Ton_SRR_Origen_Raw > 0
              THEN 1 ELSE 0 END AS bit) AS Flag_SRR_Valido,
    CAST(CASE
        WHEN Fuente_SRR = 'SIN_ORIGEN' THEN 'SIN_ORIGEN'
        WHEN Apilado_TMS_Real <= 0 THEN 'SIN_APILADO'
        WHEN Ton_SRR_Origen_Raw <= 0 THEN 'SIN_SRR_POSITIVO'
        WHEN Ton_SRR_Origen_Raw > Apilado_TMS_Real THEN 'OK_CAP_APILADO'
        ELSE 'OK'
    END AS varchar(40)) AS Estado_SRR,
    Apilado_TMS_Real,
    Ton_Stock_Oficial,
    Ton_Mina_Oficial,
    Ton_IMP_Total,
    Fuente_Dato AS Fuente_Dato_Conciliacion
FROM origen_raw;
