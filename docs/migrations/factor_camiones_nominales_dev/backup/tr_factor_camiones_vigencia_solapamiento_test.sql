
CREATE   TRIGGER inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test
ON inventar_SpcHidr.factor_camiones_parametro_vigencia_test
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;
    -- Salvaguarda también para DML privilegiado. Serializa solo esta tabla pequeña.
    DECLARE @n bigint;
    SELECT @n=COUNT_BIG(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH (TABLOCKX,HOLDLOCK);
    IF EXISTS (
        SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test a
        JOIN inventar_SpcHidr.factor_camiones_parametro_vigencia_test b
          ON a.id<b.id AND a.flota=b.flota AND a.parametro=b.parametro
        WHERE a.activo=1 AND b.activo=1
          AND (b.vigencia_hasta IS NULL OR a.vigencia_desde<b.vigencia_hasta)
          AND (a.vigencia_hasta IS NULL OR b.vigencia_desde<a.vigencia_hasta)
    ) THROW 51001, 'Existen vigencias superpuestas de limites de carga para ajuste.', 1;
END;
