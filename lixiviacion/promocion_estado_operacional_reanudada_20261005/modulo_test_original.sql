
CREATE   FUNCTION
inventar_SpcHidr.fn_estado_operacional_modulo_diario_test
(
    @fecha      date,
    @pad_id     int,
    @parcela_id int
)
RETURNS TABLE
AS
RETURN
(
    WITH

    /*==========================================================
      1. PARCELA SOLICITADA
    ==========================================================*/
    parcela_ctx AS
    (
        SELECT
            p.id_pad       AS pad_id,
            pa.nombre      AS nombre_pad,
            p.id_parcela   AS parcela_id,
            p.numero       AS numero_parcela
        FROM inventar_SpcHidr.parcela p
        INNER JOIN inventar_SpcHidr.pad pa
            ON pa.id_pad = p.id_pad
        WHERE p.id_pad     = @pad_id
          AND p.id_parcela = @parcela_id
    ),

    /*==========================================================
      2. CAMPAÑAS DE LA PARCELA
    ==========================================================*/
    campanas AS
    (
        SELECT
            c.pad_id,
            c.campana_id,
            c.parcela_id,
            MAX(c.numero_campana) AS numero_campana,
            MIN(c.fecha_ini_carguio) AS fecha_ini_campana
        FROM inventar_SpcHidr.campana_parcela_control c
        WHERE c.pad_id     = @pad_id
          AND c.parcela_id = @parcela_id
          AND c.fecha_ini_carguio IS NOT NULL
        GROUP BY
            c.pad_id,
            c.campana_id,
            c.parcela_id
    ),

    ventanas AS
    (
        SELECT
            c.*,
            LEAD(c.fecha_ini_campana) OVER
            (
                PARTITION BY c.pad_id, c.parcela_id
                ORDER BY c.fecha_ini_campana, c.campana_id
            ) AS fecha_ini_campana_siguiente
        FROM campanas c
    ),

    campana_activa AS
    (
        SELECT
            v.*,
            p.numero_parcela,
            p.nombre_pad
        FROM ventanas v
        INNER JOIN parcela_ctx p
            ON  p.pad_id     = v.pad_id
            AND p.parcela_id = v.parcela_id
        WHERE @fecha >= v.fecha_ini_campana
          AND
          (
              v.fecha_ini_campana_siguiente IS NULL
              OR @fecha < v.fecha_ini_campana_siguiente
          )
    ),

    /*==========================================================
      3. EXTREMOS REALES DE RIEGO EN LA VENTANA DE CAMPAÑA
    ==========================================================*/
    riego_ox_campana AS
    (
        SELECT
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id,

            MIN(CAST(r.fecha_registro AS date))
                AS fecha_primer_riego_real,

            MAX(CAST(r.fecha_registro AS date))
                AS fecha_ultimo_riego_real

        FROM campana_activa ca
        INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot r
            ON ca.pad_id = 1
           AND r.parcela_numero = ca.numero_parcela
           AND CAST(r.fecha_registro AS date) >= ca.fecha_ini_campana
           AND
           (
               ca.fecha_ini_campana_siguiente IS NULL
               OR CAST(r.fecha_registro AS date)
                    < ca.fecha_ini_campana_siguiente
           )
           AND r.caudal > 1

        GROUP BY
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id
    ),

    riego_sulf_campana AS
    (
        SELECT
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id,

            MIN(CAST(r.fecha_registro AS date))
                AS fecha_primer_riego_real,

            MAX(CAST(r.fecha_registro AS date))
                AS fecha_ultimo_riego_real

        FROM campana_activa ca
        INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot r
            ON ca.pad_id = 2
           AND r.parcela_numero = ca.numero_parcela
           AND CAST(r.fecha_registro AS date) >= ca.fecha_ini_campana
           AND
           (
               ca.fecha_ini_campana_siguiente IS NULL
               OR CAST(r.fecha_registro AS date)
                    < ca.fecha_ini_campana_siguiente
           )
           AND r.caudal > 1

        GROUP BY
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id
    ),

    /*==========================================================
      4. EXTREMOS REALES DE DRENAJE
    ==========================================================*/
    drenaje_ox_campana AS
    (
        SELECT
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id,

            MIN(d.fecha_operacional)
                AS fecha_primer_drenaje_real,

            MAX(d.fecha_operacional)
                AS fecha_ultimo_drenaje_real

        FROM campana_activa ca
        INNER JOIN inventar_SpcHidr.v_drena_oxido_operacional d
            ON ca.pad_id = 1
           AND d.parcela_numero = ca.numero_parcela
           AND d.fecha_operacional >= ca.fecha_ini_campana
           AND
           (
               ca.fecha_ini_campana_siguiente IS NULL
               OR d.fecha_operacional
                    < ca.fecha_ini_campana_siguiente
           )
           AND d.cu_pp > 0

        GROUP BY
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id
    ),

    drenaje_sulf_campana AS
    (
        SELECT
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id,

            MIN(d.fecha_operacional)
                AS fecha_primer_drenaje_real,

            MAX(d.fecha_operacional)
                AS fecha_ultimo_drenaje_real

        FROM campana_activa ca
        INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional d
            ON ca.pad_id = 2
           AND d.parcela_numero = ca.numero_parcela
           AND d.fecha_operacional >= ca.fecha_ini_campana
           AND
           (
               ca.fecha_ini_campana_siguiente IS NULL
               OR d.fecha_operacional
                    < ca.fecha_ini_campana_siguiente
           )
           AND d.cu_pp > 0

        GROUP BY
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id
    ),

    extremos_hidraulicos AS
    (
        SELECT
            ca.pad_id,
            ca.campana_id,
            ca.parcela_id,

            CASE
                WHEN ca.pad_id = 1
                    THEN ro.fecha_primer_riego_real
                ELSE rs.fecha_primer_riego_real
            END AS fecha_primer_riego_real,

            CASE
                WHEN ca.pad_id = 1
                    THEN ro.fecha_ultimo_riego_real
                ELSE rs.fecha_ultimo_riego_real
            END AS fecha_ultimo_riego_real,

            CASE
                WHEN ca.pad_id = 1
                    THEN dox.fecha_primer_drenaje_real
                ELSE ds.fecha_primer_drenaje_real
            END AS fecha_primer_drenaje_real,

            CASE
                WHEN ca.pad_id = 1
                    THEN dox.fecha_ultimo_drenaje_real
                ELSE ds.fecha_ultimo_drenaje_real
            END AS fecha_ultimo_drenaje_real

        FROM campana_activa ca

        LEFT JOIN riego_ox_campana ro
            ON  ro.pad_id     = ca.pad_id
            AND ro.campana_id = ca.campana_id
            AND ro.parcela_id = ca.parcela_id

        LEFT JOIN riego_sulf_campana rs
            ON  rs.pad_id     = ca.pad_id
            AND rs.campana_id = ca.campana_id
            AND rs.parcela_id = ca.parcela_id

        LEFT JOIN drenaje_ox_campana dox
            ON  dox.pad_id     = ca.pad_id
            AND dox.campana_id = ca.campana_id
            AND dox.parcela_id = ca.parcela_id

        LEFT JOIN drenaje_sulf_campana ds
            ON  ds.pad_id     = ca.pad_id
            AND ds.campana_id = ca.campana_id
            AND ds.parcela_id = ca.parcela_id
    ),

    /*==========================================================
      5. ACTIVIDAD REAL DEL DÍA
         Cobertura != actividad
    ==========================================================*/
    riego_ox_dia AS
    (
        SELECT
            parcela_numero,
            1 AS tiene_dato_riego,

            CASE
                WHEN COUNT(caudal) = 0 THEN NULL
                ELSE MAX
                (
                    CASE
                        WHEN caudal > 1 THEN 1
                        ELSE 0
                    END
                )
            END AS riego_activo

        FROM inventar_SpcHidr.v_flujos_oxido_unpivot
        WHERE CAST(fecha_registro AS date) = @fecha
        GROUP BY parcela_numero
    ),

    riego_sulf_dia AS
    (
        SELECT
            parcela_numero,
            1 AS tiene_dato_riego,

            CASE
                WHEN COUNT(caudal) = 0 THEN NULL
                ELSE MAX
                (
                    CASE
                        WHEN caudal > 1 THEN 1
                        ELSE 0
                    END
                )
            END AS riego_activo

        FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot
        WHERE CAST(fecha_registro AS date) = @fecha
        GROUP BY parcela_numero
    ),

    drenaje_ox_dia AS
    (
        SELECT
            parcela_numero,
            1 AS tiene_dato_drenaje,

            CASE
                WHEN COUNT(cu_pp) = 0 THEN NULL
                ELSE MAX
                (
                    CASE
                        WHEN cu_pp > 0 THEN 1
                        ELSE 0
                    END
                )
            END AS drenaje_activo

        FROM inventar_SpcHidr.v_drena_oxido_operacional
        WHERE fecha_operacional = @fecha
        GROUP BY parcela_numero
    ),

    drenaje_sulf_dia AS
    (
        SELECT
            parcela_numero,
            1 AS tiene_dato_drenaje,

            CASE
                WHEN COUNT(cu_pp) = 0 THEN NULL
                ELSE MAX
                (
                    CASE
                        WHEN cu_pp > 0 THEN 1
                        ELSE 0
                    END
                )
            END AS drenaje_activo

        FROM inventar_SpcHidr.v_drena_sulfuro_operacional
        WHERE fecha_operacional = @fecha
        GROUP BY parcela_numero
    ),

    actividad AS
    (
        SELECT
            p.pad_id,
            p.parcela_id,

            CASE
                WHEN p.pad_id = 1 THEN ro.tiene_dato_riego
                ELSE rs.tiene_dato_riego
            END AS tiene_dato_riego,

            CASE
                WHEN p.pad_id = 1 THEN ro.riego_activo
                ELSE rs.riego_activo
            END AS riego_activo,

            CASE
                WHEN p.pad_id = 1 THEN dox.tiene_dato_drenaje
                ELSE ds.tiene_dato_drenaje
            END AS tiene_dato_drenaje,

            CASE
                WHEN p.pad_id = 1 THEN dox.drenaje_activo
                ELSE ds.drenaje_activo
            END AS drenaje_activo

        FROM parcela_ctx p

        LEFT JOIN riego_ox_dia ro
            ON p.pad_id = 1
           AND ro.parcela_numero = p.numero_parcela

        LEFT JOIN riego_sulf_dia rs
            ON p.pad_id = 2
           AND rs.parcela_numero = p.numero_parcela

        LEFT JOIN drenaje_ox_dia dox
            ON p.pad_id = 1
           AND dox.parcela_numero = p.numero_parcela

        LEFT JOIN drenaje_sulf_dia ds
            ON p.pad_id = 2
           AND ds.parcela_numero = p.numero_parcela
    ),

    /*==========================================================
      6. MÓDULOS DE LA CAMPAÑA ACTIVA
    ==========================================================*/
    base_modulos AS
    (
        SELECT
            c.pad_id,
            c.nombre_pad,
            c.parcela_id,
            c.nombre_parcela,

            c.campana_id,
            c.numero_campana,

            c.modulo_id,
            c.nombre_modulo,
            c.secuencia_carguio,
            c.secuencia_retiro,

            c.fecha_ini_carguio,
            c.fecha_fin_carguio,

            c.fecha_ini_retiro,
            c.fecha_fin_retiro,

            a.tiene_dato_riego,
            a.riego_activo,
            a.tiene_dato_drenaje,
            a.drenaje_activo,

            h.fecha_primer_riego_real,
            h.fecha_ultimo_riego_real,
            h.fecha_primer_drenaje_real,
            h.fecha_ultimo_drenaje_real

        FROM inventar_SpcHidr.campana_parcela_control c

        INNER JOIN campana_activa ca
            ON  ca.pad_id     = c.pad_id
            AND ca.campana_id = c.campana_id
            AND ca.parcela_id = c.parcela_id

        LEFT JOIN actividad a
            ON  a.pad_id     = c.pad_id
            AND a.parcela_id = c.parcela_id

        LEFT JOIN extremos_hidraulicos h
            ON  h.pad_id     = c.pad_id
            AND h.campana_id = c.campana_id
            AND h.parcela_id = c.parcela_id

        WHERE c.fecha_ini_carguio IS NOT NULL
          AND c.fecha_ini_carguio <= @fecha
    ),

    /*==========================================================
      7. MISMA REGLA DE ESTADO VALIDADA EN V2
    ==========================================================*/
    estado AS
    (
        SELECT
            b.*,

            CASE

                WHEN b.fecha_fin_retiro IS NOT NULL
                 AND @fecha > b.fecha_fin_retiro
                    THEN 'RECLAMADO'

                WHEN b.fecha_ini_retiro IS NOT NULL
                 AND @fecha >= b.fecha_ini_retiro
                 AND
                 (
                     b.fecha_fin_retiro IS NULL
                     OR @fecha <= b.fecha_fin_retiro
                 )
                    THEN 'RECLAMO'

                WHEN @fecha >= b.fecha_ini_carguio
                 AND
                 (
                     b.fecha_fin_carguio IS NULL
                     OR @fecha < b.fecha_fin_carguio
                 )
                    THEN 'APILADO'

                WHEN b.fecha_fin_carguio IS NOT NULL
                 AND @fecha >= b.fecha_fin_carguio
                 AND
                 (
                     b.fecha_primer_riego_real IS NULL
                     OR @fecha < b.fecha_primer_riego_real
                 )
                    THEN 'CONFORMADO_PRE_RIEGO'

                WHEN b.fecha_primer_riego_real IS NOT NULL
                 AND @fecha >= b.fecha_primer_riego_real
                 AND
                 (
                     b.tiene_dato_riego IS NULL
                     OR b.riego_activo IS NULL
                     OR b.tiene_dato_drenaje IS NULL
                     OR b.drenaje_activo IS NULL
                 )
                    THEN 'SIN_COBERTURA_HIDRAULICA'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 1
                    THEN 'RIEGO_DRENAJE'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 0
                    THEN 'RIEGO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND @fecha > b.fecha_ultimo_riego_real
                    THEN 'DRENAJE_RESIDUAL'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                    THEN 'DRENAJE_CON_RIEGO_PAUSADO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0
                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND @fecha > b.fecha_ultimo_riego_real
                 AND
                 (
                     b.fecha_ultimo_drenaje_real IS NULL
                     OR @fecha > b.fecha_ultimo_drenaje_real
                 )
                 AND
                 (
                     b.fecha_ini_retiro IS NULL
                     OR @fecha < b.fecha_ini_retiro
                 )
                    THEN 'REPOSO_PRE_RECLAMO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0
                    THEN 'PAUSA_HIDRAULICA'

                ELSE 'SIN_CLASIFICAR'

            END AS estado_modulo

        FROM base_modulos b
    )

    SELECT
        @fecha AS fecha,

        pad_id,
        nombre_pad,

        parcela_id,
        TRY_CONVERT(int,nombre_parcela)
            AS numero_parcela,

        campana_id,
        numero_campana,

        modulo_id,
        nombre_modulo,

        secuencia_carguio,
        secuencia_retiro,

        estado_modulo,

        tiene_dato_riego,
        riego_activo,

        tiene_dato_drenaje,
        drenaje_activo,

        fecha_ini_carguio,
        fecha_fin_carguio,

        fecha_primer_riego_real
            AS fecha_primer_riego,

        fecha_ultimo_riego_real
            AS fecha_ultima_actividad_riego,

        fecha_primer_drenaje_real
            AS fecha_primer_drenaje,

        fecha_ultimo_drenaje_real
            AS fecha_ultima_actividad_drenaje,

        fecha_ini_retiro
            AS fecha_ini_reclamo,

        fecha_fin_retiro
            AS fecha_fin_reclamo

    FROM estado
);
