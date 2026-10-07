USE [inventar_SpcHidr];
GO
SET XACT_ABORT ON;
GO

IF OBJECT_ID(N'[inventar_SpcHidr].[dosis_acido_configuracion]', N'U') IS NULL
BEGIN
    CREATE TABLE [inventar_SpcHidr].[dosis_acido_configuracion]
    (
        configuracion_id BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_dosis_acido_configuracion PRIMARY KEY,
        umbral_mineral DECIMAL(18,6) NOT NULL,
        umbral_co3 DECIMAL(18,6) NOT NULL,
        tasa_minima DECIMAL(18,6) NOT NULL,
        tasa_base DECIMAL(18,6) NOT NULL,
        factor_co3 DECIMAL(18,6) NOT NULL,
        factor_cus_co3_sobre_025 DECIMAL(18,6) NOT NULL,
        tasa_base_co3_sobre_025 DECIMAL(18,6) NOT NULL,
        factor_co3_co3_sobre_025 DECIMAL(18,6) NOT NULL,
        factor_cus_mineral_oxido DECIMAL(18,6) NOT NULL,
        tasa_basal_mineral_oxido DECIMAL(18,6) NOT NULL,
        factor_co3_mineral_oxido DECIMAL(18,6) NOT NULL,
        fecha_submit DATETIME2(3) NOT NULL
            CONSTRAINT DF_dosis_acido_configuracion_fecha DEFAULT SYSDATETIME(),
        usuario_submit NVARCHAR(128) NOT NULL,
        comentario NVARCHAR(500) NULL,
        CONSTRAINT CK_dosis_acido_configuracion_umbral_mineral
            CHECK (umbral_mineral BETWEEN 0 AND 1),
        CONSTRAINT CK_dosis_acido_configuracion_umbral_co3
            CHECK (umbral_co3 BETWEEN 0 AND 1)
    );
END;
GO

IF NOT EXISTS (SELECT 1 FROM [inventar_SpcHidr].[dosis_acido_configuracion])
BEGIN
    INSERT INTO [inventar_SpcHidr].[dosis_acido_configuracion]
    (
        umbral_mineral, umbral_co3, tasa_minima, tasa_base, factor_co3,
        factor_cus_co3_sobre_025, tasa_base_co3_sobre_025,
        factor_co3_co3_sobre_025, factor_cus_mineral_oxido,
        tasa_basal_mineral_oxido, factor_co3_mineral_oxido,
        usuario_submit, comentario
    )
    VALUES
    (
        0.25, 0.25, 14.00, 11.00, 15.51,
        8.182, 18.99, 15.51, 8.182, 18.99, 15.51,
        N'MIGRACION_INICIAL', N'Configuración inicial del polinomio de ácido'
    );
END;
GO

CREATE OR ALTER FUNCTION [inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    @solubilidad DECIMAL(18,6),
    @co3 DECIMAL(18,6),
    @cus DECIMAL(18,6)
)
RETURNS DECIMAL(18,2)
AS
BEGIN
    DECLARE @configuracion_id BIGINT,
            @umbral_mineral DECIMAL(18,6), @umbral_co3 DECIMAL(18,6),
            @tasa_minima DECIMAL(18,6), @tasa_base DECIMAL(18,6),
            @factor_co3 DECIMAL(18,6),
            @factor_cus_co3_sobre_025 DECIMAL(18,6),
            @tasa_base_co3_sobre_025 DECIMAL(18,6),
            @factor_co3_co3_sobre_025 DECIMAL(18,6),
            @factor_cus_mineral_oxido DECIMAL(18,6),
            @tasa_basal_mineral_oxido DECIMAL(18,6),
            @factor_co3_mineral_oxido DECIMAL(18,6),
            @resultado FLOAT;

    SELECT TOP (1)
        @configuracion_id = configuracion_id,
        @umbral_mineral = umbral_mineral,
        @umbral_co3 = umbral_co3,
        @tasa_minima = tasa_minima,
        @tasa_base = tasa_base,
        @factor_co3 = factor_co3,
        @factor_cus_co3_sobre_025 = factor_cus_co3_sobre_025,
        @tasa_base_co3_sobre_025 = tasa_base_co3_sobre_025,
        @factor_co3_co3_sobre_025 = factor_co3_co3_sobre_025,
        @factor_cus_mineral_oxido = factor_cus_mineral_oxido,
        @tasa_basal_mineral_oxido = tasa_basal_mineral_oxido,
        @factor_co3_mineral_oxido = factor_co3_mineral_oxido
    FROM [inventar_SpcHidr].[dosis_acido_configuracion]
    ORDER BY configuracion_id DESC;

    IF @configuracion_id IS NULL RETURN NULL;

    SET @resultado =
        CASE
            WHEN ISNULL(@solubilidad, 0) < @umbral_mineral THEN
                CASE
                    WHEN ISNULL(@co3, 0) <= @umbral_co3 THEN @tasa_minima
                    ELSE @tasa_base + (@factor_co3 * ISNULL(@co3, 0))
                END
            ELSE
                CASE
                    WHEN @cus IS NULL OR @cus <= 0 THEN 0.0
                    WHEN (@factor_cus_co3_sobre_025 * LOG(@cus))
                         + @tasa_base_co3_sobre_025
                         + (@factor_co3_co3_sobre_025 * ISNULL(@co3, 0))
                         < @tasa_minima
                        THEN @tasa_minima
                    ELSE (@factor_cus_mineral_oxido * LOG(@cus))
                         + @tasa_basal_mineral_oxido
                         + (@factor_co3_mineral_oxido * ISNULL(@co3, 0))
                END
        END;

    RETURN CAST(ROUND(@resultado, 2) AS DECIMAL(18,2));
END;
GO
