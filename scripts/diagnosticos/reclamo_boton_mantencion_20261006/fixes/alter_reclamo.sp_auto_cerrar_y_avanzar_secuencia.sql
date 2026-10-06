/* ============================================================================
   SP 3.d reclamo.sp_auto_cerrar_y_avanzar_secuencia

   Regla pedida: "si un modulo X llega a 100 y el que sigue X+1 no esta
   abierto, se debe abrir".

Cierra los modulos ABIERTO por tres motivos distintos:



  1. SOBRE_100_PROPONER_TRASPASO:

     la extracción supera el 100 % más la tolerancia configurada.



  2. AGOTADO_CON_SIGUIENTE_TOPO:

     el módulo está prácticamente agotado y el módulo inmediatamente

     siguiente ya tiene topografía real VIGENTE.

     Para esta condición se utiliza como fecha operacional de transición

     la más tardía entre la última topografía del módulo actual y la

     primera topografía del módulo siguiente.



  3. AVANCE_DE_SECUENCIA:

     existen dos o más módulos posteriores de la misma campaña y PAD

     con topografía real VIGENTE.
   ============================================================================ */
ALTER PROCEDURE [reclamo].[sp_auto_cerrar_y_avanzar_secuencia]
(
    @EjecucionId int = NULL
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @EjecucionPropia bit = 0;
    IF @EjecucionId IS NULL
    BEGIN
        INSERT INTO [reclamo].[log_ejecucion] (procedimiento, estado)
        VALUES ('reclamo.sp_auto_cerrar_y_avanzar_secuencia', 'EN_CURSO');
        SET @EjecucionId = SCOPE_IDENTITY();
        SET @EjecucionPropia = 1;
    END;

    BEGIN TRY
        DECLARE @SecuenciaId int, @RotId tinyint, @Camp int, @Mod int, @Pad int, @ModNum int;
        DECLARE @OrdenActual int, @PctExtraido decimal(9,4), @ModulosPasados int;

        DECLARE @FlagCuadratura varchar(50);

        DECLARE @MotivoCierre varchar(60);
        DECLARE @SigSecuenciaId int, @SigModId int, @SigModNum int, @SigEstado varchar(20);
        DECLARE @EsFinDePad bit;

        DECLARE @FechaTransicion date;

        DECLARE @FechaUltimaActual date;

        DECLARE @FechaPrimeraSiguiente date;

        WHILE EXISTS
        (
            SELECT 1
            FROM [reclamo].[secuencia_rotopala] s
            INNER JOIN [reclamo].[v_cuadratura_modulo] cm
                ON cm.[campaña_id] = s.[campaña_id] AND cm.modulo_id = s.modulo_id
            WHERE s.estado = 'ABIERTO'

  AND

  (

      /* 1. Sobre 100% + tolerancia */

      cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'



      OR



      /* 2. NUEVO:

            prácticamente agotado

            + siguiente módulo con topografía real */

      (

          cm.flag_cuadratura = 'MODULO_PRACTICAMENTE_AGOTADO'

          AND cm.modulo_siguiente_propuesto IS NOT NULL

          AND EXISTS

          (

              SELECT 1

              FROM [reclamo].[topografia_avance] t4

              WHERE t4.[campaña_id] = s.[campaña_id]

                AND t4.modulo_id = cm.modulo_siguiente_propuesto

                AND t4.estado = 'VIGENTE'

          )

      )



      OR



      /* 3. Regla existente:

            dos o más módulos posteriores con topografía */

      (

          SELECT COUNT(DISTINCT mc3.modulo_id)

          FROM [reclamo].[modulo_congelado] mc3

          WHERE mc3.pad_id        = s.pad_id

            AND mc3.[campaña_id]  = s.[campaña_id]

            AND mc3.modulo_numero > s.modulo_numero

            AND EXISTS

            (

                SELECT 1

                FROM [reclamo].[topografia_avance] t3

                WHERE t3.modulo_id = mc3.modulo_id

                  AND t3.estado    = 'VIGENTE'

            )

      ) >= 2

  )
        )
        BEGIN
            SELECT TOP (1)
                @SecuenciaId = s.secuencia_id, @RotId = s.rotopala_id,
                @Camp = s.[campaña_id], @Mod = s.modulo_id,
                @Pad = s.pad_id, @ModNum = s.modulo_numero, @OrdenActual = s.orden_secuencia,
                @PctExtraido = cm.porcentaje_extraido,

                @FlagCuadratura = cm.flag_cuadratura,

                @ModulosPasados =

                (
                    SELECT COUNT(DISTINCT mc3.modulo_id)
                    FROM [reclamo].[modulo_congelado] mc3
                    WHERE mc3.pad_id        = s.pad_id
                      AND mc3.[campaña_id]  = s.[campaña_id]
                      AND mc3.modulo_numero > s.modulo_numero
                      AND EXISTS
                          (
                              SELECT 1
                              FROM [reclamo].[topografia_avance] t3
                              WHERE t3.modulo_id = mc3.modulo_id
                                AND t3.estado    = 'VIGENTE'
                          )
                )
            FROM [reclamo].[secuencia_rotopala] s
            INNER JOIN [reclamo].[v_cuadratura_modulo] cm
                ON cm.[campaña_id] = s.[campaña_id] AND cm.modulo_id = s.modulo_id
WHERE s.estado = 'ABIERTO'

  AND

  (

      /* 1. Sobre 100% + tolerancia */

      cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'



      OR



      /* 2. NUEVO:

            prácticamente agotado

            + siguiente módulo con topografía real */

      (

          cm.flag_cuadratura = 'MODULO_PRACTICAMENTE_AGOTADO'

          AND cm.modulo_siguiente_propuesto IS NOT NULL

          AND EXISTS

          (

              SELECT 1

              FROM [reclamo].[topografia_avance] t4

              WHERE t4.[campaña_id] = s.[campaña_id]

                AND t4.modulo_id = cm.modulo_siguiente_propuesto

                AND t4.estado = 'VIGENTE'

          )

      )



      OR



      /* 3. Regla existente:

            dos o más módulos posteriores con topografía */

      (

          SELECT COUNT(DISTINCT mc3.modulo_id)

          FROM [reclamo].[modulo_congelado] mc3

          WHERE mc3.pad_id        = s.pad_id

            AND mc3.[campaña_id]  = s.[campaña_id]

            AND mc3.modulo_numero > s.modulo_numero

            AND EXISTS

            (

                SELECT 1

                FROM [reclamo].[topografia_avance] t3

                WHERE t3.modulo_id = mc3.modulo_id

                  AND t3.estado    = 'VIGENTE'

            )

      ) >= 2

  )
            ORDER BY s.orden_secuencia;
/* ============================================================

   Determinar motivo real del cierre

   ============================================================ */



SET @MotivoCierre =

    CASE

        /* Regla 1:

           superó 100% + tolerancia */

        WHEN @FlagCuadratura = 'SOBRE_100_PROPONER_TRASPASO'

            THEN 'SOBRE_100_TOLERANCIA'



        /* Regla 2 NUEVA:

           prácticamente agotado

           + siguiente módulo con topografía real */

        WHEN @FlagCuadratura = 'MODULO_PRACTICAMENTE_AGOTADO'

             AND EXISTS

             (

                 SELECT 1

                 FROM [reclamo].[topografia_avance] t4

                 WHERE t4.[campaña_id] = @Camp

                   AND t4.modulo_id =

                   (

                       SELECT TOP (1)

                           s2.modulo_id

                       FROM [reclamo].[secuencia_rotopala] s2

                       WHERE s2.rotopala_id = @RotId

                         AND s2.[campaña_id] = @Camp

                         AND s2.orden_secuencia > @OrdenActual

                       ORDER BY s2.orden_secuencia

                   )

                   AND t4.estado = 'VIGENTE'

             )

            THEN 'AGOTADO_CON_SIGUIENTE_TOPO'



        /* Regla 3 existente:

           la rotopala ya avanzó 2 o más módulos */

        WHEN @ModulosPasados >= 2

            THEN 'AVANCE_DE_SECUENCIA'



        ELSE 'OTRO'

    END;

/* ============================================================

   Fecha efectiva del cambio de módulo



   Regla nueva:

   AGOTADO_CON_SIGUIENTE_TOPO

       -> usar evidencia topográfica histórica



   Reglas existentes:

       -> mantener fecha de ejecución del SP

   ============================================================ */



SET @FechaUltimaActual = NULL;
SET @FechaPrimeraSiguiente = NULL;
SET @FechaTransicion = NULL;
SET @SigModId = NULL;

SELECT @FechaUltimaActual = MAX(x.fecha_operacional)
FROM
(
    SELECT CAST(t.fecha_medicion AS date) AS fecha_operacional
    FROM [reclamo].[topografia_avance] t
    WHERE t.[campaña_id] = @Camp AND t.pad_id = @Pad AND t.modulo_id = @Mod AND t.estado = 'VIGENTE'
    UNION ALL
    SELECT CAST(cr.fecha AS date)
    FROM [inventar_SpcHidr].[control_reclamo_diario] cr
    WHERE cr.[campaña_id] = @Camp AND cr.pad_id = @Pad AND cr.modulo_id = @Mod
      AND COALESCE(cr.volumen_diario_m3,0) > 0
) x;

SELECT TOP (1) @SigModId = s2.modulo_id
FROM [reclamo].[secuencia_rotopala] s2
WHERE s2.rotopala_id = @RotId AND s2.[campaña_id] = @Camp
  AND s2.orden_secuencia > @OrdenActual
ORDER BY s2.orden_secuencia;

IF @SigModId IS NULL
BEGIN
    SELECT TOP (1) @SigModId = md.id_modulo
    FROM [inventar_SpcHidr].[disponible_rotopalas] dr
    INNER JOIN [inventar_SpcHidr].[modulo] md ON md.id_modulo = dr.modulo_id
    WHERE dr.[campaña_id] = @Camp AND md.numero > @ModNum
    ORDER BY md.numero;
END;

IF @SigModId IS NOT NULL
BEGIN
    SELECT @FechaPrimeraSiguiente = MIN(x.fecha_operacional)
    FROM
    (
        SELECT CAST(t.fecha_medicion AS date) AS fecha_operacional
        FROM [reclamo].[topografia_avance] t
        WHERE t.[campaña_id] = @Camp AND t.pad_id = @Pad
          AND t.modulo_id = @SigModId AND t.estado = 'VIGENTE'
        UNION ALL
        SELECT CAST(cr.fecha AS date)
        FROM [inventar_SpcHidr].[control_reclamo_diario] cr
        WHERE cr.[campaña_id] = @Camp AND cr.pad_id = @Pad
          AND cr.modulo_id = @SigModId AND COALESCE(cr.volumen_diario_m3,0) > 0
    ) x;
END;

SET @FechaTransicion = COALESCE(@FechaPrimeraSiguiente, @FechaUltimaActual);





            UPDATE [reclamo].[secuencia_rotopala]
            SET estado = 'CERRADO',  fecha_cierre = @FechaTransicion
            WHERE secuencia_id = @SecuenciaId;

            INSERT INTO [reclamo].[log_automatizacion]
                (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
            VALUES
                (@EjecucionId, 'CERRADO_AUTOMATICO', @Pad, @Camp, @Mod, @ModNum,
                 CASE



    WHEN @MotivoCierre = 'SOBRE_100_TOLERANCIA'

        THEN

            N'Extraccion supero el 100% mas la tolerancia configurada ('

            + CAST(@PctExtraido AS varchar)

            + N'%). Cerrado automaticamente por cuadratura.'



    WHEN @MotivoCierre = 'AGOTADO_CON_SIGUIENTE_TOPO'

        THEN

            N'Modulo practicamente agotado ('

            + CAST(@PctExtraido AS varchar)

            + N'%) y modulo siguiente con evidencia topografica real. '

            + N'Cerrado automaticamente por avance operacional de secuencia. '

            + N'Fecha efectiva de transicion: '

            + CONVERT(varchar(10), @FechaTransicion, 120)

            + N'.'



    WHEN @MotivoCierre = 'AVANCE_DE_SECUENCIA'

        THEN

            N'Rotopala ya avanzo '

            + CAST(@ModulosPasados AS varchar)

            + N' modulo(s) posteriores con evidencia topografica. '

            + N'Cerrado automaticamente por avance de secuencia.'



    ELSE

        N'Cierre automatico. Motivo no clasificado. Avance actual: '

        + CAST(@PctExtraido AS varchar)

        + N'%.'



END);

            SET @SigSecuenciaId = NULL; SET @SigModId = NULL;
            SET @SigModNum = NULL; SET @SigEstado = NULL;

            SELECT TOP (1)
                @SigSecuenciaId = s2.secuencia_id, @SigModId = s2.modulo_id,
                @SigModNum = s2.modulo_numero, @SigEstado = s2.estado
            FROM [reclamo].[secuencia_rotopala] s2
            WHERE s2.rotopala_id = @RotId AND s2.[campaña_id] = @Camp
              AND s2.orden_secuencia > @OrdenActual
            ORDER BY s2.orden_secuencia;

            IF @SigSecuenciaId IS NOT NULL AND @SigEstado = 'PENDIENTE' AND @FechaTransicion IS NOT NULL
            BEGIN
                UPDATE [reclamo].[secuencia_rotopala]
                SET estado = 'ABIERTO', fecha_apertura = @FechaTransicion
                WHERE secuencia_id = @SigSecuenciaId;

                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId, 'ABIERTO_AUTOMATICO', @Pad, @Camp, @SigModId, @SigModNum,
                     N'Modulo siguiente de la secuencia. Se abre al cerrarse el modulo '

+ CAST(@ModNum AS varchar)

+ N'. Fecha efectiva de apertura: '

+ CONVERT(varchar(10), @FechaTransicion, 120)

+ N'.');
            END
            ELSE IF @SigSecuenciaId IS NULL
            BEGIN
                SET @EsFinDePad =
                (
                    SELECT CASE WHEN @ModNum >= tp.modulo_numero_max THEN 1 ELSE 0 END
                    FROM [reclamo].[topologia_pad] tp
                    WHERE tp.pad_id = @Pad
                );

                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId,
                     CASE WHEN @EsFinDePad = 1 THEN 'ALERTA_FIN_DE_PAD' ELSE 'ALERTA_FIN_DE_CAMPANA' END,
                     @Pad, @Camp, @Mod, @ModNum,
                     CASE WHEN @EsFinDePad = 1
                          THEN N'Modulo ' + CAST(@ModNum AS varchar)
                               + N' es el ultimo del rango fisico del PAD. Revisar cierre de campana.'
                          ELSE N'No hay mas modulos congelados en esta campana despues del '
                               + CAST(@ModNum AS varchar)
                               + N'. Puede ser cambio de campana: revisar si ya hay apilado en una campana nueva.'
                     END);
            END;
            /* Si el siguiente ya estaba ABIERTO o CERRADO, no hay nada mas que hacer. */
        END;

        IF @EjecucionPropia = 1
            UPDATE [reclamo].[log_ejecucion] SET fecha_fin = SYSDATETIME(), estado = 'OK'
            WHERE ejecucion_id = @EjecucionId;
    END TRY
    BEGIN CATCH
        IF @EjecucionPropia = 1
            UPDATE [reclamo].[log_ejecucion]
            SET fecha_fin = SYSDATETIME(), estado = 'ERROR', mensaje = ERROR_MESSAGE()
            WHERE ejecucion_id = @EjecucionId;
        THROW;
    END CATCH
END;