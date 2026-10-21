"""Construye migración mínima desde el SP DEV respaldado, nunca desde uno histórico."""
import re,json,hashlib
from pathlib import Path
SCHEMA='inventar_SpcHidr'
EQUIPOS=('SRR_CV001','SRR_CV002','SRR_CV003','CHANCADOR_CV006','PRINCIPAL_CV008','PRINCIPAL_CV108')
A=SCHEMA+'.v_contingencia_totalizador_resuelto_turno'
AUTO=SCHEMA+'.v_balance_m6_totalizador_auto_turno'
V=SCHEMA+'.v_balance_m6_totalizador_resuelto_turno'
T=SCHEMA+'.balance_m6_contingencia_decision'
SP=SCHEMA+'.sp_balance_m6_guardar_contingencia'
PREVIEW=SCHEMA+'.sp_balance_m6_preview_contingencia'
AUTO_COLUMNS=('fecha_operacional turno equipo_codigo estado_tecnico_pi estado_fronteras valor_pi_bruto valor_pi_final lectura_inicio_pi lectura_fin_pi delta_frontera_pi ultima_fecha_con_cambio segundos_sin_cambio_al_cierre tonelaje_apoyo fuente_apoyo estado_apoyo tum_disponible tipo_tum lectura_inicio_tum lectura_fin_tum valor_turno_tum total_excel_tum diferencia_inicio_pi_tum diferencia_fin_pi_tum diferencia_tonelaje_pi_tum fuente_resuelta valor_bruto_resuelto valor_final_resuelto motivo_decision tum_batch_id archivo_batch').split()

def alter_definition(source):
    return re.sub(r'\bCREATE\s+(?:OR\s+ALTER\s+)?PROCEDURE\b','ALTER PROCEDURE',source,count=1,flags=re.I)

def build(folder):
    p=Path(folder);source=(p/'sp_m6_antes.sql').read_text(encoding='utf8')
    original_source=source
    already_m6=source.count(V)==2 and A not in source
    if already_m6:source=source.replace(V,A)
    assert source.count(A)==2, 'Se modificó el contrato: revisar las dos referencias'
    # No se admiten invocaciones externas ni persistencia en esta copia de preview.
    assert not re.search(r'\bEXEC(?:UTE)?\s|\bMERGE\s',source,re.I)
    patched=alter_definition(source.replace(A,V))
    (p/'03_alter_m6.sql').write_text('-- El SP vigente ya usa la capa M6: conservar su definición y hash.\n' if already_m6 else patched,encoding='utf8')
    (p/'09_rollback_m6.sql').write_text(alter_definition(original_source),encoding='utf8')
    names=AUTO_COLUMNS
    # Un solo tratamiento TUM: cero válido, umbral exclusivamente principales.
    valid="a.tum_disponible=1 AND a.valor_turno_tum IS NOT NULL AND a.valor_turno_tum>=0"
    tum="CASE WHEN a.equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108') AND a.valor_turno_tum<=100 THEN CONVERT(decimal(28,6),0) ELSE a.valor_turno_tum END"
    replace={
        'fuente_resuelta':f"CASE WHEN d.modo='TUM' THEN CASE WHEN {valid} THEN 'TUM' ELSE 'SIN_RESOLVER' END ELSE a.fuente_resuelta END",
        'valor_bruto_resuelto':f"CASE WHEN d.modo='TUM' THEN CASE WHEN {valid} THEN a.valor_turno_tum END ELSE a.valor_bruto_resuelto END",
        'valor_final_resuelto':f"CASE WHEN d.modo='TUM' THEN CASE WHEN {valid} THEN {tum} END ELSE a.valor_final_resuelto END",
        'motivo_decision':f"CASE WHEN d.modo='TUM' THEN CASE WHEN {valid} THEN 'M6_MANUAL_TUM' ELSE 'M6_PENDIENTE_TUM' END ELSE a.motivo_decision END"}
    select=',\n'.join(f"{replace.get(n,'a.['+n+']')} AS [{n}]" for n in names)
    equipment=','.join("'"+x+"'" for x in EQUIPOS)
    create=f"""-- DEV; sin decisiones iniciales ni modificación de objetos compartidos.
CREATE TABLE {T} (
 id bigint IDENTITY PRIMARY KEY, equipo_codigo varchar(40) NOT NULL,
 fecha_operacional date NOT NULL, turno char(1) NOT NULL, modo varchar(4) NOT NULL,
 version int NOT NULL, motivo nvarchar(500) NOT NULL, comentario nvarchar(1000) NULL,
 usuario nvarchar(255) NOT NULL, fecha_registro datetime2(3) NOT NULL DEFAULT SYSUTCDATETIME(),
 solicitud_id uniqueidentifier NOT NULL, solicitud_hash varbinary(32) NOT NULL,
 CONSTRAINT UQ_m6_decision_version UNIQUE(equipo_codigo,fecha_operacional,turno,version),
 CONSTRAINT UQ_m6_decision_request UNIQUE(solicitud_id,equipo_codigo,fecha_operacional,turno),
 CONSTRAINT CK_m6_decision_equipo CHECK(equipo_codigo IN ({equipment})),
 CONSTRAINT CK_m6_decision_turno CHECK(turno IN ('A','B')),
 CONSTRAINT CK_m6_decision_modo CHECK(modo IN ('AUTO','TUM')),
 CONSTRAINT CK_m6_decision_fecha CHECK(fecha_operacional>='20260901'),
 CONSTRAINT CK_m6_decision_version CHECK(version>0),
 CONSTRAINT CK_m6_decision_usuario CHECK(LEN(LTRIM(RTRIM(usuario)))>0),
 CONSTRAINT CK_m6_decision_motivo CHECK(LEN(LTRIM(RTRIM(motivo)))>0)
);
GO
CREATE VIEW {SCHEMA}.v_balance_m6_contingencia_actual AS
SELECT id,equipo_codigo,fecha_operacional,turno,modo,version,motivo,comentario,usuario,fecha_registro,solicitud_id
FROM (SELECT *,ROW_NUMBER() OVER(PARTITION BY equipo_codigo,fecha_operacional,turno ORDER BY version DESC) rn FROM {T}) x WHERE rn=1;
GO
CREATE VIEW {V} AS
SELECT {select},
 a.fuente_resuelta AS fuente_auto,a.valor_final_resuelto AS valor_auto,
 COALESCE(d.modo,'AUTO') AS modo_m6,COALESCE(d.version,0) AS version_m6,
 d.id AS decision_id_m6,d.motivo AS motivo_m6,d.usuario AS usuario_m6,d.fecha_registro AS fecha_m6,
 CONVERT(varchar(64),HASHBYTES('SHA2_256',CONCAT(CONVERT(char(10),a.fecha_operacional,23),'|',a.turno,'|',a.equipo_codigo,'|',COALESCE(d.version,0),'|',a.valor_pi_final,'|',a.valor_turno_tum,'|',a.tum_disponible,'|',a.fuente_resuelta,'|',a.valor_final_resuelto,'|',a.estado_tecnico_pi,'|',a.estado_fronteras)),2) AS huella_m6
FROM {AUTO} a
LEFT JOIN {SCHEMA}.v_balance_m6_contingencia_actual d ON d.equipo_codigo=a.equipo_codigo AND d.fecha_operacional=a.fecha_operacional AND d.turno=a.turno
WHERE a.equipo_codigo IN ({equipment});
GO
CREATE PROCEDURE {SP}
 @claves nvarchar(max),@solicitud_id uniqueidentifier,@usuario nvarchar(255),@motivo nvarchar(500),@comentario nvarchar(1000)=NULL,@huella_entradas varchar(64)=NULL
AS
BEGIN
 SET NOCOUNT ON; SET XACT_ABORT ON;
 IF DB_NAME()<>'inventar_SpcHidr' THROW 51100,'Solo DEV.',1;
 IF IS_MEMBER('balance_m6_contingencia_operador')<>1 AND IS_MEMBER('db_owner')<>1 AND IS_SRVROLEMEMBER('sysadmin')<>1
   THROW 51101,'Sin permiso de gestión M6.',1;
 IF ISJSON(@claves)<>1 OR LEFT(LTRIM(@claves),1)<>'[' OR @solicitud_id IS NULL OR NULLIF(LTRIM(RTRIM(@usuario)),'') IS NULL OR NULLIF(LTRIM(RTRIM(@motivo)),'') IS NULL
   THROW 51102,'Solicitud, usuario y motivo obligatorios.',1;
 DECLARE @n int=(SELECT COUNT(*) FROM OPENJSON(@claves));
 IF @n<1 OR @n>3000 THROW 51103,'Seleccione entre 1 y 3000 claves.',1;
 SELECT fecha_operacional,turno,equipo_codigo,modo,version_esperada,huella
 INTO #sol FROM OPENJSON(@claves) WITH(fecha_operacional date,turno varchar(10),equipo_codigo varchar(100),modo varchar(10),version_esperada int,huella varchar(100));
 IF EXISTS(SELECT 1 FROM #sol WHERE fecha_operacional IS NULL OR fecha_operacional<'20260901' OR turno IS NULL OR turno NOT IN ('A','B') OR DATALENGTH(turno)<>1 OR equipo_codigo IS NULL OR equipo_codigo NOT IN ({equipment}) OR modo IS NULL OR modo NOT IN ('AUTO','TUM') OR version_esperada IS NULL OR version_esperada<0 OR huella IS NULL OR LEN(huella)<>64)
   THROW 51104,'Clave o modo inválido.',1;
 IF EXISTS(SELECT 1 FROM #sol GROUP BY fecha_operacional,turno,equipo_codigo HAVING COUNT(*)<>1) THROW 51105,'Claves duplicadas.',1;
 DECLARE @desde date=(SELECT MIN(fecha_operacional) FROM #sol),@hasta date=(SELECT MAX(fecha_operacional) FROM #sol);
 DECLARE @hash varbinary(32)=HASHBYTES('SHA2_256',CONCAT(@claves,'|',@usuario,'|',@motivo,'|',@comentario));
 BEGIN TRY
 BEGIN TRAN;
 DECLARE @actual_entradas varchar(64);
 EXEC {SCHEMA}.sp_balance_m6_bloquear_entradas @huella=@actual_entradas OUTPUT,@solo_definiciones=1;
 DECLARE @lock int;
 EXEC @lock=sys.sp_getapplock @Resource='BALANCE_M6_CONTINGENCIA',@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;
 IF @lock<0 THROW 51106,'No se pudo bloquear la decisión M6.',1;
 IF EXISTS(SELECT 1 FROM {T} WHERE solicitud_id=@solicitud_id)
 BEGIN
   IF (SELECT COUNT(*) FROM {T} WHERE solicitud_id=@solicitud_id)<>@n OR EXISTS(SELECT 1 FROM {T} WHERE solicitud_id=@solicitud_id AND solicitud_hash<>@hash)
     THROW 51107,'Identificador reutilizado con otro contenido.',1;
   COMMIT; SELECT @solicitud_id solicitud_id,CAST(1 AS bit) idempotente; RETURN;
 END;
 EXEC {SCHEMA}.sp_balance_m6_bloquear_entradas @huella=@actual_entradas OUTPUT;
 IF @huella_entradas IS NULL OR @huella_entradas<>@actual_entradas THROW 51121,'Preview obsoleto: cambiaron entradas o versiones. Vuelva a previsualizar.',1;
 SELECT v.fecha_operacional,v.turno,v.equipo_codigo,v.version_m6,v.huella_m6,v.tum_disponible,v.valor_turno_tum
 INTO #actual FROM {V} v JOIN #sol s ON s.fecha_operacional=v.fecha_operacional AND s.turno=v.turno AND s.equipo_codigo=v.equipo_codigo
 WHERE v.fecha_operacional BETWEEN @desde AND @hasta OPTION(RECOMPILE);
 IF (SELECT COUNT(*) FROM #actual)<>@n OR EXISTS(SELECT 1 FROM #sol s JOIN #actual a ON a.fecha_operacional=s.fecha_operacional AND a.turno=s.turno AND a.equipo_codigo=s.equipo_codigo WHERE s.version_esperada<>a.version_m6 OR s.huella<>a.huella_m6)
   THROW 51108,'Cambió la fuente o la decisión; vuelva a previsualizar.',1;
 IF EXISTS(SELECT 1 FROM #sol s JOIN #actual a ON a.fecha_operacional=s.fecha_operacional AND a.turno=s.turno AND a.equipo_codigo=s.equipo_codigo WHERE s.modo='TUM' AND (a.tum_disponible<>1 OR a.tum_disponible IS NULL OR a.valor_turno_tum IS NULL OR a.valor_turno_tum<0))
   THROW 51109,'TUM no válido: no se guardó ninguna clave.',1;
 INSERT {T}(equipo_codigo,fecha_operacional,turno,modo,version,motivo,comentario,usuario,solicitud_id,solicitud_hash)
 SELECT equipo_codigo,fecha_operacional,turno,modo,version_esperada+1,@motivo,@comentario,@usuario,@solicitud_id,@hash FROM #sol;
 COMMIT; SELECT @solicitud_id solicitud_id,CAST(0 AS bit) idempotente;
 END TRY
 BEGIN CATCH
   IF XACT_STATE()<>0 ROLLBACK;
   THROW;
 END CATCH;
END;
GO
CREATE ROLE balance_m6_contingencia_operador;
GRANT EXECUTE ON {SP} TO balance_m6_contingencia_operador;
GRANT SELECT ON {V} TO balance_m6_contingencia_operador;
GRANT SELECT ON {T} TO balance_m6_contingencia_operador;
GRANT VIEW DEFINITION ON {SCHEMA}.sp_calcular_balance_flujos_modelo6_v2 TO balance_m6_contingencia_operador;
"""
    (p/'02_crear_capa_m6.sql').write_text(create,encoding='utf8')
    # Copia de cálculo independiente. Las fórmulas son byte a byte las de M6.
    preview=re.sub(r'CREATE\s+PROCEDURE\s+\[inventar_SpcHidr\]\.\[sp_calcular_balance_flujos_modelo6_v2\]', 'CREATE PROCEDURE '+PREVIEW,source,count=1,flags=re.I)
    assert preview!=source
    preview=preview.replace('@debug bit = 0','@debug bit = 0,\n    @selecciones_json nvarchar(max) = N\'[]\',\n    @usar_actual bit = 0,\n    @fuentes_snapshot_json nvarchar(max) = NULL',1)
    init=f"""
    -- Selecciones de preview locales: ninguna escritura persistente.
    IF ISJSON(@selecciones_json)<>1 OR LEFT(LTRIM(@selecciones_json),1)<>'[' THROW 51110,'Preview inválido.',1;
    SELECT a.* INTO #m6_preview_auto FROM {AUTO} a WHERE a.fecha_operacional BETWEEN @fecha_inicio AND @fecha_fin;
    -- Solo reproducibilidad no persistente: la UI habitual no envía snapshots.
    IF @fuentes_snapshot_json IS NOT NULL
    BEGIN
       IF ISJSON(@fuentes_snapshot_json)<>1 THROW 51114,'Snapshot inválido.',1;
       SELECT * INTO #m6_snapshot FROM OPENJSON(@fuentes_snapshot_json) WITH(
          fecha_operacional date,turno varchar(10),equipo_codigo varchar(100),estado_tecnico_pi varchar(80),
          fuente_resuelta varchar(30),valor_bruto_resuelto decimal(28,6),valor_final_resuelto decimal(28,6),motivo_decision varchar(80));
       IF (SELECT COUNT(*) FROM #m6_snapshot)<>(SELECT COUNT(*) FROM #m6_preview_auto)
          OR EXISTS(SELECT 1 FROM #m6_snapshot GROUP BY fecha_operacional,turno,equipo_codigo HAVING COUNT(*)<>1)
          OR EXISTS(SELECT 1 FROM #m6_snapshot s LEFT JOIN #m6_preview_auto a ON a.fecha_operacional=s.fecha_operacional AND a.turno=s.turno AND a.equipo_codigo=s.equipo_codigo WHERE a.equipo_codigo IS NULL)
          THROW 51115,'Snapshot incompleto o con claves distintas del período.',1;
       UPDATE a SET estado_tecnico_pi=s.estado_tecnico_pi,fuente_resuelta=s.fuente_resuelta,
          valor_bruto_resuelto=s.valor_bruto_resuelto,valor_final_resuelto=s.valor_final_resuelto,motivo_decision=s.motivo_decision
       FROM #m6_preview_auto a JOIN #m6_snapshot s ON s.fecha_operacional=a.fecha_operacional AND s.turno=a.turno AND s.equipo_codigo=a.equipo_codigo;
    END;
    SELECT * INTO #m6_preview_fuentes FROM #m6_preview_auto;
    IF @usar_actual=1 AND EXISTS(SELECT 1 FROM {T} WHERE fecha_operacional BETWEEN @fecha_inicio AND @fecha_fin)
       UPDATE a SET fuente_resuelta=CASE WHEN {valid} THEN 'TUM' ELSE 'SIN_RESOLVER' END,
          valor_bruto_resuelto=CASE WHEN {valid} THEN a.valor_turno_tum END,
          valor_final_resuelto=CASE WHEN {valid} THEN {tum} END,
          motivo_decision=CASE WHEN {valid} THEN 'M6_MANUAL_TUM' ELSE 'M6_PENDIENTE_TUM' END
       FROM #m6_preview_fuentes a JOIN {SCHEMA}.v_balance_m6_contingencia_actual d ON d.fecha_operacional=a.fecha_operacional AND d.turno=a.turno AND d.equipo_codigo=a.equipo_codigo WHERE d.modo='TUM';
    SELECT fecha_operacional,turno,equipo_codigo,modo INTO #preview_claves
    FROM OPENJSON(@selecciones_json) WITH(fecha_operacional date,turno varchar(10),equipo_codigo varchar(100),modo varchar(10));
    IF EXISTS(SELECT 1 FROM #preview_claves WHERE fecha_operacional IS NULL OR fecha_operacional NOT BETWEEN @fecha_inicio AND @fecha_fin OR turno IS NULL OR turno NOT IN ('A','B') OR DATALENGTH(turno)<>1 OR equipo_codigo IS NULL OR equipo_codigo NOT IN ({equipment}) OR modo IS NULL OR modo NOT IN ('AUTO','TUM')) THROW 51111,'Clave de preview inválida.',1;
    IF EXISTS(SELECT 1 FROM #preview_claves GROUP BY fecha_operacional,turno,equipo_codigo HAVING COUNT(*)>1) THROW 51112,'Claves duplicadas.',1;
    IF EXISTS(SELECT 1 FROM #preview_claves s LEFT JOIN #m6_preview_fuentes p ON p.fecha_operacional=s.fecha_operacional AND p.turno=s.turno AND p.equipo_codigo=s.equipo_codigo WHERE p.equipo_codigo IS NULL OR (s.modo='TUM' AND (p.tum_disponible<>1 OR p.tum_disponible IS NULL OR p.valor_turno_tum IS NULL OR p.valor_turno_tum<0))) THROW 51113,'TUM ausente o inválido.',1;
    -- AUTO explícito recupera A incluso si hay una decisión vigente TUM.
    UPDATE p SET fuente_resuelta=a.fuente_resuelta,valor_bruto_resuelto=a.valor_bruto_resuelto,valor_final_resuelto=a.valor_final_resuelto,motivo_decision=a.motivo_decision
    FROM #m6_preview_fuentes p JOIN #preview_claves s ON s.fecha_operacional=p.fecha_operacional AND s.turno=p.turno AND s.equipo_codigo=p.equipo_codigo
    JOIN #m6_preview_auto a ON a.fecha_operacional=p.fecha_operacional AND a.turno=p.turno AND a.equipo_codigo=p.equipo_codigo WHERE s.modo='AUTO';
    UPDATE a SET fuente_resuelta='TUM',valor_bruto_resuelto=a.valor_turno_tum,valor_final_resuelto={tum},motivo_decision='M6_PREVIEW_TUM'
    FROM #m6_preview_fuentes a JOIN #preview_claves s ON s.fecha_operacional=a.fecha_operacional AND s.turno=a.turno AND s.equipo_codigo=a.equipo_codigo WHERE s.modo='TUM';
"""
    # Inicializar después de normalizar fechas.
    marker='    DECLARE @ff_mas_1 date ='
    preview=preview.replace(marker,init+'\n'+marker,1)
    # Solo las dos referencias originales de las cargas de fuente.
    # replace en secciones posteriores al inicializador para no alterar lecturas A.
    pos=preview.index(marker)
    preview=preview[:pos]+preview[pos:].replace(A,'#m6_preview_fuentes')
    (p/'04_preview_m6.sql').write_text(preview+'\nGO\nGRANT EXECUTE ON '+PREVIEW+' TO balance_m6_contingencia_operador;\nGRANT VIEW DEFINITION ON '+PREVIEW+' TO balance_m6_contingencia_operador;\n',encoding='utf8')
    drop=f"""-- Ejecutar DESPUÉS de restaurar M6 con 09_rollback_m6.sql.
DROP PROCEDURE {PREVIEW};
DROP PROCEDURE {SP};
DROP VIEW {V};
DROP VIEW {SCHEMA}.v_balance_m6_contingencia_actual;
REVOKE VIEW DEFINITION ON {SCHEMA}.sp_calcular_balance_flujos_modelo6_v2 FROM balance_m6_contingencia_operador;
-- Archivar historial antes de una retirada definitiva. Tabla conservada deliberadamente.
"""
    (p/'09_rollback_capa.sql').write_text(drop,encoding='utf8')
    # Las huellas de dependencias se fijan al inventario DEV validado. Un cambio
    # de definición bloquea operaciones hasta regenerar y validar ese contrato.
    sql_dir=Path(__file__).with_name('sql')
    for asset in ['auto_tecnico.sql','bloquear_entradas.sql']:
        (p/('00_'+asset)).write_text((sql_dir/asset).read_text(encoding='utf8'),encoding='utf8')
    return {'sp_antes_sha256':hashlib.sha256(original_source.encode()).hexdigest(),'cambios_fuente':0 if already_m6 else 2,'contrato_entradas':'Revalidar el inventario de dependencias antes de instalar; los hashes fijados fallan cerrado ante cambios.'}
