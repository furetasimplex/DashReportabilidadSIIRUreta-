CREATE VIEW [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto]
AS
WITH pi_raw AS (
    SELECT CAST(v.fecha_turno AS date) AS fecha,
           MAX(CAST(v.cv025tot AS decimal(30,12))) AS pi_diario_original,
           MAX(CAST(v.cv025_tot AS decimal(30,12))) AS pi_alternativo,
           COUNT_BIG(*) AS pi_filas_dia
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v
    GROUP BY CAST(v.fecha_turno AS date)
), turnos AS (
    SELECT r.fecha_operacional AS fecha,
           UPPER(LTRIM(RTRIM(r.turno))) AS turno,
           r.estado_tecnico_pi,
           r.tum_disponible,
           r.tipo_tum,
           CAST(r.valor_turno_tum AS decimal(30,12)) AS tum_turno,
           CAST(r.valor_pi_final AS decimal(30,12)) AS pi_turno,
           r.tum_batch_id,
           r.archivo_batch
    FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno AS r
    WHERE r.equipo_codigo = 'RIPIOS_CV025'
), tum_dia AS (
    SELECT fecha,
           COUNT_BIG(*) AS turnos_observados,
           SUM(CASE WHEN turno IN ('A','B') AND tum_disponible=1
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>=0
                    THEN 1 ELSE 0 END) AS turnos_tum_directo,
           SUM(CASE WHEN turno IN ('A','B') AND tum_disponible=1
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>=0
                    THEN tum_turno ELSE CAST(0 AS decimal(30,12)) END) AS tum_diario,
           MAX(CASE WHEN (estado_tecnico_pi LIKE 'SIN_CAMBIO%' OR estado_tecnico_pi='SIN_PI')
                         AND tipo_tum='TUM_DIRECTO' AND tum_turno>0 THEN 1 ELSE 0 END) AS inicia_contingencia,
           MAX(CASE WHEN estado_tecnico_pi LIKE 'CON_VARIACION%' AND pi_turno>0
                    THEN 1 ELSE 0 END) AS recupera_pi,
           MAX(CASE WHEN estado_tecnico_pi LIKE 'SIN_CAMBIO%' THEN 1 ELSE 0 END) AS pi_plano,
           MAX(CASE WHEN turno='A' THEN tum_batch_id END) AS tum_batch_id_a,
           MAX(CASE WHEN turno='B' THEN tum_batch_id END) AS tum_batch_id_b,
           MAX(CASE WHEN turno='A' THEN archivo_batch END) AS archivo_batch_a,
           MAX(CASE WHEN turno='B' THEN archivo_batch END) AS archivo_batch_b
    FROM turnos
    GROUP BY fecha
), dias AS (
    SELECT COALESCE(p.fecha,t.fecha) AS fecha,
           p.pi_diario_original,p.pi_alternativo,p.pi_filas_dia,
           CASE WHEN t.turnos_observados=2 AND t.turnos_tum_directo=2
                THEN CAST(1 AS bit) ELSE CAST(0 AS bit) END AS tum_completo,
           CASE WHEN t.turnos_observados=2 AND t.turnos_tum_directo=2
                THEN t.tum_diario ELSE NULL END AS tum_diario,
           ISNULL(t.inicia_contingencia,0) AS inicia_contingencia,
           ISNULL(t.recupera_pi,0) AS recupera_pi,
           ISNULL(t.pi_plano,0) AS pi_plano,
           t.tum_batch_id_a,t.tum_batch_id_b,t.archivo_batch_a,t.archivo_batch_b
    FROM pi_raw AS p FULL OUTER JOIN tum_dia AS t ON t.fecha=p.fecha
), grupos AS (
    SELECT d.*,
           ISNULL(SUM(d.recupera_pi) OVER (ORDER BY d.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) AS grupo_recuperacion
    FROM dias AS d
), semillas AS (
    SELECT g.*,
           MIN(CASE WHEN g.inicia_contingencia=1 THEN g.fecha END)
               OVER (PARTITION BY g.grupo_recuperacion) AS fecha_inicio_episodio
    FROM grupos AS g
), dias_episodio AS (
    SELECT s.*
    FROM semillas AS s
    WHERE s.fecha_inicio_episodio IS NOT NULL AND s.fecha>=s.fecha_inicio_episodio
), balances AS (
    SELECT grupo_recuperacion,fecha_inicio_episodio,
           MAX(CASE WHEN recupera_pi=1 THEN fecha END) AS fecha_recuperacion,
           SUM(CASE WHEN pi_diario_original IS NULL OR pi_filas_dia<>1 THEN 1 ELSE 0 END) AS dias_sin_pi_unico,
           SUM(CASE WHEN tum_completo=0 THEN 1 ELSE 0 END) AS dias_sin_tum_completo,
           SUM(pi_diario_original) AS masa_pi_episodio,
           SUM(tum_diario) AS masa_tum_episodio
    FROM dias_episodio
    GROUP BY grupo_recuperacion,fecha_inicio_episodio
)
SELECT s.fecha,
       s.pi_diario_original,s.pi_alternativo,s.tum_diario,s.tum_completo,
       CAST(CASE WHEN s.recupera_pi=1 AND b.fecha_inicio_episodio IS NOT NULL THEN 'RECUPERACION'
                 WHEN s.pi_plano=1 THEN 'PI_PLANO'
                 WHEN s.pi_diario_original IS NULL THEN 'SIN_PI'
                 ELSE 'NORMAL_PI' END AS varchar(30)) AS estado_pi_dia,
       CASE WHEN b.fecha_inicio_episodio IS NOT NULL
            THEN CONCAT('CV025_',CONVERT(char(8),b.fecha_inicio_episodio,112)) END AS episodio_id,
       b.fecha_inicio_episodio,b.fecha_recuperacion,
       b.masa_pi_episodio,b.masa_tum_episodio,
       CASE WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
            THEN b.masa_pi_episodio-b.masa_tum_episodio END AS residual_masa,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_filas_dia>1 THEN 'PI_DIARIO_DUPLICADO'
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_plano=1 AND s.tum_completo=0 THEN 'SIN_TUM_NO_RESOLUBLE'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'NORMAL_PI'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'CONTINGENCIA_TUM_ABIERTA'
           WHEN b.fecha_recuperacion IS NULL THEN 'SIN_TUM_NO_RESOLUBLE'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'CONTINGENCIA_TUM_RECONCILIADA'
           ELSE 'RECUPERACION_REQUIERE_REVISION' END AS varchar(45)) AS estado_episodio,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND
                (s.pi_filas_dia>1 OR (s.pi_plano=1 AND s.tum_completo=0)) THEN 'SIN_RESOLVER'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'PI'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'TUM_PROVISIONAL'
           WHEN b.fecha_recuperacion IS NULL THEN 'SIN_RESOLVER'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'TUM'
           ELSE 'SIN_RESOLVER' END AS varchar(25)) AS fuente_resuelta_dia,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND
                (s.pi_filas_dia>1 OR (s.pi_plano=1 AND s.tum_completo=0)) THEN NULL
           WHEN b.fecha_inicio_episodio IS NULL THEN s.pi_diario_original
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN s.tum_diario
           WHEN b.fecha_recuperacion IS NULL THEN NULL
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN s.tum_diario
           ELSE NULL END AS decimal(30,12)) AS tmh_resuelto,
       CAST(CASE
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_filas_dia>1 THEN 'PI_DIARIO_DUPLICADO'
           WHEN b.fecha_inicio_episodio IS NULL AND s.pi_plano=1 AND s.tum_completo=0 THEN 'FALTA_TUM_DIRECTO'
           WHEN b.fecha_inicio_episodio IS NULL THEN 'PI_SIN_EPISODIO'
           WHEN b.fecha_recuperacion IS NULL AND s.tum_completo=1 THEN 'ESPERANDO_RECUPERACION_PI'
           WHEN b.fecha_recuperacion IS NULL THEN 'FALTA_TUM_DIRECTO'
           WHEN b.dias_sin_pi_unico=0 AND b.dias_sin_tum_completo=0
                AND b.masa_pi_episodio=b.masa_tum_episodio THEN 'MASA_PI_TUM_EXACTA'
           ELSE 'MASA_O_COBERTURA_NO_RECONCILIADA' END AS varchar(50)) AS motivo_resolucion,
       s.tum_batch_id_a,s.tum_batch_id_b,s.archivo_batch_a,s.archivo_batch_b
FROM semillas AS s
LEFT JOIN balances AS b ON b.grupo_recuperacion=s.grupo_recuperacion
                       AND s.fecha>=b.fecha_inicio_episodio;
GO

ALTER TABLE [reclamo].[cv25_diario] DROP CONSTRAINT [CK_cv_tag];
ALTER TABLE [reclamo].[cv25_diario] WITH CHECK ADD CONSTRAINT [CK_cv_tag]
CHECK ([tag_utilizado] IN ('cv025tot','cv025_tot','TUM_CV025','SIN_RESOLVER'));
GO

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

    /* ---- 3.a  PI crudo + CV025 resuelto por episodio ------------------- */
    MERGE [reclamo].[cv25_diario] AS tgt
    USING
    (
        SELECT r.fecha,
               r.pi_diario_original AS tmh_cv025tot,
               r.pi_alternativo AS tmh_cv025_tot,
               CAST(v.rc_001 AS int) AS horas_con_dato_r1,
               CAST(v.rc_002 AS int) AS horas_con_dato_r2,
               CASE WHEN @TagOficial='cv025tot' THEN r.tmh_resuelto
                    ELSE r.pi_alternativo END AS tmh_final_elegido,
               CASE WHEN @TagOficial='cv025tot' THEN r.fuente_resuelta_dia
                    ELSE 'PI' END AS fuente_resuelta_dia,
               CASE WHEN @TagOficial='cv025tot' THEN r.estado_episodio
                    ELSE 'NORMAL_PI' END AS estado_episodio,
               r.episodio_id,r.fecha_inicio_episodio,r.fecha_recuperacion,
               r.residual_masa,r.motivo_resolucion,
               r.tum_batch_id_a,r.tum_batch_id_b
        FROM [inventar_SpcHidr].[v_contingencia_cv025_diario_resuelto] AS r
        LEFT JOIN [inventar_SpcHidr].[vista_resumen_datos_filtrados] AS v
          ON CAST(v.fecha_turno AS date)=r.fecha
        WHERE r.fecha BETWEEN @FechaInicio AND @FechaFin
    ) AS src ON tgt.fecha=src.fecha
    WHEN MATCHED THEN UPDATE SET
        tmh_cv025tot=src.tmh_cv025tot,
        tmh_cv025_tot=src.tmh_cv025_tot,
        horas_con_dato_r1=src.horas_con_dato_r1,
        horas_con_dato_r2=src.horas_con_dato_r2,
        tag_utilizado=CASE WHEN src.fuente_resuelta_dia IN ('TUM','TUM_PROVISIONAL')
                           THEN 'TUM_CV025'
                           WHEN src.fuente_resuelta_dia='SIN_RESOLVER' THEN 'SIN_RESOLVER'
                           ELSE @TagOficial END,
        tmh_dia=CASE WHEN src.tmh_final_elegido<0 THEN NULL ELSE src.tmh_final_elegido END,
        humedad_pct=COALESCE(@HumedadPct,tgt.humedad_pct),
        tms_dia=CASE WHEN src.tmh_final_elegido<0 THEN NULL
                     WHEN COALESCE(@HumedadPct,tgt.humedad_pct) IS NULL THEN src.tmh_final_elegido
                     ELSE src.tmh_final_elegido*(1.0-COALESCE(@HumedadPct,tgt.humedad_pct)/100.0) END,
        fuente=CASE WHEN src.fuente_resuelta_dia='PI' THEN 'VISTA_RESUMEN_DATOS_FILTRADOS'
                    ELSE 'CONTINGENCIA_PI_TUM_CV025' END,
        metodo=CASE WHEN src.fuente_resuelta_dia='PI' THEN 'DELTA_TOTALIZADOR_CV25_DIARIO'
                    ELSE 'EPISODIO_CV025_PI_TUM' END,
        flag=CASE WHEN src.estado_episodio='RECUPERACION_REQUIERE_REVISION' THEN 'RECUPERACION_REVISAR'
                  WHEN src.estado_episodio='SIN_TUM_NO_RESOLUBLE' THEN 'SIN_TUM_NO_RESOLUBLE'
                  WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                       AND src.fuente_resuelta_dia='PI' THEN 'SIN_TOTALIZADOR'
                  WHEN src.tmh_final_elegido<0 THEN 'DELTA_NEGATIVO_REVISAR'
                  WHEN src.estado_episodio='CONTINGENCIA_TUM_ABIERTA' THEN 'CONTINGENCIA_ABIERTA'
                  WHEN COALESCE(src.tmh_cv025tot,0)=0
                       AND COALESCE(src.horas_con_dato_r1,0)+COALESCE(src.horas_con_dato_r2,0)=0
                       THEN 'SIN_OPERACION'
                  ELSE 'OK' END,
        observacion=CASE WHEN src.episodio_id IS NULL THEN NULL
                    ELSE CONCAT('episodio=',src.episodio_id,'; inicio=',CONVERT(varchar(10),src.fecha_inicio_episodio,23),
                        '; recuperacion=',CONVERT(varchar(10),src.fecha_recuperacion,23),
                        '; estado=',src.estado_episodio,'; residual=',CONVERT(varchar(50),src.residual_masa),
                        '; TUM_A=',CONVERT(varchar(20),src.tum_batch_id_a),
                        '; TUM_B=',CONVERT(varchar(20),src.tum_batch_id_b)) END,
        fecha_registro=SYSDATETIME()
    WHEN NOT MATCHED BY TARGET THEN INSERT
        (fecha,tmh_cv025tot,tmh_cv025_tot,tmh_dia,humedad_pct,tms_dia,
         horas_con_dato_r1,horas_con_dato_r2,tag_utilizado,fuente,metodo,flag,observacion)
    VALUES
        (src.fecha,src.tmh_cv025tot,src.tmh_cv025_tot,
         CASE WHEN src.tmh_final_elegido<0 THEN NULL ELSE src.tmh_final_elegido END,
         @HumedadPct,
         CASE WHEN src.tmh_final_elegido<0 THEN NULL
              WHEN @HumedadPct IS NULL THEN src.tmh_final_elegido
              ELSE src.tmh_final_elegido*(1.0-@HumedadPct/100.0) END,
         src.horas_con_dato_r1,src.horas_con_dato_r2,
         CASE WHEN src.fuente_resuelta_dia IN ('TUM','TUM_PROVISIONAL') THEN 'TUM_CV025'
              WHEN src.fuente_resuelta_dia='SIN_RESOLVER' THEN 'SIN_RESOLVER'
              ELSE @TagOficial END,
         CASE WHEN src.fuente_resuelta_dia='PI' THEN 'VISTA_RESUMEN_DATOS_FILTRADOS'
              ELSE 'CONTINGENCIA_PI_TUM_CV025' END,
         CASE WHEN src.fuente_resuelta_dia='PI' THEN 'DELTA_TOTALIZADOR_CV25_DIARIO'
              ELSE 'EPISODIO_CV025_PI_TUM' END,
         CASE WHEN src.estado_episodio='RECUPERACION_REQUIERE_REVISION' THEN 'RECUPERACION_REVISAR'
              WHEN src.estado_episodio='SIN_TUM_NO_RESOLUBLE' THEN 'SIN_TUM_NO_RESOLUBLE'
              WHEN src.tmh_cv025tot IS NULL AND src.tmh_cv025_tot IS NULL
                   AND src.fuente_resuelta_dia='PI' THEN 'SIN_TOTALIZADOR'
              WHEN src.tmh_final_elegido<0 THEN 'DELTA_NEGATIVO_REVISAR'
              WHEN src.estado_episodio='CONTINGENCIA_TUM_ABIERTA' THEN 'CONTINGENCIA_ABIERTA'
              WHEN COALESCE(src.tmh_cv025tot,0)=0
                   AND COALESCE(src.horas_con_dato_r1,0)+COALESCE(src.horas_con_dato_r2,0)=0
                   THEN 'SIN_OPERACION'
              ELSE 'OK' END,
         CASE WHEN src.episodio_id IS NULL THEN NULL
              ELSE CONCAT('episodio=',src.episodio_id,'; inicio=',CONVERT(varchar(10),src.fecha_inicio_episodio,23),
                  '; recuperacion=',CONVERT(varchar(10),src.fecha_recuperacion,23),
                  '; estado=',src.estado_episodio,'; residual=',CONVERT(varchar(50),src.residual_masa),
                  '; TUM_A=',CONVERT(varchar(20),src.tum_batch_id_a),
                  '; TUM_B=',CONVERT(varchar(20),src.tum_batch_id_b)) END);

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
        WHEN cv.tms_dia IS NULL THEN NULL
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
        WHEN cv.tms_dia IS NULL THEN NULL
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

        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'
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
        WHEN cv.tms_dia IS NULL THEN 'SIN_RESOLVER_CV25'
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
