CREATE PROCEDURE [inventar_SpcHidr].[sp_calcular_balance_flujos_copy1]
(
    @fecha_inicio date,
    @fecha_fin    date
)
AS
BEGIN
    SET NOCOUNT ON;
    -------------------------------------------------------------------------
    -- 0) NORMALIZAR FECHAS
    -------------------------------------------------------------------------
    IF @fecha_inicio > @fecha_fin
    BEGIN
        DECLARE @tmp date = @fecha_inicio;
        SET @fecha_inicio = @fecha_fin;
        SET @fecha_fin = @tmp;
    END;
    DECLARE @ff_mas_1 date = DATEADD(DAY, 1, @fecha_fin);
    -- Dias del periodo a balancear (inclusive), usado por el criterio de evaporacion (seccion 8, F61/F62/F64/F71/F72/F74/F75/F77)
    DECLARE @dias_periodo int = DATEDIFF(DAY, @fecha_inicio, @fecha_fin) + 1;
    -------------------------------------------------------------------------
    -- 1) TABLA TEMPORAL DE RESULTADOS
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#flujos_resultado') IS NOT NULL
        DROP TABLE #flujos_resultado;
    CREATE TABLE #flujos_resultado
    (
        codigo_flujo varchar(10)  NOT NULL PRIMARY KEY,
        TMS_Inicial  decimal(18,6) NULL,
        Ley_Cu_1     decimal(18,6) NULL,
        TMS_Final    decimal(18,6) NULL,
        Ley_Cu_2     decimal(18,6) NULL,
        Tonelaje     decimal(18,6) NULL,
        Ley_Cu       decimal(18,6) NULL
    );
    -------------------------------------------------------------------------
    -- 2) FLUJOS BASE F1..F15, F20..F25
    -------------------------------------------------------------------------
/* ================================================================
   BASE COMUN F1 - F2 - F3
   ----------------------------------------------------------------
   PRIORIDAD POR FECHA:
       1. MOV_CAM
       2. POWER BI solo si NO existe MOV_CAM para esa fecha

   MAPEO POWER BI VALIDADO:
       tipo_movimiento = 'REMANEJO' -> STOCK
       tipo_movimiento = 'EXPIT'    -> MINA

       mov_cam.Ton     -> mov_cam_powerbi.tonelaje_descarga_tms
       mov_cam.CuTG00  -> mov_cam_powerbi.cut_ponderado

   IMPORTANTE:
       La sustitucion es por DIA COMPLETO.
       Si existe MOV_CAM para una fecha, no se mezcla POWER BI
       para esa misma fecha.
================================================================ */

DROP TABLE IF EXISTS #Base_F123;

;WITH FechasMovCam AS
(
    SELECT DISTINCT
        CAST(m.fecha AS date) AS Fecha
    FROM inventar_SpcHidr.mov_cam m
    WHERE CAST(m.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin
      AND m.Fase <> 'SRR'
      AND m.Destino = 'CH01'
),
Base_F123 AS
(
    /* ============================================================
       1. FUENTE OFICIAL: MOV_CAM
       ============================================================ */
    SELECT
        CAST(m.fecha AS date) AS Fecha,

CASE
    WHEN UPPER(LTRIM(RTRIM(ISNULL(m.Origen, ''))))
         IN ('STOCK', 'REMANEJO')
        THEN 'Stock'

    WHEN UPPER(LTRIM(RTRIM(ISNULL(m.Origen, ''))))
         IN ('MINA', 'EXPIT')
        THEN 'Mina'

    ELSE m.Origen
END AS Origen,

        TRY_CONVERT(float, m.Ton)     AS Ton,
        TRY_CONVERT(float, m.CuTG00)  AS CuTG00,

        CAST('MOV_CAM' AS varchar(30)) AS Fuente

    FROM inventar_SpcHidr.mov_cam m

    WHERE CAST(m.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin
      AND m.Fase <> 'SRR'
      AND m.Destino = 'CH01'


    UNION ALL


    /* ============================================================
       2. FALLBACK: POWER BI
       Solo dias donde no existe MOV_CAM
       ============================================================ */
    SELECT
        CAST(p.fecha AS date) AS Fecha,

        CASE
            WHEN UPPER(LTRIM(RTRIM(ISNULL(p.tipo_movimiento, ''))))
                 = 'REMANEJO'
                THEN 'Stock'

            WHEN UPPER(LTRIM(RTRIM(ISNULL(p.tipo_movimiento, ''))))
                 = 'EXPIT'
                THEN 'Mina'

            ELSE NULL
        END AS Origen,

        TRY_CONVERT(float, p.tonelaje_descarga_tms) AS Ton,
        TRY_CONVERT(float, p.cut_ponderado)          AS CuTG00,

        CAST('POWERBI_PRELIMINAR' AS varchar(30)) AS Fuente

    FROM inventar_SpcHidr.mov_cam_powerbi p

    WHERE CAST(p.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin

      AND UPPER(LTRIM(RTRIM(ISNULL(p.fase, '')))) <> 'SRR'

      AND UPPER(LTRIM(RTRIM(ISNULL(p.destino_descarga, ''))))
          = 'CH01'

      AND NOT EXISTS
      (
          SELECT 1
          FROM FechasMovCam mc
          WHERE mc.Fecha = CAST(p.fecha AS date)
      )
)

SELECT
    Fecha,
    Origen,
    Ton,
    CuTG00,
    Fuente
INTO #Base_F123
FROM Base_F123;


/* ================================================================
   F1 - STOCK
   MOV_CAM  : Origen = Stock
   POWER BI : tipo_movimiento = REMANEJO
================================================================ */
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F1',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_F123
WHERE Origen = 'Stock';


/* ================================================================
   F2 - MINA
   MOV_CAM  : Origen = Mina
   POWER BI : tipo_movimiento = EXPIT
================================================================ */
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F2',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_F123
WHERE Origen = 'Mina';


/* ================================================================
   F3 - TOTAL ALIMENTACION CH01 NO SRR

   Mantiene la logica del SP actual:
   F3 no filtra por Origen.
================================================================ */
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F3',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_F123;

/* ================================================================
   F4 - DESCARGA SECA CHANCADO CV006 HACIA SILO
   ----------------------------------------------------------------
   TONELAJE:
       Fuente  : vista_resumen_datos_filtrados.CV006_tot
       Humedad : 2.5 %
       TMS     : SUM(CV006_tot) * 0.975

   LEY Cu:
       Se utiliza la Ley_Cu calculada para F3.

       F3 ya resuelve la jerarquia:
           1. MOV_CAM
           2. POWER BI preliminar cuando falta MOV_CAM

       Esto es equivalente a la logica historica de F4, ya que
       F3 y F4 utilizaban exactamente la misma ley de cabeza:
           Fase <> 'SRR'
           Destino = 'CH01'

   IMPORTANTE:
       Power BI NO reemplaza el tonelaje de F4.
       El tonelaje de F4 sigue viniendo de CV006.
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F4',

    ROUND(
        COALESCE(
            (
                SELECT SUM(v.CV006_tot)
                FROM inventar_SpcHidr.vista_resumen_datos_filtrados v
                WHERE v.fecha_turno >= @fecha_inicio
                  AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)
            ),
            0
        ) * 0.975,
        2
    ) AS Tonelaje,

    COALESCE(
        (
            SELECT f3.Ley_Cu
            FROM #flujos_resultado f3
            WHERE f3.codigo_flujo = 'F3'
        ),
        0
    ) AS Ley_Cu;
/* ================================================================
   F5 - DELTA INVENTARIO CHANCADO
   ----------------------------------------------------------------
   NUEVA FUENTE DE INVENTARIO:
       inventar_SpcHidr.v_inventario_chancado_test

   INVENTARIO:
       Apertura periodo:
           Inventario_Chancado_TMS_Anterior de @fecha_inicio

       Cierre periodo:
           Total_Inventario_Chancado_TMS de @fecha_fin

       Delta:
           Cierre - Apertura

   La vista ya incorpora:
       - Silo A-B
       - Harnero A-E
       - Chancado A-E
       - Tolva de compensacion
       - Humedad de inventario
       - Validacion Archive Value
       - Continuidad diaria / semilla

   LEY Cu:
       Se mantiene la metodologia vigente del F5:
       ley CH01 no-SRR en los extremos.

       La fuente de ley respeta ahora:
           MOV_CAM > POWERBI_PRELIMINAR

   IMPORTANTE:
       #Base_F123 debe seguir existiendo hasta terminar F5.
================================================================ */

;WITH
inv_i AS
(
    SELECT
        CASE
            WHEN MAX(i.Flag_Continuidad_Diaria) = 1
             AND MAX(i.Flag_Inventario_Valido) = 1
            THEN MAX(
                TRY_CONVERT(
                    float,
                    i.Inventario_Chancado_TMS_Anterior
                )
            )
            ELSE NULL
        END AS total_tms

    FROM inventar_SpcHidr.v_inventario_chancado_test i

    WHERE i.Fecha = @fecha_inicio
),

inv_f AS
(
    SELECT
        CASE
            WHEN MAX(i.Flag_Inventario_Valido) = 1
            THEN MAX(
                TRY_CONVERT(
                    float,
                    i.Total_Inventario_Chancado_TMS
                )
            )
            ELSE NULL
        END AS total_tms

    FROM inventar_SpcHidr.v_inventario_chancado_test i

    WHERE i.Fecha = @fecha_fin
),

/* ============================================================
   Ley inicial

   Utiliza la misma base normalizada F1-F3:
       MOV_CAM cuando existe
       POWER BI cuando falta MOV_CAM
   ============================================================ */
ley_i AS
(
    SELECT
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0 AS ley_cu

    FROM #Base_F123

    WHERE Fecha = @fecha_inicio
),

/* ============================================================
   Ley final
   ============================================================ */
ley_f AS
(
    SELECT
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0 AS ley_cu

    FROM #Base_F123

    WHERE Fecha = @fecha_fin
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F5',

    /* Inventario apertura */
    inv_i.total_tms AS TMS_Inicial,

    /* Ley apertura */
    CASE
        WHEN inv_i.total_tms IS NULL
            THEN NULL
        ELSE COALESCE(
            ley_i.ley_cu,
            ley_f.ley_cu
        )
    END AS Ley_Cu_1,

    /* Inventario cierre */
    inv_f.total_tms AS TMS_Final,

    /* Ley cierre */
    CASE
        WHEN inv_f.total_tms IS NULL
            THEN NULL
        ELSE COALESCE(
            ley_f.ley_cu,
            ley_i.ley_cu
        )
    END AS Ley_Cu_2,

    /* Delta inventario */
    CASE
        WHEN inv_i.total_tms IS NULL
          OR inv_f.total_tms IS NULL
            THEN NULL

        ELSE
            inv_f.total_tms
            - inv_i.total_tms
    END AS Tonelaje,

    /* ============================================================
       Ley equivalente del delta de inventario
       ============================================================ */
    CASE
        WHEN inv_i.total_tms IS NULL
          OR inv_f.total_tms IS NULL
          OR (inv_f.total_tms - inv_i.total_tms) = 0
            THEN NULL

        ELSE
            (
                (
                    inv_f.total_tms
                    *
                    COALESCE(
                        ley_f.ley_cu,
                        ley_i.ley_cu
                    )
                    / 100.0
                )
                -
                (
                    inv_i.total_tms
                    *
                    COALESCE(
                        ley_i.ley_cu,
                        ley_f.ley_cu
                    )
                    / 100.0
                )
            )
            /
            NULLIF(
                inv_f.total_tms
                - inv_i.total_tms,
                0
            )
            * 100.0
    END AS Ley_Cu

FROM inv_i
CROSS JOIN inv_f
CROSS JOIN ley_i
CROSS JOIN ley_f;

/* ================================================================
   #Base_F123 ya no se necesita despues de F5
================================================================ */
DROP TABLE IF EXISTS #Base_F123;

/* ================================================================
   BASE COMUN LEY CuT SRR
   ----------------------------------------------------------------
   Consumidores:
       F8
       F9
       F25

   PRIORIDAD POR FECHA:
       1. MOV_CAM SRR válido
       2. IMP SRR solo si MOV_CAM no tiene ley válida ese día

   IMPORTANTE:
       - MOV_CAM e IMP no se mezclan dentro del mismo día.
       - Ton_Ponderador se utiliza SOLO para calcular la ley.
       - NO define la masa de F8, F9 ni F25.
================================================================ */

DROP TABLE IF EXISTS #Ley_SRR_Dia;

;WITH MOV_CAM_SRR AS
(
    SELECT
        CAST(m.fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN TRY_CONVERT(float, m.Ton) > 0
                 AND TRY_CONVERT(float, m.CuTG00) IS NOT NULL
                THEN TRY_CONVERT(float, m.Ton)
                ELSE 0
            END
        ) AS Ton_Ponderador,

        SUM
        (
            CASE
                WHEN TRY_CONVERT(float, m.Ton) > 0
                 AND TRY_CONVERT(float, m.CuTG00) IS NOT NULL
                THEN
                    TRY_CONVERT(float, m.Ton)
                    * TRY_CONVERT(float, m.CuTG00)
                    / 100.0
                ELSE 0
            END
        ) AS FCu_Ponderador

    FROM inventar_SpcHidr.mov_cam AS m

    WHERE CAST(m.fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND UPPER(LTRIM(RTRIM(ISNULL(m.Fase, '')))) = 'SRR'

      AND UPPER(LTRIM(RTRIM(ISNULL(m.Destino, ''))))
          IN ('PRUEBA', 'CH01')

    GROUP BY
        CAST(m.fecha AS date)
),

MOV_CAM_SRR_VALIDO AS
(
    SELECT
        Fecha,
        Ton_Ponderador,

        FCu_Ponderador
        / NULLIF(Ton_Ponderador, 0)
        * 100.0 AS CuT,

        CAST('MOV_CAM' AS varchar(20)) AS Fuente

    FROM MOV_CAM_SRR

    WHERE Ton_Ponderador > 0
),

IMP_SRR AS
(
    SELECT
        CAST(i.Fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                 AND TRY_CONVERT(float, i.Ton) > 0
                 AND TRY_CONVERT(float, i.CuT) IS NOT NULL
                THEN TRY_CONVERT(float, i.Ton)
                ELSE 0
            END
        ) AS Ton_Ponderador,

        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                 AND TRY_CONVERT(float, i.Ton) > 0
                 AND TRY_CONVERT(float, i.CuT) IS NOT NULL
                THEN
                    TRY_CONVERT(float, i.Ton)
                    * TRY_CONVERT(float, i.CuT)
                    / 100.0
                ELSE 0
            END
        ) AS FCu_Ponderador

    FROM DEV_SIIR.hidro.v_imp_chancado_normalizado AS i

    WHERE CAST(i.Fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND ISNULL(i.Es_SRR, 0) = 1

    GROUP BY
        CAST(i.Fecha AS date)
),

IMP_SRR_VALIDO AS
(
    SELECT
        Fecha,
        Ton_Ponderador,

        FCu_Ponderador
        / NULLIF(Ton_Ponderador, 0)
        * 100.0 AS CuT,

        CAST('IMP' AS varchar(20)) AS Fuente

    FROM IMP_SRR

    WHERE Ton_Ponderador > 0
),

LEY_SRR_FINAL AS
(
    /* MOV_CAM tiene prioridad */
    SELECT
        m.Fecha,
        m.Ton_Ponderador,
        m.CuT,
        m.Fuente

    FROM MOV_CAM_SRR_VALIDO AS m


    UNION ALL


    /* IMP rellena solamente días sin MOV_CAM válido */
    SELECT
        i.Fecha,
        i.Ton_Ponderador,
        i.CuT,
        i.Fuente

    FROM IMP_SRR_VALIDO AS i

    WHERE NOT EXISTS
    (
        SELECT 1
        FROM MOV_CAM_SRR_VALIDO AS m
        WHERE m.Fecha = i.Fecha
    )
)

SELECT
    Fecha,
    Ton_Ponderador,
    CuT,
    Fuente

INTO #Ley_SRR_Dia

FROM LEY_SRR_FINAL;
/* ================================================================
   F8 - SRR LINEA TM1 / CV002
   ----------------------------------------------------------------
   Masa:
       metodología vigente CV002 * 0.97

   Ley:
       #Ley_SRR_Dia
       MOV_CAM -> IMP por fecha
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F8',

    /* ============================================================
       MASA - SIN CAMBIO
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(cv002_tot) * 0.97

            FROM inventar_SpcHidr.vista_resumen_datos_filtrados

            WHERE fecha_turno >= @fecha_inicio
              AND fecha_turno < DATEADD(DAY, 1, @fecha_fin)
        ),
        0
    ) AS Tonelaje,

    /* ============================================================
       LEY SRR RESUELTA
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(
                    Ton_Ponderador
                    * CuT
                    / 100.0
                )
                /
                NULLIF(
                    SUM(Ton_Ponderador),
                    0
                )
                * 100.0

            FROM #Ley_SRR_Dia
        ),
        0
    ) AS Ley_Cu;
/* ================================================================
   F9 - SRR LINEA TM2 / CV003
   ----------------------------------------------------------------
   Masa:
       metodología vigente CV003 * 0.97

   Ley:
       #Ley_SRR_Dia
       MOV_CAM -> IMP por fecha
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F9',

    /* ============================================================
       MASA - SIN CAMBIO
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(cv003_tot) * 0.97

            FROM inventar_SpcHidr.vista_resumen_datos_filtrados

            WHERE fecha_turno >= @fecha_inicio
              AND fecha_turno < DATEADD(DAY, 1, @fecha_fin)
        ),
        0
    ) AS Tonelaje,

    /* ============================================================
       LEY SRR RESUELTA
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(
                    Ton_Ponderador
                    * CuT
                    / 100.0
                )
                /
                NULLIF(
                    SUM(Ton_Ponderador),
                    0
                )
                * 100.0

            FROM #Ley_SRR_Dia
        ),
        0
    ) AS Ley_Cu;
/* ============================================================
   F10 - SAL ASIGNADA A LÍNEA CV201 / TM1

   Masa total diaria:
       topografia_sal, vía v_sal_ajustada

   Distribución:
       participación diaria de CV201 respecto de CV201 + CV202

   Solo se consideran días válidos para balance.
   Ley Cu = 0 %
   ============================================================ */
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F10',
    ISNULL(SUM(s.Sal_CV201_Dia), 0),
    0
FROM inventar_SpcHidr.v_sal_distribuida_correa_test AS s
WHERE s.Fecha >= @fecha_inicio
  AND s.Fecha < DATEADD(DAY, 1, @fecha_fin)
  AND s.Flag_Sal_Balance_Valida = 1;


/* ============================================================
   F11 - SAL ASIGNADA A LÍNEA CV202 / TM2

   Masa total diaria:
       topografia_sal, vía v_sal_ajustada

   Distribución:
       participación diaria de CV202 respecto de CV201 + CV202

   Solo se consideran días válidos para balance.
   Ley Cu = 0 %
   ============================================================ */
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F11',
    ISNULL(SUM(s.Sal_CV202_Dia), 0),
    0
FROM inventar_SpcHidr.v_sal_distribuida_correa_test AS s
WHERE s.Fecha >= @fecha_inicio
  AND s.Fecha < DATEADD(DAY, 1, @fecha_fin)
  AND s.Flag_Sal_Balance_Valida = 1;

  /* ================================================================
   F6 / F7 - MINERAL NETO TM1 / TM2
   ----------------------------------------------------------------
   ORDEN DE CALCULO:
       F8  = SRR linea TM1
       F9  = SRR linea TM2
       F10 = Sal linea TM1
       F11 = Sal linea TM2

       Luego:

       F6 = TMS bruto TM1 - F8 - F10
       F7 = TMS bruto TM2 - F9 - F11

   COBRE FINO:
       FCu F6 = FCu bruto TM1 - FCu F8
       FCu F7 = FCu bruto TM2 - FCu F9

   La sal no aporta cobre:
       F10 Ley Cu = 0
       F11 Ley Cu = 0

   FUENTES BASE:
       TMS bruto:
           inventar_SpcHidr.v_datos_apilado_tmh_v2
           + humedad resuelta por TM/turno

       Ley CuT bruta:
           inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test

   IMPORTANTE:
       - No se recalculan F8/F9/F10/F11.
       - Se consumen directamente desde #flujos_resultado.
       - No se fuerza F6/F7 >= 0.
       - Si existe una inconsistencia instrumental, debe quedar visible.
================================================================ */


/* ================================================================
   1. BASE BRUTA TM1 / TM2
================================================================ */

DROP TABLE IF EXISTS #Base_F67;

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_fin)
    )
),

TMH AS
(
    SELECT
        v.Fecha,
        x.Turno,
        x.TM,

        /* Protección ya validada para spikes de tonelaje */
        CASE
            WHEN ABS(COALESCE(x.TMH, 0)) > 150000
                THEN 0
            ELSE COALESCE(x.TMH, 0)
        END AS TMH

    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2 AS v

    CROSS APPLY
    (
        VALUES
            ('A', 'TM1', v.TMH_CV008_A),
            ('B', 'TM1', v.TMH_CV008_B),

            ('A', 'TM2', v.TMH_CV108_A),
            ('B', 'TM2', v.TMH_CV108_B)
    ) AS x
    (
        Turno,
        TM,
        TMH
    )

    WHERE v.Fecha >= @fecha_inicio
      AND v.Fecha < DATEADD(DAY, 1, @fecha_fin)
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT,
        l.Fuente_CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,
        Fuente_CuT,

        /* --------------------------------------------------------
           TMS BRUTO
           -------------------------------------------------------- */
        CASE
            WHEN TMH = 0
                THEN 0

            /* No inventar humedad */
            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                * (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                  )
        END AS TMS,

        /* --------------------------------------------------------
           COBRE FINO BRUTO
           -------------------------------------------------------- */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    * (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                      )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0
        END AS FCu

    FROM Base
),

Resumen AS
(
    SELECT
        TM,

        /* --------------------------------------------------------
           Si existe TMH positivo sin humedad, no omitir
           silenciosamente el turno.
           -------------------------------------------------------- */
        CASE
            WHEN SUM(
                    CASE
                        WHEN TMH > 0
                         AND Humedad IS NULL
                        THEN 1
                        ELSE 0
                    END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)
        END AS TMS_Bruto,

        /* --------------------------------------------------------
           Igual criterio para cobre fino.
           -------------------------------------------------------- */
        CASE
            WHEN SUM(
                    CASE
                        WHEN TMH > 0
                         AND (
                                Humedad IS NULL
                                OR CuT IS NULL
                             )
                        THEN 1
                        ELSE 0
                    END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)
        END AS FCu_Bruto,

        SUM(
            CASE
                WHEN TMH > 0
                 AND Humedad IS NULL
                THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_Humedad,

        SUM(
            CASE
                WHEN TMH > 0
                 AND Humedad IS NOT NULL
                 AND CuT IS NULL
                THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_CuT

    FROM Calculo

    GROUP BY TM
)

SELECT
    TM,
    TMS_Bruto,
    FCu_Bruto,
    Turnos_Sin_Humedad,
    Turnos_Sin_CuT

INTO #Base_F67

FROM Resumen;


/* ================================================================
   2. RECUPERAR F8 / F9 / F10 / F11 YA CALCULADOS

   No se vuelve a consultar sus fuentes.
================================================================ */

;WITH Flujos_Aux AS
(
    SELECT
        MAX(
            CASE
                WHEN codigo_flujo = 'F8'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F8_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F8'
                THEN
                    TRY_CONVERT(float, Tonelaje)
                    * TRY_CONVERT(float, Ley_Cu)
                    / 100.0
            END
        ) AS F8_FCu,


        MAX(
            CASE
                WHEN codigo_flujo = 'F9'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F9_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F9'
                THEN
                    TRY_CONVERT(float, Tonelaje)
                    * TRY_CONVERT(float, Ley_Cu)
                    / 100.0
            END
        ) AS F9_FCu,


        MAX(
            CASE
                WHEN codigo_flujo = 'F10'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F10_TMS,


        MAX(
            CASE
                WHEN codigo_flujo = 'F11'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F11_TMS

    FROM #flujos_resultado

    WHERE codigo_flujo IN
    (
        'F8',
        'F9',
        'F10',
        'F11'
    )
),

F67_Calculado AS
(
    SELECT
        b.TM,

        /* ========================================================
           TONELAJE NETO
           ======================================================== */

        CASE
            WHEN b.TM = 'TM1'
            THEN
                  b.TMS_Bruto
                - ISNULL(f.F8_TMS, 0)
                - ISNULL(f.F10_TMS, 0)

            WHEN b.TM = 'TM2'
            THEN
                  b.TMS_Bruto
                - ISNULL(f.F9_TMS, 0)
                - ISNULL(f.F11_TMS, 0)

        END AS TMS_Neto,


        /* ========================================================
           COBRE FINO NETO

           Sal no resta cobre porque Ley Cu = 0.
           ======================================================== */

        CASE
            WHEN b.TM = 'TM1'
            THEN
                  b.FCu_Bruto
                - ISNULL(f.F8_FCu, 0)

            WHEN b.TM = 'TM2'
            THEN
                  b.FCu_Bruto
                - ISNULL(f.F9_FCu, 0)

        END AS FCu_Neto

    FROM #Base_F67 AS b

    CROSS JOIN Flujos_Aux AS f
),

F67_Final AS
(
    SELECT
        TM,
        TMS_Neto,
        FCu_Neto,

        CASE
            WHEN TMS_Neto IS NULL
              OR FCu_Neto IS NULL
                THEN NULL

            WHEN TMS_Neto = 0
                THEN 0

            ELSE
                FCu_Neto
                / NULLIF(TMS_Neto, 0)
                * 100.0

        END AS Ley_Cu_Neta

    FROM F67_Calculado
)


/* ================================================================
   3. INSERT DEFINITIVO F6 / F7
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    CASE
        WHEN TM = 'TM1' THEN 'F6'
        WHEN TM = 'TM2' THEN 'F7'
    END AS codigo_flujo,

    CAST(
        TMS_Neto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        Ley_Cu_Neta
        AS decimal(18,6)
    ) AS Ley_Cu

FROM F67_Final

WHERE TM IN ('TM1', 'TM2');


/* ================================================================
   F12 / F13 - ALIMENTACION BRUTA A AGLOMERADO
   ----------------------------------------------------------------
   F12 = TM1 / CV008
   F13 = TM2 / CV108

   Se reutiliza #Base_F67 ya calculada para F6/F7.

   FUENTES:
       TMH:
           v_datos_apilado_tmh_v2

       Humedad:
           fn_humedad_resuelta_tm_turno_test

       CuT:
           v_leyes_resueltas_data_tm_reporte_test

   IMPORTANTE:
       - F12/F13 son corrientes medidas brutas.
       - No se calculan sumando F6+F8+F10 o F7+F9+F11.
       - No dependen de import_leyes_torres.
================================================================ */


/* ================================================================
   F12 - TM1 / CV008
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F12',

    CAST(
        TMS_Bruto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        CASE
            WHEN TMS_Bruto IS NULL
              OR FCu_Bruto IS NULL
                THEN NULL

            WHEN TMS_Bruto = 0
                THEN 0

            ELSE
                FCu_Bruto
                / NULLIF(TMS_Bruto, 0)
                * 100.0
        END
        AS decimal(18,6)
    ) AS Ley_Cu

FROM #Base_F67

WHERE TM = 'TM1';


/* ================================================================
   F13 - TM2 / CV108
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F13',

    CAST(
        TMS_Bruto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        CASE
            WHEN TMS_Bruto IS NULL
              OR FCu_Bruto IS NULL
                THEN NULL

            WHEN TMS_Bruto = 0
                THEN 0

            ELSE
                FCu_Bruto
                / NULLIF(TMS_Bruto, 0)
                * 100.0
        END
        AS decimal(18,6)
    ) AS Ley_Cu

FROM #Base_F67

WHERE TM = 'TM2';


/* ================================================================
   #Base_F67 ya no se necesita después de F12/F13
================================================================ */

DROP TABLE IF EXISTS #Base_F67;
/* ================================================================
   F14 / F15 - APILADO POR PAD
   ----------------------------------------------------------------
   F14 = Alimentación asociada a PAD 2
   F15 = Alimentación asociada a PAD 1

   FUENTES DE MASA Y LEY:
       TMH:
           inventar_SpcHidr.v_datos_apilado_tmh_v2

       Humedad:
           inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test

       CuT:
           inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test

   ASIGNACION A PAD:
       inventar_SpcHidr.control_apilado_diario

   IMPORTANTE:
       - control_apilado_diario.fecha YA corresponde a fecha operacional.
       - NO aplicar DATEADD(DAY,-1,fecha).
       - Solo se asignan días con volumen_diario_m3 > 0.
       - TM1 + TM2 se consolidan por fecha antes de asignar al PAD.
       - No se utiliza import_leyes_torres.
       - No se inventa humedad ni CuT faltante.
================================================================ */


/* ================================================================
   1. BASE DIARIA OPERACIONAL TM1 + TM2
================================================================ */

DROP TABLE IF EXISTS #Base_F1415_Dia;

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_fin)
    )
),

TMH AS
(
    SELECT
        v.Fecha,
        x.Turno,
        x.TM,

        /* Misma protección utilizada y validada en F6/F7/F12/F13 */
        CASE
            WHEN ABS(COALESCE(x.TMH, 0)) > 150000
                THEN 0
            ELSE COALESCE(x.TMH, 0)
        END AS TMH

    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2 AS v

    CROSS APPLY
    (
        VALUES
            ('A', 'TM1', v.TMH_CV008_A),
            ('B', 'TM1', v.TMH_CV008_B),

            ('A', 'TM2', v.TMH_CV108_A),
            ('B', 'TM2', v.TMH_CV108_B)
    ) AS x
    (
        Turno,
        TM,
        TMH
    )

    WHERE v.Fecha >= @fecha_inicio
      AND v.Fecha < DATEADD(DAY, 1, @fecha_fin)
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT,
        l.Fuente_CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,
        Fuente_CuT,

        /* ========================================================
           TMS
           ======================================================== */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                *
                (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                )

        END AS TMS,

        /* ========================================================
           COBRE FINO
           ======================================================== */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    *
                    (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                    )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0

        END AS FCu

    FROM Base
),

Resumen_Diario AS
(
    SELECT
        Fecha,

        /* ========================================================
           TMS total TM1 + TM2 del día

           Si existe TMH positivo sin humedad, el día queda NULL.
           ======================================================== */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND Humedad IS NULL
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)

        END AS TMS_Dia,


        /* ========================================================
           Cobre fino total TM1 + TM2 del día

           Si falta humedad o CuT para un turno con masa positiva,
           no se omite silenciosamente.
           ======================================================== */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND
                              (
                                  Humedad IS NULL
                                  OR CuT IS NULL
                              )
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)

        END AS FCu_Dia,


        SUM
        (
            CASE
                WHEN TMH > 0
                 AND Humedad IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_Humedad,


        SUM
        (
            CASE
                WHEN TMH > 0
                 AND Humedad IS NOT NULL
                 AND CuT IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_CuT

    FROM Calculo

    GROUP BY Fecha
)

SELECT
    Fecha,
    TMS_Dia,
    FCu_Dia,
    Turnos_Sin_Humedad,
    Turnos_Sin_CuT

INTO #Base_F1415_Dia

FROM Resumen_Diario;


/* ================================================================
   2. FECHAS OPERACIONALES CON APILADO POR PAD

   control_apilado_diario.fecha YA está desplazada D-1
   durante la importación.

   NO volver a aplicar DATEADD(DAY,-1,...).
================================================================ */

DROP TABLE IF EXISTS #Pad_F1415_Dia;

SELECT DISTINCT
    CAST(cad.fecha AS date) AS Fecha,
    cad.pad_id

INTO #Pad_F1415_Dia

FROM inventar_SpcHidr.control_apilado_diario AS cad

WHERE CAST(cad.fecha AS date)
      BETWEEN @fecha_inicio AND @fecha_fin

  AND cad.pad_id IN (1, 2)

  AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0;


/* ================================================================
   3. RESUMEN F14 / F15
   ----------------------------------------------------------------
   PAD 2 -> F14
   PAD 1 -> F15
================================================================ */

;WITH Configuracion AS
(
    SELECT
        CAST('F14' AS varchar(10)) AS codigo_flujo,
        2 AS pad_id

    UNION ALL

    SELECT
        CAST('F15' AS varchar(10)),
        1
),

Resumen AS
(
    SELECT
        c.codigo_flujo,
        c.pad_id,

        COUNT(p.Fecha) AS Dias_Con_Apilado,

        /* Día PAD sin base instrumental */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND b.Fecha IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_Base,

        /* Falta de humedad */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND ISNULL(b.Turnos_Sin_Humedad, 0) > 0
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_Humedad,

        /* Falta de CuT */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND ISNULL(b.Turnos_Sin_CuT, 0) > 0
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_CuT,

        SUM(b.TMS_Dia) AS TMS_Total,
        SUM(b.FCu_Dia) AS FCu_Total

    FROM Configuracion AS c

    LEFT JOIN #Pad_F1415_Dia AS p
        ON p.pad_id = c.pad_id

    LEFT JOIN #Base_F1415_Dia AS b
        ON b.Fecha = p.Fecha

    GROUP BY
        c.codigo_flujo,
        c.pad_id
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    codigo_flujo,

    /* ============================================================
       TONELAJE
       ============================================================ */
    CAST
    (
        CASE
            /* PAD sin días de apilado en el período */
            WHEN Dias_Con_Apilado = 0
                THEN 0

            /* No ocultar falta de información operacional */
            WHEN Dias_Sin_Base > 0
              OR Dias_Sin_Humedad > 0
                THEN NULL

            ELSE TMS_Total
        END

        AS decimal(18,6)
    ) AS Tonelaje,


    /* ============================================================
       LEY Cu
       ============================================================ */
    CAST
    (
        CASE
            /* PAD sin días de apilado */
            WHEN Dias_Con_Apilado = 0
                THEN 0

            /* Falta información necesaria para ley */
            WHEN Dias_Sin_Base > 0
              OR Dias_Sin_Humedad > 0
              OR Dias_Sin_CuT > 0
                THEN NULL

            WHEN TMS_Total = 0
                THEN 0

            ELSE
                FCu_Total
                / NULLIF(TMS_Total, 0)
                * 100.0
        END

        AS decimal(18,6)
    ) AS Ley_Cu

FROM Resumen;


/* ================================================================
   4. LIMPIEZA
================================================================ */

DROP TABLE IF EXISTS #Base_F1415_Dia;
DROP TABLE IF EXISTS #Pad_F1415_Dia;
/* ================================================================
   F20 - RIPIO TOTAL MEDIDO POR CV025
   ----------------------------------------------------------------
   Fuente física:
       CV025 = correa común de las rotopalas asociadas a F18/F19.

   Señales disponibles:
       cv025tot  = señal histórica/legacy
       cv025_tot = señal nueva

   Regla:
       1. Construir una serie única a nivel de registro mediante:
              COALESCE(cv025_tot, cv025tot)

       2. Calcular el delta diario sobre esa serie.

       3. Proteger:
              - resets;
              - diferencias negativas;
              - saltos diarios > 100.000 TMH.

       4. Humedad operacional fija vigente:
              10 %

          TMS = TMH * 0.90

   IMPORTANTE:
       No se fuerza cierre contra F18/F19.
       CV025 es una medición independiente.
================================================================ */

;WITH CV025_Base AS
(
    SELECT
        CAST(df.fecha_turno AS date) AS Fecha,

        COALESCE
        (
            TRY_CONVERT(float, df.cv025_tot),
            TRY_CONVERT(float, df.cv025tot)
        ) AS CV025_Totalizador

    FROM inventar_SpcHidr.datos_filtrados AS df

    /*
       Se incluye el día siguiente a @fecha_fin porque necesitamos
       su primer totalizador para cerrar correctamente el último día.
    */
    WHERE df.fecha_turno >= @fecha_inicio
      AND df.fecha_turno < DATEADD(DAY, 2, @fecha_fin)
),

CV025_Dia AS
(
    SELECT
        Fecha,
        MIN(CV025_Totalizador) AS Min_CV025,
        MAX(CV025_Totalizador) AS Max_CV025

    FROM CV025_Base

    GROUP BY Fecha
),

CV025_Con_Siguiente AS
(
    SELECT
        Fecha,
        Min_CV025,
        Max_CV025,

        LEAD(Min_CV025)
            OVER (ORDER BY Fecha) AS Next_Min_CV025

    FROM CV025_Dia
),

CV025_Validado AS
(
    SELECT
        Fecha,

        CASE

            /* Sin señal válida */
            WHEN Min_CV025 IS NULL
              OR Max_CV025 IS NULL
                THEN 0

            /* Protección adicional */
            WHEN Max_CV025 - Min_CV025 < 0
                THEN 0

            /* Último día disponible:
               usar recorrido interno solo si es razonable */
            WHEN Next_Min_CV025 IS NULL
             AND Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            WHEN Next_Min_CV025 IS NULL
                THEN 0

            /* Reset entre días:
               usar recorrido interno si éste es válido */
            WHEN Next_Min_CV025 - Min_CV025 < 0
             AND Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            WHEN Next_Min_CV025 - Min_CV025 < 0
                THEN 0

            /* Operación normal */
            WHEN Next_Min_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Next_Min_CV025 - Min_CV025

            /* Fallback al recorrido interno */
            WHEN Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            /* Spike no físicamente razonable */
            ELSE 0

        END AS CV025_TMH_Dia

    FROM CV025_Con_Siguiente
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F20',

    ISNULL
    (
        SUM(CV025_TMH_Dia) * 0.90,
        0
    ),

    0

FROM CV025_Validado

WHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin;
/* ================================================================
   F21 - RECLAMO POR CAMIONES PAD SULFUROS
   ----------------------------------------------------------------
   Fuente:
       Datos_conciliados_of.Camiones_TMS_Reclamo_Sulfuros

   Esta columna corresponde al cálculo operacional de camiones
   de reclamo persistido en Datos Conciliados.

   Validación agosto 2026:
       coincide 1:1 con reclamo.v_reclamo_para_conciliados.

   La ley Cu se asigna posteriormente usando la ley de F18.
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F21',

    ISNULL(
        SUM(Camiones_TMS_Reclamo_Sulfuros),
        0
    ),

    0

FROM inventar_SpcHidr.Datos_conciliados_of

WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;
-- F22
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F22',
    ISNULL(SUM(Camiones_TMS_Reclamo_Oxidos), 0),
    0
FROM inventar_SpcHidr.Datos_conciliados_of
WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;
    -- F23 y F24: se recalculan mas adelante en base a F39/F44/F48/F49/F50 (ver seccion final antes de la salida)
/* ================================================================
   F25 - ALIMENTACION SRR CV001
   ----------------------------------------------------------------
   TONELAJE:
       < 01-07-2026:
           metodología histórica CV001 * 0.97

       >= 01-07-2026:
           tot_tm.tot_001 = Process Value [TMH/h]
           integración 10 s
           TMS = TMH * 0.97

   LEY CuT:
       Se consume desde #Ley_SRR_Dia.

       La base común ya resolvió por fecha:
           1. MOV_CAM SRR
           2. IMP SRR como fallback

   IMPORTANTE:
       - MOV_CAM / IMP caracterizan la ley.
       - No definen el tonelaje F25.
       - No se fuerza F25 = F8 + F9.
================================================================ */

/* ================================================================
   4. TONELAJE F25

   Se separa histórico y Process Value para permitir períodos
   que crucen el 01-07-2026.
================================================================ */

;WITH F25_Historico AS
(
    SELECT
        SUM(
            TRY_CONVERT(float, v.cv001_tot)
        ) * 0.97 AS TMS

    FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v

    WHERE v.fecha_turno >= @fecha_inicio
      AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)

      /* tot_001 todavía era totalizador antes de esta fecha */
      AND v.fecha_turno < '2026-07-01'
),

F25_ProcessValue AS
(
    SELECT
        SUM
        (
            TRY_CONVERT(float, t.tot_001)

            /* integración de t/h cada 10 segundos */
            * 10.0
            / 3600.0

        )
        /* humedad SRR = 3 % */
        * 0.97 AS TMS

    FROM inventar_SpcHidr.tot_tm AS t

    WHERE t.fecha_turno >=
          CASE
              WHEN @fecha_inicio < '2026-07-01'
                  THEN CONVERT(date, '2026-07-01')
              ELSE @fecha_inicio
          END

      AND t.fecha_turno <= @fecha_fin

      AND t.tot_001 IS NOT NULL

      /* Un Process Value negativo no representa flujo físico */
      AND TRY_CONVERT(float, t.tot_001) >= 0
),

F25_Tonelaje AS
(
    SELECT
          ISNULL(h.TMS, 0)
        + ISNULL(p.TMS, 0) AS TMS

    FROM F25_Historico AS h
    CROSS JOIN F25_ProcessValue AS p
),

F25_Ley AS
(
    SELECT
        SUM
        (
            l.Ton_Ponderador
            * l.CuT
            / 100.0
        )
        /
        NULLIF
        (
            SUM(l.Ton_Ponderador),
            0
        )
        * 100.0 AS Ley_Cu

    FROM #Ley_SRR_Dia AS l
)


/* ================================================================
   5. INSERT DEFINITIVO F25
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F25',

    CAST(
        ISNULL(t.TMS, 0)
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        ISNULL(l.Ley_Cu, 0)
        AS decimal(18,6)
    ) AS Ley_Cu

FROM F25_Tonelaje AS t
CROSS JOIN F25_Ley AS l;


/* ================================================================
   Limpieza
================================================================ */

DROP TABLE IF EXISTS #Ley_SRR_Dia;
    -------------------------------------------------------------------------
    -- 3) F18
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f18_oficial') IS NOT NULL
        DROP TABLE #tmp_f18_oficial;
    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.[campaña_id],
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
Pct_Historico AS
(
    /* ============================================================
       Historial de avance por PAD / campaña / módulo.

       control_reclamo_diario.fecha YA es fecha operacional.
       No aplicar D-1 adicional.
       ============================================================ */
    SELECT
        CAST(crd.fecha AS date) AS fecha,
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id,

        CASE
            WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
            WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
            ELSE MAX(crd.avance_porcentaje)
        END AS pct_clip

    FROM inventar_SpcHidr.control_reclamo_diario AS crd

    WHERE CAST(crd.fecha AS date) <= @fecha_fin

    GROUP BY
        CAST(crd.fecha AS date),
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id
),

Pct_Diario AS
(
    /* ============================================================
       1. Registros del período
       ============================================================ */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    WHERE h.fecha BETWEEN @fecha_inicio AND @fecha_fin


    UNION ALL


    /* ============================================================
       2. Semilla:
          último estado anterior al inicio del período,
          por PAD / campaña / módulo.

          Permite que LAG calcule correctamente el incremento
          del primer día operacional.
       ============================================================ */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    INNER JOIN
    (
        SELECT
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(fecha) AS fecha

        FROM Pct_Historico

        WHERE fecha < @fecha_inicio

        GROUP BY
            pad_id,
            [campaña_id],
            modulo_id
    ) AS s

        ON  s.pad_id       = h.pad_id
        AND s.[campaña_id] = h.[campaña_id]
        AND s.modulo_id    = h.modulo_id
        AND s.fecha        = h.fecha
),
    Pct_Segmentado AS (
        SELECT
            p.*,
            CASE
                WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id
                    ORDER BY p.fecha
                ) THEN 1
                ELSE 0
            END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT
            ps.*,
            SUM(ps.reset_flag) OVER (
                PARTITION BY ps.[campaña_id], ps.modulo_id, ps.pad_id
                ORDER BY ps.fecha
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha,
            p.pad_id,
            p.[campaña_id],
            p.modulo_id,
            p.pct_clip AS avance_porcentaje,
            CASE
                WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                )) < 0 THEN 0
                ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                ))
            END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha,
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date)
      BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            a.fecha AS fecha_operacion,
            a.[campaña_id],
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm
          ON tm.[campaña_id] = a.[campaña_id]
         AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario vd
          ON vd.fecha = a.fecha
         AND vd.pad_id = a.pad_id
         AND vd.[campaña_id] = a.[campaña_id]
         AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 2
          AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ModulosActivos AS (
        SELECT
            r.[campaña_id],
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (
                    SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                    / NULLIF(SUM(ma.tms_reclamado_modulo), 0)
                ) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c
            ON ma.[campaña_id] = c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m
            ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p
            ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd
            ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr
            ON clr.Campana = c.[numero_campaña]
           AND clr.Parcela = p.numero
           AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        WHERE pd.id_pad = 2
    )
    SELECT
        t.Tonelaje,
        l.Ley_Cu
    INTO #tmp_f18_oficial
    FROM Calculo_Tonelaje t
    CROSS JOIN Calculo_Ley l;
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F18', Tonelaje, Ley_Cu
    FROM #tmp_f18_oficial;
    -------------------------------------------------------------------------
    -- 4) F19
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f19_oficial') IS NOT NULL
        DROP TABLE #tmp_f19_oficial;
    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.[campaña_id],
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
Pct_Historico AS
(
    SELECT
        CAST(crd.fecha AS date) AS fecha,
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id,

        CASE
            WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
            WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
            ELSE MAX(crd.avance_porcentaje)
        END AS pct_clip

    FROM inventar_SpcHidr.control_reclamo_diario AS crd

    WHERE CAST(crd.fecha AS date) <= @fecha_fin

    GROUP BY
        CAST(crd.fecha AS date),
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id
),

Pct_Diario AS
(
    /* Registros del período */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    WHERE h.fecha BETWEEN @fecha_inicio AND @fecha_fin


    UNION ALL


    /* Último estado previo = semilla */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    INNER JOIN
    (
        SELECT
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(fecha) AS fecha

        FROM Pct_Historico

        WHERE fecha < @fecha_inicio

        GROUP BY
            pad_id,
            [campaña_id],
            modulo_id
    ) AS s
        ON  s.pad_id       = h.pad_id
        AND s.[campaña_id] = h.[campaña_id]
        AND s.modulo_id    = h.modulo_id
        AND s.fecha        = h.fecha
),

    Pct_Segmentado AS (
        SELECT
            p.*,
            CASE
                WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id
                    ORDER BY p.fecha
                ) THEN 1
                ELSE 0
            END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT
            ps.*,
            SUM(ps.reset_flag) OVER (
                PARTITION BY ps.[campaña_id], ps.modulo_id, ps.pad_id
                ORDER BY ps.fecha
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha,
            p.pad_id,
            p.[campaña_id],
            p.modulo_id,
            p.pct_clip AS avance_porcentaje,
            CASE
                WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                )) < 0 THEN 0
                ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                ))
            END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha,
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            a.fecha AS fecha_operacion,
            a.[campaña_id],
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm
          ON tm.[campaña_id] = a.[campaña_id]
         AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario vd
          ON vd.fecha = a.fecha
         AND vd.pad_id = a.pad_id
         AND vd.[campaña_id] = a.[campaña_id]
         AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 1
          AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ModulosActivos AS (
        SELECT
            r.[campaña_id],
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (
                    SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                    / NULLIF(SUM(ma.tms_reclamado_modulo), 0)
                ) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c
            ON ma.[campaña_id] = c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m
            ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p
            ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd
            ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr
            ON clr.Campana = c.[numero_campaña]
           AND clr.Parcela = p.numero
           AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        WHERE pd.id_pad = 1
    )
    SELECT
        t.Tonelaje,
        l.Ley_Cu
    INTO #tmp_f19_oficial
    FROM Calculo_Tonelaje t
    CROSS JOIN Calculo_Ley l;
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F19', Tonelaje, Ley_Cu
    FROM #tmp_f19_oficial;
    -------------------------------------------------------------------------
    -- Variables de F18/F19 requeridas para la seccion 7 (ajustes finales)
    -------------------------------------------------------------------------
    DECLARE
        @ton_f18 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F18'), 0),
        @ley_f18 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F18'), 0),
        @ton_f19 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F19'), 0),
        @ley_f19 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F19'), 0);
    -------------------------------------------------------------------------
    -- 7) AJUSTES FINALES DE LEYES
    -------------------------------------------------------------------------
    UPDATE #flujos_resultado
       SET Ley_Cu = @ley_f18
     WHERE codigo_flujo = 'F21';
    UPDATE #flujos_resultado
       SET Ley_Cu = @ley_f19
     WHERE codigo_flujo = 'F22';
    UPDATE #flujos_resultado
       SET Ley_Cu = CASE
                        WHEN (@ton_f18 + @ton_f19) = 0 THEN 0
                        ELSE ((@ton_f18 * @ley_f18) + (@ton_f19 * @ley_f19)) / (@ton_f18 + @ton_f19)
                    END
     WHERE codigo_flujo = 'F20';
    -------------------------------------------------------------------------
    -- 8) FLUJOS F26..F115
    -------------------------------------------------------------------------
    
    -- F28
    -- H2SO4 hacia Tambor AD001
    --
    -- Fuente anterior:
    --   tags_sx_ew.acido_aglomerado_1_m3h
    --   Granularidad: 1 registro por hora
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.acido_aglomerado_tambor_ad001_m3h
    --   Granularidad: 1 registro diario
    --
    -- Conversión:
    --   m3/h * 24 h/dia * 1.84 t/m3 = t H2SO4/dia

    ;WITH base_f28 AS (
        SELECT 
            COALESCE(t.acido_aglomerado_tambor_ad001_m3h, 0) 
            * 24.0
            * 1.84 AS flujo_ton_dia
        FROM inventar_SpcHidr.insumos_area_humeda_flujos t
        WHERE t.fecha_registro >= @fecha_inicio
          AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
    )
    INSERT INTO #flujos_resultado 
    (
        codigo_flujo, Tonelaje, Ley_Cu
    )
    SELECT      
            'F28', 
            COALESCE(SUM(flujo_ton_dia), 0), 
            0.0
    FROM base_f28;

    -- F29
    -- H2SO4 hacia Tambor AD100
    --
    -- Fuente anterior:
    --   tags_sx_ew.acido_aglomerado_100_m3h
    --   Granularidad: horaria
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.acido_aglomerado_tambor_ad100_m3h
    --   Granularidad: diaria
    --
    -- Conversión:
    --   m3/h * 24 h/dia * 1.84 t/m3 = t H2SO4/dia
    ;WITH base_f29 AS (
        SELECT 
            COALESCE(t.acido_aglomerado_tambor_ad100_m3h, 0) 
            * 24.0
            * 1.84 AS flujo_ton_dia
        FROM inventar_SpcHidr.insumos_area_humeda_flujos t
        WHERE t.fecha_registro >= @fecha_inicio
          AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
    )
    INSERT INTO #flujos_resultado 
    (
        codigo_flujo, Tonelaje, Ley_Cu
    )
    SELECT 
            'F29', 
            COALESCE(SUM(flujo_ton_dia), 0), 
            0.0
    FROM base_f29;
-- F30-F31
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES
    ('F30',0,0),('F31',0,0);
-- F37 - DPLS
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_dpls_m3h
-- Concentración:
--   conc_cu.dump_dpls_cu
--
-- Integración:
--   m3/h * 24 h/dia = m3/dia

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_dpls_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.dump_dpls_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F37',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;

-- F38 - Feed DUMP
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_feed_dump_m3h
-- Concentración:
--   conc_cu.dump_feed_cu

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_feed_dump_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.dump_feed_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F38',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;

/* ================================================================
   F33 - TRANSFERENCIA DE COBRE DESDE PAD DUMP MINERAL A SOLUCION
   ----------------------------------------------------------------
   F37 = DPLS
   F38 = Feed DUMP

   Densidad de soluciones asumida:
       1.0 t/m3

   Cobre fino:
       CuF37 = F37 * Ley37 / 100
       CuF38 = F38 * Ley38 / 100

   Balance de cobre del nodo solucion:
       F33 + CuF38 = CuF35 + CuF37

   Como CuF35 = 0:

       F33 = CuF37 - CuF38

   F33 representa directamente toneladas de cobre fino:
       Ley F33 = 100 %
       CuF33    = F33
================================================================ */

;WITH F37 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F37'
),

F38 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F38'
),

Calculo_F33 AS
(
    SELECT
        /* Cobre fino DPLS */
        F37.Tonelaje
        * F37.Ley_Cu
        / 100.0 AS CuF37,

        /* Cobre fino Feed DUMP */
        F38.Tonelaje
        * F38.Ley_Cu
        / 100.0 AS CuF38

    FROM F37
    CROSS JOIN F38
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F33',

    /* F33 = CuF37 - CuF38 */
    CuF37 - CuF38,

    /* F33 ya representa cobre fino */
    100.0

FROM Calculo_F33;
/* ================================================================
   F35 - VARIACION / RESIDUAL PAD DUMP SOLUCION
   ----------------------------------------------------------------
   Balance de masa del nodo solucion:

       F33 + F38 = F35 + F37 + F34

   Actualmente:
       F34 = 0

   Por lo tanto:

       F35 = F33 + F38 - F37

   Convencion del modelo:
       Ley F35 = 0 %
       CuF35   = 0

   Densidad de solucion asumida:
       1.0 t/m3
================================================================ */

;WITH F33 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F33'
),

F37 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F37'
),

F38 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F38'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F35',

      F33.Tonelaje
    + F38.Tonelaje
    - F37.Tonelaje,

    0.0

FROM F33
CROSS JOIN F37
CROSS JOIN F38;
/* ================================================================
   F34 - TRANSFERENCIA / AJUSTE PAD DUMP
   ----------------------------------------------------------------
   Convencion actual del modelo:

       F34 = 0
       Ley F34 = 0 %
       CuF34 = 0

   No existe una corriente operacional asociada actualmente.
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
VALUES
(
    'F34',
    0.0,
    0.0
);
/* ================================================================
   F32 - DESCARTE MINERAL LIXIVIADO PAD DUMP
   ----------------------------------------------------------------
   Actualmente no existe fuente operacional disponible y trazable.

   Convencion vigente:
       F32     = 0
       Ley F32 = 0 %
       CuF32   = 0
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
VALUES
(
    'F32',
    0.0,
    0.0
);

/* ================================================================
   F36 - VARIACION INVENTARIO CU PAD DUMP MINERAL
   ----------------------------------------------------------------
   Balance de masa nodo solido:

       F30 + F31 + F34 = F32 + F36 + F33

   Actualmente:
       F30 = 0
       F31 = 0
       F32 = 0
       F34 = 0

   Por lo tanto:

       F36 = -F33

   Balance de cobre:

       CuF36 = -CuF33

   Como F33 representa directamente cobre fino:
       CuF33 = F33

   entonces:
       F36   = -F33
       CuF36 = -F33
       Ley36 = 100 %

   Si F33 = 0:
       F36   = 0
       Ley36 = 0
================================================================ */

;WITH F33 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #flujos_resultado

    WHERE codigo_flujo = 'F33'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F36',

    -F33.Tonelaje,

    CASE
        WHEN F33.Tonelaje = 0
            THEN 0.0
        ELSE 100.0
    END

FROM F33;

/* ================================================================
   F40 / F42 - REFINO HACIA AGLOMERADO DISTRIBUIDO POR PAD
   ----------------------------------------------------------------
   Relación:
       F40 -> PAD1 -> proporción de F15
       F42 -> PAD2 -> proporción de F14

   IMPORTANTE:
       - NO se recalculan F14/F15.
       - Se consumen directamente desde #flujos_resultado.
       - Así F40/F42 heredan exactamente la misma lógica validada
         de masa, humedad, CuT y fecha operacional.
================================================================ */

;WITH Base_F1415 AS
(
    SELECT
        MAX
        (
            CASE
                WHEN codigo_flujo = 'F14'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F14_TMS,

        MAX
        (
            CASE
                WHEN codigo_flujo = 'F15'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F15_TMS

    FROM #flujos_resultado

    WHERE codigo_flujo IN ('F14', 'F15')
),

Proporcion AS
(
    SELECT
        F14_TMS,
        F15_TMS,

        CASE
            /* Si falta una de las bases, no inventar proporción */
            WHEN F14_TMS IS NULL
              OR F15_TMS IS NULL
                THEN NULL

            WHEN F14_TMS + F15_TMS = 0
                THEN 0

            ELSE
                F14_TMS
                / NULLIF(F14_TMS + F15_TMS, 0)
        END AS Prop_F14,

        CASE
            WHEN F14_TMS IS NULL
              OR F15_TMS IS NULL
                THEN NULL

            WHEN F14_TMS + F15_TMS = 0
                THEN 0

            ELSE
                F15_TMS
                / NULLIF(F14_TMS + F15_TMS, 0)
        END AS Prop_F15

    FROM Base_F1415
),

Total_Refino_Aglomerado AS
(
    SELECT
        /* ========================================================
           Volumen total de refino hacia aglomerado

           m3/h * 24 h/día
           ======================================================== */
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
        ) AS Total_Ton,

        /* ========================================================
           Se mantiene por ahora la lógica vigente de ley.
           No se modifica en este cambio.
           ======================================================== */
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
            *
            COALESCE(
                t.refino_oxidos_aglomerado_cu_tambor_ad100_g_l,
                0
            )
        )
        /
        NULLIF
        (
            SUM
            (
                (
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                        0
                    )
                    +
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                        0
                    )
                )
                * 24.0
            ),
            0
        )
        / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.insumos_area_humeda_flujos AS t

    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)

/* ================================================================
   F40 -> PAD1 / F15
================================================================ */

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F40',

    CASE
        WHEN p.Prop_F15 IS NULL
            THEN NULL

        ELSE
            COALESCE(r.Total_Ton, 0)
            * p.Prop_F15
    END,

    COALESCE(r.Ley_Cu, 0)

FROM Total_Refino_Aglomerado AS r
CROSS JOIN Proporcion AS p;


/* ================================================================
   F42 -> PAD2 / F14
================================================================ */

;WITH Base_F1415 AS
(
    SELECT
        MAX(
            CASE
                WHEN codigo_flujo = 'F14'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F14_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F15'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F15_TMS

    FROM #flujos_resultado

    WHERE codigo_flujo IN ('F14', 'F15')
),

Proporcion AS
(
    SELECT
        CASE
            WHEN F14_TMS IS NULL
              OR F15_TMS IS NULL
                THEN NULL

            WHEN F14_TMS + F15_TMS = 0
                THEN 0

            ELSE
                F14_TMS
                / NULLIF(F14_TMS + F15_TMS, 0)
        END AS Prop_F14

    FROM Base_F1415
),

Total_Refino_Aglomerado AS
(
    SELECT
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
        ) AS Total_Ton,

        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
            *
            COALESCE(
                t.refino_oxidos_aglomerado_cu_tambor_ad100_g_l,
                0
            )
        )
        /
        NULLIF
        (
            SUM
            (
                (
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                        0
                    )
                    +
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                        0
                    )
                )
                * 24.0
            ),
            0
        )
        / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.insumos_area_humeda_flujos AS t

    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F42',

    CASE
        WHEN p.Prop_F14 IS NULL
            THEN NULL

        ELSE
            COALESCE(r.Total_Ton, 0)
            * p.Prop_F14
    END,

    COALESCE(r.Ley_Cu, 0)

FROM Total_Refino_Aglomerado AS r
CROSS JOIN Proporcion AS p;
-- F43
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES
    ('F43',0,0);

/* ================================================================
   F39 / F41 / F44 / F45 / F46
   RIEGO A PARCELAS CLASIFICADO POR NATURALEZA DE SOLUCION
   ----------------------------------------------------------------

   Fuente:
       inventar_SpcHidr.v_riego_parcelas_origen

   Mapeo:

       OX + REFINO   -> F39
       OX + ILS      -> F41
       OX + DPLS     -> F46

       SULF + REFINO -> F44
       SULF + ILS    -> F45

   Concentraciones:

       F39 -> conc_cu.oxidos_refino_cu
       F41 -> conc_cu.oxidos_ils_a_piscina_cu
       F46 -> conc_cu.dump_dpls_cu

       F44 -> conc_cu.sulfuros_refino_cu
       F45 -> conc_cu.sulfuros_ils_a_piscina_cu

   Integracion:
       caudal_riego [m3/h]
       x duración real del intervalo [h]

   Densidad de solución:
       1 t/m3

   Conversión ley:
       g/L / 10 = % Cu
================================================================ */

;WITH Configuracion AS
(
    SELECT 'F39' AS codigo_flujo, 'OX' AS pila_codigo, 'REFINO' AS origen_riego
    UNION ALL
    SELECT 'F41', 'OX',   'ILS'
    UNION ALL
    SELECT 'F46', 'OX',   'DPLS'
    UNION ALL
    SELECT 'F44', 'SULF', 'REFINO'
    UNION ALL
    SELECT 'F45', 'SULF', 'ILS'
),

/* ================================================================
   Concentraciones diarias

   Se consolida por fecha para impedir multiplicación de filas
   si conc_cu contiene más de un registro para un mismo día.
================================================================ */
Concentraciones AS
(
    SELECT
        CAST(c.fecha_registro AS date) AS Fecha,

        AVG(
            TRY_CONVERT(float, c.oxidos_refino_cu)
        ) AS Cu_Refino_Ox,

        AVG(
            TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)
        ) AS Cu_ILS_Ox,

        AVG(
            TRY_CONVERT(float, c.dump_dpls_cu)
        ) AS Cu_DPLS,

        AVG(
            TRY_CONVERT(float, c.sulfuros_refino_cu)
        ) AS Cu_Refino_Sulf,

        AVG(
            TRY_CONVERT(float, c.sulfuros_ils_a_piscina_cu)
        ) AS Cu_ILS_Sulf

    FROM inventar_SpcHidr.conc_cu AS c

    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

    GROUP BY
        CAST(c.fecha_registro AS date)
),

/* ================================================================
   Caudal de cada parcela integrado por duración real
================================================================ */
Riego_Base AS
(
    SELECT
        CAST(v.fecha_registro AS date) AS Fecha,

        UPPER(
            LTRIM(RTRIM(v.pila_codigo))
        ) AS pila_codigo,

        UPPER(
            LTRIM(RTRIM(v.origen_riego))
        ) AS origen_riego,

        TRY_CONVERT(float, v.caudal_riego)
        *
        (
            DATEDIFF_BIG
            (
                SECOND,
                v.fecha_registro,
                v.intervalo_fin
            )
            / 3600.0
        ) AS Volumen

    FROM inventar_SpcHidr.v_riego_parcelas_origen AS v

    WHERE CAST(v.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND v.intervalo_fin > v.fecha_registro

      AND UPPER(
              LTRIM(RTRIM(ISNULL(v.estado_operacional,'')))
          ) = 'ACTIVO'

      AND TRY_CONVERT(float, v.caudal_riego) >= 0
),

/* ================================================================
   Asignar concentración según PAD + naturaleza
================================================================ */
Riego_Con_Ley AS
(
    SELECT
        r.Fecha,
        r.pila_codigo,
        r.origen_riego,
        r.Volumen,

        CASE

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'REFINO'
                THEN c.Cu_Refino_Ox

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'ILS'
                THEN c.Cu_ILS_Ox

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'DPLS'
                THEN c.Cu_DPLS

            WHEN r.pila_codigo = 'SULF'
             AND r.origen_riego = 'REFINO'
                THEN c.Cu_Refino_Sulf

            WHEN r.pila_codigo = 'SULF'
             AND r.origen_riego = 'ILS'
                THEN c.Cu_ILS_Sulf

            ELSE NULL

        END AS Cu_g_L

    FROM Riego_Base AS r

    LEFT JOIN Concentraciones AS c
        ON c.Fecha = r.Fecha
),

Resumen AS
(
    SELECT
        pila_codigo,
        origen_riego,

        SUM(Volumen) AS Tonelaje,

        SUM
        (
            CASE
                WHEN Volumen > 0
                 AND Cu_g_L IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Registros_Sin_Ley,

        SUM
        (
            CASE
                WHEN Cu_g_L IS NOT NULL
                THEN Volumen * Cu_g_L
            END
        ) AS Suma_Cu_Ponderada,

        SUM
        (
            CASE
                WHEN Cu_g_L IS NOT NULL
                THEN Volumen
            END
        ) AS Volumen_Con_Ley

    FROM Riego_Con_Ley

    WHERE origen_riego IN ('REFINO', 'ILS', 'DPLS')

    GROUP BY
        pila_codigo,
        origen_riego
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)

SELECT
    cfg.codigo_flujo,

    CAST(
        COALESCE(r.Tonelaje, 0)
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST
    (
        CASE

            /* No existe ese tipo de riego durante el período */
            WHEN COALESCE(r.Tonelaje,0) = 0
                THEN 0

            /* Hay masa real pero falta concentración:
               no inventar ley */
            WHEN COALESCE(r.Registros_Sin_Ley,0) > 0
                THEN NULL

            ELSE
                (
                    r.Suma_Cu_Ponderada
                    /
                    NULLIF(r.Volumen_Con_Ley,0)
                )
                / 10.0
        END

        AS decimal(18,6)
    ) AS Ley_Cu

FROM Configuracion AS cfg

LEFT JOIN Resumen AS r
    ON  r.pila_codigo = cfg.pila_codigo
    AND r.origen_riego = cfg.origen_riego;
/* ================================================================
   F58 - PERDIDA POR EVAPORACION PAD SULFUROS
   ----------------------------------------------------------------
   Criterio vigente:
       F58 = 5 % de (F44 + F45)

   Se mantiene temporalmente el factor fijo de 5 %, pero F58
   queda como corriente explicita del balance.

   Ley Cu = 0 %
================================================================ */

;WITH F44 AS
(
    SELECT COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F44'
),
F45 AS
(
    SELECT COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F45'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F58',
    (F44.Tonelaje + F45.Tonelaje) * 0.05,
    0
FROM F44
CROSS JOIN F45;

/* ================================================================
   F68 - PERDIDA POR EVAPORACION PAD OXIDOS
   ----------------------------------------------------------------
   Criterio vigente:
       F68 = 5 % de (F39 + F41 + F43 + F46)

   Se mantiene temporalmente el factor fijo de 5 %, pero F68
   queda como corriente explicita del balance.

   Ley Cu = 0 %
================================================================ */

;WITH F39 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F39'
),
F41 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F41'
),
F43 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F43'
),
F46 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F46'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F68',
    (F39.Tonelaje + F41.Tonelaje + F43.Tonelaje + F46.Tonelaje) * 0.05,
    0.0
FROM F39
CROSS JOIN F41
CROSS JOIN F43
CROSS JOIN F46;
/* ================================================================
   F48 - INGRESO A PISCINA PLS OXIDOS
   ----------------------------------------------------------------
   Balance:

       F39 + F43 + F41 + F46 = F48 + F68

   Despejando:

       F48 = F39 + F43 + F41 + F46 - F68

   F68 representa explicitamente la perdida por evaporacion.

   IMPORTANTE:
       - Se elimina el antiguo factor * 0.95 de F48.
       - Se mantiene sin cambios la fuente actual de Ley Cu:
             riego_concentrados_oxido.ingreso_piscina_pls_cu_pp
       - El flujo diario bruto sigue utilizandose solamente para
         ponderar la concentracion.
================================================================ */

;WITH Flujo_Base_Diario AS
(
    SELECT
        CAST(f.fecha_registro AS date) AS Fecha,

        (
            COALESCE(f.parcela_01,0)
          + COALESCE(f.parcela_02,0)
          + COALESCE(f.parcela_03,0)
          + COALESCE(f.parcela_04,0)
          + COALESCE(f.parcela_05,0)
          + COALESCE(f.parcela_06,0)
          + COALESCE(f.parcela_07,0)
          + COALESCE(f.parcela_08,0)
          + COALESCE(f.parcela_09,0)
          + COALESCE(f.parcela_10,0)
          + COALESCE(f.parcela_11,0)
          + COALESCE(f.parcela_12,0)
          + COALESCE(f.parcela_13,0)
          + COALESCE(f.parcela_14,0)
          + COALESCE(f.parcela_15,0)
          + COALESCE(f.parcela_16,0)
          + COALESCE(f.parcela_17,0)
          + COALESCE(f.parcela_18,0)
          + COALESCE(f.parcela_19,0)
          + COALESCE(f.parcela_20,0)
          + COALESCE(f.parcela_21,0)
          + COALESCE(f.parcela_22,0)
          + COALESCE(f.parcela_23,0)
          + COALESCE(f.parcela_24,0)
          + COALESCE(f.parcela_25,0)
          + COALESCE(f.parcela_26,0)
          + COALESCE(f.parcela_27,0)
          + COALESCE(f.parcela_28,0)
          + COALESCE(f.parcela_29,0)
          + COALESCE(f.parcela_30,0)
          + COALESCE(f.parcela_31,0)
          + COALESCE(f.parcela_32,0)
        ) * 24.0 AS Flujo_Base_Dia

    FROM inventar_SpcHidr.flujos_reales_oxido AS f

    WHERE CAST(f.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),

Ley_Diaria AS
(
    SELECT
        CAST(p.fecha_registro AS date) AS Fecha,
        NULLIF(p.ingreso_piscina_pls_cu_pp, 0) AS Cu_g_L

    FROM inventar_SpcHidr.riego_concentrados_oxido AS p

    WHERE CAST(p.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),

Ley_F48 AS
(
    SELECT
        COALESCE
        (
            SUM
            (
                CASE
                    WHEN l.Cu_g_L IS NOT NULL
                    THEN f.Flujo_Base_Dia * l.Cu_g_L
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN l.Cu_g_L IS NOT NULL
                        THEN f.Flujo_Base_Dia
                    END
                ),
                0
            ),
            0
        ) / 10.0 AS Ley_Cu

    FROM Flujo_Base_Diario AS f

    INNER JOIN Ley_Diaria AS l
        ON l.Fecha = f.Fecha
),

Flujos AS
(
    SELECT
        MAX(CASE
                WHEN codigo_flujo = 'F39'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F39,

        MAX(CASE
                WHEN codigo_flujo = 'F41'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F41,

        MAX(CASE
                WHEN codigo_flujo = 'F43'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F43,

        MAX(CASE
                WHEN codigo_flujo = 'F46'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F46,

        MAX(CASE
                WHEN codigo_flujo = 'F68'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F68

    FROM #flujos_resultado

    WHERE codigo_flujo IN
    (
        'F39',
        'F41',
        'F43',
        'F46',
        'F68'
    )
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F48',

      COALESCE(f.F39,0)
    + COALESCE(f.F41,0)
    + COALESCE(f.F43,0)
    + COALESCE(f.F46,0)
    - COALESCE(f.F68,0),

    COALESCE(l.Ley_Cu,0)

FROM Flujos AS f
CROSS JOIN Ley_F48 AS l;
--F49
;WITH flujo_f49 AS (
    SELECT
        CAST(r.fecha_registro AS date) AS fecha,
        COALESCE(r.bleed, 0) * 24.0 AS flujo_ton_dia
    FROM inventar_SpcHidr.riego_bleed r
    WHERE CAST(r.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
ley_f49 AS (
    SELECT
        CAST(p.fecha_registro AS date) AS fecha,
        NULLIF(p.bleed_cu_pp, 0) AS cu_g_l
    FROM inventar_SpcHidr.riego_concentrados_sulfuro p
    WHERE CAST(p.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_ton_dia,
        l.cu_g_l
    FROM flujo_f49 f
    INNER JOIN ley_f49 l
        ON f.fecha = l.fecha
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F49',
    COALESCE(SUM(flujo_ton_dia), 0),

    COALESCE(
        SUM(
            CASE
                WHEN cu_g_l IS NOT NULL
                THEN flujo_ton_dia * cu_g_l
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN cu_g_l IS NOT NULL
                    THEN flujo_ton_dia
                END
            ),
            0
        ),
        0
    ) / 10.0
FROM base;
/* ================================================================
   F50 - PLS SULFUROS HACIA SX
   ----------------------------------------------------------------
   Balance:

       F44 + F45 = F50 + F49 + F58

   Despejando:

       F50 = F44 + F45 - F58 - F49

   F58 representa explicitamente la perdida por evaporacion.

   IMPORTANTE:
       - Se elimina el antiguo factor F44 * 0.95.
       - La fuente de Ley Cu de F50 se mantiene sin cambios.
================================================================ */

;WITH F44 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F44'
),

F49 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F49'
),

F58 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F58'
),
F45 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float,Tonelaje),
            0
        ) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F45'
),

Ley_F50 AS
(
    SELECT
        COALESCE(
            AVG(c.sulfuros_pls_a_sx_cu),
            0
        ) / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.conc_cu AS c

    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F50',

      F44.Tonelaje
    + F45.Tonelaje
    - F58.Tonelaje
    - F49.Tonelaje,

    COALESCE(l.Ley_Cu,0)

FROM F44
CROSS JOIN F45
CROSS JOIN F49
CROSS JOIN F58
CROSS JOIN Ley_F50 AS l;

-- F52 - Refino hacia DUMP
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_refino_dump_m3h
-- Concentración:
--   conc_cu.oxidos_refino_cu

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_refino_dump_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.oxidos_refino_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F52',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;
    -- F56
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F56',0,0);
    -- F57
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
      'F57',
      COALESCE(Tonelaje,0) * 0.07,
      0.0
    FROM #tmp_f18_oficial;

    -- F59
    -- Agua hacia Refino Sulfuros
    --
    -- Fuente anterior:
    --   tags_sx_ew.agua_refino_sulf_m3h
    --   Granularidad: horaria
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.agua_refino_sulfuros_flujo_m3h
    --   Granularidad: diaria
    --
    -- Integracion temporal:
    --   m3/h * 24 h/dia = m3/dia

;WITH base_f59 AS (
    SELECT
        COALESCE(t.agua_refino_sulfuros_flujo_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F59',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f59;

    -- F60
    ;WITH volumen_inicial AS (
        SELECT TOP 1 COALESCE(i.volumen_ref_sulfuros, 0) * 1.0 AS TMS_Inicial
        FROM inventar_SpcHidr.inv_sol_sulfuros i
        WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
        ORDER BY CAST(i.fecha_registro AS date) ASC
    ),
volumen_final AS
(
    SELECT TOP 1
        COALESCE(i.volumen_ref_sulfuros, 0) AS TMS_Final

    FROM inventar_SpcHidr.inv_sol_sulfuros i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

    ORDER BY i.fecha_registro DESC
),
    ley_inicial AS (
        SELECT TOP 1 COALESCE(c.sulfuros_refino_cu, 0) AS Ley_i_gL
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
        ORDER BY CAST(c.fecha_registro AS date) ASC
    ),
ley_final AS
(
    SELECT TOP 1
        COALESCE(c.sulfuros_refino_cu, 0) AS Ley_f_gL

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

    ORDER BY c.fecha_registro DESC
)
    INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT
        'F60',
        vi.TMS_Inicial,
        li.Ley_i_gL / 10.0,
        vf.TMS_Final,
        lf.Ley_f_gL / 10.0,
        (vf.TMS_Final - vi.TMS_Inicial),
        COALESCE((((vf.TMS_Final * lf.Ley_f_gL) - (vi.TMS_Inicial * li.Ley_i_gL)) / NULLIF((vf.TMS_Final - vi.TMS_Inicial),0)) / 10.0, 0)
    FROM volumen_inicial vi
    CROSS JOIN volumen_final vf
    CROSS JOIN ley_inicial li
    CROSS JOIN ley_final lf;
    -- F61 (evaporacion Refino Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F61'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F61', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
-- F55 = F43 + F44 + F60 + F61 - F59
-- Se utilizan subconsultas escalares para que F55 se inserte
-- aunque alguno de los flujos anteriores no tenga registro.
INSERT INTO #flujos_resultado (
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F55',

    COALESCE(
        (
            SELECT Tonelaje
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F43'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F44'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F60'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F61'
        ),
        0
    )
    -
    COALESCE(
        (
            SELECT Tonelaje
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F59'
        ),
        0
    ),

    COALESCE(
        (
            SELECT Ley_Cu
            FROM #flujos_resultado
            WHERE codigo_flujo = 'F44'
        ),
        0
    );

    -- F62 (evaporacion ILS Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F62'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F62', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    -- F63
-- Inventario de solución ILS Sulfuros
--
-- Volumen:
--   inv_sol_sulfuros.volumen_ils_sulfuros
--
-- Concentración:
--   conc_cu.sulfuros_ils_a_piscina_cu
--
-- Inventario diario: no requiere integración temporal.

;WITH volumen_inicial AS (
    SELECT TOP 1
        COALESCE(i.volumen_ils_sulfuros, 0) AS TMS_Inicial
    FROM inventar_SpcHidr.inv_sol_sulfuros i
    WHERE CAST(i.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    ORDER BY i.fecha_registro ASC
),
volumen_final AS
(
    SELECT TOP 1
        COALESCE(i.volumen_ils_sulfuros, 0) AS TMS_Final

    FROM inventar_SpcHidr.inv_sol_sulfuros i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

    ORDER BY i.fecha_registro DESC
),
ley_inicial AS (
    SELECT TOP 1
        COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_i_gL
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    ORDER BY c.fecha_registro ASC
),
ley_final AS
(
    SELECT TOP 1
        COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_f_gL

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

    ORDER BY c.fecha_registro DESC
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F63',

    vi.TMS_Inicial,
    li.Ley_i_gL / 10.0,

    vf.TMS_Final,
    lf.Ley_f_gL / 10.0,

    vf.TMS_Final - vi.TMS_Inicial,

    COALESCE(
        (
            (vf.TMS_Final * lf.Ley_f_gL)
          - (vi.TMS_Inicial * li.Ley_i_gL)
        )
        /
        NULLIF(
            vf.TMS_Final - vi.TMS_Inicial,
            0
        )
        / 10.0,
        0
    )

FROM volumen_inicial vi
CROSS JOIN volumen_final vf
CROSS JOIN ley_inicial li
CROSS JOIN ley_final lf;
/* ================================================================
   F51 - SOLUCION PLS SULFUROS -> ILS SULFUROS
   ----------------------------------------------------------------
   Balance piscina ILS Sulfuros:

       F51 = F45 + F62 + F63

   F45 = salida ILS hacia riego
   F62 = evaporacion
   F63 = delta inventario ILS

   Cobre:
       CuF51 = CuF45 + CuF63
       F62 no transporta Cu
================================================================ */

;WITH F45 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F45'
),
F62 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F62'
),
F63 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F63'
),
Calculo AS
(
    SELECT
          F45.Tonelaje
        + F62.Tonelaje
        + F63.Tonelaje AS Tonelaje_F51,

        (
            F45.Tonelaje * F45.Ley_Cu / 100.0
        )
        +
        (
            F63.Tonelaje * F63.Ley_Cu / 100.0
        ) AS FCu_F51

    FROM F45
    CROSS JOIN F62
    CROSS JOIN F63
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F51',

    Tonelaje_F51,

    CASE
        WHEN Tonelaje_F51 = 0 THEN 0
        ELSE FCu_F51 / NULLIF(Tonelaje_F51,0) * 100.0
    END

FROM Calculo;
    -- F64 (evaporacion PLS Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F64'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F64', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
/* ================================================================
   F65 - VARIACION INVENTARIO PLS SULFUROS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1 = @fecha_fin + 1 dia

   Volumen:
       inv_sol_sulfuros.volumen_pls_sulfuros

   Concentracion:
       conc_cu.sulfuros_pls_a_sx_cu
================================================================ */

;WITH base_f65 AS
(
    SELECT

        /* Inventario inicial */
        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_sulfuros)

            FROM inventar_SpcHidr.inv_sol_sulfuros AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        /* Inventario final D+1 */
        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_sulfuros)

            FROM inventar_SpcHidr.inv_sol_sulfuros AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        /* Ley inicial */
        (
            SELECT TOP 1
                TRY_CONVERT(float, c.sulfuros_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        /* Ley final D+1 */
        (
            SELECT TOP 1
                TRY_CONVERT(float, c.sulfuros_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F65',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f65;
-- F66
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F66',0,0);
-- F67
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F67',
    COALESCE(Tonelaje,0) * 0.07,
    0.0
FROM #tmp_f19_oficial;

/* ================================================================
   F69 - VARIACION INVENTARIO POND DPLS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_pond_dpls

   Concentracion:
       conc_cu.dump_dpls_cu
================================================================ */

;WITH base_f69 AS
(
    SELECT

        /* Inventario inicial */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, i.volumen_pond_dpls)
                )

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio
        ) AS TMS_Inicial,


        /* Inventario final D+1 */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, i.volumen_pond_dpls)
                )

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1
        ) AS TMS_Final,


        /* Ley inicial */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, c.dump_dpls_cu)
                )

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio
        ) AS Ley_i_gL,


        /* Ley final D+1 */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, c.dump_dpls_cu)
                )

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1
        ) AS Ley_f_gL
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F69',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (
                    TMS_Final
                    * Ley_f_gL / 10.0
                )
                -
                (
                    TMS_Inicial
                    * Ley_i_gL / 10.0
                )
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
    END

FROM base_f69;
-- F71 (evaporacion Pond DPLS*: perdida_estimada_m3_dia x dias del periodo)
;WITH ev AS (
    SELECT perdida_estimada_m3_dia
    FROM inventar_SpcHidr.tasa_evaporacion
    WHERE codigo_flujo = 'F71'
)
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F71',
    COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo,
    0.0
FROM ev;
/* ================================================================
   F53 - DPLS HACIA PLS OX
   ----------------------------------------------------------------
   Balance de masa nodo DPLS:

       F37 = F69 + F53 + F71 + F46

   Despejando:

       F53 = F37 - F69 - F71 - F46

   Donde:
       F37 = ingreso desde PAD DUMP
       F69 = variacion inventario DPLS
       F71 = perdida por evaporacion
       F46 = salida hacia PAD Ox
       F53 = salida hacia PLS Ox

   Balance de cobre:

       CuF37 = CuF69 + CuF53 + CuF71 + CuF46

   Como F71 corresponde a evaporacion:
       CuF71 = 0

   Entonces:

       CuF53 = CuF37 - CuF69 - CuF46

   IMPORTANTE:
       - Se elimina el antiguo factor fijo 0.95.
       - La evaporacion queda representada explicitamente por F71.
       - No se fuerza F53 >= 0.
================================================================ */

;WITH F37 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F37'
),

F46 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F46'
),

F69 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F69'
),

F71 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F71'
),

Calculo AS
(
    SELECT

        /* ========================================================
           MASA
           ======================================================== */
          F37.Tonelaje
        - F69.Tonelaje
        - F71.Tonelaje
        - F46.Tonelaje
            AS Tonelaje_F53,


        /* ========================================================
           COBRE FINO
           ======================================================== */
        (
            F37.Tonelaje
            * F37.Ley_Cu
            / 100.0
        )
        -
        (
            F69.Tonelaje
            * F69.Ley_Cu
            / 100.0
        )
        -
        (
            F46.Tonelaje
            * F46.Ley_Cu
            / 100.0
        )
            AS FCu_F53

    FROM F37
    CROSS JOIN F46
    CROSS JOIN F69
    CROSS JOIN F71
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F53',

    Tonelaje_F53,

    CASE
        WHEN Tonelaje_F53 = 0
         AND FCu_F53 = 0
            THEN 0

        WHEN Tonelaje_F53 = 0
            THEN NULL

        ELSE
            FCu_F53
            / NULLIF(Tonelaje_F53, 0)
            * 100.0
    END

FROM Calculo;
-- F70
;WITH inv_i AS (
    SELECT
        COALESCE(AVG(i.volumen_refino_dump), 0) AS inventario_inicial
    FROM inventar_SpcHidr.inv_sol_oxidos i
    WHERE CAST(i.fecha_registro AS date) = @fecha_inicio
),
inv_f AS
(
    SELECT
        COALESCE(AVG(i.volumen_refino_dump), 0)
        AS inventario_final

    FROM inventar_SpcHidr.inv_sol_oxidos i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1
),
ley_i AS (
    SELECT
        COALESCE(AVG(c.dump_feed_cu), 0) AS ley_inicial
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date) = @fecha_inicio
),
ley_f AS
(
    SELECT
        COALESCE(AVG(c.dump_feed_cu), 0)
        AS ley_final

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial, Ley_Cu_1,
    TMS_Final,   Ley_Cu_2,
    Tonelaje,    Ley_Cu
)
SELECT
    'F70',
    COALESCE(inv_i.inventario_inicial, 0),
    COALESCE(ley_i.ley_inicial, 0) / 10.0,
    COALESCE(inv_f.inventario_final, 0),
    COALESCE(ley_f.ley_final, 0) / 10.0,
    COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0),
    CASE
        WHEN (COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0)) = 0 THEN 0
        ELSE (
            (
                COALESCE(inv_f.inventario_final, 0) * (COALESCE(ley_f.ley_final, 0) / 10.0)
            ) -
            (
                COALESCE(inv_i.inventario_inicial, 0) * (COALESCE(ley_i.ley_inicial, 0) / 10.0)
            )
        ) / NULLIF(
            COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0),
            0
        )
    END
FROM inv_i
CROSS JOIN inv_f
CROSS JOIN ley_i
CROSS JOIN ley_f;

-- F72 (evaporacion Refino Dump: perdida_estimada_m3_dia x dias del periodo)
;WITH ev AS (
    SELECT perdida_estimada_m3_dia
    FROM inventar_SpcHidr.tasa_evaporacion
    WHERE codigo_flujo = 'F72'
)
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F72',
    COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo,
    0.0
FROM ev;
/* ================================================================
   F73 - VARIACION INVENTARIO REFINO OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_refino_oxidos

   Concentracion:
       conc_cu.oxidos_refino_cu

   Se mantiene la metodologia vigente de Ley_Cu:
       promedio de concentracion inicial y final
================================================================ */

;WITH base_f73 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F73',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                Ley_i_gL + Ley_f_gL
            )
            / 2.0
            / 10.0
    END

FROM base_f73;

  -- F74 (evaporacion Refino Oxidos: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F74'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F74', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
		
-- F54
;WITH f39 AS (
        SELECT Tonelaje, Ley_Cu
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F39'
     ),
     f40 AS (
        SELECT Tonelaje
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F40'
     ),
     f42 AS (
        SELECT Tonelaje
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F42'
     ),
     f52 AS (
        SELECT Tonelaje
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F52'
     ),
     f73 AS (
        SELECT Tonelaje
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F73'
     ),
		  f74 AS (
        SELECT Tonelaje
        FROM #flujos_resultado
        WHERE codigo_flujo = 'F74'
     )
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F54',
    (COALESCE(f39.Tonelaje,0)
   + COALESCE(f40.Tonelaje,0)
   + COALESCE(f42.Tonelaje,0)
   + COALESCE(f52.Tonelaje,0)
   + COALESCE(f73.Tonelaje,0)
   + COALESCE(f74.Tonelaje,0)),
    COALESCE(f39.Ley_Cu,0)
FROM f39
CROSS JOIN f40
CROSS JOIN f42
CROSS JOIN f52
CROSS JOIN f73
CROSS JOIN f74;
  
    -- F75 (evaporacion ILS Oxido: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F75'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F75', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
/* ================================================================
   F76 - VARIACION INVENTARIO ILS OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_ils_oxido

   Concentracion:
       conc_cu.oxidos_ils_a_piscina_cu
================================================================ */

;WITH base_f76 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_ils_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_ils_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F76',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f76;
/* ================================================================
   F47 - SOLUCION PLS OXIDOS -> ILS OXIDOS

       F47 = F41 + F75 + F76
================================================================ */

;WITH F41 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F41'
),
F75 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F75'
),
F76 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F76'
),
Calculo AS
(
    SELECT
          F41.Tonelaje
        + F75.Tonelaje
        + F76.Tonelaje AS Tonelaje_F47,

        (
            F41.Tonelaje * F41.Ley_Cu / 100.0
        )
        +
        (
            F76.Tonelaje * F76.Ley_Cu / 100.0
        ) AS FCu_F47

    FROM F41
    CROSS JOIN F75
    CROSS JOIN F76
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F47',

    Tonelaje_F47,

    CASE
        WHEN Tonelaje_F47 = 0 THEN 0
        ELSE FCu_F47 / NULLIF(Tonelaje_F47,0) * 100.0
    END

FROM Calculo;
    -- F77 (evaporacion PLS Oxido: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F77'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F77', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
/* ================================================================
   F78 - VARIACION INVENTARIO PLS OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_pls_oxido

   Concentracion:
       conc_cu.oxidos_pls_a_sx_cu
================================================================ */

;WITH base_f78 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F78',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f78;
    -- F79-F82
    ;WITH masico_f79 AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_a_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f79 AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F79', m.Tonelaje, l.Ley_Cu
    FROM masico_f79 m
    CROSS JOIN ley_f79 l;
    ;WITH masico_f80 AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_b_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f80 AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F80', m.Tonelaje, l.Ley_Cu
    FROM masico_f80 m
    CROSS JOIN ley_f80 l;
    ;WITH masico_f81 AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_c_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f81 AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F81', m.Tonelaje, l.Ley_Cu
    FROM masico_f81 m
    CROSS JOIN ley_f81 l;
    ;WITH masico_f82 AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_d_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f82 AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F82', m.Tonelaje, l.Ley_Cu
    FROM masico_f82 m
    CROSS JOIN ley_f82 l;
    -- F83-F86
    ;WITH masico_f83 AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_a_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f83 AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F83', m.Tonelaje, l.Ley_Cu
    FROM masico_f83 m
    CROSS JOIN ley_f83 l;
    ;WITH masico_f84 AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_b_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f84 AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F84', m.Tonelaje, l.Ley_Cu
    FROM masico_f84 m
    CROSS JOIN ley_f84 l;
    ;WITH masico_f85 AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_c_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f85 AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F85', m.Tonelaje, l.Ley_Cu
    FROM masico_f85 m
    CROSS JOIN ley_f85 l;
    ;WITH masico_f86 AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_d_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f86 AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F86', m.Tonelaje, l.Ley_Cu
    FROM masico_f86 m
    CROSS JOIN ley_f86 l;
    -- F87
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F87',0,0);
    -- F88-F91
-- H2SO4 hacia SX Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.acido_sx_tren_*_m3h
--   Granularidad: horaria
--   Unidad: m3/h
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.acido_sx_tren_*_l_min
--   Granularidad: diaria
--   Unidad: L/min
--
-- Conversion:
--   L/min * 60 min/h * 24 h/dia / 1000 L/m3 * 1.84 t/m3
--   = t H2SO4/dia


-- F88 - H2SO4 Tren A
;WITH base_f88 AS (
    SELECT
        COALESCE(t.acido_sx_tren_a_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F88',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f88;


-- F89 - H2SO4 Tren B
;WITH base_f89 AS (
    SELECT
        COALESCE(t.acido_sx_tren_b_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F89',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f89;


-- F90 - H2SO4 Tren C
;WITH base_f90 AS (
    SELECT
        COALESCE(t.acido_sx_tren_c_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F90',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f90;


-- F91 - H2SO4 Tren D
;WITH base_f91 AS (
    SELECT
        COALESCE(t.acido_sx_tren_d_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F91',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f91;
-- F92-F95
-- Agua W2 hacia SX - Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.agua_sx_tren_*_m3h
--   Granularidad: horaria
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.agua_w2_tren_*_m3h
--   Granularidad: diaria
--
-- Integracion temporal:
--   m3/h * 24 h/dia = m3/dia


-- F92 - Agua W2 Tren A
;WITH base_f92 AS (
    SELECT
        COALESCE(t.agua_w2_tren_a_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F92',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f92;


-- F93 - Agua W2 Tren B
;WITH base_f93 AS (
    SELECT
        COALESCE(t.agua_w2_tren_b_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F93',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f93;


-- F94 - Agua W2 Tren C
;WITH base_f94 AS (
    SELECT
        COALESCE(t.agua_w2_tren_c_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F94',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f94;


-- F95 - Agua W2 Tren D
;WITH base_f95 AS (
    SELECT
        COALESCE(t.agua_w2_tren_d_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F95',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f95;
    -- F96-F99
;WITH masico_f96 AS (
    SELECT
        COALESCE(SUM(s.ep_tren_a_m3h), 0) * 24.0 AS Tonelaje
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
ley_f96 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F96',
    m.Tonelaje,
    l.Ley_Cu
FROM masico_f96 m
CROSS JOIN ley_f96 l;

    ;WITH masico_f97 AS (
        SELECT COALESCE(SUM(s.ep_tren_b_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f97 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F97', m.Tonelaje, l.Ley_Cu
    FROM masico_f97 m
    CROSS JOIN ley_f97 l;
    ;WITH masico_f98 AS (
        SELECT COALESCE(SUM(s.ep_tren_c_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f98 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F98', m.Tonelaje, l.Ley_Cu
    FROM masico_f98 m
    CROSS JOIN ley_f98 l;
    ;WITH masico_f99 AS (
        SELECT COALESCE(SUM(s.ep_tren_d_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f99 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F99', m.Tonelaje, l.Ley_Cu
    FROM masico_f99 m
    CROSS JOIN ley_f99 l;
-- F100
-- Electrolito Rico hacia EW
--
-- Fuente única nueva:
--   sx_ep_flujos_niveles
--
-- Caudales:
--   er_ecc1_m3h
--   er_ecc2_m3h
--   er_ecc3_m3h
--
-- Concentraciones:
--   er_ecc1_gl
--   er_ecc2_gl
--   er_ecc3_gl
--
-- Granularidad:
--   diaria
--
-- Integracion:
--   m3/h * 24 h/dia = m3/dia

;WITH base_f100 AS (
    SELECT
        CAST(s.fecha_registro AS date) AS fecha,

        (
            COALESCE(s.er_ecc1_m3h, 0)
          + COALESCE(s.er_ecc2_m3h, 0)
          + COALESCE(s.er_ecc3_m3h, 0)
        ) * 24.0 AS volumen_m3_dia,

        COALESCE(s.er_ecc1_m3h, 0) AS q1,
        COALESCE(s.er_ecc2_m3h, 0) AS q2,
        COALESCE(s.er_ecc3_m3h, 0) AS q3,

        NULLIF(s.er_ecc1_gl, 0) AS c1,
        NULLIF(s.er_ecc2_gl, 0) AS c2,
        NULLIF(s.er_ecc3_gl, 0) AS c3

    FROM inventar_SpcHidr.sx_ep_flujos_niveles s

    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F100',

    COALESCE(
        SUM(volumen_m3_dia),
        0
    ) AS Tonelaje,

    COALESCE(
        SUM(
            CASE WHEN c1 IS NOT NULL THEN q1 * c1 ELSE 0 END
          + CASE WHEN c2 IS NOT NULL THEN q2 * c2 ELSE 0 END
          + CASE WHEN c3 IS NOT NULL THEN q3 * c3 ELSE 0 END
        )
        /
        NULLIF(
            SUM(
                CASE WHEN c1 IS NOT NULL THEN q1 ELSE 0 END
              + CASE WHEN c2 IS NOT NULL THEN q2 ELSE 0 END
              + CASE WHEN c3 IS NOT NULL THEN q3 ELSE 0 END
            ),
            0
        ),
        0
    ) / 10.0 AS Ley_Cu

FROM base_f100;
-- F101
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F101', 0, 0, 0, 0, 0, 0);
--F102
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F102', 0, 0, 0, 0, 0, 0);
--F103
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F103', 0, 0, 0, 0, 0, 0);
-- F104
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES
   ('F104',0,0);
-- F105
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F105', 0, 0, 0, 0, 0, 0);
--F106
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES
   ('F106',0,0);
/* ================================================================
   F108 - VARIACION DE INVENTARIO DE COBRE COLGADO
   ----------------------------------------------------------------
   Fuente:
       inventar_SpcHidr.inventario_cobre_colgado_diario

   Campo:
       inventario_total_ton

   Metodologia:

       Inventario inicial = estado en @fecha_inicio

       Inventario final   = estado en @fecha_fin + 1 día

       F108 =
           Inventario(@fecha_fin + 1)
         - Inventario(@fecha_inicio)

   Ejemplo:
       Periodo balanceado: 01-08-2026 al 16-08-2026

       Inventario inicial: 01-08-2026
       Inventario final  : 17-08-2026

   Unidad:
       toneladas de Cu

   Ley:
       100 %

   IMPORTANTE:
       - Se utiliza @ff_mas_1, ya declarado como:
             DATEADD(DAY, 1, @fecha_fin)

       - inventario_total_ton es el inventario calculado
         por el sistema.

       - excel_total_ton se mantiene solamente como referencia.

       - No requiere integración temporal ni factor x24.
================================================================ */

;WITH base_f108 AS
(
    SELECT

        /* ========================================================
           INVENTARIO INICIAL
           Fecha = @fecha_inicio
           ======================================================== */
        (
            SELECT TOP 1
                TRY_CONVERT(
                    decimal(18,6),
                    p.inventario_total_ton
                )

            FROM inventar_SpcHidr.inventario_cobre_colgado_diario AS p

            WHERE p.fecha_operacional = @fecha_inicio

            ORDER BY
                COALESCE(
                    p.updated_at,
                    p.imported_at
                ) DESC,
                p.id_registro DESC

        ) AS Inventario_Inicial,


        /* ========================================================
           INVENTARIO FINAL
           Fecha = @fecha_fin + 1 día
           ======================================================== */
        (
            SELECT TOP 1
                TRY_CONVERT(
                    decimal(18,6),
                    p.inventario_total_ton
                )

            FROM inventar_SpcHidr.inventario_cobre_colgado_diario AS p

            WHERE p.fecha_operacional = @ff_mas_1

            ORDER BY
                COALESCE(
                    p.updated_at,
                    p.imported_at
                ) DESC,
                p.id_registro DESC

        ) AS Inventario_Final
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F108',

    Inventario_Inicial,
    100.0,

    Inventario_Final,
    100.0,

    CASE
        WHEN Inventario_Inicial IS NULL
          OR Inventario_Final IS NULL
            THEN NULL

        ELSE
            Inventario_Final
            - Inventario_Inicial
    END AS Tonelaje,

    100.0

FROM base_f108;
    -- F109
    ;WITH base_f109 AS (
        SELECT COALESCE(p.real_produccion_ton,0) AS ton
        FROM inventar_SpcHidr.produccion_catodica p
        WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F109', COALESCE(SUM(ton),0), 100.0
    FROM base_f109;
    -- F107
    ;WITH f108 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F108'),
          f109 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F109')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F107', COALESCE(f108.Tonelaje,0) + COALESCE(f109.Tonelaje,0), 100.0
    FROM f108 CROSS JOIN f109;

--F110
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F110', 0, 0, 0, 0, 0, 0);
--F111
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F111', 0, 0, 0, 0, 0, 0);
--F112
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F112', 0, 0, 0, 0, 0, 0);
--F113
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F113', 0, 0, 0, 0, 0, 0);
--F114
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu) VALUES
('F114',0,0);
-- F115
    ;WITH f109 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F109'),
         f110 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F110'),
         f111 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F111'),
         f112 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F112'),
         f113 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F113'),
         f114 AS (SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo='F114')
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F115',
        COALESCE(f109.Tonelaje,0) - COALESCE(f110.Tonelaje,0) - COALESCE(f111.Tonelaje,0) - COALESCE(f112.Tonelaje,0) - COALESCE(f113.Tonelaje,0) - COALESCE(f114.Tonelaje,0),
        100.0
    FROM f109 CROSS JOIN f110 CROSS JOIN f111 CROSS JOIN f112 CROSS JOIN f113 CROSS JOIN f114;
-- F116
-- Electrolito Pobre / retorno desde EW
--
-- Volumen:
--   igual al volumen integrado de F100
--
-- Fuente de ponderadores y concentraciones:
--   sx_ep_flujos_niveles
--
-- Ponderadores:
--   er_ecc1_m3h
--   er_ecc2_m3h
--   er_ecc3_m3h
--
-- Concentraciones EP:
--   ep_ecc1_gl
--   ep_ecc2_gl
--   ep_ecc3_gl

;WITH f100 AS (
    SELECT
        COALESCE(MAX(Tonelaje), 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F100'
),
base_f116 AS (
    SELECT
        COALESCE(s.er_ecc1_m3h, 0) AS q1,
        COALESCE(s.er_ecc2_m3h, 0) AS q2,
        COALESCE(s.er_ecc3_m3h, 0) AS q3,

        NULLIF(s.ep_ecc1_gl, 0) AS c1,
        NULLIF(s.ep_ecc2_gl, 0) AS c2,
        NULLIF(s.ep_ecc3_gl, 0) AS c3

    FROM inventar_SpcHidr.sx_ep_flujos_niveles s

    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
ley_f116 AS (
    SELECT
        COALESCE(
            SUM(
                CASE
                    WHEN c1 IS NOT NULL AND q1 <> 0
                    THEN q1 * c1
                    ELSE 0
                END
              +
                CASE
                    WHEN c2 IS NOT NULL AND q2 <> 0
                    THEN q2 * c2
                    ELSE 0
                END
              +
                CASE
                    WHEN c3 IS NOT NULL AND q3 <> 0
                    THEN q3 * c3
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN c1 IS NOT NULL AND q1 <> 0
                        THEN q1
                        ELSE 0
                    END
                  +
                    CASE
                        WHEN c2 IS NOT NULL AND q2 <> 0
                        THEN q2
                        ELSE 0
                    END
                  +
                    CASE
                        WHEN c3 IS NOT NULL AND q3 <> 0
                        THEN q3
                        ELSE 0
                    END
                ),
                0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM base_f116
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F116',
    COALESCE(f100.Tonelaje, 0),
    COALESCE(l.Ley_Cu, 0)
FROM f100
CROSS JOIN ley_f116 l;

-- F117
;WITH f96 AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F96'
),
f97 AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F97'
),
f98 AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F98'
),
f99 AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F99'
),
ley_f117 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    NULLIF(s.conc_er_ta_gl, 0) +
                    NULLIF(s.conc_er_tb_gl, 0) +
                    NULLIF(s.conc_er_tc_gl, 0) +
                    NULLIF(s.conc_er_td_gl, 0)
                )
                /
                NULLIF(
                    (CASE WHEN NULLIF(s.conc_er_ta_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_tb_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_tc_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_td_gl,0) IS NOT NULL THEN 1 ELSE 0 END),
                    0
                )
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F117',
      COALESCE(f96.Tonelaje, 0)
    + COALESCE(f97.Tonelaje, 0)
    + COALESCE(f98.Tonelaje, 0)
    + COALESCE(f99.Tonelaje, 0),
    COALESCE(l.Ley_Cu, 0)
FROM f96
CROSS JOIN f97
CROSS JOIN f98
CROSS JOIN f99
CROSS JOIN ley_f117 l;
-- F118
-- Agua W1 hacia SX - Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.agua_adasa_sx_tren_*_m3h
--   Granularidad: horaria
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.agua_w1_tren_*_m3h
--   Granularidad: diaria
--
-- Integracion temporal:
--   m3/h * 24 h/dia = m3/dia

;WITH base_f118 AS (
    SELECT
        (
            COALESCE(t.agua_w1_tren_a_m3h, 0)
          + COALESCE(t.agua_w1_tren_b_m3h, 0)
          + COALESCE(t.agua_w1_tren_c_m3h, 0)
          + COALESCE(t.agua_w1_tren_d_m3h, 0)
        ) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F118',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f118;
-- F119
INSERT INTO #flujos_resultado (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F119', 0, 0, 0, 0, 0, 0);
-- F120: flujo de agua make-up hacia la piscina Feed DUMP.
-- No existe medicion directa por flujometro, por lo que se estima por balance de masa/volumen del nodo.
-- Balance del nodo Feed DUMP:
--     Entradas = F52 + F120
--     Salidas  = F38 + F70 + F72
-- Despejando:
--     F120 = F38 + F70 + F72 - F52
-- donde:
--     F70 = variacion de inventario del nodo en el periodo
--     F72 = perdida por evaporacion (ahora calculada con la tasa de evaporacion real, ver seccion 8)
-- entonces:
--     F120 = F38 + F70 + F72 - F52
-- Si el resultado es negativo, se interpreta como que no se requiere make-up externo en el periodo,
-- dado que la entrada F52 y/o la disminucion de inventario cubren las salidas del sistema.
-- F120
;WITH f38 AS (
    SELECT Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F38'
),
f70 AS (
    SELECT Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F70'
),
f72 AS (
    SELECT Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F72'
),
f52 AS (
    SELECT Tonelaje
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F52'
)
INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F120',
    CASE
        WHEN COALESCE(f38.Tonelaje, 0) + COALESCE(f70.Tonelaje, 0) + COALESCE(f72.Tonelaje, 0) - COALESCE(f52.Tonelaje, 0) < 0
            THEN 0
        ELSE COALESCE(f38.Tonelaje, 0) + COALESCE(f70.Tonelaje, 0) + COALESCE(f72.Tonelaje, 0) - COALESCE(f52.Tonelaje, 0)
    END,
    0.0
FROM f38
CROSS JOIN f70
CROSS JOIN f72
CROSS JOIN f52;
/* ================================================================
   F23 - TRANSFERENCIA DE COBRE PAD OXIDOS
   ----------------------------------------------------------------
   Representa el cobre transferido desde el mineral hacia
   la solucion durante la lixiviacion del PAD Oxidos.

   Entradas liquidas al PAD:
       F39 = Refino
       F41 = ILS
       F43 = otra entrada de solucion contemplada por el modelo
       F46 = DPLS

   Salida liquida:
       F48 = drenaje hacia PLS Oxidos

   Balance de cobre fino:

       CuF23 =
           CuF48
         - CuF39
         - CuF41
         - CuF43
         - CuF46

   F23 ya representa toneladas de cobre fino:
       Ley_Cu = 100 %
================================================================ */

;WITH F39 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F39'
),

F41 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F41'
),

F43 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F43'
),

F46 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F46'
),

F48 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F48'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F23',

      (F48.Tonelaje * F48.Ley_Cu / 100.0)

    - (F39.Tonelaje * F39.Ley_Cu / 100.0)

    - (F41.Tonelaje * F41.Ley_Cu / 100.0)

    - (F43.Tonelaje * F43.Ley_Cu / 100.0)

    - (F46.Tonelaje * F46.Ley_Cu / 100.0),

    100.0

FROM F39
CROSS JOIN F41
CROSS JOIN F43
CROSS JOIN F46
CROSS JOIN F48;
/* ================================================================
   F24 - TRANSFERENCIA DE COBRE PAD SULFUROS
   ----------------------------------------------------------------
   Representa el cobre transferido desde el mineral hacia
   la solucion durante la lixiviacion del PAD Sulfuros.

   Entradas liquidas al PAD:
       F44 = Refino
       F45 = ILS

   Salidas liquidas:
       F49 = Bleed
       F50 = drenaje PLS Sulfuros

   Balance de cobre fino:

       CuF24 =
           CuF49
         + CuF50
         - CuF44
         - CuF45

   F58 corresponde a evaporacion:
       CuF58 = 0

   F24 ya representa toneladas de cobre fino:
       Ley_Cu = 100 %
================================================================ */

;WITH F44 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F44'
),

F45 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F45'
),

F49 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F49'
),

F50 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #flujos_resultado
    WHERE codigo_flujo = 'F50'
)

INSERT INTO #flujos_resultado
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F24',

      (F49.Tonelaje * F49.Ley_Cu / 100.0)

    + (F50.Tonelaje * F50.Ley_Cu / 100.0)

    - (F44.Tonelaje * F44.Ley_Cu / 100.0)

    - (F45.Tonelaje * F45.Ley_Cu / 100.0),

    100.0

FROM F44
CROSS JOIN F45
CROSS JOIN F49
CROSS JOIN F50;
    -- F26 = F23, con 0% de ley
    ;WITH f23 AS (
        SELECT COALESCE(Tonelaje,0) AS Tonelaje
        FROM #flujos_resultado WHERE codigo_flujo = 'F23'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F26', Tonelaje, 0.0 FROM f23;
    -- F27 = F24, con 0% de ley
    ;WITH f24 AS (
        SELECT COALESCE(Tonelaje,0) AS Tonelaje
        FROM #flujos_resultado WHERE codigo_flujo = 'F24'
    )
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F27', Tonelaje, 0.0 FROM f24;
    -------------------------------------------------------------------------
    -- 8c) F16 Y F17 POR DIFERENCIA (calculado aqui, una vez que F23/F24 ya
    --     estan disponibles con su nueva definicion en base fina)
    -------------------------------------------------------------------------
    DECLARE
        @ton_f14 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F14'), 0),
        @ley_f14 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F14'), 0),
        @ton_f21 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F21'), 0),
        @ley_f21 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F21'), 0),
        @ton_f24 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F24'), 0),
        @ley_f24 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F24'), 0),
        @ton_f15 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F15'), 0),
        @ley_f15 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F15'), 0),
        @ton_f22 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F22'), 0),
        @ley_f22 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F22'), 0),
        @ton_f23 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F23'), 0),
        @ley_f23 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F23'), 0),
        @ton_f27 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F27'), 0),
        @ley_f27 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F27'), 0),
        @ton_f26 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #flujos_resultado WHERE codigo_flujo = 'F26'), 0),
        @ley_f26 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #flujos_resultado WHERE codigo_flujo = 'F26'), 0);
    DECLARE
        @ton_f16 decimal(18,6),
        @ley_f16 decimal(18,6),
        @ton_f17 decimal(18,6),
        @ley_f17 decimal(18,6);
    SET @ton_f16 = @ton_f14 - @ton_f18 - @ton_f21;
    SET @ley_f16 = CASE
        WHEN @ton_f16 = 0 THEN 0
        ELSE ((@ton_f14 * @ley_f14) - (@ton_f18 * @ley_f18) - (@ton_f21 * @ley_f21) - (@ton_f24 * @ley_f24)) / @ton_f16
    END;
    SET @ton_f17 = @ton_f15 - @ton_f19 - @ton_f22 ;
    SET @ley_f17 = CASE
        WHEN @ton_f17 = 0 THEN 0
        ELSE ((@ton_f15 * @ley_f15) - (@ton_f19 * @ley_f19) - (@ton_f22 * @ley_f22) - (@ton_f23 * @ley_f23) ) / @ton_f17
    END;
    INSERT INTO #flujos_resultado (codigo_flujo, Tonelaje, Ley_Cu)
    VALUES
        ('F16', @ton_f16, @ley_f16),
        ('F17', @ton_f17, @ley_f17);
    -------------------------------------------------------------------------
    -- 8d) INVENTARIO INICIAL DE F16 Y F17
    -------------------------------------------------------------------------
    DECLARE
        @ton14_i decimal(18,6) = 0, @ley14_i decimal(18,6) = 0,
        @ton15_i decimal(18,6) = 0, @ley15_i decimal(18,6) = 0,
        @ton18_i decimal(18,6) = 0, @ley18_i decimal(18,6) = 0,
        @ton19_i decimal(18,6) = 0, @ley19_i decimal(18,6) = 0,
        @ton21_i decimal(18,6) = 0, @ley21_i decimal(18,6) = 0,
        @ton22_i decimal(18,6) = 0, @ley22_i decimal(18,6) = 0,
        @tms_ini_f16 decimal(18,6) = 0, @ley_ini_f16 decimal(18,6) = 0,
        @tms_ini_f17 decimal(18,6) = 0, @ley_ini_f17 decimal(18,6) = 0;
/* ================================================================
   BASE DEL DIA INICIAL PARA F16 / F17
   ----------------------------------------------------------------
   Se mantiene la intención histórica del bloque:

       @ton14_i / @ley14_i = alimentación del día inicial PAD2
       @ton15_i / @ley15_i = alimentación del día inicial PAD1

   CORRECCIONES:
       - Se elimina import_leyes_torres.
       - Se usan las mismas fuentes validadas de F12/F13/F14/F15.
       - control_apilado_diario.fecha YA es fecha operacional.
       - NO se aplica DATEADD(DAY,-1,...).

   IMPORTANTE:
       No se modifica todavía la definición posterior de
       @ton18_i / @ton19_i.
================================================================ */

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_inicio)
    )
),

TMH AS
(
    SELECT
        v.Fecha,
        x.Turno,
        x.TM,

        CASE
            WHEN ABS(COALESCE(x.TMH, 0)) > 150000
                THEN 0
            ELSE COALESCE(x.TMH, 0)
        END AS TMH

    FROM inventar_SpcHidr.v_datos_apilado_tmh_v2 AS v

    CROSS APPLY
    (
        VALUES
            ('A', 'TM1', v.TMH_CV008_A),
            ('B', 'TM1', v.TMH_CV008_B),
            ('A', 'TM2', v.TMH_CV108_A),
            ('B', 'TM2', v.TMH_CV108_B)
    ) AS x
    (
        Turno,
        TM,
        TMH
    )

    WHERE v.Fecha = @fecha_inicio
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,

        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                *
                (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                )
        END AS TMS,

        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    *
                    (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                    )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0

        END AS FCu

    FROM Base
),

Resumen_Dia AS
(
    SELECT
        /* --------------------------------------------------------
           Masa total TM1 + TM2 del día inicial
           -------------------------------------------------------- */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND Humedad IS NULL
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)
        END AS TMS_Dia,

        /* --------------------------------------------------------
           Cobre fino total del día inicial
           -------------------------------------------------------- */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND
                              (
                                  Humedad IS NULL
                                  OR CuT IS NULL
                              )
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)
        END AS FCu_Dia

    FROM Calculo
),

Pad_Dia AS
(
    SELECT
        MAX
        (
            CASE
                WHEN cad.pad_id = 2
                 AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0
                    THEN 1
                ELSE 0
            END
        ) AS PAD2_Activo,

        MAX
        (
            CASE
                WHEN cad.pad_id = 1
                 AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0
                    THEN 1
                ELSE 0
            END
        ) AS PAD1_Activo

    FROM inventar_SpcHidr.control_apilado_diario AS cad

    /* fecha YA corresponde al día operacional */
    WHERE CAST(cad.fecha AS date) = @fecha_inicio
)

SELECT
    /* ============================================================
       PAD2 -> estado inicial utilizado por F16
       ============================================================ */
    @ton14_i =
        CASE
            WHEN ISNULL(p.PAD2_Activo, 0) = 1
                THEN COALESCE(r.TMS_Dia, 0)
            ELSE 0
        END,

    @ley14_i =
        CASE
            WHEN ISNULL(p.PAD2_Activo, 0) = 0
                THEN 0

            WHEN COALESCE(r.TMS_Dia, 0) = 0
                THEN 0

            ELSE
                COALESCE(r.FCu_Dia, 0)
                / NULLIF(r.TMS_Dia, 0)
                * 100.0
        END,

    /* ============================================================
       PAD1 -> estado inicial utilizado por F17
       ============================================================ */
    @ton15_i =
        CASE
            WHEN ISNULL(p.PAD1_Activo, 0) = 1
                THEN COALESCE(r.TMS_Dia, 0)
            ELSE 0
        END,

    @ley15_i =
        CASE
            WHEN ISNULL(p.PAD1_Activo, 0) = 0
                THEN 0

            WHEN COALESCE(r.TMS_Dia, 0) = 0
                THEN 0

            ELSE
                COALESCE(r.FCu_Dia, 0)
                / NULLIF(r.TMS_Dia, 0)
                * 100.0
        END

FROM Resumen_Dia AS r
CROSS JOIN Pad_Dia AS p;
    SELECT
        @ton18_i = Tonelaje,
        @ley18_i = Ley_Cu
    FROM #tmp_f18_oficial;
    SELECT
        @ton19_i = Tonelaje,
        @ley19_i = Ley_Cu
    FROM #tmp_f19_oficial;
    SET @tms_ini_f16 = @ton14_i - @ton18_i - @ton21_i;
    SET @ley_ini_f16 = CASE
        WHEN @tms_ini_f16 = 0 THEN 0
        ELSE ((@ton14_i * @ley14_i) - (@ton18_i * @ley18_i) - (@ton21_i * @ley21_i)) / @tms_ini_f16
    END;
    SET @tms_ini_f17 = @ton15_i - @ton19_i - @ton22_i;
    SET @ley_ini_f17 = CASE
        WHEN @tms_ini_f17 = 0 THEN 0
        ELSE ((@ton15_i * @ley15_i) - (@ton19_i * @ley19_i) - (@ton22_i * @ley22_i)) / @tms_ini_f17
    END;
    UPDATE #flujos_resultado
       SET TMS_Inicial = @tms_ini_f16,
           Ley_Cu_1    = @ley_ini_f16
     WHERE codigo_flujo = 'F16';
    UPDATE #flujos_resultado
       SET TMS_Inicial = @tms_ini_f17,
           Ley_Cu_1    = @ley_ini_f17
     WHERE codigo_flujo = 'F17';
    -------------------------------------------------------------------------
    -- 9) SALIDA FINAL
    -------------------------------------------------------------------------
    SELECT
        codigo_flujo AS Flujo,
        TMS_Inicial,
        Ley_Cu_1,
        TMS_Final,
        Ley_Cu_2,
        Tonelaje,
        Ley_Cu,
        Tonelaje * Ley_Cu / 100.0 AS FCu
    FROM #flujos_resultado
    ORDER BY
        TRY_CONVERT(int, REPLACE(codigo_flujo, 'F', ''));
END;