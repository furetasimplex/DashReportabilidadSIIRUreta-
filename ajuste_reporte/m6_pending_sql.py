"""SQL de la ruta pendiente M6 mínima. Generar texto nunca instala objetos."""
import json,hashlib
from pathlib import Path

CONTRACT=json.loads(Path(__file__).with_name('m6_pending_contract.json').read_text(encoding='utf8'))
COLUMNS=CONTRACT['columns'];FIELDS=tuple(c['name'] for c in COLUMNS if c['name']!='Fecha')
TYPES={c['name']:c['type'] for c in COLUMNS}
LOT='inventar_SpcHidr.rep_prod_m6_pending_lote'
STAGE='inventar_SpcHidr.rep_prod_ajustado_stg'
VERSIONS='inventar_SpcHidr.Datos_conciliados_of_ver'
PROC='inventar_SpcHidr.sp_rep_m6_insert_pending'
GUARD='inventar_SpcHidr.tr_rep_m6_pending_versions_guard'
IMMUTABLE='inventar_SpcHidr.tr_rep_m6_pending_lote_immutable'

def quote(n):return '['+n.replace(']',']]')+']'
def columns(alias=''):
 return ','.join((alias+'.' if alias else '')+quote(n) for n in FIELDS)
def row_canonical(alias):
 parts=["CAST(N'M6-PENDING-47-v1;' AS nvarchar(max))"]
 for c in COLUMNS:
  n,t=c['name'],c['type'];x=alias+'.'+quote(n)
  v=(f'CONVERT(nvarchar(max),CONVERT(varchar(99),{x},3))' if t.startswith('float') else
     f'CONVERT(nvarchar(max),CONVERT(char(10),{x},23))' if t=='date' else f'CONVERT(nvarchar(max),{x})')
  tag=n+'|'+t
  parts.append(f"CASE WHEN {x} IS NULL THEN N'{tag}|N;' ELSE N'{tag}|V'+CONVERT(nvarchar(20),DATALENGTH({v}))+N':'+{v}+N';' END")
 return '\n+'.join(parts)
def hash_select(table,where=''):
 return f"""SELECT CONVERT(binary(32),HASHBYTES('SHA2_256',CONVERT(varbinary(max),
 CAST(N'M6-PENDING-SET-v1;' AS nvarchar(max))+CONVERT(nvarchar(20),COUNT_BIG(*))+N';'+
 COALESCE(STRING_AGG(CAST({row_canonical('p')} AS nvarchar(max)),N'') WITHIN GROUP(ORDER BY p.Fecha),N'')))) payload_sha256
 FROM {table} p {where}"""
JSON_WITH=','.join(quote(c['name'])+' '+c['type']+' '+"'$."+c['name']+"'" for c in COLUMNS)
HASH_JSON_SQL=hash_select('OPENJSON(:payload_json) WITH('+JSON_WITH+')')

GUARD_DEFINITION=f'''CREATE TRIGGER {GUARD} ON {VERSIONS} AFTER INSERT,UPDATE,DELETE AS
BEGIN
 SET NOCOUNT ON;
 -- Una sentencia mixta con filas M6 y legacy se rechaza completa, nunca se filtra.
 IF EXISTS(SELECT 1 FROM deleted d JOIN {LOT} l ON l.run_id=d.run_id)
  THROW 52871,'Version M6 registrada inmutable: UPDATE/DELETE rechazado.',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN {LOT} l ON l.run_id=i.run_id
 WHERE i.caso_id<>l.caso_id OR i.Fecha NOT BETWEEN l.fecha_inicio AND l.fecha_fin
 OR ISNULL(i.estado_validacion,'')<>'PENDIENTE' OR i.es_activa<>0 OR ISNULL(i.origen,'')<>'M6_PENDING')
  THROW 52871,'La version M6 debe conservar origen, periodo y estado pendiente/inactivo.',1;
 DECLARE @u uniqueidentifier,@hash binary(32);
 DECLARE lots CURSOR LOCAL FAST_FORWARD FOR SELECT DISTINCT i.run_id FROM inserted i JOIN {LOT} l ON l.run_id=i.run_id;
 OPEN lots;FETCH NEXT FROM lots INTO @u;
 WHILE @@FETCH_STATUS=0
 BEGIN
  SELECT @hash=payload_sha256 FROM ({hash_select(VERSIONS,'WHERE p.run_id=@u')}) h;
  IF @hash<>(SELECT payload_sha256 FROM {LOT} WHERE run_id=@u)
    OR (SELECT COUNT(*) FROM {VERSIONS} WHERE run_id=@u)<>7
   THROW 52871,'Insercion M6 incompleta o payload diferente del registrado.',1;
  FETCH NEXT FROM lots INTO @u;
 END
 CLOSE lots;DEALLOCATE lots;
END'''
IMMUTABLE_DEFINITION=f'''CREATE TRIGGER {IMMUTABLE} ON {LOT} AFTER INSERT,UPDATE,DELETE AS
BEGIN SET NOCOUNT ON;
 IF EXISTS(SELECT 1 FROM deleted) THROW 52872,'Origen y payload del UUID M6 son inmutables.',1;
 IF EXISTS(SELECT 1 FROM inserted i JOIN {VERSIONS} v ON v.run_id=i.run_id)
  THROW 52872,'No atribuir origenM6 a UUID historico existente.',1;
END'''

def proc_definition():
 types=',\n'.join(quote(c['name'])+' '+c['type']+' NULL' for c in COLUMNS)
 inherited=','.join(quote(n) for n in CONTRACT['inherited'])
 allowed=','.join("N'"+c['name']+"'" for c in COLUMNS)
 numeric=','.join("N'"+c['name']+"'" for c in COLUMNS if c['type'].startswith('float') or c['type']=='int')
 ints=','.join("N'"+c['name']+"'" for c in COLUMNS if c['type']=='int')
 strings=','.join("N'"+c['name']+"'" for c in COLUMNS if c['type'].startswith('nvarchar'))
 adjusted=' OR '.join(quote(n)+' IS NULL OR '+quote(n)+'<0' for n in CONTRACT['adjusted'])
 target_checks=[]
 for col,codes,measure in [('Chancado_TMS_Real',['F3'],'masa_reconciliada'),('Sal_promedio_dia',['F13','F14'],'masa_reconciliada'),
  ('SRR_TMS_promedio_dia',['F9'],'masa_reconciliada'),('SRR_TMS_promedio_dia*Ley_CuT_Real_srr/100.0',['F9'],'fino_cu_reconciliado'),
  ('Apilado_TMS_Real',['F18','F19'],'masa_reconciliada'),('Cobre_fino_Apilado_Real',['F18','F19'],'fino_cu_reconciliado'),
  ('TMS_Rotopala_1_Real',['F32'],'masa_reconciliada'),('TMS_Rotopala_2_Real',['F35'],'masa_reconciliada'),
  ('Camiones_TMS_Reclamo_Oxidos',['F33'],'masa_reconciliada'),('Camiones_TMS_Reclamo_Sulfuros',['F36'],'masa_reconciliada')]:
  cs=','.join("'"+s+"'" for s in codes)
  target_checks.append(f"((SELECT SUM({col}) FROM @payload),(SELECT SUM({measure}) FROM DEV_SIIR.hidro.recon_resultado_flujo WITH(HOLDLOCK) WHERE caso_id=@caso_id AND run_id=@solver_run_id AND codigo_flujo IN({cs})))")
 math_checks='INSERT @checks VALUES '+',\n'.join(target_checks)+';'
 return f'''CREATE PROCEDURE {PROC}
 @run_id uniqueidentifier,@caso_id int,@modelo_id int,@solver_run_id int,
 @version_reglas int,@payload_json nvarchar(max),@expected_hash binary(32),@usuario nvarchar(128)
AS
BEGIN
 SET NOCOUNT ON;SET XACT_ABORT ON;
 SET ANSI_NULLS ON;SET ANSI_PADDING ON;SET ANSI_WARNINGS ON;SET ARITHABORT ON;
 SET CONCAT_NULL_YIELDS_NULL ON;SET NUMERIC_ROUNDABORT OFF;
 IF DB_NAME()<>N'inventar_SpcHidr' OR LOWER(CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')))<>N'vps-5347319-x'
  THROW 52870,'Solo DEV autorizado.',1;
 IF ISNULL(TRY_CONVERT(int,SESSION_CONTEXT(N'm6_pending_execute_dev')),0)<>1
  THROW 52870,'Falta ejecucion DEV explicita de la ruta pendiente.',1;
 IF @run_id IS NULL OR @caso_id<>10009 OR @caso_id IS NULL OR @modelo_id<>2 OR @modelo_id IS NULL
  OR @solver_run_id<>10082 OR @solver_run_id IS NULL OR @version_reglas<>1 OR @version_reglas IS NULL
  OR @expected_hash IS NULL OR @usuario IS NULL OR LEN(LTRIM(RTRIM(@usuario)))=0
  THROW 52870,'Esta ruta solo admite caso10009/modelo2/run10082/reglas1.',1;
 IF NOT EXISTS(SELECT 1 FROM sys.triggers WHERE object_id=OBJECT_ID(N'{GUARD}') AND is_disabled=0)
  OR ISNULL(HASHBYTES('SHA2_256',CONVERT(varbinary(max),OBJECT_DEFINITION(OBJECT_ID(N'{GUARD}')))),0x00)<>0x{hashlib.sha256(GUARD_DEFINITION.encode('utf-16le')).hexdigest()}
  THROW 52870,'Proteccion M6 no instalada o no coincide con version revisada.',1;
 IF ISJSON(@payload_json)<>1 OR LEFT(LTRIM(@payload_json),1)<>'[' THROW 52870,'Payload debe ser array JSON.',1;
 IF (SELECT COUNT(*) FROM OPENJSON(@payload_json))<>7 THROW 52870,'Se requieren siete filas.',1;
 IF EXISTS(SELECT 1 FROM OPENJSON(@payload_json) r WHERE r.type<>5
  OR (SELECT COUNT(*) FROM OPENJSON(r.value))<>48
  OR (SELECT COUNT(DISTINCT [key] COLLATE Latin1_General_100_BIN2) FROM OPENJSON(r.value))<>48)
  THROW 52870,'Cada fila requiere Fecha y47campos unicos.',1;
 IF EXISTS(SELECT 1 FROM OPENJSON(@payload_json) r CROSS APPLY OPENJSON(r.value) c
  WHERE c.[key] COLLATE Latin1_General_100_BIN2 NOT IN({allowed})
   OR (c.[key] IN({numeric}) AND c.type NOT IN(0,2))
   OR (c.[key] IN({ints}) AND c.type<>0 AND TRY_CONVERT(int,c.value) IS NULL)
   OR (c.[key] IN({strings}) AND (c.type NOT IN(0,1) OR DATALENGTH(c.value)>510))
   OR (c.[key]='Fecha' AND (c.type<>1 OR LEN(c.value)<>10 OR TRY_CONVERT(date,c.value,23) IS NULL)))
  THROW 52870,'Nombres/tipos/fechas del contrato47 invalidos.',1;
 DECLARE @payload TABLE({types});
 INSERT @payload SELECT * FROM OPENJSON(@payload_json) WITH({JSON_WITH});
 IF (SELECT COUNT(DISTINCT Fecha) FROM @payload)<>7
  OR EXISTS(SELECT 1 FROM @payload WHERE Fecha IS NULL OR Fecha NOT BETWEEN '20260901' AND '20260907')
  THROW 52870,'Periodo incompleto/duplicado o distinto de01..07Sep2026.',1;
 DECLARE @hash binary(32);
 SELECT @hash=payload_sha256 FROM ({hash_select('@payload')}) h;
 IF @hash<>@expected_hash THROW 52870,'Hash del payload distinto del presentado.',1;
 DECLARE @own bit=CASE WHEN @@TRANCOUNT=0 THEN 1 ELSE 0 END,@lock int,
 @resource nvarchar(255)=N'M6_PENDING_UUID:'+CONVERT(nvarchar(36),@run_id);
 BEGIN TRY
 IF @own=1 BEGIN TRAN;
 EXEC @lock=sys.sp_getapplock @Resource=@resource,@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;
 IF @lock<0 THROW 52870,'No se obtuvo bloqueoUUID.',1;
 IF EXISTS(SELECT 1 FROM {LOT} WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id)
 BEGIN
  IF NOT EXISTS(SELECT 1 FROM {LOT} WHERE run_id=@run_id AND caso_id=@caso_id AND modelo_id=@modelo_id
   AND solver_run_id=@solver_run_id AND version_reglas=@version_reglas AND payload_sha256=@hash AND usuario=@usuario)
   THROW 52870,'UUID registrado con otro origen/contenido/usuario.',1;
  DECLARE @old_hash binary(32),@stage_hash binary(32);
  SELECT @old_hash=payload_sha256 FROM ({hash_select(VERSIONS,'WHERE p.run_id=@run_id')}) h;
  SELECT @stage_hash=payload_sha256 FROM ({hash_select(STAGE,'WHERE p.run_id=@run_id')}) h;
  IF @old_hash<>@hash OR @stage_hash<>@hash OR (SELECT COUNT(*) FROM {VERSIONS} WHERE run_id=@run_id)<>7
   OR EXISTS(SELECT 1 FROM {STAGE} WHERE run_id=@run_id AND (caso_id<>@caso_id OR version_reglas<>@version_reglas))
   OR EXISTS(SELECT 1 FROM {VERSIONS} WHERE run_id=@run_id AND (ISNULL(estado_validacion,'')<>'PENDIENTE' OR es_activa<>0 OR caso_id<>@caso_id))
   THROW 52870,'Lote previo incompleto o alterado.',1;
  IF @own=1 COMMIT;
  SELECT @run_id run_id,7 rows_in_batch,0 rows_inserted,CAST(1 AS bit) idempotent;RETURN;
 END
 IF EXISTS(SELECT 1 FROM {STAGE} WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id)
  OR EXISTS(SELECT 1 FROM {VERSIONS} WITH(UPDLOCK,HOLDLOCK) WHERE run_id=@run_id)
  THROW 52870,'UUID ya utilizado fuera de la ruta M6; no atribuir origen retrospectivo.',1;
 IF NOT EXISTS(SELECT 1 FROM DEV_SIIR.hidro.recon_caso c WITH(HOLDLOCK)
 JOIN DEV_SIIR.hidro.recon_modelo m WITH(HOLDLOCK) ON m.id=c.modelo_id
 JOIN DEV_SIIR.hidro.recon_solver_run r WITH(HOLDLOCK) ON r.caso_id=c.id AND r.id=@solver_run_id
 WHERE c.id=@caso_id AND c.modelo_id=@modelo_id AND m.codigo='hidrometalurgia_125_v2'
 AND m.total_flujos=125 AND m.legacy_modelo_id=6 AND m.activo=1 AND r.estado='success'
 AND CAST(c.fecha_inicio AS date)='20260901' AND CAST(c.fecha_fin AS date)='20260907')
  THROW 52870,'Caso/modelo/solver/periodo no corresponde.',1;
 IF (SELECT COUNT(*) FROM DEV_SIIR.hidro.recon_resultado_flujo WITH(HOLDLOCK) WHERE caso_id=@caso_id AND run_id=@solver_run_id)<>125
  OR (SELECT COUNT(DISTINCT codigo_flujo) FROM DEV_SIIR.hidro.recon_resultado_flujo WITH(HOLDLOCK) WHERE caso_id=@caso_id AND run_id=@solver_run_id)<>125
  THROW 52870,'Resultados125 incompletos/duplicados.',1;
 IF EXISTS(SELECT 1 FROM DEV_SIIR.hidro.recon_resultado_flujo r WITH(HOLDLOCK)
 LEFT JOIN DEV_SIIR.hidro.recon_flujo_modelo f WITH(HOLDLOCK) ON f.id=r.flujo_modelo_id
 WHERE r.caso_id=@caso_id AND r.run_id=@solver_run_id AND
 (f.modelo_id IS NULL OR f.modelo_id<>@modelo_id OR f.activo<>1 OR f.codigo_flujo<>r.codigo_flujo
 OR TRY_CONVERT(int,SUBSTRING(r.codigo_flujo,2,10)) IS NULL
 OR TRY_CONVERT(int,SUBSTRING(r.codigo_flujo,2,10)) NOT BETWEEN 1 AND 125
 OR r.codigo_flujo<>CONCAT('F',TRY_CONVERT(int,SUBSTRING(r.codigo_flujo,2,10)))
 OR r.masa_reconciliada IS NULL OR r.fino_cu_reconciliado IS NULL))
  THROW 52870,'Claves reconciliadas no pertenecen al modelo125.',1;
 IF EXISTS(SELECT 1 FROM @payload WHERE {adjusted}) THROW 52870,'Columnas ajustadas ausentes/negativas.',1;
 DECLARE @checks TABLE(actual float,target float);
 {math_checks}
 IF EXISTS(SELECT 1 FROM @checks WHERE actual IS NULL OR target IS NULL OR ABS(actual-target)>1E-8+ABS(target)*1E-12)
  THROW 52870,'Los objetivos reconciliados no coinciden con el payload.',1;
 IF EXISTS(SELECT 1 FROM @payload WHERE Ley_CuT_Real>100 OR Ley_CuT_Real_srr>100
 OR ABS(Apilado_TMS_Real*Ley_CuT_Real/100.0-Cobre_fino_Apilado_Real)>1E-8+ABS(Cobre_fino_Apilado_Real)*1E-12
 OR ABS(SRR_TMS_Turno_A+SRR_TMS_Turno_B-SRR_TMS_promedio_dia)>1E-8+ABS(SRR_TMS_promedio_dia)*1E-12
 OR ABS(Sal_turno_A+Sal_Turno_B-Sal_promedio_dia)>1E-8+ABS(Sal_promedio_dia)*1E-12
 OR ABS(Apilado_TMH_turno_A+Apilado_TMH_turno_B-Apilado_TMH_promedio_dia)>1E-8+ABS(Apilado_TMH_promedio_dia)*1E-12)
  THROW 52870,'Relaciones diarias incompatibles con reglas vigentes.',1;
 IF (SELECT COUNT(*) FROM inventar_SpcHidr.Datos_conciliados_of WITH(HOLDLOCK) WHERE Fecha BETWEEN '20260901' AND '20260907')<>7
  OR EXISTS(SELECT Fecha,{inherited} FROM @payload EXCEPT
   SELECT Fecha,{inherited} FROM inventar_SpcHidr.Datos_conciliados_of WITH(HOLDLOCK) WHERE Fecha BETWEEN '20260901' AND '20260907')
  THROW 52870,'Las28heredadas o el periodo base cambiaron.',1;
 INSERT {LOT}(run_id,caso_namespace,caso_id,modelo_id,modelo_codigo,legacy_modelo_id,solver_run_id,
 fecha_inicio,fecha_fin,cantidad_dias,version_reglas,payload_sha256,estado_lote,usuario,sql_principal)
 VALUES(@run_id,N'DEV_SIIR.hidro.recon_caso',@caso_id,@modelo_id,'hidrometalurgia_125_v2',6,@solver_run_id,
 '20260901','20260907',7,@version_reglas,@hash,'PENDIENTE',@usuario,ORIGINAL_LOGIN());
 INSERT {STAGE}(run_id,caso_id,Fecha,{columns()},version_reglas,ts_ajuste,estado)
 SELECT @run_id,@caso_id,p.Fecha,{columns('p')},@version_reglas,SYSUTCDATETIME(),'1' FROM @payload p;
 SELECT @stage_hash=payload_sha256 FROM ({hash_select(STAGE,'WHERE p.run_id=@run_id')}) h;
 IF @stage_hash<>@hash THROW 52870,'La lectura del staging difiere del payload.',1;
 INSERT {VERSIONS}(Fecha,{columns()},estado,run_id,caso_id,version_reglas,ts_ajuste,es_activa,origen,
 comentario,fecha_validacion,usuario_validacion,estado_validacion,validation_id)
 SELECT p.Fecha,{columns('p')},1,@run_id,@caso_id,@version_reglas,SYSUTCDATETIME(),0,N'M6_PENDING',
 N'Insercion pendiente M6; no oficial',NULL,NULL,'PENDIENTE',NULL FROM {STAGE} p WHERE p.run_id=@run_id;
 SELECT @old_hash=payload_sha256 FROM ({hash_select(VERSIONS,'WHERE p.run_id=@run_id')}) h;
 IF @old_hash<>@hash OR (SELECT COUNT(*) FROM {VERSIONS} WHERE run_id=@run_id)<>7
  THROW 52870,'La copia de47campos no conserva el payload.',1;
 IF @own=1 COMMIT;
 SELECT @run_id run_id,7 rows_in_batch,7 rows_inserted,CAST(0 AS bit) idempotent;
 END TRY BEGIN CATCH
  IF @own=1 AND XACT_STATE()<>0 ROLLBACK;
  THROW;
 END CATCH;
END'''

TABLE_DEFINITION=f'''CREATE TABLE {LOT}(
 run_id uniqueidentifier NOT NULL CONSTRAINT PK_rep_prod_m6_pending_lote PRIMARY KEY,
 caso_namespace nvarchar(128) NOT NULL,caso_id int NOT NULL,modelo_id int NOT NULL,
 modelo_codigo varchar(64) NOT NULL,legacy_modelo_id int NOT NULL,solver_run_id int NOT NULL,
 fecha_inicio date NOT NULL,fecha_fin date NOT NULL,cantidad_dias int NOT NULL,
 version_reglas int NOT NULL,payload_sha256 binary(32) NOT NULL,
 payload_canon_version varchar(32) NOT NULL CONSTRAINT DF_rep_prod_m6_pending_canon DEFAULT 'M6_PENDING_47_V1',
 estado_lote varchar(20) NOT NULL,
 usuario nvarchar(128) NOT NULL,sql_principal nvarchar(128) NOT NULL,
 created_utc datetime2(7) NOT NULL CONSTRAINT DF_rep_prod_m6_pending_lote_utc DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_rep_prod_m6_pending_scope CHECK(caso_namespace=N'DEV_SIIR.hidro.recon_caso' AND caso_id=10009
 AND modelo_id=2 AND modelo_codigo='hidrometalurgia_125_v2' AND legacy_modelo_id=6 AND solver_run_id=10082
 AND fecha_inicio=CONVERT(date,'20260901',112) AND fecha_fin=CONVERT(date,'20260907',112)
 AND cantidad_dias=7 AND version_reglas=1 AND payload_canon_version='M6_PENDING_47_V1' AND estado_lote='PENDIENTE'))'''

def definitions():
 return {GUARD:GUARD_DEFINITION,IMMUTABLE:IMMUTABLE_DEFINITION,PROC:proc_definition()}
def installation_script():
 statements=[TABLE_DEFINITION]+list(definitions().values())
 escaped=['EXEC sys.sp_executesql N\''+s.replace("'","''")+"';" for s in statements]
 return """-- PROPUESTA: no ejecutar antes de respaldo recuperable/verificado y pruebas.
:ON ERROR EXIT
:setvar ApproveM6PendingDEV "0"
SET NOCOUNT ON;SET XACT_ABORT ON;
SET ANSI_NULLS ON;SET QUOTED_IDENTIFIER ON;SET ANSI_PADDING ON;SET ANSI_WARNINGS ON;
SET ARITHABORT ON;SET CONCAT_NULL_YIELDS_NULL ON;SET NUMERIC_ROUNDABORT OFF;
IF '$(ApproveM6PendingDEV)'<>'1' THROW 52870,'Instalacion no autorizada.',1;
IF DB_NAME()<>N'inventar_SpcHidr' OR LOWER(CONVERT(nvarchar(128),SERVERPROPERTY('ServerName')))<>N'vps-5347319-x'
 THROW 52870,'Instalacion solo en DEV registrado.',1;
IF OBJECT_ID(N'inventar_SpcHidr.rep_prod_m6_pending_lote') IS NOT NULL THROW 52870,'No sobrescribir instalacion previa.',1;
BEGIN TRY BEGIN TRAN;
"""+'\n'.join(escaped)+"\nCOMMIT;END TRY BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK;THROW;END CATCH;\n"
