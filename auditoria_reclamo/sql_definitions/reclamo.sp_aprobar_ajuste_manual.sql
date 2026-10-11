/* ============================================================================
   SP 5. reclamo.sp_aprobar_ajuste_manual

   Separa quien propone de quien aprueba. El procedimiento impide que ambos
   sean el mismo login, salvo que se pase @PermitirAutoaprobacion = 1, lo que
   queda anotado en la observacion.
   ============================================================================ */
CREATE   PROCEDURE [reclamo].[sp_aprobar_ajuste_manual]
(
    @AjusteId                int,
    @Decision                varchar(20),
    @Comentario              nvarchar(500) = NULL,
    @PermitirAutoaprobacion  bit = 0
)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @Decision NOT IN ('APROBADO','RECHAZADO','REVERTIDO')
        THROW 60401, 'La decision debe ser APROBADO, RECHAZADO o REVERTIDO.', 1;

    DECLARE @Solicitante sysname =
    (
        SELECT usuario_solicita FROM [reclamo].[ajuste_manual] WHERE ajuste_id = @AjusteId
    );

    IF @Solicitante IS NULL
        THROW 60402, 'No existe ese ajuste.', 1;

    IF @Solicitante = SUSER_SNAME() AND @PermitirAutoaprobacion = 0
        THROW 60403,
              'Quien propone un ajuste no deberia aprobarlo. Use @PermitirAutoaprobacion = 1 si corresponde.', 1;

    UPDATE [reclamo].[ajuste_manual]
    SET estado           = @Decision,
        usuario_aprueba  = SUSER_SNAME(),
        fecha_aprobacion = SYSDATETIME(),
        observacion      = LTRIM(RTRIM(COALESCE(observacion, N'')
                           + N' | ' + @Decision + N': ' + COALESCE(@Comentario, N'sin comentario')
                           + CASE WHEN @PermitirAutoaprobacion = 1
                                  THEN N' | AUTOAPROBADO POR EL SOLICITANTE' ELSE N'' END))
    WHERE ajuste_id = @AjusteId;

    PRINT 'Ajuste ' + CAST(@AjusteId AS varchar) + ' -> ' + @Decision;
    PRINT 'Recuerde reprocesar el rango con sp_calcular_reclamo_diario.';

    SELECT * FROM [reclamo].[ajuste_manual] WHERE ajuste_id = @AjusteId;
END;