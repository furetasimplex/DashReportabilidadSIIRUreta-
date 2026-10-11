-- CANDIDATO PARA REVISION MANUAL; NO LISTO PARA DESPLIEGUE. NO EJECUTADO.
-- Evidencia LIVE proporcionada por usuario 04/10/2026; ver EVIDENCIA_LIVE_USUARIO.txt.
-- VALIDADO LIVE: funcionalidad TEST V4; falta sys.columns LIVE33 para conciliar este candidato25.
-- Desbloqueo parcial: ya no hay SELECTs fuente faltantes. Permanece guarda de ensayo.
SET NOCOUNT ON;
SET XACT_ABORT ON;
DECLARE @habilitar_ensayo bit=0;
DECLARE @servidor_autorizado sysname=NULL,@base_autorizada sysname=NULL;
IF @habilitar_ensayo<>1 OR @servidor_autorizado IS NULL OR @base_autorizada IS NULL
 THROW 51200,'Pendiente validacion final y autorizacion de ensayo manual.',1;
IF @@SERVERNAME<>@servidor_autorizado OR DB_NAME()<>@base_autorizada
 THROW 51201,'Conexion no autorizada.',1;
IF @@TRANCOUNT<>0 THROW 51202,'Usar sesion sin transaccion externa.',1;
IF OBJECT_ID(N'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2') IS NOT NULL
 THROW 51203,'V2 ya existe: no se reemplaza ningun objeto.',1;
DECLARE @ddl nvarchar(max)=N'CREATE VIEW [inventar_SpcHidr].[vw_tablero_lixiviacion_final_v2]
AS
WITH flujo AS (
 -- Fuente/grano aprobados como DISENO; conservacion TEST V4 VALIDADO LIVE segun usuario; equivalencia local pendiente.
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_oxido_long
 UNION ALL
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_sulfuro_long
), drenaje_raw AS (
 -- VALIDADO LIVE (evidencia usuario 04/10): fecha operacional, PAD y siete analitos.
 -- Se normaliza desde timestamp RAW; nunca desde s.fecha ya normalizada.
 -- Los casts decimal(12,2) pertenecen a *_long y no se agregan ni cambian aqui.
SELECT 1 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,s.nro_parcela_pad,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_drena_concentrados_oxido_long s
 UNION ALL
SELECT 2 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,s.nro_parcela_pad,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_drena_concentrados_sulfuro_long s
), drenaje AS (
 SELECT d.*,p.id_parcela AS parcela_id
 FROM drenaje_raw d LEFT JOIN inventar_SpcHidr.parcela p
 ON p.numero=d.nro_parcela_pad AND p.id_pad=d.pad_id
 -- P29-P32 SULF permanecen en fuente. Sin flujo fisico no crean filas V2.
 -- JOIN TEST V4 VALIDADO LIVE; equivalencia de este candidato local pendiente.
), refino AS (
 -- VALIDADO LIVE: regla operacional y PAD 1/2. Sin nuevos casts quimicos.
 -- Composicion inline equivalente a los fragmentos conceptuales aportados;
 -- no supone publicacion de nuevas vistas operacionales ni altera vistas base.
SELECT 1 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_riego_oxido_refino_base s
 UNION ALL
SELECT 2 AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 CASE WHEN s.fecha_registro >= ''2026-06-01T21:00:00'' AND DATEPART(HOUR,s.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST(s.fecha_registro AS date)) ELSE CAST(s.fecha_registro AS date) END AS fecha,
 s.cu_pp,s.h_p,s.ph,s.cl,s.fet,s.fe2,s.eh
 FROM inventar_SpcHidr.vw_riego_sulfuro_refino_base s
), campana_parcela_base AS (
 -- VALIDADO LIVE: SOLO preagregacion hidraulica. No agrega TMS/leyes/modulos.
 SELECT c.pad_id,c.campana_id,c.numero_campana,c.parcela_id,
 MIN(c.fecha_primer_riego) AS fecha_primer_riego,
 MAX(c.fecha_ultimo_riego) AS fecha_ultimo_riego
 FROM inventar_SpcHidr.campana_parcela_control c
 GROUP BY c.pad_id,c.campana_id,c.numero_campana,c.parcela_id
), campana_parcela_orden AS (
 SELECT c.*,LEAD(c.fecha_primer_riego) OVER (
 PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_primer_riego,c.campana_id
 ) AS siguiente_primer_riego FROM campana_parcela_base c
), campana_parcela AS (
 SELECT c.*,CASE
 WHEN c.fecha_ultimo_riego IS NULL THEN NULL
 WHEN c.siguiente_primer_riego IS NULL THEN c.fecha_ultimo_riego
 WHEN c.fecha_ultimo_riego < DATEADD(DAY,-1,c.siguiente_primer_riego) THEN c.fecha_ultimo_riego
 ELSE DATEADD(DAY,-1,c.siguiente_primer_riego)
 END AS fecha_limite_hidraulica FROM campana_parcela_orden c
)
, base AS (
 -- VALIDADO LIVE: proyeccion funcional TEST V4. Contrato local 25 vs LIVE33 pendiente de conciliar.
 SELECT f.pad_id,f.parcela_id,f.fecha,c.campana_id,c.numero_campana,
 CASE WHEN c.campana_id IS NULL THEN ''FUERA_VENTANA_RIEGO''
      ELSE ''CAMPANA_HIDRAULICA'' END AS estado_asignacion,
 f.flujo_m3_h,f.flujo_m3_d,
 d.cu_pp AS cu_drenaje_gl,d.h_p AS h_drenaje,d.ph AS ph_drenaje,
 d.cl AS cl_drenaje,d.fet AS fet_drenaje,d.fe2 AS fe2_drenaje,d.eh AS eh_drenaje,
 r.cu_pp AS cu_refino_gl,r.h_p AS h_refino,r.ph AS ph_refino,
 r.cl AS cl_refino,r.fet AS fet_refino,r.fe2 AS fe2_refino,r.eh AS eh_refino,
 -- VALIDADO LIVE: unidad Cu g/L y formulas. No implica validacion de esta vista.
 d.cu_pp-r.cu_pp AS delta_cu_gl
 FROM flujo f
 LEFT JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
 LEFT JOIN refino r ON r.pad_id=f.pad_id AND r.fecha=f.fecha
 -- VALIDADO LIVE: ventana inclusiva, NULL ultimo riego no asigna campana.
 LEFT JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
 AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica
), transferencia AS (
 SELECT b.*,b.flujo_m3_d*b.delta_cu_gl AS transferencia_cu_kg_d FROM base b
)
SELECT pad_id,parcela_id,fecha,campana_id,numero_campana,estado_asignacion,
 flujo_m3_h,flujo_m3_d,
 cu_drenaje_gl,h_drenaje,ph_drenaje,cl_drenaje,fet_drenaje,fe2_drenaje,eh_drenaje,
 cu_refino_gl,h_refino,ph_refino,cl_refino,fet_refino,fe2_refino,eh_refino,
 delta_cu_gl,transferencia_cu_kg_d,transferencia_cu_kg_d/1000.0 AS transferencia_cu_t_d
FROM transferencia;';

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
BEGIN TRY
 BEGIN TRANSACTION;
 EXEC sys.sp_executesql @ddl;
 -- Si se habilita un ensayo futuro: V2 existe solo dentro de esta transaccion.
 -- Para validar 02/04 en ensayo: integrarlos aqui en un lote revisado, antes de
 -- ROLLBACK, o preparar una transaccion manual separada en la misma sesion.
 -- Este lote completo revierte inmediatamente: no deja V2 para consultas posteriores.
 -- No hay COMMIT ni promocion autorizada en este paquete.
 ROLLBACK TRANSACTION;
END TRY
BEGIN CATCH
 IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;
