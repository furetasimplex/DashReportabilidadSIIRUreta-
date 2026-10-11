/* ============================================================================
   SP 3.d reclamo.sp_auto_cerrar_y_avanzar_secuencia

   Regla pedida: "si un modulo X llega a 100 y el que sigue X+1 no esta
   abierto, se debe abrir".

   Cierra los modulos ABIERTO por dos motivos distintos:

     1. SOBRE_100_PROPONER_TRASPASO: la cuadratura (reclamo.v_cuadratura_modulo,
        que ya incluye la linea base y la tolerancia configurada) marca que
        la extraccion supero el 100 % del volumen congelado.

     2. AVANCE_DE_SECUENCIA (agregado 2026-07-30, corregido el mismo dia
        tras verificar en base de datos, regla pedida por el usuario): el
        modulo sigue ABIERTO pero la rotopala ya paso de largo -- hay dos o
        mas modulos de numero mayor, mismo pad y campaña, con AL MENOS UNA
        medicion real VIGENTE en reclamo.topografia_avance.

        Version anterior (incorrecta, descartada): se conto contra
        secuencia_rotopala.estado <> 'PENDIENTE'. Se comprobo con el caso
        del modulo 124 (campaña 8, modulo_id 188) que esa evidencia no
        sirve: secuencia_rotopala solo tenia UNA fila para esa rotopala y
        campaña (el propio 124), porque esa tabla solo agrega el siguiente
        modulo cuando el anterior SE CIERRA -- y como 124 nunca cerraba,
        125 a 130 nunca llegaban a tener fila ahi aunque ya estuvieran
        CONGELADOS en modulo_congelado y con mediciones reales de
        topografia posteriores al 2026-07-08 (verificado: 125 con 3
        mediciones, 126 con 12, 127 con 11, 128 con 3, 129 con 4, 130 con
        3). La evidencia correcta es la medicion fisica real, no el estado
        formal de una tabla que depende del propio cierre que se busca
        disparar.

        Esto pasa cuando un modulo se estanca justo por debajo del 100 %
        (la topografia deja de medirlo porque la rotopala fisicamente ya se
        movio) y por eso nunca dispara el motivo 1. Sin este segundo motivo
        quedaria ABIERTO para siempre, compitiendo indefinidamente por
        tonelaje preliminar de CV25 que ya no le corresponde. No se fuerza
        el cierre por simple antiguedad ni por dias sin medicion: se exige
        evidencia fisica concreta de mediciones reales en modulos
        posteriores (regla R5, maximo dos), no una suposicion de tiempo ni
        el estado de una tabla que todavia no se alcanzo a poblar.

   Abre el que sigue en la MISMA rotopala y campana, por orden_secuencia.

   "El que sigue" nunca se calcula como modulo_numero + 1: se toma de
   secuencia_rotopala, que respeta la campana y el rango fisico del PAD.

   Cuidado explicito con los dos casos limite:
     - Modulo final del PAD (modulo_numero = topologia_pad.modulo_numero_max):
       no hay siguiente posible. Se registra ALERTA_FIN_DE_PAD.
     - No hay siguiente CONGELADO en la secuencia de esta campana, sin ser
       el ultimo del PAD: puede ser cambio de campana (una campana nueva ya
       empezo a apilar en otra posicion) o que el siguiente modulo todavia
       no tiene base en disponible_rotopalas. Se registra
       ALERTA_FIN_DE_CAMPANA. No se adivina ni se fuerza nada.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_auto_cerrar_y_avanzar_secuencia]
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
        DECLARE @SigSecuenciaId int, @SigModId int, @SigModNum int, @SigEstado varchar(20);
        DECLARE @EsFinDePad bit;

        WHILE EXISTS
        (
            SELECT 1
            FROM [reclamo].[secuencia_rotopala] s
            INNER JOIN [reclamo].[v_cuadratura_modulo] cm
                ON cm.[campaña_id] = s.[campaña_id] AND cm.modulo_id = s.modulo_id
            WHERE s.estado = 'ABIERTO'
              AND
              (
                  cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'
                  OR
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
                  cm.flag_cuadratura = 'SOBRE_100_PROPONER_TRASPASO'
                  OR
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

            UPDATE [reclamo].[secuencia_rotopala]
            SET estado = 'CERRADO', fecha_cierre = CAST(SYSDATETIME() AS date)
            WHERE secuencia_id = @SecuenciaId;

            INSERT INTO [reclamo].[log_automatizacion]
                (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
            VALUES
                (@EjecucionId, 'CERRADO_AUTOMATICO', @Pad, @Camp, @Mod, @ModNum,
                 CASE
                     WHEN @PctExtraido >= 100
                         THEN N'Extraccion alcanzo o supero el 100% del volumen congelado ('
                              + CAST(@PctExtraido AS varchar) + N'%).'
                     ELSE N'Rotopala ya avanzo ' + CAST(@ModulosPasados AS varchar)
                          + N' modulo(s) mas adelante en la secuencia sin que este se cerrara '
                          + N'(quedo estancado en ' + CAST(@PctExtraido AS varchar)
                          + N'% sin nuevas mediciones). Cerrado automaticamente por avance de '
                          + N'secuencia, no por cuadratura.'
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

            IF @SigSecuenciaId IS NOT NULL AND @SigEstado = 'PENDIENTE'
            BEGIN
                UPDATE [reclamo].[secuencia_rotopala]
                SET estado = 'ABIERTO', fecha_apertura = CAST(SYSDATETIME() AS date)
                WHERE secuencia_id = @SigSecuenciaId;

                INSERT INTO [reclamo].[log_automatizacion]
                    (ejecucion_id, accion, pad_id, [campaña_id], modulo_id, modulo_numero, detalle)
                VALUES
                    (@EjecucionId, 'ABIERTO_AUTOMATICO', @Pad, @Camp, @SigModId, @SigModNum,
                     N'Modulo siguiente de la secuencia. Se abre al cerrarse el modulo '
                        + CAST(@ModNum AS varchar) + N'.');
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