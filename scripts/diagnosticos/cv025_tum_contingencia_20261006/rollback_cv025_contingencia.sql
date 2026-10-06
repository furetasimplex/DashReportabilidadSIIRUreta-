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

ALTER PROCEDURE [reclamo].[sp_cargar_cv25_horas]
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

ALTER VIEW [reclamo].[v_cv25_diario]
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

/* ============================================================================
   V10. reclamo.v_diferencia_cv25

   Agregado diario a nivel planta del contraste entre el totalizador y la
   topografia. Es la vista que alimenta el grafico principal del dashboard.

   Regla R7: CV25 recibe la carga conjunta de ambas rotopalas y NO recibe
   camiones. Por eso la comparacion se hace contra el reclamo de rotopala
   solamente, sin sumar camiones.
   ============================================================================ */
ALTER VIEW [reclamo].[v_diferencia_cv25]
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

UPDATE [reclamo].[cv25_diario]
SET tmh_dia=CASE WHEN tmh_cv025tot<0 THEN NULL ELSE tmh_cv025tot END,
    tms_dia=CASE WHEN tmh_cv025tot<0 THEN NULL WHEN humedad_pct IS NULL THEN tmh_cv025tot
                 ELSE tmh_cv025tot*(1.0-humedad_pct/100.0) END,
    tag_utilizado='cv025tot',fuente='VISTA_RESUMEN_DATOS_FILTRADOS',
    metodo='DELTA_TOTALIZADOR_CV25_DIARIO',observacion=NULL,
    flag=CASE WHEN tmh_cv025tot IS NULL AND tmh_cv025_tot IS NULL THEN 'SIN_TOTALIZADOR'
              WHEN tmh_cv025tot<0 THEN 'DELTA_NEGATIVO_REVISAR'
              WHEN COALESCE(tmh_cv025tot,0)=0
                   AND COALESCE(horas_con_dato_r1,0)+COALESCE(horas_con_dato_r2,0)=0
                   THEN 'SIN_OPERACION' ELSE 'OK' END
WHERE tag_utilizado IN ('TUM_CV025','SIN_RESOLVER');
GO

ALTER TABLE [reclamo].[cv25_diario] DROP CONSTRAINT [CK_cv_tag];
ALTER TABLE [reclamo].[cv25_diario] WITH CHECK ADD CONSTRAINT [CK_cv_tag]
CHECK ([tag_utilizado]='cv025_tot' OR [tag_utilizado]='cv025tot');
GO

DROP VIEW [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto];
