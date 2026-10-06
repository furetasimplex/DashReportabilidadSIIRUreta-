-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  05_sp_razon_lixiviacion_v2.sql
  Esquema : inventar_SpcHidr

  DEFINICIÓN DE RAZÓN DE LIXIVIACIÓN (RL):
    RL (m³/ton) = Σ caudal_acumulado (m³) / TMS_total (ton)

  COMPORTAMIENTO POR CAMPAÑA:
    - La misma parcela_numero aparece en múltiples campañas en las vistas
    - dia_ciclo y RL se REINICIAN en 1 al inicio de cada campaña
    - @campana_id filtra exactamente una campaña
    - La fecha de inicio del ciclo viene de campana_parcela_control.fecha_primer_riego

  PROBLEMA DE MÓDULOS MÚLTIPLES:
    campana_parcela_control tiene 2+ filas por (campana_id, parcela_id)
    porque cada módulo genera una fila. Se pre-agrega con GROUP BY para
    evitar que el JOIN duplique registros de flujo.

  MODELO DE DATOS:
    parcela                  → id_parcela, id_pad, numero
    campana_parcela_control  → campana_id, pad_id, parcela_id,
                               tms_cargado, cut_tm_total, cus_tm_total,
                               altura_modulo_max, fecha_primer_riego,
                               fecha_ultimo_riego, estado_ciclo
    v_flujos_oxido_unpivot   → fecha_registro, parcela_numero, caudal (m³/h)
    v_flujos_sulfuro_unpivot → fecha_registro, parcela_numero, caudal (m³/h)
    v_drena_oxido_unpivot    → fecha_registro, parcela_numero, cu_pp (g/L)
    v_drena_sulfuro_unpivot  → fecha_registro, parcela_numero, cu_pp (g/L)
    recuperaciones_pad       → Recuperacion_parcela acumulada (%)
    parcela_campana_cinetica → Rmax, k1, k2, A

  Parámetros:
    @parcela_id      INT
    @campana_id      INT
    @pad_id          INT   = NULL  (auto desde tabla parcela)
    @proyectar_dias  INT   = 0
    @factor_caudal   FLOAT = 24.0  (m³/h × 24 = m³/día)

  Uso:
      EXEC inventar_SpcHidr.sp_razon_lixiviacion @parcela_id=1, @campana_id=1;
      EXEC inventar_SpcHidr.sp_razon_lixiviacion @parcela_id=33, @campana_id=5;
      EXEC inventar_SpcHidr.sp_razon_lixiviacion @parcela_id=1, @campana_id=2,
           @proyectar_dias=30;
================================================================================
*/

CREATE   PROCEDURE inventar_SpcHidr.sp_razon_lixiviacion
    @parcela_id     INT,
    @campana_id     INT,
    @pad_id         INT   = NULL,
    @proyectar_dias INT   = 0,
    @factor_caudal  FLOAT = 24.0
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

    /* -----------------------------------------------------------------------
       0. Resolver pad_id desde tabla parcela
    ----------------------------------------------------------------------- */
    IF @pad_id IS NULL
        SELECT TOP 1 @pad_id = id_pad
        FROM   inventar_SpcHidr.parcela
        WHERE  id_parcela = @parcela_id;

    /* -----------------------------------------------------------------------
       1. Parámetros base de la parcela para ESTA CAMPAÑA
          PRE-AGREGAR por campana_id para evitar duplicados de módulos.
          Cada parcela puede tener N módulos → SUM tms, MIN/MAX fechas.
    ----------------------------------------------------------------------- */
    DECLARE
        @tms_total      FLOAT       = 0,
        @cut_total      FLOAT       = 0,
        @cus_total      FLOAT       = 0,
        @altura_max     FLOAT       = 0,
        @parcela_numero INT         = 0,
        @numero_campana INT         = 0,
        @estado_ciclo   VARCHAR(20) = '',
        @fecha_ini      DATE        = NULL,
        @fecha_fin      DATE        = NULL,
        @dias_max_real  INT         = 0;

    SELECT
        @tms_total      = SUM(cpc.tms_cargado),
        @cut_total      = SUM(cpc.cut_tm_total),
        @cus_total      = SUM(cpc.cus_tm_total),
        @altura_max     = MAX(cpc.altura_modulo_max),
        @numero_campana = MAX(cpc.numero_campana),
        @estado_ciclo   = MAX(cpc.estado_ciclo),
        /* Inicio del ciclo = primer riego de la campaña en esta parcela */
        @fecha_ini      = CAST(MIN(cpc.fecha_primer_riego) AS DATE),
        /* Fin = último riego o hoy si sigue activa */
        @fecha_fin      = CAST(MAX(ISNULL(cpc.fecha_ultimo_riego,
                                          GETDATE())) AS DATE)
    FROM inventar_SpcHidr.campana_parcela_control cpc
    WHERE cpc.campana_id = @campana_id
      AND cpc.pad_id     = @pad_id
      AND cpc.parcela_id = @parcela_id;

    /* Número visible de parcela para vincular con las vistas */
    SELECT @parcela_numero = numero
    FROM   inventar_SpcHidr.parcela
    WHERE  id_parcela = @parcela_id;

    /* -----------------------------------------------------------------------
       2. Parámetros cinéticos para esta campaña
    ----------------------------------------------------------------------- */
    DECLARE
        @Rmax FLOAT = NULL,
        @k1   FLOAT = NULL,
        @k2   FLOAT = NULL,
        @A    FLOAT = NULL;

    SELECT TOP 1
        @Rmax = ck.Rmax,
        @k1   = ck.k1,
        @k2   = ck.k2,
        @A    = ck.A
    FROM inventar_SpcHidr.parcela_campana_cinetica ck
    WHERE ck.parcela_id = @parcela_id
      AND ck.campana_id = @campana_id
      AND ck.pad_id     = @pad_id;

    /* -----------------------------------------------------------------------
       3. Serie diaria de flujos para ESTA campaña
          dia_ciclo reinicia en 1 = primer día de riego de la campaña
          El filtro BETWEEN fecha_ini AND fecha_fin asegura que solo
          se incluyen los flujos del período de esta campaña
          (no los de campañas anteriores/posteriores con el mismo número de parcela)
    ----------------------------------------------------------------------- */
    CREATE TABLE #serie (
        fecha_registro  DATE,
        dia_ciclo       INT,
        caudal_m3_dia   FLOAT,
        cu_pp           FLOAT,
        rec_acum_pct    FLOAT
    );

    IF @pad_id = 1  /* PAD OXIDO: parcela_id 1..32 */
    BEGIN
        INSERT INTO #serie (fecha_registro, dia_ciclo, caudal_m3_dia, cu_pp)
        SELECT
            CAST(f.fecha_registro AS DATE)                  AS fecha_registro,
            /* dia_ciclo reinicia en 1 para esta campaña */
            DATEDIFF(day, @fecha_ini,
                     CAST(f.fecha_registro AS DATE)) + 1    AS dia_ciclo,
            ISNULL(f.caudal, 0) * @factor_caudal            AS caudal_m3_dia,
            d.cu_pp
        FROM inventar_SpcHidr.v_flujos_oxido_unpivot f
        LEFT JOIN inventar_SpcHidr.v_drena_oxido_unpivot d
               ON CAST(d.fecha_registro AS DATE) = CAST(f.fecha_registro AS DATE)
              AND d.parcela_numero               = f.parcela_numero
        WHERE f.parcela_numero = @parcela_numero
          /* Filtro de fechas de ESTA campaña — reinicia ciclo */
          AND CAST(f.fecha_registro AS DATE) >= @fecha_ini
          AND CAST(f.fecha_registro AS DATE) <= @fecha_fin;
    END
    ELSE  /* PAD SULFURO: parcela_id 33..60, numero 1..28 */
    BEGIN
        INSERT INTO #serie (fecha_registro, dia_ciclo, caudal_m3_dia, cu_pp)
        SELECT
            CAST(f.fecha_registro AS DATE),
            DATEDIFF(day, @fecha_ini,
                     CAST(f.fecha_registro AS DATE)) + 1,
            ISNULL(f.caudal, 0) * @factor_caudal,
            d.cu_pp
        FROM inventar_SpcHidr.v_flujos_sulfuro_unpivot f
        LEFT JOIN inventar_SpcHidr.v_drena_sulfuro_unpivot d
               ON CAST(d.fecha_registro AS DATE) = CAST(f.fecha_registro AS DATE)
              AND d.parcela_numero               = f.parcela_numero
        WHERE f.parcela_numero = @parcela_numero
          AND CAST(f.fecha_registro AS DATE) >= @fecha_ini
          AND CAST(f.fecha_registro AS DATE) <= @fecha_fin;
    END

    /* Recuperación acumulada para ESTA campaña desde recuperaciones_pad */
    UPDATE s
    SET    s.rec_acum_pct = rp.Recuperacion_parcela
    FROM   #serie s
    INNER JOIN inventar_SpcHidr.recuperaciones_pad rp
            ON CAST(rp.Fecha_drenaje AS DATE) = s.fecha_registro
           AND rp.parcela_id                  = @parcela_id
           AND CAST(rp.campaña_id AS INT)     = @campana_id;

    SELECT @dias_max_real = ISNULL(MAX(dia_ciclo), 0) FROM #serie;

    /* -----------------------------------------------------------------------
       4. Resultado histórico con RL y acumulados
          RL = Σ caudal_m3 / TMS_total  (reinicia por campaña)
    ----------------------------------------------------------------------- */
    SELECT
        s.dia_ciclo,
        s.fecha_registro,
        'real'                                              AS tipo,
        @campana_id                                         AS campana_id,
        @numero_campana                                     AS numero_campana,
        @pad_id                                             AS pad_id,
        @parcela_id                                         AS parcela_id,
        @parcela_numero                                     AS parcela_numero,

        /* Flujo diario (m³/día) */
        ROUND(s.caudal_m3_dia, 2)                          AS caudal_m3_dia,

        /* RL DIARIA = caudal_dia / TMS_total */
        ROUND(
            s.caudal_m3_dia / NULLIF(@tms_total, 0),
        6)                                                  AS rl_diaria,

        /* RL ACUMULADA = Σcaudal / TMS_total (reinicia en dia_ciclo=1) */
        ROUND(
            SUM(s.caudal_m3_dia)
                OVER (ORDER BY s.dia_ciclo
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
            / NULLIF(@tms_total, 0),
        4)                                                  AS rl_acum,

        /* Volumen acumulado bruto (m³) */
        ROUND(
            SUM(s.caudal_m3_dia)
                OVER (ORDER BY s.dia_ciclo
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
        2)                                                  AS volumen_acum_m3,

        /* Concentración Cu drenaje (g/L) */
        ROUND(s.cu_pp, 4)                                  AS cu_drenaje_gl,

        /* Cu extraído (ton/día) = caudal_m3 × cu_pp(g/L) / 1000 */
        ROUND(
            s.caudal_m3_dia * ISNULL(s.cu_pp, 0) / 1000.0,
        4)                                                  AS cu_diario_ton,

        /* Cu acumulado (ton) — reinicia por campaña */
        ROUND(
            SUM(s.caudal_m3_dia * ISNULL(s.cu_pp, 0) / 1000.0)
                OVER (ORDER BY s.dia_ciclo
                      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW),
        4)                                                  AS cu_acum_ton,

        /* Recuperación real (%) de recuperaciones_pad */
        ROUND(s.rec_acum_pct, 2)                           AS rec_acum_pct,

        /* Recuperación modelo cinético (%) */
        CASE WHEN @Rmax IS NOT NULL THEN
            ROUND(
                @Rmax * (
                      @A       * (1 - EXP(-@k1 * s.dia_ciclo))
                    + (1 - @A) * (1 - EXP(-@k2 * s.dia_ciclo))
                ), 2)
        ELSE NULL END                                       AS rec_modelo_pct,

        /* Metadatos */
        @tms_total                                          AS tms_total,
        @cut_total                                          AS cut_tm_total,
        @cus_total                                          AS cus_tm_total,
        @altura_max                                         AS altura_modulo_max,
        @estado_ciclo                                       AS estado_ciclo,
        @Rmax                                               AS Rmax,
        @k1                                                 AS k1,
        @k2                                                 AS k2,
        @A                                                  AS A_fraccion_rapida

    FROM #serie s
    WHERE s.dia_ciclo >= 1

    UNION ALL

    /* -----------------------------------------------------------------------
       5. Proyección cinética (días futuros si @proyectar_dias > 0)
          RL proyectada usa caudal promedio histórico de ESTA campaña
    ----------------------------------------------------------------------- */
    SELECT
        @dias_max_real + ROW_NUMBER() OVER (ORDER BY (SELECT NULL)),
        CAST(NULL AS DATE),
        'proyectado',
        @campana_id, @numero_campana, @pad_id,
        @parcela_id, @parcela_numero,
        hist.caudal_prom,
        ROUND(hist.caudal_prom / NULLIF(@tms_total, 0), 6),
        ROUND(
            (hist.vol_acum
             + hist.caudal_prom * ROW_NUMBER() OVER (ORDER BY (SELECT NULL)))
            / NULLIF(@tms_total, 0),
        4),
        ROUND(
            hist.vol_acum
            + hist.caudal_prom * ROW_NUMBER() OVER (ORDER BY (SELECT NULL)),
        2),
        CAST(NULL AS FLOAT),
        CAST(NULL AS FLOAT),
        CAST(NULL AS FLOAT),
        CAST(NULL AS FLOAT),
        CASE WHEN @Rmax IS NOT NULL THEN
            ROUND(
                @Rmax * (
                      @A       * (1 - EXP(-@k1 * (@dias_max_real + ROW_NUMBER() OVER (ORDER BY (SELECT NULL)))))
                    + (1 - @A) * (1 - EXP(-@k2 * (@dias_max_real + ROW_NUMBER() OVER (ORDER BY (SELECT NULL)))))
                ), 2)
        ELSE NULL END,
        @tms_total, @cut_total, @cus_total, @altura_max,
        @estado_ciclo, @Rmax, @k1, @k2, @A
    FROM (
        SELECT TOP (@proyectar_dias) 1 AS n FROM sys.all_columns
    ) p
    CROSS JOIN (
        SELECT
            AVG(caudal_m3_dia) AS caudal_prom,
            SUM(caudal_m3_dia) AS vol_acum
        FROM #serie
        WHERE dia_ciclo >= 1
    ) hist
    WHERE @proyectar_dias > 0
      AND @Rmax IS NOT NULL

    ORDER BY dia_ciclo;

    DROP TABLE #serie;

END;
