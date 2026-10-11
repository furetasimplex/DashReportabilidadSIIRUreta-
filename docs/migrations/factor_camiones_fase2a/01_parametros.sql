-- DEV solamente. El runner valida servidor efectivo además de la base.
IF DB_NAME() <> N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
IF OBJECT_ID('inventar_SpcHidr.factor_camiones_parametro_vigencia_test','U') IS NULL
BEGIN
    CREATE TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test (
        id bigint IDENTITY PRIMARY KEY,
        flota varchar(3) NOT NULL CHECK (flota IN ('KOM','CAT')),
        parametro varchar(40) NOT NULL CHECK (parametro='LIMITE_CARGA_AJUSTE'),
        valor decimal(18,6) NOT NULL CHECK (valor>0),
        vigencia_desde date NOT NULL,
        vigencia_hasta date NULL,
        motivo nvarchar(1000) NOT NULL CHECK (LEN(LTRIM(RTRIM(motivo)))>0),
        usuario_registro nvarchar(128) NOT NULL CHECK (LEN(LTRIM(RTRIM(usuario_registro)))>0),
        fecha_registro datetime2(7) NOT NULL DEFAULT SYSDATETIME(),
        activo bit NOT NULL DEFAULT 1,
        CONSTRAINT CK_factor_vigencia_intervalo CHECK (vigencia_hasta IS NULL OR vigencia_hasta>vigencia_desde),
        CONSTRAINT UQ_factor_vigencia_inicio UNIQUE (flota,parametro,vigencia_desde)
    );
    CREATE UNIQUE INDEX UX_factor_vigencia_abierta
        ON inventar_SpcHidr.factor_camiones_parametro_vigencia_test(flota,parametro)
        WHERE activo=1 AND vigencia_hasta IS NULL;
END;
IF OBJECT_ID('inventar_SpcHidr.factor_camiones_parametro_auditoria_test','U') IS NULL
BEGIN
    CREATE TABLE inventar_SpcHidr.factor_camiones_parametro_auditoria_test (
        id bigint IDENTITY PRIMARY KEY,
        flota varchar(3) NOT NULL,
        parametro varchar(40) NOT NULL,
        accion varchar(30) NOT NULL CHECK (accion='NUEVA_VIGENCIA'),
        valor_anterior decimal(18,6) NULL,
        valor_nuevo decimal(18,6) NOT NULL,
        vigencia_desde date NOT NULL,
        usuario nvarchar(128) NOT NULL,
        motivo nvarchar(1000) NOT NULL,
        fecha_registro datetime2(7) NOT NULL,
        es_retroactivo bit NOT NULL
    );
END;
-- No permitir DML directo a usuarios ordinarios. El procedimiento usa ownership chaining.
DENY INSERT, UPDATE, DELETE ON inventar_SpcHidr.factor_camiones_parametro_vigencia_test TO public;
DENY INSERT, UPDATE, DELETE ON inventar_SpcHidr.factor_camiones_parametro_auditoria_test TO public;
GO
CREATE OR ALTER TRIGGER inventar_SpcHidr.tr_factor_camiones_vigencia_solapamiento_test
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
GO
-- Seed idempotente: no altera intervalos existentes ni vuelve a abrir la historia.
IF (SELECT MIN(Fecha) FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test) <> CONVERT(date,'20260701',112)
   OR NOT EXISTS (SELECT 1 FROM inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test)
    THROW 51002, 'Inicio materializado V2 distinto de 01-07-2026.', 1;
IF NOT EXISTS (SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test)
BEGIN
    INSERT inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        (flota,parametro,valor,vigencia_desde,motivo,usuario_registro)
    VALUES ('KOM','LIMITE_CARGA_AJUSTE',380,'20260701',N'Seed: limites originales cadena V2; MIN(Fecha)=01-07-2026',N'MIGRACION_FASE2A'),
           ('CAT','LIMITE_CARGA_AJUSTE',265,'20260701',N'Seed: limites originales cadena V2; MIN(Fecha)=01-07-2026',N'MIGRACION_FASE2A');
END;
IF (SELECT COUNT(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
    WHERE vigencia_desde='20260701' AND parametro='LIMITE_CARGA_AJUSTE' AND activo=1
    AND ((flota='KOM' AND valor=380) OR (flota='CAT' AND valor=265))) <> 2
    THROW 51003, 'Seed existente incompatible; no se sobrescribe historia.', 1;
