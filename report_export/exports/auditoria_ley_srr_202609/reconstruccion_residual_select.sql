WITH MovCam_Deduplicado AS
    (
        SELECT
            m.*,
            rn = ROW_NUMBER() OVER
            (
                PARTITION BY
                    m.Fecha, m.Turno, m.Origen, m.Solido, m.Fase, m.Banco,
                    m.Pala, m.Destino, m.Poligono_CIO, m.Flota_CEX, m.Ton,
                    m.N_BREAK, m.[Ton hum diseño CAEX], m.Tonelaje_Hum_CIO,
                    m.Tonelaje_seco_CIO, m.PONDHumedad
                ORDER BY m.mov_id
            )
        FROM [inventar_SpcHidr].[mov_cam] AS m
        WHERE CAST(m.Fecha AS date) >= '20260901'
          AND CAST(m.Fecha AS date) <= '20260930'
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Destino, '')))) = 'CH01'
          AND UPPER(LTRIM(RTRIM(ISNULL(m.Fase, '')))) <> 'SRR'
    )
, lms_mc AS (    SELECT
        Fecha = CAST(Fecha AS date),
        Tonelaje_Mina_Stock = SUM(Tonelaje_seco_CIO),
        Ley_CuT_Mina_Stock = SUM(Tonelaje_seco_CIO * CuTG00) / NULLIF(SUM(Tonelaje_seco_CIO), 0),
        Cantidad_Registros_Validos = COUNT(*)
    FROM MovCam_Deduplicado
    WHERE rn = 1 AND Tonelaje_seco_CIO > 0 AND CuTG00 IS NOT NULL
    GROUP BY CAST(Fecha AS date)), lms_ic AS (SELECT
        CAST(ic.[date] AS date) AS Fecha,
        SUM(COALESCE(ic.tonnage, 0)) AS Tonelaje_Mina_Stock,
        SUM(ic.tonnage * ic.cut)
            / NULLIF(SUM(CASE WHEN ic.cut IS NOT NULL THEN ic.tonnage ELSE NULL END), 0)
            AS Ley_CuT_Mina_Stock,
        COUNT(*) AS Cantidad_Registros_Validos
    FROM [DEV_SIIR].[hidro].[imp_csv] ic
    WHERE ic.[to]     = 'CH01'
      AND ic.shovel  <> 'SRR'
      AND ic.origen   = 'IMP'
      AND ic.tonnage  > 0
      AND ic.cut IS NOT NULL
      AND CAST(ic.[date] AS date) >= '20260901'
      AND CAST(ic.[date] AS date) <= '20260930'
    GROUP BY CAST(ic.[date] AS date)), lms AS (SELECT Fecha,Ley_CuT_Mina_Stock,'MOV_CAM' AS Fuente FROM lms_mc UNION ALL SELECT Fecha,Ley_CuT_Mina_Stock,'IMP' FROM lms_ic i WHERE NOT EXISTS (SELECT 1 FROM lms_mc m WHERE m.Fecha=i.Fecha)), srr_turno AS
    (
        SELECT
            CAST(Fecha AS date) AS Fecha,
            Turno,
            CASE
                WHEN SRR IS NULL OR Apilado_TMS_Real IS NULL THEN NULL
                ELSE Apilado_TMS_Real * SRR / 100.0
            END AS SRR_TMS_Turno
        FROM [inventar_SpcHidr].[reporte_turno_cache_emision_test]
        WHERE CAST(Fecha AS date) >= '20260901'
          AND CAST(Fecha AS date) <= '20260930'
    )
, srr AS (    SELECT
        Fecha,
        SUM(CASE WHEN Turno = 'A' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_A,
        SUM(CASE WHEN Turno = 'B' THEN SRR_TMS_Turno END) AS SRR_TMS_Turno_B,
        SUM(SRR_TMS_Turno)                                AS SRR_TMS_Dia,
        CASE
            WHEN COUNT(DISTINCT Turno) >= 2
             AND SUM(CASE WHEN SRR_TMS_Turno IS NULL THEN 1 ELSE 0 END) = 0
                THEN 'OK'
            WHEN SUM(SRR_TMS_Turno) IS NOT NULL
                THEN 'OK_PARCIAL'
            ELSE 'SIN_SRR_TMS'
        END AS Flag_SRR_TMS_Dia
    FROM srr_turno
    GROUP BY Fecha) SELECT dc.Fecha,s.SRR_TMS_Dia,s.Flag_SRR_TMS_Dia,g.CuT_Real_Dia,lms.Ley_CuT_Mina_Stock,lms.Fuente AS Fuente_Ley_Mina_Stock,aj.Apilado_TMS_Bruto_Sin_Ajuste,aj.Apilado_TMS_Bruto_Ajustado,aj.Flag_Usa_Ajuste,aj.Sal_TMH_Dia,aj.Delta_Inventario_Chancado_TMS,aj.Chancado_TMS_Reporte,aj.SRR_TMS_Dia AS SRR_TMS_Fisico,dc.Ley_CuT_Real_srr AS Ley_Publicada,             CASE
                WHEN ISNULL(s.Flag_SRR_TMS_Dia, '') <> 'OK' OR s.SRR_TMS_Dia IS NULL OR s.SRR_TMS_Dia <= 0 THEN NULL
                WHEN g.CuT_Real_Dia IS NULL THEN NULL
                WHEN lms.Ley_CuT_Mina_Stock IS NULL THEN NULL
                WHEN CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END IS NULL THEN NULL
                WHEN aj.Sal_TMH_Dia IS NULL THEN NULL
                WHEN aj.Delta_Inventario_Chancado_TMS IS NULL THEN NULL
                WHEN aj.Chancado_TMS_Reporte IS NULL THEN NULL
                ELSE
                    (
                        g.CuT_Real_Dia
                        * (
                            CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1 THEN aj.Apilado_TMS_Bruto_Ajustado ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END
                            - aj.Sal_TMH_Dia
                            + aj.Delta_Inventario_Chancado_TMS
                          )
                        - (lms.Ley_CuT_Mina_Stock * aj.Chancado_TMS_Reporte)
                    )
                    / NULLIF(s.SRR_TMS_Dia, 0)
            END AS Ley_CuT_Real_srr FROM inventar_SpcHidr.Datos_conciliados_of dc LEFT JOIN srr s ON s.Fecha=dc.Fecha LEFT JOIN lms ON lms.Fecha=dc.Fecha LEFT JOIN inventar_SpcHidr.fn_generador_reporte_diario_emision_test('20260901','20261001') g ON g.Fecha=dc.Fecha LEFT JOIN inventar_SpcHidr.v_ajuste_camiones_emision_test aj ON aj.Fecha=dc.Fecha WHERE dc.Fecha>='20260901' AND dc.Fecha<'20261001' ORDER BY dc.Fecha