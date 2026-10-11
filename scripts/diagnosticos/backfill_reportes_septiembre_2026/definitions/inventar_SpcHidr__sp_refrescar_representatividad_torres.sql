CREATE   PROCEDURE
    inventar_SpcHidr.sp_refrescar_representatividad_torres
    @fecha_inicio date,
    @fecha_fin date
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @fecha_inicio IS NULL
       OR @fecha_fin IS NULL
       OR @fecha_inicio > @fecha_fin
    BEGIN
        THROW 50001,
              'Rango de fechas inválido para refrescar representatividad.',
              1;
    END;

    BEGIN TRY
        BEGIN TRANSACTION;

        DELETE FROM inventar_SpcHidr.representatividad_torres_resultado
        WHERE Dia >= @fecha_inicio
          AND Dia <= @fecha_fin;

        INSERT INTO inventar_SpcHidr.representatividad_torres_resultado
        (
            Dia,

            TM1_TurnoA_Quimico,
            TM1_TurnoA_Fisico,
            TM1_TurnoB_Quimico,
            TM1_TurnoB_Fisico,

            TM2_TurnoA_Quimico,
            TM2_TurnoA_Fisico,
            TM2_TurnoB_Quimico,
            TM2_TurnoB_Fisico,

            SRR_TurnoA_Quimico,
            SRR_TurnoA_Fisico,
            SRR_TurnoB_Quimico,
            SRR_TurnoB_Fisico,

            fecha_calculo
        )
        SELECT
            Dia,

            CAST(TM1_TurnoA_Quimico AS decimal(18,10)),
            CAST(TM1_TurnoA_Fisico  AS decimal(18,10)),
            CAST(TM1_TurnoB_Quimico AS decimal(18,10)),
            CAST(TM1_TurnoB_Fisico  AS decimal(18,10)),

            CAST(TM2_TurnoA_Quimico AS decimal(18,10)),
            CAST(TM2_TurnoA_Fisico  AS decimal(18,10)),
            CAST(TM2_TurnoB_Quimico AS decimal(18,10)),
            CAST(TM2_TurnoB_Fisico  AS decimal(18,10)),

            CAST(SRR_TurnoA_Quimico AS decimal(18,10)),
            CAST(SRR_TurnoA_Fisico  AS decimal(18,10)),
            CAST(SRR_TurnoB_Quimico AS decimal(18,10)),
            CAST(SRR_TurnoB_Fisico  AS decimal(18,10)),

            SYSDATETIME()

        FROM inventar_SpcHidr.v_representatividad_diaria_calculada

        WHERE Dia >= @fecha_inicio
          AND Dia <= @fecha_fin;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;

        THROW;
    END CATCH;
END;
