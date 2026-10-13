CREATE PROCEDURE inventar_SpcHidr.sp_flujo_riego_drenaje
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

    /*==========================================================
      0. RANGO GENERAL
    ==========================================================*/

    IF @fecha_desde IS NULL
    BEGIN
        SELECT @fecha_desde =
            MIN(fecha_ini)
        FROM
        (
            SELECT MIN(CAST(fecha_primer_riego AS date)) AS fecha_ini
            FROM inventar_SpcHidr.campana_parcela_control
            WHERE campana_id = @campana_id
              AND (@pad_id IS NULL OR pad_id = @pad_id)

            UNION ALL

            SELECT MIN(CAST(fecha_ini_drenaje AS date))
            FROM inventar_SpcHidr.campana_parcela_control
            WHERE campana_id = @campana_id
              AND (@pad_id IS NULL OR pad_id = @pad_id)
        ) x;
    END;

    IF @fecha_hasta IS NULL
    BEGIN
        SELECT @fecha_hasta =
            MAX(fecha_fin)
        FROM
        (
            SELECT MAX(CAST(fecha_ultimo_riego AS date)) AS fecha_fin
            FROM inventar_SpcHidr.campana_parcela_control
            WHERE campana_id = @campana_id
              AND (@pad_id IS NULL OR pad_id = @pad_id)

            UNION ALL

            SELECT MAX(CAST(fecha_fin_drenaje AS date))
            FROM inventar_SpcHidr.campana_parcela_control
            WHERE campana_id = @campana_id
              AND (@pad_id IS NULL OR pad_id = @pad_id)
        ) x;
    END;

    IF @fecha_hasta IS NULL
        SET @fecha_hasta = CAST(GETDATE() AS date);


    /*==========================================================
      1. RIEGO
      UNA FILA FUENTE = UNA FILA EN #FLUJOS
    ==========================================================*/

    CREATE TABLE #flujos
    (
        fecha_registro  DATE,
        pad_id          INT,
        parcela_id      INT,
        parcela_numero  INT,
        campana_id      INT,
        caudal          FLOAT
    );


    /* OXIDO */
    INSERT INTO #flujos
    SELECT
        CAST(f.fecha_registro AS date),
        1,
        p.id_parcela,
        p.numero,
        @campana_id,
        f.caudal

    FROM inventar_SpcHidr.v_flujos_oxido_unpivot f

    INNER JOIN inventar_SpcHidr.parcela p
        ON p.numero = f.parcela_numero
       AND p.id_pad = 1

    WHERE (@pad_id IS NULL OR @pad_id = 1)
      AND (@parcela_id IS NULL OR p.id_parcela = @parcela_id)

      AND CAST(f.fecha_registro AS date)
            BETWEEN @fecha_desde AND @fecha_hasta

      AND EXISTS
      (
          SELECT 1

          FROM inventar_SpcHidr.campana_parcela_control cpc

          WHERE cpc.pad_id     = 1
            AND cpc.campana_id = @campana_id
            AND cpc.parcela_id = p.id_parcela

            AND cpc.fecha_primer_riego IS NOT NULL
            AND cpc.fecha_ultimo_riego IS NOT NULL

            AND CAST(f.fecha_registro AS date)
                BETWEEN CAST(cpc.fecha_primer_riego AS date)
                    AND CAST(cpc.fecha_ultimo_riego AS date)
      );


    /* SULFURO */
    INSERT INTO #flujos
    SELECT
        CAST(f.fecha_registro AS date),
        2,
        p.id_parcela,
        p.numero,
        @campana_id,
        f.caudal

    FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot f

    INNER JOIN inventar_SpcHidr.parcela p
        ON p.numero = f.parcela_numero
       AND p.id_pad = 2

    WHERE (@pad_id IS NULL OR @pad_id = 2)
      AND (@parcela_id IS NULL OR p.id_parcela = @parcela_id)

      AND CAST(f.fecha_registro AS date)
            BETWEEN @fecha_desde AND @fecha_hasta

      AND EXISTS
      (
          SELECT 1

          FROM inventar_SpcHidr.campana_parcela_control cpc

          WHERE cpc.pad_id     = 2
            AND cpc.campana_id = @campana_id
            AND cpc.parcela_id = p.id_parcela

            AND cpc.fecha_primer_riego IS NOT NULL
            AND cpc.fecha_ultimo_riego IS NOT NULL

            AND CAST(f.fecha_registro AS date)
                BETWEEN CAST(cpc.fecha_primer_riego AS date)
                    AND CAST(cpc.fecha_ultimo_riego AS date)
      );


    /*==========================================================
      2. DRENAJE
      USA SU PROPIA VENTANA CPC
    ==========================================================*/

    CREATE TABLE #drena
    (
        fecha_registro  DATE,
        pad_id          INT,
        parcela_id      INT,
        parcela_numero  INT,
        campana_id      INT,
        cu_pp           FLOAT
    );


    /* OXIDO */
    INSERT INTO #drena
    SELECT
        d.fecha_operacional,
        1,
        p.id_parcela,
        p.numero,
        @campana_id,
        d.cu_pp

    FROM inventar_SpcHidr.v_drena_oxido_operacional d

    INNER JOIN inventar_SpcHidr.parcela p
        ON p.numero = d.parcela_numero
       AND p.id_pad = 1

    WHERE (@pad_id IS NULL OR @pad_id = 1)
      AND (@parcela_id IS NULL OR p.id_parcela = @parcela_id)

      AND d.fecha_operacional
            BETWEEN @fecha_desde AND @fecha_hasta

      AND EXISTS
      (
          SELECT 1

          FROM inventar_SpcHidr.campana_parcela_control cpc

          WHERE cpc.pad_id     = 1
            AND cpc.campana_id = @campana_id
            AND cpc.parcela_id = p.id_parcela

            AND cpc.fecha_ini_drenaje IS NOT NULL
            AND cpc.fecha_fin_drenaje IS NOT NULL

            AND d.fecha_operacional
                BETWEEN CAST(cpc.fecha_ini_drenaje AS date)
                    AND CAST(cpc.fecha_fin_drenaje AS date)
      );


    /* SULFURO */
    INSERT INTO #drena
    SELECT
        d.fecha_operacional,
        2,
        p.id_parcela,
        p.numero,
        @campana_id,
        d.cu_pp

    FROM inventar_SpcHidr.v_drena_sulfuro_operacional d

    INNER JOIN inventar_SpcHidr.parcela p
        ON p.numero = d.parcela_numero
       AND p.id_pad = 2

    WHERE (@pad_id IS NULL OR @pad_id = 2)
      AND (@parcela_id IS NULL OR p.id_parcela = @parcela_id)

      AND d.fecha_operacional
            BETWEEN @fecha_desde AND @fecha_hasta

      AND EXISTS
      (
          SELECT 1

          FROM inventar_SpcHidr.campana_parcela_control cpc

          WHERE cpc.pad_id     = 2
            AND cpc.campana_id = @campana_id
            AND cpc.parcela_id = p.id_parcela

            AND cpc.fecha_ini_drenaje IS NOT NULL
            AND cpc.fecha_fin_drenaje IS NOT NULL

            AND d.fecha_operacional
                BETWEEN CAST(cpc.fecha_ini_drenaje AS date)
                    AND CAST(cpc.fecha_fin_drenaje AS date)
      );


    /*==========================================================
      3. CONTEXTO CPC
      UNA FILA POR CAMPANA + PAD + PARCELA

      IMPORTANTE:
      Por ahora NO redefino TMS ni leyes.
      Mantengo MAX para aislar exclusivamente el bug hidráulico.
    ==========================================================*/

    ;WITH contexto AS
    (
        SELECT
            campana_id,
            pad_id,
            parcela_id,

            MAX(tms_cargado)
                AS tms_cargado,

            MAX(cut_tm_total)
                AS cut_tm_total,

            MAX(nombre_parcela)
                AS nombre_parcela,

            MAX(estado_ciclo)
                AS estado_ciclo

        FROM inventar_SpcHidr.campana_parcela_control

        WHERE campana_id = @campana_id
          AND (@pad_id IS NULL OR pad_id = @pad_id)
          AND (@parcela_id IS NULL OR parcela_id = @parcela_id)

        GROUP BY
            campana_id,
            pad_id,
            parcela_id
    )

    SELECT
        CASE @agrupar_por
            WHEN 'mes'
                THEN CAST(
                    DATEFROMPARTS(
                        YEAR(f.fecha_registro),
                        MONTH(f.fecha_registro),
                        1
                    ) AS date
                )

            WHEN 'semana'
                THEN CAST(
                    DATEADD(
                        day,
                        -(DATEPART(weekday,f.fecha_registro)-2+7)%7,
                        f.fecha_registro
                    ) AS date
                )

            ELSE f.fecha_registro
        END AS fecha,

        CASE @agrupar_por
            WHEN 'mes'
                THEN LEFT(DATENAME(month,f.fecha_registro),3)
                     + '-'
                     + CAST(YEAR(f.fecha_registro) AS varchar(4))

            WHEN 'semana'
                THEN 'S'
                     + RIGHT(
                         '0'
                         + CAST(
                             DATEPART(iso_week,f.fecha_registro)
                             AS varchar(2)
                         ),
                         2
                       )
                     + '-'
                     + CAST(YEAR(f.fecha_registro) AS varchar(4))

            ELSE CONVERT(varchar(10),f.fecha_registro,103)
        END AS periodo_label,

        f.pad_id,

        CASE
            WHEN f.pad_id = 1 THEN 'Oxido'
            ELSE 'Sulfuro'
        END AS pad_nombre,

        f.parcela_id,
        f.parcela_numero,
        f.campana_id,

        ROUND(SUM(f.caudal),2)
            AS caudal_riego_total,

        ROUND(AVG(f.caudal),2)
            AS caudal_riego_prom,

        COUNT(f.caudal)
            AS n_registros_riego,

        ROUND(AVG(d.cu_pp),4)
            AS cu_drenaje_prom_gl,

        ROUND(MAX(d.cu_pp),4)
            AS cu_drenaje_max_gl,

        ROUND(MIN(d.cu_pp),4)
            AS cu_drenaje_min_gl,

        MAX(ctx.tms_cargado)
            AS tms_cargado,

        MAX(ctx.cut_tm_total)
            AS cut_tm_total,

        MAX(ctx.nombre_parcela)
            AS nombre_parcela,

        MAX(ctx.estado_ciclo)
            AS estado_ciclo

    FROM #flujos f

    LEFT JOIN #drena d
        ON  d.fecha_registro = f.fecha_registro
        AND d.pad_id         = f.pad_id
        AND d.parcela_id     = f.parcela_id
        AND d.campana_id     = f.campana_id

    LEFT JOIN contexto ctx
        ON  ctx.campana_id = f.campana_id
        AND ctx.pad_id     = f.pad_id
        AND ctx.parcela_id = f.parcela_id

    GROUP BY
        CASE @agrupar_por
            WHEN 'mes'
                THEN CAST(
                    DATEFROMPARTS(
                        YEAR(f.fecha_registro),
                        MONTH(f.fecha_registro),
                        1
                    ) AS date
                )
            WHEN 'semana'
                THEN CAST(
                    DATEADD(
                        day,
                        -(DATEPART(weekday,f.fecha_registro)-2+7)%7,
                        f.fecha_registro
                    ) AS date
                )
            ELSE f.fecha_registro
        END,

        CASE @agrupar_por
            WHEN 'mes'
                THEN LEFT(DATENAME(month,f.fecha_registro),3)
                     + '-'
                     + CAST(YEAR(f.fecha_registro) AS varchar(4))
            WHEN 'semana'
                THEN 'S'
                     + RIGHT(
                         '0'
                         + CAST(
                             DATEPART(iso_week,f.fecha_registro)
                             AS varchar(2)
                         ),
                         2
                       )
                     + '-'
                     + CAST(YEAR(f.fecha_registro) AS varchar(4))
            ELSE CONVERT(varchar(10),f.fecha_registro,103)
        END,

        f.pad_id,
        f.parcela_id,
        f.parcela_numero,
        f.campana_id

    ORDER BY
        fecha,
        f.pad_id,
        f.parcela_numero;

END;
