-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
/*
================================================================================
  04_sp_resumen_campana.sql
  Esquema : inventar_SpcHidr

  MODELO DE DATOS REAL VERIFICADO:
  ─────────────────────────────────
  campana_parcela_control:
    campana_id, pad_id, parcela_id, modulo_id, numero_campana,
    nombre_pad, nombre_parcela, nombre_modulo,
    tms_cargado, tmh_cargado, cut_tm_total (%), cus_tm_total (%),
    cu_insoluble_total (%), humedad_promedio, sal_promedio,
    altura_modulo_max,
    fecha_ini_carguio, fecha_fin_carguio,
    fecha_ini_reposo,  fecha_fin_reposo,
    fecha_ini_operacion, fecha_fin_operacion,
    fecha_ini_drenaje,   fecha_fin_drenaje,
    fecha_primer_riego,  fecha_ultimo_riego,
    dias_carguio, dias_reposo, dias_operacion, dias_drenaje,
    estado_ciclo  ('drenaje','DRENAJE','reclamo','reposo','operacion','sin_dato')

  recuperaciones_pad:
    pad_id, parcela_id, campaña_id (= campana_id),
    Fecha_drenaje, Recuperacion_parcela (%)

  parcela_campana_cinetica (opcional):
    pad_id, parcela_id, campana_id, Rmax, k1, k2, A, r2

  NOTAS:
    • estado_ciclo tiene mayúsculas mixtas → normalizar con LOWER()
    • cut_tm_total en % directo (ej: 0.81 = 0.81%)
    • Cu apilado (ton) = tms_cargado × cut_tm_total / 100
    • Cu recuperado (ton) = Cu_apilado × rec_max_obs / 100
    • rec_max_obs = MAX(Recuperacion_parcela) de recuperaciones_pad

  Retorna una fila de KPIs por campaña (y pad opcional).

  Uso:
      EXEC inventar_SpcHidr.sp_resumen_campana @campana_id = 1;
      EXEC inventar_SpcHidr.sp_resumen_campana @campana_id = 1, @pad_id = 1;
      EXEC inventar_SpcHidr.sp_resumen_campana @campana_id = 5, @pad_id = 2;
================================================================================
*/

CREATE   PROCEDURE inventar_SpcHidr.sp_resumen_campana
    @campana_id  INT,
    @pad_id      INT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;

    /* -----------------------------------------------------------------------
       1. Base: una fila por parcela (agregando módulos con SUM/MAX/MIN)
          Se agrupan los módulos de la misma parcela en la misma campaña.
    ----------------------------------------------------------------------- */
    CREATE TABLE #base (
        campana_id      INT,
        numero_campana  INT,
        pad_id          INT,
        nombre_pad      VARCHAR(20),
        parcela_id      INT,
        nombre_parcela  INT,
        /* Tonelaje total de todos los módulos de la parcela */
        tms_total       FLOAT,
        tmh_total       FLOAT,
        /* Ley CuT ponderada por TMS: Σ(cut × tms) / Σtms */
        cut_pond        FLOAT,
        cus_pond        FLOAT,
        cuins_pond      FLOAT,
        /* Cu metálico apilado (ton) = tms × cut/100 */
        cu_apilado      FLOAT,
        /* Días de operación (promedio de módulos) */
        dias_operacion  FLOAT,
        dias_drenaje    FLOAT,
        dias_carguio    FLOAT,
        dias_reposo     FLOAT,
        /* Fechas del ciclo */
        fecha_ini_riego DATE,
        fecha_fin_riego DATE,
        /* Estado normalizado */
        estado_ciclo    VARCHAR(20)
    );

    INSERT INTO #base
    SELECT
        cpc.campana_id,
        MAX(cpc.numero_campana)                             AS numero_campana,
        cpc.pad_id,
        MAX(cpc.nombre_pad)                                 AS nombre_pad,
        cpc.parcela_id,
        MAX(cpc.nombre_parcela)                             AS nombre_parcela,
        /* Tonelaje: suma de todos los módulos */
        SUM(ISNULL(cpc.tms_cargado, 0))                    AS tms_total,
        SUM(ISNULL(cpc.tmh_cargado, 0))                    AS tmh_total,
        /* CuT ponderado por TMS */
        CASE WHEN SUM(ISNULL(cpc.tms_cargado,0)) > 0
             THEN SUM(ISNULL(cpc.cut_tm_total,0) * ISNULL(cpc.tms_cargado,0))
                  / SUM(ISNULL(cpc.tms_cargado,0))
             ELSE NULL END                                  AS cut_pond,
        CASE WHEN SUM(ISNULL(cpc.tms_cargado,0)) > 0
             THEN SUM(ISNULL(cpc.cus_tm_total,0) * ISNULL(cpc.tms_cargado,0))
                  / SUM(ISNULL(cpc.tms_cargado,0))
             ELSE NULL END                                  AS cus_pond,
        CASE WHEN SUM(ISNULL(cpc.tms_cargado,0)) > 0
             THEN SUM(ISNULL(cpc.cu_insoluble_total,0) * ISNULL(cpc.tms_cargado,0))
                  / SUM(ISNULL(cpc.tms_cargado,0))
             ELSE NULL END                                  AS cuins_pond,
        /* Cu apilado (ton) */
        SUM(ISNULL(cpc.tms_cargado,0) * ISNULL(cpc.cut_tm_total,0) / 100.0)
                                                            AS cu_apilado,
        /* Días (promedio entre módulos) */
        AVG(ISNULL(cpc.dias_operacion, 0))                 AS dias_operacion,
        AVG(ISNULL(cpc.dias_drenaje,   0))                 AS dias_drenaje,
        AVG(ISNULL(cpc.dias_carguio,   0))                 AS dias_carguio,
        AVG(ISNULL(cpc.dias_reposo,    0))                 AS dias_reposo,
        /* Fechas del ciclo */
        CAST(MIN(cpc.fecha_primer_riego) AS DATE)          AS fecha_ini_riego,
        CAST(MAX(cpc.fecha_ultimo_riego)  AS DATE)         AS fecha_fin_riego,
        /* Estado normalizado (LOWER para unificar 'drenaje'/'DRENAJE') */
        LOWER(MAX(cpc.estado_ciclo))                       AS estado_ciclo
    FROM inventar_SpcHidr.campana_parcela_control cpc
    WHERE cpc.campana_id = @campana_id
      AND (@pad_id IS NULL OR cpc.pad_id = @pad_id)
    GROUP BY cpc.campana_id, cpc.pad_id, cpc.parcela_id;

    /* -----------------------------------------------------------------------
       2. Recuperación máxima observada por parcela en esta campaña
          desde recuperaciones_pad (última medición)
    ----------------------------------------------------------------------- */
    CREATE TABLE #rec (
        pad_id          INT,
        parcela_id      INT,
        campana_id      INT,
        rec_max_obs     FLOAT,
        rec_ultimo      FLOAT,
        dias_datos      INT
    );

    INSERT INTO #rec
    SELECT
        rp.pad_id,
        rp.parcela_id,
        CAST(rp.campaña_id AS INT),
        MAX(rp.Recuperacion_parcela)    AS rec_max_obs,
        /* Último valor registrado (mayor fecha) */
        MAX(CASE WHEN rp.Fecha_drenaje = mx.ultima_fecha
                 THEN rp.Recuperacion_parcela END) AS rec_ultimo,
        COUNT(*)                        AS dias_datos
    FROM inventar_SpcHidr.recuperaciones_pad rp
    INNER JOIN (
        SELECT pad_id, parcela_id, campaña_id,
               MAX(Fecha_drenaje) AS ultima_fecha
        FROM   inventar_SpcHidr.recuperaciones_pad
        WHERE  CAST(campaña_id AS INT) = @campana_id
          AND  (@pad_id IS NULL OR pad_id = @pad_id)
        GROUP BY pad_id, parcela_id, campaña_id
    ) mx ON  rp.pad_id     = mx.pad_id
         AND rp.parcela_id = mx.parcela_id
         AND rp.campaña_id = mx.campaña_id
    WHERE CAST(rp.campaña_id AS INT) = @campana_id
      AND (@pad_id IS NULL OR rp.pad_id = @pad_id)
    GROUP BY rp.pad_id, rp.parcela_id, CAST(rp.campaña_id AS INT);

    /* -----------------------------------------------------------------------
       3. Parámetros cinéticos promedio (R² ponderado, Rmax promedio)
    ----------------------------------------------------------------------- */
    CREATE TABLE #cin (
        pad_id      INT,
        rmax_prom   FLOAT,
        r2_prom     FLOAT,
        n_ajustes   INT
    );

    INSERT INTO #cin
    SELECT
        pad_id,
        AVG(Rmax)   AS rmax_prom,
        AVG(r2)     AS r2_prom,
        COUNT(*)    AS n_ajustes
    FROM inventar_SpcHidr.parcela_campana_cinetica
    WHERE campana_id = @campana_id
      AND (@pad_id IS NULL OR pad_id = @pad_id)
    GROUP BY pad_id;

    /* -----------------------------------------------------------------------
       4. Join final: base + recuperación + cinética
    ----------------------------------------------------------------------- */
    CREATE TABLE #join (
        pad_id          INT,
        nombre_pad      VARCHAR(20),
        parcela_id      INT,
        tms_total       FLOAT,
        cut_pond        FLOAT,
        cus_pond        FLOAT,
        cuins_pond      FLOAT,
        cu_apilado      FLOAT,
        cu_recuperado   FLOAT,
        cu_wip          FLOAT,
        rec_max_obs     FLOAT,
        rec_ultimo      FLOAT,
        dias_operacion  FLOAT,
        dias_drenaje    FLOAT,
        estado_ciclo    VARCHAR(20)
    );

    INSERT INTO #join
    SELECT
        b.pad_id,
        b.nombre_pad,
        b.parcela_id,
        b.tms_total,
        b.cut_pond,
        b.cus_pond,
        b.cuins_pond,
        b.cu_apilado,
        /* Cu recuperado = Cu apilado × rec_max_obs / 100 */
        b.cu_apilado * ISNULL(r.rec_max_obs, 0) / 100.0    AS cu_recuperado,
        /* Cu WIP = apilado − recuperado */
        b.cu_apilado - b.cu_apilado * ISNULL(r.rec_max_obs, 0) / 100.0 AS cu_wip,
        ISNULL(r.rec_max_obs, 0)                            AS rec_max_obs,
        ISNULL(r.rec_ultimo,  0)                            AS rec_ultimo,
        b.dias_operacion,
        b.dias_drenaje,
        b.estado_ciclo
    FROM #base b
    LEFT JOIN #rec r
           ON r.pad_id     = b.pad_id
          AND r.parcela_id = b.parcela_id
          AND r.campana_id = b.campana_id;

    /* -----------------------------------------------------------------------
       5. Resultado final — una fila de KPIs por campaña (y pad si se filtra)
    ----------------------------------------------------------------------- */
    SELECT
        @campana_id                                         AS campana_id,
        MAX(b.numero_campana)                               AS numero_campana,
        GETDATE()                                           AS fecha_corte,
        ISNULL(MAX(b.nombre_pad), 'Todos')                 AS nombre_pad,

        /* ── Tonelaje ─────────────────────────────────────────────── */
        ROUND(SUM(j.tms_total), 0)                          AS tms_total,
        COUNT(DISTINCT j.parcela_id)                        AS total_parcelas,

        /* ── Calidad ponderada ───────────────────────────────────────*/
        ROUND(
            SUM(j.cut_pond * j.tms_total) / NULLIF(SUM(j.tms_total), 0),
        4)                                                  AS cut_pond_campana,
        ROUND(
            SUM(j.cus_pond * j.tms_total) / NULLIF(SUM(j.tms_total), 0),
        4)                                                  AS cus_pond_campana,
        ROUND(
            SUM(j.cuins_pond * j.tms_total) / NULLIF(SUM(j.tms_total), 0),
        4)                                                  AS cuins_pond_campana,

        /* ── Cobre ───────────────────────────────────────────────── */
        ROUND(SUM(j.cu_apilado),   2)                       AS cu_apilado_ton,
        ROUND(SUM(j.cu_recuperado),2)                       AS cu_recuperado_ton,
        ROUND(SUM(j.cu_wip),       2)                       AS cu_wip_ton,

        /* ── Recuperación ────────────────────────────────────────── */
        ROUND(AVG(j.rec_max_obs),  2)                       AS rec_prom_max_obs,
        ROUND(AVG(j.rec_ultimo),   2)                       AS rec_prom_ultimo,
        ROUND(MAX(j.rec_max_obs),  2)                       AS rec_max_campana,
        ROUND(MIN(CASE WHEN j.rec_max_obs > 0
                       THEN j.rec_max_obs END), 2)          AS rec_min_campana,

        /* ── Días de operación ───────────────────────────────────── */
        ROUND(AVG(j.dias_operacion), 1)                     AS dias_op_prom,
        ROUND(AVG(j.dias_drenaje),   1)                     AS dias_drenaje_prom,
        ROUND(MAX(b.dias_carguio),   1)                     AS dias_carguio_prom,
        ROUND(MAX(b.dias_reposo),    1)                     AS dias_reposo_prom,

        /* ── Fechas del ciclo ────────────────────────────────────── */
        MIN(b.fecha_ini_riego)                              AS fecha_inicio_campana,
        MAX(b.fecha_fin_riego)                              AS fecha_fin_campana,
        DATEDIFF(day, MIN(b.fecha_ini_riego),
                      MAX(ISNULL(b.fecha_fin_riego,
                                 CAST(GETDATE() AS DATE)))) AS duracion_dias_campana,

        /* ── Estado de parcelas ──────────────────────────────────── */
        SUM(CASE WHEN j.estado_ciclo IN ('drenaje','operacion')
                 THEN 1 ELSE 0 END)                         AS parcelas_activas,
        SUM(CASE WHEN j.estado_ciclo = 'reclamo'
                 THEN 1 ELSE 0 END)                         AS parcelas_reclamo,
        SUM(CASE WHEN j.estado_ciclo = 'reposo'
                 THEN 1 ELSE 0 END)                         AS parcelas_reposo,
        SUM(CASE WHEN j.estado_ciclo IN ('sin_dato','')
                  OR j.estado_ciclo IS NULL
                 THEN 1 ELSE 0 END)                         AS parcelas_sin_dato,

        /* ── Modelo cinético (si existe) ─────────────────────────── */
        ROUND(MAX(c.rmax_prom),  2)                         AS rmax_modelo_prom,
        ROUND(MAX(c.r2_prom),    4)                         AS r2_modelo_prom,
        MAX(c.n_ajustes)                                    AS n_parcelas_con_modelo

    FROM #join j
    INNER JOIN #base b
            ON b.pad_id     = j.pad_id
           AND b.parcela_id = j.parcela_id
    LEFT JOIN #cin c ON c.pad_id = j.pad_id
    ;  -- sin GROUP BY: resultado es una sola fila (toda la campaña agregada)

    DROP TABLE #base;
    DROP TABLE #rec;
    DROP TABLE #cin;
    DROP TABLE #join;

END;
