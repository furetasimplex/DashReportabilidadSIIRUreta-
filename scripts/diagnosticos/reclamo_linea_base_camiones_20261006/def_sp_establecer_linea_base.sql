/* ============================================================================
   SP 3.b reclamo.sp_establecer_linea_base

   Fija, de una sola vez, cuanto se habia extraido de cada modulo ANTES de la
   fecha de corte del sistema.

   Es la pieza que hace viable la decision de no operar retroactivamente. El
   sistema arranca el 1 de julio de 2026 y no recalcula el pasado, pero
   tampoco puede ignorarlo: un modulo que venia reclamandose desde mayo
   apareceria como intacto y la cuadratura daria cualquier cosa.

   La linea base se toma de las tablas historicas, con fecha ESTRICTAMENTE
   ANTERIOR al corte, y queda congelada en modulo_congelado. No se vuelve a
   calcular salvo que se ejecute este procedimiento otra vez.

   @SoloSiVacio (agregado 2026-07-30, default 1 = seguro): solo establece
   linea base en modulos donde fecha_linea_base todavia esta NULL. Nunca
   toca un modulo que ya tiene linea base establecida. Esto es lo que hace
   seguro llamarlo repetidas veces -- en particular, desde
   sp_auto_congelar_modulos_nuevos cada vez que congela un modulo nuevo,
   sin riesgo de pisar la linea base ya buena de otro modulo de la misma
   campaña. Antes de este cambio, cualquier modulo que se congelara despues
   de la corrida manual original quedaba con m3_rotopala_previo = 0 para
   siempre, porque nadie volvia a correr este procedimiento para el
   (confirmado en los modulos 33, 34, 35, 36 y 38 de PAD1, campaña 4).

   Para forzar un recalculo deliberado de una linea base ya existente
   (recalibracion manual, no el uso normal), pasar @SoloSiVacio = 0. En ese
   caso sigue aplicando la advertencia original: sobrescribe lo que haya.

   IMPORTANTE: en su uso normal (@SoloSiVacio = 1) es seguro y esperable
   ejecutarlo muchas veces; cada modulo solo recibe su linea base una vez,
   la primera vez que sp_establecer_linea_base lo ve con fecha_linea_base
   NULL.

   @Silencioso (agregado 2026-07-30, default 0): cuando esta en 1, no emite
   los SELECT de vista previa ni de "ATENCION sobre 100 % al corte". Es
   para el llamado automatico desde sp_auto_congelar_modulos_nuevos: ese
   procedimiento es invocado, a su vez, desde sp_auto_mantener_secuencia y
   desde ahi desde el dashboard, que espera UN SOLO result set (el resumen
   final de cambios/alertas). Si sp_establecer_linea_base devolviera sus
   propios SELECT en medio de esa cadena, el dashboard leeria el result set
   equivocado. En uso manual interactivo se deja en 0 (default) para ver la
   vista previa como siempre.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_establecer_linea_base]
(
    @CampañaId    int = NULL,
    @PadId        int = NULL,
    @Confirmar    bit = 0,
    @SoloSiVacio  bit = 1,
    @Silencioso   bit = 0
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @Corte date = [reclamo].[fn_fecha_corte]();

    IF @Corte IS NULL
        THROW 60601,
              'No hay FECHA_CORTE_SISTEMA en reclamo.configuracion.', 1;

    PRINT '-- Fecha de corte del sistema: ' + CONVERT(varchar(10), @Corte, 120);
    PRINT '-- Se acumula todo lo anterior a esa fecha como linea base.';
    PRINT CASE WHEN @SoloSiVacio = 1
               THEN '-- Modo seguro: solo modulos sin linea base todavia.'
               ELSE '-- Modo forzado: recalcula y pisa la linea base existente.'
          END;

    IF OBJECT_ID('tempdb..#LineaBase') IS NOT NULL DROP TABLE #LineaBase;

    SELECT
        mc.[campaña_id],
        mc.modulo_id,
        mc.modulo_numero,
        mc.pad_id,
        mc.m3_totales,
        COALESCE(
        (
            SELECT SUM(COALESCE(crc.volumen_diario_m3, 0))
            FROM [inventar_SpcHidr].[control_reclamo_sulfuro_camiones_thm_diario] crc
            WHERE crc.[campaña_id] = mc.[campaña_id]
              AND crc.modulo_id    = mc.modulo_id
              AND CAST(crc.fecha AS date) < @Corte
        ), 0)                                       AS m3_camiones_previo,
        COALESCE(
        (
            SELECT SUM(COALESCE(cr.volumen_diario_m3, 0))
            FROM [inventar_SpcHidr].[control_reclamo_diario] cr
            WHERE cr.[campaña_id] = mc.[campaña_id]
              AND cr.modulo_id    = mc.modulo_id
              AND CAST(cr.fecha AS date) < @Corte
        ), 0)                                       AS m3_rotopala_previo
    INTO #LineaBase
    FROM [reclamo].[modulo_congelado] mc
    WHERE mc.estado = 'CONGELADO'
      AND (@CampañaId   IS NULL OR mc.[campaña_id] = @CampañaId)
      AND (@PadId       IS NULL OR mc.pad_id       = @PadId)
      AND (@SoloSiVacio = 0    OR mc.fecha_linea_base IS NULL);

    /* Vista previa antes de escribir. Se omite en modo silencioso. */
    IF @Silencioso = 0
    BEGIN
        SELECT
            lb.[campaña_id],
            lb.pad_id,
            lb.modulo_numero,
            lb.m3_totales,
            lb.m3_camiones_previo,
            lb.m3_rotopala_previo,
            lb.m3_camiones_previo + lb.m3_rotopala_previo AS m3_extraido_previo,
            CASE
                WHEN lb.m3_totales = 0 THEN NULL
                ELSE (lb.m3_camiones_previo + lb.m3_rotopala_previo) * 100.0 / lb.m3_totales
            END                                           AS pct_previo,
            lb.m3_totales - (lb.m3_camiones_previo + lb.m3_rotopala_previo)
                                                          AS m3_saldo_al_corte,
            CASE
                WHEN lb.m3_totales = 0
                    THEN 'SIN_VOLUMEN'
                WHEN lb.m3_camiones_previo + lb.m3_rotopala_previo > lb.m3_totales
                    THEN 'YA_SOBRE_100_AL_CORTE'
                WHEN (lb.m3_camiones_previo + lb.m3_rotopala_previo) * 100.0 / lb.m3_totales > 99
                    THEN 'AGOTADO_AL_CORTE'
                WHEN lb.m3_camiones_previo + lb.m3_rotopala_previo = 0
                    THEN 'SIN_MOVIMIENTO_PREVIO'
                ELSE 'CON_SALDO'
            END                                           AS situacion_al_corte
        FROM #LineaBase lb
        ORDER BY lb.pad_id, lb.modulo_numero;
    END;

    IF @Confirmar = 0
    BEGIN
        PRINT '';
        PRINT 'MODO VISTA PREVIA. No se escribio nada.';
        PRINT 'Revise el resultado y vuelva a ejecutar con @Confirmar = 1.';
        DROP TABLE #LineaBase;
        RETURN;
    END;

    /* Se usa MERGE y no UPDATE ... FROM con alias.

       Motivo: UPDATE <alias> SET ... FROM <tabla> AS <alias> hace que SQL
       Server registre el ALIAS como entidad referenciada en
       sys.sql_expression_dependencies, con referenced_id NULL. La validacion
       1.2 del script 05, que busca referencias no resueltas, lo reportaba
       como si fuera un objeto inexistente. Era un falso positivo, pero
       ensuciaba un control que debe quedar en cero. MERGE no lo produce. */
    MERGE [reclamo].[modulo_congelado] AS tgt
    USING #LineaBase AS src
        ON  src.[campaña_id] = tgt.[campaña_id]
        AND src.modulo_id    = tgt.modulo_id
    WHEN MATCHED THEN UPDATE SET
        m3_camiones_previo = src.m3_camiones_previo,
        m3_rotopala_previo = src.m3_rotopala_previo,
        fecha_linea_base   = @Corte;

    PRINT '';
    PRINT 'Linea base establecida en ' + CAST(@@ROWCOUNT AS varchar) + ' modulos.';
    PRINT 'Corte: ' + CONVERT(varchar(10), @Corte, 120);

    /* Modulos que ya llegaban sobre 100 % antes del corte. Son el pasivo
       historico: quedan documentados, pero el sistema no los recalcula. */
    IF EXISTS (SELECT 1 FROM #LineaBase
               WHERE m3_totales > 0
                 AND m3_camiones_previo + m3_rotopala_previo > m3_totales)
    BEGIN
        PRINT '';
        PRINT 'ATENCION: los siguientes modulos ya superaban el 100 % ANTES del';
        PRINT 'corte. Se registran tal cual. No corresponde ajustarlos con el';
        PRINT 'sistema nuevo: son parte del pasivo historico.';

        IF @Silencioso = 0
        SELECT
            lb.pad_id, lb.modulo_numero, lb.m3_totales,
            lb.m3_camiones_previo, lb.m3_rotopala_previo,
            (lb.m3_camiones_previo + lb.m3_rotopala_previo) * 100.0 / lb.m3_totales AS pct
        FROM #LineaBase lb
        WHERE lb.m3_totales > 0
          AND lb.m3_camiones_previo + lb.m3_rotopala_previo > lb.m3_totales
        ORDER BY pct DESC;
    END;

    DROP TABLE #LineaBase;
END;
