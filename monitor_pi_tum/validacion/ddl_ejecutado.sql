-- DEV exclusivamente. Ejecutar en inventar_SpcHidr.
CREATE TABLE inventar_SpcHidr.contingencia_estado_operacional_test (
    id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_contingencia_estado_operacional_test PRIMARY KEY,
    fecha_operacional date NOT NULL,
    turno char(1) NOT NULL,
    estado_operacional varchar(20) NOT NULL,
    comentario nvarchar(1000) NULL,
    usuario nvarchar(255) NOT NULL,
    fecha_registro datetime2(3) NOT NULL CONSTRAINT DF_contingencia_estado_operacional_test_fecha DEFAULT SYSDATETIME(),
    CONSTRAINT CK_contingencia_estado_operacional_test_turno CHECK (turno IN ('A','B')),
    CONSTRAINT CK_contingencia_estado_operacional_test_estado CHECK (estado_operacional IN ('OPERATIVO','MANTENCION','CAIDA_PI')),
    CONSTRAINT CK_contingencia_estado_operacional_test_usuario CHECK (LEN(LTRIM(RTRIM(usuario))) > 0)
);
CREATE INDEX IX_contingencia_estado_operacional_test_vigente ON inventar_SpcHidr.contingencia_estado_operacional_test
    (fecha_operacional, turno, fecha_registro DESC, id DESC);
GO
CREATE PROCEDURE inventar_SpcHidr.sp_guardar_contingencia_estado_operacional_test
    @fecha_operacional date,
    @turno varchar(10),
    @estado_operacional varchar(50),
    @comentario nvarchar(max),
    @usuario nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    IF DB_NAME() <> 'inventar_SpcHidr' THROW 50010, 'Operacion permitida solo en DEV.', 1;
    IF @fecha_operacional IS NULL THROW 50011, 'Fecha operacional requerida.', 1;
    IF @turno IS NULL OR @turno NOT IN ('A','B') OR DATALENGTH(@turno) <> 1
        THROW 50012, 'Turno invalido.', 1;
    IF @estado_operacional IS NULL OR @estado_operacional NOT IN ('OPERATIVO','MANTENCION','CAIDA_PI')
        THROW 50013, 'Estado operacional invalido.', 1;
    IF @usuario IS NULL OR LEN(LTRIM(RTRIM(@usuario))) = 0 OR DATALENGTH(@usuario) > 510
        THROW 50014, 'Usuario requerido o demasiado largo.', 1;
    IF DATALENGTH(@comentario) > 2000 THROW 50015, 'Comentario supera 1000 caracteres.', 1;
    INSERT INTO inventar_SpcHidr.contingencia_estado_operacional_test (fecha_operacional, turno, estado_operacional, comentario, usuario)
    OUTPUT inserted.id, inserted.fecha_registro
    VALUES (@fecha_operacional, @turno, @estado_operacional, @comentario, @usuario);
END;
GO
CREATE VIEW inventar_SpcHidr.v_contingencia_estado_operacional_actual_test
AS
WITH versiones AS (
    SELECT id AS id_declaracion, fecha_operacional, turno, estado_operacional,
           comentario, usuario, fecha_registro,
           ROW_NUMBER() OVER (PARTITION BY fecha_operacional, turno
                              ORDER BY fecha_registro DESC, id DESC) AS rn
    FROM inventar_SpcHidr.contingencia_estado_operacional_test
)
SELECT id_declaracion, fecha_operacional, turno, estado_operacional, comentario, usuario, fecha_registro
FROM versiones WHERE rn = 1;
GO
CREATE VIEW inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test
AS
SELECT
    b.fecha_operacional,
    b.turno,
    b.equipo_codigo,
    b.estado_tecnico_pi,
    b.estado_fronteras,
    b.valor_pi_bruto,
    b.valor_pi_final,
    b.lectura_inicio_pi,
    b.lectura_fin_pi,
    b.delta_frontera_pi,
    b.ultima_fecha_con_cambio,
    b.segundos_sin_cambio_al_cierre,
    b.tonelaje_apoyo,
    b.fuente_apoyo,
    b.estado_apoyo,
    b.tum_disponible,
    b.tipo_tum,
    b.lectura_inicio_tum,
    b.lectura_fin_tum,
    b.valor_turno_tum,
    b.total_excel_tum,
    b.diferencia_inicio_pi_tum,
    b.diferencia_fin_pi_tum,
    b.diferencia_tonelaje_pi_tum,
    b.tum_batch_id,
    b.archivo_batch,
    b.fuente_resuelta AS fuente_automatica,
    b.valor_bruto_resuelto AS valor_bruto_automatico,
    b.valor_final_resuelto AS valor_final_automatico,
    b.motivo_decision AS motivo_automatico,
    d.id_declaracion,
    d.estado_operacional,
    d.comentario AS comentario_operacional,
    d.usuario AS usuario_declaracion,
    d.fecha_registro AS fecha_declaracion,
    CAST(CASE WHEN d.id_declaracion IS NULL THEN 'AUTOMATICO_LEGACY'
         ELSE 'DECLARACION_ESPECIALISTA' END AS varchar(30)) AS modo_resolucion,
    CAST(CASE
        WHEN d.id_declaracion IS NULL THEN b.fuente_resuelta
        WHEN d.estado_operacional IN ('OPERATIVO','MANTENCION') AND b.valor_pi_final IS NOT NULL THEN 'PI'
        WHEN d.estado_operacional = 'CAIDA_PI' AND t.valido = 1 THEN 'TUM'
        ELSE NULL END AS varchar(30)) AS fuente_resuelta,
    CASE
        WHEN d.id_declaracion IS NULL THEN b.valor_bruto_resuelto
        WHEN d.estado_operacional IN ('OPERATIVO','MANTENCION') AND b.valor_pi_final IS NOT NULL THEN b.valor_pi_bruto
        WHEN d.estado_operacional = 'CAIDA_PI' AND t.valido = 1 THEN b.valor_turno_tum
        ELSE NULL END AS valor_bruto_resuelto,
    CASE
        WHEN d.id_declaracion IS NULL THEN b.valor_final_resuelto
        WHEN d.estado_operacional IN ('OPERATIVO','MANTENCION') AND b.valor_pi_final IS NOT NULL THEN b.valor_pi_final
        WHEN d.estado_operacional = 'CAIDA_PI' AND t.valido = 1 THEN
            CASE WHEN b.equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108')
                      AND b.valor_turno_tum <= 100 THEN 0 ELSE b.valor_turno_tum END
        ELSE NULL END AS valor_final_resuelto,
    CAST(CASE
        WHEN d.id_declaracion IS NULL THEN
            CASE WHEN b.fuente_resuelta IN ('PI','TUM') AND b.valor_final_resuelto IS NOT NULL
                 THEN 'RESUELTO' ELSE 'SIN_RESOLVER' END
        WHEN d.estado_operacional IN ('OPERATIVO','MANTENCION') THEN
            CASE WHEN b.valor_pi_final IS NOT NULL THEN 'RESUELTO' ELSE 'PENDIENTE_PI' END
        WHEN d.estado_operacional = 'CAIDA_PI' AND t.valido = 1 THEN 'RESUELTO'
        ELSE 'PENDIENTE_TUM' END AS varchar(30)) AS estado_resolucion,
    CAST(CASE
        WHEN d.id_declaracion IS NULL THEN b.motivo_decision
        WHEN d.estado_operacional IN ('OPERATIVO','MANTENCION') THEN
            CONCAT('DECLARACION_', d.estado_operacional,
                   CASE WHEN b.valor_pi_final IS NOT NULL THEN '_USA_PI' ELSE '_PI_NO_DISPONIBLE' END)
        WHEN d.estado_operacional = 'CAIDA_PI' AND t.valido = 1 THEN
            CONCAT('DECLARACION_CAIDA_PI_USA_', b.tipo_tum)
        ELSE 'DECLARACION_CAIDA_PI_PENDIENTE_TUM' END AS varchar(100)) AS motivo_decision
FROM inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno AS b
LEFT JOIN inventar_SpcHidr.v_contingencia_estado_operacional_actual_test AS d
    ON d.fecha_operacional = b.fecha_operacional AND d.turno = b.turno
CROSS APPLY (SELECT CASE WHEN b.tum_disponible = 1 AND b.valor_turno_tum IS NOT NULL
                         AND b.valor_turno_tum >= 0 THEN 1 ELSE 0 END AS valido) AS t;
