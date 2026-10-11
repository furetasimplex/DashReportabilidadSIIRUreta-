"""Produce tablas del diagnóstico a partir de las capturas locales, sin SQL."""
import json
from pathlib import Path
from decimal import Decimal
from .inspeccionar import OUT
def read(n):return json.loads((OUT/(n+'.json')).read_text(encoding='utf-8'))
def table(headers,rows):
    fmt=lambda x:'NULL' if x is None else str(x).replace('|','/').replace('\n',' ')
    return '\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('|'+ '|'.join(fmt(x) for x in row)+'|\n' for row in rows)+'\n'
def write(n,s):(OUT.parent/(n+'.md')).write_text(s,encoding='utf-8')
def main():
    key=lambda r:(r['Fecha'],r['Turno'])
    by=lambda name,k:{k(r):r for r in read(name)}
    cache=by('sept_reporte_turno_cache_emision_test',key);direct=by('sept_reporte_directo',key)
    prop=by('sept_v_apilado_proporcion_final_reporte_test',key)
    factor=by('sept_v_ajuste_camiones_emision_test',lambda r:r['Fecha'])
    hist=by('sept_Historico_Apilado_Diario',lambda r:r['Fecha'])
    daily=by('sept_v_reporte_diario_apilado_test',lambda r:r['Fecha'])
    ctl=by('sept_Control_Apilado_TMH_v2_test',lambda r:r['Fecha'])
    srr=by('sept_v_srr_tms_origen_turno_emision_test',key)
    rows=[];srrrows=[];histrows=[]
    for (d,t),r in sorted(cache.items()):
        if d=='2026-09-05':continue
        p=prop[(d,t)];v=daily[d];h=hist[d];f=factor[d]['Factor_Aplicacion_Reportes']
        oldkeys={x.lower():x for x in h}
        old=h['TMH_Bruto_'+t]*(1-h['Humedad_Turno_'+t]/100)*f-h[oldkeys['sal_turno_'+t.lower()]]
        cause={'2026-09-04':'Vista sin factor V2; cache y directo coinciden',
               '2026-09-06':'Vista sin factor V2; cache y directo coinciden',
               '2026-09-07':'A: factor distinto de 1; B: cache usa TMH previo (35896)',
               '2026-09-08':'Cache usa TMH previo 35897/35896; factor también usa histórico previo',
               '2026-09-09':'Cache usa TMH previo 35896/35896; factor numérico=1',
               '2026-09-10':'Cache actualizado; histórico/factor aún previos'}[d]
        rows.append([d,t,p['Apilado_TMS_Con_SRR'],r['Apilado_TMS_Real'],direct[(d,t)]['Apilado_TMS_Real'],f,h['TMH_Bruto_'+t],v['TMH_Bruto_'+t],old,cause])
        source=srr[(d,t)]
        srrrows.append([d,t,source['Fuente_SRR'],p['TMS_SRR'],source['Ton_SRR_Origen_Raw'],source['Ton_SRR_Usado_Actual'],source['Flag_SRR_Capeado_Por_Apilado'],None if p['Prop_Final_SRR'] is None else 100*p['Prop_Final_SRR'],r['SRR'],direct[(d,t)]['SRR'],Decimal(r['Apilado_TMS_Real'])*Decimal(r['SRR'])/100])
    for d in sorted(hist):
        histrows.append([d,ctl[d]['Fecha_Calculo'],hist[d]['Fecha_Calculo'],factor[d]['Fecha_Calculo'],next(r['Fecha_Actualizacion'] for k,r in cache.items() if k[0]==d),hist[d]['TMH_Bruto_Dia'],ctl[d]['TMH_Apilado_Total_Dia'],factor[d]['Apilado_TMH_Bruto_Original']])
    write('COMPARACION_SEPTIEMBRE','# Comparación exacta de septiembre\n\nEl directo ejecuta el cuerpo vigente del SP con la única escritura de trazabilidad redirigida a #traza. No se alteró el SP. Cache conserva su redondeo decimal(…,6); diferencias <0,000001 frente al cálculo float son de representación.\n'+table(['Fecha','Turno','Vista TMS sin factor V2','Cache TMS','Directo SP TMS','Factor V2 aplicado','TMH histórico previo','TMH vigente','TMS reproducido con histórico × factor','Diagnóstico'],rows)+'\n## Fotografías persistidas\n'+table(['Fecha','Control calculado','Histórico calculado','Factor calculado','Cache actualizado','TMH histórico','TMH vigente','TMH input persistido factor'],histrows)+'\n## SRR: masa y porcentaje\n'+table(['Fecha','Turno','Origen efectivo','TMS_SRR vista antigua','Masa origen','Masa usada factor','Cap activo','% vista antigua','% cache','% directo SP','Masa reconstruida %cache'],srrrows))
    old=read('baseline_inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test')[0]
    new=read('secuencia_A_historico')['pasos'][-1]['factor'][0]
    write('INPUTS_FACTOR','# Inputs y salidas del mantenedor del factor — 10-09\n\nIzquierda: fila persistida. Derecha: mantenedor SQL simulado con histórico refrescado desde su vista vigente. Todas las columnas conservadas. El SP puro ejecutado con histórico real vuelve a leer 71793: evidencia en evidencia/calculo_factor_actual.json.\n'+table(['Columna','Persistido','Con histórico actualizado'],[[k,v,new.get(k)] for k,v in old.items()]))
    factorrows=[];reprows=[]
    for n in ['A_original','B_original','A_historico','B_historico']:
        run=read('secuencia_'+n);last=run['pasos'][-1];f=last['aplicacion'][0]
        factorrows.append([n,f['Factor_Ajuste_Calculado'],f['Factor_Aplicacion_Reportes'],f['Apilado_TMH_Bruto_Original'],f['Apilado_TMH_Bruto_Ajustado'],run['persistentes_identicos']])
        for r in last['cache']:reprows.append([n,*[r[k] for k in ['Turno','Apilado_TMS_Real','STOCK','MINA','SRR','FeS_Real','Malla_Menos_1_2_Real']]])
    write('SECUENCIAS','# Secuencias simuladas\n\nA_original=Factor→Cache; B_original=Cache→Factor→Cache. Ambas omiten histórico. A_historico=Histórico→Factor→Cache; B_historico=Histórico→Cache→Factor→Cache. Control_Apilado ya tiene TUM vigente en todas.\n\nSolo tablas temporales de sesión, sin UPDATE/DELETE/INSERT sobre tablas persistentes. Se reutilizan cuerpos SQL vigentes, con destinos y fuentes materializadas desviados a #hist/#factor/#cache/#traza/#srr/#ajuste. El motor ejecutó las mismas fórmulas; no se instalaron SP ni vistas. Se verificaron filas persistentes de histórico/factor/cache/trazabilidad idénticas antes/después y se hizo rollback final. Clays no se refrescó: sus fuentes se mantuvieron constantes para aislar el orden solicitado.\n'+table(['Secuencia','Factor calculado','Factor reportes','TMH original','TMH ajustado','Persistentes intactos'],factorrows)+table(['Secuencia','Turno','Apilado TMS','STOCK %','MINA %','SRR %','FeS','Malla -1/2'],reprows))
    capfile=OUT/'secuencia_CAP_SINTETICO.json'
    if capfile.exists():
        cap=read('secuencia_CAP_SINTETICO');rows=[]
        for i,step in enumerate(cap['pasos'],1):
            rows.append([i,step['paso'],step['aplicacion'][0]['Factor_Aplicacion_Reportes'],*[r['Apilado_TMS_Real'] for r in step['cache']],*[r['Ton_SRR_Usado_Actual'] for r in step['srr']],*[r['Flag_SRR_Capeado_Por_Apilado'] for r in step['srr']]])
        write('CAP_CONVERGENCIA','# Prueba condicional de cap — sintética, no estado real DEV\n\nMismos orígenes IMP reales del 10-09 y mismo histórico actualizado; únicamente la copia temporal del cache arranca con 1000 TMS por turno. Ningún control real 04–10 tiene cap activo. Esta prueba ilustra el riesgo de alimentar el factor con una fotografía insuficiente de apilado.\n'+table(['Paso','Acción','Factor aplicado','Cache A','Cache B','SRR A','SRR B','Cap A','Cap B'],rows)+'\nPersistentes idénticos: '+str(cap['persistentes_identicos'])+'. No demuestra convergencia universal.\n')
if __name__=='__main__':main()
