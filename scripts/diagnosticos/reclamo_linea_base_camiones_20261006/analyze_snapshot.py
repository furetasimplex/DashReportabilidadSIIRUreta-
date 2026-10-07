"""Derive campaign 10 baseline, source, system and freeze timelines offline."""
import csv
import json
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path

BASE=Path(__file__).resolve().parent
data=json.loads((BASE/'snapshot.json').read_text(encoding='utf-8'))['results']
config={r['clave']:r['valor'] for r in data['config']}
cut=date.fromisoformat(config['FECHA_CORTE_SISTEMA'])
def num(value): return Decimal(str(value or '0'))
def day(value): return date.fromisoformat(value[:10])
def write(name,rows,fields):
    with (BASE/name).open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        w.writeheader();w.writerows(rows)

sources=defaultdict(list)
systems=defaultdict(list)
for r in data['source']: sources[r['modulo_id']].append(r)
for r in data['system']: systems[r['modulo_id']].append(r)
for v in sources.values(): v.sort(key=lambda r:r['fecha'])
for v in systems.values(): v.sort(key=lambda r:r['fecha'])

summary=[]
detail=[]
for module in data['modules']:
    mid=module['modulo_id']; sr=sources[mid]; sy=systems[mid]
    pre=[r for r in sr if day(r['fecha'])<cut]
    prior=sum((num(r['volumen_diario_m3']) for r in pre),Decimal(0))
    actual=num(module['m3_camiones_previo'])
    diff=prior-actual
    if not pre: classification='SIN_HISTORICO_PRE_CORTE' if actual==0 else 'PREVIO_INCOMPLETO'
    elif abs(diff)<=Decimal('0.001'): classification='OK'
    elif actual==0 and prior!=0: classification='PREVIO_FALTANTE'
    else: classification='PREVIO_INCOMPLETO'
    latest=sy[-1] if sy else None
    sys_date=day(latest['fecha']) if latest else None
    sys_cum=num(latest['m3_camiones_acum']) if latest else Decimal(0)
    aligned=[r for r in sr if sys_date and day(r['fecha'])<=sys_date]
    aligned_source=aligned[-1] if aligned else None
    latest_source=sr[-1] if sr else None
    source_aligned=num(aligned_source['volumen_final_reclamado']) if aligned_source else None
    source_latest=num(latest_source['volumen_final_reclamado']) if latest_source else None
    start=day(sr[0]['fecha']) if sr else None
    end=day(sr[-1]['fecha']) if sr else None
    present={day(r['fecha']) for r in sr}
    missing=[]
    if start and end:
        current=start
        while current<=end:
            if current not in present: missing.append(current.isoformat())
            current+=timedelta(days=1)
    summary.append({
        'campaña_id':10,'pad_id':2,'modulo_id':mid,'modulo_numero':module['modulo_numero'],
        'fecha_corte':cut,'fecha_congelamiento':module['fecha_congelamiento'],
        'fecha_linea_base':module['fecha_linea_base'],'m3_previo_actual':actual,
        'm3_previo_esperado':prior,'diferencia_linea_base':diff,
        'clasificacion':classification,'filas_pre_corte':len(pre),
        'primera_fecha_fuente':start,'ultima_fecha_pre_corte':pre[-1]['fecha'] if pre else '',
        'ultima_fecha_sistema':sys_date,'m3_sistema_actual':sys_cum,
        'm3_total_reconstruido':prior+sys_cum,
        'fecha_fuente_alineada':aligned_source['fecha'] if aligned_source else '',
        'm3_acumulado_fuente_alineado':source_aligned,
        'diferencia_vs_fuente_alineado':(prior+sys_cum-source_aligned) if source_aligned is not None else '',
        'ultima_fecha_fuente':latest_source['fecha'] if latest_source else '',
        'm3_acumulado_fuente_ultimo':source_latest,
        'diferencia_vs_fuente_ultimo':(prior+sys_cum-source_latest) if source_latest is not None else '',
        'huecos_fechas_fuente':';'.join(missing),
    })
    if mid in (81,87):
        running=Decimal(0)
        sys_by_date={r['fecha']:r for r in sy}
        previous=None
        for r in sr:
            value=num(r['volumen_diario_m3']);running+=value
            final=num(r['volumen_final_reclamado'])
            sysrow=sys_by_date.get(r['fecha'])
            detail.append({
                'fecha':r['fecha'],'campaña':r['campaña'],'campaña_id':r['campaña_id'],
                'modulo':r['modulo'],'modulo_id':mid,'lado_corte':'PRE_CORTE' if day(r['fecha'])<cut else 'DESDE_CORTE',
                'volumen_diario_m3':value,'volumen_final_reclamado':final,
                'avance_porcentaje':r['avance_porcentaje'],'suma_deltas_desde_primera_fila':running,
                'brecha_final_vs_suma':final-running,
                'delta_acumulado_fuente':final-previous if previous is not None else '',
                'sistema_m3_dia':num(sysrow['m3_camiones_dia']) if sysrow else '',
                'sistema_m3_acum':num(sysrow['m3_camiones_acum']) if sysrow else '',
                'brecha_diaria_fuente_sistema':value-num(sysrow['m3_camiones_dia']) if sysrow else '',
            })
            previous=final

write('detalle_m17_m23.csv',detail,list(detail[0]))
write('campania10_auditoria.csv',summary,list(summary[0]))

log_by_id={r['ejecucion_id']:r for r in data['execution_logs']}
chron=[]
for log in sorted(data['automation_logs'],key=lambda r:(r['fecha_evento'],r['log_id'])):
    execution=log_by_id.get(log['ejecucion_id'],{})
    module=next((r for r in data['modules'] if r['modulo_id']==log['modulo_id']),{})
    chron.append({'modulo_id':log['modulo_id'],'modulo_numero':log['modulo_numero'],
                  'fecha_evento':log['fecha_evento'],'log_id':log['log_id'],
                  'ejecucion_id':log['ejecucion_id'],'accion':log['accion'],
                  'detalle':log['detalle'],'procedimiento_ejecucion':execution.get('procedimiento',''),
                  'estado_ejecucion':execution.get('estado',''),
                  'fecha_inicio_ejecucion':execution.get('fecha_inicio',''),
                  'fecha_congelamiento_modulo':module.get('fecha_congelamiento',''),
                  'fecha_linea_base_modulo':module.get('fecha_linea_base','')})
write('cronologia_congelamiento.csv',chron,list(chron[0]))
print('cut',cut,'modules',len(summary),'pre_cut_rows',sum(r['filas_pre_corte'] for r in summary),
      'baseline_differences',[r['modulo_id'] for r in summary if abs(r['diferencia_linea_base'])>Decimal('0.001')])
for r in summary:
    if r['modulo_id'] in (81,87): print(r)
