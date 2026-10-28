"""Ruta opt-in para siete versiones PENDIENTE M6 en DEV; no cambia rutas legacy.

Preparar es puro. execute_pending exige evidencias de respaldo y protección previas.
Nunca llama al MERGE/cache, Set/ClearActiveRun ni publicación oficial.
"""
from dataclasses import dataclass
from datetime import date,datetime,timezone
import hashlib,json,math,uuid
import pandas as pd
from sqlalchemy import text
from . import m6_pending_sql as sql
from .rep_prod_adjuster import prepare_ajuste_m6_125

FIELDS=sql.FIELDS
CONTEXT={'caso_id':10009,'modelo_id':2,'solver_run_id':10082,'modelo_codigo':'hidrometalurgia_125_v2',
         'legacy_modelo_id':6,'total_flujos':125}
EXPECTED={'F08F09_MASA':77148.856848,'F08F09_FCU':312.067403,'F14F15_MASA':269177.274180,'F14F15_FCU':1558.784652}

class PendingGateError(ValueError):pass

def require(ok,message):
    if not ok:raise PendingGateError(message)

def validate_context(context):
    require(all(context.get(k)==v for k,v in CONTEXT.items()),'Solo caso10009/modelo2/solver10082 de125flujos.')
    require(str(context['fecha_inicio'])[:10]=='2026-09-01' and str(context['fecha_fin'])[:10]=='2026-09-07',
            'Periodo permitido:01..07/09/2026.')

def payload_records(frame):
    require(set(['Fecha',*FIELDS]).issubset(frame.columns),'Falta alguna de las47 columnas o Fecha.')
    require(not frame.columns.duplicated().any(),'Columnas duplicadas.')
    records=[]
    for _,row in frame.iterrows():
        item={}
        require(pd.notna(row['Fecha']),'FechaNULL.')
        item['Fecha']=date.fromisoformat(str(row['Fecha'])[:10]).isoformat()
        for name in FIELDS:
            value=row[name];kind=sql.TYPES[name]
            if pd.isna(value):value=None
            elif kind=='int':
                require(not isinstance(value,bool) and float(value).is_integer() and -(2**31)<=int(value)<2**31,'Entero no representable: '+name)
                value=int(value)
            elif kind.startswith('float'):
                require(not isinstance(value,bool) and math.isfinite(float(value)),'Float no finito: '+name)
                value=float(value)
            else:
                require(isinstance(value,str) and len(value.encode('utf-16le'))<=510,'Texto inválido/demasiado largo: '+name)
            item[name]=value
        records.append(item)
    records.sort(key=lambda r:r['Fecha'])
    require([r['Fecha'] for r in records]==[f'2026-09-{d:02d}' for d in range(1,8)],'Se requieren siete fechas completas y únicas.')
    return records

def serialize_payload(records):
    return json.dumps(records,ensure_ascii=False,allow_nan=False,separators=(',',':'))

def compare_payload(expected,actual):
    """Igualdad exacta de los47campos tipados y NULL, sin tolerancia de floats."""
    left=payload_records(pd.DataFrame(expected));right=payload_records(pd.DataFrame(actual))
    require(left==right,'Las47columnas/NULL de lectura no coinciden exactamente con el payload.')
    return True

def prepare_pending(results,catalog,context,daily,rules,*,run_id=None):
    validate_context(context)
    run=str(uuid.UUID(str(run_id))) if run_id is not None else str(uuid.uuid4())
    result=prepare_ajuste_m6_125(results,catalog,context,daily,rules,adjustment_run_id=run)
    require(result['persistido'] is False and result['publicable'] is False,'El preparador debe permanecer puro/no publicable.')
    require(set(result['columnas_ajustadas'])==set(sql.CONTRACT['adjusted']) and set(result['columnas_heredadas'])==set(sql.CONTRACT['inherited']),
            'Contrato19ajustadas/28heredadas diferente.')
    for key,value in EXPECTED.items():
        require(math.isclose(result['targets'][key],value,rel_tol=1e-12,abs_tol=1e-8),'Objetivo distinto del caso autorizado: '+key)
    diagnostic=next(d for d in result['diagnosticos'] if d['codigo']=='CONTRASTE_BRUTO_ASIGNADO')
    require(math.isclose(diagnostic['diferencia_masa'],0.043440,rel_tol=1e-12,abs_tol=1e-8),'Contraste F16/17 vsF18/19 cambió.')
    records=payload_records(result['datos'])
    return {'run_id':run,'context':dict(context),'version_reglas':1,'records':records,
            'payload_json':serialize_payload(records),'preparador':result,'publicable':False,'persistido':False}

def _records(conn,query,params=None):
    return [dict(r) for r in conn.execute(text(query),params or {}).mappings()]

def _guard_dev(conn):
    from lixiviacion.phase_flags import guard_connection
    guard_connection(conn)
    row=_records(conn,"SELECT DB_NAME() db,CAST(SERVERPROPERTY('ServerName') AS nvarchar(128)) server_name")[0]
    require(row['db']=='inventar_SpcHidr' and row['server_name'].lower()=='vps-5347319-x','La identidad DEV no coincide.')
    return row

def load_prepare(conn,*,caso_id,modelo_id,solver_run_id,run_id=None):
    """Solo SELECT y preparador puro; SELECTHOLDLOCK mantiene snapshot en la transacción."""
    require((caso_id,modelo_id,solver_run_id)==(10009,2,10082),'Seleccionar caso/modelo/solver explícitos autorizados.')
    _guard_dev(conn)
    contexts=_records(conn,"""SELECT c.id caso_id,c.modelo_id,c.fecha_inicio,c.fecha_fin,
        r.id solver_run_id,r.caso_id run_caso_id,r.estado estado_run,m.codigo modelo_codigo,m.total_flujos,m.legacy_modelo_id
        FROM DEV_SIIR.hidro.recon_caso c WITH(HOLDLOCK)
        JOIN DEV_SIIR.hidro.recon_solver_run r WITH(HOLDLOCK) ON r.caso_id=c.id AND r.id=:solver
        JOIN DEV_SIIR.hidro.recon_modelo m WITH(HOLDLOCK) ON m.id=c.modelo_id
        WHERE c.id=:caso AND c.modelo_id=:modelo""",{'caso':caso_id,'modelo':modelo_id,'solver':solver_run_id})
    require(len(contexts)==1,'Origen reconciliado inexistente/ambiguo.')
    context=contexts[0];validate_context(context)
    results=pd.DataFrame(_records(conn,"""SELECT codigo_flujo,caso_id,run_id,flujo_modelo_id,masa_reconciliada,fino_cu_reconciliado
        FROM DEV_SIIR.hidro.recon_resultado_flujo WITH(HOLDLOCK) WHERE caso_id=:caso AND run_id=:solver""",{'caso':caso_id,'solver':solver_run_id}))
    catalog=pd.DataFrame(_records(conn,"""SELECT id,modelo_id,codigo_flujo,activo FROM DEV_SIIR.hidro.recon_flujo_modelo WITH(HOLDLOCK)
        WHERE modelo_id=:modelo ORDER BY orden_solver""",{'modelo':modelo_id}))
    daily=pd.DataFrame(_records(conn,"SELECT * FROM inventar_SpcHidr.Datos_conciliados_of WITH(HOLDLOCK) WHERE Fecha BETWEEN '20260901' AND '20260907' ORDER BY Fecha"))
    rules=pd.DataFrame(_records(conn,"""SELECT regla_id,col_nombre,orden_calculo,tipo_regla,target_code,formula_py,depende_de,params_json
        FROM inventar_SpcHidr.rep_prod_reglas WITH(HOLDLOCK) WHERE activo=1 AND reporte_nombre='reporte_prod' ORDER BY orden_calculo,regla_id"""))
    return prepare_pending(results,catalog,context,daily,rules,run_id=run_id)

@dataclass(frozen=True)
class ExecutionEvidence:
    execute_dev:bool=False
    actor:str=''
    server_name:str=''
    database_name:str=''
    backup_verified_recoverable:bool=False
    backup_reference:str=''
    backup_sha256:str=''
    protection_overlap_test_passed:bool=False
    protection_test_reference:str=''
    consumers_review_passed:bool=False
    baseline_sha256:str=''

    def validate(self):
        require(self.execute_dev is True,'Sin autorización explícita de ejecución DEV.')
        require(isinstance(self.actor,str) and 0<len(self.actor.strip())<=128,'Falta usuario operador autenticado/autorizado.')
        require(self.database_name=='inventar_SpcHidr' and self.server_name.lower()=='vps-5347319-x','Evidencia de otro servidor/base.')
        require(self.backup_verified_recoverable is True and bool(self.backup_reference),'Respaldo recuperable/verificado no acreditado.')
        for h in (self.backup_sha256,self.baseline_sha256):
            require(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h),'Falta huella verificable de respaldo/baseline.')
        require(self.protection_overlap_test_passed is True and bool(self.protection_test_reference),'Protección M6 y solapamiento legacy no probados.')
        require(self.consumers_review_passed is True,'Consumidores oficiales no revisados.')

def history_digest(records):
    # Solo para baseline local de la misma versión de cliente, no sustituye hashSQL47.
    def normalized(v):
        if isinstance(v,(date,datetime)):return v.isoformat()
        if isinstance(v,uuid.UUID):return str(v).lower()
        return str(v)
    rows=[{k:(str(v).lower() if k=='run_id' and v is not None else v) for k,v in r.items()} for r in records]
    return hashlib.sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False,separators=(',',':'),default=normalized).encode('utf8')).hexdigest()

def check_installed_contract(conn):
    for name,definition in sql.definitions().items():
        rows=_records(conn,"SELECT OBJECT_DEFINITION(OBJECT_ID(:name)) definition",{'name':name})
        require(len(rows)==1 and rows[0]['definition'] is not None,'Objeto ausente o definición no visible: '+name)
        require(rows[0]['definition']==definition,'Definición instalada distinta del paquete: '+name)
    triggers=_records(conn,"SELECT name,is_disabled FROM sys.triggers WHERE object_id IN(OBJECT_ID(:g),OBJECT_ID(:i))",{'g':sql.GUARD,'i':sql.IMMUTABLE})
    require(len(triggers)==2 and all(not r['is_disabled'] for r in triggers),'Protecciones deshabilitadas/ausentes.')
    actual=_records(conn,"""SELECT o.name tabla,c.name columna,t.name tipo,c.max_length,c.precision,c.scale
        FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id JOIN sys.columns c ON c.object_id=o.object_id
        JOIN sys.types t ON t.user_type_id=c.user_type_id WHERE s.name='inventar_SpcHidr'
        AND o.name IN('rep_prod_ajustado_stg','Datos_conciliados_of_ver','Datos_conciliados_of')""")
    by={(r['tabla'],r['columna']):r for r in actual}
    for table in ('rep_prod_ajustado_stg','Datos_conciliados_of_ver','Datos_conciliados_of'):
        for c in sql.COLUMNS:
            r=by.get((table,c['name']));kind=c['type']
            require(r is not None and r['tipo']==kind.split('(')[0],'Contrato SQL47 diferente: '+table+'.'+c['name'])
            if kind.startswith('nvarchar'):require(r['max_length']==510,'LongitudSQL diferente.')
            if kind.startswith('float'):require(r['precision']==53,'PrecisiónSQL diferente.')

def execute_pending(engine,prepared,*,evidence:ExecutionEvidence):
    """Único punto de escritura opt-in. Todo staging+registro+pendientes es atómico.

    Las evidencias se emiten/revisan fuera de esta API por el operador autorizado;
    no convertir true en prueba de backup ni ejecutar instalación automáticamente.
    """
    evidence.validate()  # Antes de conectar o intentar instalar/escribir.
    require(prepared.get('version_reglas')==1 and prepared.get('publicable') is False,'Contrato de preparación inválido.')
    run=str(uuid.UUID(prepared['run_id']));validate_context(prepared['context'])
    require(serialize_payload(payload_records(pd.DataFrame(prepared['records'])))==prepared['payload_json'],'Payload preparado fue alterado.')
    with engine.connect().execution_options(isolation_level='SERIALIZABLE') as conn:
        with conn.begin():
            identity=_guard_dev(conn);check_installed_contract(conn)
            before=_records(conn,'SELECT * FROM '+sql.VERSIONS+' ORDER BY run_id,Fecha')
            require(history_digest([r for r in before if str(r['run_id']).lower()!=run.lower()])==evidence.baseline_sha256,
                    'El histórico ajeno al UUID cambió desde la evidencia revisada.')
            reader_before=_records(conn,'SELECT * FROM inventar_SpcHidr.vw_datos_conciliados_reporte ORDER BY Fecha')
            # En un retry el source puede haber avanzado: el UUID ya insertado usa su snapshot
            # previo, pero se verifica contenido exacto, origen y ambos destinos en el SP.
            existing=_records(conn,'SELECT run_id FROM '+sql.LOT+' WHERE run_id=:run',{'run':run})
            if not existing:
                current=load_prepare(conn,caso_id=10009,modelo_id=2,solver_run_id=10082,run_id=run)
                compare_payload(prepared['records'],current['records'])
            fingerprint=conn.execute(text(sql.HASH_JSON_SQL),{'payload_json':prepared['payload_json']}).scalar_one()
            conn.execute(text("EXEC sys.sp_set_session_context @key=N'm6_pending_execute_dev',@value=1"))
            try:
                params=dict(run=run,caso=10009,modelo=2,solver=10082,reglas=1,payload=prepared['payload_json'],hash=bytes(fingerprint),usuario=evidence.actor.strip())
                receipt=_records(conn,f'''EXEC {sql.PROC} @run_id=:run,@caso_id=:caso,@modelo_id=:modelo,@solver_run_id=:solver,
                    @version_reglas=:reglas,@payload_json=:payload,@expected_hash=:hash,@usuario=:usuario''',params)
                require(len(receipt)==1,'Falta recibo único de inserción pendiente.')
                stage=_records(conn,'SELECT Fecha,'+sql.columns()+' FROM '+sql.STAGE+' WHERE run_id=:run ORDER BY Fecha',{'run':run})
                versions=_records(conn,'SELECT * FROM '+sql.VERSIONS+' WHERE run_id=:run ORDER BY Fecha',{'run':run})
                compare_payload(prepared['records'],stage);compare_payload(prepared['records'],versions)
                require(all(r['estado_validacion']=='PENDIENTE' and not r['es_activa'] and r['caso_id']==10009 for r in versions),'Estado M6 no pendiente/inactivo.')
                after=_records(conn,'SELECT * FROM '+sql.VERSIONS+' ORDER BY run_id,Fecha')
                retained=[r for r in after if str(r['run_id']).lower()!=run.lower()]
                original=[r for r in before if str(r['run_id']).lower()!=run.lower()]
                require(retained==original and len(after)==len(original)+7,'Se alteró/eliminó histórico o hay filas inesperadas.')
                require(_records(conn,'SELECT * FROM inventar_SpcHidr.vw_datos_conciliados_reporte ORDER BY Fecha')==reader_before,'El consumidor oficial cambió.')
                return {'run_id':run,'rows_inserted':receipt[0]['rows_inserted'],'rows_in_batch':7,'idempotent':bool(receipt[0]['idempotent']),
                        'persistido':True,'publicable':False,'estado_validacion':'PENDIENTE','es_activa':False,
                        'payload_sha256':bytes(fingerprint).hex(),'historico_antes':len(before),'historico_despues':len(after),
                        'servidor':identity['server_name'],'comparacion_47_exacta':True}
            finally:
                # SESSION_CONTEXT sobrevive rollback/pool; limpiar incluso si el SP falla.
                # Si la conexión queda inutilizable, descartar en vez de devolverla al pool.
                try:conn.execute(text("EXEC sys.sp_set_session_context @key=N'm6_pending_execute_dev',@value=NULL"))
                except Exception:conn.invalidate()

def main(argv=None):
    """CLI: preparación de lectura por defecto; escritura solo con --execute-dev/evidencias."""
    import argparse,contextlib,io
    from pathlib import Path
    parser=argparse.ArgumentParser(description='M6 pendiente DEV: no publica ni activa versiones.')
    parser.add_argument('--caso',required=True,type=int);parser.add_argument('--modelo',required=True,type=int)
    parser.add_argument('--solver-run',required=True,type=int);parser.add_argument('--run-id')
    parser.add_argument('--output',required=True,help='JSON de evidencia dentro de auditorias/')
    parser.add_argument('--execute-dev',action='store_true');parser.add_argument('--evidence-json')
    args=parser.parse_args(argv)
    require((args.caso,args.modelo,args.solver_run)==(10009,2,10082),'Contexto no autorizado.')
    root=Path(__file__).resolve().parents[1];output=Path(args.output).resolve()
    require(output.is_relative_to(root/'auditorias'),'La evidencia local debe guardarse en auditorias/.')
    proof=None
    if args.execute_dev:
        require(bool(args.evidence_json),'La escritura requiere evidencias verificadas del operador.')
        proof=ExecutionEvidence(**json.loads(Path(args.evidence_json).read_text(encoding='utf8')))
        proof.validate()
    from db_connection import get_engine
    from env_loader import load_app_env
    from lixiviacion import phase_flags
    load_app_env();require(phase_flags.is_dev(),'Fuera del entornoDEV fijado.')
    with contextlib.redirect_stdout(io.StringIO()):engine=get_engine()
    require(engine is not None,'No hay conexión configuradaDEV.')
    with engine.connect() as conn:
        prepared=load_prepare(conn,caso_id=args.caso,modelo_id=args.modelo,solver_run_id=args.solver_run,run_id=args.run_id)
    if args.execute_dev:result=execute_pending(engine,prepared,evidence=proof)
    else:result={'run_id_solo_local':prepared['run_id'],'persistido':False,'publicable':False,'rows_written':0,
                 'records':prepared['records'],'targets':prepared['preparador']['targets'],'diagnosticos':prepared['preparador']['diagnosticos']}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf8')
    print('Resultado en evidencia local; publicación oficial permanece bloqueada.')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Nunca imprimir Engine/URL, SQL con parámetros ni traceback de credenciales.
        print(str(exc) if isinstance(exc,PendingGateError) else 'Ruta pendiente detenida: '+type(exc).__name__)
        raise SystemExit(2)
