"""Acceso exclusivamente DEV. Montar la pantalla no abre conexiones."""
import contextlib,io,json,hashlib,uuid
from datetime import date
from decimal import Decimal
from pathlib import Path
from sqlalchemy import text
from env_loader import load_app_env
from lixiviacion import phase_flags
from .build_sql import EQUIPOS

def engine_dev():
    load_app_env()
    if not phase_flags.is_dev():raise ValueError('Contingencia M6 disponible exclusivamente en DEV.')
    from db_connection import get_engine
    with contextlib.redirect_stdout(io.StringIO()):return get_engine()

def records(result):
    def value(v):
        if isinstance(v,Decimal):return float(v)
        if isinstance(v,uuid.UUID):return str(v)
        if hasattr(v,'isoformat'):return v.isoformat()
        return v
    return [{k:value(v) for k,v in r.items()} for r in result.mappings()]

def period(inicio,turno_inicio,fin,turno_fin,equipos):
    inicio=date.fromisoformat(str(inicio));fin=date.fromisoformat(str(fin))
    if inicio<date(2026,9,1) or fin<inicio or (fin-inicio).days>90:raise ValueError('Seleccione un rango de hasta 91 días desde 01-09-2026.')
    if turno_inicio not in ('A','B') or turno_fin not in ('A','B') or (inicio,turno_inicio)>(fin,turno_fin):raise ValueError('Rango de turnos inválido.')
    if not equipos or any(e not in EQUIPOS for e in equipos):raise ValueError('Seleccione señales del Balance M6.')
    return dict(inicio=str(inicio),fin=str(fin),ti=turno_inicio,tf=turno_fin)

def load_rows(inicio,ti,fin,tf,equipos):
    params=period(inicio,ti,fin,tf,equipos)
    with engine_dev().connect() as c:
        phase_flags.guard_connection(c)
        rows=records(c.execute(text('''SELECT fecha_operacional,turno,equipo_codigo,valor_pi_final AS pi_tmh,
          valor_turno_tum AS tum_tmh,tum_disponible,estado_tecnico_pi AS calidad_pi,
          fuente_auto,valor_auto,modo_m6,fuente_resuelta AS fuente_m6,valor_final_resuelto AS valor_m6,
          (CASE WHEN tum_disponible=1 AND valor_turno_tum>=0 THEN CASE WHEN equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108') AND valor_turno_tum<=100 THEN 0 ELSE valor_turno_tum END END)-valor_pi_final AS diferencia,
          ((CASE WHEN tum_disponible=1 AND valor_turno_tum>=0 THEN CASE WHEN equipo_codigo IN ('PRINCIPAL_CV008','PRINCIPAL_CV108') AND valor_turno_tum<=100 THEN 0 ELSE valor_turno_tum END END)-valor_pi_final)*CASE WHEN equipo_codigo LIKE 'SRR_%' THEN 0.97 WHEN equipo_codigo='CHANCADOR_CV006' THEN 0.975 ELSE 1.0-humedad_m6/100.0 END AS diferencia_tms,
          COALESCE(motivo_m6,motivo_decision) AS motivo_m6,version_m6,huella_m6
          FROM inventar_SpcHidr.v_balance_m6_totalizador_resuelto_turno r
          OUTER APPLY (SELECT CASE r.equipo_codigo WHEN 'PRINCIPAL_CV008' THEN h.Humedad_TM1 WHEN 'PRINCIPAL_CV108' THEN h.Humedad_TM2 END AS humedad_m6
             FROM inventar_SpcHidr.fn_humedad_resuelta_tm_turno_test(CAST(:inicio AS date),DATEADD(DAY,1,CAST(:fin AS date))) h
             WHERE h.Fecha=r.fecha_operacional AND h.Turno=r.turno) humedad
          WHERE fecha_operacional BETWEEN :inicio AND :fin
          AND (fecha_operacional>:inicio OR turno>=:ti)
          AND (fecha_operacional<:fin OR turno<=:tf)
          ORDER BY fecha_operacional,turno,equipo_codigo'''),params))
    return [r for r in rows if r['equipo_codigo'] in equipos]

def cases(inicio,fin):
    if not inicio or not fin:return []
    with engine_dev().connect() as c:
        phase_flags.guard_connection(c)
        return records(c.execute(text('''SELECT caso_id,nombre_caso FROM inventar_SpcHidr.casos_balance
            WHERE modelo=6 AND CAST(fecha_ini AS date)=:i AND CAST(fecha AS date)=:f ORDER BY caso_id'''),{'i':inicio,'f':fin}))

def history(inicio,fin):
    with engine_dev().connect() as c:
        phase_flags.guard_connection(c)
        return records(c.execute(text('''SELECT id,fecha_operacional,turno,equipo_codigo,modo,version,motivo,comentario,usuario,fecha_registro,solicitud_id,
          CAST(CASE WHEN version=MAX(version) OVER(PARTITION BY equipo_codigo,fecha_operacional,turno) THEN 1 ELSE 0 END AS bit) AS vigente
         FROM inventar_SpcHidr.balance_m6_contingencia_decision WHERE fecha_operacional BETWEEN :i AND :f ORDER BY id DESC'''),{'i':inicio,'f':fin}))

def check_contract(c):
    expected=json.loads(Path(__file__).with_name('contract.json').read_text(encoding='utf8'))
    for n,k in [('sp_calcular_balance_flujos_modelo6_v2','m6_sha256'),('sp_balance_m6_preview_contingencia','preview_sha256'),('v_balance_m6_totalizador_auto_turno','auto_sha256'),('v_balance_m6_totalizador_resuelto_turno','resuelto_sha256'),('sp_balance_m6_guardar_contingencia','writer_sha256'),('sp_balance_m6_bloquear_entradas','entradas_sha256')]:
        definition=c.execute(text('SELECT OBJECT_DEFINITION(OBJECT_ID(:n))'),{'n':'inventar_SpcHidr.'+n}).scalar_one()
        if not definition or hashlib.sha256(definition.encode()).hexdigest()!=expected.get(k):raise ValueError('La versión M6 instalada cambió. Se requiere validar el preview antes de continuar.')

def selection(rows,selected,modo):
    if modo not in ('AUTO','TUM'):raise ValueError('Modo inválido.')
    if not selected:raise ValueError('Marque al menos un registro; no hay activación global.')
    out=[]
    for idx in sorted(set(selected)):
        if not isinstance(idx,int) or idx<0 or idx>=len(rows):raise ValueError('Selección inválida.')
        r=rows[idx]
        if r['equipo_codigo'] not in EQUIPOS:raise ValueError('Equipo fuera del alcance M6.')
        if modo=='TUM' and (not r['tum_disponible'] or r['tum_tmh'] is None or r['tum_tmh']<0):raise ValueError(f"TUM no disponible para {r['fecha_operacional']} {r['turno']} {r['equipo_codigo']}")
        out.append(dict(fecha_operacional=r['fecha_operacional'],turno=r['turno'],equipo_codigo=r['equipo_codigo'],modo=modo,version_esperada=r['version_m6'],huella=r['huella_m6']))
    return out

def calculate(c,inicio,fin,case_id,keys=(),actual=False,snapshot=None):
    return records(c.execute(text('''EXEC inventar_SpcHidr.sp_balance_m6_preview_contingencia
       @fecha_inicio=:i,@fecha_fin=:f,@caso_id=:caso,@selecciones_json=:s,@usar_actual=:a,@fuentes_snapshot_json=:snapshot'''),
       dict(i=inicio,f=fin,caso=case_id,s=json.dumps(list(keys),ensure_ascii=False),a=int(actual),snapshot=json.dumps(snapshot,ensure_ascii=False) if snapshot is not None else None)))

def compare(auto,proposed):
    a={r['Flujo']:r for r in auto};b={r['Flujo']:r for r in proposed}
    if set(a)!=set(b) or len(a)!=125:raise ValueError('El preview no contiene los 125 flujos esperados.')
    out=[]
    for k in sorted(a,key=lambda k:int(k[1:])):
        row={'Flujo':k}
        changed=False
        for col in ['Tonelaje','Ley_Cu','FCu']:
            av=a[k][col];bv=b[k][col]
            delta=round(bv-av,6) if av is not None and bv is not None else None
            row[col+'_AUTO']=av;row[col+'_M6']=bv;row['delta_'+col]=delta
            changed |= (delta!=0 if delta is not None else av!=bv)
        row['estado']='CAMBIA' if changed else 'IGUAL';out.append(row)
    return out

def lock_inputs(c,definitions_only=False):
    c.exec_driver_sql('SET LOCK_TIMEOUT 10000; IF @@TRANCOUNT=0 BEGIN TRANSACTION;')
    return c.execute(text('''DECLARE @h varchar(64);
       EXEC inventar_SpcHidr.sp_balance_m6_bloquear_entradas @huella=@h OUTPUT,@solo_definiciones=:only;
       SELECT @h huella'''),{'only':int(definitions_only)}).scalar_one()

def preview(inicio,fin,case_id,keys):
    with engine_dev().connect() as c:
        phase_flags.guard_connection(c);check_contract(c)
        try:
            stamp=lock_inputs(c)
            current=records(c.execute(text('''SELECT fecha_operacional,turno,equipo_codigo,version_m6,huella_m6
              FROM inventar_SpcHidr.v_balance_m6_totalizador_resuelto_turno
              WHERE fecha_operacional BETWEEN :i AND :f'''),dict(i=inicio,f=fin)))
            index={(r['fecha_operacional'],r['turno'],r['equipo_codigo']):r for r in current}
            for k in keys:
                r=index.get((k['fecha_operacional'],k['turno'],k['equipo_codigo']))
                if not r or r['version_m6']!=k['version_esperada'] or r['huella_m6']!=k['huella']:raise ValueError('Cambió una fuente o decisión. Consulte y previsualice nuevamente.')
            auto=calculate(c,inicio,fin,case_id)
            proposed=calculate(c,inicio,fin,case_id,keys,True)
            lock_inputs(c,True);check_contract(c)
            return {'comparacion':compare(auto,proposed),'huella_entradas':stamp}
        finally:c.rollback()

def persist(keys,request_id,usuario,motivo,comentario,huella_entradas):
    if not usuario or not isinstance(usuario,str):raise ValueError('Sesión autenticada requerida.')
    if not motivo or not motivo.strip() or len(motivo)>500:raise ValueError('Indique un motivo de hasta 500 caracteres.')
    if len(comentario or '')>1000:raise ValueError('Comentario demasiado largo.')
    uuid.UUID(request_id)
    if not isinstance(huella_entradas,str) or len(huella_entradas)!=64:raise ValueError('Preview válido requerido; vuelva a previsualizar.')
    with engine_dev().connect() as c:
        phase_flags.guard_connection(c);check_contract(c)
        c.exec_driver_sql('SET LOCK_TIMEOUT 10000;')
        result=records(c.execute(text('''EXEC inventar_SpcHidr.sp_balance_m6_guardar_contingencia
          @claves=:k,@solicitud_id=:s,@usuario=:u,@motivo=:m,@comentario=:c,@huella_entradas=:h'''),
          dict(k=json.dumps(keys,ensure_ascii=False,separators=(',',':')),s=request_id,u=usuario,m=motivo.strip(),c=comentario or None,h=huella_entradas)))
        c.commit()
    return result
