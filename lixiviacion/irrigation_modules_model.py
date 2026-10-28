"""Dimension modular diaria: funciones puras, sin fases ni inferencias hidraulicas."""
import hashlib
import json
import re
import unicodedata
import uuid
from datetime import date, datetime

STATES = ('SELECCION_CONOCIDA', 'NINGUN_MODULO', 'SIN_INFORMACION')
STALE_MESSAGE = 'El contexto operacional cambió. Actualice el detalle antes de confirmar los módulos.'
CANON_VERSION = 'IMR_JSON_NFC_UTF16LE_V1'
SNAPSHOT_FIELDS = ('modulo_id','nombre_visible','control_id_snapshot','secuencia_carguio',
                   'fecha_ini_carguio','fecha_fin_carguio','fecha_ini_retiro','fecha_fin_retiro')


class StaleContextError(ValueError):
    pass


def _clean(value):
    if isinstance(value, dict):
        return {unicodedata.normalize('NFC', str(k)): _clean(v) for k,v in value.items()}
    if isinstance(value, (tuple,list)):
        return [_clean(x) for x in value]
    if isinstance(value, (date,datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes,bytearray,memoryview)):
        return bytes(value).hex().upper()
    if isinstance(value, str):
        return unicodedata.normalize('NFC',value)
    return value


def dump(value):
    return json.dumps(_clean(value), ensure_ascii=False, sort_keys=True, separators=(',',':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(dump(value).encode('utf-16le')).digest()


def validate_scope(fecha, pad, parcela):
    day=date.fromisoformat(str(fecha))
    if type(pad) is not int or type(parcela) is not int or pad not in (1,2) or parcela<1:
        raise ValueError('PAD/parcela deben ser identidades SQL válidas.')
    return day,pad,parcela


def roster_context(rows):
    if not rows:
        raise ValueError('No existe roster estructural para PAD/parcela/fecha.')
    first=rows[0]
    members=[{k:row.get(k) for k in SNAPSHOT_FIELDS} for row in rows if row.get('modulo_id') is not None]
    reliable=first.get('estado_roster')=='CONFIABLE'
    numbered=[]
    for row in rows:
        if row.get('modulo_id') is None:continue
        name=str(row.get('nombre_visible') or '')
        match=re.fullmatch(r'M([0-9]+)',name,flags=re.IGNORECASE)
        numbered.append((row.get('secuencia_carguio'),int(match[1]) if match else None,str(row.get('fecha_ini_carguio'))[:10]))
    if reliable:
        valid_sequences=all(type(x[0]) is int and x[0]>0 for x in numbered)
        valid_names=all(x[1] is not None and x[1]>0 for x in numbered)
        if not (valid_sequences and valid_names and sorted(x[0] for x in numbered)==list(range(1,len(numbered)+1))):
            reliable=False
        else:
            ordered_numbers=sorted(numbered)
            reliable=(len({x[1] for x in numbered})==len(numbered)
                      and all(a[1]<b[1] and a[2]<=b[2] for a,b in zip(ordered_numbers,ordered_numbers[1:])))
    if reliable:
        ordered=sorted([r for r in rows if r.get('modulo_id') is not None],key=lambda r:r['orden_incremental'])
        members=[{k:r.get(k) for k in SNAPSHOT_FIELDS} for r in ordered]
    else:
        # Solo posicion documental; no autoriza sugerencia ni orden operacional.
        members.sort(key=lambda r:(str(r.get('nombre_visible') or ''),r['control_id_snapshot']))
    if len({m['modulo_id'] for m in members}) != len(members):
        raise ValueError('Roster estructural duplicado.')
    return dict(fecha=str(first['fecha'])[:10],pad_id=first['pad_id'],parcela_id=first['parcela_id'],
                campana_id=first.get('campana_id'),numero_campana=first.get('numero_campana'),
                estado_roster=('ORDEN_AMBIGUO' if first.get('estado_roster')=='CONFIABLE' and not reliable else first.get('estado_roster')),total=first.get('total_modulos'),
                orden_confiable=reliable,miembros=members)


def reference_preview(roster, quantity):
    original=None if quantity is None else str(quantity)
    if quantity is None:
        return dict(estado='SIN_INFORMACION',cantidad=None,cantidad_original=None,sugeridos=None,observacion='Sin cantidad informada.')
    if isinstance(quantity,str) and re.fullmatch(r'[0-9]+',quantity.strip()):
        quantity=int(quantity)
    if type(quantity) is not int or quantity<0:
        return dict(estado='INCONSISTENTE',cantidad=None,cantidad_original=original,sugeridos=None,observacion='N debe ser entero no negativo; no se trunca.')
    if roster['campana_id'] is None or roster['total'] is None or quantity>roster['total']:
        return dict(estado='INCONSISTENTE',cantidad=quantity,cantidad_original=original,sugeridos=None,observacion='N supera el roster o la campaña/denominador no está resuelta.')
    if not roster['orden_confiable']:
        return dict(estado='ORDEN_AMBIGUO',cantidad=quantity,cantidad_original=original,sugeridos=None,observacion='No existe un orden estructural confiable para sugerir módulos.')
    suggested=[dict(modulo_id=m['modulo_id'],nombre_visible=m['nombre_visible'],orden_incremental=i+1)
               for i,m in enumerate(roster['miembros'][:quantity])]
    return dict(estado='VALIDA',cantidad=quantity,cantidad_original=original,sugeridos=suggested,observacion=None)


def selection(roster, state, selected):
    if state not in STATES:
        raise ValueError('Estado modular inválido.')
    if roster['campana_id'] is None or roster['total'] is None or roster['estado_roster'] not in ('CONFIABLE','ORDEN_AMBIGUO'):
        raise ValueError('La campaña o el roster no permiten una confirmación inequívoca.')
    if not isinstance(selected,list) or any(type(x) is not int for x in selected):
        raise ValueError('La selección debe contener IDs SQL enteros.')
    allowed={m['modulo_id'] for m in roster['miembros']}
    if len(set(selected))!=len(selected) or not set(selected)<=allowed:
        raise ValueError('Selección duplicada o ajena al roster.')
    if state=='SELECCION_CONOCIDA' and not selected:
        raise ValueError('Seleccione al menos un módulo.')
    if state!='SELECCION_CONOCIDA' and selected:
        raise ValueError('Cero o sin información no admiten módulos seleccionados.')
    return [m['modulo_id'] for m in roster['miembros'] if m['modulo_id'] in selected], (None if state=='SIN_INFORMACION' else len(selected))


def check_context(expected, current):
    if not isinstance(expected,str) or expected != current:
        raise StaleContextError(STALE_MESSAGE)


TEMPORAL_VERSION = 'IMR_ASOF_V1'
INCOMPATIBLE_MESSAGE = 'Confirmación modular previa no aplicable al roster actual.'


def compatibility_signature(roster):
    """Identidad/orden, no nombres documentales, controles ni hitos informativos."""
    if roster.get('campana_id') is None or roster.get('total') is None:
        return None
    members=roster['miembros']
    if roster['total']!=len(members) or len({m['modulo_id'] for m in members})!=len(members):return None
    ordered=sorted([(m['modulo_id'],m.get('secuencia_carguio')) for m in members],key=lambda x:x[0])
    return digest(dict(version=TEMPORAL_VERSION,pad=roster['pad_id'],parcela=roster['parcela_id'],
        campana=roster['campana_id'],orden_confiable=roster['orden_confiable'],modulos=ordered)).hex()


def header_signature(header):
    return compatibility_signature(dict(pad_id=header['pad_id'],parcela_id=header['parcela_id'],
        campana_id=header['campana_id'],total=header['total_modulos_snapshot'],
        orden_confiable=bool(header['orden_es_operacional']),miembros=json.loads(header['roster_snapshot_json'])))


def temporal_points(headers, events):
    """Última revisión de cada punto; un cierre jamás permite volver a V1."""
    groups={}
    for h in headers:
        key=(h['pad_id'],h['parcela_id'],h['campana_id'],str(h['fecha_efectiva'])[:10])
        groups.setdefault(key,[]).append(h)
    points=[]
    for key,revisions in groups.items():
        latest=max(revisions,key=lambda h:h['version'])
        seals=[e for e in events if e['id_confirmacion_modular']==latest['id_confirmacion']
               and e['tipo_evento'] in ('CONFIRMAR','RECTIFICAR','MARCAR_SIN_INFORMACION')]
        annulments=[e for e in events if e['tipo_evento']=='ANULAR'
                    and any(e['id_confirmacion_modular']==h['id_confirmacion'] for h in revisions)]
        # Las lecturas nunca ignoran una revisión incompleta para rescatar su anterior.
        closed=[str(e['fecha_efectiva'])[:10] for e in events if e['tipo_evento']=='CERRAR'
                and any(e['id_confirmacion_modular']==h['id_confirmacion'] for h in revisions)]
        points.append(dict(header=latest,sellada=bool(seals),cierre=min(closed,default=None),
            fecha=key[-1],campana_id=key[2],anulacion=max(annulments,key=lambda e:e['id_evento']) if annulments else None))
    return sorted(points,key=lambda p:(p['fecha'],p['campana_id']))


def resolve_temporal(roster, headers, events, structural_path=()):
    day=str(roster['fecha'])[:10]
    points=[p for p in temporal_points(headers,events) if p['campana_id']==roster['campana_id']]
    effective=[p for p in points if not p['anulacion']]
    candidates=[p for p in effective if p['fecha']<=day]
    exact=next((p for p in points if p['fecha']==day),None)
    point=max(candidates,key=lambda p:p['fecha']) if candidates else None
    result=dict(fecha_consultada=day,fecha_origen=point['fecha'] if point else None,
        aplicabilidad='SIN_CONFIRMACION',heredada=bool(point and point['fecha']<day),
        cierre=point['cierre'] if point else None,fin=None,firma_compatible=compatibility_signature(roster))
    if point:
        if not point['sellada']:raise StaleContextError('Hay una decisión modular incompleta; requiere revisión administrativa.')
        next_date=min((p['fecha'] for p in effective if p['fecha']>point['fecha']),default=None)
        result['fin']=min((x for x in (next_date,point['cierre']) if x),default=None)
        if point['cierre'] and point['cierre']<=day:
            result['aplicabilidad']='CERRADA'
        else:
            expected=header_signature(point['header'])
            path=[roster,*structural_path]
            compatible=expected is not None and all(compatibility_signature(r)==expected for r in path)
            result['aplicabilidad']='VIGENTE' if compatible else 'ROSTER_INCOMPATIBLE'
    return dict(temporal=result,punto_fecha=exact['header'] if exact else None,
        candidato=point['header'] if point else None,
        vigente=point['header'] if point and result['aplicabilidad']=='VIGENTE' else None)
