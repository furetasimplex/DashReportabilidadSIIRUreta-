-- reclamo.sp_cargar_cv25_horas SHA256 192da27c09cc39f9db1d79586c2dc45036a95d1c3d33ee07319bbe6a5924fe75
/* ================================================================
   Error al correr "Recalcular" (rango 01 al 05-ago-2026):

   IntegrityError: The MERGE statement conflicted with the CHECK
   constraint "CK_cv_tmh". Column 'tmh_dia'. Tabla reclamo.cv25_diario.

   Causa: CK_cv_tmh exige tmh_dia IS NULL OR tmh_dia >= 0. El SP ya
   detecta un delta negativo del totalizador CV25 y lo marca con
   flag='DELTA_NEGATIVO_REVISAR', pero el mismo MERGE seguia
   escribiendo ese valor negativo tal cual en tmh_dia/tms_dia -- el
   flag diagnosticaba el problema, pero no evitaba el valor invalido.
   Debe haber aparecido un delta negativo nuevo (probable reinicio o
   caida del totalizador CV25 sin corregir) en alguna fecha del rango
   01-05 agosto, algo que antes no se topaba porque este SP solo se
   corria a mano en rangos ya revisados.

   Fix: cuando el delta elegido (segun @TagOficial) es negativo,
   tmh_dia y tms_dia quedan NULL (pasa el CHECK) en vez de escribir el
   valor negativo. Las columnas crudas tmh_cv025tot/tmh_cv025_tot NO
   se tocan -- se conserva el dato de origen intacto para diagnostico
   -- y el flag sigue en DELTA_NEGATIVO_REVISAR para que quede visible
   en el dashboard. Resto del procedimiento sin cambios.
================================================================ */

CREATE PROCEDURE [reclamo].[sp_cargar_cv25_horas]
(
    @FechaInicio date,
    @FechaFin    date,
    @HumedadPct  decimal(9,6) = NULL,
    @TagOficial  varchar(40)  = 'cv025tot'
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @FechaInicio IS NULL OR @FechaFin IS NULL
        THROW 60201, 'Debe informar el rango de fechas.', 1;

    IF @TagOficial NOT IN ('cv025tot','cv025_tot')
        THROW 60202, 'El tag oficial debe ser cv025tot o cv025_tot.', 1;

    /* ---- 3.a  Totalizador CV25 diario ---------------------------------- */
    MERGE [reclamo].[cv25_diario] AS tgt
    USING
    (
        SELECT
            CAST(v.fecha_turno AS date)               AS fecha,
            CAST(v.[cv025tot]  AS decimal(30,12))     AS tmh_cv025tot,
            CAST(v.[cv025_tot] AS decimal(30,12))     AS tmh_cv025_tot,
            CAST(v.rc_001 AS int)                     AS horas_con_dato_r1,
            CAST(v.rc_002 AS int)                     AS horas_con_dato_r2
        FROM [inventar_SpcHidr].[vista_resumen_datos_filtrados] v
        WHERE CAST(v.fecha_turno AS date) >= @FechaInicio
          AND CAST(v.fecha_turno AS date) <= @FechaFin
    ) AS src
        ON tgt.fecha = src.fecha
    WHEN MATCHED THEN UPDATE SET
        tmh_cv025tot      = src.tmh_cv025tot,
        tmh_cv025_tot     = src.tmh_cv025_tot,
        horas_con_dato_r1 = src.horas_con_dato_r1,
        horas_con_dato_r2 = src.horas_con_dato_r2,
        tag_utilizado     = @TagOficial,
        tmh_dia           = CASE
                               WHEN (CASE WHEN @TagOficial = 'cv025tot'
                                          THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END) < 0
                                   THEN NULL
                               ELSE CASE WHEN @TagOficial = 'cv025tot'
                                         THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END
                            END,
        humedad_pct       = COALESCE(@HumedadPct, tgt.humedad_pct),
        tms_dia           = CASE
                               WHEN (CASE WHEN @TagOficial = 'cv025tot'
                                          THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END) < 0
                                   THEN NULL
                               WHEN COALESCE(@HumedadPct, tgt.humedad_pct) IS NULL
                                   THEN CASE WHEN @TagOficial = 'cv025tot'
                                             THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END
                               ELSE (CASE WHEN @TagOficial = 'cv025tot'
                                          THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END)
                                    * (1.0 - COALESCE(@HumedadPct, tgt.humedad_pct) / 100.0)
                            END,
        flag              = CASE
                               WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                                   THEN 'SIN_TOTALIZADOR'
                               WHEN COALESCE(src.tmh_cv025tot, src.tmh_cv025_tot) < 0
                                   THEN 'DELTA_NEGATIVO_REVISAR'
                               WHEN COALESCE(src.tmh_cv025tot, 0) = 0
                                AND COALESCE(src.horas_con_dato_r1, 0)
                                  + COALESCE(src.horas_con_dato_r2, 0) = 0
                                   THEN 'SIN_OPERACION'
                               ELSE 'OK'
                            END,
        fecha_registro    = SYSDATETIME()
    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        fecha, tmh_cv025tot, tmh_cv025_tot, tmh_dia, humedad_pct, tms_dia,
        horas_con_dato_r1, horas_con_dato_r2, tag_utilizado, flag
    )
    VALUES
    (
        src.fecha, src.tmh_cv025tot, src.tmh_cv025_tot,
        CASE
            WHEN (CASE WHEN @TagOficial = 'cv025tot'
                       THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END) < 0
                THEN NULL
            ELSE CASE WHEN @TagOficial = 'cv025tot' THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END
        END,
        @HumedadPct,
        CASE
            WHEN (CASE WHEN @TagOficial = 'cv025tot'
                       THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END) < 0
                THEN NULL
            WHEN @HumedadPct IS NULL
                THEN CASE WHEN @TagOficial = 'cv025tot' THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END
            ELSE (CASE WHEN @TagOficial = 'cv025tot' THEN src.tmh_cv025tot ELSE src.tmh_cv025_tot END)
                 * (1.0 - @HumedadPct / 100.0)
        END,
        src.horas_con_dato_r1, src.horas_con_dato_r2, @TagOficial,
        CASE
            WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                THEN 'SIN_TOTALIZADOR'
            WHEN COALESCE(src.tmh_cv025tot, src.tmh_cv025_tot) < 0
                THEN 'DELTA_NEGATIVO_REVISAR'
            WHEN COALESCE(src.tmh_cv025tot, 0) = 0
             AND COALESCE(src.horas_con_dato_r1, 0) + COALESCE(src.horas_con_dato_r2, 0) = 0
                THEN 'SIN_OPERACION'
            ELSE 'OK'
        END
    );

    PRINT 'CV25 diario cargado      : ' + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';

    /* ---- 3.b  Horas de operacion por rotopala y turno -------------------
       datos_filtrados es horaria y trae su propia columna turno. */
    DECLARE @Umbral1 decimal(18,6) = (SELECT umbral_corriente  FROM [reclamo].[rotopala] WHERE rotopala_id = 1);
    DECLARE @Hpm1    decimal(9,6)  = (SELECT horas_por_muestra FROM [reclamo].[rotopala] WHERE rotopala_id = 1);
    DECLARE @Umbral2 decimal(18,6) = (SELECT umbral_corriente  FROM [reclamo].[rotopala] WHERE rotopala_id = 2);
    DECLARE @Hpm2    decimal(9,6)  = (SELECT horas_por_muestra FROM [reclamo].[rotopala] WHERE rotopala_id = 2);

    ;WITH muestras AS
    (
        SELECT
            CAST(df.fecha_turno AS date)                  AS fecha_turno,
            CAST(UPPER(LTRIM(RTRIM(df.turno))) AS char(1)) AS turno,
            SUM(CASE WHEN df.rc001corr > @Umbral1 THEN 1 ELSE 0 END) AS n_r1,
            SUM(CASE WHEN df.rc002corr > @Umbral2 THEN 1 ELSE 0 END) AS n_r2
        FROM [inventar_SpcHidr].[datos_filtrados] df
        WHERE CAST(df.fecha_turno AS date) >= @FechaInicio
          AND CAST(df.fecha_turno AS date) <= @FechaFin
          AND df.turno IS NOT NULL
          AND UPPER(LTRIM(RTRIM(df.turno))) IN ('A','B')
        GROUP BY
            CAST(df.fecha_turno AS date),
            CAST(UPPER(LTRIM(RTRIM(df.turno))) AS char(1))
    ),
    desglose AS
    (
        SELECT fecha_turno, turno, CAST(1 AS tinyint) AS rotopala_id,
               n_r1 AS muestras, @Hpm1 AS hpm
        FROM muestras
        UNION ALL
        SELECT fecha_turno, turno, CAST(2 AS tinyint),
               n_r2, @Hpm2
        FROM muestras
    )
    MERGE [reclamo].[rotopala_horas_turno] AS tgt
    USING desglose AS src
        ON  tgt.fecha_turno = src.fecha_turno
        AND tgt.turno       = src.turno
        AND tgt.rotopala_id = src.rotopala_id
    WHEN MATCHED THEN UPDATE SET
        muestras_sobre_umbral = src.muestras,
        horas_por_muestra     = src.hpm,
        horas_operacion       = CAST(src.muestras * src.hpm AS decimal(18,6)),
        flag                  = CASE
                                    WHEN src.muestras * src.hpm > 12.5
                                        THEN 'HORAS_SOBRE_TURNO_REVISAR'
                                    WHEN src.muestras = 0
                                        THEN 'SIN_OPERACION'
                                    ELSE 'OK'
                                END,
        fecha_registro        = SYSDATETIME()
    WHEN NOT MATCHED BY TARGET THEN INSERT
    (
        fecha_turno, turno, rotopala_id,
        muestras_sobre_umbral, horas_por_muestra, horas_operacion, flag
    )
    VALUES
    (
        src.fecha_turno, src.turno, src.rotopala_id,
        src.muestras, src.hpm,
        CAST(src.muestras * src.hpm AS decimal(18,6)),
        CASE
            WHEN src.muestras * src.hpm > 12.5 THEN 'HORAS_SOBRE_TURNO_REVISAR'
            WHEN src.muestras = 0              THEN 'SIN_OPERACION'
            ELSE 'OK'
        END
    );

    PRINT 'Horas de rotopala cargadas: ' + CAST(@@ROWCOUNT AS varchar) + ' filas afectadas';

    /* ---- 3.c  Contraste entre los dos tags del totalizador -------------- */
    IF EXISTS
    (
        SELECT 1 FROM [reclamo].[cv25_diario]
        WHERE fecha BETWEEN @FechaInicio AND @FechaFin
          AND tmh_cv025tot IS NOT NULL AND tmh_cv025_tot IS NOT NULL
          AND tmh_cv025_tot <> 0
          AND ABS(tmh_cv025tot - tmh_cv025_tot) * 100.0 / tmh_cv025_tot > 1
    )
    BEGIN
        PRINT '';
        PRINT 'ATENCION: los dos tags del totalizador CV25 difieren en mas de 1 %';
        PRINT 'en las siguientes fechas. Se publico el tag ' + @TagOficial + '.';

        SELECT
            fecha, tmh_cv025tot, tmh_cv025_tot,
            tmh_cv025tot - tmh_cv025_tot AS diferencia,
            (tmh_cv025tot - tmh_cv025_tot) * 100.0 / NULLIF(tmh_cv025_tot,0) AS diferencia_pct
        FROM [reclamo].[cv25_diario]
        WHERE fecha BETWEEN @FechaInicio AND @FechaFin
          AND tmh_cv025tot IS NOT NULL AND tmh_cv025_tot IS NOT NULL
          AND tmh_cv025_tot <> 0
          AND ABS(tmh_cv025tot - tmh_cv025_tot) * 100.0 / tmh_cv025_tot > 1
        ORDER BY fecha;
    END;

    /* ---- 3.d  Alerta explicita de deltas negativos en el rango ---------
       Nuevo en v1.1: antes el negativo solo se veia si alguien miraba el
       flag columna por columna. Ahora sale como aviso directo, ya que con
       el fix tmh_dia/tms_dia quedan en NULL y el dato podria pasar
       desapercibido si nadie revisa reclamo.cv25_diario. */
    IF EXISTS
    (
        SELECT 1 FROM [reclamo].[cv25_diario]
        WHERE fecha BETWEEN @FechaInicio AND @FechaFin
          AND flag = 'DELTA_NEGATIVO_REVISAR'
    )
    BEGIN
        PRINT '';
        PRINT 'ATENCION: delta negativo del totalizador CV25 en las siguientes';
        PRINT 'fechas. tmh_dia/tms_dia quedaron en NULL (no se publica un';
        PRINT 'valor negativo). Revisar el totalizador de origen.';

        SELECT fecha, tmh_cv025tot, tmh_cv025_tot, tmh_dia, tms_dia, flag
        FROM [reclamo].[cv25_diario]
        WHERE fecha BETWEEN @FechaInicio AND @FechaFin
          AND flag = 'DELTA_NEGATIVO_REVISAR'
        ORDER BY fecha;
    END;

    SELECT * FROM [reclamo].[v_cv25_diario]
    WHERE fecha >= @FechaInicio AND fecha <= @FechaFin
    ORDER BY fecha;
END;

GO

-- inventar_SpcHidr.v_contingencia_pi_frontera_turno SHA256 264ed686d490c25b12b0dc5c720a9084b61c5e8ca7bf5130ea4ac6945ec73e9c
CREATE   VIEW
inventar_SpcHidr.v_contingencia_pi_frontera_turno
AS

WITH fronteras AS
(
    SELECT
        pi.fecha_operacional,
        pi.turno,
        pi.equipo_codigo,

        /* Ya traemos directamente el resultado del totalizador.
           Evitamos volver a expandir la misma vista. */
        pi.delta_observado_pi,

        CASE
            WHEN pi.turno = 'A'
                THEN DATEADD
                (
                    HOUR,
                    8,
                    CAST(pi.fecha_operacional AS datetime2)
                )

            WHEN pi.turno = 'B'
                THEN DATEADD
                (
                    HOUR,
                    20,
                    CAST(pi.fecha_operacional AS datetime2)
                )
        END AS fecha_hora_inicio,

        CASE
            WHEN pi.turno = 'A'
                THEN DATEADD
                (
                    HOUR,
                    20,
                    CAST(pi.fecha_operacional AS datetime2)
                )

            WHEN pi.turno = 'B'
                THEN DATEADD
                (
                    HOUR,
                    8,
                    CAST
                    (
                        DATEADD(DAY, 1, pi.fecha_operacional)
                        AS datetime2
                    )
                )
        END AS fecha_hora_fin

    FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno
         AS pi
)

SELECT
    f.fecha_operacional,
    f.turno,
    f.equipo_codigo,

    f.fecha_hora_inicio,
    f.fecha_hora_fin,

    ini.valor_pi AS lectura_inicio_pi,
    fin.valor_pi AS lectura_fin_pi,

    CAST
    (
        CASE
            /* SRR CV001 mantiene EXACTAMENTE su integración temporal */
            WHEN f.equipo_codigo = 'SRR_CV001'
                THEN f.delta_observado_pi

            /* Resto: frontera final - inicial */
            WHEN ini.valor_pi IS NOT NULL
             AND fin.valor_pi IS NOT NULL
                THEN fin.valor_pi - ini.valor_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS delta_frontera_pi,

    CAST
    (
        CASE
            WHEN ini.valor_pi IS NULL
             AND fin.valor_pi IS NULL
                THEN 'SIN_AMBAS_FRONTERAS'

            WHEN ini.valor_pi IS NULL
                THEN 'SIN_FRONTERA_INICIAL'

            WHEN fin.valor_pi IS NULL
                THEN 'SIN_FRONTERA_FINAL'

            ELSE 'FRONTERAS_COMPLETAS'
        END
        AS varchar(40)
    ) AS estado_fronteras

FROM fronteras AS f

LEFT JOIN inventar_SpcHidr.v_contingencia_pi_serie AS ini
    ON  ini.equipo_codigo     = f.equipo_codigo
    AND ini.fecha_operacional = f.fecha_operacional
    AND ini.turno             = f.turno
    AND ini.fecha_hora        = f.fecha_hora_inicio

/* Deliberadamente se conserva EXACTO el JOIN productivo */
LEFT JOIN inventar_SpcHidr.v_contingencia_pi_serie AS fin
    ON  fin.equipo_codigo = f.equipo_codigo
    AND fin.fecha_hora    = f.fecha_hora_fin;


GO

-- inventar_SpcHidr.v_contingencia_pi_serie SHA256 e5406793983de1b69a74abc001a7294d5481696e24eab82bfba71dad85ff0991
CREATE   VIEW inventar_SpcHidr.v_contingencia_pi_serie
AS

/* ============================================================
   CV008 - PRINCIPAL
   ÚNICO CAMBIO TÉCNICO:
   usar fecha_turno / codigo_turno ya calculados.
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2) AS fecha_hora,
    CAST(t.fecha_turno AS date) AS fecha_operacional,
    CAST(t.codigo_turno AS varchar(1)) AS turno,
    CAST('PRINCIPAL_CV008' AS varchar(40)) AS equipo_codigo,
    CAST(t.tot_008 AS decimal(28,6)) AS valor_pi,
    CAST('tot_TM.tot_008' AS varchar(100)) AS fuente_pi,
    CAST(10 AS int) AS cadencia_esperada_seg
FROM inventar_SpcHidr.tot_TM AS t
WHERE t.tot_008 IS NOT NULL

UNION ALL

/* ============================================================
   CV108 - PRINCIPAL
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2),
    CAST(t.fecha_turno AS date),
    CAST(t.codigo_turno AS varchar(1)),
    CAST('PRINCIPAL_CV108' AS varchar(40)),
    CAST(t.tot_108 AS decimal(28,6)),
    CAST('tot_TM.tot_108' AS varchar(100)),
    CAST(10 AS int)
FROM inventar_SpcHidr.tot_TM AS t
WHERE t.tot_108 IS NOT NULL

UNION ALL

/* ============================================================
   CV006 - CHANCADOR
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('CHANCADOR_CV006' AS varchar(40)),
    CAST(d.cv006_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv006_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv006_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV002
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('SRR_CV002' AS varchar(40)),
    CAST(d.cv002_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv002_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv002_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV003
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('SRR_CV003' AS varchar(40)),
    CAST(d.cv003_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv003_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv003_tot IS NOT NULL

UNION ALL

/* ============================================================
   SRR CV001 - PROCESS VALUE
   MISMA matemática.
   Sólo cambia la derivación fecha_operacional / turno.
   ============================================================ */
SELECT
    CAST(t.fecha AS datetime2),
    CAST(t.fecha_turno AS date),
    CAST(t.codigo_turno AS varchar(1)),
    CAST('SRR_CV001' AS varchar(40)),
    CAST(t.tot_001 AS decimal(28,6)),
    CAST(
        'tot_TM.tot_001_PROCESS_VALUE'
        AS varchar(100)
    ),
    CAST(10 AS int)

FROM inventar_SpcHidr.tot_TM AS t

WHERE t.fecha >= '2026-07-01T08:00:00'
  AND t.tot_001 IS NOT NULL
  AND TRY_CONVERT(float, t.tot_001) >= 0

UNION ALL

/* ============================================================
   CV025 - RIPIOS
   SIN CAMBIOS
   ============================================================ */
SELECT
    CAST(d.fecha_inicial AS datetime2),

    CASE
        WHEN CAST(d.fecha_inicial AS time) < '08:00:00'
            THEN DATEADD(DAY, -1, CAST(d.fecha_inicial AS date))
        ELSE CAST(d.fecha_inicial AS date)
    END,

    CASE
        WHEN CAST(d.fecha_inicial AS time) >= '08:00:00'
         AND CAST(d.fecha_inicial AS time) <  '20:00:00'
            THEN 'A'
        ELSE 'B'
    END,

    CAST('RIPIOS_CV025' AS varchar(40)),
    CAST(d.cv025_tot AS decimal(28,6)),
    CAST('datos_filtrados.cv025_tot' AS varchar(100)),
    CAST(3600 AS int)

FROM inventar_SpcHidr.datos_filtrados AS d
WHERE d.cv025_tot IS NOT NULL;


GO

-- inventar_SpcHidr.v_contingencia_pi_totalizador_turno SHA256 78aa4b812cf48a210141f8475f18a35399433ca73f899d67fbc1b4f7a71c71b7
CREATE   VIEW
inventar_SpcHidr.v_contingencia_pi_totalizador_turno
AS

WITH serie AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo,
        fecha_hora,
        valor_pi,
        fuente_pi,
        cadencia_esperada_seg,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS rn_inicio,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora DESC
        ) AS rn_fin,

        LAG(fecha_hora) OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS fecha_anterior,

        LAG(valor_pi) OVER
        (
            PARTITION BY
                fecha_operacional,
                turno,
                equipo_codigo
            ORDER BY fecha_hora
        ) AS valor_anterior

    FROM inventar_SpcHidr.v_contingencia_pi_serie
),

calc AS
(
    SELECT
        *,

        DATEDIFF
        (
            SECOND,
            fecha_anterior,
            fecha_hora
        ) AS gap_seg,

        CASE
            WHEN valor_anterior IS NOT NULL
             AND valor_pi <> valor_anterior
                THEN 1
            ELSE 0
        END AS cambio

    FROM serie
),

resumen AS
(
    SELECT
        fecha_operacional,
        turno,
        equipo_codigo,

        MAX(fuente_pi)
            AS fuente_pi,

        MAX(cadencia_esperada_seg)
            AS cadencia_esperada_seg,

        COUNT(*)
            AS registros,

        COUNT(DISTINCT valor_pi)
            AS valores_distintos,

        MIN(fecha_hora)
            AS primera_fecha_registro,

        MAX(fecha_hora)
            AS ultima_fecha_registro,

        MAX
        (
            CASE
                WHEN rn_inicio = 1
                    THEN valor_pi
            END
        ) AS lectura_inicial_pi,

        MAX
        (
            CASE
                WHEN rn_fin = 1
                    THEN valor_pi
            END
        ) AS lectura_final_pi,

        MAX
        (
            CASE
                WHEN cambio = 1
                    THEN fecha_hora
            END
        ) AS ultima_fecha_con_cambio,

        MAX(gap_seg)
            AS max_gap_seg,

        SUM
        (
            CASE
                WHEN gap_seg >= cadencia_esperada_seg * 2
                    THEN 1
                ELSE 0
            END
        ) AS cantidad_gaps_anormales,

        /* SRR CV001 PROCESS VALUE:
           metodología exactamente igual a la oficial */
        SUM
        (
            CASE
                WHEN equipo_codigo = 'SRR_CV001'
                 AND valor_pi IS NOT NULL
                 AND valor_pi >= 0
                    THEN
                        TRY_CONVERT(float, valor_pi)
                        * cadencia_esperada_seg
                        / 3600.0
                ELSE 0
            END
        ) AS process_value_integrado_tmh

    FROM calc

    GROUP BY
        fecha_operacional,
        turno,
        equipo_codigo
),

diagnostico AS
(
    SELECT
        *,

        CAST
        (
            43200.0 / cadencia_esperada_seg
            AS int
        ) AS registros_esperados,

        CAST
        (
            registros * 100.0
            /
            NULLIF
            (
                43200.0 / cadencia_esperada_seg,
                0
            )
            AS decimal(10,2)
        ) AS cobertura_pct,

        CASE
            WHEN valores_distintos = 1
                THEN 43200

            WHEN ultima_fecha_con_cambio IS NOT NULL
                THEN DATEDIFF
                (
                    SECOND,
                    ultima_fecha_con_cambio,
                    ultima_fecha_registro
                )

            ELSE NULL
        END AS segundos_sin_cambio_al_cierre

    FROM resumen
)

SELECT
    fecha_operacional,
    turno,
    equipo_codigo,

    fuente_pi,
    cadencia_esperada_seg,

    registros_esperados,
    registros,
    cobertura_pct,

    valores_distintos,

    primera_fecha_registro,
    ultima_fecha_registro,

    lectura_inicial_pi,
    lectura_final_pi,

    CAST
    (
        CASE
            WHEN equipo_codigo = 'SRR_CV001'
                THEN process_value_integrado_tmh

            ELSE
                lectura_final_pi - lectura_inicial_pi
        END
        AS decimal(28,6)
    ) AS delta_observado_pi,

    ultima_fecha_con_cambio,
    segundos_sin_cambio_al_cierre,

    max_gap_seg,
    cantidad_gaps_anormales,

    CASE
        WHEN valores_distintos = 1
         AND registros = registros_esperados
         AND cantidad_gaps_anormales = 0
            THEN 'SIN_CAMBIO_TURNO_COMPLETO'

        WHEN valores_distintos = 1
            THEN 'SIN_CAMBIO_CON_COBERTURA_PARCIAL'

        WHEN registros < registros_esperados
          OR cantidad_gaps_anormales > 0
            THEN 'CON_VARIACION_COBERTURA_PARCIAL'

        ELSE 'CON_VARIACION'
    END AS estado_tecnico_pi

FROM diagnostico;


GO

-- inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno SHA256 8158c9e547b7698fc917cd22f9047a9f8ee580f412be2d6090321fb3d59fe6a5
CREATE   VIEW
inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno
AS

WITH claves AS
(
    /* PI */
    SELECT
        p.fecha_operacional,
        p.turno,
        p.equipo_codigo
    FROM inventar_SpcHidr.v_contingencia_pi_totalizador_turno AS p
    WHERE p.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )

    UNION

    /* TUM */
    SELECT
        t.fecha_operacional,
        t.turno,
        t.equipo_codigo
    FROM inventar_SpcHidr.v_contingencia_totalizador_turno AS t
    WHERE t.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )
)

SELECT
    c.fecha_operacional,
    c.turno,
    c.equipo_codigo,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
                THEN 'SIN_PI'
            ELSE pi.estado_tecnico_pi
        END
        AS varchar(50)
    ) AS estado_tecnico_pi,

    pi.cobertura_pct,
    pi.valores_distintos,
    pi.ultima_fecha_con_cambio,
    pi.segundos_sin_cambio_al_cierre,
    pi.cantidad_gaps_anormales,

    f.fecha_hora_inicio,
    f.fecha_hora_fin,
    f.lectura_inicio_pi,
    f.lectura_fin_pi,
    f.delta_frontera_pi,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
                THEN 'SIN_PI'
            ELSE f.estado_fronteras
        END
        AS varchar(40)
    ) AS estado_fronteras,

    apoyo.tonelaje_apoyo,
    apoyo.fuente_apoyo,

    CAST
    (
        COALESCE(apoyo.estado_apoyo, 'SIN_INFORMACION')
        AS varchar(30)
    ) AS estado_apoyo,

    tum.id AS tum_id,

    tum.lectura_inicial AS lectura_inicio_tum,
    tum.lectura_final   AS lectura_fin_tum,

    tum.valor_turno AS valor_turno_tum,
    tum.total_excel AS total_excel_tum,

    tum.lectura_inicial_calculada,
    tum.lectura_final_calculada,

    tum.informe_tipo,
    tum.circuito,
    tum.equipo_nombre,

    tum.batch_id AS tum_batch_id,
    tum.archivo_batch,
    tum.quality_json,

    CAST
    (
        CASE
            WHEN tum.id IS NULL THEN 0
            ELSE 1
        END
        AS bit
    ) AS tum_disponible,

    CAST
    (
        CASE
            WHEN c.equipo_codigo = 'SRR_CV001'
                THEN NULL

            WHEN pi.equipo_codigo IS NULL
                THEN NULL

            WHEN tum.lectura_inicial IS NOT NULL
             AND f.lectura_inicio_pi IS NOT NULL
                THEN tum.lectura_inicial - f.lectura_inicio_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_inicio_pi_tum,

    CAST
    (
        CASE
            WHEN c.equipo_codigo = 'SRR_CV001'
                THEN NULL

            WHEN pi.equipo_codigo IS NULL
                THEN NULL

            WHEN tum.lectura_final IS NOT NULL
             AND f.lectura_fin_pi IS NOT NULL
                THEN tum.lectura_final - f.lectura_fin_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_fin_pi_tum,

    CAST
    (
        CASE
            WHEN tum.valor_turno IS NOT NULL
             AND f.delta_frontera_pi IS NOT NULL
                THEN tum.valor_turno - f.delta_frontera_pi

            ELSE NULL
        END
        AS decimal(28,6)
    ) AS diferencia_tonelaje_pi_tum,

    CAST
    (
        CASE
            WHEN pi.equipo_codigo IS NULL
             AND tum.id IS NOT NULL
                THEN 'SIN_PI_CON_TUM'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND tum.id IS NOT NULL
                THEN 'EVALUAR_CON_TUM'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND apoyo.estado_apoyo = 'MOVIMIENTO_CONFIRMADO'
             AND tum.id IS NULL
                THEN 'ESPERA_TUM_PI_INCONSISTENTE'

            WHEN pi.estado_tecnico_pi IN
            (
                'SIN_CAMBIO_TURNO_COMPLETO',
                'SIN_CAMBIO_CON_COBERTURA_PARCIAL'
            )
             AND tum.id IS NULL
                THEN 'SIN_EVIDENCIA_SUFICIENTE'

            WHEN pi.estado_tecnico_pi =
                 'CON_VARIACION_COBERTURA_PARCIAL'
             AND tum.id IS NOT NULL
                THEN 'PI_Y_TUM_DISPONIBLES'

            WHEN pi.estado_tecnico_pi =
                 'CON_VARIACION_COBERTURA_PARCIAL'
             AND tum.id IS NULL
                THEN 'PI_CON_GAP_SIN_TUM'

            WHEN pi.estado_tecnico_pi = 'CON_VARIACION'
             AND tum.id IS NOT NULL
                THEN 'PI_Y_TUM_DISPONIBLES'

            WHEN pi.estado_tecnico_pi = 'CON_VARIACION'
             AND tum.id IS NULL
                THEN 'PI_DISPONIBLE_SIN_TUM'

            ELSE 'REQUIERE_REVISION'
        END
        AS varchar(50)
    ) AS estado_diagnostico

FROM claves AS c

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_totalizador_turno AS pi
    ON  pi.fecha_operacional = c.fecha_operacional
    AND pi.turno             = c.turno
    AND pi.equipo_codigo     = c.equipo_codigo

LEFT JOIN
    inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f
    ON  f.fecha_operacional = c.fecha_operacional
    AND f.turno             = c.turno
    AND f.equipo_codigo     = c.equipo_codigo

LEFT JOIN
    inventar_SpcHidr.v_contingencia_apoyo_operacional_turno AS apoyo
    ON  apoyo.fecha_operacional = c.fecha_operacional
    AND apoyo.turno             = c.turno
    AND c.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108'
    )

OUTER APPLY
(
    SELECT TOP (1)
        t.*
    FROM inventar_SpcHidr.v_contingencia_totalizador_turno AS t
    WHERE t.fecha_operacional = c.fecha_operacional
      AND t.turno             = c.turno
      AND t.equipo_codigo     = c.equipo_codigo
    ORDER BY
        t.source_revision_at DESC,
        t.updated_at DESC,
        t.batch_id DESC
) AS tum;


GO

-- inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno SHA256 d2dead4f16a60d5981d0d22abe4c28bb3bcb249ba4ccc7673a72f89fa533aad2
CREATE VIEW [inventar_SpcHidr].[v_contingencia_totalizador_resuelto_turno]
AS

/* ================================================================
   RESOLVEDOR FINAL PI / TUM POR TURNO

   Clave:
       fecha_operacional + turno + equipo_codigo

   Reglas principales:
     1. PI válido/con variación:
        -> PI

     2. PI no confiable / plano:
        -> TUM si existe

     3. PI completamente ausente:
        -> TUM si existe

     4. Sin PI confiable y sin TUM:
        -> SIN_RESOLVER

   IMPORTANTE:
   - TUM_DIRECTO, TUM_MIXTO y TUM_CALCULADO son utilizables.
   - NULL = falta información.
   - 0 TUM = cero operacional válido.
   - No aplicar factores de humedad 0.97 / 0.975 / 0.90 aquí.

   CAMBIO TUM:
   - CV008/CV108 dejan de leer v_datos_apilado_tmh_v2.
   - Su PI se obtiene directamente desde
     v_contingencia_pi_frontera_turno.
   - Regla productiva:
         NULL    -> NULL
         <=100 t -> 0
         >100 t  -> delta PI
================================================================ */

WITH pi_productivo AS
(

    /* ============================================================
       CV008 - PRINCIPAL TM1

       PI independiente de Control_Apilado_TMH_v2_test.

       v_contingencia_pi_frontera_turno ya entrega:
           turno A = 08:00 -> 20:00
           turno B = 20:00 -> 08:00 siguiente

       Regla productiva vigente:
           NULL    -> NULL
           <=100 t -> 0
           >100 t  -> delta
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('PRINCIPAL_CV008' AS varchar(40))
            AS equipo_codigo,

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ) AS valor_pi_bruto,

        CAST
        (
            CASE
                WHEN f.delta_frontera_pi IS NULL
                    THEN NULL

                WHEN f.delta_frontera_pi <= 100
                    THEN 0

                ELSE f.delta_frontera_pi
            END
            AS decimal(28,6)
        ) AS valor_pi_final

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'PRINCIPAL_CV008'


    UNION ALL


    /* ============================================================
       CV108 - PRINCIPAL TM2

       Misma metodología que CV008.
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('PRINCIPAL_CV108' AS varchar(40))
            AS equipo_codigo,

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ) AS valor_pi_bruto,

        CAST
        (
            CASE
                WHEN f.delta_frontera_pi IS NULL
                    THEN NULL

                WHEN f.delta_frontera_pi <= 100
                    THEN 0

                ELSE f.delta_frontera_pi
            END
            AS decimal(28,6)
        ) AS valor_pi_final

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'PRINCIPAL_CV108'


    UNION ALL


    /* ============================================================
       CV006 - CHANCADOR
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('CHANCADOR_CV006' AS varchar(40)),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        )

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'CHANCADOR_CV006'


    UNION ALL


    /* ============================================================
       CV025 - RIPIOS
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('RIPIOS_CV025' AS varchar(40)),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        )

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'RIPIOS_CV025'


    UNION ALL


    /* ============================================================
       SRR CV001

       Process Value integrado:
           SUM(tot_001 * 10 / 3600)

       delta_frontera_pi ya contiene esa integración.
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('SRR_CV001' AS varchar(40)),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        )

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'SRR_CV001'


    UNION ALL


    /* ============================================================
       SRR CV002
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('SRR_CV002' AS varchar(40)),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        )

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'SRR_CV002'


    UNION ALL


    /* ============================================================
       SRR CV003
       ============================================================ */

    SELECT
        f.fecha_operacional,
        f.turno,
        CAST('SRR_CV003' AS varchar(40)),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        ),

        CAST(
            f.delta_frontera_pi
            AS decimal(28,6)
        )

    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f

    WHERE f.equipo_codigo = 'SRR_CV003'
),


base AS
(
    SELECT
        d.fecha_operacional,
        d.turno,
        d.equipo_codigo,

        /* ========================================================
           PI
           ======================================================== */

        d.estado_tecnico_pi,
        d.cobertura_pct,

        d.ultima_fecha_con_cambio,
        d.segundos_sin_cambio_al_cierre,

        d.lectura_inicio_pi,
        d.lectura_fin_pi,
        d.delta_frontera_pi,
        d.estado_fronteras,

        /*
           LEFT JOIN intencional.

           Si PI desapareció completamente:
               p.valor_pi_* = NULL

           pero la fila del diagnóstico sigue existiendo gracias
           al universo PI UNION TUM.
        */

        p.valor_pi_bruto,
        p.valor_pi_final,


        /* ========================================================
           APOYO OPERACIONAL
           ======================================================== */

        d.tonelaje_apoyo,
        d.fuente_apoyo,
        d.estado_apoyo,


        /* ========================================================
           TUM
           ======================================================== */

        d.tum_id,
        d.tum_disponible,

        d.lectura_inicio_tum,
        d.lectura_fin_tum,

        d.valor_turno_tum,
        d.total_excel_tum,

        d.lectura_inicial_calculada,
        d.lectura_final_calculada,

        d.diferencia_inicio_pi_tum,
        d.diferencia_fin_pi_tum,
        d.diferencia_tonelaje_pi_tum,

        d.archivo_batch,
        d.tum_batch_id,


        /* ========================================================
           TIPO DE TUM

           Sólo trazabilidad.
           Los tres tipos son utilizables como contingencia.
           ======================================================== */

        CAST
        (
            CASE

                WHEN d.tum_disponible = 0
                    THEN 'SIN_TUM'

                WHEN ISNULL(d.lectura_inicial_calculada,0) = 0
                 AND ISNULL(d.lectura_final_calculada,0) = 0
                    THEN 'TUM_DIRECTO'

                WHEN ISNULL(d.lectura_inicial_calculada,0) = 1
                 AND ISNULL(d.lectura_final_calculada,0) = 1
                    THEN 'TUM_CALCULADO'

                ELSE 'TUM_MIXTO'

            END
            AS varchar(30)
        ) AS tipo_tum

    FROM
        inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno
            AS d

    LEFT JOIN pi_productivo AS p
        ON  p.fecha_operacional = d.fecha_operacional
        AND p.turno             = d.turno
        AND p.equipo_codigo     = d.equipo_codigo

    WHERE d.equipo_codigo IN
    (
        'CHANCADOR_CV006',
        'PRINCIPAL_CV008',
        'PRINCIPAL_CV108',
        'RIPIOS_CV025',
        'SRR_CV001',
        'SRR_CV002',
        'SRR_CV003'
    )
),


decision AS
(
    SELECT
        *,

        CAST
        (
            CASE

                /* =================================================
                   CASO:
                   PI completamente ausente + TUM existente.

                   Un TUM = 0 es válido.
                   No confundir ausencia PI con PI=0.
                   ================================================= */

                WHEN estado_tecnico_pi = 'SIN_PI'
                 AND tum_disponible = 1
                 AND valor_turno_tum IS NOT NULL
                 AND valor_turno_tum >= 0

                    THEN 'TUM'


                /* =================================================
                   SRR CV001

                   Process Value integrado.

                   Para CV001 NO se exige frontera exacta 08/20,
                   porque F25 vigente integra todos los registros
                   disponibles del período.

                   Por eso:
                       CON_VARIACION
                       CON_VARIACION_COBERTURA_PARCIAL

                   continúan usando PI.
                   ================================================= */

                WHEN equipo_codigo = 'SRR_CV001'
                 AND estado_tecnico_pi IN
                 (
                     'CON_VARIACION',
                     'CON_VARIACION_COBERTURA_PARCIAL'
                 )
                 AND valor_pi_final IS NOT NULL
                 AND valor_pi_final >= 0

                    THEN 'PI'


                /* =================================================
                   RESTO DE TOTALIZADORES

                   Para señales acumulativas:
                   - fronteras completas
                   - existe variación
                   - delta >= 0
                   ================================================= */

                WHEN equipo_codigo <> 'SRR_CV001'
                 AND estado_fronteras = 'FRONTERAS_COMPLETAS'
                 AND delta_frontera_pi IS NOT NULL
                 AND delta_frontera_pi >= 0
                 AND estado_tecnico_pi IN
                 (
                     'CON_VARIACION',
                     'CON_VARIACION_COBERTURA_PARCIAL'
                 )

                    THEN 'PI'


                /* =================================================
                   PI plano / incompleto / no confiable + TUM

                   Se acepta:
                       TUM_DIRECTO
                       TUM_MIXTO
                       TUM_CALCULADO

                   Incluye TUM = 0.
                   ================================================= */

                WHEN tum_disponible = 1
                 AND valor_turno_tum IS NOT NULL
                 AND valor_turno_tum >= 0

                    THEN 'TUM'


                /* =================================================
                   No existe una fuente válida
                   ================================================= */

                ELSE 'SIN_RESOLVER'

            END
            AS varchar(30)
        ) AS fuente_resuelta

    FROM base
)


SELECT
    fecha_operacional,
    turno,
    equipo_codigo,


    /* ============================================================
       PI
       ============================================================ */

    estado_tecnico_pi,
    estado_fronteras,

    valor_pi_bruto,
    valor_pi_final,

    lectura_inicio_pi,
    lectura_fin_pi,
    delta_frontera_pi,

    ultima_fecha_con_cambio,
    segundos_sin_cambio_al_cierre,


    /* ============================================================
       APOYO OPERACIONAL
       ============================================================ */

    tonelaje_apoyo,
    fuente_apoyo,
    estado_apoyo,


    /* ============================================================
       TUM
       ============================================================ */

    tum_disponible,
    tipo_tum,

    lectura_inicio_tum,
    lectura_fin_tum,

    valor_turno_tum,
    total_excel_tum,

    diferencia_inicio_pi_tum,
    diferencia_fin_pi_tum,
    diferencia_tonelaje_pi_tum,


    /* ============================================================
       DECISIÓN
       ============================================================ */

    fuente_resuelta,


    /* ============================================================
       VALOR BRUTO RESUELTO
       ============================================================ */

    CAST
    (
        CASE

            WHEN fuente_resuelta = 'PI'
                THEN valor_pi_bruto

            WHEN fuente_resuelta = 'TUM'
                THEN valor_turno_tum

            ELSE NULL

        END
        AS decimal(28,6)
    ) AS valor_bruto_resuelto,


    /* ============================================================
       VALOR FINAL RESUELTO

       NO se aplican aquí:
           SRR   0.97
           CV006 0.975
           CV025 0.90

       Esos factores corresponden a consumidores finales.
       ============================================================ */

    CAST
    (
        CASE

            /* ----------------------------------------------------
               PI
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'PI'
                THEN valor_pi_final


            /* ----------------------------------------------------
               CV006
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo = 'CHANCADOR_CV006'
             AND valor_turno_tum >= 0

                THEN valor_turno_tum


            /* ----------------------------------------------------
               CV025
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo = 'RIPIOS_CV025'
             AND valor_turno_tum >= 0

                THEN valor_turno_tum


            /* ----------------------------------------------------
               SRR CV001 / CV002 / CV003

               TUM 0 también es cero válido.
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'SRR_CV001',
                 'SRR_CV002',
                 'SRR_CV003'
             )
             AND valor_turno_tum >= 0

                THEN valor_turno_tum


            /* ----------------------------------------------------
               CV008 / CV108

               Regla productiva vigente:
                   <= 100 t -> 0
                   >  100 t -> valor
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'PRINCIPAL_CV008',
                 'PRINCIPAL_CV108'
             )
             AND valor_turno_tum > 100

                THEN valor_turno_tum


            WHEN fuente_resuelta = 'TUM'
             AND equipo_codigo IN
             (
                 'PRINCIPAL_CV008',
                 'PRINCIPAL_CV108'
             )
             AND valor_turno_tum <= 100

                THEN 0


            ELSE NULL

        END
        AS decimal(28,6)
    ) AS valor_final_resuelto,


    /* ============================================================
       MOTIVO DE DECISIÓN
       ============================================================ */

    CAST
    (
        CASE

            /* ----------------------------------------------------
               PI ausente completamente
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_DIRECTO'

                THEN 'SIN_PI_USA_TUM_DIRECTO'


            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_MIXTO'

                THEN 'SIN_PI_USA_TUM_MIXTO'


            WHEN fuente_resuelta = 'TUM'
             AND estado_tecnico_pi = 'SIN_PI'
             AND tipo_tum = 'TUM_CALCULADO'

                THEN 'SIN_PI_USA_TUM_CALCULADO'


            /* ----------------------------------------------------
               PI prioritario
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'PI'
             AND tum_disponible = 0

                THEN 'PI_DISPONIBLE'


            WHEN fuente_resuelta = 'PI'
             AND tum_disponible = 1

                THEN 'PI_PRIORITARIO_TUM_SOLO_CONTROL'


            /* ----------------------------------------------------
               PI existente pero en contingencia
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_DIRECTO'

                THEN 'PI_EN_CONTINGENCIA_USA_TUM_DIRECTO'


            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_MIXTO'

                THEN 'PI_EN_CONTINGENCIA_USA_TUM_MIXTO'


            WHEN fuente_resuelta = 'TUM'
             AND tipo_tum = 'TUM_CALCULADO'

                THEN 'PI_EN_CONTINGENCIA_USA_TUM_CALCULADO'


            /* ----------------------------------------------------
               Sin resolver con movimiento externo
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND estado_apoyo = 'MOVIMIENTO_CONFIRMADO'

                THEN 'MOVIMIENTO_CONFIRMADO_ESPERANDO_TUM'


            /* ----------------------------------------------------
               SRR sin fuente
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND equipo_codigo IN
             (
                 'SRR_CV001',
                 'SRR_CV002',
                 'SRR_CV003'
             )

                THEN 'SRR_SIN_TUM'


            /* ----------------------------------------------------
               CV025 sin fuente
               ---------------------------------------------------- */

            WHEN fuente_resuelta = 'SIN_RESOLVER'
             AND equipo_codigo = 'RIPIOS_CV025'

                THEN 'CV025_SIN_TUM'


            ELSE 'SIN_EVIDENCIA_SUFICIENTE'

        END
        AS varchar(80)
    ) AS motivo_decision,


    /* ============================================================
       TRAZABILIDAD
       ============================================================ */

    tum_batch_id,
    archivo_batch

FROM decision;


GO

-- reclamo.v_cv25_diario SHA256 f1d9befa1514708eb8cbfe6f4ce88702572af73996ed441972e60c15c3c79cc1
CREATE VIEW [reclamo].[v_cv25_diario]
AS

WITH hr AS
(
    SELECT
        fecha_turno AS fecha,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 1
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r1,

        SUM
        (
            CASE
                WHEN h.rotopala_id = 2
                THEN h.horas_operacion
                ELSE 0
            END
        ) AS horas_r2,

        SUM(h.horas_operacion) AS horas_total,

        COUNT(DISTINCT h.turno) AS turnos_con_dato

    FROM [reclamo].[rotopala_horas_turno] h

    GROUP BY
        fecha_turno
)

SELECT
    COALESCE(cv.fecha, hr.fecha) AS fecha,

    cv.tmh_dia,
    cv.tms_dia,

    cv.tmh_cv025tot,
    cv.tmh_cv025_tot,

    cv.tag_utilizado,

    cv.flag AS flag_cv25,

    cv.tmh_cv025tot - cv.tmh_cv025_tot
        AS diferencia_entre_tags,

    ------------------------------------------------------------
    -- Contraste de tags CV025
    ------------------------------------------------------------
    CASE
        WHEN cv.tmh_cv025tot IS NULL
          OR cv.tmh_cv025_tot IS NULL
            THEN 'SIN_CONTRASTE'

        WHEN cv.tmh_cv025_tot = 0
            THEN 'TAG_SECUNDARIO_CERO'

        WHEN
            ABS(cv.tmh_cv025tot - cv.tmh_cv025_tot)
            * 100.0 / cv.tmh_cv025_tot > 1
            THEN 'TAGS_DIFIEREN_SOBRE_1_PCT'

        ELSE 'OK'
    END AS flag_tags,

    hr.horas_r1,
    hr.horas_r2,
    hr.horas_total,
    hr.turnos_con_dato,

    ------------------------------------------------------------
    -- TMS estimado R1
    --
    -- Si CV025 = 0, no hubo operación:
    -- corresponde explícitamente 0 TMS.
    --
    -- Si CV025 > 0 pero no hay horas:
    -- no podemos repartir el tonelaje.
    ------------------------------------------------------------
    CASE
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r1
            / hr.horas_total
    END AS tms_estimado_r1,

    ------------------------------------------------------------
    -- TMS estimado R2
    ------------------------------------------------------------
    CASE
        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 0

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN NULL

        ELSE
            cv.tms_dia
            * hr.horas_r2
            / hr.horas_total
    END AS tms_estimado_r2,

    ------------------------------------------------------------
    -- Estado del preliminar
    ------------------------------------------------------------
    CASE
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'

        WHEN COALESCE(cv.tms_dia, 0) = 0
            THEN 'CV25_CERO_SIN_OPERACION'

        WHEN COALESCE(hr.horas_total, 0) = 0
            THEN 'SIN_HORAS_NO_REPARTIBLE'

        ELSE 'OK'
    END AS flag_preliminar

FROM [reclamo].[cv25_diario] cv

FULL OUTER JOIN hr
    ON hr.fecha = cv.fecha;


GO

-- reclamo.v_diferencia_cv25 SHA256 97b19223c78e31fb0415a0203ce6d6ae488d0fdd98fc665cc62564a24cc967d6
/* ============================================================================
   V10. reclamo.v_diferencia_cv25

   Agregado diario a nivel planta del contraste entre el totalizador y la
   topografia. Es la vista que alimenta el grafico principal del dashboard.

   Regla R7: CV25 recibe la carga conjunta de ambas rotopalas y NO recibe
   camiones. Por eso la comparacion se hace contra el reclamo de rotopala
   solamente, sin sumar camiones.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_diferencia_cv25]
AS
WITH topo AS
(
    SELECT
        rd.fecha_operacion                  AS fecha,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_topografia,
        SUM(CASE WHEN rd.fuente_reclamo = 'PRELIMINAR_CV25'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_preliminar,
        SUM(rd.tms_rotopala_dia)            AS tms_publicado,
        SUM(rd.tms_camiones_dia)            AS tms_camiones,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA' THEN 1 ELSE 0 END)
                                            AS modulos_topografia,
        SUM(CASE WHEN rd.fuente_reclamo = 'PRELIMINAR_CV25' THEN 1 ELSE 0 END)
                                            AS modulos_preliminar
    FROM [reclamo].[v_reclamo_diario] rd
    GROUP BY rd.fecha_operacion
)
SELECT
    COALESCE(cv.fecha, t.fecha)             AS fecha,
    cv.tms_dia                              AS tms_cv25,
    cv.tmh_dia                              AS tmh_cv25,
    cv.horas_r1,
    cv.horas_r2,
    cv.horas_total,

    t.tms_topografia,
    t.tms_preliminar,
    t.tms_publicado,
    t.tms_camiones,
    t.modulos_topografia,
    t.modulos_preliminar,

    t.tms_topografia - cv.tms_dia           AS diferencia_topografia_cv25,
    CASE
        WHEN COALESCE(cv.tms_dia,0) = 0 THEN NULL
        ELSE (t.tms_topografia - cv.tms_dia) * 100.0 / cv.tms_dia
    END                                     AS diferencia_pct,

    CASE
        WHEN cv.fecha IS NULL
            THEN 'SIN_CV25'
        WHEN COALESCE(t.modulos_topografia,0) = 0
            THEN 'SIN_TOPOGRAFIA_SOLO_PRELIMINAR'
        WHEN COALESCE(cv.tms_dia,0) = 0
            THEN 'CV25_CERO'
        WHEN ABS((t.tms_topografia - cv.tms_dia) * 100.0 / cv.tms_dia) > 10
            THEN 'BRECHA_SOBRE_10_PCT'
        ELSE 'OK'
    END                                     AS flag_diferencia
FROM [reclamo].[v_cv25_diario] cv
FULL OUTER JOIN topo t
    ON t.fecha = cv.fecha;

GO

-- reclamo.v_preliminar_cv25 SHA256 7187d11c0da212a4ade1835707fbf6d1ad881f9f90d25864a0c0364a08dad3d6
CREATE VIEW [reclamo].[v_preliminar_cv25]
AS

WITH abiertos AS
(
    SELECT
        mb.[campaña_id],
        mb.pad_id,
        mb.modulo_id,
        mb.modulo_numero,
        mb.rotopala_id,
        mb.orden_secuencia,
        mb.m3_totales,
        mb.densidad_oficial,
        mb.fecha_apertura,
        mb.fecha_cierre,

        (
            SELECT MAX(ta.fecha_medicion)
            FROM [reclamo].[topografia_avance] ta
            WHERE ta.[campaña_id] = mb.[campaña_id]
              AND ta.modulo_id = mb.modulo_id
              AND ta.estado = 'VIGENTE'
        ) AS ultima_medicion_topografica

    FROM [reclamo].[v_modulo_base] mb

    WHERE mb.estado_secuencia = 'ABIERTO'
      AND mb.rotopala_id IS NOT NULL
),

cv AS
(
    SELECT
        d.fecha,
        d.tms_estimado_r1,
        d.tms_estimado_r2,
        d.horas_r1,
        d.horas_r2,
        d.flag_preliminar

    FROM [reclamo].[v_cv25_diario] d

    -- Solo días operacionales ya cerrados.
    -- El día actual no se publica como preliminar.
    WHERE d.fecha < CAST(SYSDATETIME() AS date)
),

base AS
(
    SELECT
        cv.fecha,
        a.[campaña_id],
        a.pad_id,
        a.modulo_id,
        a.modulo_numero,
        a.rotopala_id,
        a.m3_totales,
        a.densidad_oficial,
        a.ultima_medicion_topografica,

        CASE
            WHEN a.rotopala_id = 1
                THEN cv.tms_estimado_r1
            ELSE cv.tms_estimado_r2
        END AS tms_rotopala_dia_total,

        CASE
            WHEN a.rotopala_id = 1
                THEN cv.horas_r1
            ELSE cv.horas_r2
        END AS horas_rotopala,

        cv.flag_preliminar,

        COUNT(*) OVER
        (
            PARTITION BY cv.fecha, a.rotopala_id
        ) AS modulos_abiertos

    FROM cv

    CROSS JOIN abiertos a

    WHERE
        (
            a.fecha_apertura IS NULL
            OR cv.fecha >= a.fecha_apertura
        )

        AND
        (
            a.fecha_cierre IS NULL
            OR cv.fecha <= a.fecha_cierre
        )

        AND
        (
            a.ultima_medicion_topografica IS NULL
            OR cv.fecha > a.ultima_medicion_topografica
        )
),

con_acumulado AS
(
    SELECT
        b.fecha AS fecha_operacion,
        b.[campaña_id],
        b.pad_id,
        b.modulo_id,
        b.modulo_numero,
        b.rotopala_id,
        b.horas_rotopala,
        b.modulos_abiertos,
        b.m3_totales,
        b.densidad_oficial,

        --------------------------------------------------------
        -- DIARIO
        --------------------------------------------------------
        CAST
        (
            b.tms_rotopala_dia_total / b.modulos_abiertos
            AS decimal(30,12)
        ) AS tms_preliminar_dia,

        CAST
        (
            CASE
                WHEN b.densidad_oficial = 0
                    THEN NULL
                ELSE
                    (
                        b.tms_rotopala_dia_total
                        / b.modulos_abiertos
                    )
                    / b.densidad_oficial
            END
            AS decimal(30,12)
        ) AS m3_preliminar_dia,

        --------------------------------------------------------
        -- ACUMULADO TMS
        --------------------------------------------------------
        SUM
        (
            CAST
            (
                b.tms_rotopala_dia_total / b.modulos_abiertos
                AS decimal(30,12)
            )
        )
        OVER
        (
            PARTITION BY
                b.[campaña_id],
                b.modulo_id

            ORDER BY b.fecha

            ROWS UNBOUNDED PRECEDING
        ) AS tms_preliminar_acum,

        --------------------------------------------------------
        -- ACUMULADO M3
        --------------------------------------------------------
        SUM
        (
            CAST
            (
                CASE
                    WHEN b.densidad_oficial = 0
                        THEN 0
                    ELSE
                        (
                            b.tms_rotopala_dia_total
                            / b.modulos_abiertos
                        )
                        / b.densidad_oficial
                END
                AS decimal(30,12)
            )
        )
        OVER
        (
            PARTITION BY
                b.[campaña_id],
                b.modulo_id

            ORDER BY b.fecha

            ROWS UNBOUNDED PRECEDING
        ) AS m3_preliminar_acum,

        CAST(
            'PRELIMINAR_CV25'
            AS varchar(40)
        ) AS fuente_reclamo,

        CAST(
            'CV25_REPARTIDO_POR_HORAS_ROTOPALA'
            AS varchar(80)
        ) AS metodo_calculo,

        b.flag_preliminar

    FROM base b

    WHERE b.tms_rotopala_dia_total IS NOT NULL
)

SELECT
    ca.fecha_operacion,
    ca.[campaña_id],
    ca.pad_id,
    ca.modulo_id,
    ca.modulo_numero,
    ca.rotopala_id,
    ca.horas_rotopala,
    ca.modulos_abiertos,

    ca.tms_preliminar_dia,
    ca.m3_preliminar_dia,

    ca.tms_preliminar_acum,
    ca.m3_preliminar_acum,

    CASE
        WHEN ca.m3_totales = 0
            THEN NULL
        ELSE CAST
        (
            ca.m3_preliminar_acum / ca.m3_totales
            AS float
        )
    END AS avance_preliminar_pct_total,

    ca.fuente_reclamo,
    ca.metodo_calculo,
    ca.flag_preliminar

FROM con_acumulado ca;


GO

-- reclamo.v_preliminar_cv25_con_acumulado SHA256 5b8d3086a792abbc67f9faa05cf4eb01721dc7e6e8c8b8c1effe411d30ecc53e
/* ============================================================================
   CORRECCIÓN FINAL: v_preliminar_cv25_con_acumulado
   
   EL BUG: La fórmula anterior restaba al final, anulando la suma anterior
   
   CORRECCIÓN: 
   m3_preliminar_acum = m3_acum_ultima_topografia + SUM(m3_preliminar_dia)
   
   Sin restar nada. Simple suma de acumulados.
   ============================================================================ */

CREATE VIEW [reclamo].[v_preliminar_cv25_con_acumulado] AS
WITH abiertos AS
(
    SELECT [campaña_id], modulo_id, MAX(fecha_medicion) AS ultima_topografia_fecha
    FROM [reclamo].[v_topografia_resuelta]
    GROUP BY [campaña_id], modulo_id
),
cv AS
(
    SELECT 
        [campaña_id], 
        modulo_id, 
        ultima_topografia_fecha,
        (SELECT MAX(m3_reclamado_acum) 
         FROM [reclamo].[v_topografia_resuelta] tr
         WHERE tr.[campaña_id] = ab.[campaña_id]
           AND tr.modulo_id = ab.modulo_id
           AND tr.fecha_medicion = ab.ultima_topografia_fecha) AS m3_acum_ultima_topografia
    FROM abiertos ab
),
base AS
(
    SELECT 
        c.[campaña_id],
        c.modulo_id,
        c.m3_acum_ultima_topografia,
        pv.fecha_operacion,
        pv.m3_preliminar_dia,
        pv.tms_preliminar_dia,
        pv.fuente_reclamo,
        pv.metodo_calculo
    FROM cv c
    LEFT JOIN [reclamo].[v_preliminar_cv25] pv
        ON pv.[campaña_id] = c.[campaña_id]
       AND pv.modulo_id = c.modulo_id
       AND pv.fecha_operacion > c.ultima_topografia_fecha
),
preliminar_diario AS
(
    SELECT 
        [campaña_id],
        modulo_id,
        m3_acum_ultima_topografia,
        fecha_operacion,
        m3_preliminar_dia,
        tms_preliminar_dia,
        fuente_reclamo,
        metodo_calculo
    FROM base
),
preliminar_acum AS
(
    SELECT
        pd.[campaña_id],
        pd.modulo_id,
        pd.fecha_operacion,
        pd.m3_preliminar_dia,
        pd.tms_preliminar_dia,
        /* CORRECCIÓN: sumar acumulado anterior + preliminar actual (SIN restar nada) */
        COALESCE(pd.m3_acum_ultima_topografia, 0)
        + SUM(COALESCE(pd.m3_preliminar_dia, 0))
          OVER (
              PARTITION BY pd.[campaña_id], pd.modulo_id
              ORDER BY pd.fecha_operacion
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ) AS m3_preliminar_acum,
        COALESCE(pd.tms_preliminar_dia, 0) * 
        (
            SELECT COALESCE(densidad_oficial, 1) 
            FROM [reclamo].[v_modulo_base] mb
            WHERE mb.[campaña_id] = pd.[campaña_id]
              AND mb.modulo_id = pd.modulo_id
        )
        + SUM(COALESCE(pd.tms_preliminar_dia, 0) * 
              (SELECT COALESCE(densidad_oficial, 1) FROM [reclamo].[v_modulo_base] mb 
               WHERE mb.[campaña_id] = pd.[campaña_id] AND mb.modulo_id = pd.modulo_id))
          OVER (
              PARTITION BY pd.[campaña_id], pd.modulo_id
              ORDER BY pd.fecha_operacion
              ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
          ) AS tms_preliminar_acum,
        pd.m3_acum_ultima_topografia,
        pd.fuente_reclamo,
        pd.metodo_calculo
    FROM preliminar_diario pd
)
SELECT
    pa.fecha_operacion,
    pa.[campaña_id],
    pa.modulo_id,
    pa.tms_preliminar_dia,
    pa.m3_preliminar_dia,
    pa.m3_preliminar_acum,
    pa.m3_acum_ultima_topografia,
    pa.fuente_reclamo,
    pa.metodo_calculo
FROM preliminar_acum pa;

GO

-- reclamo.v_rendimiento_rotopala SHA256 fd04034b78db47de8ada9b2c43bd8b82ddba2a7d2331afe1a1e2493f1e96fa7c
/* ============================================================================
   V9. reclamo.v_rendimiento_rotopala

   Replica la hoja Rendimiento del libro de ripios: tms/hr por pesometro y por
   topografia, y su diferencia.

   Es el control de rendimiento que el usuario pidio: permite ver si una
   rotopala esta rindiendo por debajo de su tasa horaria habitual.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_rendimiento_rotopala]
AS
WITH topo_dia AS
(
    SELECT
        rd.fecha_operacion                  AS fecha,
        rd.rotopala_id,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_topografia,
        SUM(rd.tms_rotopala_dia)            AS tms_publicado,
        COUNT(*)                            AS modulos_con_movimiento
    FROM [reclamo].[v_reclamo_diario] rd
    WHERE rd.rotopala_id IS NOT NULL
    GROUP BY rd.fecha_operacion, rd.rotopala_id
)
SELECT
    d.fecha,
    r.rotopala_id,
    r.nombre                                AS rotopala,
    r.material,

    CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END AS horas_operacion,
    d.horas_total,
    d.tms_dia                               AS tms_cv25_dia_ambas,
    CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END
                                            AS tms_cv25_asignado,

    td.tms_topografia,
    td.tms_publicado,
    td.modulos_con_movimiento,

    /* Rendimiento en toneladas secas por hora. */
    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END,0) = 0
            THEN NULL
        ELSE (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
             / (CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END)
    END                                     AS rendimiento_pesometro_tms_hr,

    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END,0) = 0
            THEN NULL
        ELSE td.tms_topografia
             / (CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END)
    END                                     AS rendimiento_topografia_tms_hr,

    /* Diferencia entre lo que dice la correa y lo que dice la topografia. */
    td.tms_topografia
        - (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
                                            AS diferencia_tms,

    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1
                           ELSE d.tms_estimado_r2 END, 0) = 0 THEN NULL
        ELSE (td.tms_topografia
              - (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END))
             * 100.0
             / (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
    END                                     AS diferencia_pct,

    d.flag_preliminar                       AS flag_cv25
FROM [reclamo].[v_cv25_diario] d
CROSS JOIN [reclamo].[rotopala] r
LEFT JOIN topo_dia td
    ON  td.fecha       = d.fecha
    AND td.rotopala_id = r.rotopala_id
WHERE r.activa = 1;

GO

-- inventar_SpcHidr.vista_resumen_datos_filtrados SHA256 1e4fb62414e6e7634ad615ddaf128be945f95aaf7464c4f0b0cc00fa3ab94b86
CREATE VIEW [inventar_SpcHidr].[vista_resumen_datos_filtrados] AS WITH grp AS (
	SELECT
		df.fecha_turno,
		MIN(df.cv006_tot) AS min_cv006_tot,
		MAX(df.cv006_tot) AS max_cv006_tot,
		MIN(df.cv201_tot) / 1000.0 AS min_cv201_tot,
		MAX(df.cv201_tot) / 1000.0 AS max_cv201_tot,
		MIN(df.cv202_tot) / 1000.0 AS min_cv202_tot,
		MAX(df.cv202_tot) / 1000.0 AS max_cv202_tot,
		MIN(df.cv008_tot) AS min_cv008_tot,
		MAX(df.cv008_tot) AS max_cv008_tot,
		MIN(df.cv108_tot) AS min_cv108_tot,
		MAX(df.cv108_tot) AS max_cv108_tot,
		MIN(df.cv003_tot) AS min_cv003_tot,
		MAX(df.cv003_tot) AS max_cv003_tot,
		MIN(df.cv002_tot) AS min_cv002_tot,
		MAX(df.cv002_tot) AS max_cv002_tot,
		MIN(df.cv001_tot) AS min_cv001_tot,
		MAX(df.cv001_tot) AS max_cv001_tot,
		MIN(df.cv025tot) AS min_cv025tot,
		MAX(df.cv025tot) AS max_cv025tot,
		MIN(df.cv025_tot) AS min_cv025_tot,
		MAX(df.cv025_tot) AS max_cv025_tot,
		MIN(df.nivel_silo_a) AS min_niv_silo_a,
		MAX(df.nivel_silo_a) AS max_niv_silo_a,
		MIN(df.nivel_silo_b) AS min_niv_silo_b,
		MAX(df.nivel_silo_b) AS max_niv_silo_b,
		MIN(df.nivel_harnero_a) AS min_niv_har_a,
		MAX(df.nivel_harnero_a) AS max_niv_har_a,
		MIN(df.nivel_harnero_b) AS min_niv_har_b,
		MAX(df.nivel_harnero_b) AS max_niv_har_b,
		MIN(df.nivel_harnero_c) AS min_niv_har_c,
		MAX(df.nivel_harnero_c) AS max_niv_har_c,
		MIN(df.nivel_harnero_d) AS min_niv_har_d,
		MAX(df.nivel_harnero_d) AS max_niv_har_d,
		MIN(df.nivel_harnero_e) AS min_niv_har_e,
		MAX(df.nivel_harnero_e) AS max_niv_har_e,
		MIN(df.nivel_chancado_a) AS min_niv_cha_a,
		MAX(df.nivel_chancado_a) AS max_niv_cha_a,
		MIN(df.nivel_chancado_b) AS min_niv_cha_b,
		MAX(df.nivel_chancado_b) AS max_niv_cha_b,
		MIN(df.nivel_chancado_c) AS min_niv_cha_c,
		MAX(df.nivel_chancado_c) AS max_niv_cha_c,
		MIN(df.nivel_chancado_d) AS min_niv_cha_d,
		MAX(df.nivel_chancado_d) AS max_niv_cha_d,
		MIN(df.nivel_chancado_e) AS min_niv_cha_e,
		MAX(df.nivel_chancado_e) AS max_niv_cha_e,
		SUM(CASE WHEN df.RC002CORR IS NOT NULL THEN 1 ELSE 0 END) AS rc_002,
		SUM(CASE WHEN df.RC001CORR IS NOT NULL THEN 1 ELSE 0 END) AS rc_001
	FROM
		inventar_SpcHidr.datos_filtrados AS df
	GROUP BY
		df.fecha_turno
),
grp_with_next AS (
	SELECT
		g.*,
		LEAD (g.min_cv006_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv006_tot,
		LEAD (g.min_cv201_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv201_tot,
		LEAD (g.min_cv202_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv202_tot,
		LEAD (g.min_cv008_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv008_tot,
		LEAD (g.min_cv108_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv108_tot,
		LEAD (g.min_cv003_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv003_tot,
		LEAD (g.min_cv002_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv002_tot,
		LEAD (g.min_cv001_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv001_tot,
		LEAD (g.min_cv025tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv025tot,
		LEAD (g.min_cv025_tot) OVER (ORDER BY g.fecha_turno) AS next_min_cv025_tot,
		LEAD (g.min_niv_silo_a) OVER (ORDER BY g.fecha_turno) AS next_min_niv_silo_a,
		LEAD (g.min_niv_silo_b) OVER (ORDER BY g.fecha_turno) AS next_min_niv_silo_b,
		LEAD (g.min_niv_har_a) OVER (ORDER BY g.fecha_turno) AS next_min_niv_har_a,
		LEAD (g.min_niv_har_b) OVER (ORDER BY g.fecha_turno) AS next_min_niv_har_b,
		LEAD (g.min_niv_har_c) OVER (ORDER BY g.fecha_turno) AS next_min_niv_har_c,
		LEAD (g.min_niv_har_d) OVER (ORDER BY g.fecha_turno) AS next_min_niv_har_d,
		LEAD (g.min_niv_har_e) OVER (ORDER BY g.fecha_turno) AS next_min_niv_har_e,
		LEAD (g.min_niv_cha_a) OVER (ORDER BY g.fecha_turno) AS next_min_niv_cha_a,
		LEAD (g.min_niv_cha_b) OVER (ORDER BY g.fecha_turno) AS next_min_niv_cha_b,
		LEAD (g.min_niv_cha_c) OVER (ORDER BY g.fecha_turno) AS next_min_niv_cha_c,
		LEAD (g.min_niv_cha_d) OVER (ORDER BY g.fecha_turno) AS next_min_niv_cha_d,
		LEAD (g.min_niv_cha_e) OVER (ORDER BY g.fecha_turno) AS next_min_niv_cha_e
	FROM
		grp AS g
) SELECT
	gwn.fecha_turno,
	COALESCE(gwn.next_min_cv006_tot - gwn.min_cv006_tot, gwn.max_cv006_tot - gwn.min_cv006_tot) AS cv006_tot,
	CASE
		WHEN gwn.max_cv201_tot - gwn.min_cv201_tot < 0 THEN
			0
		WHEN gwn.next_min_cv201_tot IS NULL
			AND gwn.max_cv201_tot - gwn.min_cv201_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv201_tot - gwn.min_cv201_tot
		WHEN gwn.next_min_cv201_tot IS NULL THEN
			0
		WHEN gwn.next_min_cv201_tot - gwn.min_cv201_tot < 0
			AND gwn.max_cv201_tot - gwn.min_cv201_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv201_tot - gwn.min_cv201_tot
		WHEN gwn.next_min_cv201_tot - gwn.min_cv201_tot < 0 THEN
			0
		WHEN gwn.next_min_cv201_tot - gwn.min_cv201_tot BETWEEN 0
			AND 10000 THEN
			gwn.next_min_cv201_tot - gwn.min_cv201_tot
		WHEN gwn.max_cv201_tot - gwn.min_cv201_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv201_tot - gwn.min_cv201_tot
		ELSE
			0
	END AS cv201_tot,
	CASE
		WHEN gwn.max_cv202_tot - gwn.min_cv202_tot < 0 THEN
			0
		WHEN gwn.next_min_cv202_tot IS NULL
			AND gwn.max_cv202_tot - gwn.min_cv202_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv202_tot - gwn.min_cv202_tot
		WHEN gwn.next_min_cv202_tot IS NULL THEN
			0
		WHEN gwn.next_min_cv202_tot - gwn.min_cv202_tot < 0
			AND gwn.max_cv202_tot - gwn.min_cv202_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv202_tot - gwn.min_cv202_tot
		WHEN gwn.next_min_cv202_tot - gwn.min_cv202_tot < 0 THEN
			0
		WHEN gwn.next_min_cv202_tot - gwn.min_cv202_tot BETWEEN 0
			AND 10000 THEN
			gwn.next_min_cv202_tot - gwn.min_cv202_tot
		WHEN gwn.max_cv202_tot - gwn.min_cv202_tot BETWEEN 0
			AND 10000 THEN
			gwn.max_cv202_tot - gwn.min_cv202_tot
		ELSE
			0
	END AS cv202_tot,
	COALESCE(gwn.next_min_cv008_tot - gwn.min_cv008_tot, gwn.max_cv008_tot - gwn.min_cv008_tot) AS cv008_tot,
	COALESCE(gwn.next_min_cv108_tot - gwn.min_cv108_tot, gwn.max_cv108_tot - gwn.min_cv108_tot) AS cv108_tot,
	COALESCE(gwn.next_min_cv003_tot - gwn.min_cv003_tot, gwn.max_cv003_tot - gwn.min_cv003_tot) AS cv003_tot,
	COALESCE(gwn.next_min_cv002_tot - gwn.min_cv002_tot, gwn.max_cv002_tot - gwn.min_cv002_tot) AS cv002_tot,
	CASE
		WHEN COALESCE(gwn.next_min_cv001_tot - gwn.min_cv001_tot, gwn.max_cv001_tot - gwn.min_cv001_tot) > 100000 THEN
			0
		ELSE
			COALESCE(gwn.next_min_cv001_tot - gwn.min_cv001_tot, gwn.max_cv001_tot - gwn.min_cv001_tot)
	END AS cv001_tot,
	gwn.rc_002,
	gwn.rc_001,
	COALESCE(gwn.next_min_cv025tot - gwn.min_cv025tot, gwn.max_cv025tot - gwn.min_cv025tot) AS cv025tot,
	CASE
		WHEN gwn.max_cv025_tot - gwn.min_cv025_tot < 0 THEN
			0
		WHEN gwn.next_min_cv025_tot IS NULL
			AND gwn.max_cv025_tot - gwn.min_cv025_tot BETWEEN 0
			AND 100000 THEN
			gwn.max_cv025_tot - gwn.min_cv025_tot
		WHEN gwn.next_min_cv025_tot IS NULL THEN
			0
		WHEN gwn.next_min_cv025_tot - gwn.min_cv025_tot < 0
			AND gwn.max_cv025_tot - gwn.min_cv025_tot BETWEEN 0
			AND 100000 THEN
			gwn.max_cv025_tot - gwn.min_cv025_tot
		WHEN gwn.next_min_cv025_tot - gwn.min_cv025_tot < 0 THEN
			0
		WHEN gwn.next_min_cv025_tot - gwn.min_cv025_tot BETWEEN 0
			AND 100000 THEN
			gwn.next_min_cv025_tot - gwn.min_cv025_tot
		WHEN gwn.max_cv025_tot - gwn.min_cv025_tot BETWEEN 0
			AND 100000 THEN
			gwn.max_cv025_tot - gwn.min_cv025_tot
		ELSE
			0
	END AS cv025_tot,
	COALESCE(gwn.next_min_niv_silo_a - gwn.min_niv_silo_a, gwn.max_niv_silo_a - gwn.min_niv_silo_a) AS niv_silo_a,
	COALESCE(gwn.next_min_niv_silo_b - gwn.min_niv_silo_b, gwn.max_niv_silo_b - gwn.min_niv_silo_b) AS niv_silo_b,
	COALESCE(gwn.next_min_niv_har_a - gwn.min_niv_har_a, gwn.max_niv_har_a - gwn.min_niv_har_a) AS niv_har_a,
	COALESCE(gwn.next_min_niv_har_b - gwn.min_niv_har_b, gwn.max_niv_har_b - gwn.min_niv_har_b) AS niv_har_b,
	COALESCE(gwn.next_min_niv_har_c - gwn.min_niv_har_c, gwn.max_niv_har_c - gwn.min_niv_har_c) AS niv_har_c,
	COALESCE(gwn.next_min_niv_har_d - gwn.min_niv_har_d, gwn.max_niv_har_d - gwn.min_niv_har_d) AS niv_har_d,
	COALESCE(gwn.next_min_niv_har_e - gwn.min_niv_har_e, gwn.max_niv_har_e - gwn.min_niv_har_e) AS niv_har_e,
	COALESCE(gwn.next_min_niv_cha_a - gwn.min_niv_cha_a, gwn.max_niv_cha_a - gwn.min_niv_cha_a) AS niv_cha_a,
	COALESCE(gwn.next_min_niv_cha_b - gwn.min_niv_cha_b, gwn.max_niv_cha_b - gwn.min_niv_cha_b) AS niv_cha_b,
	COALESCE(gwn.next_min_niv_cha_c - gwn.min_niv_cha_c, gwn.max_niv_cha_c - gwn.min_niv_cha_c) AS niv_cha_c,
	COALESCE(gwn.next_min_niv_cha_d - gwn.min_niv_cha_d, gwn.max_niv_cha_d - gwn.min_niv_cha_d) AS niv_cha_d,
	COALESCE(gwn.next_min_niv_cha_e - gwn.min_niv_cha_e, gwn.max_niv_cha_e - gwn.min_niv_cha_e) AS niv_cha_e
FROM
	grp_with_next AS gwn;