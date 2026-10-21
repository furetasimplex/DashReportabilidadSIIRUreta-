USE [inventar_SpcHidr_PROD];
GO
SET XACT_ABORT ON;
GO

CREATE OR ALTER PROCEDURE [inventar_SpcHidr].[sp_registrar_dosis_acido_configuracion]
    @vigencia_desde DATE,
    @configuracion_esperada BIGINT,
    @umbral_mineral DECIMAL(18,6),
    @umbral_co3 DECIMAL(18,6),
    @tasa_minima DECIMAL(18,6),
    @tasa_base DECIMAL(18,6),
    @factor_co3 DECIMAL(18,6),
    @factor_cus_co3_sobre_025 DECIMAL(18,6),
    @tasa_base_co3_sobre_025 DECIMAL(18,6),
    @factor_co3_co3_sobre_025 DECIMAL(18,6),
    @factor_cus_mineral_oxido DECIMAL(18,6),
    @tasa_basal_mineral_oxido DECIMAL(18,6),
    @factor_co3_mineral_oxido DECIMAL(18,6),
    @usuario_submit NVARCHAR(128),
    @comentario NVARCHAR(500) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    IF @vigencia_desde IS NULL THROW 51010, 'Debe indicar la fecha de inicio de vigencia.', 1;
    IF NULLIF(LTRIM(RTRIM(@usuario_submit)), N'') IS NULL
        THROW 51011, 'Debe indicar el usuario autenticado.', 1;
    IF @umbral_mineral NOT BETWEEN 0 AND 1 OR @umbral_co3 NOT BETWEEN 0 AND 1
        THROW 51012, 'Los umbrales deben estar entre 0 y 1.', 1;

    BEGIN TRANSACTION;

    DECLARE @actual BIGINT, @ultima_vigencia DATE;
    SELECT TOP (1)
        @actual = configuracion_id,
        @ultima_vigencia = vigencia_desde
    FROM [inventar_SpcHidr].[dosis_acido_configuracion] WITH (UPDLOCK, HOLDLOCK)
    ORDER BY vigencia_desde DESC, configuracion_id DESC;

    IF @actual <> @configuracion_esperada
        THROW 51013, 'La configuración cambió desde la revisión. Actualice y confirme nuevamente.', 1;
    IF @vigencia_desde <= @ultima_vigencia
        THROW 51014, 'La nueva vigencia debe comenzar después de la última configuración.', 1;

    INSERT INTO [inventar_SpcHidr].[dosis_acido_configuracion]
    (
        vigencia_desde,
        umbral_mineral, umbral_co3, tasa_minima, tasa_base, factor_co3,
        factor_cus_co3_sobre_025, tasa_base_co3_sobre_025,
        factor_co3_co3_sobre_025, factor_cus_mineral_oxido,
        tasa_basal_mineral_oxido, factor_co3_mineral_oxido,
        usuario_submit, comentario
    )
    OUTPUT INSERTED.configuracion_id, INSERTED.vigencia_desde,
           INSERTED.fecha_submit, INSERTED.usuario_submit, INSERTED.comentario
    VALUES
    (
        @vigencia_desde,
        @umbral_mineral, @umbral_co3, @tasa_minima, @tasa_base, @factor_co3,
        @factor_cus_co3_sobre_025, @tasa_base_co3_sobre_025,
        @factor_co3_co3_sobre_025, @factor_cus_mineral_oxido,
        @tasa_basal_mineral_oxido, @factor_co3_mineral_oxido,
        LTRIM(RTRIM(@usuario_submit)), NULLIF(LTRIM(RTRIM(@comentario)), N'')
    );

    COMMIT TRANSACTION;
END;
GO
