"""Lectura V2 aislada y administración append-only; nunca modifica señales base."""
from contextlib import contextmanager
from datetime import date,datetime
from decimal import Decimal
import hashlib,json,uuid
import auth
from flask import has_request_context,session,request
from sqlalchemy import text
from .db import _connection
from . import phase_flags
from .phase_model import ADMIN_PHASES,REASONS,MODEL_VERSION,alert_level
SOURCE='inventar_SpcHidr.fn_estado_operacional_parcela_v2'
DECISIONS='inventar_SpcHidr.estado_operacional_parcela_override'
EVENTS='inventar_SpcHidr.estado_operacional_parcela_override_evento'
class ConflictError(ValueError):pass

def encode(v):
    if isinstance(v,(date,datetime)):return v.isoformat()
    if isinstance(v,Decimal):return str(v)
    raise TypeError(type(v).__name__)
def dump(v):return json.dumps(v,default=encode,ensure_ascii=False,sort_keys=True,separators=(',',':'))
def clean(row):
    row=dict(row)
    row['riego_activo']=row['riego_activo_v2']
    if not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):
        row.update(fase_final=row['fase_calculada_modelo'],origen_fase_final='AUTOMATICO',fase_administrativa=None,
                   override_id=None,override_status=None,motivo_revision_administrativa=None,
                   override_desde=None,fecha_hasta_declarada=None,usuario_creacion=None,fecha_creacion=None,motivo_texto=None,observacion=None,
                   revision_requerida=int(row['motivo_revision_modelo'] is not None),motivo_revision=row['motivo_revision_modelo'])
        row['nivel_alerta']=alert_level(row['pad_id'],row['fase_final'],row['dias_sin_riego_confirmados'],row['riego_activo'])
    if not phase_flags.enabled('ENABLE_PHASE_ALERTS'):row['nivel_alerta']='SIN_ALERTA'
    return row

def snapshot(day):
    from .map_db import validate_snapshot
    day=date.fromisoformat(str(day)[:10])
    with _connection() as conn:
        phase_flags.guard_connection(conn)
        rows=[clean(r) for r in conn.execute(text(f'SELECT * FROM {SOURCE}(:fecha)'),{'fecha':day}).mappings()]
    return validate_snapshot(rows,day.isoformat())


def operational(filters):
    """Serie diaria V2 para Diagnóstico; consulta la TVF vigente sin replicar fases."""
    if filters.get('parcela') is None:
        return None, []
    if not phase_flags.enabled('ENABLE_PHASE_MODEL_V2'):
        raise PermissionError('La evolución operacional requiere el modelo V2 habilitado en DEV.')
    from .db import where, SOURCE as hydraulic_source
    from .phase_model import PHASES
    where(filters)
    start,end=(date.fromisoformat(filters[k][:10]) for k in ('desde','hasta'))
    if (end-start).days>32767:
        raise ValueError('Período operacional excede el calendario disponible.')
    params=dict(desde=start,hasta=end,pad=int(filters['pad']) if filters.get('pad') is not None else None,
                parcela=int(filters['parcela']))
    fields=('fecha','pad_id','parcela_id','numero_parcela','nombre_pad','campana_id','numero_campana',
            'fase_calculada_modelo','fase_final','origen_fase_final','condicion_dia','nivel_alerta',
            'riego_activo_v2','tiene_dato_riego','drenaje_activo','tiene_dato_drenaje','calidad_estado',
            'motivo_revision_modelo','dias_sin_riego_confirmados')
    with _connection() as conn:
        phase_flags.guard_connection(conn)
        rows=[clean(r) for r in conn.execute(text(f'''WITH fechas AS (
            SELECT CAST(:desde AS date) fecha
            UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date)
        ) SELECT {','.join('v.'+field for field in fields)}
        FROM fechas d CROSS APPLY {SOURCE}(d.fecha) v
        WHERE v.parcela_id=:parcela AND (:pad IS NULL OR v.pad_id=:pad)
        ORDER BY v.fecha OPTION(MAXRECURSION 32767,RECOMPILE)'''),params).mappings()]
        hydraulic=[dict(r) for r in conn.execute(text(f'''SELECT fecha,pad_id,parcela_id,
            campana_id campana_hidraulica_id,numero_campana numero_campana_hidraulica,estado_asignacion
            FROM {hydraulic_source} WHERE fecha BETWEEN :desde AND :hasta
            AND parcela_id=:parcela AND (:pad IS NULL OR pad_id=:pad)'''),params).mappings()]
    assignment={}
    for row in hydraulic:
        key=(row['fecha'],row['pad_id'],row['parcela_id'])
        if key in assignment:raise ValueError('Asignación hidráulica duplicada; no se deduplican filas.')
        assignment[key]=row
    seen=set()
    for row in rows:
        if row['fecha'] in seen or not start<=row['fecha']<=end or row['parcela_id']!=params['parcela'] or (params['pad'] is not None and row['pad_id']!=params['pad']):
            raise ValueError('Grano operacional V2 inválido; no se deduplican ni replican fases.')
        if row['fase_final'] not in PHASES or row['fase_final']=='SIN_COBERTURA':
            raise ValueError('Fase estructural V2 no disponible; no se utiliza el modelo anterior.')
        seen.add(row['fecha'])
        metadata=assignment.get((row['fecha'],row['pad_id'],row['parcela_id']),{})
        row.update({field:metadata.get(field) for field in ('campana_hidraulica_id','numero_campana_hidraulica','estado_asignacion')})
    header=next((r for r in rows if r['fecha']==end),None)
    return header,rows

def _row(conn,day,pad,parcel):
    rows=[dict(r) for r in conn.execute(text(f'SELECT * FROM {SOURCE}(:fecha) WHERE pad_id=:pad AND parcela_id=:parcela'),{'fecha':day,'pad':pad,'parcela':parcel}).mappings()]
    if len(rows)!=1:raise ValueError('Identidad operacional no disponible o ambigua.')
    return rows[0]

def _revision(conn,pad,parcel,campaign,lock=False):
    hint=' WITH(UPDLOCK,HOLDLOCK)' if lock else ''
    records=[dict(r) for r in conn.execute(text(f'SELECT id_override,version,familia_override_id FROM {DECISIONS}{hint} WHERE pad_id=:pad AND parcela_id=:parcela AND campana_id=:campana ORDER BY id_override'),{'pad':pad,'parcela':parcel,'campana':campaign}).mappings()]
    latest=records[-1] if records else None
    event=conn.execute(text(f'SELECT COALESCE(MAX(e.id_evento),0) FROM {EVENTS} e JOIN {DECISIONS} o ON o.id_override=e.id_override WHERE o.pad_id=:pad AND o.parcela_id=:parcela AND o.campana_id=:campana'),{'pad':pad,'parcela':parcel,'campana':campaign}).scalar_one()
    return {'decision':latest['id_override'] if latest else 0,'evento':event},latest

def _fingerprint(row,revision):
    evidence={k:v for k,v in row.items() if k not in ('fecha_creacion',)}
    return hashlib.sha256(dump({'evidencia':evidence,'revision':revision}).encode()).hexdigest()

def preview(day,pad,parcel):
    if not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):raise PermissionError('Las confirmaciones están deshabilitadas.')
    day=date.fromisoformat(str(day)[:10]);pad,parcel=int(pad),int(parcel)
    with _connection() as conn:
        phase_flags.guard_connection(conn);row=_row(conn,day,pad,parcel)
        rev,_=_revision(conn,pad,parcel,row['campana_id'])
    return {'row':row,'revision':rev,'context_token':_fingerprint(row,rev)}

def history(pad,parcel,campaign):
    if not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):return [],[]
    params={'pad':int(pad),'parcela':int(parcel),'campana':int(campaign)}
    with _connection() as conn:
        phase_flags.guard_connection(conn)
        rows=[dict(r) for r in conn.execute(text(f'SELECT * FROM {DECISIONS} WHERE pad_id=:pad AND parcela_id=:parcela AND campana_id=:campana ORDER BY id_override'),params).mappings()]
        events=[dict(r) for r in conn.execute(text(f'SELECT e.* FROM {EVENTS} e JOIN {DECISIONS} o ON o.id_override=e.id_override WHERE o.pad_id=:pad AND o.parcela_id=:parcela AND o.campana_id=:campana ORDER BY e.id_evento'),params).mappings()]
    return rows,events

def _actor():
    if not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_WRITE') or not phase_flags.enabled('ENABLE_PHASE_MODEL_V2') or not phase_flags.enabled('ENABLE_OPERATIONAL_PHASE_OVERRIDES_READ'):
        raise PermissionError('La escritura de confirmaciones está deshabilitada.')
    if not has_request_context() or not isinstance(session.get('user'),str) or not session['user'].strip():
        raise PermissionError('Se requiere una sesión autenticada.')
    if request.method!='POST':raise PermissionError('Las confirmaciones requieren una solicitud de registro.')
    # Dash publica JSON en el mismo origen; también se valida cualquier Origin recibido.
    origin=request.headers.get('Origin')
    if origin and origin.rstrip('/')!=request.host_url.rstrip('/'):
        raise PermissionError('Origen de solicitud no autorizado.')
    actor=session['user'].strip()
    if len(actor)>150:raise ValueError('Identidad de usuario inválida.')
    if not auth.user_can_write_operational_decisions(actor):
        raise PermissionError('Se requiere un usuario activo con permiso para registrar decisiones operacionales.')
    return actor


def administrative_context(row, revision):
    """Precondiciones administrativas, sin inferir ni cambiar una fase."""
    active = bool(row.get('override_id') and revision.get('decision') == row.get('override_id')
                  and row.get('override_status') in ('VIGENTE','CONTRADICHO','APARTADO_ESTRUCTURA'))
    return {'compatible': row.get('consolidacion_modulos') == 'UNANIME'
            and row.get('estructura_unica') == 'DISPONIBLE' and row.get('retiro_fisico') == 0,
            'active': active, 'contradiction': active and row.get('override_status') == 'CONTRADICHO'}

@contextmanager
def _transaction():
    with _connection() as conn:
        with conn.begin():
            phase_flags.guard_connection(conn)
            yield conn

def _event(conn,oid,kind,actor,effective,before,after,motive,evidence,correlation,key=None):
    conn.execute(text(f'''INSERT {EVENTS}(id_override,tipo_evento,actor,fecha_efectiva,antes_json,despues_json,motivo,evidencia_json,correlation_id,idempotency_key)
    VALUES(:oid,:kind,:actor,:effective,:before,:after,:motive,:evidence,:correlation,:key)'''),
    dict(oid=oid,kind=kind,actor=actor,effective=effective,before=dump(before) if before is not None else None,
         after=dump(after) if after is not None else None,motive=motive,evidence=dump(evidence),correlation=correlation,key=key))

def decide(payload):
    """Un solo punto de escritura, con identidad/scope/evidencia revalidados en servidor."""
    actor=_actor()
    action=payload.get('accion')
    if action not in ('CONFIRMAR','RECTIFICAR','CERRAR','RESOLVER_CONTRADICCION','ANULAR'):
        raise ValueError('Acción no válida.')
    phase=payload.get('fase')
    if action not in ('CERRAR','ANULAR') and phase not in ADMIN_PHASES:raise ValueError('Seleccione una fase administrable.')
    reason=payload.get('motivo_codigo');motive=str(payload.get('motivo_texto') or '').strip()
    if reason not in REASONS or not motive or len(motive)>1000:raise ValueError('Seleccione un motivo y escriba su justificación.')
    observation=str(payload.get('observacion') or '').strip()
    if len(observation)>2000:raise ValueError('La observación excede el tamaño permitido.')
    effective=date.fromisoformat(str(payload.get('fecha_desde'))[:10])
    from zoneinfo import ZoneInfo
    today=datetime.now(ZoneInfo('America/Santiago')).date()
    if effective>today:raise ValueError('La fecha efectiva no puede ser futura.')
    end=date.fromisoformat(payload['fecha_hasta']) if payload.get('fecha_hasta') else None
    if end and end<effective:raise ValueError('El término debe ser posterior o igual al inicio.')
    pad,parcel,campaign=(int(payload[k]) for k in ('pad_id','parcela_id','campana_id'))
    key=str(uuid.UUID(str(payload.get('idempotency_key'))));correlation=str(uuid.uuid4())
    request_hash=hashlib.sha256(dump({k:v for k,v in payload.items() if k not in ('context_token','revision')}|{'actor':actor}).encode()).hexdigest()
    with _transaction() as conn:
        rev,latest=_revision(conn,pad,parcel,campaign,lock=True)
        duplicate=conn.execute(text(f'SELECT id_override,payload_sha256,usuario_creacion FROM {DECISIONS} WHERE idempotency_key=:key'),{'key':key}).mappings().first()
        if duplicate:
            if duplicate['payload_sha256']!=request_hash or duplicate['usuario_creacion']!=actor:raise ConflictError('La clave de reintento ya corresponde a otra solicitud.')
            return {'id_override':duplicate['id_override'],'reintento':True}
        close_dup=conn.execute(text(f'SELECT id_override,evidencia_json,actor FROM {EVENTS} WHERE idempotency_key=:key'),{'key':key}).mappings().first()
        if close_dup:
            if json.loads(close_dup['evidencia_json']).get('payload_sha256')!=request_hash or close_dup['actor']!=actor:raise ConflictError('La clave de reintento ya fue utilizada.')
            return {'id_override':close_dup['id_override'],'reintento':True}
        if rev!=payload.get('revision'):raise ConflictError('La decisión cambió. Actualice la evidencia antes de confirmar.')
        row=_row(conn,effective,pad,parcel)
        if row['campana_id']!=campaign:raise ValueError('La fecha corresponde a otra campaña. La confirmación no puede trasladarse.')
        if _fingerprint(row,rev)!=payload.get('context_token'):raise ConflictError('Las señales cambiaron. Revise la evidencia actualizada.')
        # Se comprueba también el ámbito futuro declarado; nunca cruzar otra campaña.
        next_start=conn.execute(text('''SELECT MIN(fecha_ini_carguio) FROM inventar_SpcHidr.campana_parcela_control
        WHERE pad_id=:pad AND parcela_id=:parcela AND campana_id<>:campana AND fecha_ini_carguio>:fecha'''),{'pad':pad,'parcela':parcel,'campana':campaign,'fecha':effective}).scalar_one()
        if end and next_start and end>=next_start:raise ValueError('El período atraviesa una nueva campaña.')
        if action not in ('CERRAR','ANULAR') and (row['consolidacion_modulos']!='UNANIME' or row['estructura_unica']!='DISPONIBLE' or row['retiro_fisico']==1):
            raise ValueError('Los hitos físicos o la mezcla de módulos impiden una confirmación hidráulica.')
        if row['override_status']=='CONFLICTO_OVERRIDE':raise ConflictError('Hay confirmaciones en conflicto; se requiere revisión.')
        prior_id=int(payload.get('override_id') or 0)
        if action in ('RECTIFICAR','CERRAR','ANULAR','RESOLVER_CONTRADICCION'):
            if not latest or prior_id!=latest['id_override']:raise ConflictError('Seleccione la versión más reciente para esta acción.')
            if not administrative_context(row,rev)['active']:
                raise ValueError('No existe una confirmación abierta para esta acción.')
        if action=='RESOLVER_CONTRADICCION' and not administrative_context(row,rev)['contradiction']:
            raise ValueError('No hay una contradicción vigente para la fecha efectiva.')
        evidence={'snapshot':row,'revision':rev,'payload_sha256':request_hash,'referencia_usuario':str(payload.get('referencia') or '')[:1000]}
        if latest and row['override_status']=='CONTRADICHO':
            exists=conn.execute(text(f"SELECT COUNT(*) FROM {EVENTS} WHERE id_override=:oid AND tipo_evento='CONTRADICCION_DETECTADA'"),{'oid':latest['id_override']}).scalar_one()
            if not exists:_event(conn,latest['id_override'],'CONTRADICCION_DETECTADA',actor,effective,None,row,motive,evidence,correlation)
        if latest and row['override_status']=='CERRADO_HITO':
            exists=conn.execute(text(f"SELECT COUNT(*) FROM {EVENTS} WHERE id_override=:oid AND tipo_evento='CIERRE_HITO'"),{'oid':latest['id_override']}).scalar_one()
            if not exists:_event(conn,latest['id_override'],'CIERRE_HITO',actor,row.get('inicio_retiro') or effective,None,row,motive,evidence,correlation)
        if action in ('CERRAR','ANULAR'):
            _event(conn,prior_id,'CIERRE_MANUAL' if action=='CERRAR' else 'ANULACION',actor,effective,row,None,motive,evidence,correlation,key)
            return {'id_override':prior_id,'cerrado':True}
        family=str(latest['familia_override_id']) if latest else str(uuid.uuid4())
        version=latest['version']+1 if latest else 1
        params=dict(familia_override_id=family,version=version,supersede_override_id=latest['id_override'] if latest else None,
                    pad_id=pad,parcela_id=parcel,parcela_numero=row['numero_parcela'],campana_id=campaign,numero_campana=row['numero_campana'],
                    fecha_desde=effective,fecha_hasta_declarada=end,fase_calculada_al_confirmar=row['fase_calculada_modelo'],
                    fase_final_previa=row['fase_final'],fase_administrativa=phase,accion=action,motivo_codigo=reason,motivo_texto=motive,
                    observacion=observation or None,condicion_al_confirmar=row['condicion_dia'],nivel_alerta_al_confirmar=row['nivel_alerta'],
                    dias_sin_riego_al_confirmar=row['dias_sin_riego_confirmados'],ultimo_riego_al_confirmar=row['fecha_ultimo_riego_real'],
                    caudal_al_confirmar=row['caudal_operacional'],ultima_ley_cu_pp_al_confirmar=row['valor_ultima_ley_cu_pp'],
                    fecha_ultima_ley_cu_pp_al_confirmar=row['fecha_ultima_ley_cu_pp'],
                    fecha_fin_drenaje_referencia=row['fecha_ultima_ley_cu_pp'] if phase=='ESPERA_RECLAMO' else None,
                    fuente_ultima_ley_cu_pp=row['fuente_cu_pp'],snapshot_evidencia_json=dump(evidence),usuario_creacion=actor,
                    idempotency_key=key,payload_sha256=request_hash,version_reglas=MODEL_VERSION)
        cols=','.join(params);values=','.join(':'+k for k in params)
        oid=conn.execute(text(f'INSERT {DECISIONS}({cols}) OUTPUT inserted.id_override VALUES({values})'),params).scalar_one()
        if latest:_event(conn,latest['id_override'],'DECISION_SUSTITUIDA',actor,effective,row,{'id_override':oid},motive,evidence,correlation)
        kind='DECISION_RECTIFICADA' if action=='RECTIFICAR' else 'DECISION_CREADA'
        _event(conn,oid,kind,actor,effective,row,params,motive,evidence,correlation)
        if action=='RESOLVER_CONTRADICCION':_event(conn,oid,'CONTRADICCION_RESUELTA',actor,effective,row,params,motive,evidence,correlation)
        return {'id_override':oid,'version':version,'reintento':False}
