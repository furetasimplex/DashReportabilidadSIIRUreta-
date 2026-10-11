
CREATE   PROCEDURE [inventar_SpcHidr].[sp_factor_ajuste_camiones_srr_origen_test]
    @FechaInicio date,
    @FechaFin date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 50001, 'FechaInicio y FechaFin son obligatorias.', 1;
    IF @FechaInicio > @FechaFin
        THROW 50002, 'FechaInicio no puede ser mayor que FechaFin.', 1;

    ;WITH srr_dia AS
    (
        SELECT
            Fecha,
            SUM(CASE WHEN Turno='A' THEN Ton_SRR_Usado_Actual ELSE 0 END) AS SRR_TMS_Turno_A_Origen,
            SUM(CASE WHEN Turno='B' THEN Ton_SRR_Usado_Actual ELSE 0 END) AS SRR_TMS_Turno_B_Origen,
            SUM(Ton_SRR_Usado_Actual) AS SRR_TMS_Dia_Origen,
            MAX(CASE WHEN Turno='A' THEN Fuente_SRR END) AS Fuente_SRR_Turno_A,
            MAX(CASE WHEN Turno='B' THEN Fuente_SRR END) AS Fuente_SRR_Turno_B,
            MAX(CASE WHEN Turno='A' THEN CONVERT(int,Flag_SRR_Capeado_Por_Apilado) ELSE 0 END) AS Flag_SRR_Capeado_A,
            MAX(CASE WHEN Turno='B' THEN CONVERT(int,Flag_SRR_Capeado_Por_Apilado) ELSE 0 END) AS Flag_SRR_Capeado_B
        FROM [inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test]
        WHERE Fecha BETWEEN @FechaInicio AND @FechaFin
        GROUP BY Fecha
    ),
    base AS
    (
        SELECT
            i.Fecha,
            TRY_CONVERT(float,a.TMH_Bruto_Dia) AS Apilado_TMH_Bruto,
            TRY_CONVERT(float,a.Apilado_TMH_promedio_dia) AS Apilado_TMH_Neto,
            TRY_CONVERT(float,a.Sal_promedio_dia) AS Sal_Dia,
            h.Humedad_Inventario,
            h.Flag_Humedad_Inventario_Valida,
            i.Total_Inventario_Chancado_TMS,
            i.Inventario_Chancado_TMS_Anterior,
            i.Delta_Inventario_Chancado_TMS,
            i.Flag_Continuidad_Diaria,
            i.Flag_Inventario_Valido,
            COALESCE(s.SRR_TMS_Turno_A_Origen,0) AS SRR_TMS_Turno_A_Origen,
            COALESCE(s.SRR_TMS_Turno_B_Origen,0) AS SRR_TMS_Turno_B_Origen,
            COALESCE(s.SRR_TMS_Dia_Origen,0) AS SRR_TMS_Dia_Origen,
            COALESCE(s.Fuente_SRR_Turno_A,'SIN_ORIGEN') AS Fuente_SRR_Turno_A,
            COALESCE(s.Fuente_SRR_Turno_B,'SIN_ORIGEN') AS Fuente_SRR_Turno_B,
            CONVERT(bit,COALESCE(s.Flag_SRR_Capeado_A,0)) AS Flag_SRR_Capeado_A,
            CONVERT(bit,COALESCE(s.Flag_SRR_Capeado_B,0)) AS Flag_SRR_Capeado_B
        FROM [inventar_SpcHidr].[v_inventario_chancado_test] i
        LEFT JOIN [inventar_SpcHidr].[Historico_Apilado_Diario] a
          ON CAST(a.Fecha AS date)=i.Fecha
        LEFT JOIN [inventar_SpcHidr].[v_humedad_inventario_test] h
          ON h.Fecha=i.Fecha
        LEFT JOIN srr_dia s ON s.Fecha=i.Fecha
        WHERE i.Fecha BETWEEN @FechaInicio AND @FechaFin
    ),
    balance AS
    (
        SELECT b.*,
            CASE WHEN b.Apilado_TMH_Bruto IS NOT NULL
                       AND b.Flag_Humedad_Inventario_Valida=1
                 THEN b.Apilado_TMH_Bruto*(1.0-b.Humedad_Inventario/100.0) END AS Apilado_TMS_Sin_Ajuste
        FROM base b
    ),
    mineral AS
    (
        SELECT b.*,
            CASE WHEN b.Apilado_TMS_Sin_Ajuste IS NOT NULL
                       AND b.Flag_Inventario_Valido=1
                       AND b.Delta_Inventario_Chancado_TMS IS NOT NULL
                 THEN b.Apilado_TMS_Sin_Ajuste+b.Delta_Inventario_Chancado_TMS END AS Mineral_Chancado_TMS_Sin_Ajuste
        FROM balance b
    ),
    chancado AS
    (
        SELECT m.*,
            CASE WHEN m.Mineral_Chancado_TMS_Sin_Ajuste IS NOT NULL
                       AND m.Sal_Dia IS NOT NULL AND m.SRR_TMS_Dia_Origen IS NOT NULL
                 THEN m.Mineral_Chancado_TMS_Sin_Ajuste-m.Sal_Dia-m.SRR_TMS_Dia_Origen END AS Chancado_TMS_Sin_Ajuste
        FROM mineral m
    ),
    camiones AS
    (
        SELECT
            m.fecha AS Fecha,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.flota_cex_tc))))='KOM'
                     THEN COALESCE(TRY_CONVERT(float,m.ton_descarga),0) ELSE 0 END) AS Produccion_KOM_TMH,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.flota_cex_tc))))='CAT'
                     THEN COALESCE(TRY_CONVERT(float,m.ton_descarga),0) ELSE 0 END) AS Produccion_CAT_TMH,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.flota_cex_tc))))='KOM'
                     THEN COALESCE(TRY_CONVERT(float,m.n_break),0) ELSE 0 END) AS Vueltas_KOM,
            SUM(CASE WHEN UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.flota_cex_tc))))='CAT'
                     THEN COALESCE(TRY_CONVERT(float,m.n_break),0) ELSE 0 END) AS Vueltas_CAT
        FROM [inventar_SpcHidr].[mov_cam_powerbi] m
        WHERE m.fecha BETWEEN @FechaInicio AND @FechaFin
          AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.destino_descarga))))='CH01'
          AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.fase))))<>'SRR'
          AND UPPER(LTRIM(RTRIM(CONVERT(nvarchar(100),m.flota_cex_tc)))) IN ('KOM','CAT')
        GROUP BY m.fecha
    ),
    factor_base AS
    (
        SELECT b.*,
            COALESCE(c.Produccion_KOM_TMH,0) AS Produccion_KOM_TMH,
            COALESCE(c.Produccion_CAT_TMH,0) AS Produccion_CAT_TMH,
            COALESCE(c.Vueltas_KOM,0) AS Vueltas_KOM,
            COALESCE(c.Vueltas_CAT,0) AS Vueltas_CAT,
            COALESCE(c.Produccion_KOM_TMH,0)+COALESCE(c.Produccion_CAT_TMH,0) AS Dato_Mina_TMH,
            CASE WHEN b.Chancado_TMS_Sin_Ajuste IS NOT NULL
                       AND b.Humedad_Inventario>=0 AND b.Humedad_Inventario<100
                 THEN b.Chancado_TMS_Sin_Ajuste/NULLIF(1.0-b.Humedad_Inventario/100.0,0) END AS Chancado_TMH_Sin_Ajuste
        FROM chancado b LEFT JOIN camiones c ON c.Fecha=b.Fecha
    ),
    cargas AS
    (
        SELECT f.*,
            CASE WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL AND f.Dato_Mina_TMH>0
                 THEN f.Chancado_TMH_Sin_Ajuste*f.Produccion_KOM_TMH/f.Dato_Mina_TMH END AS Chancado_KOM_TMH_Sin_Ajuste,
            CASE WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL AND f.Dato_Mina_TMH>0
                 THEN f.Chancado_TMH_Sin_Ajuste*f.Produccion_CAT_TMH/f.Dato_Mina_TMH END AS Chancado_CAT_TMH_Sin_Ajuste,
            CASE WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL AND f.Dato_Mina_TMH>0
                       AND f.Produccion_KOM_TMH>0 AND f.Vueltas_KOM>0
                 THEN (f.Chancado_TMH_Sin_Ajuste*f.Produccion_KOM_TMH/f.Dato_Mina_TMH)/f.Vueltas_KOM END AS Carga_KOM_Sin_Ajuste,
            CASE WHEN f.Chancado_TMH_Sin_Ajuste IS NOT NULL AND f.Dato_Mina_TMH>0
                       AND f.Produccion_CAT_TMH>0 AND f.Vueltas_CAT>0
                 THEN (f.Chancado_TMH_Sin_Ajuste*f.Produccion_CAT_TMH/f.Dato_Mina_TMH)/f.Vueltas_CAT END AS Carga_CAT_Sin_Ajuste
        FROM factor_base f
    ),
    corregido AS
    (
        SELECT c.*,
            CASE WHEN c.Produccion_KOM_TMH=0 THEN 0.0
                 WHEN c.Vueltas_KOM<=0 OR c.Carga_KOM_Sin_Ajuste IS NULL THEN NULL
                 WHEN c.Carga_KOM_Sin_Ajuste<=380 THEN c.Chancado_KOM_TMH_Sin_Ajuste
                 ELSE c.Vueltas_KOM*380.0 END AS KOM_TMH_Corregido,
            CASE WHEN c.Produccion_CAT_TMH=0 THEN 0.0
                 WHEN c.Vueltas_CAT<=0 OR c.Carga_CAT_Sin_Ajuste IS NULL THEN NULL
                 WHEN c.Carga_CAT_Sin_Ajuste<=265 THEN c.Chancado_CAT_TMH_Sin_Ajuste
                 ELSE c.Vueltas_CAT*265.0 END AS CAT_TMH_Corregido
        FROM cargas c
    )
    SELECT
        c.Fecha,
        c.SRR_TMS_Turno_A_Origen, c.SRR_TMS_Turno_B_Origen, c.SRR_TMS_Dia_Origen,
        c.Fuente_SRR_Turno_A, c.Fuente_SRR_Turno_B,
        c.Flag_SRR_Capeado_A, c.Flag_SRR_Capeado_B,
        c.Chancado_TMS_Sin_Ajuste, c.Chancado_TMH_Sin_Ajuste,
        c.Produccion_KOM_TMH, c.Produccion_CAT_TMH, c.Vueltas_KOM, c.Vueltas_CAT,
        c.Carga_KOM_Sin_Ajuste, c.Carga_CAT_Sin_Ajuste,
        c.KOM_TMH_Corregido, c.CAT_TMH_Corregido,
        CASE WHEN c.Chancado_TMH_Sin_Ajuste>0 AND c.Dato_Mina_TMH>0
                   AND c.KOM_TMH_Corregido IS NOT NULL AND c.CAT_TMH_Corregido IS NOT NULL
                   AND (c.Produccion_KOM_TMH=0 OR c.Vueltas_KOM>0)
                   AND (c.Produccion_CAT_TMH=0 OR c.Vueltas_CAT>0)
             THEN (c.KOM_TMH_Corregido+c.CAT_TMH_Corregido)/c.Chancado_TMH_Sin_Ajuste END AS Factor_Ajuste_Calculado,
        CASE WHEN c.Chancado_TMH_Sin_Ajuste>0 AND c.Dato_Mina_TMH>0
                   AND c.KOM_TMH_Corregido IS NOT NULL AND c.CAT_TMH_Corregido IS NOT NULL
                   AND (c.Produccion_KOM_TMH=0 OR c.Vueltas_KOM>0)
                   AND (c.Produccion_CAT_TMH=0 OR c.Vueltas_CAT>0)
             THEN 1 ELSE 0 END AS Flag_Factor_Ajuste_Valido,
        CASE
            WHEN c.Flag_Humedad_Inventario_Valida<>1 OR c.Humedad_Inventario IS NULL THEN 'SIN_HUMEDAD'
            WHEN c.Flag_Inventario_Valido<>1 OR c.Delta_Inventario_Chancado_TMS IS NULL THEN 'SIN_INVENTARIO'
            WHEN c.Chancado_TMH_Sin_Ajuste IS NULL THEN 'SIN_BALANCE_CHANCADO'
            WHEN c.Dato_Mina_TMH<=0 THEN 'SIN_DATOS_CAMIONES'
            WHEN (c.Produccion_KOM_TMH>0 AND c.Vueltas_KOM<=0)
              OR (c.Produccion_CAT_TMH>0 AND c.Vueltas_CAT<=0) THEN 'SIN_VUELTAS'
            WHEN c.Carga_KOM_Sin_Ajuste>380 AND c.Carga_CAT_Sin_Ajuste>265 THEN 'OK_AJUSTE_AMBAS_FLOTAS'
            WHEN c.Carga_KOM_Sin_Ajuste>380 THEN 'OK_AJUSTE_KOM'
            WHEN c.Carga_CAT_Sin_Ajuste>265 THEN 'OK_AJUSTE_CAT'
            ELSE 'OK_SIN_AJUSTE'
        END AS Estado_Calculo
    FROM corregido c
    ORDER BY c.Fecha;
END;
