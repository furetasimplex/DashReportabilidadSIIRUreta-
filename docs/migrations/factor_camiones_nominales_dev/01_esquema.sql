-- SOLO DEV. Ejecutar en la misma transaccion que los contratos SQL.
SET XACT_ABORT ON;
IF DB_NAME()<>N'inventar_SpcHidr' THROW 51000, 'Solo DEV.', 1;
IF @@TRANCOUNT=0 THROW 51030, 'La migracion requiere una transaccion externa.', 1;

-- Conservar el nombre del CHECK observado en el respaldo vivo.
IF EXISTS (SELECT 1 FROM sys.check_constraints
           WHERE parent_object_id=OBJECT_ID('inventar_SpcHidr.factor_camiones_parametro_vigencia_test')
             AND name='CK__factor_ca__param__41EF6173')
    ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test
        DROP CONSTRAINT CK__factor_ca__param__41EF6173;
ALTER TABLE inventar_SpcHidr.factor_camiones_parametro_vigencia_test WITH CHECK
    ADD CONSTRAINT CK__factor_ca__param__41EF6173
    CHECK (parametro IN ('LIMITE_CARGA_AJUSTE','CARGA_NOMINAL_TMH_VIAJE'));

IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_KOM_TMH_Viaje') IS NULL
    ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test
        ADD Carga_Nominal_KOM_TMH_Viaje decimal(18,6) NULL;
IF COL_LENGTH('inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test','Carga_Nominal_CAT_TMH_Viaje') IS NULL
    ALTER TABLE inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test
        ADD Carga_Nominal_CAT_TMH_Viaje decimal(18,6) NULL;

-- Bootstrap explicito de la nueva categoria; no invocar el administrador temporal.
-- No cambiar semillas de limites ni inventar nominales materializados historicos.
INSERT inventar_SpcHidr.factor_camiones_parametro_vigencia_test
    (flota,parametro,valor,vigencia_desde,motivo,usuario_registro)
SELECT s.flota,'CARGA_NOMINAL_TMH_VIAJE',s.valor,CONVERT(date,'20260701',112),
    N'Seed aprobado: carga nominal por viaje para reconstruccion de produccion V2; vigencia 2026-07-01.',
    N'MIGRACION_NOMINALES_V2_DEV'
FROM (VALUES ('KOM',CAST(357 AS decimal(18,6))),('CAT',CAST(236 AS decimal(18,6)))) s(flota,valor)
WHERE NOT EXISTS (
    SELECT 1 FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test p
    WHERE p.flota=s.flota AND p.parametro='CARGA_NOMINAL_TMH_VIAJE'
);
IF (SELECT COUNT(*) FROM inventar_SpcHidr.factor_camiones_parametro_vigencia_test
    WHERE parametro='CARGA_NOMINAL_TMH_VIAJE' AND vigencia_desde='20260701' AND activo=1
      AND ((flota='KOM' AND valor=357) OR (flota='CAT' AND valor=236)))<>2
    THROW 51031, 'Seed nominal existente incompatible; no se sobrescribe historia.', 1;
