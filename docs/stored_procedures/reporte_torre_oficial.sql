/* inventar_SpcHidr.reporte_torre_oficial_* — SQL Server 2017+
   Snapshot oficial del reporte Representatividad Torres (descarga sin SP).
   Un reporte activo por mes calendario (periodo_mes YYYY-MM).
   Ejecutar en SSMS / Azure Data Studio (soporta GO como separador de lotes). */
USE [inventar_SpcHidr];
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.schemas WHERE name = N'inventar_SpcHidr'
)
    EXEC(N'CREATE SCHEMA [inventar_SpcHidr] AUTHORIZATION [dbo]');
GO

IF OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_cab', N'U') IS NULL
CREATE TABLE inventar_SpcHidr.reporte_torre_oficial_cab (
    id_reporte              BIGINT          NOT NULL,
    periodo_mes             CHAR(7)         NOT NULL,
    periodo_inicio          DATE            NOT NULL,
    periodo_fin             DATE            NOT NULL,
    fecha_corte_operacional DATE            NOT NULL,
    anio_fiscal             SMALLINT        NULL,
    fecha_generacion        DATETIME2(0)    NOT NULL
        CONSTRAINT DF_rto_cab_fecha DEFAULT (SYSDATETIME()),
    usuario                 NVARCHAR(100)   NOT NULL,
    estado                  NVARCHAR(20)    NOT NULL
        CONSTRAINT DF_rto_cab_estado DEFAULT ('FINALIZADO'),
    activo                  BIT             NOT NULL
        CONSTRAINT DF_rto_cab_activo DEFAULT (1),
    fecha_eliminacion       DATETIME2(0)    NULL,
    usuario_eliminacion     NVARCHAR(100)   NULL,

    CONSTRAINT PK_reporte_torre_oficial_cab PRIMARY KEY CLUSTERED (id_reporte)
);
GO

IF OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_snapshot', N'U') IS NULL
CREATE TABLE inventar_SpcHidr.reporte_torre_oficial_snapshot (
    id_reporte      BIGINT          NOT NULL,
    bloque          NVARCHAR(40)    NOT NULL,
    payload         NVARCHAR(MAX)   NOT NULL,
    filas           INT             NOT NULL,
    fecha_carga     DATETIME2(0)    NOT NULL
        CONSTRAINT DF_rto_snap_fecha DEFAULT (SYSDATETIME()),

    CONSTRAINT PK_reporte_torre_oficial_snapshot
        PRIMARY KEY CLUSTERED (id_reporte, bloque),
    CONSTRAINT FK_rto_snap_cab
        FOREIGN KEY (id_reporte)
        REFERENCES inventar_SpcHidr.reporte_torre_oficial_cab (id_reporte)
);
GO

IF OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_detalle', N'U') IS NULL
CREATE TABLE inventar_SpcHidr.reporte_torre_oficial_detalle (
    id_reporte              BIGINT          NOT NULL,
    Fecha                   DATE            NOT NULL,
    Turno                   NVARCHAR(2)     NOT NULL,

    Semana                  NVARCHAR(20)    NULL,
    Pad                     NVARCHAR(100)   NULL,
    TMH_CV08                DECIMAL(18, 4)  NULL,
    Rep_TM1_Quimico         INT             NULL,
    TMH_CV108               DECIMAL(18, 4)  NULL,
    Rep_TM2_Quimico         INT             NULL,
    Rep_Turno_Quimico       INT             NULL,
    Rep_TM1_Fisico          INT             NULL,
    Rep_TM2_Fisico          INT             NULL,
    Rep_Turno_Fisico        INT             NULL,
    TM1_Activo              INT             NULL,
    TM2_Activo              INT             NULL,

    Comentario_TM1_Quimico  NVARCHAR(500)   NULL,
    Comentario_TM2_Quimico  NVARCHAR(500)   NULL,
    Comentario_TM1_Fisico   NVARCHAR(500)   NULL,
    Comentario_TM2_Fisico   NVARCHAR(500)   NULL,

    CONSTRAINT PK_reporte_torre_oficial_detalle
        PRIMARY KEY CLUSTERED (id_reporte, Fecha, Turno),
    CONSTRAINT FK_rto_det_cab
        FOREIGN KEY (id_reporte)
        REFERENCES inventar_SpcHidr.reporte_torre_oficial_cab (id_reporte)
);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'UX_rto_cab_mes_activo'
      AND object_id = OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_cab')
)
CREATE UNIQUE NONCLUSTERED INDEX UX_rto_cab_mes_activo
    ON inventar_SpcHidr.reporte_torre_oficial_cab (periodo_mes)
    WHERE activo = 1;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_rto_cab_generacion'
      AND object_id = OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_cab')
)
CREATE NONCLUSTERED INDEX IX_rto_cab_generacion
    ON inventar_SpcHidr.reporte_torre_oficial_cab (fecha_generacion DESC)
    INCLUDE (activo, periodo_mes);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_rto_cab_periodo_mes'
      AND object_id = OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_cab')
)
CREATE NONCLUSTERED INDEX IX_rto_cab_periodo_mes
    ON inventar_SpcHidr.reporte_torre_oficial_cab (periodo_mes)
    INCLUDE (activo, id_reporte);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = N'IX_rto_det_fecha'
      AND object_id = OBJECT_ID(N'inventar_SpcHidr.reporte_torre_oficial_detalle')
)
CREATE NONCLUSTERED INDEX IX_rto_det_fecha
    ON inventar_SpcHidr.reporte_torre_oficial_detalle (id_reporte, Fecha, Turno);
GO
