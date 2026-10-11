-- ============================================================================
-- CREAR TABLA DE AUDITORÍA PARA REPORTABILIDAD POST-BALANCE
-- ============================================================================
-- Script para crear la tabla inventar_SpcHidr.Audit_Ajustes_Reportabilidad
-- que registra todos los ajustes aplicados a los datos de reportabilidad
-- ============================================================================

USE SIIR_Dev;
GO

-- Crear tabla de auditoría
CREATE TABLE inventar_SpcHidr.Audit_Ajustes_Reportabilidad (
    audit_id INT PRIMARY KEY IDENTITY(1,1),
    caso_balance NVARCHAR(50) NOT NULL,
    run_id INT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    planta NVARCHAR(50),
    
    -- Datos del ajuste
    flujo_id NVARCHAR(100) NOT NULL,
    fecha_dia DATE NOT NULL,
    valor_medido DECIMAL(18,4),
    diferencia_reconciliada DECIMAL(18,4),
    ajuste_aplicado DECIMAL(18,4),
    porcentaje_aporte DECIMAL(8,4),  -- % del flujo respecto al total diario
    valor_final DECIMAL(18,4),
    
    -- Metadata de auditoría
    usuario_ajuste NVARCHAR(100),
    timestamp_ajuste DATETIME2 DEFAULT GETDATE(),
    fuente_run_id INT,  -- run_id de la reconciliación origen
    metodo_distribucion NVARCHAR(50),  -- 'Proporcional_Aporte_Diario'
    
    -- Control
    version_balance INT DEFAULT 1,  -- Número de versión del balance para este período
    is_active BIT DEFAULT 1,
    
    CONSTRAINT fk_audit_caso FOREIGN KEY (caso_balance) 
        REFERENCES inventar_SpcHidr.Casos_Balance(caso_balance)
);

GO

-- Crear índices para optimización
CREATE INDEX idx_audit_periodo 
    ON inventar_SpcHidr.Audit_Ajustes_Reportabilidad(caso_balance, fecha_inicio, fecha_fin);

CREATE INDEX idx_audit_run 
    ON inventar_SpcHidr.Audit_Ajustes_Reportabilidad(caso_balance, run_id);

CREATE INDEX idx_audit_fecha_dia 
    ON inventar_SpcHidr.Audit_Ajustes_Reportabilidad(fecha_dia, flujo_id);

CREATE INDEX idx_audit_activo 
    ON inventar_SpcHidr.Audit_Ajustes_Reportabilidad(is_active, caso_balance);

GO

-- Crear vista para datos activos (oficial)
CREATE VIEW inventar_SpcHidr.vw_Audit_Ajustes_Activos AS
SELECT 
    audit_id, caso_balance, run_id, fecha_inicio, fecha_fin, planta,
    flujo_id, fecha_dia, valor_medido, ajuste_aplicado, valor_final,
    usuario_ajuste, timestamp_ajuste, metodo_distribucion, version_balance
FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
WHERE is_active = 1;

GO

-- Crear vista para historial completo
CREATE VIEW inventar_SpcHidr.vw_Audit_Ajustes_Historial AS
SELECT 
    audit_id, caso_balance, run_id, fecha_inicio, fecha_fin, planta,
    flujo_id, fecha_dia, valor_medido, ajuste_aplicado, porcentaje_aporte, valor_final,
    usuario_ajuste, timestamp_ajuste, metodo_distribucion, version_balance,
    CASE WHEN is_active = 1 THEN 'OFICIAL' ELSE 'ARCHIVADO' END as estado
FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
ORDER BY run_id DESC, fecha_dia, flujo_id;

GO

PRINT '✓ Tabla de auditoría creada correctamente'
PRINT '✓ Índices creados'
PRINT '✓ Vistas creadas'
