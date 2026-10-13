-- Versión independiente: fórmulas con códigos M6 y un único bloque de aportes.
-- Generado por scripts/generar_sp_modelo6_v2.py. No modifica los SP actuales.
-- No necesita ejecutar ni instalar los procedimientos anteriores.
CREATE   PROCEDURE [inventar_SpcHidr].[sp_calcular_balance_flujos_modelo6_v2]
    @fecha_inicio date,
    @fecha_fin date,
    @caso_id int = NULL,
    @debug bit = 0
AS
BEGIN
    SET NOCOUNT ON;
    IF @fecha_inicio IS NULL OR @fecha_fin IS NULL
        THROW 51002, 'Se requieren ambas fechas.', 1;
    -------------------------------------------------------------------------
    -- 0) NORMALIZAR FECHAS
    -------------------------------------------------------------------------
    IF @fecha_inicio > @fecha_fin
    BEGIN
        DECLARE @tmp date = @fecha_inicio;
        SET @fecha_inicio = @fecha_fin;
        SET @fecha_fin = @tmp;
    END;
    DECLARE @ff_mas_1 date = DATEADD(DAY, 1, @fecha_fin);
    -- Dias del periodo a balancear (inclusive), usado por el criterio de evaporacion (seccion 8, F61/F62/F64/F71/F72/F74/F75/F77)
    DECLARE @dias_periodo int = DATEDIFF(DAY, @fecha_inicio, @fecha_fin) + 1;

DECLARE @FechaInicioContingenciaTUM date = '2026-09-01';

DECLARE @FechaInicioContingenciaPeriodo date =
    CASE
        WHEN @fecha_inicio > @FechaInicioContingenciaTUM
            THEN @fecha_inicio
        ELSE @FechaInicioContingenciaTUM
    END;

/* ================================================================
   ÚLTIMO DÍA OPERACIONAL COMPLETO

   El balance no debe exigir PI/TUM para:
       - el día operacional actualmente abierto
       - días futuros incluidos en @fecha_fin

   Ejemplo:
       si hoy es 10-09,
       el último día operacional completamente cerrado es 09-09.
================================================================ */
DECLARE @UltimoDiaOperacionalCompleto date =
    CASE
        /* Desde las 08:00 de hoy, ayer ya está completamente cerrado */
        WHEN CAST(GETDATE() AS time) >= '08:00:00'
            THEN DATEADD(DAY, -1, CAST(GETDATE() AS date))

        /* Antes de las 08:00, el día operacional de ayer todavía está abierto */
        ELSE DATEADD(DAY, -2, CAST(GETDATE() AS date))
    END;

DECLARE @FechaFinContingenciaPeriodo date =
    CASE
        WHEN @fecha_fin < @UltimoDiaOperacionalCompleto
            THEN @fecha_fin
        ELSE @UltimoDiaOperacionalCompleto
    END;
    -------------------------------------------------------------------------
    -- 1) TABLA TEMPORAL DE RESULTADOS
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#valores_m6') IS NOT NULL
        DROP TABLE #valores_m6;
    CREATE TABLE #valores_m6
    (
        codigo_flujo varchar(64)  NOT NULL PRIMARY KEY,
        TMS_Inicial  decimal(18,6) NULL,
        Ley_Cu_1     decimal(18,6) NULL,
        TMS_Final    decimal(18,6) NULL,
        Ley_Cu_2     decimal(18,6) NULL,
        Tonelaje     decimal(18,6) NULL,
        Ley_Cu       decimal(18,6) NULL
    );


    IF @caso_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM inventar_SpcHidr.casos_balance
        WHERE caso_id=@caso_id AND modelo=6
          AND CAST(fecha_ini AS date)=@fecha_inicio AND CAST(fecha AS date)=@fecha_fin)
        THROW 51003, 'El caso no corresponde al modelo 6 y período solicitados.', 1;
    CREATE TABLE #definiciones_m6 (destino varchar(10) PRIMARY KEY, componentes int, habilitado bit);
    CREATE TABLE #componentes_m6 (destino varchar(10), origen varchar(64) UNIQUE, orden_componente smallint NOT NULL, PRIMARY KEY(destino, origen));
    CREATE TABLE #m6_manual (destino varchar(10) PRIMARY KEY, masa decimal(18,6), fino decimal(18,6), aplicado bit DEFAULT 0);
    INSERT #definiciones_m6 VALUES
('F1', 1, 1),
('F2', 1, 1),
('F3', 1, 1),
('F4', 1, 1),
('F5', 1, 1),
('F6', 1, 1),
('F7', 1, 1),
('F8', 1, 1),
('F9', 1, 1),
('F10', 1, 1),
('F11', 1, 1),
('F12', 1, 1),
('F13', 1, 1),
('F14', 1, 1),
('F15', 1, 1),
('F16', 1, 1),
('F17', 1, 1),
('F18', 1, 1),
('F19', 1, 1),
('F20', 1, 1),
('F21', 1, 1),
('F22', 1, 1),
('F23', 1, 1),
('F24', 1, 1),
('F25', 1, 1),
('F26', 1, 1),
('F27', 1, 1),
('F28', 1, 1),
('F29', 1, 1),
('F30', 1, 1),
('F31', 1, 1),
('F32', 1, 1),
('F33', 1, 0),
('F34', 1, 1),
('F35', 1, 1),
('F36', 1, 0),
('F37', 1, 1),
('F38', 1, 0),
('F39', 1, 1),
('F40', 1, 1),
('F41', 1, 1),
('F42', 1, 1),
('F43', 1, 1),
('F44', 1, 1),
('F45', 1, 1),
('F46', 1, 1),
('F47', 1, 1),
('F48', 1, 1),
('F49', 1, 1),
('F50', 1, 1),
('F51', 1, 1),
('F52', 1, 1),
('F53', 1, 1),
('F54', 1, 1),
('F55', 1, 1),
('F56', 1, 1),
('F57', 4, 1),
('F58', 1, 1),
('F59', 1, 1),
('F60', 1, 1),
('F61', 1, 1),
('F62', 1, 1),
('F63', 4, 1),
('F64', 1, 1),
('F65', 1, 1),
('F66', 1, 1),
('F67', 1, 1),
('F68', 1, 1),
('F69', 2, 1),
('F70', 2, 1),
('F71', 1, 1),
('F72', 1, 1),
('F73', 1, 1),
('F74', 1, 1),
('F75', 2, 1),
('F76', 2, 1),
('F77', 1, 1),
('F78', 1, 1),
('F79', 1, 1),
('F80', 1, 1),
('F81', 1, 1),
('F82', 1, 1),
('F83', 1, 1),
('F84', 1, 1),
('F85', 1, 1),
('F86', 1, 1),
('F87', 1, 1),
('F88', 1, 1),
('F89', 1, 1),
('F90', 1, 1),
('F91', 1, 1),
('F92', 4, 1),
('F93', 1, 1),
('F94', 4, 1),
('F95', 1, 1),
('F96', 1, 1),
('F97', 1, 1),
('F98', 1, 1),
('F99', 4, 1),
('F100', 1, 1),
('F101', 2, 1),
('F102', 1, 1),
('F103', 1, 1),
('F104', 1, 1),
('F105', 1, 1),
('F106', 1, 1),
('F107', 1, 1),
('F108', 1, 1),
('F109', 1, 1),
('F110', 1, 1),
('F111', 1, 1),
('F112', 1, 1),
('F113', 1, 1),
('F114', 1, 1),
('F115', 1, 1),
('F116', 1, 1),
('F117', 1, 1),
('F118', 1, 1),
('F119', 1, 1),
('F120', 1, 1),
('F121', 1, 1),
('F122', 1, 1);
    INSERT #componentes_m6 VALUES
('F1', 'F1', 1),
('F2', 'F2', 1),
('F3', 'F3', 1),
('F4', 'F4', 1),
('F5', 'F5', 1),
('F6', 'F6', 1),
('F7', 'F7', 1),
('F8', 'F8', 1),
('F9', 'F9', 1),
('F10', 'F10', 1),
('F11', 'F11', 1),
('F12', 'F12', 1),
('F13', 'F13', 1),
('F14', 'F14', 1),
('F15', 'F15', 1),
('F16', 'F16', 1),
('F17', 'F17', 1),
('F18', 'F18', 1),
('F19', 'F19', 1),
('F20', 'F20', 1),
('F21', 'F21', 1),
('F22', 'F22', 1),
('F23', 'F23', 1),
('F24', 'F24', 1),
('F25', 'F25', 1),
('F26', 'F26', 1),
('F27', 'F27', 1),
('F28', 'F28', 1),
('F29', 'F29', 1),
('F30', 'F30', 1),
('F31', 'F31', 1),
('F32', 'F32', 1),
('F33', 'F33', 1),
('F34', 'F34', 1),
('F35', 'F35', 1),
('F36', 'F36', 1),
('F37', 'F37', 1),
('F38', 'F38', 1),
('F39', 'F39', 1),
('F40', 'F40', 1),
('F41', 'F41', 1),
('F42', 'F42', 1),
('F43', 'F43', 1),
('F44', 'F44', 1),
('F45', 'F45', 1),
('F46', 'F46', 1),
('F47', 'F47', 1),
('F48', 'F48', 1),
('F49', 'F49', 1),
('F50', 'F50', 1),
('F51', 'F51', 1),
('F52', 'F52', 1),
('F53', 'F53', 1),
('F54', 'F54', 1),
('F55', 'F55', 1),
('F56', 'F56', 1),
('F57', 'F57_A', 1),
('F57', 'F57_B', 2),
('F57', 'F57_C', 3),
('F57', 'F57_D', 4),
('F58', 'F58', 1),
('F59', 'F59', 1),
('F60', 'F60', 1),
('F61', 'F61', 1),
('F62', 'F62', 1),
('F63', 'F63_A', 1),
('F63', 'F63_B', 2),
('F63', 'F63_C', 3),
('F63', 'F63_D', 4),
('F64', 'F64', 1),
('F65', 'F65', 1),
('F66', 'F66', 1),
('F67', 'F67', 1),
('F68', 'F68', 1),
('F69', 'F69_OX', 1),
('F69', 'F69_SULF', 2),
('F70', 'F70_PRINCIPAL', 1),
('F70', 'F70_ADICIONAL', 2),
('F71', 'F71', 1),
('F72', 'F72', 1),
('F73', 'F73', 1),
('F74', 'F74', 1),
('F75', 'F75_OX', 2),
('F75', 'F75_SULF', 1),
('F76', 'F76_SULF', 1),
('F76', 'F76_OX', 2),
('F77', 'F77', 1),
('F78', 'F78', 1),
('F79', 'F79', 1),
('F80', 'F80', 1),
('F81', 'F81', 1),
('F82', 'F82', 1),
('F83', 'F83', 1),
('F84', 'F84', 1),
('F85', 'F85', 1),
('F86', 'F86', 1),
('F87', 'F87', 1),
('F88', 'F88', 1),
('F89', 'F89', 1),
('F90', 'F90', 1),
('F91', 'F91', 1),
('F92', 'F92_A', 1),
('F92', 'F92_B', 2),
('F92', 'F92_C', 3),
('F92', 'F92_D', 4),
('F93', 'F93', 1),
('F94', 'F94_A', 1),
('F94', 'F94_B', 2),
('F94', 'F94_C', 3),
('F94', 'F94_D', 4),
('F95', 'F95', 1),
('F96', 'F96', 1),
('F97', 'F97', 1),
('F98', 'F98', 1),
('F99', 'F99_A', 1),
('F99', 'F99_B', 2),
('F99', 'F99_C', 3),
('F99', 'F99_D', 4),
('F100', 'F100', 1),
('F101', 'F101_A', 1),
('F101', 'F101_B', 2),
('F102', 'F102', 1),
('F103', 'F103', 1),
('F104', 'F104', 1),
('F105', 'F105', 1),
('F106', 'F106', 1),
('F107', 'F107', 1),
('F108', 'F108', 1),
('F109', 'F109', 1),
('F110', 'F110', 1),
('F111', 'F111', 1),
('F112', 'F112', 1),
('F113', 'F113', 1),
('F114', 'F114', 1),
('F115', 'F115', 1),
('F116', 'F116', 1),
('F117', 'F117', 1),
('F118', 'F118', 1),
('F119', 'F119', 1),
('F120', 'F120', 1),
('F121', 'F121', 1),
('F122', 'F122', 1);
    INSERT #definiciones_m6 VALUES ('F123', 1, 1),('F124', 1, 1),('F125', 1, 1);
    INSERT #componentes_m6 VALUES ('F123', 'F123', 1),('F124', 'F124', 1),('F125', 'F125', 1);
    -- Validar los 125 códigos; Id_flujo es identidad, no el número F.
    IF (SELECT COUNT(*) FROM inventar_SpcHidr.flujo_modelos WHERE modelo=6 AND activo=1)<>125
       OR EXISTS (SELECT destino FROM #definiciones_m6 EXCEPT
                  SELECT Flujos FROM inventar_SpcHidr.flujo_modelos WHERE modelo=6 AND activo=1)
        THROW 51004, 'La definición activa debe contener exactamente F1 a F125.', 1;
    -- Un aporte inválido no se convierte silenciosamente en cero.
    IF EXISTS (
        SELECT 1 FROM BM_manual.fujos_Manuales fm
        WHERE fm.modelo_id=6 AND fm.caso_id=@caso_id AND ISNULL(fm.Activo,1)=1
          AND fm.fecha>=@fecha_inicio AND fm.fecha<@ff_mas_1
          AND (TRY_CONVERT(decimal(18,6),fm.valor) IS NULL
            OR (fm.fcu IS NOT NULL AND TRY_CONVERT(decimal(18,6),fm.fcu) IS NULL)
            OR (fm.fcu IS NULL AND TRY_CONVERT(decimal(18,6),fm.leyCu) IS NULL)
            OR fm.flujo_id IS NULL OR fm.flujo_id NOT BETWEEN 1 AND 125))
        THROW 51005, 'Aporte manual inválido: revisar código, masa, fino o ley.', 1;
    INSERT #m6_manual(destino,masa,fino)
    SELECT CONCAT('F',fm.flujo_id), SUM(CONVERT(decimal(18,6),fm.valor)),
        SUM(COALESCE(TRY_CONVERT(decimal(18,6),fm.fcu),
            TRY_CONVERT(decimal(18,6),fm.valor)*TRY_CONVERT(decimal(18,6),fm.leyCu)/100.0))
    FROM BM_manual.fujos_Manuales fm
    WHERE fm.modelo_id=6 AND fm.caso_id=@caso_id AND ISNULL(fm.Activo,1)=1
      AND fm.fecha>=@fecha_inicio AND fm.fecha<@ff_mas_1
    AND fm.flujo_id NOT IN (24,28)
    GROUP BY fm.flujo_id;
    -- F0 sin fuente operacional: cálculo explícito, incluso sin registros manuales.
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F12', 0, 0); -- F12 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F15', 0, 0); -- F15 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F52', 0, 0); -- F52 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F80', 0, 0); -- F80 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F83', 0, 0); -- F83 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F84', 0, 0); -- F84 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F85', 0, 0); -- F85 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F86', 0, 0); -- F86 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F89', 0, 0); -- F89 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F91', 0, 0); -- F91 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F93', 0, 0); -- F93 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F106', 0, 0); -- F106 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F109', 0, 0); -- F109 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F114', 0, 0); -- F114 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F115', 0, 0); -- F115 = base F0 (0 masa, 0 ley) + aporte manual
    INSERT #valores_m6(codigo_flujo,Tonelaje,Ley_Cu) VALUES ('F122', 0, 0); -- F122 = base F0 (0 masa, 0 ley) + aporte manual
    CREATE TABLE #m6_f0(destino varchar(10) PRIMARY KEY);
    INSERT #m6_f0 VALUES ('F12'),('F15'),('F52'),('F57'),('F63'),('F69'),('F70'),('F75'),('F76'),('F80'),('F83'),('F84'),('F85'),('F86'),('F89'),('F91'),('F92'),('F93'),('F94'),('F99'),('F101'),('F106'),('F109'),('F114'),('F115'),('F122');

    

    -------------------------------------------------------------------------

    -- Etapa 0 aplica los aportes de los F0 manuales ya inicializados.
    -- Cada etapa calcula una base usando los resultados corregidos anteriores.
    -- El bloque común de aportes se ejecuta después de cada etapa, una sola vez por flujo.
    DECLARE @etapa int=0;
    DECLARE @listos TABLE(destino varchar(10) PRIMARY KEY);
    WHILE @etapa<=117
    BEGIN

    -- ETAPA 0: operación y reclamo antes de aportes manuales.
    IF @etapa=0
    BEGIN
-- F20: PAD Óxidos (1). F22: PAD Sulfuros (2).
-- Se conserva el intervalo BETWEEN solicitado para fecha_ini_operacion.
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT d.destino, COALESCE(SUM(cpc.tms_cargado),0),
       COALESCE(SUM(cpc.tms_cargado*cpc.cut_tm_total/100.0)
                /NULLIF(SUM(cpc.tms_cargado),0),0)*100.0
FROM (VALUES ('F20',1),('F22',2)) d(destino,pad_id)
LEFT JOIN (
    inventar_SpcHidr.campana_parcela_control cpc
    INNER JOIN inventar_SpcHidr.parcela p ON p.id_parcela=cpc.parcela_id
    INNER JOIN inventar_SpcHidr.[pad] pa ON pa.id_pad=p.id_pad
) ON pa.id_pad=d.pad_id
 AND cpc.fecha_ini_operacion BETWEEN @fecha_inicio AND @fecha_fin
 AND cpc.tms_cargado IS NOT NULL
GROUP BY d.destino;

-- F30: PAD Sulfuro, fino residual de pilas que se solapan con el período de reclamo.
-- Se reproduce la fórmula solicitada: Tonelaje contiene fino residual, no masa cargada.
;WITH reclamo_sulfuro AS (
    SELECT cpc.campana_id,cpc.parcela_id,cpc.tms_cargado,cpc.cut_tm_total
    FROM inventar_SpcHidr.campana_parcela_control cpc
    INNER JOIN inventar_SpcHidr.parcela p ON p.id_parcela=cpc.parcela_id
    INNER JOIN inventar_SpcHidr.[pad] pa ON pa.id_pad=p.id_pad
    WHERE pa.id_pad=2 AND cpc.fecha_ini_retiro IS NOT NULL
      AND cpc.fecha_ini_retiro<=@fecha_fin
      AND ISNULL(cpc.fecha_fin_retiro,@fecha_fin)>=@fecha_inicio
      AND cpc.tms_cargado IS NOT NULL
), recuperacion_max_su AS (
    SELECT r.campaña_id,r.parcela_id,MAX(r.Recuperacion_parcela) rec_max
    FROM inventar_SpcHidr.Recuperaciones_pad r
    WHERE r.Fecha_drenaje<=@fecha_fin AND r.pad_id=2
    GROUP BY r.campaña_id,r.parcela_id
)
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT 'F30',
       COALESCE(SUM(rs.tms_cargado*rs.cut_tm_total/100.0)-SUM(COALESCE(rm.rec_max,0)),0),
       COALESCE((SUM(rs.tms_cargado*rs.cut_tm_total/100.0)-SUM(COALESCE(rm.rec_max,0)))
                /NULLIF(SUM(rs.tms_cargado),0)*100.0,0)
FROM reclamo_sulfuro rs
LEFT JOIN recuperacion_max_su rm ON rm.campaña_id=rs.campana_id AND rm.parcela_id=rs.parcela_id;

-- F26: PAD Óxido, fino residual de pilas que se solapan con el período de reclamo.
-- Se reproduce la fórmula solicitada: Tonelaje contiene fino residual, no masa cargada.
;WITH reclamo_oxido AS (
    SELECT cpc.campana_id,cpc.parcela_id,cpc.tms_cargado,cpc.cut_tm_total
    FROM inventar_SpcHidr.campana_parcela_control cpc
    INNER JOIN inventar_SpcHidr.parcela p ON p.id_parcela=cpc.parcela_id
    INNER JOIN inventar_SpcHidr.[pad] pa ON pa.id_pad=p.id_pad
    WHERE pa.id_pad=1 AND cpc.fecha_ini_retiro IS NOT NULL
      AND cpc.fecha_ini_retiro<=@fecha_fin
      AND ISNULL(cpc.fecha_fin_retiro,@fecha_fin)>=@fecha_inicio
      AND cpc.tms_cargado IS NOT NULL
), recuperacion_max_ox AS (
    SELECT r.campaña_id,r.parcela_id,MAX(r.Recuperacion_parcela) rec_max
    FROM inventar_SpcHidr.Recuperaciones_pad r
    WHERE r.Fecha_drenaje<=@fecha_fin AND r.pad_id=1
    GROUP BY r.campaña_id,r.parcela_id
)
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT 'F26',
       COALESCE(SUM(ro.tms_cargado*ro.cut_tm_total/100.0)-SUM(COALESCE(rm.rec_max,0)),0),
       COALESCE((SUM(ro.tms_cargado*ro.cut_tm_total/100.0)-SUM(COALESCE(rm.rec_max,0)))
                /NULLIF(SUM(ro.tms_cargado),0)*100.0,0)
FROM reclamo_oxido ro
LEFT JOIN recuperacion_max_ox rm ON rm.campaña_id=ro.campana_id AND rm.parcela_id=ro.parcela_id;

    END;

    -- ETAPA 1; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=1
    BEGIN
    -- Fuentes operacionales y flujos del modelo 6.
    -------------------------------------------------------------------------
/* ================================================================
   BASE COMUN F2 - F1 - F3
   ----------------------------------------------------------------
   PRIORIDAD POR FECHA:
       1. MOV_CAM
       2. POWER BI solo si NO existe MOV_CAM para esa fecha

   MAPEO POWER BI VALIDADO:
       tipo_movimiento = 'REMANEJO' -> STOCK
       tipo_movimiento = 'EXPIT'    -> MINA

       mov_cam.Ton     -> mov_cam_powerbi.tonelaje_descarga_tms
       mov_cam.CuTG00  -> mov_cam_powerbi.cut_ponderado

   IMPORTANTE:
       La sustitucion es por DIA COMPLETO.
       Si existe MOV_CAM para una fecha, no se mezcla POWER BI
       para esa misma fecha.
================================================================ */

DROP TABLE IF EXISTS #Base_BASE_CHANCADO;

;WITH FechasMovCam AS
(
    SELECT DISTINCT
        CAST(m.fecha AS date) AS Fecha
    FROM inventar_SpcHidr.mov_cam m
    WHERE CAST(m.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin
      AND m.Fase <> 'SRR'
      AND m.Destino = 'CH01'
),
Base_BASE_CHANCADO AS
(
    /* ============================================================
       1. FUENTE OFICIAL: MOV_CAM
       ============================================================ */
    SELECT
        CAST(m.fecha AS date) AS Fecha,

CASE
    WHEN UPPER(LTRIM(RTRIM(ISNULL(m.Origen, ''))))
         IN ('STOCK', 'REMANEJO')
        THEN 'Stock'

    WHEN UPPER(LTRIM(RTRIM(ISNULL(m.Origen, ''))))
         IN ('MINA', 'EXPIT')
        THEN 'Mina'

    ELSE m.Origen
END AS Origen,

        TRY_CONVERT(float, m.Ton)     AS Ton,
        TRY_CONVERT(float, m.CuTG00)  AS CuTG00,

        CAST('MOV_CAM' AS varchar(30)) AS Fuente

    FROM inventar_SpcHidr.mov_cam m

    WHERE CAST(m.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin
      AND m.Fase <> 'SRR'
      AND m.Destino = 'CH01'


    UNION ALL


    /* ============================================================
       2. FALLBACK: POWER BI
       Solo dias donde no existe MOV_CAM
       ============================================================ */
    SELECT
        CAST(p.fecha AS date) AS Fecha,

        CASE
            WHEN UPPER(LTRIM(RTRIM(ISNULL(p.tipo_movimiento, ''))))
                 = 'REMANEJO'
                THEN 'Stock'

            WHEN UPPER(LTRIM(RTRIM(ISNULL(p.tipo_movimiento, ''))))
                 = 'EXPIT'
                THEN 'Mina'

            ELSE NULL
        END AS Origen,

        TRY_CONVERT(float, p.tonelaje_descarga_tms) AS Ton,
        TRY_CONVERT(float, p.cut_ponderado)          AS CuTG00,

        CAST('POWERBI_PRELIMINAR' AS varchar(30)) AS Fuente

    FROM inventar_SpcHidr.mov_cam_powerbi p

    WHERE CAST(p.fecha AS date) BETWEEN @fecha_inicio AND @fecha_fin

      AND UPPER(LTRIM(RTRIM(ISNULL(p.fase, '')))) <> 'SRR'

      AND UPPER(LTRIM(RTRIM(ISNULL(p.destino_descarga, ''))))
          = 'CH01'

      AND NOT EXISTS
      (
          SELECT 1
          FROM FechasMovCam mc
          WHERE mc.Fecha = CAST(p.fecha AS date)
      )
)

SELECT
    Fecha,
    Origen,
    Ton,
    CuTG00,
    Fuente
INTO #Base_BASE_CHANCADO
FROM Base_BASE_CHANCADO;


/* ================================================================
   F2 - STOCK
   MOV_CAM  : Origen = Stock
   POWER BI : tipo_movimiento = REMANEJO
================================================================ */
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F2',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_BASE_CHANCADO
WHERE Origen = 'Stock';
    
    END;

    -- ETAPA 2; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=2
    BEGIN





/* ================================================================
   F1 - MINA
   MOV_CAM  : Origen = Mina
   POWER BI : tipo_movimiento = EXPIT
================================================================ */
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F1',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_BASE_CHANCADO
WHERE Origen = 'Mina';
    
    END;

    -- ETAPA 3; lee resultados M6: F1, F2
    IF @etapa=3
    BEGIN





/* ================================================================
   F3 - TOTAL ALIMENTACION CH01 NO SRR

   Mantiene la logica del SP actual:
   F3 no filtra por Origen.
================================================================ */
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F3',

    ISNULL(
        SUM(Ton),
        0
    ),

    ISNULL(
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0,
        0
    )

FROM #Base_BASE_CHANCADO;

    
    -- Público F3 = F1 + F2, después de sus aportes; fino ponderado.
    IF EXISTS (SELECT 1 FROM #valores_m6 WHERE codigo_flujo IN ('F2','F1')
        HAVING COUNT(Tonelaje)=2 AND COUNT(Ley_Cu)=2 AND SUM(Tonelaje)=0
        AND ABS(SUM(Tonelaje*Ley_Cu/100.0))>0.000001)
        THROW 51012, 'F3: la suma tiene masa cero y fino distinto de cero.', 1;
    UPDATE r SET Tonelaje=s.masa,
        Ley_Cu=CASE WHEN s.masa=0 THEN 0 ELSE s.fino*100.0/s.masa END
    FROM #valores_m6 r CROSS JOIN (
        SELECT CASE WHEN COUNT(Tonelaje)=2 THEN SUM(Tonelaje) END masa,
            CASE WHEN COUNT(Tonelaje)=2 AND COUNT(Ley_Cu)=2
                 THEN SUM(Tonelaje*Ley_Cu/100.0) END fino
        FROM #valores_m6 WHERE codigo_flujo IN ('F2','F1')) s
    WHERE r.codigo_flujo='F3';
    
    END;

    -- ETAPA 4; lee resultados M6: F3
    IF @etapa=4
    BEGIN




/* ================================================================
   BASE CONTINGENCIA CORREAS PARA BALANCE
   ----------------------------------------------------------------
   Equipos:
       CHANCADOR_CV006
       PRINCIPAL_CV008
       PRINCIPAL_CV108

   Metodología temporal:
       < 01-09-2026
           fuente histórica vigente

       >= 01-09-2026 y día operacional cerrado
           fuente resuelta PI/TUM por turno

       Día operacional abierto / futuro
           se conserva la fuente PI histórica/provisional

   IMPORTANTE:
       - No incluye CV025.
       - Un valor resuelto = 0 es válido.
       - Para días cerrados no se permite continuar con un
         equipo-turno SIN_RESOLVER.
================================================================ */

DROP TABLE IF EXISTS #Contingencia_Correas;

CREATE TABLE #Contingencia_Correas
(
    fecha_operacional     date          NOT NULL,
    turno                 char(1)       NOT NULL,
    equipo_codigo         varchar(40)   NOT NULL,
    estado_tecnico_pi     varchar(50)   NULL,
    fuente_resuelta       varchar(30)   NULL,
    valor_final_resuelto  decimal(28,6) NULL,
    tipo_tum              varchar(30)   NULL,
    motivo_decision       varchar(80)   NULL,
    PRIMARY KEY (fecha_operacional, turno, equipo_codigo)
);

IF @FechaInicioContingenciaPeriodo <= @FechaFinContingenciaPeriodo
BEGIN
    ;WITH Fechas AS
    (
        SELECT @FechaInicioContingenciaPeriodo AS fecha_operacional

        UNION ALL

        SELECT DATEADD(DAY, 1, fecha_operacional)
        FROM Fechas
        WHERE fecha_operacional < @FechaFinContingenciaPeriodo
    ),
    Turnos AS
    (
        SELECT CAST('A' AS char(1)) AS turno
        UNION ALL
        SELECT CAST('B' AS char(1))
    ),
    Equipos AS
    (
        SELECT CAST('CHANCADOR_CV006' AS varchar(40)) AS equipo_codigo
        UNION ALL SELECT CAST('PRINCIPAL_CV008' AS varchar(40))
        UNION ALL SELECT CAST('PRINCIPAL_CV108' AS varchar(40))
    )
    INSERT INTO #Contingencia_Correas
    (
        fecha_operacional,
        turno,
        equipo_codigo,
        estado_tecnico_pi,
        fuente_resuelta,
        valor_final_resuelto,
        tipo_tum,
        motivo_decision
    )
    SELECT
        f.fecha_operacional,
        t.turno,
        e.equipo_codigo,
        r.estado_tecnico_pi,
        r.fuente_resuelta,
        r.valor_final_resuelto,
        r.tipo_tum,
        r.motivo_decision
    FROM Fechas AS f
    CROSS JOIN Turnos AS t
    CROSS JOIN Equipos AS e
    LEFT JOIN inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno AS r
        ON  r.fecha_operacional = f.fecha_operacional
        AND r.turno             = t.turno
        AND r.equipo_codigo     = e.equipo_codigo
    OPTION (MAXRECURSION 32767);

    IF EXISTS
    (
        SELECT 1
        FROM #Contingencia_Correas
        WHERE fuente_resuelta IS NULL
           OR fuente_resuelta = 'SIN_RESOLVER'
           OR valor_final_resuelto IS NULL
    )
    BEGIN
        THROW 51002,
        'Contingencia correas: existen turnos cerrados sin resolver PI/TUM para CV006/CV008/CV108. El balance no puede continuar con información parcial.',
        1;
    END;
END;

/* ================================================================
   BASE TMH PRINCIPAL PARA BALANCE
   ----------------------------------------------------------------
   TM1 = PRINCIPAL_CV008
   TM2 = PRINCIPAL_CV108

   Esta tabla temporal centraliza únicamente la FUENTE de TMH.
   Las reglas posteriores de humedad, CuT, TMS, FCu y PAD no cambian.
================================================================ */

DROP TABLE IF EXISTS #TMH_Principal_Balance;

CREATE TABLE #TMH_Principal_Balance
(
    Fecha       date        NOT NULL,
    Turno       char(1)     NOT NULL,
    TM          varchar(3)  NOT NULL,
    TMH         float       NULL,
    Fuente_TMH  varchar(30) NULL,
    PRIMARY KEY (Fecha, Turno, TM)
);

/* Histórico pre-cutover + día operacional abierto/futuro. */
INSERT INTO #TMH_Principal_Balance
(
    Fecha,
    Turno,
    TM,
    TMH,
    Fuente_TMH
)
SELECT
    v.Fecha,
    x.Turno,
    x.TM,
    CASE
        WHEN ABS(COALESCE(TRY_CONVERT(float, x.TMH), 0)) > 150000
            THEN 0
        ELSE COALESCE(TRY_CONVERT(float, x.TMH), 0)
    END AS TMH,
    CASE
        WHEN v.Fecha < @FechaInicioContingenciaTUM
            THEN 'PI_HISTORICO'
        ELSE 'PI_DIA_ABIERTO'
    END AS Fuente_TMH
FROM inventar_SpcHidr.v_datos_apilado_tmh_v2 AS v
CROSS APPLY
(
    VALUES
        ('A', 'TM1', v.TMH_CV008_A),
        ('B', 'TM1', v.TMH_CV008_B),
        ('A', 'TM2', v.TMH_CV108_A),
        ('B', 'TM2', v.TMH_CV108_B)
) AS x(Turno, TM, TMH)
WHERE v.Fecha >= @fecha_inicio
  AND v.Fecha < DATEADD(DAY, 1, @fecha_fin)
  AND
  (
         v.Fecha < @FechaInicioContingenciaTUM
      OR v.Fecha > @FechaFinContingenciaPeriodo
  );

/* Días cerrados desde el cutover: PI/TUM resuelto. */
INSERT INTO #TMH_Principal_Balance
(
    Fecha,
    Turno,
    TM,
    TMH,
    Fuente_TMH
)
SELECT
    c.fecha_operacional,
    c.turno,
    CASE
        WHEN c.equipo_codigo = 'PRINCIPAL_CV008' THEN 'TM1'
        WHEN c.equipo_codigo = 'PRINCIPAL_CV108' THEN 'TM2'
    END AS TM,
    CASE
        WHEN ABS(TRY_CONVERT(float, c.valor_final_resuelto)) > 150000
            THEN 0
        ELSE TRY_CONVERT(float, c.valor_final_resuelto)
    END AS TMH,
    c.fuente_resuelta AS Fuente_TMH
FROM #Contingencia_Correas AS c
WHERE c.equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108');

/* ================================================================
   F4 - DESCARGA SECA CHANCADO CV006 HACIA SILO
   ----------------------------------------------------------------
   TONELAJE:
       < 01-09-2026 / día abierto:
           vista_resumen_datos_filtrados.CV006_tot

       >= 01-09-2026, día operacional cerrado:
           #Contingencia_Correas / CHANCADOR_CV006
           (PI prioritario; TUM sólo en contingencia)

       Humedad : 2.5 %
       TMS     : TMH resuelto * 0.975

   LEY Cu:
       Se utiliza la Ley_Cu calculada para F3.

       F3 ya resuelve la jerarquia:
           1. MOV_CAM
           2. POWER BI preliminar cuando falta MOV_CAM

       Esto es equivalente a la logica historica de F4, ya que
       F3 y F4 utilizaban exactamente la misma ley de cabeza:
           Fase <> 'SRR'
           Destino = 'CH01'

   IMPORTANTE:
       Power BI NO reemplaza el tonelaje de F4.
       El tonelaje de F4 sigue viniendo de CV006.
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F4',

    ROUND
    (
        (
            /* Histórico pre-cutover + día operacional abierto/futuro. */
            COALESCE
            (
                (
                    SELECT SUM(TRY_CONVERT(float, v.CV006_tot))
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v
                    WHERE v.fecha_turno >= @fecha_inicio
                      AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)
                      AND
                      (
                             v.fecha_turno < @FechaInicioContingenciaTUM
                          OR v.fecha_turno >= DATEADD(DAY, 1, @FechaFinContingenciaPeriodo)
                      )
                ),
                0
            )
            +
            /* Días cerrados desde el cutover: PI/TUM resuelto por turno. */
            COALESCE
            (
                (
                    SELECT SUM(TRY_CONVERT(float, c.valor_final_resuelto))
                    FROM #Contingencia_Correas AS c
                    WHERE c.equipo_codigo = 'CHANCADOR_CV006'
                ),
                0
            )
        ) * 0.975,
        2
    ) AS Tonelaje,

    COALESCE(
        (
            SELECT f3.Ley_Cu
            FROM #valores_m6 f3
            WHERE f3.codigo_flujo = 'F3'
        ),
        0
    ) AS Ley_Cu;
    
    END;

    -- ETAPA 5; lee resultados M6: F8
    IF @etapa=5
    BEGIN



/* ================================================================
   F8 - DELTA INVENTARIO CHANCADO
   ----------------------------------------------------------------
   NUEVA FUENTE DE INVENTARIO:
       inventar_SpcHidr.v_inventario_chancado_test

   INVENTARIO:
       Apertura periodo:
           Inventario_Chancado_TMS_Anterior de @fecha_inicio

       Cierre periodo:
           Total_Inventario_Chancado_TMS de @fecha_fin

       Delta:
           Cierre - Apertura

   La vista ya incorpora:
       - Silo A-B
       - Harnero A-E
       - Chancado A-E
       - Tolva de compensacion
       - Humedad de inventario
       - Validacion Archive Value
       - Continuidad diaria / semilla

   LEY Cu:
       Se mantiene la metodologia vigente del F8:
       ley CH01 no-SRR en los extremos.

       La fuente de ley respeta ahora:
           MOV_CAM > POWERBI_PRELIMINAR

   IMPORTANTE:
       #Base_BASE_CHANCADO debe seguir existiendo hasta terminar F8.
================================================================ */

;WITH
inv_i AS
(
    SELECT
        CASE
            WHEN MAX(i.Flag_Continuidad_Diaria) = 1
             AND MAX(i.Flag_Inventario_Valido) = 1
            THEN MAX(
                TRY_CONVERT(
                    float,
                    i.Inventario_Chancado_TMS_Anterior
                )
            )
            ELSE NULL
        END AS total_tms

    FROM inventar_SpcHidr.v_inventario_chancado_test i

    WHERE i.Fecha = @fecha_inicio
),

inv_f AS
(
    SELECT
        CASE
            WHEN MAX(i.Flag_Inventario_Valido) = 1
            THEN MAX(
                TRY_CONVERT(
                    float,
                    i.Total_Inventario_Chancado_TMS
                )
            )
            ELSE NULL
        END AS total_tms

    FROM inventar_SpcHidr.v_inventario_chancado_test i

    WHERE i.Fecha = @fecha_fin
),

/* ============================================================
   Ley inicial

   Utiliza la misma base normalizada F2-F3:
       MOV_CAM cuando existe
       POWER BI cuando falta MOV_CAM
   ============================================================ */
ley_i AS
(
    SELECT
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0 AS ley_cu

    FROM #Base_BASE_CHANCADO

    WHERE Fecha = @fecha_inicio
),

/* ============================================================
   Ley final
   ============================================================ */
ley_f AS
(
    SELECT
        (
            SUM(Ton * CuTG00 / 100.0)
            /
            NULLIF(SUM(Ton), 0)
        ) * 100.0 AS ley_cu

    FROM #Base_BASE_CHANCADO

    WHERE Fecha = @fecha_fin
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F8',

    /* Inventario apertura */
    inv_i.total_tms AS TMS_Inicial,

    /* Ley apertura */
    CASE
        WHEN inv_i.total_tms IS NULL
            THEN NULL
        ELSE COALESCE(
            ley_i.ley_cu,
            ley_f.ley_cu
        )
    END AS Ley_Cu_1,

    /* Inventario cierre */
    inv_f.total_tms AS TMS_Final,

    /* Ley cierre */
    CASE
        WHEN inv_f.total_tms IS NULL
            THEN NULL
        ELSE COALESCE(
            ley_f.ley_cu,
            ley_i.ley_cu
        )
    END AS Ley_Cu_2,

    /* Delta inventario */
    CASE
        WHEN inv_i.total_tms IS NULL
          OR inv_f.total_tms IS NULL
            THEN NULL

        ELSE
            inv_f.total_tms
            - inv_i.total_tms
    END AS Tonelaje,

    /* ============================================================
       Ley equivalente del delta de inventario
       ============================================================ */
    CASE
        WHEN inv_i.total_tms IS NULL
          OR inv_f.total_tms IS NULL
          OR (inv_f.total_tms - inv_i.total_tms) = 0
            THEN NULL

        ELSE
            (
                (
                    inv_f.total_tms
                    *
                    COALESCE(
                        ley_f.ley_cu,
                        ley_i.ley_cu
                    )
                    / 100.0
                )
                -
                (
                    inv_i.total_tms
                    *
                    COALESCE(
                        ley_i.ley_cu,
                        ley_f.ley_cu
                    )
                    / 100.0
                )
            )
            /
            NULLIF(
                inv_f.total_tms
                - inv_i.total_tms,
                0
            )
            * 100.0
    END AS Ley_Cu

FROM inv_i
CROSS JOIN inv_f
CROSS JOIN ley_i
CROSS JOIN ley_f;

    
    -- Público F5 y F8 comparten base histórica F5, no sus aportes manuales.
    INSERT #valores_m6
    SELECT 'F5',TMS_Inicial,Ley_Cu_1,TMS_Final,Ley_Cu_2,Tonelaje,Ley_Cu
    FROM #valores_m6 WHERE codigo_flujo='F8';
    
    END;

    -- ETAPA 6; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=6
    BEGIN




/* ================================================================
   #Base_BASE_CHANCADO ya no se necesita despues de F8
================================================================ */
DROP TABLE IF EXISTS #Base_BASE_CHANCADO;

/* ================================================================
   BASE COMUN LEY CuT SRR
   ----------------------------------------------------------------
   Consumidores:
       F11
       F10
       F9

   PRIORIDAD POR FECHA:
       1. MOV_CAM SRR válido
       2. IMP SRR solo si MOV_CAM no tiene ley válida ese día

   IMPORTANTE:
       - MOV_CAM e IMP no se mezclan dentro del mismo día.
       - Ton_Ponderador se utiliza SOLO para calcular la ley.
       - NO define la masa de F11, F10 ni F9.
================================================================ */

DROP TABLE IF EXISTS #Ley_SRR_Dia;

;WITH MOV_CAM_SRR AS
(
    SELECT
        CAST(m.fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN TRY_CONVERT(float, m.Ton) > 0
                 AND TRY_CONVERT(float, m.CuTG00) IS NOT NULL
                THEN TRY_CONVERT(float, m.Ton)
                ELSE 0
            END
        ) AS Ton_Ponderador,

        SUM
        (
            CASE
                WHEN TRY_CONVERT(float, m.Ton) > 0
                 AND TRY_CONVERT(float, m.CuTG00) IS NOT NULL
                THEN
                    TRY_CONVERT(float, m.Ton)
                    * TRY_CONVERT(float, m.CuTG00)
                    / 100.0
                ELSE 0
            END
        ) AS FCu_Ponderador

    FROM inventar_SpcHidr.mov_cam AS m

    WHERE CAST(m.fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND UPPER(LTRIM(RTRIM(ISNULL(m.Fase, '')))) = 'SRR'

      AND UPPER(LTRIM(RTRIM(ISNULL(m.Destino, ''))))
          IN ('PRUEBA', 'CH01')

    GROUP BY
        CAST(m.fecha AS date)
),

MOV_CAM_SRR_VALIDO AS
(
    SELECT
        Fecha,
        Ton_Ponderador,

        FCu_Ponderador
        / NULLIF(Ton_Ponderador, 0)
        * 100.0 AS CuT,

        CAST('MOV_CAM' AS varchar(20)) AS Fuente

    FROM MOV_CAM_SRR

    WHERE Ton_Ponderador > 0
),

IMP_SRR AS
(
    SELECT
        CAST(i.Fecha AS date) AS Fecha,

        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                 AND TRY_CONVERT(float, i.Ton) > 0
                 AND TRY_CONVERT(float, i.CuT) IS NOT NULL
                THEN TRY_CONVERT(float, i.Ton)
                ELSE 0
            END
        ) AS Ton_Ponderador,

        SUM
        (
            CASE
                WHEN ISNULL(i.Es_SRR, 0) = 1
                 AND TRY_CONVERT(float, i.Ton) > 0
                 AND TRY_CONVERT(float, i.CuT) IS NOT NULL
                THEN
                    TRY_CONVERT(float, i.Ton)
                    * TRY_CONVERT(float, i.CuT)
                    / 100.0
                ELSE 0
            END
        ) AS FCu_Ponderador

    FROM DEV_SIIR.hidro.v_imp_chancado_normalizado AS i

    WHERE CAST(i.Fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND ISNULL(i.Es_SRR, 0) = 1

    GROUP BY
        CAST(i.Fecha AS date)
),

IMP_SRR_VALIDO AS
(
    SELECT
        Fecha,
        Ton_Ponderador,

        FCu_Ponderador
        / NULLIF(Ton_Ponderador, 0)
        * 100.0 AS CuT,

        CAST('IMP' AS varchar(20)) AS Fuente

    FROM IMP_SRR

    WHERE Ton_Ponderador > 0
),

LEY_SRR_FINAL AS
(
    /* MOV_CAM tiene prioridad */
    SELECT
        m.Fecha,
        m.Ton_Ponderador,
        m.CuT,
        m.Fuente

    FROM MOV_CAM_SRR_VALIDO AS m


    UNION ALL


    /* IMP rellena solamente días sin MOV_CAM válido */
    SELECT
        i.Fecha,
        i.Ton_Ponderador,
        i.CuT,
        i.Fuente

    FROM IMP_SRR_VALIDO AS i

    WHERE NOT EXISTS
    (
        SELECT 1
        FROM MOV_CAM_SRR_VALIDO AS m
        WHERE m.Fecha = i.Fecha
    )
)

SELECT
    Fecha,
    Ton_Ponderador,
    CuT,
    Fuente

INTO #Ley_SRR_Dia

FROM LEY_SRR_FINAL;


/* ================================================================
   BASE CONTINGENCIA SRR PARA BALANCE
   ================================================================ */

DROP TABLE IF EXISTS #Contingencia_SRR;

CREATE TABLE #Contingencia_SRR
(
    fecha_operacional     date          NOT NULL,
    turno                 char(1)       NOT NULL,
    equipo_codigo         varchar(40)   NOT NULL,

    estado_tecnico_pi     varchar(50)   NULL,
    fuente_resuelta       varchar(30)   NULL,
    valor_final_resuelto  decimal(28,6) NULL,

    tipo_tum              varchar(30)   NULL,
    motivo_decision       varchar(80)   NULL,

    PRIMARY KEY
    (
        fecha_operacional,
        turno,
        equipo_codigo
    )
);


IF @FechaInicioContingenciaPeriodo <= @FechaFinContingenciaPeriodo
BEGIN

    ;WITH Fechas AS
    (
        SELECT
            @FechaInicioContingenciaPeriodo AS fecha_operacional

        UNION ALL

        SELECT
            DATEADD(DAY, 1, fecha_operacional)

        FROM Fechas

        WHERE fecha_operacional < @FechaFinContingenciaPeriodo
    ),

    Turnos AS
    (
        SELECT CAST('A' AS char(1)) AS turno

        UNION ALL

        SELECT CAST('B' AS char(1))
    ),

    Equipos AS
    (
        SELECT CAST('SRR_CV001' AS varchar(40)) AS equipo_codigo

        UNION ALL

        SELECT CAST('SRR_CV002' AS varchar(40))

        UNION ALL

        SELECT CAST('SRR_CV003' AS varchar(40))
    )

    INSERT INTO #Contingencia_SRR
    (
        fecha_operacional,
        turno,
        equipo_codigo,

        estado_tecnico_pi,
        fuente_resuelta,
        valor_final_resuelto,

        tipo_tum,
        motivo_decision
    )

    SELECT
        f.fecha_operacional,
        t.turno,
        e.equipo_codigo,

        r.estado_tecnico_pi,
        r.fuente_resuelta,
        r.valor_final_resuelto,

        r.tipo_tum,
        r.motivo_decision

    FROM Fechas AS f

    CROSS JOIN Turnos AS t

    CROSS JOIN Equipos AS e

    LEFT JOIN
        inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno AS r
        ON  r.fecha_operacional = f.fecha_operacional
        AND r.turno             = t.turno
        AND r.equipo_codigo     = e.equipo_codigo

    OPTION (MAXRECURSION 32767);


    /* ============================================================
       VALIDACIÓN DE SEGURIDAD

       Si falta cualquier fecha + turno + equipo:
       NO continuar con un balance parcial.

       OJO:
       valor_final_resuelto = 0 es perfectamente válido.
       ============================================================ */
    IF EXISTS
    (
        SELECT 1

        FROM #Contingencia_SRR

        WHERE fuente_resuelta IS NULL
           OR fuente_resuelta = 'SIN_RESOLVER'
           OR valor_final_resuelto IS NULL
    )
    BEGIN

        THROW 51001,
        'Contingencia SRR: existen turnos sin resolver PI/TUM. F11, F10 y F9 no pueden calcularse con información parcial.',
        1;

    END;

END;

/* ================================================================
   F11 - SRR LINEA TM1 / CV002
   ----------------------------------------------------------------
Masa:
    < 01-09-2026:
        CV002 histórico

    >= 01-09-2026:
        SRR_CV002 resuelto PI/TUM por turno

    TMS = TMH * 0.97

   Ley:
       #Ley_SRR_Dia
       MOV_CAM -> IMP por fecha
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F11',
/* ============================================================
   MASA

   < 01-09-2026:
       metodología histórica CV002

   >= 01-09-2026:
       valor resuelto por turno:
           PI prioritario
           TUM sólo en contingencia

   Factor TMS:
       0.97
   ============================================================ */
CAST
(
    (
        /* Histórico anterior al 01-09 */
        COALESCE
        (
            (
                SELECT
                    SUM(v.cv002_tot)

                FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v

                WHERE v.fecha_turno >= @fecha_inicio
                  AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)
                  AND v.fecha_turno < @FechaInicioContingenciaTUM
            ),
            0
        )

        +

        /* Desde 01-09: PI/TUM resuelto */
        COALESCE
        (
            (
                SELECT
                    SUM(c.valor_final_resuelto)

                FROM #Contingencia_SRR AS c

                WHERE c.equipo_codigo = 'SRR_CV002'
            ),
            0
        )
    )
    * 0.97

    AS decimal(18,6)
) AS Tonelaje,

    /* ============================================================
       LEY SRR RESUELTA
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(
                    Ton_Ponderador
                    * CuT
                    / 100.0
                )
                /
                NULLIF(
                    SUM(Ton_Ponderador),
                    0
                )
                * 100.0

            FROM #Ley_SRR_Dia
        ),
        0
    ) AS Ley_Cu;
    
    END;

    -- ETAPA 7; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=7
    BEGIN



/* ================================================================
   F10 - SRR LINEA TM2 / CV003
   ----------------------------------------------------------------
    Masa:
        < 01-09-2026:
            CV003 histórico

        >= 01-09-2026:
            SRR_CV003 resuelto PI/TUM por turno

        TMS = TMH * 0.97
   Ley:
       #Ley_SRR_Dia
       MOV_CAM -> IMP por fecha
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F10',

CAST
(
    (
        /* ====================================================
           HISTÓRICO ANTERIOR AL 01-09-2026
           ==================================================== */
        COALESCE
        (
            (
                SELECT
                    SUM(v.cv003_tot)

                FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v

                WHERE v.fecha_turno >= @fecha_inicio
                  AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)
                  AND v.fecha_turno < @FechaInicioContingenciaTUM
            ),
            0
        )

        +

        /* ====================================================
           DESDE 01-09-2026

           Se consume la fuente RESUELTA por turno:
               PI cuando es válido/confiable
               TUM sólo cuando PI entra en contingencia
           ==================================================== */
        COALESCE
        (
            (
                SELECT
                    SUM(c.valor_final_resuelto)

                FROM #Contingencia_SRR AS c

                WHERE c.equipo_codigo = 'SRR_CV003'
            ),
            0
        )
    )
    * 0.97

    AS decimal(18,6)
) AS Tonelaje,

    /* ============================================================
       LEY SRR RESUELTA
       ============================================================ */
    ISNULL
    (
        (
            SELECT
                SUM(
                    Ton_Ponderador
                    * CuT
                    / 100.0
                )
                /
                NULLIF(
                    SUM(Ton_Ponderador),
                    0
                )
                * 100.0

            FROM #Ley_SRR_Dia
        ),
        0
    ) AS Ley_Cu;
    
    END;

    -- ETAPA 8; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=8
    BEGIN



/* ============================================================
   F14 - SAL ASIGNADA A LÍNEA CV201 / TM1

   Masa total diaria:
       topografia_sal, vía v_sal_ajustada

   Distribución:
       participación diaria de CV201 respecto de CV201 + CV202

   Solo se consideran días válidos para balance.
   Ley Cu = 0 %
   ============================================================ */
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F14',
    ISNULL(SUM(s.Sal_CV201_Dia), 0),
    0
FROM inventar_SpcHidr.v_sal_distribuida_correa_test AS s
WHERE s.Fecha >= @fecha_inicio
  AND s.Fecha < DATEADD(DAY, 1, @fecha_fin)
  AND s.Flag_Sal_Balance_Valida = 1;
    
    END;

    -- ETAPA 9; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=9
    BEGIN





/* ============================================================
   F13 - SAL ASIGNADA A LÍNEA CV202 / TM2

   Masa total diaria:
       topografia_sal, vía v_sal_ajustada

   Distribución:
       participación diaria de CV202 respecto de CV201 + CV202

   Solo se consideran días válidos para balance.
   Ley Cu = 0 %
   ============================================================ */
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F13',
    ISNULL(SUM(s.Sal_CV202_Dia), 0),
    0
FROM inventar_SpcHidr.v_sal_distribuida_correa_test AS s
WHERE s.Fecha >= @fecha_inicio
  AND s.Fecha < DATEADD(DAY, 1, @fecha_fin)
  AND s.Flag_Sal_Balance_Valida = 1;
    
    END;

    -- ETAPA 10; lee resultados M6: F10, F11, F13, F14
    IF @etapa=10
    BEGIN




  /* ================================================================
   F6 / F7 - MINERAL NETO TM1 / TM2
   ----------------------------------------------------------------
   ORDEN DE CALCULO:
       F11  = SRR linea TM1
       F10  = SRR linea TM2
       F14 = Sal linea TM1
       F13 = Sal linea TM2

       Luego:

       F6 = TMS bruto TM1 - F11 - F14
       F7 = TMS bruto TM2 - F10 - F13

   COBRE FINO:
       FCu F6 = FCu bruto TM1 - FCu F11
       FCu F7 = FCu bruto TM2 - FCu F10

   La sal no aporta cobre:
       F14 Ley Cu = 0
       F13 Ley Cu = 0

   FUENTES BASE:
       TMS bruto:
           #TMH_Principal_Balance
           (histórico PI / resolver PI-TUM desde cutover)
           + humedad resuelta por TM/turno

       Ley CuT bruta:
           inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test

   IMPORTANTE:
       - No se recalculan F11/F10/F14/F13.
       - Se consumen directamente desde #valores_m6.
       - No se fuerza F6/F7 >= 0.
       - Si existe una inconsistencia instrumental, debe quedar visible.
================================================================ */


/* ================================================================
   1. BASE BRUTA TM1 / TM2
================================================================ */

DROP TABLE IF EXISTS #Base_F116;

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_fin)
    )
),

TMH AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH
    FROM #TMH_Principal_Balance
    WHERE Fecha >= @fecha_inicio
      AND Fecha < DATEADD(DAY, 1, @fecha_fin)
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT,
        l.Fuente_CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,
        Fuente_CuT,

        /* --------------------------------------------------------
           TMS BRUTO
           -------------------------------------------------------- */
        CASE
            WHEN TMH = 0
                THEN 0

            /* No inventar humedad */
            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                * (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                  )
        END AS TMS,

        /* --------------------------------------------------------
           COBRE FINO BRUTO
           -------------------------------------------------------- */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    * (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                      )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0
        END AS FCu

    FROM Base
),

Resumen AS
(
    SELECT
        TM,

        /* --------------------------------------------------------
           Si existe TMH positivo sin humedad, no omitir
           silenciosamente el turno.
           -------------------------------------------------------- */
        CASE
            WHEN SUM(
                    CASE
                        WHEN TMH > 0
                         AND Humedad IS NULL
                        THEN 1
                        ELSE 0
                    END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)
        END AS TMS_Bruto,

        /* --------------------------------------------------------
           Igual criterio para cobre fino.
           -------------------------------------------------------- */
        CASE
            WHEN SUM(
                    CASE
                        WHEN TMH > 0
                         AND (
                                Humedad IS NULL
                                OR CuT IS NULL
                             )
                        THEN 1
                        ELSE 0
                    END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)
        END AS FCu_Bruto,

        SUM(
            CASE
                WHEN TMH > 0
                 AND Humedad IS NULL
                THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_Humedad,

        SUM(
            CASE
                WHEN TMH > 0
                 AND Humedad IS NOT NULL
                 AND CuT IS NULL
                THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_CuT

    FROM Calculo

    GROUP BY TM
)

SELECT
    TM,
    TMS_Bruto,
    FCu_Bruto,
    Turnos_Sin_Humedad,
    Turnos_Sin_CuT

INTO #Base_F116

FROM Resumen;


/* ================================================================
   2. RECUPERAR F11 / F10 / F14 / F13 YA CALCULADOS

   No se vuelve a consultar sus fuentes.
================================================================ */

;WITH Flujos_Aux AS
(
    SELECT
        MAX(
            CASE
                WHEN codigo_flujo = 'F11'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F11_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F11'
                THEN
                    TRY_CONVERT(float, Tonelaje)
                    * TRY_CONVERT(float, Ley_Cu)
                    / 100.0
            END
        ) AS F11_FCu,


        MAX(
            CASE
                WHEN codigo_flujo = 'F10'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F10_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F10'
                THEN
                    TRY_CONVERT(float, Tonelaje)
                    * TRY_CONVERT(float, Ley_Cu)
                    / 100.0
            END
        ) AS F10_FCu,


        MAX(
            CASE
                WHEN codigo_flujo = 'F14'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F14_TMS,


        MAX(
            CASE
                WHEN codigo_flujo = 'F13'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F13_TMS

    FROM #valores_m6

    WHERE codigo_flujo IN
    (
        'F11',
        'F10',
        'F14',
        'F13'
    )
),

F116_Calculado AS
(
    SELECT
        b.TM,

        /* ========================================================
           TONELAJE NETO
           ======================================================== */

        CASE
            WHEN b.TM = 'TM1'
            THEN
                  b.TMS_Bruto
                - ISNULL(f.F11_TMS, 0)
                - ISNULL(f.F14_TMS, 0)

            WHEN b.TM = 'TM2'
            THEN
                  b.TMS_Bruto
                - ISNULL(f.F10_TMS, 0)
                - ISNULL(f.F13_TMS, 0)

        END AS TMS_Neto,


        /* ========================================================
           COBRE FINO NETO

           Sal no resta cobre porque Ley Cu = 0.
           ======================================================== */

        CASE
            WHEN b.TM = 'TM1'
            THEN
                  b.FCu_Bruto
                - ISNULL(f.F11_FCu, 0)

            WHEN b.TM = 'TM2'
            THEN
                  b.FCu_Bruto
                - ISNULL(f.F10_FCu, 0)

        END AS FCu_Neto

    FROM #Base_F116 AS b

    CROSS JOIN Flujos_Aux AS f
),

F116_Final AS
(
    SELECT
        TM,
        TMS_Neto,
        FCu_Neto,

        CASE
            WHEN TMS_Neto IS NULL
              OR FCu_Neto IS NULL
                THEN NULL

            WHEN TMS_Neto = 0
                THEN 0

            ELSE
                FCu_Neto
                / NULLIF(TMS_Neto, 0)
                * 100.0

        END AS Ley_Cu_Neta

    FROM F116_Calculado
)


/* ================================================================
   3. INSERT DEFINITIVO F6 / F7
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    CASE
        WHEN TM = 'TM1' THEN 'F6'
        WHEN TM = 'TM2' THEN 'F7'
    END AS codigo_flujo,

    CAST(
        TMS_Neto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        Ley_Cu_Neta
        AS decimal(18,6)
    ) AS Ley_Cu

FROM F116_Final

WHERE TM IN ('TM1', 'TM2');
    
    END;

    -- ETAPA 11; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=11
    BEGIN





/* ================================================================
   F16 / F17 - ALIMENTACION BRUTA A AGLOMERADO
   ----------------------------------------------------------------
   F16 = TM1 / CV008
   F17 = TM2 / CV108

   Se reutiliza #Base_F116 ya calculada para F6/F7.

   FUENTES:
       TMH:
           #TMH_Principal_Balance
           (histórico PI / resolver PI-TUM desde cutover)

       Humedad:
           fn_humedad_resuelta_tm_turno_test

       CuT:
           v_leyes_resueltas_data_tm_reporte_test

   IMPORTANTE:
       - F16/F17 son corrientes medidas brutas.
       - No se calculan sumando F6+F11+F14 o F7+F10+F13.
       - No dependen de import_leyes_torres.
================================================================ */


/* ================================================================
   F16 - TM1 / CV008
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F16',

    CAST(
        TMS_Bruto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        CASE
            WHEN TMS_Bruto IS NULL
              OR FCu_Bruto IS NULL
                THEN NULL

            WHEN TMS_Bruto = 0
                THEN 0

            ELSE
                FCu_Bruto
                / NULLIF(TMS_Bruto, 0)
                * 100.0
        END
        AS decimal(18,6)
    ) AS Ley_Cu

FROM #Base_F116

WHERE TM = 'TM1';
    
    END;

    -- ETAPA 12; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=12
    BEGIN





/* ================================================================
   F17 - TM2 / CV108
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F17',

    CAST(
        TMS_Bruto
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST(
        CASE
            WHEN TMS_Bruto IS NULL
              OR FCu_Bruto IS NULL
                THEN NULL

            WHEN TMS_Bruto = 0
                THEN 0

            ELSE
                FCu_Bruto
                / NULLIF(TMS_Bruto, 0)
                * 100.0
        END
        AS decimal(18,6)
    ) AS Ley_Cu

FROM #Base_F116

WHERE TM = 'TM2';
    
    END;

    -- ETAPA 13; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=13
    BEGIN





/* ================================================================
   #Base_F116 ya no se necesita después de F16/F17
================================================================ */

DROP TABLE IF EXISTS #Base_F116;
/* ================================================================
   F19 / F18 - APILADO POR PAD
   ----------------------------------------------------------------
   F19 = Alimentación asociada a PAD 2
   F18 = Alimentación asociada a PAD 1

   FUENTES DE MASA Y LEY:
       TMH:
           #TMH_Principal_Balance
           (histórico PI / resolver PI-TUM desde cutover)

       Humedad:
           inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test

       CuT:
           inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test

   ASIGNACION A PAD:
       inventar_SpcHidr.control_apilado_diario

   IMPORTANTE:
       - control_apilado_diario.fecha YA corresponde a fecha operacional.
       - NO aplicar DATEADD(DAY,-1,fecha).
       - Solo se asignan días con volumen_diario_m3 > 0.
       - TM1 + TM2 se consolidan por fecha antes de asignar al PAD.
       - No se utiliza import_leyes_torres.
       - No se inventa humedad ni CuT faltante.
================================================================ */


/* ================================================================
   1. BASE DIARIA OPERACIONAL TM1 + TM2
================================================================ */

DROP TABLE IF EXISTS #Base_BASE_APILADO_Dia;

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_fin)
    )
),

TMH AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH
    FROM #TMH_Principal_Balance
    WHERE Fecha >= @fecha_inicio
      AND Fecha < DATEADD(DAY, 1, @fecha_fin)
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT,
        l.Fuente_CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,
        Fuente_CuT,

        /* ========================================================
           TMS
           ======================================================== */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                *
                (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                )

        END AS TMS,

        /* ========================================================
           COBRE FINO
           ======================================================== */
        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    *
                    (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                    )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0

        END AS FCu

    FROM Base
),

Resumen_Diario AS
(
    SELECT
        Fecha,

        /* ========================================================
           TMS total TM1 + TM2 del día

           Si existe TMH positivo sin humedad, el día queda NULL.
           ======================================================== */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND Humedad IS NULL
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)

        END AS TMS_Dia,


        /* ========================================================
           Cobre fino total TM1 + TM2 del día

           Si falta humedad o CuT para un turno con masa positiva,
           no se omite silenciosamente.
           ======================================================== */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND
                              (
                                  Humedad IS NULL
                                  OR CuT IS NULL
                              )
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)

        END AS FCu_Dia,


        SUM
        (
            CASE
                WHEN TMH > 0
                 AND Humedad IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_Humedad,


        SUM
        (
            CASE
                WHEN TMH > 0
                 AND Humedad IS NOT NULL
                 AND CuT IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Turnos_Sin_CuT

    FROM Calculo

    GROUP BY Fecha
)

SELECT
    Fecha,
    TMS_Dia,
    FCu_Dia,
    Turnos_Sin_Humedad,
    Turnos_Sin_CuT

INTO #Base_BASE_APILADO_Dia

FROM Resumen_Diario;


/* ================================================================
   2. FECHAS OPERACIONALES CON APILADO POR PAD

   control_apilado_diario.fecha YA está desplazada D-1
   durante la importación.

   NO volver a aplicar DATEADD(DAY,-1,...).
================================================================ */

DROP TABLE IF EXISTS #Pad_BASE_APILADO_Dia;

SELECT DISTINCT
    CAST(cad.fecha AS date) AS Fecha,
    cad.pad_id

INTO #Pad_BASE_APILADO_Dia

FROM inventar_SpcHidr.control_apilado_diario AS cad

WHERE CAST(cad.fecha AS date)
      BETWEEN @fecha_inicio AND @fecha_fin

  AND cad.pad_id IN (1, 2)

  AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0;


/* ================================================================
   3. RESUMEN F19 / F18
   ----------------------------------------------------------------
   PAD 2 -> F19
   PAD 1 -> F18
================================================================ */

;WITH Configuracion AS
(
    SELECT
        CAST('F19' AS varchar(10)) AS codigo_flujo,
        2 AS pad_id

    UNION ALL

    SELECT
        CAST('F18' AS varchar(10)),
        1
),

Resumen AS
(
    SELECT
        c.codigo_flujo,
        c.pad_id,

        COUNT(p.Fecha) AS Dias_Con_Apilado,

        /* Día PAD sin base instrumental */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND b.Fecha IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_Base,

        /* Falta de humedad */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND ISNULL(b.Turnos_Sin_Humedad, 0) > 0
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_Humedad,

        /* Falta de CuT */
        SUM
        (
            CASE
                WHEN p.Fecha IS NOT NULL
                 AND ISNULL(b.Turnos_Sin_CuT, 0) > 0
                    THEN 1
                ELSE 0
            END
        ) AS Dias_Sin_CuT,

        SUM(b.TMS_Dia) AS TMS_Total,
        SUM(b.FCu_Dia) AS FCu_Total

    FROM Configuracion AS c

    LEFT JOIN #Pad_BASE_APILADO_Dia AS p
        ON p.pad_id = c.pad_id

    LEFT JOIN #Base_BASE_APILADO_Dia AS b
        ON b.Fecha = p.Fecha

    GROUP BY
        c.codigo_flujo,
        c.pad_id
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    codigo_flujo,

    /* ============================================================
       TONELAJE
       ============================================================ */
    CAST
    (
        CASE
            /* PAD sin días de apilado en el período */
            WHEN Dias_Con_Apilado = 0
                THEN 0

            /* No ocultar falta de información operacional */
            WHEN Dias_Sin_Base > 0
              OR Dias_Sin_Humedad > 0
                THEN NULL

            ELSE TMS_Total
        END

        AS decimal(18,6)
    ) AS Tonelaje,


    /* ============================================================
       LEY Cu
       ============================================================ */
    CAST
    (
        CASE
            /* PAD sin días de apilado */
            WHEN Dias_Con_Apilado = 0
                THEN 0

            /* Falta información necesaria para ley */
            WHEN Dias_Sin_Base > 0
              OR Dias_Sin_Humedad > 0
              OR Dias_Sin_CuT > 0
                THEN NULL

            WHEN TMS_Total = 0
                THEN 0

            ELSE
                FCu_Total
                / NULLIF(TMS_Total, 0)
                * 100.0
        END

        AS decimal(18,6)
    ) AS Ley_Cu

FROM Resumen;
    
    END;

    -- ETAPA 14; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=14
    BEGIN





/* ================================================================
   4. LIMPIEZA
================================================================ */

DROP TABLE IF EXISTS #Base_BASE_APILADO_Dia;
DROP TABLE IF EXISTS #Pad_BASE_APILADO_Dia;
/* ================================================================
   F38 - RIPIO TOTAL MEDIDO POR CV025
   ----------------------------------------------------------------
   Fuente física:
       CV025 = correa común de las rotopalas asociadas a F35/F32.

   Señales disponibles:
       cv025tot  = señal histórica/legacy
       cv025_tot = señal nueva

   Regla:
       1. Construir una serie única a nivel de registro mediante:
              COALESCE(cv025_tot, cv025tot)

       2. Calcular el delta diario sobre esa serie.

       3. Proteger:
              - resets;
              - diferencias negativas;
              - saltos diarios > 100.000 TMH.

       4. Humedad operacional fija vigente:
              10 %

          TMS = TMH * 0.90

   IMPORTANTE:
       No se fuerza cierre contra F35/F32.
       CV025 es una medición independiente.
================================================================ */

;WITH CV025_Base AS
(
    SELECT
        CAST(df.fecha_turno AS date) AS Fecha,

        COALESCE
        (
            TRY_CONVERT(float, df.cv025_tot),
            TRY_CONVERT(float, df.cv025tot)
        ) AS CV025_Totalizador

    FROM inventar_SpcHidr.datos_filtrados AS df

    /*
       Se incluye el día siguiente a @fecha_fin porque necesitamos
       su primer totalizador para cerrar correctamente el último día.
    */
    WHERE df.fecha_turno >= @fecha_inicio
      AND df.fecha_turno < DATEADD(DAY, 2, @fecha_fin)
),

CV025_Dia AS
(
    SELECT
        Fecha,
        MIN(CV025_Totalizador) AS Min_CV025,
        MAX(CV025_Totalizador) AS Max_CV025

    FROM CV025_Base

    GROUP BY Fecha
),

CV025_Con_Siguiente AS
(
    SELECT
        Fecha,
        Min_CV025,
        Max_CV025,

        LEAD(Min_CV025)
            OVER (ORDER BY Fecha) AS Next_Min_CV025

    FROM CV025_Dia
),

CV025_Validado AS
(
    SELECT
        Fecha,

        CASE

            /* Sin señal válida */
            WHEN Min_CV025 IS NULL
              OR Max_CV025 IS NULL
                THEN 0

            /* Protección adicional */
            WHEN Max_CV025 - Min_CV025 < 0
                THEN 0

            /* Último día disponible:
               usar recorrido interno solo si es razonable */
            WHEN Next_Min_CV025 IS NULL
             AND Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            WHEN Next_Min_CV025 IS NULL
                THEN 0

            /* Reset entre días:
               usar recorrido interno si éste es válido */
            WHEN Next_Min_CV025 - Min_CV025 < 0
             AND Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            WHEN Next_Min_CV025 - Min_CV025 < 0
                THEN 0

            /* Operación normal */
            WHEN Next_Min_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Next_Min_CV025 - Min_CV025

            /* Fallback al recorrido interno */
            WHEN Max_CV025 - Min_CV025
                 BETWEEN 0 AND 100000
                THEN Max_CV025 - Min_CV025

            /* Spike no físicamente razonable */
            ELSE 0

        END AS CV025_TMH_Dia

    FROM CV025_Con_Siguiente
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F38',

    ISNULL
    (
        SUM(CV025_TMH_Dia) * 0.90,
        0
    ),

    0

FROM CV025_Validado

WHERE Fecha BETWEEN @fecha_inicio AND @fecha_fin;
    
    END;

    -- ETAPA 15; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=15
    BEGIN



/* ================================================================
   F36 - RECLAMO POR CAMIONES PAD SULFUROS
   ----------------------------------------------------------------
   Fuente:
       Datos_conciliados_of.Camiones_TMS_Reclamo_Sulfuros

   Esta columna corresponde al cálculo operacional de camiones
   de reclamo persistido en Datos Conciliados.

   Validación agosto 2026:
       coincide 1:1 con reclamo.v_reclamo_para_conciliados.

   La ley Cu se asigna posteriormente usando la ley de F35.
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F36',

    ISNULL(
        SUM(Camiones_TMS_Reclamo_Sulfuros),
        0
    ),

    0

FROM inventar_SpcHidr.Datos_conciliados_of

WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;
    
    END;

    -- ETAPA 16; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=16
    BEGIN



-- F33
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F33',
    ISNULL(SUM(Camiones_TMS_Reclamo_Oxidos), 0),
    0
FROM inventar_SpcHidr.Datos_conciliados_of
WHERE fecha BETWEEN @fecha_inicio AND @fecha_fin;
    
    END;

    -- ETAPA 17; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=17
    BEGIN



    -- F25 y F29: se recalculan mas adelante en base a F70_PRINCIPAL/F72/F44/F48/F47 (ver seccion final antes de la salida)
/* ================================================================
   F9 - ALIMENTACION SRR CV001
   ----------------------------------------------------------------

   METODOLOGIA POR PERIODO

   < 01-07-2026
       CV001 histórico acumulativo

   01-07-2026 a 31-08-2026
       Process Value PI
       integración cada 10 segundos

   >= 01-09-2026
       SRR_CV001 resuelto por turno:
           PI prioritario
           TUM sólo en contingencia

   Humedad:
       TMS = TMH * 0.97

   IMPORTANTE:
       MOV_CAM / IMP sólo caracterizan la Ley CuT.
       No definen la masa de F9.
       No se fuerza F9 = F11 + F10.
================================================================ */

;WITH F9_Historico AS
(
    /* ============================================================
       1. HISTORICO ANTERIOR AL 01-07-2026
       ============================================================ */
    SELECT
        SUM
        (
            TRY_CONVERT(float, v.cv001_tot)
        ) AS TMH

    FROM inventar_SpcHidr.vista_resumen_datos_filtrados AS v

    WHERE v.fecha_turno >= @fecha_inicio
      AND v.fecha_turno < DATEADD(DAY, 1, @fecha_fin)
      AND v.fecha_turno < '2026-07-01'
),

F9_ProcessValue_PreContingencia AS
(
    /* ============================================================
       2. PROCESS VALUE

       Desde 01-07-2026
       hasta antes del 01-09-2026.

       Conserva exactamente la integración vigente:
           t/h * 10 / 3600
       ============================================================ */
    SELECT
        SUM
        (
            TRY_CONVERT(float, t.tot_001)
            * 10.0
            / 3600.0
        ) AS TMH

    FROM inventar_SpcHidr.tot_tm AS t

    WHERE t.fecha_turno >=
          CASE
              WHEN @fecha_inicio < '2026-07-01'
                  THEN CONVERT(date, '2026-07-01')
              ELSE @fecha_inicio
          END

      AND t.fecha_turno <= @fecha_fin

      AND t.fecha_turno < @FechaInicioContingenciaTUM

      AND t.tot_001 IS NOT NULL
      AND TRY_CONVERT(float, t.tot_001) >= 0
),

F9_Resuelto_Contingencia AS
(
    /* ============================================================
       3. DESDE 01-09-2026

       No se lee TUM directamente.

       valor_final_resuelto contiene:
           PI  cuando PI es confiable
           TUM cuando PI entra en contingencia

       #Contingencia_SRR ya está limitada al período operacional
       cerrado y validado.
       ============================================================ */
    SELECT
        SUM
        (
            c.valor_final_resuelto
        ) AS TMH

    FROM #Contingencia_SRR AS c

    WHERE c.equipo_codigo = 'SRR_CV001'
),

F9_Tonelaje AS
(
    SELECT
        (
              COALESCE(h.TMH, 0)
            + COALESCE(p.TMH, 0)
            + COALESCE(r.TMH, 0)
        )
        * 0.97 AS TMS

    FROM F9_Historico AS h

    CROSS JOIN F9_ProcessValue_PreContingencia AS p

    CROSS JOIN F9_Resuelto_Contingencia AS r
),

F9_Ley AS
(
    /* ============================================================
       LEY SRR

       SIN CAMBIOS:
           MOV_CAM
           ->
           IMP fallback
       ============================================================ */
    SELECT
        SUM
        (
            l.Ton_Ponderador
            * l.CuT
            / 100.0
        )
        /
        NULLIF
        (
            SUM(l.Ton_Ponderador),
            0
        )
        * 100.0 AS Ley_Cu

    FROM #Ley_SRR_Dia AS l
)


INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F9',

    CAST
    (
        COALESCE(t.TMS, 0)
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST
    (
        COALESCE(l.Ley_Cu, 0)
        AS decimal(18,6)
    ) AS Ley_Cu

FROM F9_Tonelaje AS t

CROSS JOIN F9_Ley AS l;
    
    END;

    -- ETAPA 18; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=18
    BEGIN





/* ================================================================
   Limpieza
================================================================ */

DROP TABLE IF EXISTS #Contingencia_SRR;
DROP TABLE IF EXISTS #Ley_SRR_Dia;
    -------------------------------------------------------------------------
    -- 3) F35
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f35_oficial') IS NOT NULL
        DROP TABLE #tmp_f35_oficial;
    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.[campaña_id],
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
Pct_Historico AS
(
    /* ============================================================
       Historial de avance por PAD / campaña / módulo.

       control_reclamo_diario.fecha YA es fecha operacional.
       No aplicar D-1 adicional.
       ============================================================ */
    SELECT
        CAST(crd.fecha AS date) AS fecha,
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id,

        CASE
            WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
            WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
            ELSE MAX(crd.avance_porcentaje)
        END AS pct_clip

    FROM inventar_SpcHidr.control_reclamo_diario AS crd

    WHERE CAST(crd.fecha AS date) <= @fecha_fin

    GROUP BY
        CAST(crd.fecha AS date),
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id
),

Pct_Diario AS
(
    /* ============================================================
       1. Registros del período
       ============================================================ */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    WHERE h.fecha BETWEEN @fecha_inicio AND @fecha_fin


    UNION ALL


    /* ============================================================
       2. Semilla:
          último estado anterior al inicio del período,
          por PAD / campaña / módulo.

          Permite que LAG calcule correctamente el incremento
          del primer día operacional.
       ============================================================ */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    INNER JOIN
    (
        SELECT
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(fecha) AS fecha

        FROM Pct_Historico

        WHERE fecha < @fecha_inicio

        GROUP BY
            pad_id,
            [campaña_id],
            modulo_id
    ) AS s

        ON  s.pad_id       = h.pad_id
        AND s.[campaña_id] = h.[campaña_id]
        AND s.modulo_id    = h.modulo_id
        AND s.fecha        = h.fecha
),
    Pct_Segmentado AS (
        SELECT
            p.*,
            CASE
                WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id
                    ORDER BY p.fecha
                ) THEN 1
                ELSE 0
            END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT
            ps.*,
            SUM(ps.reset_flag) OVER (
                PARTITION BY ps.[campaña_id], ps.modulo_id, ps.pad_id
                ORDER BY ps.fecha
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha,
            p.pad_id,
            p.[campaña_id],
            p.modulo_id,
            p.pct_clip AS avance_porcentaje,
            CASE
                WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                )) < 0 THEN 0
                ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                ))
            END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha,
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date)
      BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            a.fecha AS fecha_operacion,
            a.[campaña_id],
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm
          ON tm.[campaña_id] = a.[campaña_id]
         AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario vd
          ON vd.fecha = a.fecha
         AND vd.pad_id = a.pad_id
         AND vd.[campaña_id] = a.[campaña_id]
         AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 2
          AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ModulosActivos AS (
        SELECT
            r.[campaña_id],
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (
                    SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                    / NULLIF(SUM(ma.tms_reclamado_modulo), 0)
                ) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c
            ON ma.[campaña_id] = c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m
            ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p
            ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd
            ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr
            ON clr.Campana = c.[numero_campaña]
           AND clr.Parcela = p.numero
           AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        WHERE pd.id_pad = 2
    )
    SELECT
        t.Tonelaje,
        l.Ley_Cu
    INTO #tmp_f35_oficial
    FROM Calculo_Tonelaje t
    CROSS JOIN Calculo_Ley l;
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F35', Tonelaje, Ley_Cu
    FROM #tmp_f35_oficial;
    
    END;

    -- ETAPA 19; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=19
    BEGIN



    -------------------------------------------------------------------------
    -- 4) F32
    -------------------------------------------------------------------------
    IF OBJECT_ID('tempdb..#tmp_f32_oficial') IS NOT NULL
        DROP TABLE #tmp_f32_oficial;
    ;WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.[campaña_id],
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos mt
        GROUP BY mt.[campaña_id], mt.modulo_id
    ),
Pct_Historico AS
(
    SELECT
        CAST(crd.fecha AS date) AS fecha,
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id,

        CASE
            WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
            WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
            ELSE MAX(crd.avance_porcentaje)
        END AS pct_clip

    FROM inventar_SpcHidr.control_reclamo_diario AS crd

    WHERE CAST(crd.fecha AS date) <= @fecha_fin

    GROUP BY
        CAST(crd.fecha AS date),
        crd.pad_id,
        crd.[campaña_id],
        crd.modulo_id
),

Pct_Diario AS
(
    /* Registros del período */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    WHERE h.fecha BETWEEN @fecha_inicio AND @fecha_fin


    UNION ALL


    /* Último estado previo = semilla */
    SELECT
        h.fecha,
        h.pad_id,
        h.[campaña_id],
        h.modulo_id,
        h.pct_clip

    FROM Pct_Historico AS h

    INNER JOIN
    (
        SELECT
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(fecha) AS fecha

        FROM Pct_Historico

        WHERE fecha < @fecha_inicio

        GROUP BY
            pad_id,
            [campaña_id],
            modulo_id
    ) AS s
        ON  s.pad_id       = h.pad_id
        AND s.[campaña_id] = h.[campaña_id]
        AND s.modulo_id    = h.modulo_id
        AND s.fecha        = h.fecha
),

    Pct_Segmentado AS (
        SELECT
            p.*,
            CASE
                WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id
                    ORDER BY p.fecha
                ) THEN 1
                ELSE 0
            END AS reset_flag
        FROM Pct_Diario p
    ),
    Pct_Seg_Id AS (
        SELECT
            ps.*,
            SUM(ps.reset_flag) OVER (
                PARTITION BY ps.[campaña_id], ps.modulo_id, ps.pad_id
                ORDER BY ps.fecha
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS seg_id
        FROM Pct_Segmentado ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha,
            p.pad_id,
            p.[campaña_id],
            p.modulo_id,
            p.pct_clip AS avance_porcentaje,
            CASE
                WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                )) < 0 THEN 0
                ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (
                    PARTITION BY p.[campaña_id], p.modulo_id, p.pad_id, p.seg_id
                    ORDER BY p.fecha
                ))
            END AS avance_incremental
        FROM Pct_Seg_Id p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha,
            pad_id,
            [campaña_id],
            modulo_id,
            MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY CAST(fecha AS date), pad_id, [campaña_id], modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            a.fecha AS fecha_operacion,
            a.[campaña_id],
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario a
        JOIN Tms_Apilado_Por_Modulo tm
          ON tm.[campaña_id] = a.[campaña_id]
         AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario vd
          ON vd.fecha = a.fecha
         AND vd.pad_id = a.pad_id
         AND vd.[campaña_id] = a.[campaña_id]
         AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 1
          AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ModulosActivos AS (
        SELECT
            r.[campaña_id],
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario r
        WHERE r.fecha_operacion BETWEEN @fecha_inicio AND @fecha_fin
        GROUP BY r.[campaña_id], r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (
                    SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                    / NULLIF(SUM(ma.tms_reclamado_modulo), 0)
                ) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos ma
        INNER JOIN inventar_SpcHidr.campaña c
            ON ma.[campaña_id] = c.[id_campaña]
        INNER JOIN inventar_SpcHidr.modulo m
            ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela p
            ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad pd
            ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio clr
            ON clr.Campana = c.[numero_campaña]
           AND clr.Parcela = p.numero
           AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        WHERE pd.id_pad = 1
    )
    SELECT
        t.Tonelaje,
        l.Ley_Cu
    INTO #tmp_f32_oficial
    FROM Calculo_Tonelaje t
    CROSS JOIN Calculo_Ley l;
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F32', Tonelaje, Ley_Cu
    FROM #tmp_f32_oficial;
    
    END;

    -- ETAPA 20; lee resultados M6: F32, F35
    IF @etapa=20
    BEGIN



    -------------------------------------------------------------------------
    -- Variables de F35/F32 requeridas para la seccion 7 (ajustes finales)
    -------------------------------------------------------------------------
    DECLARE
        @ton_f35 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F35'), 0),
        @ley_f35 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F35'), 0),
        @ton_f32 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F32'), 0),
        @ley_f32 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F32'), 0);
    -------------------------------------------------------------------------
    -- 7) AJUSTES FINALES DE LEYES
    -------------------------------------------------------------------------
    UPDATE #valores_m6
       SET Ley_Cu = @ley_f35
     WHERE codigo_flujo = 'F36';
    UPDATE #valores_m6
       SET Ley_Cu = @ley_f32
     WHERE codigo_flujo = 'F33';
    UPDATE #valores_m6
       SET Ley_Cu = CASE
                        WHEN (@ton_f35 + @ton_f32) = 0 THEN 0
                        ELSE ((@ton_f35 * @ley_f35) + (@ton_f32 * @ley_f32)) / (@ton_f35 + @ton_f32)
                    END
     WHERE codigo_flujo = 'F38';
    -------------------------------------------------------------------------
    -- Fuentes operacionales y flujos del modelo 6.
    -------------------------------------------------------------------------
    

    UPDATE #definiciones_m6 SET habilitado=1 WHERE destino IN ('F33','F36','F38');
    
    END;

    -- ETAPA 21; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=21
    BEGIN

    -- F95
    -- H2SO4 hacia Tambor AD001
    --
    -- Fuente anterior:
    --   tags_sx_ew.acido_aglomerado_1_m3h
    --   Granularidad: 1 registro por hora
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.acido_aglomerado_tambor_ad001_m3h
    --   Granularidad: 1 registro diario
    --
    -- Conversión:
    --   m3/h * 24 h/dia * 1.84 t/m3 = t H2SO4/dia

    ;WITH base_f95 AS (
        SELECT 
            COALESCE(t.acido_aglomerado_tambor_ad001_m3h, 0) 
            * 24.0
            * 1.84 AS flujo_ton_dia
        FROM inventar_SpcHidr.insumos_area_humeda_flujos t
        WHERE t.fecha_registro >= @fecha_inicio
          AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
    )
    INSERT INTO #valores_m6 
    (
        codigo_flujo, Tonelaje, Ley_Cu
    )
    SELECT      
            'F95', 
            COALESCE(SUM(flujo_ton_dia), 0), 
            0.0
    FROM base_f95;
    
    END;

    -- ETAPA 22; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=22
    BEGIN




    -- F96
    -- H2SO4 hacia Tambor AD100
    --
    -- Fuente anterior:
    --   tags_sx_ew.acido_aglomerado_100_m3h
    --   Granularidad: horaria
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.acido_aglomerado_tambor_ad100_m3h
    --   Granularidad: diaria
    --
    -- Conversión:
    --   m3/h * 24 h/dia * 1.84 t/m3 = t H2SO4/dia
    ;WITH base_f96 AS (
        SELECT 
            COALESCE(t.acido_aglomerado_tambor_ad100_m3h, 0) 
            * 24.0
            * 1.84 AS flujo_ton_dia
        FROM inventar_SpcHidr.insumos_area_humeda_flujos t
        WHERE t.fecha_registro >= @fecha_inicio
          AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
    )
    INSERT INTO #valores_m6 
    (
        codigo_flujo, Tonelaje, Ley_Cu
    )
    SELECT 
            'F96', 
            COALESCE(SUM(flujo_ton_dia), 0), 
            0.0
    FROM base_f96;
    
    END;

    -- ETAPA 23; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=23
    BEGIN



-- F39-F40
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES
    ('F39',0,0),('F40',0,0);
    
    END;

    -- ETAPA 24; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=24
    BEGIN



-- F51 - DPLS
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_dpls_m3h
-- Concentración:
--   conc_cu.dump_dpls_cu
--
-- Integración:
--   m3/h * 24 h/dia = m3/dia

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_dpls_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.dump_dpls_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F51',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;
    
    END;

    -- ETAPA 25; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=25
    BEGIN




-- F77 - Feed DUMP
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_feed_dump_m3h
-- Concentración:
--   conc_cu.dump_feed_cu

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_feed_dump_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.dump_feed_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F77',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;
    
    END;

    -- ETAPA 26; lee resultados M6: F51, F77
    IF @etapa=26
    BEGIN




/* ================================================================
   F42 - TRANSFERENCIA DE COBRE DESDE PAD DUMP MINERAL A SOLUCION
   ----------------------------------------------------------------
   F51 = DPLS
   F77 = Feed DUMP

   Densidad de soluciones asumida:
       1.0 t/m3

   Cobre fino:
       CuF37 = F51 * Ley37 / 100
       CuF38 = F77 * Ley38 / 100

   Balance de cobre del nodo solucion:
       F42 + CuF38 = CuF35 + CuF37

   Como CuF35 = 0:

       F42 = CuF37 - CuF38

   F42 representa directamente toneladas de cobre fino:
       Ley F42 = 100 %
       CuF33    = F42
================================================================ */

;WITH F51 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu

    FROM #valores_m6

    WHERE codigo_flujo = 'F51'
),

F77 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu

    FROM #valores_m6

    WHERE codigo_flujo = 'F77'
),

Calculo_F42 AS
(
    SELECT
        /* Cobre fino DPLS */
        F51.Tonelaje
        * F51.Ley_Cu
        / 100.0 AS CuF37,

        /* Cobre fino Feed DUMP */
        F77.Tonelaje
        * F77.Ley_Cu
        / 100.0 AS CuF38

    FROM F51
    CROSS JOIN F77
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F42',

    /* F42 = CuF37 - CuF38 */
    CuF37 - CuF38,

    /* F42 ya representa cobre fino */
    100.0

FROM Calculo_F42;
    
    END;

    -- ETAPA 27; lee resultados M6: F42, F51, F77
    IF @etapa=27
    BEGIN



/* ================================================================
   F53 - VARIACION / RESIDUAL PAD DUMP SOLUCION
   ----------------------------------------------------------------
   Balance de masa del nodo solucion:

       F42 + F77 = F53 + F51 + F41

   Actualmente:
       F41 = 0

   Por lo tanto:

       F53 = F42 + F77 - F51

   Convencion del modelo:
       Ley F53 = 0 %
       CuF35   = 0

   Densidad de solucion asumida:
       1.0 t/m3
================================================================ */

;WITH F42 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #valores_m6

    WHERE codigo_flujo = 'F42'
),

F51 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #valores_m6

    WHERE codigo_flujo = 'F51'
),

F77 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #valores_m6

    WHERE codigo_flujo = 'F77'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F53',

      F42.Tonelaje
    + F77.Tonelaje
    - F51.Tonelaje,

    0.0

FROM F42
CROSS JOIN F51
CROSS JOIN F77;
    
    END;

    -- ETAPA 28; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=28
    BEGIN



/* ================================================================
   F41 - TRANSFERENCIA / AJUSTE PAD DUMP
   ----------------------------------------------------------------
   Convencion actual del modelo:

       F41 = 0
       Ley F41 = 0 %
       CuF34 = 0

   No existe una corriente operacional asociada actualmente.
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
VALUES
(
    'F41',
    0.0,
    0.0
);
    
    END;

    -- ETAPA 29; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=29
    BEGIN



/* ================================================================
   AUX_DESCARTE_MINERAL - DESCARTE MINERAL LIXIVIADO PAD DUMP
   ----------------------------------------------------------------
   Actualmente no existe fuente operacional disponible y trazable.

   Convencion vigente:
       AUX_DESCARTE_MINERAL     = 0
       Ley AUX_DESCARTE_MINERAL = 0 %
       CuF32   = 0
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
VALUES
(
    'AUX_DESCARTE_MINERAL',
    0.0,
    0.0
);
    
    END;

    -- ETAPA 30; lee resultados M6: F42
    IF @etapa=30
    BEGIN




/* ================================================================
   F43 - VARIACION INVENTARIO CU PAD DUMP MINERAL
   ----------------------------------------------------------------
   Balance de masa nodo solido:

       F39 + F40 + F41 = AUX_DESCARTE_MINERAL + F43 + F42

   Actualmente:
       F39 = 0
       F40 = 0
       AUX_DESCARTE_MINERAL = 0
       F41 = 0

   Por lo tanto:

       F43 = -F42

   Balance de cobre:

       CuF36 = -CuF33

   Como F42 representa directamente cobre fino:
       CuF33 = F42

   entonces:
       F43   = -F42
       CuF36 = -F42
       Ley36 = 100 %

   Si F42 = 0:
       F43   = 0
       Ley36 = 0
================================================================ */

;WITH F42 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float, Tonelaje),
            0
        ) AS Tonelaje

    FROM #valores_m6

    WHERE codigo_flujo = 'F42'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F43',

    -F42.Tonelaje,

    CASE
        WHEN F42.Tonelaje = 0
            THEN 0.0
        ELSE 100.0
    END

FROM F42;
    
    END;

    -- ETAPA 31; lee resultados M6: F18, F19
    IF @etapa=31
    BEGIN




/* ================================================================
   F71 / F73 - REFINO HACIA AGLOMERADO DISTRIBUIDO POR PAD
   ----------------------------------------------------------------
   Relación:
       F71 -> PAD1 -> proporción de F18
       F73 -> PAD2 -> proporción de F19

   IMPORTANTE:
       - NO se recalculan F19/F18.
       - Se consumen directamente desde #valores_m6.
       - Así F71/F73 heredan exactamente la misma lógica validada
         de masa, humedad, CuT y fecha operacional.
================================================================ */

;WITH Base_BASE_APILADO AS
(
    SELECT
        MAX
        (
            CASE
                WHEN codigo_flujo = 'F19'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F19_TMS,

        MAX
        (
            CASE
                WHEN codigo_flujo = 'F18'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F18_TMS

    FROM #valores_m6

    WHERE codigo_flujo IN ('F19', 'F18')
),

Proporcion AS
(
    SELECT
        F19_TMS,
        F18_TMS,

        CASE
            /* Si falta una de las bases, no inventar proporción */
            WHEN F19_TMS IS NULL
              OR F18_TMS IS NULL
                THEN NULL

            WHEN F19_TMS + F18_TMS = 0
                THEN 0

            ELSE
                F19_TMS
                / NULLIF(F19_TMS + F18_TMS, 0)
        END AS Prop_F19,

        CASE
            WHEN F19_TMS IS NULL
              OR F18_TMS IS NULL
                THEN NULL

            WHEN F19_TMS + F18_TMS = 0
                THEN 0

            ELSE
                F18_TMS
                / NULLIF(F19_TMS + F18_TMS, 0)
        END AS Prop_F18

    FROM Base_BASE_APILADO
),

Total_Refino_Aglomerado AS
(
    SELECT
        /* ========================================================
           Volumen total de refino hacia aglomerado

           m3/h * 24 h/día
           ======================================================== */
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
        ) AS Total_Ton,

        /* ========================================================
           Se mantiene por ahora la lógica vigente de ley.
           No se modifica en este cambio.
           ======================================================== */
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
            *
            COALESCE(
                t.refino_oxidos_aglomerado_cu_tambor_ad100_g_l,
                0
            )
        )
        /
        NULLIF
        (
            SUM
            (
                (
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                        0
                    )
                    +
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                        0
                    )
                )
                * 24.0
            ),
            0
        )
        / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.insumos_area_humeda_flujos AS t

    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)

/* ================================================================
   F71 -> PAD1 / F18
================================================================ */

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F71',

    CASE
        WHEN p.Prop_F18 IS NULL
            THEN NULL

        ELSE
            COALESCE(r.Total_Ton, 0)
            * p.Prop_F18
    END,

    COALESCE(r.Ley_Cu, 0)

FROM Total_Refino_Aglomerado AS r
CROSS JOIN Proporcion AS p;
    
    END;

    -- ETAPA 32; lee resultados M6: F18, F19
    IF @etapa=32
    BEGIN





/* ================================================================
   F73 -> PAD2 / F19
================================================================ */

;WITH Base_BASE_APILADO AS
(
    SELECT
        MAX(
            CASE
                WHEN codigo_flujo = 'F19'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F19_TMS,

        MAX(
            CASE
                WHEN codigo_flujo = 'F18'
                THEN TRY_CONVERT(float, Tonelaje)
            END
        ) AS F18_TMS

    FROM #valores_m6

    WHERE codigo_flujo IN ('F19', 'F18')
),

Proporcion AS
(
    SELECT
        CASE
            WHEN F19_TMS IS NULL
              OR F18_TMS IS NULL
                THEN NULL

            WHEN F19_TMS + F18_TMS = 0
                THEN 0

            ELSE
                F19_TMS
                / NULLIF(F19_TMS + F18_TMS, 0)
        END AS Prop_F19

    FROM Base_BASE_APILADO
),

Total_Refino_Aglomerado AS
(
    SELECT
        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
        ) AS Total_Ton,

        SUM
        (
            (
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                    0
                )
                +
                COALESCE(
                    t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                    0
                )
            )
            * 24.0
            *
            COALESCE(
                t.refino_oxidos_aglomerado_cu_tambor_ad100_g_l,
                0
            )
        )
        /
        NULLIF
        (
            SUM
            (
                (
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad001_m3h,
                        0
                    )
                    +
                    COALESCE(
                        t.refino_oxidos_aglomerado_tambor_ad100_m3h,
                        0
                    )
                )
                * 24.0
            ),
            0
        )
        / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.insumos_area_humeda_flujos AS t

    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F73',

    CASE
        WHEN p.Prop_F19 IS NULL
            THEN NULL

        ELSE
            COALESCE(r.Total_Ton, 0)
            * p.Prop_F19
    END,

    COALESCE(r.Ley_Cu, 0)

FROM Total_Refino_Aglomerado AS r
CROSS JOIN Proporcion AS p;
    
    END;

    -- ETAPA 33; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=33
    BEGIN



-- F70_ADICIONAL
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES
    ('F70_ADICIONAL',0,0);
    
    END;

    -- ETAPA 34; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=34
    BEGIN




/* ================================================================
   F70_PRINCIPAL / F60 / F72 / F66 / F81
   RIEGO A PARCELAS CLASIFICADO POR NATURALEZA DE SOLUCION
   ----------------------------------------------------------------

   Fuente:
       inventar_SpcHidr.v_riego_parcelas_origen

   Mapeo:

       OX + REFINO   -> F70_PRINCIPAL
       OX + ILS      -> F60
       OX + DPLS     -> F81

       SULF + REFINO -> F72
       SULF + ILS    -> F66

   Concentraciones:

       F70_PRINCIPAL -> conc_cu.oxidos_refino_cu
       F60 -> conc_cu.oxidos_ils_a_piscina_cu
       F81 -> conc_cu.dump_dpls_cu

       F72 -> conc_cu.sulfuros_refino_cu
       F66 -> conc_cu.sulfuros_ils_a_piscina_cu

   Integracion:
       caudal_riego [m3/h]
       x duración real del intervalo [h]

   Densidad de solución:
       1 t/m3

   Conversión ley:
       g/L / 10 = % Cu
================================================================ */

;WITH Configuracion AS
(
    SELECT 'F70_PRINCIPAL' AS codigo_flujo, 'OX' AS pila_codigo, 'REFINO' AS origen_riego
    UNION ALL
    SELECT 'F60', 'OX',   'ILS'
    UNION ALL
    SELECT 'F81', 'OX',   'DPLS'
    UNION ALL
    SELECT 'F72', 'SULF', 'REFINO'
    UNION ALL
    SELECT 'F66', 'SULF', 'ILS'
),

/* ================================================================
   Concentraciones diarias

   Se consolida por fecha para impedir multiplicación de filas
   si conc_cu contiene más de un registro para un mismo día.
================================================================ */
Concentraciones AS
(
    SELECT
        CAST(c.fecha_registro AS date) AS Fecha,

        AVG(
            TRY_CONVERT(float, c.oxidos_refino_cu)
        ) AS Cu_Refino_Ox,

        AVG(
            TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)
        ) AS Cu_ILS_Ox,

        AVG(
            TRY_CONVERT(float, c.dump_dpls_cu)
        ) AS Cu_DPLS,

        AVG(
            TRY_CONVERT(float, c.sulfuros_refino_cu)
        ) AS Cu_Refino_Sulf,

        AVG(
            TRY_CONVERT(float, c.sulfuros_ils_a_piscina_cu)
        ) AS Cu_ILS_Sulf

    FROM inventar_SpcHidr.conc_cu AS c

    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

    GROUP BY
        CAST(c.fecha_registro AS date)
),

/* ================================================================
   Caudal de cada parcela integrado por duración real
================================================================ */
Riego_Base AS
(
    SELECT
        CAST(v.fecha_registro AS date) AS Fecha,

        UPPER(
            LTRIM(RTRIM(v.pila_codigo))
        ) AS pila_codigo,

        UPPER(
            LTRIM(RTRIM(v.origen_riego))
        ) AS origen_riego,

        TRY_CONVERT(float, v.caudal_riego)
        *
        (
            DATEDIFF_BIG
            (
                SECOND,
                v.fecha_registro,
                v.intervalo_fin
            )
            / 3600.0
        ) AS Volumen

    FROM inventar_SpcHidr.v_riego_parcelas_origen AS v

    WHERE CAST(v.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin

      AND v.intervalo_fin > v.fecha_registro

      AND UPPER(
              LTRIM(RTRIM(ISNULL(v.estado_operacional,'')))
          ) = 'ACTIVO'

      AND TRY_CONVERT(float, v.caudal_riego) >= 0
),

/* ================================================================
   Asignar concentración según PAD + naturaleza
================================================================ */
Riego_Con_Ley AS
(
    SELECT
        r.Fecha,
        r.pila_codigo,
        r.origen_riego,
        r.Volumen,

        CASE

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'REFINO'
                THEN c.Cu_Refino_Ox

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'ILS'
                THEN c.Cu_ILS_Ox

            WHEN r.pila_codigo = 'OX'
             AND r.origen_riego = 'DPLS'
                THEN c.Cu_DPLS

            WHEN r.pila_codigo = 'SULF'
             AND r.origen_riego = 'REFINO'
                THEN c.Cu_Refino_Sulf

            WHEN r.pila_codigo = 'SULF'
             AND r.origen_riego = 'ILS'
                THEN c.Cu_ILS_Sulf

            ELSE NULL

        END AS Cu_g_L

    FROM Riego_Base AS r

    LEFT JOIN Concentraciones AS c
        ON c.Fecha = r.Fecha
),

Resumen AS
(
    SELECT
        pila_codigo,
        origen_riego,

        SUM(Volumen) AS Tonelaje,

        SUM
        (
            CASE
                WHEN Volumen > 0
                 AND Cu_g_L IS NULL
                    THEN 1
                ELSE 0
            END
        ) AS Registros_Sin_Ley,

        SUM
        (
            CASE
                WHEN Cu_g_L IS NOT NULL
                THEN Volumen * Cu_g_L
            END
        ) AS Suma_Cu_Ponderada,

        SUM
        (
            CASE
                WHEN Cu_g_L IS NOT NULL
                THEN Volumen
            END
        ) AS Volumen_Con_Ley

    FROM Riego_Con_Ley

    WHERE origen_riego IN ('REFINO', 'ILS', 'DPLS')

    GROUP BY
        pila_codigo,
        origen_riego
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)

SELECT
    cfg.codigo_flujo,

    CAST(
        COALESCE(r.Tonelaje, 0)
        AS decimal(18,6)
    ) AS Tonelaje,

    CAST
    (
        CASE

            /* No existe ese tipo de riego durante el período */
            WHEN COALESCE(r.Tonelaje,0) = 0
                THEN 0

            /* Hay masa real pero falta concentración:
               no inventar ley */
            WHEN COALESCE(r.Registros_Sin_Ley,0) > 0
                THEN NULL

            ELSE
                (
                    r.Suma_Cu_Ponderada
                    /
                    NULLIF(r.Volumen_Con_Ley,0)
                )
                / 10.0
        END

        AS decimal(18,6)
    ) AS Ley_Cu

FROM Configuracion AS cfg

LEFT JOIN Resumen AS r
    ON  r.pila_codigo = cfg.pila_codigo
    AND r.origen_riego = cfg.origen_riego;
    
    END;

    -- ETAPA 35; lee resultados M6: F66, F72
    IF @etapa=35
    BEGIN



/* ================================================================
   F67 - PERDIDA POR EVAPORACION PAD SULFUROS
   ----------------------------------------------------------------
   Criterio vigente:
       F67 = 5 % de (F72 + F66)

   Se mantiene temporalmente el factor fijo de 5 %, pero F67
   queda como corriente explicita del balance.

   Ley Cu = 0 %
================================================================ */

;WITH F72 AS
(
    SELECT COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F72'
),
F66 AS
(
    SELECT COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F66'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F67',
    (F72.Tonelaje + F66.Tonelaje) * 0.05,
    0
FROM F72
CROSS JOIN F66;
    
    END;

    -- ETAPA 36; lee resultados M6: F60, F70_ADICIONAL, F70_PRINCIPAL, F81
    IF @etapa=36
    BEGIN




/* ================================================================
   F68 - PERDIDA POR EVAPORACION PAD OXIDOS
   ----------------------------------------------------------------
   Criterio vigente:
       F68 = 5 % de (F70_PRINCIPAL + F60 + F70_ADICIONAL + F81)

   Se mantiene temporalmente el factor fijo de 5 %, pero F68
   queda como corriente explicita del balance.

   Ley Cu = 0 %
================================================================ */

;WITH F70_PRINCIPAL AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F70_PRINCIPAL'
),
F60 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F60'
),
F70_ADICIONAL AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F70_ADICIONAL'
),
F81 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F81'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F68',
    (F70_PRINCIPAL.Tonelaje + F60.Tonelaje + F70_ADICIONAL.Tonelaje + F81.Tonelaje) * 0.05,
    0.0
FROM F70_PRINCIPAL
CROSS JOIN F60
CROSS JOIN F70_ADICIONAL
CROSS JOIN F81;
    
    END;

    -- ETAPA 37; lee resultados M6: F60, F68, F70_ADICIONAL, F70_PRINCIPAL, F81
    IF @etapa=37
    BEGIN



/* ================================================================
   F44 - INGRESO A PISCINA PLS OXIDOS
   ----------------------------------------------------------------
   Balance:

       F70_PRINCIPAL + F70_ADICIONAL + F60 + F81 = F44 + F68

   Despejando:

       F44 = F70_PRINCIPAL + F70_ADICIONAL + F60 + F81 - F68

   F68 representa explicitamente la perdida por evaporacion.

   IMPORTANTE:
       - Se elimina el antiguo factor * 0.95 de F44.
       - Se mantiene sin cambios la fuente actual de Ley Cu:
             riego_concentrados_oxido.ingreso_piscina_pls_cu_pp
       - El flujo diario bruto sigue utilizandose solamente para
         ponderar la concentracion.
================================================================ */

;WITH Flujo_Base_Diario AS
(
    SELECT
        CAST(f.fecha_registro AS date) AS Fecha,

        (
            COALESCE(f.parcela_01,0)
          + COALESCE(f.parcela_02,0)
          + COALESCE(f.parcela_03,0)
          + COALESCE(f.parcela_04,0)
          + COALESCE(f.parcela_05,0)
          + COALESCE(f.parcela_06,0)
          + COALESCE(f.parcela_07,0)
          + COALESCE(f.parcela_08,0)
          + COALESCE(f.parcela_09,0)
          + COALESCE(f.parcela_10,0)
          + COALESCE(f.parcela_11,0)
          + COALESCE(f.parcela_12,0)
          + COALESCE(f.parcela_13,0)
          + COALESCE(f.parcela_14,0)
          + COALESCE(f.parcela_15,0)
          + COALESCE(f.parcela_16,0)
          + COALESCE(f.parcela_17,0)
          + COALESCE(f.parcela_18,0)
          + COALESCE(f.parcela_19,0)
          + COALESCE(f.parcela_20,0)
          + COALESCE(f.parcela_21,0)
          + COALESCE(f.parcela_22,0)
          + COALESCE(f.parcela_23,0)
          + COALESCE(f.parcela_24,0)
          + COALESCE(f.parcela_25,0)
          + COALESCE(f.parcela_26,0)
          + COALESCE(f.parcela_27,0)
          + COALESCE(f.parcela_28,0)
          + COALESCE(f.parcela_29,0)
          + COALESCE(f.parcela_30,0)
          + COALESCE(f.parcela_31,0)
          + COALESCE(f.parcela_32,0)
        ) * 24.0 AS Flujo_Base_Dia

    FROM inventar_SpcHidr.flujos_reales_oxido AS f

    WHERE CAST(f.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),

Ley_Diaria AS
(
    SELECT
        CAST(p.fecha_registro AS date) AS Fecha,
        NULLIF(p.ingreso_piscina_pls_cu_pp, 0) AS Cu_g_L

    FROM inventar_SpcHidr.riego_concentrados_oxido AS p

    WHERE CAST(p.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),

Ley_F44 AS
(
    SELECT
        COALESCE
        (
            SUM
            (
                CASE
                    WHEN l.Cu_g_L IS NOT NULL
                    THEN f.Flujo_Base_Dia * l.Cu_g_L
                END
            )
            /
            NULLIF
            (
                SUM
                (
                    CASE
                        WHEN l.Cu_g_L IS NOT NULL
                        THEN f.Flujo_Base_Dia
                    END
                ),
                0
            ),
            0
        ) / 10.0 AS Ley_Cu

    FROM Flujo_Base_Diario AS f

    INNER JOIN Ley_Diaria AS l
        ON l.Fecha = f.Fecha
),

Flujos AS
(
    SELECT
        MAX(CASE
                WHEN codigo_flujo = 'F70_PRINCIPAL'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F70_PRINCIPAL,

        MAX(CASE
                WHEN codigo_flujo = 'F60'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F60,

        MAX(CASE
                WHEN codigo_flujo = 'F70_ADICIONAL'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F70_ADICIONAL,

        MAX(CASE
                WHEN codigo_flujo = 'F81'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F81,

        MAX(CASE
                WHEN codigo_flujo = 'F68'
                THEN TRY_CONVERT(float,Tonelaje)
            END) AS F68

    FROM #valores_m6

    WHERE codigo_flujo IN
    (
        'F70_PRINCIPAL',
        'F60',
        'F70_ADICIONAL',
        'F81',
        'F68'
    )
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F44',

      COALESCE(f.F70_PRINCIPAL,0)
    + COALESCE(f.F60,0)
    + COALESCE(f.F70_ADICIONAL,0)
    + COALESCE(f.F81,0)
    - COALESCE(f.F68,0),

    COALESCE(l.Ley_Cu,0)

FROM Flujos AS f
CROSS JOIN Ley_F44 AS l;
    
    END;

    -- ETAPA 38; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=38
    BEGIN



--F48
;WITH flujo_f48 AS (
    SELECT
        CAST(r.fecha_registro AS date) AS fecha,
        COALESCE(r.bleed, 0) * 24.0 AS flujo_ton_dia
    FROM inventar_SpcHidr.riego_bleed r
    WHERE CAST(r.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
ley_f48 AS (
    SELECT
        CAST(p.fecha_registro AS date) AS fecha,
        NULLIF(p.bleed_cu_pp, 0) AS cu_g_l
    FROM inventar_SpcHidr.riego_concentrados_sulfuro p
    WHERE CAST(p.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_ton_dia,
        l.cu_g_l
    FROM flujo_f48 f
    INNER JOIN ley_f48 l
        ON f.fecha = l.fecha
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F48',
    COALESCE(SUM(flujo_ton_dia), 0),

    COALESCE(
        SUM(
            CASE
                WHEN cu_g_l IS NOT NULL
                THEN flujo_ton_dia * cu_g_l
            END
        )
        /
        NULLIF(
            SUM(
                CASE
                    WHEN cu_g_l IS NOT NULL
                    THEN flujo_ton_dia
                END
            ),
            0
        ),
        0
    ) / 10.0
FROM base;
    
    END;

    -- ETAPA 39; lee resultados M6: F48, F66, F67, F72
    IF @etapa=39
    BEGIN



/* ================================================================
   F47 - PLS SULFUROS HACIA SX
   ----------------------------------------------------------------
   Balance:

       F72 + F66 = F47 + F48 + F67

   Despejando:

       F47 = F72 + F66 - F67 - F48

   F67 representa explicitamente la perdida por evaporacion.

   IMPORTANTE:
       - Se elimina el antiguo factor F72 * 0.95.
       - La fuente de Ley Cu de F47 se mantiene sin cambios.
================================================================ */

;WITH F72 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F72'
),

F48 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F48'
),

F67 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F67'
),
F66 AS
(
    SELECT
        COALESCE(
            TRY_CONVERT(float,Tonelaje),
            0
        ) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F66'
),

Ley_F47 AS
(
    SELECT
        COALESCE(
            AVG(c.sulfuros_pls_a_sx_cu),
            0
        ) / 10.0 AS Ley_Cu

    FROM inventar_SpcHidr.conc_cu AS c

    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F47',

      F72.Tonelaje
    + F66.Tonelaje
    - F67.Tonelaje
    - F48.Tonelaje,

    COALESCE(l.Ley_Cu,0)

FROM F72
CROSS JOIN F66
CROSS JOIN F48
CROSS JOIN F67
CROSS JOIN Ley_F47 AS l;
    
    END;

    -- ETAPA 40; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=40
    BEGIN




-- F74 - Refino hacia DUMP
-- Nueva fuente diaria:
--   balance_dump_leach_flujos.flujo_refino_dump_m3h
-- Concentración:
--   conc_cu.oxidos_refino_cu

;WITH flujo_diario AS (
    SELECT
        CAST(t.fecha_registro AS date) AS fecha,
        COALESCE(t.flujo_refino_dump_m3h, 0) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.balance_dump_leach_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
cu_diario AS (
    SELECT
        CAST(c.fecha_registro AS date) AS fecha,
        COALESCE(c.oxidos_refino_cu, 0) AS cu_g_l
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
base AS (
    SELECT
        f.flujo_m3_dia,
        c.cu_g_l
    FROM flujo_diario f
    INNER JOIN cu_diario c
        ON f.fecha = c.fecha
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F74',
    COALESCE(SUM(flujo_m3_dia), 0),
    COALESCE(
        SUM(flujo_m3_dia * cu_g_l)
        / NULLIF(SUM(flujo_m3_dia), 0),
        0
    ) / 10.0
FROM base;
    
    END;

    -- ETAPA 41; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=41
    BEGIN



    -- F50
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F50',0,0);
    
    END;

    -- ETAPA 42; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=42
    BEGIN



    -- F117
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
      'F117',
      COALESCE(Tonelaje,0) * 0.07,
      0.0
    FROM #tmp_f35_oficial;
    
    END;

    -- ETAPA 43; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=43
    BEGIN




    -- F90
    -- Agua hacia Refino Sulfuros
    --
    -- Fuente anterior:
    --   tags_sx_ew.agua_refino_sulf_m3h
    --   Granularidad: horaria
    --
    -- Fuente nueva:
    --   insumos_area_humeda_flujos.agua_refino_sulfuros_flujo_m3h
    --   Granularidad: diaria
    --
    -- Integracion temporal:
    --   m3/h * 24 h/dia = m3/dia

;WITH base_f90 AS (
    SELECT
        COALESCE(t.agua_refino_sulfuros_flujo_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F90',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f90;
    
    END;

    -- ETAPA 44; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=44
    BEGIN




    -- F76_SULF
    ;WITH volumen_inicial AS (
        SELECT TOP 1 COALESCE(i.volumen_ref_sulfuros, 0) * 1.0 AS TMS_Inicial
        FROM inventar_SpcHidr.inv_sol_sulfuros i
        WHERE CAST(i.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
        ORDER BY CAST(i.fecha_registro AS date) ASC
    ),
volumen_final AS
(
    SELECT TOP 1
        COALESCE(i.volumen_ref_sulfuros, 0) AS TMS_Final

    FROM inventar_SpcHidr.inv_sol_sulfuros i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

    ORDER BY i.fecha_registro DESC
),
    ley_inicial AS (
        SELECT TOP 1 COALESCE(c.sulfuros_refino_cu, 0) AS Ley_i_gL
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
        ORDER BY CAST(c.fecha_registro AS date) ASC
    ),
ley_final AS
(
    SELECT TOP 1
        COALESCE(c.sulfuros_refino_cu, 0) AS Ley_f_gL

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

    ORDER BY c.fecha_registro DESC
)
    INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
    SELECT
        'F76_SULF',
        vi.TMS_Inicial,
        li.Ley_i_gL / 10.0,
        vf.TMS_Final,
        lf.Ley_f_gL / 10.0,
        (vf.TMS_Final - vi.TMS_Inicial),
        COALESCE((((vf.TMS_Final * lf.Ley_f_gL) - (vi.TMS_Inicial * li.Ley_i_gL)) / NULLIF((vf.TMS_Final - vi.TMS_Inicial),0)) / 10.0, 0)
    FROM volumen_inicial vi
    CROSS JOIN volumen_final vf
    CROSS JOIN ley_inicial li
    CROSS JOIN ley_final lf;
    
    END;

    -- ETAPA 45; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=45
    BEGIN



    -- F75_SULF (evaporacion Refino Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F61' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F75_SULF', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 46; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=46
    BEGIN




    -- F87 (evaporacion ILS Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F62' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F87', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 47; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=47
    BEGIN



    -- F82
-- Inventario de solución ILS Sulfuros
--
-- Volumen:
--   inv_sol_sulfuros.volumen_ils_sulfuros
--
-- Concentración:
--   conc_cu.sulfuros_ils_a_piscina_cu
--
-- Inventario diario: no requiere integración temporal.

;WITH volumen_inicial AS (
    SELECT TOP 1
        COALESCE(i.volumen_ils_sulfuros, 0) AS TMS_Inicial
    FROM inventar_SpcHidr.inv_sol_sulfuros i
    WHERE CAST(i.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    ORDER BY i.fecha_registro ASC
),
volumen_final AS
(
    SELECT TOP 1
        COALESCE(i.volumen_ils_sulfuros, 0) AS TMS_Final

    FROM inventar_SpcHidr.inv_sol_sulfuros i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

    ORDER BY i.fecha_registro DESC
),
ley_inicial AS (
    SELECT TOP 1
        COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_i_gL
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    ORDER BY c.fecha_registro ASC
),
ley_final AS
(
    SELECT TOP 1
        COALESCE(c.sulfuros_ils_a_piscina_cu, 0) AS Ley_f_gL

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

    ORDER BY c.fecha_registro DESC
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F82',

    vi.TMS_Inicial,
    li.Ley_i_gL / 10.0,

    vf.TMS_Final,
    lf.Ley_f_gL / 10.0,

    vf.TMS_Final - vi.TMS_Inicial,

    COALESCE(
        (
            (vf.TMS_Final * lf.Ley_f_gL)
          - (vi.TMS_Inicial * li.Ley_i_gL)
        )
        /
        NULLIF(
            vf.TMS_Final - vi.TMS_Inicial,
            0
        )
        / 10.0,
        0
    )

FROM volumen_inicial vi
CROSS JOIN volumen_final vf
CROSS JOIN ley_inicial li
CROSS JOIN ley_final lf;
    
    END;

    -- ETAPA 48; lee resultados M6: F66, F82, F87
    IF @etapa=48
    BEGIN



/* ================================================================
   F49 - SOLUCION PLS SULFUROS -> ILS SULFUROS
   ----------------------------------------------------------------
   Balance piscina ILS Sulfuros:

       F49 = F66 + F87 + F82

   F66 = salida ILS hacia riego
   F87 = evaporacion
   F82 = delta inventario ILS

   Cobre:
       CuF51 = CuF45 + CuF63
       F87 no transporta Cu
================================================================ */

;WITH F66 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F66'
),
F87 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F87'
),
F82 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F82'
),
Calculo AS
(
    SELECT
          F66.Tonelaje
        + F87.Tonelaje
        + F82.Tonelaje AS Tonelaje_F49,

        (
            F66.Tonelaje * F66.Ley_Cu / 100.0
        )
        +
        (
            F82.Tonelaje * F82.Ley_Cu / 100.0
        ) AS FCu_F49

    FROM F66
    CROSS JOIN F87
    CROSS JOIN F82
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F49',

    Tonelaje_F49,

    CASE
        WHEN Tonelaje_F49 = 0 THEN 0
        ELSE FCu_F49 / NULLIF(Tonelaje_F49,0) * 100.0
    END

FROM Calculo;
    
    END;

    -- ETAPA 49; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=49
    BEGIN



    -- F64 (evaporacion PLS Sulfuros: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F64' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F64', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 50; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=50
    BEGIN



/* ================================================================
   F65 - VARIACION INVENTARIO PLS SULFUROS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1 = @fecha_fin + 1 dia

   Volumen:
       inv_sol_sulfuros.volumen_pls_sulfuros

   Concentracion:
       conc_cu.sulfuros_pls_a_sx_cu
================================================================ */

;WITH base_f65 AS
(
    SELECT

        /* Inventario inicial */
        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_sulfuros)

            FROM inventar_SpcHidr.inv_sol_sulfuros AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        /* Inventario final D+1 */
        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_sulfuros)

            FROM inventar_SpcHidr.inv_sol_sulfuros AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        /* Ley inicial */
        (
            SELECT TOP 1
                TRY_CONVERT(float, c.sulfuros_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        /* Ley final D+1 */
        (
            SELECT TOP 1
                TRY_CONVERT(float, c.sulfuros_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F65',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f65;
    
    END;

    -- ETAPA 51; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=51
    BEGIN



-- F46
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F46',0,0);
    
    END;

    -- ETAPA 52; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=52
    BEGIN



-- F116
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F116',
    COALESCE(Tonelaje,0) * 0.07,
    0.0
FROM #tmp_f32_oficial;
    
    END;

    -- ETAPA 53; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=53
    BEGIN




/* ================================================================
   F56 - VARIACION INVENTARIO POND DPLS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_pond_dpls

   Concentracion:
       conc_cu.dump_dpls_cu
================================================================ */

;WITH base_f56 AS
(
    SELECT

        /* Inventario inicial */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, i.volumen_pond_dpls)
                )

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio
        ) AS TMS_Inicial,


        /* Inventario final D+1 */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, i.volumen_pond_dpls)
                )

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1
        ) AS TMS_Final,


        /* Ley inicial */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, c.dump_dpls_cu)
                )

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio
        ) AS Ley_i_gL,


        /* Ley final D+1 */
        (
            SELECT
                AVG(
                    TRY_CONVERT(float, c.dump_dpls_cu)
                )

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F56',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (
                    TMS_Final
                    * Ley_f_gL / 10.0
                )
                -
                (
                    TMS_Inicial
                    * Ley_i_gL / 10.0
                )
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
    END

FROM base_f56;
    
    END;

    -- ETAPA 54; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=54
    BEGIN



-- F55 (evaporacion Pond DPLS*: perdida_estimada_m3_dia x dias del periodo)
;WITH ev AS (
    SELECT perdida_estimada_m3_dia
    FROM inventar_SpcHidr.tasa_evaporacion
    WHERE codigo_flujo = 'F71' /* clave histórica de la tabla fuente */
)
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F55',
    COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo,
    0.0
FROM ev;
    
    END;

    -- ETAPA 55; lee resultados M6: F51, F55, F56, F81
    IF @etapa=55
    BEGIN



/* ================================================================
   F54 - DPLS HACIA PLS OX
   ----------------------------------------------------------------
   Balance de masa nodo DPLS:

       F51 = F56 + F54 + F55 + F81

   Despejando:

       F54 = F51 - F56 - F55 - F81

   Donde:
       F51 = ingreso desde PAD DUMP
       F56 = variacion inventario DPLS
       F55 = perdida por evaporacion
       F81 = salida hacia PAD Ox
       F54 = salida hacia PLS Ox

   Balance de cobre:

       CuF37 = CuF69 + CuF53 + CuF71 + CuF46

   Como F55 corresponde a evaporacion:
       CuF71 = 0

   Entonces:

       CuF53 = CuF37 - CuF69 - CuF46

   IMPORTANTE:
       - Se elimina el antiguo factor fijo 0.95.
       - La evaporacion queda representada explicitamente por F55.
       - No se fuerza F54 >= 0.
================================================================ */

;WITH F51 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F51'
),

F81 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F81'
),

F56 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F56'
),

F55 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float, Tonelaje), 0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float, Ley_Cu), 0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F55'
),

Calculo AS
(
    SELECT

        /* ========================================================
           MASA
           ======================================================== */
          F51.Tonelaje
        - F56.Tonelaje
        - F55.Tonelaje
        - F81.Tonelaje
            AS Tonelaje_F54,


        /* ========================================================
           COBRE FINO
           ======================================================== */
        (
            F51.Tonelaje
            * F51.Ley_Cu
            / 100.0
        )
        -
        (
            F56.Tonelaje
            * F56.Ley_Cu
            / 100.0
        )
        -
        (
            F81.Tonelaje
            * F81.Ley_Cu
            / 100.0
        )
            AS FCu_F54

    FROM F51
    CROSS JOIN F81
    CROSS JOIN F56
    CROSS JOIN F55
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F54',

    Tonelaje_F54,

    CASE
        WHEN Tonelaje_F54 = 0
         AND FCu_F54 = 0
            THEN 0

        WHEN Tonelaje_F54 = 0
            THEN NULL

        ELSE
            FCu_F54
            / NULLIF(Tonelaje_F54, 0)
            * 100.0
    END

FROM Calculo;
    
    END;

    -- ETAPA 56; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=56
    BEGIN



-- F79
;WITH inv_i AS (
    SELECT
        COALESCE(AVG(i.volumen_refino_dump), 0) AS inventario_inicial
    FROM inventar_SpcHidr.inv_sol_oxidos i
    WHERE CAST(i.fecha_registro AS date) = @fecha_inicio
),
inv_f AS
(
    SELECT
        COALESCE(AVG(i.volumen_refino_dump), 0)
        AS inventario_final

    FROM inventar_SpcHidr.inv_sol_oxidos i

    WHERE CAST(i.fecha_registro AS date) = @ff_mas_1
),
ley_i AS (
    SELECT
        COALESCE(AVG(c.dump_feed_cu), 0) AS ley_inicial
    FROM inventar_SpcHidr.conc_cu c
    WHERE CAST(c.fecha_registro AS date) = @fecha_inicio
),
ley_f AS
(
    SELECT
        COALESCE(AVG(c.dump_feed_cu), 0)
        AS ley_final

    FROM inventar_SpcHidr.conc_cu c

    WHERE CAST(c.fecha_registro AS date) = @ff_mas_1
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial, Ley_Cu_1,
    TMS_Final,   Ley_Cu_2,
    Tonelaje,    Ley_Cu
)
SELECT
    'F79',
    COALESCE(inv_i.inventario_inicial, 0),
    COALESCE(ley_i.ley_inicial, 0) / 10.0,
    COALESCE(inv_f.inventario_final, 0),
    COALESCE(ley_f.ley_final, 0) / 10.0,
    COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0),
    CASE
        WHEN (COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0)) = 0 THEN 0
        ELSE (
            (
                COALESCE(inv_f.inventario_final, 0) * (COALESCE(ley_f.ley_final, 0) / 10.0)
            ) -
            (
                COALESCE(inv_i.inventario_inicial, 0) * (COALESCE(ley_i.ley_inicial, 0) / 10.0)
            )
        ) / NULLIF(
            COALESCE(inv_f.inventario_final, 0) - COALESCE(inv_i.inventario_inicial, 0),
            0
        )
    END
FROM inv_i
CROSS JOIN inv_f
CROSS JOIN ley_i
CROSS JOIN ley_f;
    
    END;

    -- ETAPA 57; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=57
    BEGIN




-- F78 (evaporacion Refino Dump: perdida_estimada_m3_dia x dias del periodo)
;WITH ev AS (
    SELECT perdida_estimada_m3_dia
    FROM inventar_SpcHidr.tasa_evaporacion
    WHERE codigo_flujo = 'F72' /* clave histórica de la tabla fuente */
)
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F78',
    COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo,
    0.0
FROM ev;
    
    END;

    -- ETAPA 58; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=58
    BEGIN



/* ================================================================
   F76_OX - VARIACION INVENTARIO REFINO OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_refino_oxidos

   Concentracion:
       conc_cu.oxidos_refino_cu

   Se mantiene la metodologia vigente de Ley_Cu:
       promedio de concentracion inicial y final
================================================================ */

;WITH base_f76_ox AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F76_OX',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                Ley_i_gL + Ley_f_gL
            )
            / 2.0
            / 10.0
    END

FROM base_f76_ox;
    
    END;

    -- ETAPA 59; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=59
    BEGIN




  -- F75_OX (evaporacion Refino Oxidos: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F74' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F75_OX', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 60; lee resultados M6: F70_ADICIONAL, F72, F75_SULF, F76_SULF, F90
    IF @etapa=60
    BEGIN



-- F69_SULF = F70_ADICIONAL + F72 + F76_SULF + F75_SULF - F90
-- Se utilizan subconsultas escalares para que F69_SULF se inserte
-- aunque alguno de los flujos anteriores no tenga registro.
INSERT INTO #valores_m6 (
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F69_SULF',

    COALESCE(
        (
            SELECT Tonelaje
            FROM #valores_m6
            WHERE codigo_flujo = 'F70_ADICIONAL'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #valores_m6
            WHERE codigo_flujo = 'F72'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #valores_m6
            WHERE codigo_flujo = 'F76_SULF'
        ),
        0
    )
    +
    COALESCE(
        (
            SELECT Tonelaje
            FROM #valores_m6
            WHERE codigo_flujo = 'F75_SULF'
        ),
        0
    )
    -
    COALESCE(
        (
            SELECT Tonelaje
            FROM #valores_m6
            WHERE codigo_flujo = 'F90'
        ),
        0
    ),

    COALESCE(
        (
            SELECT Ley_Cu
            FROM #valores_m6
            WHERE codigo_flujo = 'F72'
        ),
        0
    );
    
    END;

    -- ETAPA 61; lee resultados M6: F70_PRINCIPAL, F71, F73, F74, F75_OX, F76_OX
    IF @etapa=61
    BEGIN



		
-- F69_OX
;WITH f70_principal AS (
        SELECT Tonelaje, Ley_Cu
        FROM #valores_m6
        WHERE codigo_flujo = 'F70_PRINCIPAL'
     ),
     f71 AS (
        SELECT Tonelaje
        FROM #valores_m6
        WHERE codigo_flujo = 'F71'
     ),
     f73 AS (
        SELECT Tonelaje
        FROM #valores_m6
        WHERE codigo_flujo = 'F73'
     ),
     f74 AS (
        SELECT Tonelaje
        FROM #valores_m6
        WHERE codigo_flujo = 'F74'
     ),
     f76_ox AS (
        SELECT Tonelaje
        FROM #valores_m6
        WHERE codigo_flujo = 'F76_OX'
     ),
		  f75_ox AS (
        SELECT Tonelaje
        FROM #valores_m6
        WHERE codigo_flujo = 'F75_OX'
     )
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F69_OX',
    (COALESCE(f70_principal.Tonelaje,0)
   + COALESCE(f71.Tonelaje,0)
   + COALESCE(f73.Tonelaje,0)
   + COALESCE(f74.Tonelaje,0)
   + COALESCE(f76_ox.Tonelaje,0)
   + COALESCE(f75_ox.Tonelaje,0)),
    COALESCE(f70_principal.Ley_Cu,0)
FROM f70_principal
CROSS JOIN f71
CROSS JOIN f73
CROSS JOIN f74
CROSS JOIN f76_ox
CROSS JOIN f75_ox;
    
    END;

    -- ETAPA 62; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=62
    BEGIN



  
    -- F62 (evaporacion ILS Oxido: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F75' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F62', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 63; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=63
    BEGIN



/* ================================================================
   F61 - VARIACION INVENTARIO ILS OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_ils_oxido

   Concentracion:
       conc_cu.oxidos_ils_a_piscina_cu
================================================================ */

;WITH base_f61 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_ils_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_ils_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_ils_a_piscina_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F61',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f61;
    
    END;

    -- ETAPA 64; lee resultados M6: F60, F61, F62
    IF @etapa=64
    BEGIN



/* ================================================================
   F45 - SOLUCION PLS OXIDOS -> ILS OXIDOS

       F45 = F60 + F62 + F61
================================================================ */

;WITH F60 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F60'
),
F62 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F62'
),
F61 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0) AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F61'
),
Calculo AS
(
    SELECT
          F60.Tonelaje
        + F62.Tonelaje
        + F61.Tonelaje AS Tonelaje_F45,

        (
            F60.Tonelaje * F60.Ley_Cu / 100.0
        )
        +
        (
            F61.Tonelaje * F61.Ley_Cu / 100.0
        ) AS FCu_F45

    FROM F60
    CROSS JOIN F62
    CROSS JOIN F61
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F45',

    Tonelaje_F45,

    CASE
        WHEN Tonelaje_F45 = 0 THEN 0
        ELSE FCu_F45 / NULLIF(Tonelaje_F45,0) * 100.0
    END

FROM Calculo;
    
    END;

    -- ETAPA 65; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=65
    BEGIN



    -- F59 (evaporacion PLS Oxido: perdida_estimada_m3_dia x dias del periodo)
    ;WITH ev AS (
        SELECT perdida_estimada_m3_dia
        FROM inventar_SpcHidr.tasa_evaporacion
        WHERE codigo_flujo = 'F77' /* clave histórica de la tabla fuente */
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F59', COALESCE(ev.perdida_estimada_m3_dia, 0) * @dias_periodo, 0.0
    FROM ev;
    
    END;

    -- ETAPA 66; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=66
    BEGIN



/* ================================================================
   F58 - VARIACION INVENTARIO PLS OXIDOS
   ----------------------------------------------------------------
   Apertura:
       @fecha_inicio

   Cierre:
       @ff_mas_1

   Volumen:
       inv_sol_oxidos.volumen_pls_oxido

   Concentracion:
       conc_cu.oxidos_pls_a_sx_cu
================================================================ */

;WITH base_f58 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_pls_oxido)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_pls_a_sx_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F58',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                (TMS_Final   * Ley_f_gL)
              - (TMS_Inicial * Ley_i_gL)
            )
            /
            NULLIF(
                TMS_Final - TMS_Inicial,
                0
            )
            / 10.0
    END

FROM base_f58;
    
    END;

    -- ETAPA 67; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=67
    BEGIN



    -- F57_A-F57_D
    ;WITH masico_f57_a AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_a_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f57_a AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F57_A', m.Tonelaje, l.Ley_Cu
    FROM masico_f57_a m
    CROSS JOIN ley_f57_a l;
    
    END;

    -- ETAPA 68; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=68
    BEGIN



    ;WITH masico_f57_b AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_b_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f57_b AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F57_B', m.Tonelaje, l.Ley_Cu
    FROM masico_f57_b m
    CROSS JOIN ley_f57_b l;
    
    END;

    -- ETAPA 69; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=69
    BEGIN



    ;WITH masico_f57_c AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_c_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f57_c AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F57_C', m.Tonelaje, l.Ley_Cu
    FROM masico_f57_c m
    CROSS JOIN ley_f57_c l;
    
    END;

    -- ETAPA 70; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=70
    BEGIN



    ;WITH masico_f57_d AS (
        SELECT COALESCE(SUM(s.pls_oxido_sx_tren_d_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f57_d AS (
        SELECT COALESCE(AVG(c.oxidos_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F57_D', m.Tonelaje, l.Ley_Cu
    FROM masico_f57_d m
    CROSS JOIN ley_f57_d l;
    
    END;

    -- ETAPA 71; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=71
    BEGIN



    -- F63_A-F63_D
    ;WITH masico_f63_a AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_a_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f63_a AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F63_A', m.Tonelaje, l.Ley_Cu
    FROM masico_f63_a m
    CROSS JOIN ley_f63_a l;
    
    END;

    -- ETAPA 72; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=72
    BEGIN



    ;WITH masico_f63_b AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_b_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f63_b AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F63_B', m.Tonelaje, l.Ley_Cu
    FROM masico_f63_b m
    CROSS JOIN ley_f63_b l;
    
    END;

    -- ETAPA 73; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=73
    BEGIN



    ;WITH masico_f63_c AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_c_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f63_c AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F63_C', m.Tonelaje, l.Ley_Cu
    FROM masico_f63_c m
    CROSS JOIN ley_f63_c l;
    
    END;

    -- ETAPA 74; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=74
    BEGIN



    ;WITH masico_f63_d AS (
        SELECT COALESCE(SUM(s.pls_sulfuro_sx_tren_d_m3_h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_pls_ep s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f63_d AS (
        SELECT COALESCE(AVG(c.sulfuros_pls_a_sx_cu), 0) / 10.0 AS Ley_Cu
        FROM inventar_SpcHidr.conc_cu c
        WHERE CAST(c.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F63_D', m.Tonelaje, l.Ley_Cu
    FROM masico_f63_d m
    CROSS JOIN ley_f63_d l;
    
    END;

    -- ETAPA 75; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=75
    BEGIN



    -- AUX_EVAP_SX
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('AUX_EVAP_SX',0,0);
    
    END;

    -- ETAPA 76; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=76
    BEGIN



    -- F94_A-F94_D
-- H2SO4 hacia SX Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.acido_sx_tren_*_m3h
--   Granularidad: horaria
--   Unidad: m3/h
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.acido_sx_tren_*_l_min
--   Granularidad: diaria
--   Unidad: L/min
--
-- Conversion:
--   L/min * 60 min/h * 24 h/dia / 1000 L/m3 * 1.84 t/m3
--   = t H2SO4/dia


-- F94_A - H2SO4 Tren A
;WITH base_f94_a AS (
    SELECT
        COALESCE(t.acido_sx_tren_a_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F94_A',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f94_a;
    
    END;

    -- ETAPA 77; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=77
    BEGIN





-- F94_B - H2SO4 Tren B
;WITH base_f94_b AS (
    SELECT
        COALESCE(t.acido_sx_tren_b_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F94_B',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f94_b;
    
    END;

    -- ETAPA 78; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=78
    BEGIN





-- F94_C - H2SO4 Tren C
;WITH base_f94_c AS (
    SELECT
        COALESCE(t.acido_sx_tren_c_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F94_C',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f94_c;
    
    END;

    -- ETAPA 79; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=79
    BEGIN





-- F94_D - H2SO4 Tren D
;WITH base_f94_d AS (
    SELECT
        COALESCE(t.acido_sx_tren_d_l_min, 0)
        * 60.0
        * 24.0
        / 1000.0
        * 1.84 AS ton_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F94_D',
    COALESCE(SUM(ton_dia), 0),
    0.0
FROM base_f94_d;
    
    END;

    -- ETAPA 80; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=80
    BEGIN



-- F92_A-F92_D
-- Agua W2 hacia SX - Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.agua_sx_tren_*_m3h
--   Granularidad: horaria
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.agua_w2_tren_*_m3h
--   Granularidad: diaria
--
-- Integracion temporal:
--   m3/h * 24 h/dia = m3/dia


-- F92_A - Agua W2 Tren A
;WITH base_f92_a AS (
    SELECT
        COALESCE(t.agua_w2_tren_a_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F92_A',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f92_a;
    
    END;

    -- ETAPA 81; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=81
    BEGIN





-- F92_B - Agua W2 Tren B
;WITH base_f92_b AS (
    SELECT
        COALESCE(t.agua_w2_tren_b_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F92_B',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f92_b;
    
    END;

    -- ETAPA 82; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=82
    BEGIN





-- F92_C - Agua W2 Tren C
;WITH base_f92_c AS (
    SELECT
        COALESCE(t.agua_w2_tren_c_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F92_C',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f92_c;
    
    END;

    -- ETAPA 83; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=83
    BEGIN





-- F92_D - Agua W2 Tren D
;WITH base_f92_d AS (
    SELECT
        COALESCE(t.agua_w2_tren_d_m3h, 0)
        * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F92_D',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_f92_d;
    
    END;

    -- ETAPA 84; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=84
    BEGIN



    -- F99_A-F99_D
;WITH masico_f99_a AS (
    SELECT
        COALESCE(SUM(s.ep_tren_a_m3h), 0) * 24.0 AS Tonelaje
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
),
ley_f99_a AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F99_A',
    m.Tonelaje,
    l.Ley_Cu
FROM masico_f99_a m
CROSS JOIN ley_f99_a l;
    
    END;

    -- ETAPA 85; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=85
    BEGIN




    ;WITH masico_f99_b AS (
        SELECT COALESCE(SUM(s.ep_tren_b_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f99_b AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F99_B', m.Tonelaje, l.Ley_Cu
    FROM masico_f99_b m
    CROSS JOIN ley_f99_b l;
    
    END;

    -- ETAPA 86; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=86
    BEGIN



    ;WITH masico_f99_c AS (
        SELECT COALESCE(SUM(s.ep_tren_c_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f99_c AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F99_C', m.Tonelaje, l.Ley_Cu
    FROM masico_f99_c m
    CROSS JOIN ley_f99_c l;
    
    END;

    -- ETAPA 87; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=87
    BEGIN



    ;WITH masico_f99_d AS (
        SELECT COALESCE(SUM(s.ep_tren_d_m3h), 0) * 24.0 AS Tonelaje
        FROM inventar_SpcHidr.sx_ep_flujos_niveles s
        WHERE CAST(s.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    ),
    ley_f99_d AS (
    SELECT
        COALESCE(
            AVG(
                (
                    COALESCE(s.ep_ecc1_gl, 0) +
                    COALESCE(s.ep_ecc2_gl, 0) +
                    COALESCE(s.ep_ecc3_gl, 0)
                ) / 3.0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE CAST(s.fecha_registro AS date)
          BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F99_D', m.Tonelaje, l.Ley_Cu
    FROM masico_f99_d m
    CROSS JOIN ley_f99_d l;
    
    END;

    -- ETAPA 88; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=88
    BEGIN



-- F100
-- Electrolito Rico hacia EW
--
-- Fuente única nueva:
--   sx_ep_flujos_niveles
--
-- Caudales:
--   er_ecc1_m3h
--   er_ecc2_m3h
--   er_ecc3_m3h
--
-- Concentraciones:
--   er_ecc1_gl
--   er_ecc2_gl
--   er_ecc3_gl
--
-- Granularidad:
--   diaria
--
-- Integracion:
--   m3/h * 24 h/dia = m3/dia

;WITH base_f100 AS (
    SELECT
        CAST(s.fecha_registro AS date) AS fecha,

        (
            COALESCE(s.er_ecc1_m3h, 0)
          + COALESCE(s.er_ecc2_m3h, 0)
          + COALESCE(s.er_ecc3_m3h, 0)
        ) * 24.0 AS volumen_m3_dia,

        COALESCE(s.er_ecc1_m3h, 0) AS q1,
        COALESCE(s.er_ecc2_m3h, 0) AS q2,
        COALESCE(s.er_ecc3_m3h, 0) AS q3,

        NULLIF(s.er_ecc1_gl, 0) AS c1,
        NULLIF(s.er_ecc2_gl, 0) AS c2,
        NULLIF(s.er_ecc3_gl, 0) AS c3

    FROM inventar_SpcHidr.sx_ep_flujos_niveles s

    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F100',

    COALESCE(
        SUM(volumen_m3_dia),
        0
    ) AS Tonelaje,

    COALESCE(
        SUM(
            CASE WHEN c1 IS NOT NULL THEN q1 * c1 ELSE 0 END
          + CASE WHEN c2 IS NOT NULL THEN q2 * c2 ELSE 0 END
          + CASE WHEN c3 IS NOT NULL THEN q3 * c3 ELSE 0 END
        )
        /
        NULLIF(
            SUM(
                CASE WHEN c1 IS NOT NULL THEN q1 ELSE 0 END
              + CASE WHEN c2 IS NOT NULL THEN q2 ELSE 0 END
              + CASE WHEN c3 IS NOT NULL THEN q3 ELSE 0 END
            ),
            0
        ),
        0
    ) / 10.0 AS Ley_Cu

FROM base_f100;
    
    END;

    -- ETAPA 89; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=89
    BEGIN



-- F98
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F98', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 90; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=90
    BEGIN



--F101_A
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F101_A', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 91; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=91
    BEGIN



--F101_B
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F101_B', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 92; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=92
    BEGIN



-- F113
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES
   ('F113',0,0);
    
    END;

    -- ETAPA 93; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=93
    BEGIN



-- F104
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F104', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 94; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=94
    BEGIN



--F108
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES
   ('F108',0,0);
    
    END;

    -- ETAPA 95; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=95
    BEGIN



/* ================================================================
   F107 - VARIACION DE INVENTARIO DE COBRE COLGADO
   ----------------------------------------------------------------
   Fuente:
       inventar_SpcHidr.inventario_cobre_colgado_diario

   Campo:
       inventario_total_ton

   Metodologia:

       Inventario inicial = estado en @fecha_inicio

       Inventario final   = estado en @fecha_fin + 1 día

       F107 =
           Inventario(@fecha_fin + 1)
         - Inventario(@fecha_inicio)

   Ejemplo:
       Periodo balanceado: 01-08-2026 al 16-08-2026

       Inventario inicial: 01-08-2026
       Inventario final  : 17-08-2026

   Unidad:
       toneladas de Cu

   Ley:
       100 %

   IMPORTANTE:
       - Se utiliza @ff_mas_1, ya declarado como:
             DATEADD(DAY, 1, @fecha_fin)

       - inventario_total_ton es el inventario calculado
         por el sistema.

       - excel_total_ton se mantiene solamente como referencia.

       - No requiere integración temporal ni factor x24.
================================================================ */

;WITH base_f107 AS
(
    SELECT

        /* ========================================================
           INVENTARIO INICIAL
           Fecha = @fecha_inicio
           ======================================================== */
        (
            SELECT TOP 1
                TRY_CONVERT(
                    decimal(18,6),
                    p.inventario_total_ton
                )

            FROM inventar_SpcHidr.inventario_cobre_colgado_diario AS p

            WHERE p.fecha_operacional = @fecha_inicio

            ORDER BY
                COALESCE(
                    p.updated_at,
                    p.imported_at
                ) DESC,
                p.id_registro DESC

        ) AS Inventario_Inicial,


        /* ========================================================
           INVENTARIO FINAL
           Fecha = @fecha_fin + 1 día
           ======================================================== */
        (
            SELECT TOP 1
                TRY_CONVERT(
                    decimal(18,6),
                    p.inventario_total_ton
                )

            FROM inventar_SpcHidr.inventario_cobre_colgado_diario AS p

            WHERE p.fecha_operacional = @ff_mas_1

            ORDER BY
                COALESCE(
                    p.updated_at,
                    p.imported_at
                ) DESC,
                p.id_registro DESC

        ) AS Inventario_Final
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F107',

    Inventario_Inicial,
    100.0,

    Inventario_Final,
    100.0,

    CASE
        WHEN Inventario_Inicial IS NULL
          OR Inventario_Final IS NULL
            THEN NULL

        ELSE
            Inventario_Final
            - Inventario_Inicial
    END AS Tonelaje,

    100.0

FROM base_f107;
    
    END;

    -- ETAPA 96; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=96
    BEGIN



    -- F105
    ;WITH base_f105 AS (
        SELECT COALESCE(p.real_produccion_ton,0) AS ton
        FROM inventar_SpcHidr.produccion_catodica p
        WHERE CAST(p.fecha_registro AS date) BETWEEN @fecha_inicio AND @fecha_fin
    )
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F105', COALESCE(SUM(ton),0), 100.0
    FROM base_f105;
    
    END;

    -- ETAPA 97; lee resultados M6: F105, F107
    IF @etapa=97
    BEGIN



    -- F103
    ;WITH f107 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F107'),
          f105 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F105')
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT 'F103', COALESCE(f107.Tonelaje,0) + COALESCE(f105.Tonelaje,0), 100.0
    FROM f107 CROSS JOIN f105;
    
    END;

    -- ETAPA 98; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=98
    BEGIN




--F118
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F118', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 99; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=99
    BEGIN



--F119
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F119', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 100; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=100
    BEGIN



--F120
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F120', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 101; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=101
    BEGIN



--F121
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F121', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 102; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=102
    BEGIN



--F111
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES
('F111',0,0);
    
    END;

    -- ETAPA 103; lee resultados M6: F105, F111, F118, F119, F120, F121
    IF @etapa=103
    BEGIN



-- F112
    ;WITH f105 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F105'),
         f118 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F118'),
         f119 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F119'),
         f120 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F120'),
         f121 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F121'),
         f111 AS (SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo='F111')
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    SELECT
        'F112',
        COALESCE(f105.Tonelaje,0) - COALESCE(f118.Tonelaje,0) - COALESCE(f119.Tonelaje,0) - COALESCE(f120.Tonelaje,0) - COALESCE(f121.Tonelaje,0) - COALESCE(f111.Tonelaje,0),
        100.0
    FROM f105 CROSS JOIN f118 CROSS JOIN f119 CROSS JOIN f120 CROSS JOIN f121 CROSS JOIN f111;
    
    END;

    -- ETAPA 104; lee resultados M6: F100
    IF @etapa=104
    BEGIN



-- F102
-- Electrolito Pobre / retorno desde EW
--
-- Volumen:
--   igual al volumen integrado de F100
--
-- Fuente de ponderadores y concentraciones:
--   sx_ep_flujos_niveles
--
-- Ponderadores:
--   er_ecc1_m3h
--   er_ecc2_m3h
--   er_ecc3_m3h
--
-- Concentraciones EP:
--   ep_ecc1_gl
--   ep_ecc2_gl
--   ep_ecc3_gl

;WITH f100 AS (
    SELECT
        COALESCE(MAX(Tonelaje), 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F100'
),
base_f102 AS (
    SELECT
        COALESCE(s.er_ecc1_m3h, 0) AS q1,
        COALESCE(s.er_ecc2_m3h, 0) AS q2,
        COALESCE(s.er_ecc3_m3h, 0) AS q3,

        NULLIF(s.ep_ecc1_gl, 0) AS c1,
        NULLIF(s.ep_ecc2_gl, 0) AS c2,
        NULLIF(s.ep_ecc3_gl, 0) AS c3

    FROM inventar_SpcHidr.sx_ep_flujos_niveles s

    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
),
ley_f102 AS (
    SELECT
        COALESCE(
            SUM(
                CASE
                    WHEN c1 IS NOT NULL AND q1 <> 0
                    THEN q1 * c1
                    ELSE 0
                END
              +
                CASE
                    WHEN c2 IS NOT NULL AND q2 <> 0
                    THEN q2 * c2
                    ELSE 0
                END
              +
                CASE
                    WHEN c3 IS NOT NULL AND q3 <> 0
                    THEN q3 * c3
                    ELSE 0
                END
            )
            /
            NULLIF(
                SUM(
                    CASE
                        WHEN c1 IS NOT NULL AND q1 <> 0
                        THEN q1
                        ELSE 0
                    END
                  +
                    CASE
                        WHEN c2 IS NOT NULL AND q2 <> 0
                        THEN q2
                        ELSE 0
                    END
                  +
                    CASE
                        WHEN c3 IS NOT NULL AND q3 <> 0
                        THEN q3
                        ELSE 0
                    END
                ),
                0
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM base_f102
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F102',
    COALESCE(f100.Tonelaje, 0),
    COALESCE(l.Ley_Cu, 0)
FROM f100
CROSS JOIN ley_f102 l;
    
    END;

    -- ETAPA 105; lee resultados M6: F99_A, F99_B, F99_C, F99_D
    IF @etapa=105
    BEGIN




-- F97
;WITH f99_a AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F99_A'
),
f99_b AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F99_B'
),
f99_c AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F99_C'
),
f99_d AS (
    SELECT COALESCE(Tonelaje, 0) AS Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F99_D'
),
ley_f97 AS (
    SELECT
        COALESCE(
            AVG(
                (
                    NULLIF(s.conc_er_ta_gl, 0) +
                    NULLIF(s.conc_er_tb_gl, 0) +
                    NULLIF(s.conc_er_tc_gl, 0) +
                    NULLIF(s.conc_er_td_gl, 0)
                )
                /
                NULLIF(
                    (CASE WHEN NULLIF(s.conc_er_ta_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_tb_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_tc_gl,0) IS NOT NULL THEN 1 ELSE 0 END +
                     CASE WHEN NULLIF(s.conc_er_td_gl,0) IS NOT NULL THEN 1 ELSE 0 END),
                    0
                )
            ),
            0
        ) / 10.0 AS Ley_Cu
    FROM inventar_SpcHidr.sx_ep_flujos_niveles s
    WHERE s.fecha_registro >= @fecha_inicio
      AND s.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F97',
      COALESCE(f99_a.Tonelaje, 0)
    + COALESCE(f99_b.Tonelaje, 0)
    + COALESCE(f99_c.Tonelaje, 0)
    + COALESCE(f99_d.Tonelaje, 0),
    COALESCE(l.Ley_Cu, 0)
FROM f99_a
CROSS JOIN f99_b
CROSS JOIN f99_c
CROSS JOIN f99_d
CROSS JOIN ley_f97 l;
    
    END;

    -- ETAPA 106; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=106
    BEGIN



-- AUX_AGUA_W1
-- Agua W1 hacia SX - Trenes A, B, C y D
--
-- Fuente anterior:
--   tags_sx_ew.agua_adasa_sx_tren_*_m3h
--   Granularidad: horaria
--
-- Fuente nueva:
--   insumos_area_humeda_flujos.agua_w1_tren_*_m3h
--   Granularidad: diaria
--
-- Integracion temporal:
--   m3/h * 24 h/dia = m3/dia

;WITH base_aux_agua_w1 AS (
    SELECT
        (
            COALESCE(t.agua_w1_tren_a_m3h, 0)
          + COALESCE(t.agua_w1_tren_b_m3h, 0)
          + COALESCE(t.agua_w1_tren_c_m3h, 0)
          + COALESCE(t.agua_w1_tren_d_m3h, 0)
        ) * 24.0 AS flujo_m3_dia
    FROM inventar_SpcHidr.insumos_area_humeda_flujos t
    WHERE t.fecha_registro >= @fecha_inicio
      AND t.fecha_registro < DATEADD(DAY, 1, @fecha_fin)
)
INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'AUX_AGUA_W1',
    COALESCE(SUM(flujo_m3_dia), 0),
    0.0
FROM base_aux_agua_w1;
    
    END;

    -- ETAPA 107; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=107
    BEGIN



-- F110
INSERT INTO #valores_m6 (codigo_flujo, TMS_Inicial, Ley_Cu_1, TMS_Final, Ley_Cu_2, Tonelaje, Ley_Cu)
VALUES ('F110', 0, 0, 0, 0, 0, 0);
    
    END;

    -- ETAPA 108; lee resultados M6: F74, F77, F78, F79
    IF @etapa=108
    BEGIN



-- F88: flujo de agua make-up hacia la piscina Feed DUMP.
-- No existe medicion directa por flujometro, por lo que se estima por balance de masa/volumen del nodo.
-- Balance del nodo Feed DUMP:
--     Entradas = F74 + F88
--     Salidas  = F77 + F79 + F78
-- Despejando:
--     F88 = F77 + F79 + F78 - F74
-- donde:
--     F79 = variacion de inventario del nodo en el periodo
--     F78 = perdida por evaporacion (ahora calculada con la tasa de evaporacion real, ver seccion 8)
-- entonces:
--     F88 = F77 + F79 + F78 - F74
-- Si el resultado es negativo, se interpreta como que no se requiere make-up externo en el periodo,
-- dado que la entrada F74 y/o la disminucion de inventario cubren las salidas del sistema.
-- F88
;WITH f77 AS (
    SELECT Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F77'
),
f79 AS (
    SELECT Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F79'
),
f78 AS (
    SELECT Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F78'
),
f74 AS (
    SELECT Tonelaje
    FROM #valores_m6
    WHERE codigo_flujo = 'F74'
)
INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
SELECT
    'F88',
    CASE
        WHEN COALESCE(f77.Tonelaje, 0) + COALESCE(f79.Tonelaje, 0) + COALESCE(f78.Tonelaje, 0) - COALESCE(f74.Tonelaje, 0) < 0
            THEN 0
        ELSE 0 --COALESCE(f77.Tonelaje, 0) + COALESCE(f79.Tonelaje, 0) + COALESCE(f78.Tonelaje, 0) - COALESCE(f74.Tonelaje, 0)
    END,
    0.0
FROM f77
CROSS JOIN f79
CROSS JOIN f78
CROSS JOIN f74;
    
    END;

    -- ETAPA 109; lee resultados M6: F44, F60, F70_ADICIONAL, F70_PRINCIPAL, F81
    IF @etapa=109
    BEGIN



/* ================================================================
   F25 - TRANSFERENCIA DE COBRE PAD OXIDOS
   ----------------------------------------------------------------
   Representa el cobre transferido desde el mineral hacia
   la solucion durante la lixiviacion del PAD Oxidos.

   Entradas liquidas al PAD:
       F70_PRINCIPAL = Refino
       F60 = ILS
       F70_ADICIONAL = otra entrada de solucion contemplada por el modelo
       F81 = DPLS

   Salida liquida:
       F44 = drenaje hacia PLS Oxidos

   Balance de cobre fino:

       CuF23 =
           CuF48
         - CuF39
         - CuF41
         - CuF43
         - CuF46

   F25 ya representa toneladas de cobre fino:
       Ley_Cu = 100 %
================================================================ */

;WITH F70_PRINCIPAL AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F70_PRINCIPAL'
),

F60 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F60'
),

F70_ADICIONAL AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F70_ADICIONAL'
),

F81 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F81'
),

F44 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F44'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F25',

      (F44.Tonelaje * F44.Ley_Cu / 100.0)

    - (F70_PRINCIPAL.Tonelaje * F70_PRINCIPAL.Ley_Cu / 100.0)

    - (F60.Tonelaje * F60.Ley_Cu / 100.0)

    - (F70_ADICIONAL.Tonelaje * F70_ADICIONAL.Ley_Cu / 100.0)

    - (F81.Tonelaje * F81.Ley_Cu / 100.0),

    100.0

FROM F70_PRINCIPAL
CROSS JOIN F60
CROSS JOIN F70_ADICIONAL
CROSS JOIN F81
CROSS JOIN F44;
    
    END;

    -- ETAPA 110; lee resultados M6: F47, F48, F66, F72
    IF @etapa=110
    BEGIN



/* ================================================================
   F29 - TRANSFERENCIA DE COBRE PAD SULFUROS
   ----------------------------------------------------------------
   Representa el cobre transferido desde el mineral hacia
   la solucion durante la lixiviacion del PAD Sulfuros.

   Entradas liquidas al PAD:
       F72 = Refino
       F66 = ILS

   Salidas liquidas:
       F48 = Bleed
       F47 = drenaje PLS Sulfuros

   Balance de cobre fino:

       CuF24 =
           CuF49
         + CuF50
         - CuF44
         - CuF45

   F67 corresponde a evaporacion:
       CuF58 = 0

   F29 ya representa toneladas de cobre fino:
       Ley_Cu = 100 %
================================================================ */

;WITH F72 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F72'
),

F66 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F66'
),

F48 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F48'
),

F47 AS
(
    SELECT
        COALESCE(TRY_CONVERT(float,Tonelaje),0) AS Tonelaje,
        COALESCE(TRY_CONVERT(float,Ley_Cu),0)   AS Ley_Cu
    FROM #valores_m6
    WHERE codigo_flujo = 'F47'
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    Tonelaje,
    Ley_Cu
)
SELECT
    'F29',

      (F48.Tonelaje * F48.Ley_Cu / 100.0)

    + (F47.Tonelaje * F47.Ley_Cu / 100.0)

    - (F72.Tonelaje * F72.Ley_Cu / 100.0)

    - (F66.Tonelaje * F66.Ley_Cu / 100.0),

    100.0

FROM F72
CROSS JOIN F66
CROSS JOIN F48
CROSS JOIN F47;
    
    END;

    -- ETAPA 111; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=111
    BEGIN



    -- F24 fijo en cero por definición del modelo; sin aportes manuales
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F24', 0, 0);
    
    END;

    -- ETAPA 112; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=112
    BEGIN



    -- F28 fijo en cero por definición del modelo; sin aportes manuales
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu) VALUES ('F28', 0, 0);
    
    END;

    -- ETAPA 113; lee resultados M6: F18, F19, F24, F25, F28, F29, F33, F36
    IF @etapa=113
    BEGIN



    -------------------------------------------------------------------------
    -- 8c) AUX_INV_PAD_SULF Y AUX_INV_PAD_OX POR DIFERENCIA (calculado aqui, una vez que F25/F29 ya
    --     estan disponibles con su nueva definicion en base fina)
    -------------------------------------------------------------------------
    DECLARE
        @ton_f19 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F19'), 0),
        @ley_f19 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F19'), 0),
        @ton_f36 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F36'), 0),
        @ley_f36 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F36'), 0),
        @ton_f29 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F29'), 0),
        @ley_f29 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F29'), 0),
        @ton_f18 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F18'), 0),
        @ley_f18 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F18'), 0),
        @ton_f33 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F33'), 0),
        @ley_f33 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F33'), 0),
        @ton_f25 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F25'), 0),
        @ley_f25 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F25'), 0),
        @ton_f28 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F28'), 0),
        @ley_f28 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F28'), 0),
        @ton_f24 decimal(18,6) = ISNULL((SELECT Tonelaje FROM #valores_m6 WHERE codigo_flujo = 'F24'), 0),
        @ley_f24 decimal(18,6) = ISNULL((SELECT Ley_Cu   FROM #valores_m6 WHERE codigo_flujo = 'F24'), 0);
    DECLARE
        @ton_aux_inv_pad_sulf decimal(18,6),
        @ley_aux_inv_pad_sulf decimal(18,6),
        @ton_aux_inv_pad_ox decimal(18,6),
        @ley_aux_inv_pad_ox decimal(18,6);
    SET @ton_aux_inv_pad_sulf = @ton_f19 - @ton_f35 - @ton_f36;
    SET @ley_aux_inv_pad_sulf = CASE
        WHEN @ton_aux_inv_pad_sulf = 0 THEN 0
        ELSE ((@ton_f19 * @ley_f19) - (@ton_f35 * @ley_f35) - (@ton_f36 * @ley_f36) - (@ton_f29 * @ley_f29)) / @ton_aux_inv_pad_sulf
    END;
    SET @ton_aux_inv_pad_ox = @ton_f18 - @ton_f32 - @ton_f33 ;
    SET @ley_aux_inv_pad_ox = CASE
        WHEN @ton_aux_inv_pad_ox = 0 THEN 0
        ELSE ((@ton_f18 * @ley_f18) - (@ton_f32 * @ley_f32) - (@ton_f33 * @ley_f33) - (@ton_f25 * @ley_f25) ) / @ton_aux_inv_pad_ox
    END;
    INSERT INTO #valores_m6 (codigo_flujo, Tonelaje, Ley_Cu)
    VALUES
        ('AUX_INV_PAD_SULF', @ton_aux_inv_pad_sulf, @ley_aux_inv_pad_sulf),
        ('AUX_INV_PAD_OX', @ton_aux_inv_pad_ox, @ley_aux_inv_pad_ox);
    
    END;

    -- ETAPA 114; lee resultados M6: fuentes operacionales / inicialización
    IF @etapa=114
    BEGIN



    -------------------------------------------------------------------------
    -- 8d) INVENTARIO INICIAL DE AUX_INV_PAD_SULF Y AUX_INV_PAD_OX
    -------------------------------------------------------------------------
    DECLARE
        @ton_f19_i decimal(18,6) = 0, @ley_f19_i decimal(18,6) = 0,
        @ton_f18_i decimal(18,6) = 0, @ley_f18_i decimal(18,6) = 0,
        @ton_f35_i decimal(18,6) = 0, @ley_f35_i decimal(18,6) = 0,
        @ton_f32_i decimal(18,6) = 0, @ley_f32_i decimal(18,6) = 0,
        @ton_f36_i decimal(18,6) = 0, @ley_f36_i decimal(18,6) = 0,
        @ton_f33_i decimal(18,6) = 0, @ley_f33_i decimal(18,6) = 0,
        @tms_ini_aux_inv_pad_sulf decimal(18,6) = 0, @ley_ini_aux_inv_pad_sulf decimal(18,6) = 0,
        @tms_ini_aux_inv_pad_ox decimal(18,6) = 0, @ley_ini_aux_inv_pad_ox decimal(18,6) = 0;
/* ================================================================
   BASE DEL DIA INICIAL PARA AUX_INV_PAD_SULF / AUX_INV_PAD_OX
   ----------------------------------------------------------------
   Se mantiene la intención histórica del bloque:

       @ton_f19_i / @ley_f19_i = alimentación del día inicial PAD2
       @ton_f18_i / @ley_f18_i = alimentación del día inicial PAD1

   CORRECCIONES:
       - Se elimina import_leyes_torres.
       - Se usan las mismas fuentes validadas de F16/F17/F19/F18.
       - control_apilado_diario.fecha YA es fecha operacional.
       - NO se aplica DATEADD(DAY,-1,...).

   IMPORTANTE:
       No se modifica todavía la definición posterior de
       @ton_f35_i / @ton_f32_i.
================================================================ */

;WITH Humedad AS
(
    SELECT
        Fecha,
        Turno,
        Humedad_TM1,
        Humedad_TM2

    FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test
    (
        @fecha_inicio,
        DATEADD(DAY, 1, @fecha_inicio)
    )
),

TMH AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH
    FROM #TMH_Principal_Balance
    WHERE Fecha = @fecha_inicio
),

Base AS
(
    SELECT
        t.Fecha,
        t.Turno,
        t.TM,
        t.TMH,

        CASE
            WHEN t.TM = 'TM1'
                THEN h.Humedad_TM1

            WHEN t.TM = 'TM2'
                THEN h.Humedad_TM2
        END AS Humedad,

        l.CuT

    FROM TMH AS t

    LEFT JOIN Humedad AS h
        ON  h.Fecha = t.Fecha
        AND h.Turno = t.Turno

    LEFT JOIN inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test AS l
        ON  l.Fecha = t.Fecha
        AND l.Turno = t.Turno
        AND l.TM    = t.TM
),

Calculo AS
(
    SELECT
        Fecha,
        Turno,
        TM,
        TMH,
        Humedad,
        CuT,

        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
                THEN NULL

            ELSE
                TMH
                *
                (
                    1.0
                    - TRY_CONVERT(float, Humedad) / 100.0
                )
        END AS TMS,

        CASE
            WHEN TMH = 0
                THEN 0

            WHEN Humedad IS NULL
              OR CuT IS NULL
                THEN NULL

            ELSE
                (
                    TMH
                    *
                    (
                        1.0
                        - TRY_CONVERT(float, Humedad) / 100.0
                    )
                )
                * TRY_CONVERT(float, CuT)
                / 100.0

        END AS FCu

    FROM Base
),

Resumen_Dia AS
(
    SELECT
        /* --------------------------------------------------------
           Masa total TM1 + TM2 del día inicial
           -------------------------------------------------------- */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND Humedad IS NULL
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(TMS)
        END AS TMS_Dia,

        /* --------------------------------------------------------
           Cobre fino total del día inicial
           -------------------------------------------------------- */
        CASE
            WHEN SUM
                 (
                     CASE
                         WHEN TMH > 0
                          AND
                              (
                                  Humedad IS NULL
                                  OR CuT IS NULL
                              )
                             THEN 1
                         ELSE 0
                     END
                 ) > 0
                THEN NULL

            ELSE SUM(FCu)
        END AS FCu_Dia

    FROM Calculo
),

Pad_Dia AS
(
    SELECT
        MAX
        (
            CASE
                WHEN cad.pad_id = 2
                 AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0
                    THEN 1
                ELSE 0
            END
        ) AS PAD2_Activo,

        MAX
        (
            CASE
                WHEN cad.pad_id = 1
                 AND TRY_CONVERT(float, cad.volumen_diario_m3) > 0
                    THEN 1
                ELSE 0
            END
        ) AS PAD1_Activo

    FROM inventar_SpcHidr.control_apilado_diario AS cad

    /* fecha YA corresponde al día operacional */
    WHERE CAST(cad.fecha AS date) = @fecha_inicio
)

SELECT
    /* ============================================================
       PAD2 -> estado inicial utilizado por AUX_INV_PAD_SULF
       ============================================================ */
    @ton_f19_i =
        CASE
            WHEN ISNULL(p.PAD2_Activo, 0) = 1
                THEN COALESCE(r.TMS_Dia, 0)
            ELSE 0
        END,

    @ley_f19_i =
        CASE
            WHEN ISNULL(p.PAD2_Activo, 0) = 0
                THEN 0

            WHEN COALESCE(r.TMS_Dia, 0) = 0
                THEN 0

            ELSE
                COALESCE(r.FCu_Dia, 0)
                / NULLIF(r.TMS_Dia, 0)
                * 100.0
        END,

    /* ============================================================
       PAD1 -> estado inicial utilizado por AUX_INV_PAD_OX
       ============================================================ */
    @ton_f18_i =
        CASE
            WHEN ISNULL(p.PAD1_Activo, 0) = 1
                THEN COALESCE(r.TMS_Dia, 0)
            ELSE 0
        END,

    @ley_f18_i =
        CASE
            WHEN ISNULL(p.PAD1_Activo, 0) = 0
                THEN 0

            WHEN COALESCE(r.TMS_Dia, 0) = 0
                THEN 0

            ELSE
                COALESCE(r.FCu_Dia, 0)
                / NULLIF(r.TMS_Dia, 0)
                * 100.0
        END

FROM Resumen_Dia AS r
CROSS JOIN Pad_Dia AS p;
    SELECT
        @ton_f35_i = Tonelaje,
        @ley_f35_i = Ley_Cu
    FROM #tmp_f35_oficial;
    SELECT
        @ton_f32_i = Tonelaje,
        @ley_f32_i = Ley_Cu
    FROM #tmp_f32_oficial;
    SET @tms_ini_aux_inv_pad_sulf = @ton_f19_i - @ton_f35_i - @ton_f36_i;
    SET @ley_ini_aux_inv_pad_sulf = CASE
        WHEN @tms_ini_aux_inv_pad_sulf = 0 THEN 0
        ELSE ((@ton_f19_i * @ley_f19_i) - (@ton_f35_i * @ley_f35_i) - (@ton_f36_i * @ley_f36_i)) / @tms_ini_aux_inv_pad_sulf
    END;
    SET @tms_ini_aux_inv_pad_ox = @ton_f18_i - @ton_f32_i - @ton_f33_i;
    SET @ley_ini_aux_inv_pad_ox = CASE
        WHEN @tms_ini_aux_inv_pad_ox = 0 THEN 0
        ELSE ((@ton_f18_i * @ley_f18_i) - (@ton_f32_i * @ley_f32_i) - (@ton_f33_i * @ley_f33_i)) / @tms_ini_aux_inv_pad_ox
    END;
    UPDATE #valores_m6
       SET TMS_Inicial = @tms_ini_aux_inv_pad_sulf,
           Ley_Cu_1    = @ley_ini_aux_inv_pad_sulf
     WHERE codigo_flujo = 'AUX_INV_PAD_SULF';
    UPDATE #valores_m6
       SET TMS_Inicial = @tms_ini_aux_inv_pad_ox,
           Ley_Cu_1    = @ley_ini_aux_inv_pad_ox
     WHERE codigo_flujo = 'AUX_INV_PAD_OX';
    /* ================================================================
       LIMPIEZA CONTINGENCIA CORREAS
       ================================================================ */
    DROP TABLE IF EXISTS #TMH_Principal_Balance;
    DROP TABLE IF EXISTS #Contingencia_Correas;



    END;

    -- ETAPA 115: F123/F124 leen bases corregidas; F125 consulta inventario óxido.
    IF @etapa=115
    BEGIN
-- Las etapas anteriores ya aplicaron una sola vez los aportes manuales de las bases.
-- Una base desconocida se conserva NULL: nunca sumar sólo la otra mitad.
IF EXISTS (
    SELECT d.destino
    FROM (VALUES ('F123','F71'),('F123','F95'),('F124','F73'),('F124','F96')) d(destino,origen)
    LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
    GROUP BY d.destino
    HAVING COUNT(r.Tonelaje)=2 AND COUNT(r.Ley_Cu)=2
       AND SUM(r.Tonelaje)=0 AND ABS(SUM(r.Tonelaje*r.Ley_Cu/100.0))>0.000001
)
    THROW 51012, 'F123/F124: suma de masa cero con fino no nulo.', 1;
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT d.destino,
       CASE WHEN COUNT(r.Tonelaje)=2 THEN SUM(r.Tonelaje) END,
       CASE WHEN COUNT(r.Tonelaje)=2 AND COUNT(r.Ley_Cu)=2
            THEN CASE WHEN SUM(r.Tonelaje)=0 THEN 0
                 ELSE SUM(r.Tonelaje*r.Ley_Cu)/NULLIF(SUM(r.Tonelaje),0) END END
FROM (VALUES ('F123','F71'),('F123','F95'),('F124','F73'),('F124','F96')) d(destino,origen)
LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
GROUP BY d.destino;

-- F125: inventario independiente de refino óxido; no copia aportes de F76.
;WITH base_f125 AS
(
    SELECT

        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @fecha_inicio

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Inicial,


        (
            SELECT TOP 1
                TRY_CONVERT(float, i.volumen_refino_oxidos)

            FROM inventar_SpcHidr.inv_sol_oxidos AS i

            WHERE CAST(i.fecha_registro AS date) = @ff_mas_1

            ORDER BY i.fecha_registro DESC
        ) AS TMS_Final,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @fecha_inicio

            ORDER BY c.fecha_registro DESC
        ) AS Ley_i_gL,


        (
            SELECT TOP 1
                TRY_CONVERT(float, c.oxidos_refino_cu)

            FROM inventar_SpcHidr.conc_cu AS c

            WHERE CAST(c.fecha_registro AS date) = @ff_mas_1

            ORDER BY c.fecha_registro DESC
        ) AS Ley_f_gL
)

INSERT INTO #valores_m6
(
    codigo_flujo,
    TMS_Inicial,
    Ley_Cu_1,
    TMS_Final,
    Ley_Cu_2,
    Tonelaje,
    Ley_Cu
)

SELECT
    'F125',

    TMS_Inicial,
    Ley_i_gL / 10.0,

    TMS_Final,
    Ley_f_gL / 10.0,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
            THEN NULL

        ELSE
            TMS_Final - TMS_Inicial
    END,

    CASE
        WHEN TMS_Inicial IS NULL
          OR TMS_Final IS NULL
          OR Ley_i_gL IS NULL
          OR Ley_f_gL IS NULL
            THEN NULL

        WHEN TMS_Final - TMS_Inicial = 0
            THEN 0

        ELSE
            (
                Ley_i_gL + Ley_f_gL
            )
            / 2.0
            / 10.0
    END

FROM base_f125;

    END;

    -- ETAPA 116: inventarios de apilado con todas las bases corregidas.
    IF @etapa=116
    BEGIN
-- F21 = F18 + F114 - F20; F23 = F19 + F115 - F22.
-- Las seis bases ya incluyen sus aportes manuales. Conservar masa y fino con signo.
IF EXISTS (
 SELECT d.destino
 FROM (VALUES ('F21','F18',1),('F21','F114',1),('F21','F20',-1),
              ('F23','F19',1),('F23','F115',1),('F23','F22',-1)) d(destino,origen,signo)
 LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
 GROUP BY d.destino
 HAVING COUNT(r.Tonelaje)=3 AND COUNT(r.Ley_Cu)=3
    AND SUM(d.signo*r.Tonelaje)=0
    AND ABS(SUM(d.signo*r.Tonelaje*r.Ley_Cu/100.0))>0.000001
)
 THROW 51013,'F21/F23: inventario de masa cero con fino no nulo.',1;
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT d.destino,
       CASE WHEN COUNT(r.Tonelaje)=3 THEN SUM(d.signo*r.Tonelaje) END,
       CASE WHEN COUNT(r.Tonelaje)=3 AND COUNT(r.Ley_Cu)=3
            THEN CASE WHEN SUM(d.signo*r.Tonelaje)=0 THEN 0
                 ELSE SUM(d.signo*r.Tonelaje*r.Ley_Cu)/NULLIF(SUM(d.signo*r.Tonelaje),0) END END
FROM (VALUES ('F21','F18',1),('F21','F114',1),('F21','F20',-1),
             ('F23','F19',1),('F23','F115',1),('F23','F22',-1)) d(destino,origen,signo)
LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
GROUP BY d.destino;

    END;

    -- ETAPA 117: inventarios de operación y reclamo con bases corregidas.
    IF @etapa=117
    BEGIN
-- Inventarios de operación y reclamo: bases después de sus aportes manuales.
-- Conservar signos, propagar bases desconocidas y ponderar ley por fino neto.
IF EXISTS (
 SELECT d.destino
 FROM (VALUES
('F37','F30',1,3),
 ('F37','F35',-1,3),
 ('F37','F36',-1,3),
 ('F34','F26',1,3),
 ('F34','F32',-1,3),
 ('F34','F33',-1,3),
 ('F31','F22',1,4),
 ('F31','F28',1,4),
 ('F31','F29',-1,4),
 ('F31','F30',-1,4),
 ('F27','F20',1,4),
 ('F27','F24',1,4),
 ('F27','F25',-1,4),
 ('F27','F26',-1,4)) d(destino,origen,signo,componentes)
 LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
 GROUP BY d.destino,d.componentes
 HAVING COUNT(r.Tonelaje)=d.componentes AND COUNT(r.Ley_Cu)=d.componentes
    AND SUM(d.signo*r.Tonelaje)=0
    AND ABS(SUM(d.signo*r.Tonelaje*r.Ley_Cu/100.0))>0.000001
)
 THROW 51014,'F27/F31/F34/F37: inventario de masa cero con fino no nulo.',1;
INSERT INTO #valores_m6(codigo_flujo,Tonelaje,Ley_Cu)
SELECT d.destino,
       CASE WHEN COUNT(r.Tonelaje)=d.componentes THEN SUM(d.signo*r.Tonelaje) END,
       CASE WHEN COUNT(r.Tonelaje)=d.componentes AND COUNT(r.Ley_Cu)=d.componentes
            THEN CASE WHEN SUM(d.signo*r.Tonelaje)=0 THEN 0
                 ELSE SUM(d.signo*r.Tonelaje*r.Ley_Cu)/NULLIF(SUM(d.signo*r.Tonelaje),0) END END
FROM (VALUES
('F37','F30',1,3),
 ('F37','F35',-1,3),
 ('F37','F36',-1,3),
 ('F34','F26',1,3),
 ('F34','F32',-1,3),
 ('F34','F33',-1,3),
 ('F31','F22',1,4),
 ('F31','F28',1,4),
 ('F31','F29',-1,4),
 ('F31','F30',-1,4),
 ('F27','F20',1,4),
 ('F27','F24',1,4),
 ('F27','F25',-1,4),
 ('F27','F26',-1,4)) d(destino,origen,signo,componentes)
LEFT JOIN #valores_m6 r ON r.codigo_flujo=d.origen
GROUP BY d.destino,d.componentes;

    END;

    -- APORTES MANUALES COMUNES: suma de masa/fino antes de la etapa siguiente.
    -- Normalizar componentes F0 antes de aplicar aportes y leer dependencias.
    -- No reemplazar valores presentes ni convertir otros flujos a cero.
    IF OBJECT_ID('tempdb..#m6_f0') IS NOT NULL
        UPDATE r SET Tonelaje=COALESCE(r.Tonelaje,0), Ley_Cu=COALESCE(r.Ley_Cu,0)
        FROM #valores_m6 r JOIN #componentes_m6 f ON f.origen=r.codigo_flujo
        JOIN #m6_f0 z ON z.destino=f.destino;
    DELETE FROM @listos;
    INSERT @listos
    SELECT m.destino FROM #definiciones_m6 m
    JOIN #m6_manual a ON a.destino=m.destino AND a.aplicado=0
    JOIN #componentes_m6 f ON f.destino=m.destino
    JOIN #valores_m6 r ON r.codigo_flujo=f.origen
    WHERE m.habilitado=1
    GROUP BY m.destino,m.componentes
    HAVING COUNT(*)=m.componentes;

    IF EXISTS(SELECT 1 FROM @listos l JOIN #componentes_m6 f ON f.destino=l.destino
              JOIN #valores_m6 r ON r.codigo_flujo=f.origen
              WHERE r.Tonelaje IS NULL OR r.Ley_Cu IS NULL)
        THROW 51010, 'No se puede sumar un aporte a una base desconocida.', 1;

    -- En un agregado, repartir masa y fino por |masa base|. Si todas son cero,
    -- repartir en partes iguales. Esto conserva el aporte total y permite que
    -- cada consulta dependiente lea ya corregidos sus componentes históricos.
    -- El último componente absorbe residuos de redondeo a seis decimales.
    ;WITH bases AS (
        SELECT f.destino,f.origen,r.Tonelaje,r.Ley_Cu,a.masa,a.fino,
            SUM(ABS(r.Tonelaje)) OVER(PARTITION BY f.destino) AS peso,
            COUNT(*) OVER(PARTITION BY f.destino) AS cantidad,
            ROW_NUMBER() OVER(PARTITION BY f.destino ORDER BY f.orden_componente) AS rn
        FROM @listos l JOIN #componentes_m6 f ON f.destino=l.destino
        JOIN #m6_manual a ON a.destino=l.destino
        JOIN #valores_m6 r ON r.codigo_flujo=f.origen
        WHERE a.masa<>0 OR a.fino<>0
    ), cuotas AS (
        SELECT *,CONVERT(decimal(18,6),masa *
            CASE WHEN peso=0 THEN 1.0/cantidad ELSE ABS(Tonelaje)/peso END) AS dm,
            CONVERT(decimal(18,6),fino *
            CASE WHEN peso=0 THEN 1.0/cantidad ELSE ABS(Tonelaje)/peso END) AS df
        FROM bases
    ), ajustes AS (
        SELECT *,CASE WHEN rn=cantidad
            THEN masa-SUM(CASE WHEN rn<cantidad THEN dm ELSE 0 END) OVER(PARTITION BY destino)
            ELSE dm END AS delta_masa,
            CASE WHEN rn=cantidad
            THEN fino-SUM(CASE WHEN rn<cantidad THEN df ELSE 0 END) OVER(PARTITION BY destino)
            ELSE df END AS delta_fino
        FROM cuotas
    )
    SELECT origen,Tonelaje+delta_masa AS masa_nueva,
           Tonelaje*Ley_Cu/100.0+delta_fino AS fino_nuevo
    INTO #m6_ajuste_actual FROM ajustes;

    IF EXISTS(SELECT 1 FROM #m6_ajuste_actual WHERE masa_nueva=0 AND ABS(fino_nuevo)>0.000001)
        THROW 51011, 'Un aporte deja masa cero y fino no nulo; revisar masa/ley del aporte.', 1;
    UPDATE r SET Tonelaje=a.masa_nueva,
        Ley_Cu=CASE WHEN a.masa_nueva=0 THEN 0 ELSE a.fino_nuevo*100.0/a.masa_nueva END
    FROM #valores_m6 r JOIN #m6_ajuste_actual a ON a.origen=r.codigo_flujo;
    -- No acotar inventarios negativos ni sustituir la medición por el aporte.
    UPDATE a SET aplicado=1 FROM #m6_manual a JOIN @listos l ON l.destino=a.destino;

    DROP TABLE #m6_ajuste_actual;

    SET @etapa+=1;
    END;
    -- Cada destino tiene una base explícita y todos los aportes deben haberse aplicado.
    IF EXISTS(SELECT 1 FROM #m6_manual WHERE aplicado=0)
        THROW 51006, 'Quedan aportes sin fuente completa; revisar definición del modelo.', 1;
    SELECT m.destino AS Flujo,
        CASE WHEN m.componentes=1 THEN MAX(r.TMS_Inicial) END AS TMS_Inicial,
        CASE WHEN m.componentes=1 THEN MAX(r.Ley_Cu_1) END AS Ley_Cu_1,
        CASE WHEN m.componentes=1 THEN MAX(r.TMS_Final) END AS TMS_Final,
        CASE WHEN m.componentes=1 THEN MAX(r.Ley_Cu_2) END AS Ley_Cu_2,
        CASE WHEN COUNT(r.Tonelaje)=m.componentes THEN SUM(r.Tonelaje) END AS Tonelaje,
        CASE WHEN COUNT(r.Tonelaje)=m.componentes AND COUNT(r.Ley_Cu)=m.componentes
             THEN CASE WHEN SUM(r.Tonelaje)=0 THEN 0
                  ELSE SUM(r.Tonelaje*r.Ley_Cu)/SUM(r.Tonelaje) END END AS Ley_Cu,
        CASE WHEN COUNT(r.Tonelaje)=m.componentes AND COUNT(r.Ley_Cu)=m.componentes
             THEN SUM(r.Tonelaje*r.Ley_Cu/100.0) END AS FCu
    INTO #m6_salida
    FROM #definiciones_m6 m JOIN #componentes_m6 f ON f.destino=m.destino
    LEFT JOIN #valores_m6 r ON r.codigo_flujo=f.origen
    GROUP BY m.destino,m.componentes;
    -- F0: ninguna celda numérica vacía; conservar valores existentes.
    UPDATE s SET TMS_Inicial=COALESCE(s.TMS_Inicial,0), Ley_Cu_1=COALESCE(s.Ley_Cu_1,0),
        TMS_Final=COALESCE(s.TMS_Final,0), Ley_Cu_2=COALESCE(s.Ley_Cu_2,0),
        Tonelaje=COALESCE(s.Tonelaje,0), Ley_Cu=COALESCE(s.Ley_Cu,0),
        FCu=COALESCE(s.FCu,COALESCE(s.Tonelaje,0)*COALESCE(s.Ley_Cu,0)/100.0)
    FROM #m6_salida s JOIN #m6_f0 z ON z.destino=s.Flujo;
    IF EXISTS(SELECT 1 FROM #m6_salida WHERE Tonelaje=0 AND ABS(FCu)>0.000001)
        THROW 51007, 'Masa cero con fino distinto de cero: revisar representación del flujo.', 1;
    SELECT Flujo,TMS_Inicial,Ley_Cu_1,TMS_Final,Ley_Cu_2,Tonelaje,Ley_Cu,FCu
    FROM #m6_salida ORDER BY CONVERT(int,SUBSTRING(Flujo,2,10));
    IF @debug=1
    BEGIN
        -- Segundo resultado: componentes M6 que permiten auditar las sumas.
        SELECT f.destino AS Flujo_M6, f.origen AS Componente_M6,
               r.Tonelaje,r.Ley_Cu,r.Tonelaje*r.Ley_Cu/100.0 AS FCu,
               a.masa AS Aporte_Masa_M6,a.fino AS Aporte_Fino_M6,a.aplicado
        FROM #componentes_m6 f JOIN #valores_m6 r ON r.codigo_flujo=f.origen
        LEFT JOIN #m6_manual a ON a.destino=f.destino
        ORDER BY TRY_CONVERT(int,SUBSTRING(f.destino,2,10)),f.origen;
        -- El aporte de un agregado se repite en sus componentes; no volver a sumarlo.
    END;
END;