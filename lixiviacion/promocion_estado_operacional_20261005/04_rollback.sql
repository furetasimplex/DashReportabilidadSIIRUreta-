-- PREPARADO, NO EJECUTADO. Solo tras una futura promoción autorizada.
-- Oficial inexistente al precheck. Actualmente no hay nada que revertir.
-- 1. Restituir SOURCE en lixiviacion/map_db.py a:
-- inventar_SpcHidr.fn_estado_operacional_parcela_diario_test_v2
-- 2. Ejecutar tests y smoke contra TEST. Verificar consumidores antes de retirar oficial.
-- 3. En conexión DEV verificada, habilitar manualmente esta guarda y ejecutar.
IF DB_NAME() <> N'inventar_SpcHidr'
    THROW 51200, 'Rollback permitido exclusivamente en DEV.', 1;
DECLARE @ejecutar_rollback bit = 0;
IF @ejecutar_rollback <> 1
    THROW 51201, 'Rollback no habilitado. Revisar README y dependencias.', 1;
DROP FUNCTION IF EXISTS inventar_SpcHidr.fn_estado_operacional_parcela_diario;
-- Nunca eliminar TEST V2 ni TEST anterior.
