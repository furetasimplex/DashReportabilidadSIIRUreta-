-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  02_sp_compilar_parcela_campana_base.sql  — v8 (datos reales verificados)
  Esquema : inventar_SpcHidr

  CLAVES VERIFICADAS con datos reales de modulos_turnos.xlsx:
    modulos_turnos.campaña_id    = ID interno  (1,2,3…11) — MISMO que recuperaciones_pad
    modulos_turnos.Campana       = número visible (7,8,9…18) → va a numero_campana
    modulos_turnos.pad_id        = mismo que recuperaciones_pad
    modulos_turnos.parcela_id    = mismo que recuperaciones_pad

  JOIN: pad_id + parcela_id + campaña_id  (directo, mismo sistema en ambas tablas)

  Correcciones acumuladas:
    • Sin BEGIN/COMMIT TRANSACTION explícito  (error 266 FreeTDS)
    • Sin area_m2 ni modulo en INSERT        (error 207)
    • Sin subconsultas en PRINT              (error 1046 FreeTDS)
    • Sin dbo. en código SQL                 (esquema inventar_SpcHidr)
    • Sin BEGIN TRY para tabla campana       (IF EXISTS en su lugar)
    • XACT_ABORT OFF                         (compatible con IF EXISTS)
================================================================================
*/

CREATE   PROCEDURE inventar_SpcHidr.sp_compilar_parcela_campana_base
    @pad_id      INT         = NULL,
    @campana_id  INT         = NULL,
    @modo        VARCHAR(10) = 'incremental',
    @verbose     BIT         = 0
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT OFF;

    DECLARE @fecha_corte  DATE     = DATEADD(day, -45, GETDATE());
    DECLARE @ts_ini       DATETIME = GETDATE();
    DECLARE @filas_del    INT      = 0;
    DECLARE @filas_ins    INT      = 0;
    DECLARE @n_campanas   INT      = 0;
    DECLARE @n_comp       INT      = 0;
    DECLARE @msg          VARCHAR(500);

    IF @verbose = 1
    BEGIN
        SET @msg = CONVERT(VARCHAR(23), GETDATE(), 120)
                 + ' | INICIO sp_compilar_parcela_campana_base | modo=' + @modo;
        PRINT @msg;
    END

    /* -----------------------------------------------------------------------
       1. Campañas a procesar → #ca
          campana_id  = ID interno (1..11)  — clave de recuperaciones_pad
    ----------------------------------------------------------------------- */
    CREATE TABLE #ca (campana_id INT PRIMARY KEY);

    IF @modo = 'full'
        INSERT INTO #ca (campana_id)
        SELECT DISTINCT CAST(campaña_id AS INT)
        FROM   inventar_SpcHidr.recuperaciones_pad
        WHERE  campaña_id IS NOT NULL
          AND  (@campana_id IS NULL OR CAST(campaña_id AS INT) = @campana_id);
    ELSE
        INSERT INTO #ca (campana_id)
        SELECT DISTINCT CAST(campaña_id AS INT)
        FROM   inventar_SpcHidr.recuperaciones_pad
        WHERE  campaña_id  IS NOT NULL
          AND  Fecha_drenaje >= @fecha_corte
          AND  (@campana_id IS NULL OR CAST(campaña_id AS INT) = @campana_id);

    SELECT @n_campanas = COUNT(*) FROM #ca;

    IF @verbose = 1
    BEGIN
        SET @msg = '  Campanas a procesar: ' + CAST(@n_campanas AS VARCHAR(10));
        PRINT @msg;
    END

    /* -----------------------------------------------------------------------
       2. Compilar desde modulos_turnos → #comp
          JOIN directo por pad_id + parcela_id + campaña_id (mismo ID en ambas tablas)
          numero_campana viene de la columna Campana (número visible ej: 16, 17, 18)
    ----------------------------------------------------------------------- */
    CREATE TABLE #comp (
        pad_id              INT,
        pad_nombre          NVARCHAR(20),
        parcela_id          INT,
        campana_id          INT,
        numero_campana      INT,
        tms_total           FLOAT,
        tmh_total           FLOAT,
        cut_pond            FLOAT,
        cus_pond            FLOAT,
        cuins_pond          FLOAT,
        co3_pond            FLOAT,
        cl_pond             FLOAT,
        fet_pond            FLOAT,
        fes_pond            FLOAT,
        tasa_ox_pond        FLOAT,
        m100_pond           FLOAT,
        m325_pond           FLOAT,
        bajo325_pond        FLOAT,
        rec_global_pond     FLOAT,
        transicional_pond   FLOAT,
        supergeno_pond      FLOAT,
        oxido_pond          FLOAT,
        betaclay_pond       FLOAT,
        cuoxi_pond          FLOAT,
        cuins2_pond         FLOAT,
        srr_cut_pond        FLOAT,
        srr_cus_pond        FLOAT,
        srr_m100_pond       FLOAT,
        srr_co3_pond        FLOAT,
        srr_rec_pond        FLOAT,
        altura_real         FLOAT,
        n_turnos            INT,
        n_modulos           INT
    );

    INSERT INTO #comp
    SELECT
        mt.pad_id,
        MAX(mt.PAD)                                         AS pad_nombre,
        mt.parcela_id,
        mt.campaña_id                                       AS campana_id,
        MAX(mt.Campana)                                     AS numero_campana,
        /* Tonelaje */
        SUM(ISNULL(mt.TMS, 0))                              AS tms_total,
        SUM(ISNULL(mt.TMH, 0))                              AS tmh_total,
        /* Leyes ponderadas: SUM(ley * TMS) / SUM(TMS) */
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.CuT_TM,0)          *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.CuS_TM,0)          *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Cu_Insoluble,0)    *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.CO3,0)             *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Cl_Sol_Ac,0)       *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.FeT,0)             *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.FeS,0)             *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Tasa_Oxidacion,0)  *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        /* Granulometría ponderada */
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.M100,0)            *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.M325,0)            *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Bajo_Malla_325,0)  *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        /* Mineralogía ponderada */
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Recuperacion_global,0)*ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Transicional,0)    *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Supergeno,0)       *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Oxido,0)           *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.Betaclay,0)        *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.CUOXI,0)           *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.CUINS,0)           *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        /* SRR ponderado */
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.SRR_CuT,0)         *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.SRR_CuS,0)         *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.SRR_Malla_100,0)   *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.SRR_CO3,0)         *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0 THEN SUM(ISNULL(mt.SRR_Rec,0)         *ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0)) ELSE NULL END,
        /* Geometría: altura ponderada por TMS */
        CASE WHEN SUM(ISNULL(mt.TMS,0))>0
             THEN SUM(ISNULL(mt.[Altura Módulo],0)*ISNULL(mt.TMS,0))/SUM(ISNULL(mt.TMS,0))
             ELSE NULL END,
        COUNT(*)                                            AS n_turnos,
        COUNT(DISTINCT mt.Modulo)                           AS n_modulos

    FROM inventar_SpcHidr.modulos_turnos mt
    INNER JOIN #ca ON mt.campaña_id = #ca.campana_id
    WHERE mt.parcela_id IS NOT NULL
      AND mt.campaña_id IS NOT NULL
      AND mt.pad_id     IS NOT NULL
      AND (@pad_id IS NULL OR mt.pad_id = @pad_id)
    GROUP BY mt.pad_id, mt.parcela_id, mt.campaña_id;

    SELECT @n_comp = COUNT(*) FROM #comp;

    IF @verbose = 1
    BEGIN
        SET @msg = '  Filas compiladas desde modulos_turnos: ' + CAST(@n_comp AS VARCHAR(10));
        PRINT @msg;
    END

    /* -----------------------------------------------------------------------
       3. Fechas del ciclo desde recuperaciones_pad → #fec
          Clave: pad_id + parcela_id + campana_id (mismo ID interno)
    ----------------------------------------------------------------------- */
    CREATE TABLE #fec (
        pad_id      INT,
        parcela_id  INT,
        campana_id  INT,
        fecha_ini   DATE,
        fecha_fin   DATE,
        rec_max_obs FLOAT,
        n_dias      INT
    );

    INSERT INTO #fec
    SELECT
        rp.pad_id,
        rp.parcela_id,
        CAST(rp.campaña_id AS INT),
        MIN(rp.Fecha_drenaje),
        MAX(rp.Fecha_drenaje),
        MAX(rp.Recuperacion_parcela),
        COUNT(*)
    FROM inventar_SpcHidr.recuperaciones_pad rp
    INNER JOIN #ca ON CAST(rp.campaña_id AS INT) = #ca.campana_id
    WHERE rp.parcela_id IS NOT NULL
      AND (@pad_id IS NULL OR rp.pad_id = @pad_id)
    GROUP BY rp.pad_id, rp.parcela_id, CAST(rp.campaña_id AS INT);

    /* -----------------------------------------------------------------------
       4. Número de campaña visible → #nc
          Si existe inventar_SpcHidr.campana la usa; si no, toma numero_campana
          directamente de #comp (columna Campana de modulos_turnos).
    ----------------------------------------------------------------------- */
    CREATE TABLE #nc (campana_id INT, numero_campana INT);

    IF EXISTS (
        SELECT 1 FROM sys.objects
        WHERE name      = 'campana'
          AND schema_id = SCHEMA_ID('inventar_SpcHidr')
    )
    BEGIN
        INSERT INTO #nc (campana_id, numero_campana)
        SELECT id_campana, ISNULL(numero_campana, id_campana)
        FROM   inventar_SpcHidr.campana;
    END
    ELSE
    BEGIN
        -- Fallback: numero_campana viene de columna Campana de modulos_turnos
        INSERT INTO #nc (campana_id, numero_campana)
        SELECT DISTINCT campana_id, numero_campana
        FROM   #comp;
    END

    /* -----------------------------------------------------------------------
       5. DELETE + INSERT
          Join final por pad_id + parcela_id + campana_id (ID interno en ambos)
    ----------------------------------------------------------------------- */
    DELETE dest
    FROM   inventar_SpcHidr.parcela_campana_base dest
    INNER JOIN #ca ON dest.campana_id = #ca.campana_id
    WHERE (@pad_id IS NULL OR dest.pad_id = @pad_id);

    SET @filas_del = @@ROWCOUNT;

    INSERT INTO inventar_SpcHidr.parcela_campana_base (
        pad_id, pad_nombre, parcela_id, campana_id, numero_campana,
        tms_total, tmh_total,
        cut_pond, cus_pond, cuins_pond, co3_pond, cl_pond,
        fet_pond, fes_pond, tasa_oxid_pond,
        m100_pond, m325_pond, bajo325_pond,
        rec_global_pond, transicional_pond, supergeno_pond, oxido_pond,
        betaclay_pond, cuoxi_pond, cuins2_pond,
        srr_cut_pond, srr_cus_pond, srr_m100_pond, srr_co3_pond, srr_rec_pond,
        altura_real,
        fecha_inicio_riego, fecha_ultimo_dato, rec_max_obs,
        estado_ciclo, n_turnos_fuente, n_modulos, fecha_compilacion
    )
    SELECT
        COALESCE(c.pad_id,     f.pad_id),
        ISNULL(c.pad_nombre,   'DESCONOCIDO'),
        COALESCE(c.parcela_id, f.parcela_id),
        COALESCE(c.campana_id, f.campana_id),
        ISNULL(nc.numero_campana, c.numero_campana),
        c.tms_total,
        c.tmh_total,
        c.cut_pond,
        c.cus_pond,
        c.cuins_pond,
        c.co3_pond,
        c.cl_pond,
        c.fet_pond,
        c.fes_pond,
        c.tasa_ox_pond,
        c.m100_pond,
        c.m325_pond,
        c.bajo325_pond,
        c.rec_global_pond,
        c.transicional_pond,
        c.supergeno_pond,
        c.oxido_pond,
        c.betaclay_pond,
        c.cuoxi_pond,
        c.cuins2_pond,
        c.srr_cut_pond,
        c.srr_cus_pond,
        c.srr_m100_pond,
        c.srr_co3_pond,
        c.srr_rec_pond,
        c.altura_real,
        f.fecha_ini,
        f.fecha_fin,
        f.rec_max_obs,
        CASE
            WHEN f.fecha_fin IS NULL                       THEN 'sin_datos'
            WHEN f.fecha_fin >= DATEADD(day,-5,GETDATE())  THEN 'activo'
            ELSE 'completado'
        END,
        ISNULL(c.n_turnos,  0),
        ISNULL(c.n_modulos, 0),
        GETDATE()
    FROM #comp c
    FULL JOIN #fec f
           ON c.pad_id     = f.pad_id
          AND c.parcela_id = f.parcela_id
          AND c.campana_id = f.campana_id
    LEFT JOIN #nc nc
           ON COALESCE(c.campana_id, f.campana_id) = nc.campana_id
    WHERE COALESCE(c.pad_id,     f.pad_id)     IS NOT NULL
      AND COALESCE(c.parcela_id, f.parcela_id) IS NOT NULL
      AND COALESCE(c.campana_id, f.campana_id) IS NOT NULL;

    SET @filas_ins = @@ROWCOUNT;

    /* -----------------------------------------------------------------------
       6. Limpieza
    ----------------------------------------------------------------------- */
    DROP TABLE #ca;
    DROP TABLE #comp;
    DROP TABLE #fec;
    DROP TABLE #nc;

    IF @verbose = 1
    BEGIN
        SET @msg = CONVERT(VARCHAR(23), GETDATE(), 120)
                 + ' | FIN | borradas='  + CAST(@filas_del AS VARCHAR(10))
                 + ' | insertadas='      + CAST(@filas_ins AS VARCHAR(10))
                 + ' | ms='              + CAST(DATEDIFF(ms, @ts_ini, GETDATE()) AS VARCHAR(10));
        PRINT @msg;
    END

END;
