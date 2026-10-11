-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE   PROCEDURE inventar_SpcHidr.sp_actualizar_campana_parcela_control
    @pad_id     INT = NULL,
    @parcela_id INT = NULL,
    @campana_id INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    ;WITH camp_rango AS (
        SELECT
            c.[id_campaña]                          AS campana_id,
            pa.id_pad,
            MAX(c.[numero_campaña])                 AS numero_campana,
            MIN(CAST(c.fecha_inicio  AS DATE))      AS camp_fecha_ini,
            MAX(CAST(c.fecha_termino AS DATE))      AS camp_fecha_fin
        FROM inventar_SpcHidr.[campaña] c
        INNER JOIN inventar_SpcHidr.modulo  mc ON mc.id_modulo  = c.id_modulo
        INNER JOIN inventar_SpcHidr.parcela pc ON pc.id_parcela = mc.id_parcela
        INNER JOIN inventar_SpcHidr.[pad]   pa ON pa.id_pad     = pc.id_pad
        GROUP BY c.[id_campaña], pa.id_pad
    ),

    universo AS (
        SELECT DISTINCT
            m.campana_id    AS campaña_id,
            m.pad_id,
            m.parcela_id    AS id_parcela,
            m.modulo_id
        FROM inventar_SpcHidr.mapa_campana_modulo_parcela m
        WHERE (@pad_id     IS NULL OR m.pad_id     = @pad_id)
          AND (@parcela_id IS NULL OR m.parcela_id = @parcela_id)
          AND (@campana_id IS NULL OR m.campana_id = @campana_id)
    ),

    base AS (
        SELECT
            u.campaña_id,
            u.pad_id,
            u.id_parcela,
            u.modulo_id,
            p.numero                        AS num_parcela,
            mo.numero                       AS num_modulo,
            pa.nombre                       AS nombre_pad,
            CAST(p.numero  AS VARCHAR(10))  AS nombre_parcela,
            CAST(mo.numero AS VARCHAR(10))  AS nombre_modulo,
            apc.col_numero,
            UPPER(pa.nombre)                AS tipo_pad,
            cr.numero_campana,
            cr.camp_fecha_ini,
            cr.camp_fecha_fin
        FROM universo u
        INNER JOIN inventar_SpcHidr.modulo  mo ON mo.id_modulo  = u.modulo_id
        INNER JOIN inventar_SpcHidr.parcela p  ON p.id_parcela  = u.id_parcela
        INNER JOIN inventar_SpcHidr.[pad]   pa ON pa.id_pad     = u.pad_id
        LEFT  JOIN inventar_SpcHidr.aux_parcela_columna apc
            ON apc.parcela_id = u.id_parcela
        LEFT  JOIN camp_rango cr
            ON cr.campana_id = u.campaña_id
           AND cr.id_pad     = u.pad_id
    ),

    carguio AS (
        SELECT
            m.campana_id                            AS campaña_id,
            m.modulo_id,
            m.parcela_id                            AS id_parcela,
            m.pad_id,
            CAST(m.fecha_ini_carguio AS DATE)       AS fecha_ini_carguio,
            CAST(m.fecha_fin_carguio AS DATE)       AS fecha_fin_carguio,
            ROW_NUMBER() OVER (
                PARTITION BY m.campana_id, m.parcela_id
                ORDER BY m.fecha_ini_carguio, m.modulo_id
            )                                       AS secuencia_carguio
        FROM inventar_SpcHidr.mapa_campana_modulo_parcela m
        WHERE m.fecha_ini_carguio IS NOT NULL
          AND (@pad_id     IS NULL OR m.pad_id     = @pad_id)
          AND (@parcela_id IS NULL OR m.parcela_id = @parcela_id)
          AND (@campana_id IS NULL OR m.campana_id = @campana_id)
    ),

    reclamo AS (
        SELECT
            m.campana_id                            AS campaña_id,
            m.modulo_id,
            m.parcela_id                            AS id_parcela,
            m.pad_id,
            CAST(m.fecha_ini_reclamo AS DATE)       AS fecha_ini_retiro,
            CAST(m.fecha_fin_reclamo AS DATE)       AS fecha_fin_retiro,
            ROW_NUMBER() OVER (
                PARTITION BY m.campana_id, m.parcela_id
                ORDER BY m.fecha_ini_reclamo, m.modulo_id
            )                                       AS secuencia_retiro
        FROM inventar_SpcHidr.mapa_campana_modulo_parcela m
        WHERE m.fecha_ini_reclamo IS NOT NULL
          AND (@pad_id     IS NULL OR m.pad_id     = @pad_id)
          AND (@parcela_id IS NULL OR m.parcela_id = @parcela_id)
          AND (@campana_id IS NULL OR m.campana_id = @campana_id)
    ),

    riego_oxido AS (
        SELECT
            b.campaña_id,
            b.modulo_id,
            b.id_parcela,
            MIN(CAST(f.fecha_registro AS DATE)) AS fecha_primer_riego,
            MAX(CAST(f.fecha_registro AS DATE)) AS fecha_ultimo_riego
        FROM base b
        INNER JOIN carguio ca
            ON  ca.campaña_id = b.campaña_id
            AND ca.modulo_id  = b.modulo_id
            AND ca.id_parcela = b.id_parcela
        INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot f
            ON  f.parcela_numero = b.col_numero
            AND f.caudal > 1
            AND CAST(f.fecha_registro AS DATE) >= ca.fecha_ini_carguio
            AND CAST(f.fecha_registro AS DATE) <= ISNULL(b.camp_fecha_fin, CAST(GETDATE() AS DATE))
        WHERE b.tipo_pad LIKE '%OXIDO%'
          AND b.col_numero IS NOT NULL
        GROUP BY b.campaña_id, b.modulo_id, b.id_parcela
    ),

    riego_sulfuro AS (
        SELECT
            b.campaña_id,
            b.modulo_id,
            b.id_parcela,
            MIN(CAST(f.fecha_registro AS DATE)) AS fecha_primer_riego,
            MAX(CAST(f.fecha_registro AS DATE)) AS fecha_ultimo_riego
        FROM base b
        INNER JOIN carguio ca
            ON  ca.campaña_id = b.campaña_id
            AND ca.modulo_id  = b.modulo_id
            AND ca.id_parcela = b.id_parcela
        INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot f
            ON  f.parcela_numero = b.col_numero
            AND f.caudal > 1
            AND CAST(f.fecha_registro AS DATE) >= ca.fecha_ini_carguio
            AND CAST(f.fecha_registro AS DATE) <= ISNULL(b.camp_fecha_fin, CAST(GETDATE() AS DATE))
        WHERE b.tipo_pad LIKE '%SULFURO%'
          AND b.col_numero IS NOT NULL
        GROUP BY b.campaña_id, b.modulo_id, b.id_parcela
    ),

    drenaje_oxido AS (
        SELECT
            b.campaña_id,
            b.modulo_id,
            b.id_parcela,
            MIN(CAST(d.fecha_registro AS DATE)) AS fecha_ini_drenaje,
            MAX(CAST(d.fecha_registro AS DATE)) AS fecha_fin_drenaje
        FROM base b
        INNER JOIN carguio ca
            ON  ca.campaña_id = b.campaña_id
            AND ca.modulo_id  = b.modulo_id
            AND ca.id_parcela = b.id_parcela
        INNER JOIN inventar_SpcHidr.v_drena_oxido_unpivot d
            ON  d.parcela_numero = b.col_numero
            AND d.cu_pp > 0
            AND CAST(d.fecha_registro AS DATE) >= ca.fecha_ini_carguio
            AND CAST(d.fecha_registro AS DATE) <= ISNULL(b.camp_fecha_fin, CAST(GETDATE() AS DATE))
        WHERE b.tipo_pad LIKE '%OXIDO%'
          AND b.col_numero IS NOT NULL
        GROUP BY b.campaña_id, b.modulo_id, b.id_parcela
    ),

    drenaje_sulfuro AS (
        SELECT
            b.campaña_id,
            b.modulo_id,
            b.id_parcela,
            MIN(CAST(d.fecha_registro AS DATE)) AS fecha_ini_drenaje,
            MAX(CAST(d.fecha_registro AS DATE)) AS fecha_fin_drenaje
        FROM base b
        INNER JOIN carguio ca
            ON  ca.campaña_id = b.campaña_id
            AND ca.modulo_id  = b.modulo_id
            AND ca.id_parcela = b.id_parcela
        INNER JOIN inventar_SpcHidr.v_drena_sulfuro_unpivot d
            ON  d.parcela_numero = b.col_numero
            AND d.cu_pp > 0
            AND CAST(d.fecha_registro AS DATE) >= ca.fecha_ini_carguio
            AND CAST(d.fecha_registro AS DATE) <= ISNULL(b.camp_fecha_fin, CAST(GETDATE() AS DATE))
        WHERE b.tipo_pad LIKE '%SULFURO%'
          AND b.col_numero IS NOT NULL
        GROUP BY b.campaña_id, b.modulo_id, b.id_parcela
    ),

    tonelajes AS (
        SELECT
            mt.[campaña_id],
            mt.modulo_id,
            SUM(mt.TMH)                                                         AS tmh_cargado,
            SUM(mt.TMS)                                                         AS tms_cargado,
            CASE WHEN SUM(mt.TMH) > 0
                 THEN SUM(mt.Humedad    * mt.TMH) / SUM(mt.TMH) END            AS humedad_promedio,
            CASE WHEN SUM(mt.TMS) > 0
                 THEN SUM(mt.Sal        * mt.TMS) / SUM(mt.TMS) END            AS sal_promedio,
            CASE WHEN SUM(mt.TMS) > 0
                 THEN SUM(mt.[CuT_TM]  * mt.TMS) / SUM(mt.TMS) END            AS cut_tm_total,
            CASE WHEN SUM(mt.TMS) > 0
                 THEN SUM(mt.[CuS_TM]  * mt.TMS) / SUM(mt.TMS) END            AS cus_tm_total,
            CASE WHEN SUM(mt.TMS) > 0
                 THEN SUM(mt.[Cu_Insoluble] * mt.TMS) / SUM(mt.TMS) END        AS cu_insoluble_total,
            MAX(mt.[Altura Módulo])                                             AS altura_modulo_max
        FROM inventar_SpcHidr.modulos_turnos mt
        WHERE mt.[campaña_id] IS NOT NULL
          AND mt.modulo_id    IS NOT NULL
          AND (@pad_id     IS NULL OR mt.pad_id     = @pad_id)
          AND (@campana_id IS NULL OR mt.[campaña_id] = @campana_id)
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),

    resultado AS (
        SELECT
            b.campaña_id,
            b.modulo_id,
            b.id_parcela,
            b.pad_id,
            b.numero_campana,
            b.nombre_pad,
            b.nombre_parcela,
            b.nombre_modulo,

            ca.secuencia_carguio,
            rc.secuencia_retiro,

            ca.fecha_ini_carguio,
            ca.fecha_fin_carguio,

            ca.fecha_fin_carguio AS fecha_ini_reposo,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                THEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
            END AS fecha_fin_reposo,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                THEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
            END AS fecha_ini_operacion,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                 AND COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje)
                     >= COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
                THEN COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje)
            END AS fecha_fin_operacion,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                 AND COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje)
                     >= COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
                THEN COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje)
            END AS fecha_ini_drenaje,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                 AND COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje)
                     >= COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
                THEN COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje)
            END AS fecha_fin_drenaje,

            rc.fecha_ini_retiro,
            rc.fecha_fin_retiro,

            t.tmh_cargado,
            t.tms_cargado,
            t.humedad_promedio,
            t.sal_promedio,
            t.cut_tm_total,
            t.cus_tm_total,
            t.cu_insoluble_total,
            t.altura_modulo_max,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                THEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
            END AS fecha_primer_riego,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                THEN COALESCE(ro.fecha_ultimo_riego, rs.fecha_ultimo_riego)
            END AS fecha_ultimo_riego,

            DATEDIFF(DAY, ca.fecha_ini_carguio, ca.fecha_fin_carguio) AS dias_carguio,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                THEN DATEDIFF(DAY, ca.fecha_fin_carguio,
                                   COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego))
            END AS dias_reposo,

            CASE
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) >= ca.fecha_fin_carguio
                 AND COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje)
                     >= COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego)
                THEN DATEDIFF(DAY, COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego),
                                   COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje))
            END AS dias_operacion,

            CASE
                WHEN COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje) IS NOT NULL
                 AND COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje) IS NOT NULL
                THEN DATEDIFF(DAY, COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje),
                                   COALESCE(do2.fecha_fin_drenaje, ds.fecha_fin_drenaje))
            END AS dias_drenaje,

            DATEDIFF(DAY, rc.fecha_ini_retiro, rc.fecha_fin_retiro) AS dias_retiro,

            CASE
                WHEN rc.fecha_ini_retiro IS NOT NULL
                    THEN 'reclamo'
                WHEN COALESCE(do2.fecha_ini_drenaje, ds.fecha_ini_drenaje) IS NOT NULL
                    THEN 'drenaje'
                WHEN COALESCE(ro.fecha_primer_riego, rs.fecha_primer_riego) IS NOT NULL
                    THEN 'operacion'
                WHEN ca.fecha_fin_carguio IS NOT NULL
                    THEN 'reposo'
                WHEN ca.fecha_ini_carguio IS NOT NULL
                    THEN 'carguio'
                ELSE 'sin_dato'
            END AS estado_ciclo

        FROM base b
        LEFT JOIN carguio ca
            ON  ca.campaña_id = b.campaña_id
            AND ca.modulo_id  = b.modulo_id
            AND ca.id_parcela = b.id_parcela
        LEFT JOIN reclamo rc
            ON  rc.campaña_id = b.campaña_id
            AND rc.modulo_id  = b.modulo_id
            AND rc.id_parcela = b.id_parcela
        LEFT JOIN riego_oxido ro
            ON  ro.campaña_id = b.campaña_id
            AND ro.modulo_id  = b.modulo_id
            AND ro.id_parcela = b.id_parcela
        LEFT JOIN riego_sulfuro rs
            ON  rs.campaña_id = b.campaña_id
            AND rs.modulo_id  = b.modulo_id
            AND rs.id_parcela = b.id_parcela
        LEFT JOIN drenaje_oxido do2
            ON  do2.campaña_id = b.campaña_id
            AND do2.modulo_id  = b.modulo_id
            AND do2.id_parcela = b.id_parcela
        LEFT JOIN drenaje_sulfuro ds
            ON  ds.campaña_id = b.campaña_id
            AND ds.modulo_id  = b.modulo_id
            AND ds.id_parcela = b.id_parcela
        LEFT JOIN tonelajes t
            ON  t.[campaña_id] = b.campaña_id
            AND t.modulo_id    = b.modulo_id
    )

    MERGE inventar_SpcHidr.campana_parcela_control AS tgt
    USING resultado AS src
        ON  tgt.campana_id  = src.campaña_id
        AND tgt.pad_id      = src.pad_id
        AND tgt.parcela_id  = src.id_parcela
        AND tgt.modulo_id   = src.modulo_id

    WHEN MATCHED THEN UPDATE SET
        tgt.numero_campana      = src.numero_campana,
        tgt.nombre_pad          = src.nombre_pad,
        tgt.nombre_parcela      = src.nombre_parcela,
        tgt.nombre_modulo       = src.nombre_modulo,
        tgt.secuencia_carguio   = src.secuencia_carguio,
        tgt.secuencia_retiro    = src.secuencia_retiro,
        tgt.fecha_ini_carguio   = src.fecha_ini_carguio,
        tgt.fecha_fin_carguio   = src.fecha_fin_carguio,
        tgt.fecha_ini_reposo    = src.fecha_ini_reposo,
        tgt.fecha_fin_reposo    = src.fecha_fin_reposo,
        tgt.fecha_ini_operacion = src.fecha_ini_operacion,
        tgt.fecha_fin_operacion = src.fecha_fin_operacion,
        tgt.fecha_ini_drenaje   = src.fecha_ini_drenaje,
        tgt.fecha_fin_drenaje   = src.fecha_fin_drenaje,
        tgt.fecha_ini_retiro    = src.fecha_ini_retiro,
        tgt.fecha_fin_retiro    = src.fecha_fin_retiro,
        tgt.tmh_cargado         = src.tmh_cargado,
        tgt.tms_cargado         = src.tms_cargado,
        tgt.humedad_promedio    = src.humedad_promedio,
        tgt.sal_promedio        = src.sal_promedio,
        tgt.cut_tm_total        = src.cut_tm_total,
        tgt.cus_tm_total        = src.cus_tm_total,
        tgt.cu_insoluble_total  = src.cu_insoluble_total,
        tgt.altura_modulo_max   = src.altura_modulo_max,
        tgt.fecha_primer_riego  = src.fecha_primer_riego,
        tgt.fecha_ultimo_riego  = src.fecha_ultimo_riego,
        tgt.dias_carguio        = src.dias_carguio,
        tgt.dias_reposo         = src.dias_reposo,
        tgt.dias_operacion      = src.dias_operacion,
        tgt.dias_drenaje        = src.dias_drenaje,
        tgt.dias_retiro         = src.dias_retiro,
        tgt.estado_ciclo        = src.estado_ciclo,
        tgt.fecha_actualizacion = GETDATE()

    WHEN NOT MATCHED BY TARGET THEN INSERT (
        campana_id, pad_id, parcela_id, modulo_id,
        numero_campana, nombre_pad, nombre_parcela, nombre_modulo,
        secuencia_carguio, secuencia_retiro,
        fecha_ini_carguio, fecha_fin_carguio,
        fecha_ini_reposo, fecha_fin_reposo,
        fecha_ini_operacion, fecha_fin_operacion,
        fecha_ini_drenaje, fecha_fin_drenaje,
        fecha_ini_retiro, fecha_fin_retiro,
        tmh_cargado, tms_cargado,
        humedad_promedio, sal_promedio,
        cut_tm_total, cus_tm_total, cu_insoluble_total,
        altura_modulo_max,
        fecha_primer_riego, fecha_ultimo_riego,
        dias_carguio, dias_reposo, dias_operacion, dias_drenaje, dias_retiro,
        estado_ciclo, fecha_creacion, fecha_actualizacion
    ) VALUES (
        src.campaña_id, src.pad_id, src.id_parcela, src.modulo_id,
        src.numero_campana, src.nombre_pad, src.nombre_parcela, src.nombre_modulo,
        src.secuencia_carguio, src.secuencia_retiro,
        src.fecha_ini_carguio, src.fecha_fin_carguio,
        src.fecha_ini_reposo, src.fecha_fin_reposo,
        src.fecha_ini_operacion, src.fecha_fin_operacion,
        src.fecha_ini_drenaje, src.fecha_fin_drenaje,
        src.fecha_ini_retiro, src.fecha_fin_retiro,
        src.tmh_cargado, src.tms_cargado,
        src.humedad_promedio, src.sal_promedio,
        src.cut_tm_total, src.cus_tm_total, src.cu_insoluble_total,
        src.altura_modulo_max,
        src.fecha_primer_riego, src.fecha_ultimo_riego,
        src.dias_carguio, src.dias_reposo, src.dias_operacion, src.dias_drenaje, src.dias_retiro,
        src.estado_ciclo, GETDATE(), GETDATE()
    );

    SELECT @@ROWCOUNT AS filas_afectadas, GETDATE() AS ejecutado_en;
END;
