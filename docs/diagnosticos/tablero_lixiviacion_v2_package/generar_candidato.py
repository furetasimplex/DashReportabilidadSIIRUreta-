"""Generacion LOCAL de texto SQL para revision; nunca conecta ni ejecuta SQL."""
from pathlib import Path
OUT=Path(__file__).resolve().parent

def fecha(alias):
    return f"CASE WHEN {alias}.fecha_registro >= '2026-06-01T21:00:00' AND DATEPART(HOUR,{alias}.fecha_registro)>=20 THEN DATEADD(DAY,1,CAST({alias}.fecha_registro AS date)) ELSE CAST({alias}.fecha_registro AS date) END"

quimica='cu_pp,h_p,ph,cl,fet,fe2,eh'
def rama(tipo,pad,refino=False):
    name=f'vw_riego_{tipo}_refino_base' if refino else f'vw_drena_concentrados_{tipo}_long'
    extra='' if refino else ',s.nro_parcela_pad'
    return f'''SELECT {pad} AS pad_id,s.id_registro,s.fecha_registro AS fecha_registro_raw,
 {fecha('s')} AS fecha{extra},
 {','.join('s.'+x for x in quimica.split(','))}
 FROM inventar_SpcHidr.{name} s'''

common='''WITH flujo AS (
 -- Fuente/grano aprobados como DISENO; conservacion TEST V4 VALIDADO LIVE segun usuario; equivalencia local pendiente.
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_oxido_long
 UNION ALL
 SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM inventar_SpcHidr.vw_flujos_reales_sulfuro_long
), drenaje_raw AS (
 -- VALIDADO LIVE (evidencia usuario 04/10): fecha operacional, PAD y siete analitos.
 -- Se normaliza desde timestamp RAW; nunca desde s.fecha ya normalizada.
 -- Los casts decimal(12,2) pertenecen a *_long y no se agregan ni cambian aqui.
'''+rama('oxido',1)+'\n UNION ALL\n'+rama('sulfuro',2)+'''
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
'''+rama('oxido',1,True)+'\n UNION ALL\n'+rama('sulfuro',2,True)+'''
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
)'''

projection='''
, base AS (
 -- VALIDADO LIVE: proyeccion funcional TEST V4. Contrato local 25 vs LIVE33 pendiente de conciliar.
 SELECT f.pad_id,f.parcela_id,f.fecha,c.campana_id,c.numero_campana,
 CASE WHEN c.campana_id IS NULL THEN 'FUERA_VENTANA_RIEGO'
      ELSE 'CAMPANA_HIDRAULICA' END AS estado_asignacion,
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
FROM transferencia;'''
ddl='CREATE VIEW [inventar_SpcHidr].[vw_tablero_lixiviacion_final_v2]\nAS\n'+common+projection
candidate='''-- CANDIDATO PARA REVISION MANUAL; NO LISTO PARA DESPLIEGUE. NO EJECUTADO.
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
DECLARE @ddl nvarchar(max)=N\''''+ddl.replace("'","''")+"';\n"+'''
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
'''
(OUT/'01_create_v2_candidate.sql').write_text(candidate,encoding='utf-8')

checks=[]
def check(label,query): checks.append((label,query))
check('01. Claves NULL/duplicadas FUENTE (cero filas esperado)', '''SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS filas FROM flujo
GROUP BY pad_id,parcela_id,fecha HAVING COUNT_BIG(*)>1 OR pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL''')
check('02. Claves NULL/duplicadas V2 (cero filas)', '''SELECT pad_id,parcela_id,fecha,COUNT_BIG(*) AS filas FROM v
GROUP BY pad_id,parcela_id,fecha HAVING COUNT_BIG(*)>1 OR pad_id IS NULL OR parcela_id IS NULL OR fecha IS NULL''')
for left,right in [('flujo','v'),('v','flujo')]:
 check('03. Conservacion EXACTA '+left+' menos '+right+' (cero filas; combinar unicidad/conteos)',f'''SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM {left}
EXCEPT SELECT pad_id,parcela_id,fecha,flujo_m3_h,flujo_m3_d FROM {right}''')
check('04. Cobertura por PAD/fecha (informativo; comparar pares)', '''SELECT 'FUENTE' AS origen,pad_id,fecha,COUNT_BIG(*) AS filas,COUNT(flujo_m3_d) AS no_null,SUM(flujo_m3_d) AS m3 FROM flujo GROUP BY pad_id,fecha
UNION ALL SELECT 'V2',pad_id,fecha,COUNT_BIG(*),COUNT(flujo_m3_d),SUM(flujo_m3_d) FROM v GROUP BY pad_id,fecha ORDER BY pad_id,fecha,origen''')
check('05. Drenaje raw por PAD/numero/fecha (cero duplicados)', '''SELECT pad_id,nro_parcela_pad,fecha,COUNT_BIG(*) AS filas FROM drenaje_raw
GROUP BY pad_id,nro_parcela_pad,fecha HAVING COUNT_BIG(*)>1 OR fecha IS NULL''')
check('06. Refino PAD/fecha (cero duplicados)', '''SELECT pad_id,fecha,COUNT_BIG(*) AS filas FROM refino GROUP BY pad_id,fecha HAVING COUNT_BIG(*)>1 OR fecha IS NULL''')
check('07. Dimension parcela: unicidad PAD/numero (cero filas)', '''SELECT id_pad,numero,COUNT_BIG(*) AS filas FROM inventar_SpcHidr.parcela
WHERE id_pad IN (1,2) GROUP BY id_pad,numero HAVING COUNT_BIG(*)>1''')
check('08. Drenaje sin dimension (informativo: distinguir historicos SULF29-32, no remapear)', '''SELECT pad_id,nro_parcela_pad,COUNT_BIG(*) AS filas FROM drenaje WHERE parcela_id IS NULL GROUP BY pad_id,nro_parcela_pad''')
for source,join in [('drenaje','d.parcela_id=f.parcela_id AND '),('refino','')]:
 check('09. Coincidencias '+source+' despues de JOIN fisico (cero multiplicidad)', f'''SELECT f.pad_id,f.parcela_id,f.fecha,COUNT_BIG(*) AS coincidencias FROM flujo f
JOIN {source} d ON d.pad_id=f.pad_id AND {join}d.fecha=f.fecha
GROUP BY f.pad_id,f.parcela_id,f.fecha HAVING COUNT_BIG(*)>1''')
check('10. Campanas por clave: contar coincidencias, no esconder con DISTINCT (cero >1)', '''SELECT f.pad_id,f.parcela_id,f.fecha,COUNT_BIG(*) AS coincidencias
FROM flujo f JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica
GROUP BY f.pad_id,f.parcela_id,f.fecha HAVING COUNT_BIG(*)>1''')
check('11. Conservacion filas fuera de ventana (cero filas)', '''SELECT f.* FROM flujo f WHERE NOT EXISTS (
SELECT 1 FROM campana_parcela c WHERE c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica)
AND NOT EXISTS (SELECT 1 FROM v WHERE v.pad_id=f.pad_id AND v.parcela_id=f.parcela_id AND v.fecha=f.fecha
AND v.campana_id IS NULL AND v.numero_campana IS NULL AND v.estado_asignacion='FUERA_VENTANA_RIEGO')''')
expected='''SELECT f.pad_id,f.parcela_id,f.fecha,c.campana_id,c.numero_campana,
CASE WHEN c.campana_id IS NULL THEN 'FUERA_VENTANA_RIEGO' ELSE 'CAMPANA_HIDRAULICA' END AS estado_asignacion
FROM flujo f LEFT JOIN campana_parcela c ON c.pad_id=f.pad_id AND c.parcela_id=f.parcela_id
AND f.fecha>=c.fecha_primer_riego AND f.fecha<=c.fecha_limite_hidraulica'''
check('12. Campana/numero/estado esperado menos V2 (cero filas)',expected+'\nEXCEPT SELECT pad_id,parcela_id,fecha,campana_id,numero_campana,estado_asignacion FROM v')
check('13. V2 menos campana/numero/estado esperado (cero filas)','SELECT pad_id,parcela_id,fecha,campana_id,numero_campana,estado_asignacion FROM v\nEXCEPT '+expected)
check('14. Cu de fuentes menos V2 (cero filas)', '''SELECT f.pad_id,f.parcela_id,f.fecha,d.cu_pp,r.cu_pp FROM flujo f
LEFT JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
LEFT JOIN refino r ON r.pad_id=f.pad_id AND r.fecha=f.fecha
EXCEPT SELECT pad_id,parcela_id,fecha,cu_drenaje_gl,cu_refino_gl FROM v''')
check('14b. Otros seis analitos por lado (cero diferencias)', '''SELECT f.pad_id,f.parcela_id,f.fecha,
d.h_p,d.ph,d.cl,d.fet,d.fe2,d.eh,r.h_p,r.ph,r.cl,r.fet,r.fe2,r.eh FROM flujo f
LEFT JOIN drenaje d ON d.pad_id=f.pad_id AND d.parcela_id=f.parcela_id AND d.fecha=f.fecha
LEFT JOIN refino r ON r.pad_id=f.pad_id AND r.fecha=f.fecha
EXCEPT SELECT pad_id,parcela_id,fecha,h_drenaje,ph_drenaje,cl_drenaje,fet_drenaje,fe2_drenaje,eh_drenaje,
h_refino,ph_refino,cl_refino,fet_refino,fe2_refino,eh_refino FROM v''')
check('14c. Fuera de ventana con numero o estado contradictorio (cero filas)', '''SELECT * FROM v
WHERE (campana_id IS NULL AND (numero_campana IS NOT NULL OR estado_asignacion<>'FUERA_VENTANA_RIEGO'))
OR (campana_id IS NOT NULL AND estado_asignacion<>'CAMPANA_HIDRAULICA') OR estado_asignacion IS NULL''')
check('15. Formulas y NULL (cero diferencias; precision final pendiente)', '''SELECT pad_id,parcela_id,fecha,delta_cu_gl,transferencia_cu_kg_d,transferencia_cu_t_d FROM v
EXCEPT SELECT pad_id,parcela_id,fecha,cu_drenaje_gl-cu_refino_gl,
flujo_m3_d*(cu_drenaje_gl-cu_refino_gl),(flujo_m3_d*(cu_drenaje_gl-cu_refino_gl))/1000.0 FROM v''')
check('16. NULL/negativos (informativo, no rechazar ni convertir a cero)', '''SELECT * FROM v WHERE delta_cu_gl IS NULL OR delta_cu_gl<0''')
check('17. Reconciliacion periodo LIVE aportado (informativa; V2 aun pendiente)', '''SELECT pad_id,COUNT_BIG(*) AS claves,
SUM(CASE WHEN campana_id IS NOT NULL THEN 1 ELSE 0 END) AS con_campana,
SUM(CASE WHEN campana_id IS NULL THEN 1 ELSE 0 END) AS fuera,
SUM(CASE WHEN campana_id IS NULL AND flujo_m3_d>0 THEN 1 ELSE 0 END) AS positivos_fuera,
SUM(CASE WHEN campana_id IS NULL THEN flujo_m3_d END) AS m3_fuera
FROM v WHERE fecha BETWEEN '20260601' AND '20260910' GROUP BY pad_id''')
validation='''-- READ ONLY, NO EJECUTADO. TEST V4 funcional VALIDADO LIVE; candidato local no equiparado al contrato LIVE33.
-- Los mismos CTE de 01 son generados desde generar_candidato.py, sin placeholders.
-- Ejecutar futuro manualmente sobre corte estable; no presupone snapshot isolation.
-- EXCEPT compara NULL sin rellenar cero, pero elimina duplicados: revisar 01/02/04.
-- Si V2 solo existe en ensayo de 01, ejecutar aqui EN LA MISMA SESION antes de rollback.
SET NOCOUNT ON;
IF OBJECT_ID(N'inventar_SpcHidr.vw_tablero_lixiviacion_final_v2',N'V') IS NULL
 THROW 51300,'No existe V2 visible para validar.',1;
DECLARE @ctes nvarchar(max)=N\''''+common.replace("'","''")+''',v AS (SELECT * FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2) ';
DECLARE @sql nvarchar(max);
'''
for label,q in checks:
 validation+='\n-- '+label+'\nSET @sql=@ctes+N\''+q.replace("'","''")+";';\nEXEC sys.sp_executesql @sql;\n"
validation+='''
-- Referencias LIVE aportadas (NO resultados ejecutados aqui):
-- OX: 3264 claves,2219 con campana,1045 fuera,106 positivos fuera,6.128278 m3.
-- SULF:2856 claves,1839 con campana,1017 fuera,0 positivos fuera.
-- 6.128278 y desglose por parcela son cifras reportadas; precision exacta pendiente.
-- No usar umbral de descarte: conservar incluso flujo_m3_h positivo <0.01.
-- Ejemplo dimensional aportado:672*(2.03-0.28)=1176 kg/d=1.176 t/d.
-- No exigir igualdad de conteos V2 contra legacy ni aprobar tolerancias arbitrarias.
'''
(OUT/'02_validate_v2_readonly.sql').write_text(validation,encoding='utf-8')
print('01/02 generados localmente; SQL no ejecutado.')
