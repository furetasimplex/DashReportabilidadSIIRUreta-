"""Persistencia modular DEV independiente; autorizacion backend existente."""
from contextlib import contextmanager
from datetime import date
import json
import uuid
from sqlalchemy import text
from . import phase_db, phase_flags
from . import irrigation_modules_model as model

SCHEMA='inventar_SpcHidr'
REF=SCHEMA+'.parcela_modulos_riego_referencia'
CONF=SCHEMA+'.parcela_modulos_riego_confirmacion'
DETAIL=SCHEMA+'.parcela_modulos_riego_detalle'
EVENT=SCHEMA+'.parcela_modulos_riego_evento'


@contextmanager
def _connection(connection=None):
    if not phase_flags.is_dev():
        raise PermissionError('Módulos en riego está habilitado exclusivamente en DEV.')
    if connection is not None:
        if not connection.in_transaction():
            raise ValueError('La conexión externa debe tener una transacción activa.')
        phase_flags.guard_connection(connection)
        yield connection
    else:
        from db_connection import get_engine
        with get_engine().begin() as conn:
            phase_flags.guard_connection(conn)
            yield conn


def _rows(conn, sql, params=None):
    return [dict(r) for r in conn.execute(text(sql),params or {}).mappings()]


def resolve_roster(fecha, pad_id, parcela_id, *, connection=None):
    scope=model.validate_scope(fecha,pad_id,parcela_id)
    with _connection(connection) as conn:
        return _resolve(conn,*scope)


def _resolve(conn, day, pad, parcel):
    rows=_rows(conn,f'''SELECT * FROM {SCHEMA}.fn_modulos_riego_roster(:day,:pad,:parcel)
        ORDER BY orden_incremental,numero_nombre,control_id_snapshot''',dict(day=day,pad=pad,parcel=parcel))
    return model.roster_context(rows)


def _reference(conn, day, pad, parcel, lock=False):
    hint='UPDLOCK,HOLDLOCK' if lock else 'HOLDLOCK'
    rows=_rows(conn,f'''SELECT * FROM {REF} WITH({hint})
        WHERE fecha_operacional=:day AND pad_id=:pad AND parcela_id=:parcel ORDER BY version DESC''',
        dict(day=day,pad=pad,parcel=parcel))
    return rows[0] if rows else None


def reference_for_day(fecha,pad_id,parcela_id,*,connection=None):
    with _connection(connection) as conn:
        return _reference(conn,*model.validate_scope(fecha,pad_id,parcela_id))


def _snapshot(conn, day, pad, parcel, lock=False):
    roster=_resolve(conn,day,pad,parcel)
    ref=_reference(conn,day,pad,parcel,lock)
    hint='UPDLOCK,HOLDLOCK' if lock else 'HOLDLOCK'
    headers=_rows(conn,f'''SELECT * FROM {CONF} WITH({hint})
        WHERE pad_id=:pad AND parcela_id=:parcel ORDER BY fecha_efectiva DESC,version DESC''',dict(pad=pad,parcel=parcel))
    events=_rows(conn,f'''SELECT e.* FROM {EVENT} e WITH(HOLDLOCK) JOIN {CONF} h WITH(HOLDLOCK)
        ON h.id_confirmacion=e.id_confirmacion_modular WHERE h.pad_id=:pad AND h.parcela_id=:parcel
        ORDER BY e.id_evento''',dict(pad=pad,parcel=parcel))
    resolved=model.resolve_temporal(roster,headers,events)
    path=[]
    if resolved['candidato']:
        start=resolved['temporal']['fecha_origen']
        # La TVF incorpora miembros/campañas en sus fechas de inicio. Revisar todos
        # esos hitos evita heredar a través de un corte intermedio, sin filas diarias.
        boundaries=_rows(conn,f'''SELECT DISTINCT fecha_ini_carguio fecha FROM {SCHEMA}.campana_parcela_control WITH(HOLDLOCK)
            WHERE pad_id=:pad AND parcela_id=:parcel AND fecha_ini_carguio>:start AND fecha_ini_carguio<=:day
            ORDER BY fecha_ini_carguio''',dict(pad=pad,parcel=parcel,start=start,day=day))
        path=[_resolve(conn,date.fromisoformat(start),pad,parcel),
              *[_resolve(conn,r['fecha'],pad,parcel) for r in boundaries]]
        resolved=model.resolve_temporal(roster,headers,events,path)
    active=resolved['vigente'];latest=resolved['punto_fecha'];selected=[]
    if active:
        selected=_rows(conn,f'SELECT * FROM {DETAIL} WHERE id_confirmacion_modular=:id AND seleccionado=1 ORDER BY orden_snapshot',{'id':active['id_confirmacion']})
    reference=None
    if ref:
        reference={k:ref[k] for k in ('id_referencia','version','fuente','estado_referencia','cantidad_modulos_referencia','total_modulos_snapshot','observacion','roster_sha256','payload_sha256')}
        reference['sugeridos']=json.loads(ref['modulos_sugeridos_json']) if ref['modulos_sugeridos_json'] is not None else None
        reference['estructura_actual']=bytes(ref['roster_sha256'])==model.digest(roster['miembros'])
    exact_point=next((p for p in model.temporal_points(headers,events) if latest and p['header']['id_confirmacion']==latest['id_confirmacion']),None)
    revision=dict(id=latest['id_confirmacion'] if latest else None,version=latest['version'] if latest else 0,
                  evento=max((x['id_evento'] for x in events),default=None),
                  cerrada=bool(exact_point and exact_point['cierre']),
                  anulada=bool(exact_point and exact_point['anulacion']))
    # Solo metadata/hash: no anidar payload/contexto de cabeceras históricas.
    timeline=[{k:h[k] for k in ('id_confirmacion','familia_id','fecha_efectiva','campana_id','version','payload_sha256','roster_sha256')} for h in headers]
    event_context=[{k:e[k] for k in ('id_evento','id_confirmacion_modular','tipo_evento','fecha_efectiva','payload_sha256')} for e in events]
    context=dict(roster=roster,referencia=reference,revision=revision,canon=model.CANON_VERSION,
        temporal_version=model.TEMPORAL_VERSION,linea=timeline,eventos=event_context,estructura_intermedia=path)
    return dict(roster=roster,referencia=reference,revision=revision,context_token=model.digest(context).hex(),
                contexto=context,seleccion=selected,**resolved)


def modular_snapshot(fecha,pad_id,parcela_id,*,connection=None):
    with _connection(connection) as conn:
        return _snapshot(conn,*model.validate_scope(fecha,pad_id,parcela_id))


def modular_history(fecha,pad_id,parcela_id,*,connection=None):
    day,pad,parcel=model.validate_scope(fecha,pad_id,parcela_id)
    with _connection(connection) as conn:
        headers=_rows(conn,f'''SELECT * FROM {CONF}
            WHERE pad_id=:pad AND parcela_id=:parcel ORDER BY fecha_efectiva DESC,version DESC''',
            dict(pad=pad,parcel=parcel))
        for row in headers:
            row['detalle']=_rows(conn,f'SELECT * FROM {DETAIL} WHERE id_confirmacion_modular=:id ORDER BY orden_snapshot',{'id':row['id_confirmacion']})
            row['eventos']=_rows(conn,f'SELECT * FROM {EVENT} WHERE id_confirmacion_modular=:id ORDER BY id_evento',{'id':row['id_confirmacion']})
        state=_snapshot(conn,day,pad,parcel)
        all_events=[e for h in headers for e in h['eventos']]
        points=model.temporal_points(headers,all_events)
        for row in headers:
            point=next(p for p in points if p['campana_id']==row['campana_id'] and p['fecha']==str(row['fecha_efectiva'])[:10])
            next_date=min((p['fecha'] for p in points if not p['anulacion'] and p['campana_id']==row['campana_id'] and p['fecha']>point['fecha']),default=None)
            row['vigencia_hasta']=min((x for x in (next_date,point['cierre']) if x),default=None)
            row['anulacion']=point['anulacion']
            row['situacion_temporal']=('ANULADO' if point['anulacion'] else 'Supersedida' if row['version']<point['header']['version'] else
                'Futura' if point['fecha']>day.isoformat() else
                'Cerrada' if point['cierre'] and point['cierre']<=day.isoformat() else
                'Vigente' if state['vigente'] and state['vigente']['id_confirmacion']==row['id_confirmacion'] else 'Histórica / no aplicable')
        return headers


def _lock(conn,day,pad,parcel):
    result=conn.execute(text('''DECLARE @r int;
        EXEC @r=sys.sp_getapplock @Resource=:resource,@LockMode='Exclusive',@LockOwner='Transaction',@LockTimeout=10000;
        SELECT @r;'''),{'resource':f'IMR:{pad}:{parcel}'}).scalar_one()
    if result<0:
        raise model.StaleContextError('No se pudo obtener el bloqueo modular; vuelva a intentar.')
    # Protege estructuras contra cambios entre validacion y COMMIT.
    for sql in (
        f'SELECT id_parcela FROM {SCHEMA}.parcela WITH(HOLDLOCK) WHERE id_parcela=:parcel AND id_pad=:pad',
        f'SELECT id_modulo,numero FROM {SCHEMA}.modulo WITH(HOLDLOCK) WHERE id_parcela=:parcel',
        f'SELECT id_campana_parcela_control FROM {SCHEMA}.campana_parcela_control WITH(HOLDLOCK) WHERE pad_id=:pad AND parcela_id=:parcel'):
        conn.execute(text(sql),dict(pad=pad,parcel=parcel)).fetchall()


def _insert(conn,table,values,id_column=None):
    if table not in (REF,CONF,DETAIL,EVENT):raise ValueError('Tabla modular inválida.')
    fields=list(values)
    command=f'INSERT INTO {table}('+','.join(fields)+')'
    if id_column:
        command='SET NOCOUNT ON; DECLARE @ids TABLE(id bigint); '+command+f' OUTPUT INSERTED.{id_column} INTO @ids'
    command+=' VALUES('+','.join(':'+x for x in fields)+');'
    if id_column:command+=' SELECT id FROM @ids;'
    result=conn.execute(text(command),values)
    return int(result.scalar_one()) if id_column else None


def _request(payload,action,actor):
    day,pad,parcel=model.validate_scope(payload['fecha'],payload['pad_id'],payload['parcela_id'])
    ids=payload.get('seleccion',[])
    if not isinstance(ids,list) or any(type(x) is not int for x in ids):raise ValueError('IDs de selección inválidos.')
    motive=str(payload.get('motivo') or '').strip()
    if not motive or len(motive)>1000:raise ValueError('Indique un motivo de hasta 1.000 caracteres.')
    return dict(fecha=day.isoformat(),pad_id=pad,parcela_id=parcel,accion=action,actor=actor,
                estado=payload.get('estado'),seleccion=sorted(ids),context_token=payload.get('context_token'),
                motivo=motive,observacion=str(payload.get('observacion') or '')[:2000],
                evidencia=str(payload.get('evidencia') or '')[:1000]),str(uuid.UUID(str(payload['idempotency_key'])))


def _duplicate(conn,key,request):
    rows=_rows(conn,f'SELECT * FROM {EVENT} WITH(UPDLOCK,HOLDLOCK) WHERE idempotency_key=:key',{'key':key})
    if rows:
        if bytes(rows[0]['payload_sha256'])!=model.digest(request) or rows[0]['actor']!=request['actor']:
            raise model.StaleContextError('La clave de reintento ya fue utilizada con otro contenido.')
        return dict(id_confirmacion=rows[0]['id_confirmacion_modular'],reintento=True)
    return None


def _decide(payload,action,connection=None):
    actor=phase_db._actor()  # Puerta existente; nunca aceptar actor del cliente.
    request,key=_request(payload,action,actor)
    day,pad,parcel=model.validate_scope(request['fecha'],request['pad_id'],request['parcela_id'])
    with _connection(connection) as conn:
        _lock(conn,day,pad,parcel)
        duplicate=_duplicate(conn,key,request)
        if duplicate:return duplicate
        snapshot=_snapshot(conn,day,pad,parcel,True)
        model.check_context(request['context_token'],snapshot['context_token'])
        active=snapshot['vigente'];latest=snapshot['revision']
        exact=snapshot.get('punto_fecha',active)
        temporal=snapshot.get('temporal',{})
        if latest.get('anulada') and action in ('ANULAR','RECTIFICAR'):
            raise ValueError('El punto ya está anulado; ninguna de sus versiones puede reactivarse.')
        if action=='ANULAR' and (not exact or latest.get('cerrada')):
            raise ValueError('Anular requiere un punto no cerrado en su fecha efectiva original.')
        if action=='RECTIFICAR' and (not exact or latest.get('cerrada')):
            raise ValueError('Rectificar requiere un punto no cerrado en su fecha efectiva original.')
        if action=='CERRAR' and (not active or temporal.get('cierre')):
            raise ValueError('No existe una confirmación modular vigente para esta acción.')
        if action=='CONFIRMAR' and exact:
            raise ValueError('Ya existe un punto en esta fecha; no se permite otra V1 ni reabrirlo.')
        if action=='CONFIRMAR' and temporal.get('aplicabilidad')=='CERRADA' and day.isoformat()<=temporal['cierre']:
            raise ValueError('Después de un cierre, registre el nuevo punto en una fecha posterior al cierre.')
        if action=='CONFIRMAR':
            latest=dict(id=None,version=0)  # Nueva fecha, nueva familia; no supersede al punto heredado.
        roster=snapshot['roster']
        event_action=action
        if action in ('CERRAR','ANULAR'):
            identifier=(exact if action=='ANULAR' else active)['id_confirmacion']
        else:
            selected,count=model.selection(roster,request['estado'],request['seleccion'])
            event_action='MARCAR_SIN_INFORMACION' if request['estado']=='SIN_INFORMACION' else action
            ref=snapshot['referencia']
            if ref and not ref['estructura_actual']:
                raise model.StaleContextError('La referencia pertenece a otra estructura. Actualice la referencia antes de confirmar.')
            ref_snapshot=None if not ref else model.dump(dict(id_referencia=ref['id_referencia'],version=ref['version'],payload_sha256=bytes(ref['payload_sha256']).hex().upper(),fuente=ref['fuente'],estado=ref['estado_referencia']))
            prior=_rows(conn,f'SELECT familia_id FROM {CONF} WHERE id_confirmacion=:id',{'id':latest['id']}) if latest['id'] else []
            identifier=_insert(conn,CONF,dict(
                familia_id=str(prior[0]['familia_id']) if prior else str(uuid.uuid4()),version=latest['version']+1,
                version_anterior=latest['version'] if latest['id'] else None,supersede_id=latest['id'],
                fecha_efectiva=day,pad_id=pad,parcela_id=parcel,campana_id=roster['campana_id'],numero_campana_snapshot=roster['numero_campana'],
                estado_modular=request['estado'],cantidad_confirmada=count,total_modulos_snapshot=roster['total'],
                accion=event_action,referencia_id=ref['id_referencia'] if ref else None,referencia_snapshot_json=ref_snapshot,
                roster_snapshot_json=model.dump(roster['miembros']),roster_sha256=model.digest(roster['miembros']),orden_es_operacional=roster['orden_confiable'],
                contexto_json=model.dump(snapshot['contexto']),context_sha256=bytes.fromhex(snapshot['context_token']),canon_version=model.CANON_VERSION,
                usuario=actor,motivo_codigo='DECISION_MODULAR',justificacion=request['motivo'],observacion=request['observacion'],evidencia_usuario=request['evidencia'],
                idempotency_key=key,payload_json=model.dump(request),payload_sha256=model.digest(request)), 'id_confirmacion')
            for order,member in enumerate(roster['miembros'],1):
                chosen=member['modulo_id'] in selected
                _insert(conn,DETAIL,dict(id_confirmacion_modular=identifier,modulo_id=member['modulo_id'],nombre_modulo_snapshot=member['nombre_visible'],
                    orden_snapshot=order,seleccionado=chosen,origen_seleccion=('DESCONOCIDO' if count is None else 'MANUAL' if chosen else 'NO_SELECCIONADO'),
                    control_id_snapshot=member['control_id_snapshot'],secuencia_carguio_snapshot=member['secuencia_carguio'],
                    fecha_ini_carguio_snapshot=member['fecha_ini_carguio'],fecha_fin_carguio_snapshot=member['fecha_fin_carguio'],
                    fecha_ini_retiro_snapshot=member['fecha_ini_retiro'],fecha_fin_retiro_snapshot=member['fecha_fin_retiro']))
        _insert(conn,EVENT,dict(id_confirmacion_modular=identifier,tipo_evento=event_action,actor=actor,fecha_efectiva=day,
            motivo=request['motivo'],antes_json=model.dump(dict(id=active['id_confirmacion'])) if active else None,
            despues_json=model.dump(dict(id=identifier,accion=event_action)),evidencia_json=model.dump(dict(request=request,revision=latest)),
            context_sha256=bytes.fromhex(snapshot['context_token']),correlation_id=str(uuid.uuid4()),idempotency_key=key,
            payload_json=model.dump(request),payload_sha256=model.digest(request)), 'id_evento')
        return dict(id_confirmacion=identifier,reintento=False,accion=event_action)


def confirm_modules(payload,*,connection=None):return _decide(payload,'CONFIRMAR',connection)
def rectify_modules(payload,*,connection=None):return _decide(payload,'RECTIFICAR',connection)
def close_modules(payload,*,connection=None):return _decide(payload,'CERRAR',connection)

def annul_modules(payload,*,connection=None):return _decide(payload,'ANULAR',connection)


def preview_reference(fecha,pad_id,parcela_id,quantity,*,connection=None):
    snapshot=modular_snapshot(fecha,pad_id,parcela_id,connection=connection)
    return dict(snapshot=snapshot,referencia=model.reference_preview(snapshot['roster'],quantity))


def import_reference(payload,*,connection=None):
    actor=phase_db._actor()
    day,pad,parcel=model.validate_scope(payload['fecha'],payload['pad_id'],payload['parcela_id'])
    key=str(uuid.UUID(str(payload['idempotency_key'])))
    request={k:payload.get(k) for k in ('fecha','pad_id','parcela_id','cantidad','archivo','fuente','hash_origen','context_token')}
    request['actor']=actor
    if not isinstance(request['fuente'],str) or not request['fuente'].strip() or len(request['fuente'])>200:
        raise ValueError('Fuente requerida de hasta 200 caracteres.')
    try:origin=bytes.fromhex(str(request['hash_origen']))
    except ValueError as exc:raise ValueError('Hash de origen inválido.') from exc
    if len(origin)!=32:raise ValueError('Hash de origen debe ser SHA256.')
    with _connection(connection) as conn:
        _lock(conn,day,pad,parcel)
        duplicate=_rows(conn,f'SELECT * FROM {REF} WITH(UPDLOCK,HOLDLOCK) WHERE idempotency_key=:key',{'key':key})
        if duplicate:
            if bytes(duplicate[0]['payload_sha256'])!=model.digest(request):raise model.StaleContextError('Clave de importación reutilizada con otro contenido.')
            return dict(id_referencia=duplicate[0]['id_referencia'],reintento=True)
        snapshot=_snapshot(conn,day,pad,parcel,True)
        model.check_context(request['context_token'],snapshot['context_token'])
        roster=snapshot['roster'];reference=model.reference_preview(roster,payload.get('cantidad'))
        previous=_reference(conn,day,pad,parcel,True)
        identifier=_insert(conn,REF,dict(familia_id=str(previous['familia_id']) if previous else str(uuid.uuid4()),
            version=previous['version']+1 if previous else 1,version_anterior=previous['version'] if previous else None,
            supersede_id=previous['id_referencia'] if previous else None,fecha_operacional=day,pad_id=pad,parcela_id=parcel,
            campana_id=roster['campana_id'],cantidad_modulos_referencia=reference['cantidad'],cantidad_original=reference['cantidad_original'],
            total_modulos_snapshot=roster['total'],estado_referencia=reference['estado'],fuente=request['fuente'],archivo_origen=request['archivo'],
            fecha_fuente=None,hash_origen=origin,tipo_hash_origen='ARCHIVO' if request['archivo'] else 'EVIDENCIA',
            roster_snapshot_json=model.dump(roster['miembros']),roster_sha256=model.digest(roster['miembros']),
            modulos_sugeridos_json=model.dump(reference['sugeridos']) if reference['sugeridos'] is not None else None,
            regla_orden_version=model.CANON_VERSION,evidencia_json=model.dump(dict(request=request,validacion=reference)),
            observacion=reference['observacion'],imported_by=actor,idempotency_key=key,payload_json=model.dump(request),payload_sha256=model.digest(request)), 'id_referencia')
        return dict(id_referencia=identifier,reintento=False,estado=reference['estado'])
