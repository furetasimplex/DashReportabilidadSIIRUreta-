/* DEV ONLY: trazabilidad final de analitos del Analisis TM. */
IF OBJECT_ID(N'inventar_SpcHidr.trazabilidad_analitos_tm_emision_test', N'U') IS NULL
BEGIN
    CREATE TABLE inventar_SpcHidr.trazabilidad_analitos_tm_emision_test
    (
        Fecha date NOT NULL,
        Turno varchar(5) NOT NULL,
        TM_Destino varchar(10) NOT NULL,
        Analito varchar(30) NOT NULL,
        Valor_Final float NULL,
        Fuente_Base varchar(10) NULL,
        Fuente_Tecnica varchar(100) NULL,
        Fecha_Origen date NULL,
        Turno_Origen varchar(5) NULL,
        TM_Origen varchar(10) NULL,
        Resolucion varchar(60) NOT NULL,
        Representatividad_Quimica decimal(18,10) NULL,
        Representatividad_Fisica decimal(18,10) NULL,
        Fecha_Proceso datetime2(3) NOT NULL
            CONSTRAINT DF_trazabilidad_analitos_tm_fecha_proceso DEFAULT SYSDATETIME(),
        CONSTRAINT PK_trazabilidad_analitos_tm_emision_test
            PRIMARY KEY (Fecha, Turno, TM_Destino, Analito)
    );
END;
GO

/*
El ALTER PROCEDURE completo se genera desde la definicion DEV auditada.
La captura se inserta despues de BLOQUE 11I y antes de BLOQUE 12.
*/
