USE [inventar_SpcHidr_PROD];
GO
SET XACT_ABORT ON;
GO

/*
    Tabla inmutable de parámetros del polinomio de ácido.
    La vigencia_hasta no se almacena: se deriva desde la siguiente
    vigencia_desde para evitar rangos contradictorios.
*/
IF OBJECT_ID(N'[inventar_SpcHidr].[dosis_acido_configuracion]', N'U') IS NULL
BEGIN
    CREATE TABLE [inventar_SpcHidr].[dosis_acido_configuracion]
    (
        configuracion_id BIGINT IDENTITY(1,1) NOT NULL
            CONSTRAINT PK_dosis_acido_configuracion PRIMARY KEY,
        vigencia_desde DATE NOT NULL,
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

/* Compatibilidad con una instalación previa de la tabla sin vigencias. */
IF COL_LENGTH(N'inventar_SpcHidr.dosis_acido_configuracion', N'vigencia_desde') IS NULL
BEGIN
    IF (SELECT COUNT_BIG(*) FROM [inventar_SpcHidr].[dosis_acido_configuracion]) > 1
        THROW 51001,
              'Existen varias configuraciones sin vigencia. Debe mapear sus fechas antes de migrar.',
              1;

    EXEC sys.sp_executesql N'
        ALTER TABLE [inventar_SpcHidr].[dosis_acido_configuracion]
            ADD vigencia_desde DATE NULL;';

    EXEC sys.sp_executesql N'
        UPDATE [inventar_SpcHidr].[dosis_acido_configuracion]
        SET vigencia_desde = CONVERT(date, ''19000101'', 112)
        WHERE vigencia_desde IS NULL;';

    EXEC sys.sp_executesql N'
        ALTER TABLE [inventar_SpcHidr].[dosis_acido_configuracion]
            ALTER COLUMN vigencia_desde DATE NOT NULL;';
END;
GO

IF NOT EXISTS
(
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'[inventar_SpcHidr].[dosis_acido_configuracion]')
      AND name = N'UX_dosis_acido_configuracion_vigencia_desde'
)
BEGIN
    CREATE UNIQUE INDEX UX_dosis_acido_configuracion_vigencia_desde
        ON [inventar_SpcHidr].[dosis_acido_configuracion](vigencia_desde);
END;
GO

IF NOT EXISTS (SELECT 1 FROM [inventar_SpcHidr].[dosis_acido_configuracion])
BEGIN
    INSERT INTO [inventar_SpcHidr].[dosis_acido_configuracion]
    (
        vigencia_desde,
        umbral_mineral, umbral_co3, tasa_minima, tasa_base, factor_co3,
        factor_cus_co3_sobre_025, tasa_base_co3_sobre_025,
        factor_co3_co3_sobre_025, factor_cus_mineral_oxido,
        tasa_basal_mineral_oxido, factor_co3_mineral_oxido,
        usuario_submit, comentario
    )
    VALUES
    (
        CONVERT(date, '19000101', 112),
        0.25, 0.25, 14.00, 11.00, 15.51,
        8.182, 18.99, 15.51, 8.182, 18.99, 15.51,
        N'MIGRACION_INICIAL',
        N'Parámetros históricos utilizados antes del versionado temporal'
    );
END;
GO
