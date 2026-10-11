-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  sp_flujo_riego_drenaje.sql  — v3 (replanteo con tablas reales)
  Esquema : inventar_SpcHidr

  MODELO DE DATOS REAL VERIFICADO:
  ─────────────────────────────────
  parcela           → id_parcela, id_pad, numero
                      PAD OXIDO:   id_pad=1, parcela_id 1..32  (numero 1..32)
                      PAD SULFURO: id_pad=2, parcela_id 33..60 (numero 1..28)

  campana_parcela_control → vincula fecha a campaña por parcela:
                      campana_id, pad_id, parcela_id, fecha_primer_riego,
                      fecha_ultimo_riego, estado_ciclo, tms_cargado, cut_tm_total,
                      cus_tm_total, tmh_cargado, nombre_parcela

  v_flujos_oxido_unpivot   → id_flujo_real, fecha_registro, parcela_numero, caudal
  v_flujos_sulfuro_unpivot → id_flujo_real, fecha_registro, parcela_numero, caudal
  v_drena_oxido_unpivot    → id_registro,   fecha_registro, parcela_numero, cu_pp
  v_drena_sulfuro_unpivot  → id_registro,   fecha_registro, parcela_numero, cu_pp

  LÓGICA DE VINCULACIÓN:
    1. parcela_numero en las vistas = columna "numero" de tabla parcela
    2. Unir parcela por (id_pad + numero) → obtener id_parcela
    3. Unir campana_parcela_control por (pad_id + parcela_id) donde
       fecha_registro BETWEEN fecha_primer_riego AND fecha_ultimo_riego
       → obtener campana_id

  Parámetros:
    @campana_id   INT          — ID interno de la campaña
    @pad_id       INT = NULL   — 1=Oxido, 2=Sulfuro, NULL=ambos
    @parcela_id   INT = NULL   — id_parcela (tabla parcela), NULL=todas
    @fecha_desde  DATE = NULL
    @fecha_hasta  DATE = NULL
    @agrupar_por  VARCHAR(10) = 'dia'  -- 'dia' | 'semana' | 'mes'

  Uso:
      EXEC inventar_SpcHidr.sp_flujo_riego_drenaje @campana_id = 11;
      EXEC inventar_SpcHidr.sp_flujo_riego_drenaje @campana_id = 11, @pad_id = 1;
      EXEC inventar_SpcHidr.sp_flujo_riego_drenaje @campana_id = 11, @pad_id = 2,
           @agrupar_por = 'mes';
================================================================================
*/

CREATE   PROCEDURE inventar_SpcHidr.sp_flujo_riego_drenaje
    @campana_id  INT,
    @pad_id      INT         = NULL,
    @parcela_id  INT         = NULL,
    @fecha_desde DATE        = NULL,
    @fecha_hasta DATE        = NULL,
    @agrupar_por VARCHAR(10) = 'dia'
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

    /* -----------------------------------------------------------------------
       0. Rango de fechas desde campana_parcela_control si no se especifican
    ----------------------------------------------------------------------- */
    IF @fecha_desde IS NULL
        SELECT @fecha_desde = CAST(MIN(fecha_primer_riego) AS DATE)
        FROM   inventar_SpcHidr.campana_parcela_control
        WHERE  campana_id = @campana_id
          AND  (@pad_id IS NULL OR pad_id = @pad_id);

    IF @fecha_hasta IS NULL
        SELECT @fecha_hasta = CAST(MAX(fecha_ultimo_riego) AS DATE)
        FROM   inventar_SpcHidr.campana_parcela_control
        WHERE  campana_id = @campana_id
          AND  (@pad_id IS NULL OR pad_id = @pad_id);

    IF @fecha_hasta IS NULL SET @fecha_hasta = CAST(GETDATE() AS DATE);

    /* -----------------------------------------------------------------------
       1. FLUJOS RIEGO — PAD OXIDO (id_pad = 1)
          v_flujos_oxido_unpivot.parcela_numero → parcela.numero WHERE id_pad=1
          Vinculación a campaña por fecha_registro BETWEEN riego_ini AND riego_fin
    ----------------------------------------------------------------------- */
    CREATE TABLE #flujos (
        fecha_registro  DATE,
        pad_id          INT,
        parcela_id      INT,
        parcela_numero  INT,
        campana_id      INT,
        caudal          FLOAT,
        tipo            VARCHAR(10)   -- 'riego'
    );

    /* Oxido */
    INSERT INTO #flujos
    SELECT
        CAST(f.fecha_registro AS DATE),
        1                               AS pad_id,
        p.id_parcela,
        p.numero                        AS parcela_numero,
        cpc.campana_id,
        f.caudal,
        'riego'
    FROM inventar_SpcHidr.v_flujos_oxido_unpivot f
    INNER JOIN inventar_SpcHidr.parcela p
            ON p.numero  = f.parcela_numero
           AND p.id_pad  = 1
    INNER JOIN inventar_SpcHidr.campana_parcela_control cpc
            ON cpc.pad_id     = 1
           AND cpc.parcela_id = p.id_parcela
           AND CAST(f.fecha_registro AS DATE)
               BETWEEN CAST(cpc.fecha_primer_riego AS DATE)
                   AND CAST(cpc.fecha_ultimo_riego  AS DATE)
    WHERE cpc.campana_id = @campana_id
      AND CAST(f.fecha_registro AS DATE) BETWEEN @fecha_desde AND @fecha_hasta
      AND (@pad_id     IS NULL OR 1             = @pad_id)
      AND (@parcela_id IS NULL OR p.id_parcela  = @parcela_id);

    /* Sulfuro */
    INSERT INTO #flujos
    SELECT
        CAST(f.fecha_registro AS DATE),
        2,
        p.id_parcela,
        p.numero,
        cpc.campana_id,
        f.caudal,
        'riego'
    FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot f
    INNER JOIN inventar_SpcHidr.parcela p
            ON p.numero = f.parcela_numero
           AND p.id_pad = 2
    INNER JOIN inventar_SpcHidr.campana_parcela_control cpc
            ON cpc.pad_id     = 2
           AND cpc.parcela_id = p.id_parcela
           AND CAST(f.fecha_registro AS DATE)
               BETWEEN CAST(cpc.fecha_primer_riego AS DATE)
                   AND CAST(cpc.fecha_ultimo_riego  AS DATE)
    WHERE cpc.campana_id = @campana_id
      AND CAST(f.fecha_registro AS DATE) BETWEEN @fecha_desde AND @fecha_hasta
      AND (@pad_id     IS NULL OR 2             = @pad_id)
      AND (@parcela_id IS NULL OR p.id_parcela  = @parcela_id);

    /* -----------------------------------------------------------------------
       2. CONCENTRACIÓN DRENAJE (Cu g/L)
    ----------------------------------------------------------------------- */
    CREATE TABLE #drena (
        fecha_registro  DATE,
        pad_id          INT,
        parcela_id      INT,
        parcela_numero  INT,
        campana_id      INT,
        cu_pp           FLOAT
    );

    /* Oxido */
    INSERT INTO #drena
    SELECT
        CAST(d.fecha_registro AS DATE),
        1,
        p.id_parcela,
        p.numero,
        cpc.campana_id,
        d.cu_pp
    FROM inventar_SpcHidr.v_drena_oxido_unpivot d
    INNER JOIN inventar_SpcHidr.parcela p
            ON p.numero = d.parcela_numero
           AND p.id_pad = 1
    INNER JOIN inventar_SpcHidr.campana_parcela_control cpc
            ON cpc.pad_id     = 1
           AND cpc.parcela_id = p.id_parcela
           AND CAST(d.fecha_registro AS DATE)
               BETWEEN CAST(cpc.fecha_primer_riego AS DATE)
                   AND CAST(cpc.fecha_ultimo_riego  AS DATE)
    WHERE cpc.campana_id = @campana_id
      AND CAST(d.fecha_registro AS DATE) BETWEEN @fecha_desde AND @fecha_hasta
      AND (@pad_id     IS NULL OR 1             = @pad_id)
      AND (@parcela_id IS NULL OR p.id_parcela  = @parcela_id);

    /* Sulfuro */
    INSERT INTO #drena
    SELECT
        CAST(d.fecha_registro AS DATE),
        2,
        p.id_parcela,
        p.numero,
        cpc.campana_id,
        d.cu_pp
    FROM inventar_SpcHidr.v_drena_sulfuro_unpivot d
    INNER JOIN inventar_SpcHidr.parcela p
            ON p.numero = d.parcela_numero
           AND p.id_pad = 2
    INNER JOIN inventar_SpcHidr.campana_parcela_control cpc
            ON cpc.pad_id     = 2
           AND cpc.parcela_id = p.id_parcela
           AND CAST(d.fecha_registro AS DATE)
               BETWEEN CAST(cpc.fecha_primer_riego AS DATE)
                   AND CAST(cpc.fecha_ultimo_riego  AS DATE)
    WHERE cpc.campana_id = @campana_id
      AND CAST(d.fecha_registro AS DATE) BETWEEN @fecha_desde AND @fecha_hasta
      AND (@pad_id     IS NULL OR 2             = @pad_id)
      AND (@parcela_id IS NULL OR p.id_parcela  = @parcela_id);

    /* -----------------------------------------------------------------------
       3. Resultado final con agrupación por día / semana / mes
          y join entre flujos + drenaje por fecha + pad + parcela
    ----------------------------------------------------------------------- */
    SELECT
        /* Período */
        CASE @agrupar_por
            WHEN 'mes'    THEN CAST(DATEFROMPARTS(YEAR(f.fecha_registro), MONTH(f.fecha_registro), 1) AS DATE)
            WHEN 'semana' THEN CAST(DATEADD(day, -(DATEPART(weekday, f.fecha_registro)-2+7)%7, f.fecha_registro) AS DATE)
            ELSE               f.fecha_registro
        END                                                 AS fecha,

        CASE @agrupar_por
            WHEN 'mes'    THEN LEFT(DATENAME(month, f.fecha_registro), 3)
                               + '-' + CAST(YEAR(f.fecha_registro) AS VARCHAR(4))
            WHEN 'semana' THEN 'S' + RIGHT('0' + CAST(DATEPART(iso_week, f.fecha_registro) AS VARCHAR(2)), 2)
                               + '-' + CAST(YEAR(f.fecha_registro) AS VARCHAR(4))
            ELSE               CONVERT(VARCHAR(10), f.fecha_registro, 103)
        END                                                 AS periodo_label,

        f.pad_id,
        CASE f.pad_id WHEN 1 THEN 'Oxido' ELSE 'Sulfuro' END AS pad_nombre,
        f.parcela_id,
        f.parcela_numero,
        f.campana_id,

        /* Flujo riego */
        ROUND(SUM(f.caudal), 2)                             AS caudal_riego_total,
        ROUND(AVG(f.caudal), 2)                             AS caudal_riego_prom,
        COUNT(f.caudal)                                     AS n_registros_riego,

        /* Concentración drenaje Cu (g/L) */
        ROUND(AVG(d.cu_pp), 4)                              AS cu_drenaje_prom_gl,
        ROUND(MAX(d.cu_pp), 4)                              AS cu_drenaje_max_gl,
        ROUND(MIN(d.cu_pp), 4)                              AS cu_drenaje_min_gl,

        /* Contexto campaña/parcela desde campana_parcela_control */
        MAX(cpc.tms_cargado)                                AS tms_cargado,
        MAX(cpc.cut_tm_total)                               AS cut_tm_total,
        MAX(cpc.nombre_parcela)                             AS nombre_parcela,
        MAX(cpc.estado_ciclo)                               AS estado_ciclo

    FROM #flujos f
    LEFT JOIN #drena d
           ON d.fecha_registro = f.fecha_registro
          AND d.pad_id         = f.pad_id
          AND d.parcela_id     = f.parcela_id
    LEFT JOIN inventar_SpcHidr.campana_parcela_control cpc
           ON cpc.campana_id  = f.campana_id
          AND cpc.pad_id      = f.pad_id
          AND cpc.parcela_id  = f.parcela_id

    GROUP BY
        CASE @agrupar_por
            WHEN 'mes'    THEN CAST(DATEFROMPARTS(YEAR(f.fecha_registro), MONTH(f.fecha_registro), 1) AS DATE)
            WHEN 'semana' THEN CAST(DATEADD(day, -(DATEPART(weekday, f.fecha_registro)-2+7)%7, f.fecha_registro) AS DATE)
            ELSE               f.fecha_registro
        END,
        CASE @agrupar_por
            WHEN 'mes'    THEN LEFT(DATENAME(month, f.fecha_registro), 3) + '-' + CAST(YEAR(f.fecha_registro) AS VARCHAR(4))
            WHEN 'semana' THEN 'S' + RIGHT('0' + CAST(DATEPART(iso_week, f.fecha_registro) AS VARCHAR(2)), 2) + '-' + CAST(YEAR(f.fecha_registro) AS VARCHAR(4))
            ELSE               CONVERT(VARCHAR(10), f.fecha_registro, 103)
        END,
        f.pad_id,
        f.parcela_id,
        f.parcela_numero,
        f.campana_id

    ORDER BY fecha, f.pad_id, f.parcela_numero;

    DROP TABLE #flujos;
    DROP TABLE #drena;

END;
