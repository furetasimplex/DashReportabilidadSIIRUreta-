"""Contrato, presentación y oráculo de pruebas del modelo causal V2.
La lectura de producción obtiene la clasificación de la TVF independiente.
"""
from datetime import date,timedelta
MODEL_VERSION='FASE_OPERACIONAL_V2_20261008'
ALERT_VERSION='PAUSA_RC_V1_20261008'
PHASES={
 'APILADO':('Apilado','stacked'),'ESPERA_RIEGO':('Espera de riego','formed'),
 'HUMECTACION':('Humectación','wetting'),'RIEGO_CONTINUO':('Riego continuo','hydraulic'),
 'DRENAJE_RESIDUAL':('Drenaje residual','draining'),'ESPERA_RECLAMO':('Espera de reclamo','waiting'),
 'RECLAMO':('Reclamo','reclaiming'),'RECLAMADO':('Reclamado','reclaimed'),
 'MIXTO':('Mixto','mixed'),'SIN_COBERTURA':('Sin información del día','missing'),
 'NO_EVALUABLE':('Sin información suficiente','missing')}
CONDITIONS={'RIEGO_ACTIVO':'Riego activo','RIEGO_DRENAJE':'Riego y aporte de drenaje',
 'RIEGO_PAUSADO_CON_DRENAJE':'Riego pausado con aporte de drenaje','PAUSA_HIDRAULICA':'Pausa hidráulica',
 'SIN_COBERTURA':'Sin información suficiente del día','SIN_ACTIVIDAD':'Sin actividad registrada'}
ALERTS={'SIN_ALERTA':'Sin alerta','PAUSA_RECIENTE':'Pausa reciente','PAUSA_PROLONGADA':'Pausa prolongada',
 'PAUSA_EXCEPCIONAL':'Pausa excepcional','SIN_COBERTURA':'Información de riego incompleta'}
STATUSES={'VIGENTE':'Vigente','CONTRADICHO':'Requiere revisión','CERRADO_HITO':'Cerrada por actividad física',
 'CERRADO_MANUAL':'Confirmación cerrada','ANULADO':'Anulada','FINALIZADO':'Período finalizado',
 'APARTADO_ESTRUCTURA':'Apartada por situación de módulos','CONFLICTO_OVERRIDE':'Confirmaciones en conflicto'}
REASONS={'FIN_RIEGO_CONFIRMADO':'Término de riego confirmado','PRIMER_APORTE_CONFIRMADO':'Primer aporte confirmado',
 'DRENAJE_RESIDUAL_CONFIRMADO':'Drenaje residual confirmado','FIN_DRENAJE_CONFIRMADO':'Término de drenaje confirmado',
 'ESPERA_RECLAMO_CONFIRMADA':'Espera de reclamo confirmada','CORRECCION_ESTADO':'Corrección de fase',
 'VALIDACION_TERRENO':'Validación en terreno','OTRO':'Otro motivo'}
EVENTS={'DECISION_CREADA':'Confirmación registrada','DECISION_SUSTITUIDA':'Confirmación sustituida',
 'DECISION_RECTIFICADA':'Decisión rectificada','CIERRE_MANUAL':'Confirmación cerrada','CIERRE_HITO':'Cierre por actividad física',
 'ANULACION':'Decisión anulada','CONTRADICCION_DETECTADA':'Contradicción registrada','CONTRADICCION_RESUELTA':'Revisión resuelta'}
ADMIN_PHASES=('HUMECTACION','RIEGO_CONTINUO','DRENAJE_RESIDUAL','ESPERA_RECLAMO')
def label(code,catalog=PHASES):
    v=catalog.get(code)
    return v[0] if isinstance(v,tuple) else v or 'Sin información'
def d(value):
    return date.fromisoformat(str(value)[:10]) if value is not None else None

def alert_level(pad,phase,days,irrigation):
    if phase!='RIEGO_CONTINUO':return 'SIN_ALERTA'
    if irrigation is None:return 'SIN_COBERTURA'
    recent,prolonged,exceptional=(3,22,39) if pad==1 else (3,14,33)
    return ('PAUSA_EXCEPCIONAL' if days is not None and days>=exceptional else
            'PAUSA_PROLONGADA' if days is not None and days>=prolonged else
            'PAUSA_RECIENTE' if days is not None and days>=recent else 'SIN_ALERTA')

def calculate(day,modules,irrigation,chemistry,pad=1,campaign_start=None):
    """Oráculo independiente para fixtures acotados; ignora señales posteriores a D."""
    day=d(day)
    active=[m for m in modules if d(m.get('fecha_ini_carguio')) is None or d(m['fecha_ini_carguio'])<=day]
    starts=[d(m['fecha_ini_carguio']) for m in active if m.get('fecha_ini_carguio')]
    begin=d(campaign_start) or min(starts,default=day)
    def daily(rows,field):
        out={}
        for r in rows:
            dt=d(r['fecha'])
            if not begin<=dt<=day:continue
            v=r.get(field)
            if field=='caudal' and v is not None and v<0:v=0
            if dt not in out:out[dt]=v
            elif v is not None:out[dt]=v if out[dt] is None else max(v,out[dt])
        return out
    qs=daily(irrigation,'caudal');cs=daily(chemistry,'cu_pp')
    if not starts and campaign_start is None:qs,cs={},{}  # Sin campaña, no asociar señales de otra identidad.
    available=[d(m['fecha_fin_carguio']) for m in active if m.get('fecha_ini_carguio') and m.get('fecha_fin_carguio') and d(m['fecha_ini_carguio'])<=d(m['fecha_fin_carguio'])<=day]
    eligible=min(available,default=None)
    recognized=[dt for dt,v in qs.items() if v is not None and v>1 and eligible is not None and dt>=eligible]
    first=min(recognized,default=None);last=max((dt for dt,v in qs.items() if v is not None and v>1),default=None)
    proxies=[dt for dt,v in cs.items() if v is not None and v>0]
    first_proxy=min((dt for dt in proxies if first and dt>=first),default=None)
    latest_proxy=max(proxies,default=None)
    hyd='ESPERA_RIEGO' if not first else 'HUMECTACION' if not first_proxy else 'RIEGO_CONTINUO'
    states=[];structure=[]
    for m in active:
        ini,fin,ret,end=(d(m.get(k)) for k in ('fecha_ini_carguio','fecha_fin_carguio','fecha_ini_retiro','fecha_fin_retiro'))
        invalid=(fin and fin<=day and (ini is None or fin<ini)) or (end and end<=day and (ret is None or end<ret))
        s=('NO_EVALUABLE' if invalid else 'RECLAMADO' if end and day>end else 'RECLAMO' if ret and day>=ret else
           'NO_EVALUABLE' if ini is None else 'APILADO' if fin is None or day<fin else 'DISPONIBLE')
        structure.append(s);states.append(hyd if s=='DISPONIBLE' else s)
    phase=states[0] if states and len(set(states))==1 else 'MIXTO' if states else 'NO_EVALUABLE'
    if phase=='RECLAMADO' and len(active)<len(modules):phase='MIXTO'
    q,c=qs.get(day),cs.get(day);r=None if q is None else int(q>1);g=None if c is None else int(c>0)
    condition=('SIN_COBERTURA' if r is None else 'RIEGO_DRENAJE' if r==1 and g==1 else 'RIEGO_ACTIVO' if r==1 else
               'SIN_COBERTURA' if g is None else 'RIEGO_PAUSADO_CON_DRENAJE' if g==1 else 'PAUSA_HIDRAULICA' if first else 'SIN_ACTIVIDAD')
    days=None
    if r is not None and last is not None:
        days=0;dt=day
        while r==0 and dt>last and qs.get(dt) is not None and 0<=qs[dt]<=1:
            days+=1;dt-=timedelta(days=1)
    return dict(fase_calculada_modelo=phase,fase_final=phase,origen_fase_final='AUTOMATICO',condicion_dia=condition,
                caudal_operacional=q,cu_pp=c,riego_activo=r,drenaje_proxy_activo=g,
                fecha_primer_riego_reconocido=first,fecha_primer_cu_pp_valido=first_proxy,fecha_ultimo_riego_real=last,
                fecha_ultima_ley_cu_pp=latest_proxy,valor_ultima_ley_cu_pp=cs.get(latest_proxy),dias_sin_riego_confirmados=days,
                proxy_previo_riego=int(bool(first and proxies and min(proxies)<first)),
                transicion_mismo_dia=int(bool(first and first_proxy==first)),
                consolidacion_modulos='MIXTO' if phase=='MIXTO' else 'NO_EVALUABLE' if phase=='NO_EVALUABLE' else 'UNANIME',
                nivel_alerta=alert_level(pad,phase,days,r),version_modelo=MODEL_VERSION,version_alerta=ALERT_VERSION)
