/* ============================================================================
   SP 7. reclamo.sp_validar_reglas_negocio

   Verifica las reglas que el modelo no puede imponer por constraint porque
   dependen de varias filas a la vez. Devuelve un conjunto de hallazgos.

   Cero filas significa que la data cumple todas las reglas.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_validar_reglas_negocio]
(
    @FechaInicio date = NULL,
    @FechaFin    date = NULL
)
AS
BEGIN
    SET NOCOUNT ON;

    SET @FechaInicio = COALESCE(@FechaInicio, '1900-01-01');
    SET @FechaFin    = COALESCE(@FechaFin,    '2999-12-31');

    IF OBJECT_ID('tempdb..#Hallazgos') IS NOT NULL DROP TABLE #Hallazgos;
    CREATE TABLE #Hallazgos
    (
        regla       varchar(10),
        severidad   varchar(12),
        descripcion nvarchar(300),
        detalle     nvarchar(500)
    );

    /* R5 - mas de dos modulos abiertos por rotopala */
    INSERT INTO #Hallazgos
    SELECT
        'R5', 'CRITICO',
        N'Mas de dos modulos ABIERTOS para la misma rotopala',
        N'Rotopala ' + CAST(s.rotopala_id AS nvarchar(3))
            + N', campana ' + CAST(s.[campaña_id] AS nvarchar(10))
            + N', modulos abiertos: ' + CAST(COUNT(*) AS nvarchar(10))
    FROM [reclamo].[secuencia_rotopala] s
    WHERE s.estado = 'ABIERTO'
    GROUP BY s.rotopala_id, s.[campaña_id]
    HAVING COUNT(*) > 2;

    /* R5 - retroceso en la secuencia */
    /* CORRECCION 30-07-2026: la particion incluye la campana. El script 00
       mostro que al iniciar una campana nueva la numeracion se reinicia (por
       ejemplo, en el PAD 1 el 15-07-2025 se pasa de M64 a M1). Sin particionar
       por campana ese reinicio se contaba como retroceso. */
    ;WITH mov AS
    (
        SELECT
            cd.fecha_operacion,
            cd.rotopala_id,
            cd.[campaña_id],
            MAX(cd.modulo_numero) AS modulo_max
        FROM [reclamo].[calculo_diario] cd
        WHERE cd.tms_rotopala_dia > 0
          AND cd.rotopala_id IS NOT NULL
          AND cd.fecha_operacion BETWEEN @FechaInicio AND @FechaFin
        GROUP BY cd.fecha_operacion, cd.rotopala_id, cd.[campaña_id]
    ),
    sec AS
    (
        SELECT
            m.*,
            LAG(m.modulo_max) OVER
            (
                PARTITION BY m.rotopala_id, m.[campaña_id]
                ORDER BY m.fecha_operacion
            ) AS modulo_max_ant
        FROM mov m
    )
    INSERT INTO #Hallazgos
    SELECT
        'R5', 'ADVERTENCIA',
        N'La rotopala retrocedio a un modulo de numero menor dentro de la misma campana',
        N'Fecha ' + CONVERT(nvarchar(10), s.fecha_operacion, 120)
            + N', rotopala ' + CAST(s.rotopala_id AS nvarchar(3))
            + N', campana ' + CAST(s.[campaña_id] AS nvarchar(10))
            + N', de M' + CAST(s.modulo_max_ant AS nvarchar(10))
            + N' a M'  + CAST(s.modulo_max AS nvarchar(10))
    FROM sec s
    WHERE s.modulo_max_ant IS NOT NULL
      AND s.modulo_max < s.modulo_max_ant;

    /* R6 - rotopala reclamando de un PAD que no le corresponde */
    INSERT INTO #Hallazgos
    SELECT
        'R6', 'CRITICO',
        N'Reclamo de rotopala en un PAD que no le corresponde',
        N'Fecha ' + CONVERT(nvarchar(10), cd.fecha_operacion, 120)
            + N', rotopala ' + CAST(cd.rotopala_id AS nvarchar(3))
            + N', pad ' + CAST(cd.pad_id AS nvarchar(10))
    FROM [reclamo].[calculo_diario] cd
    INNER JOIN [reclamo].[rotopala] r ON r.rotopala_id = cd.rotopala_id
    WHERE cd.pad_id <> r.pad_id
      AND cd.fecha_operacion BETWEEN @FechaInicio AND @FechaFin;

    /* R3 - rotopala antes de cerrar camiones en el mismo modulo.
       DEGRADADO A ALERTA el 30-07-2026 por decision del usuario: el
       solapamiento ocurre en la practica y no invalida el dato. Se reporta
       para que alguien lo mire, no para impedir la publicacion. */
    ;WITH prim AS
    (
        SELECT
            cd.[campaña_id], cd.modulo_id,
            MIN(cd.fecha_operacion) AS primera_roto
        FROM [reclamo].[calculo_diario] cd
        WHERE cd.tms_rotopala_dia > 0
        GROUP BY cd.[campaña_id], cd.modulo_id
    ),
    ult AS
    (
        SELECT
            c.[campaña_id], c.modulo_id,
            MAX(c.fecha) AS ultimo_camion
        FROM [reclamo].[camiones_reclamo] c
        WHERE c.estado = 'VIGENTE' AND COALESCE(c.m3_oficial,0) > 0
        GROUP BY c.[campaña_id], c.modulo_id
    )
    INSERT INTO #Hallazgos
    SELECT
        'R3', 'ALERTA',
        N'La rotopala comenzo antes de cerrar el reclamo por camiones',
        N'Campana ' + CAST(p.[campaña_id] AS nvarchar(10))
            + N', modulo ' + CAST(p.modulo_id AS nvarchar(10))
            + N', roto ' + CONVERT(nvarchar(10), p.primera_roto, 120)
            + N' vs ultimo camion ' + CONVERT(nvarchar(10), u.ultimo_camion, 120)
    FROM prim p
    INNER JOIN ult u
        ON u.[campaña_id] = p.[campaña_id] AND u.modulo_id = p.modulo_id
    WHERE p.primera_roto < u.ultimo_camion;

    /* R9 - cuadratura sobre 100 por ciento */
    INSERT INTO #Hallazgos
    SELECT
        'R9', 'CRITICO',
        N'Extraccion acumulada sobre el 100 por ciento del volumen del modulo',
        N'Modulo M' + CAST(cm.modulo_numero AS nvarchar(10))
            + N', ' + CAST(CAST(cm.porcentaje_extraido AS decimal(9,2)) AS nvarchar(20)) + N' %'
            + N', excedente ' + CAST(CAST(cm.m3_excedente AS decimal(18,1)) AS nvarchar(30)) + N' m3'
            + N'. Modulo siguiente propuesto: ' + COALESCE(CAST(cm.modulo_siguiente_propuesto AS nvarchar(10)), N'ninguno')
    FROM [reclamo].[v_cuadratura_modulo] cm
    WHERE cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO';

    /* R10 - ajustes aprobados sin antecedente util */
    INSERT INTO #Hallazgos
    SELECT
        'R10', 'CRITICO',
        N'Ajuste aprobado con antecedente vacio o generico',
        N'ajuste_id ' + CAST(a.ajuste_id AS nvarchar(10))
            + N', tipo ' + a.tipo_ajuste
            + N', ref: ' + COALESCE(a.antecedente_ref, N'(vacio)')
    FROM [reclamo].[ajuste_manual] a
    WHERE a.estado = 'APROBADO'
      AND (a.antecedente_ref IS NULL OR LEN(LTRIM(RTRIM(a.antecedente_ref))) < 10);

    /* R2 - modulo fuera del rango fisico de su PAD.
       Oxido 1 a 64 (32 parcelas x 2), sulfuro 1 a 140 (28 parcelas x 5). */
    INSERT INTO #Hallazgos
    SELECT
        'R2', 'CRITICO',
        N'Modulo fuera del rango fisico del PAD',
        N'Campana ' + CAST(mb.[campaña_id] AS nvarchar(10))
            + N', PAD ' + CAST(mb.pad_id AS nvarchar(10))
            + N', modulo M' + CAST(mb.modulo_numero AS nvarchar(10))
            + N'. Rango valido: 1 a ' + CAST(mb.modulo_numero_max AS nvarchar(10))
    FROM [reclamo].[v_modulo_base] mb
    WHERE mb.flag_topologia = 'MODULO_FUERA_DEL_RANGO_DEL_PAD';

    /* R1 - reclamo sobre modulos no congelados */
    INSERT INTO #Hallazgos
    SELECT
        'R1', 'CRITICO',
        N'Existe reclamo sobre un modulo que no esta congelado',
        N'Campana ' + CAST(cd.[campaña_id] AS nvarchar(10))
            + N', modulo ' + CAST(cd.modulo_id AS nvarchar(10))
    FROM [reclamo].[calculo_diario] cd
    WHERE cd.tms_conformado IS NULL
      AND cd.fecha_operacion BETWEEN @FechaInicio AND @FechaFin
    GROUP BY cd.[campaña_id], cd.modulo_id;

    SELECT
        h.regla,
        h.severidad,
        h.descripcion,
        h.detalle
    FROM #Hallazgos h
    ORDER BY
        CASE h.severidad WHEN 'CRITICO' THEN 1 ELSE 2 END,
        h.regla,
        h.detalle;

    DECLARE @N int = (SELECT COUNT(*) FROM #Hallazgos);
    IF @N = 0
        PRINT 'Sin hallazgos. La data cumple todas las reglas verificables.';
    ELSE
        PRINT 'Hallazgos encontrados: ' + CAST(@N AS varchar);

    DROP TABLE #Hallazgos;
END;