"""Construye rollback de los ocho objetos de expansión V1. Nunca ejecuta SQL."""
import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).parent
OUT=ROOT/'bloqueadores'
DROP=[
 'reclamo.v_diferencia_cv25_contingencia_test',
 'reclamo.v_reclamo_diario_contingencia_test',
 'reclamo.v_preliminar_cv25_con_acumulado_contingencia_test',
 'reclamo.v_preliminar_cv25_contingencia_test',
 'reclamo.v_cv25_diario_contingencia_test',
]
RESTORE=[
 'inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test',
 'inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test',
 'inventar_SpcHidr.v_bd_ton_t12_contingencia_test',
]
def main():
    names=DROP+RESTORE
    assert set(names)=={p.stem for p in (ROOT/'ddl').glob('*.sql')}
    manifest={'alcance':'Ocho objetos de expansión V1: cinco creados y tres modificados. No desinstala fases anteriores del módulo PI/TUM.',
              'ejecutado':False,'objetos':[]}
    sql="""-- ROLLBACK INTEGRAL EXPANSION V1. PREPARADO, NO EJECUTADO.
-- Solo DEV. Conserva tablas de datos y objetos oficiales.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
IF DB_NAME() <> N'inventar_SpcHidr'
 OR CONVERT(nvarchar(128),SERVERPROPERTY('MachineName')) <> N'VPS-5347319-X'
    THROW 51090, 'Rollback permitido exclusivamente en DEV verificado.', 1;
BEGIN TRY
BEGIN TRANSACTION;
"""
    literals=','.join("N'"+n+"'" for n in DROP)
    sql+=f"""-- Bloquear nuevos consumidores fuera de las cinco vistas a retirar.
IF EXISTS (
 SELECT 1 FROM sys.sql_expression_dependencies d
 WHERE OBJECT_SCHEMA_NAME(d.referenced_id)+'.'+OBJECT_NAME(d.referenced_id) IN ({literals})
 AND OBJECT_SCHEMA_NAME(d.referencing_id)+'.'+OBJECT_NAME(d.referencing_id) NOT IN ({literals})
)
 THROW 51091, 'Existen dependencias externas nuevas: revisar antes de rollback.', 1;
"""
    for i,n in enumerate(names,1):
        new=n in DROP
        previous=None if new else ROOT/'backup'/(n+'.sql')
        entry={'orden':i,'objeto':n,'accion':'DROP VIEW' if new else 'RESTORE DEFINITION',
               'existia_antes_v1':not new,'definicion_previa':None if new else str(previous.relative_to(ROOT)),
               'estado_previo':'AUSENTE: creado por desplegar_reclamo_dev.py, que exige OBJECT_ID IS NULL' if new else 'DEFINICION_RESPALDADA',
               'rollback_individual':'rollback_'+n+'.sql',
               'ddl_actual':'ddl/'+n+'.sql'}
        if new:
            body='DROP VIEW '+n+';'
        else:
            original=previous.read_bytes().decode('utf-8').replace('\r\r\n','\n').replace('\r\n','\n')
            body=re.sub(r'\bCREATE\s+(?:OR\s+ALTER\s+)?(VIEW|PROCEDURE)\b',r'ALTER \1',original,count=1,flags=re.I)
            assert re.search(r'\bALTER\s+(VIEW|PROCEDURE)\b',body,re.I)
            entry['sha256_definicion_previa']=hashlib.sha256(previous.read_bytes()).hexdigest()
        manifest['objetos'].append(entry)
        sql+=f'\n-- {i}. {n}\n'
        if new:sql+=f"IF OBJECT_ID(N'{n}',N'V') IS NOT NULL\n"
        sql+="EXEC sys.sp_executesql N'"+body.replace("'","''")+"';\n"
    sql+='COMMIT TRANSACTION;\nEND TRY\nBEGIN CATCH\n IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;\n THROW;\nEND CATCH;\n'
    (OUT/'rollback_integral_v1.sql').write_text(sql,encoding='utf-8')
    manifest['sha256_script']=hashlib.sha256((OUT/'rollback_integral_v1.sql').read_bytes()).hexdigest()
    (OUT/'manifiesto_rollback_v1.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    rows=['# Rollback integral expansión V1','',manifest['alcance'],'',
          'No ejecutado. Orden: retirar consumidores Reclamo antes de su fuente; restaurar Balance y peso teórico antes de la vista de tonelajes que consume este último.',
          '', '|Orden|Objeto|Estado previo|Definición previa / acción|','|---|---|---|---|']
    for e in manifest['objetos']:
        rows.append('|'+ '|'.join([str(e['orden']),e['objeto'],'Ausente' if not e['existia_antes_v1'] else 'Existente',e['definicion_previa'] or 'No había definición; DROP VIEW'])+'|')
    rows+=['','[Script integral](rollback_integral_v1.sql) · [Manifiesto con hashes](manifiesto_rollback_v1.json)',
           '', 'Las definiciones previas a esta corrección de tipos se conservan además en los archivos *.antes.sql. El rollback integral vuelve al estado anterior a expansión V1, no al estado con el defecto float.',
           '', 'La vista v_representatividad_diaria_calculada_contingencia_test tiene un respaldo pero no fue modificada por los DDL de expansión V1; se conserva. Las tablas de acciones, los SP de gestión y el resolvedor operacional son preexistentes a esta expansión y permanecen. No existe evidencia suficiente para reconstruir un rollback de todas las fases anteriores; este manifiesto no lo pretende.',
           '', 'Se bloquean dependencias SQL nuevas externas a las cinco vistas retiradas. Los consumidores externos a SQL (aplicación/reportes) deben volver a apuntar a sus fuentes previas antes de ejecutar. No se ejecutó el script ni se probó su DDL con cambios reales por la restricción expresa del usuario.']
    (OUT/'ROLLBACK.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
if __name__=='__main__':main()
