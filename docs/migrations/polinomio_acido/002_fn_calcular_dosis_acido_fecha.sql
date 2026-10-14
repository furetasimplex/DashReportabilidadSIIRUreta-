USE [inventar_SpcHidr_PROD];
GO
SET XACT_ABORT ON;
GO

CREATE OR ALTER FUNCTION [inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]
(
    @fecha_calculo DATE,
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

    IF @fecha_calculo IS NULL RETURN NULL;

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
    WHERE vigencia_desde <= @fecha_calculo
    ORDER BY vigencia_desde DESC, configuracion_id DESC;

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

/* Compatibilidad: conserva el contrato anterior y usa la fecha actual. */
CREATE OR ALTER FUNCTION [inventar_SpcHidr].[fn_calcular_dosis_acido]
(
    @solubilidad DECIMAL(18,6),
    @co3 DECIMAL(18,6),
    @cus DECIMAL(18,6)
)
RETURNS DECIMAL(18,2)
AS
BEGIN
    RETURN [inventar_SpcHidr].[fn_calcular_dosis_acido_fecha]
    (
        CAST(GETDATE() AS date), @solubilidad, @co3, @cus
    );
END;
GO
