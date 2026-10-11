"""Organiza evidencia local; no conexiones ni cambios funcionales."""
import json
import re
from decimal import Decimal as D
from pathlib import Path

ROOT=Path(__file__).parent
OUT=ROOT/'cierre'
def read(n): return json.loads((OUT/(n+'.json')).read_text(encoding='utf-8'))
def table(headers,rows):
    def cell(v): return 'NULL' if v is None else str(v).replace('|','/').replace('\n',' ')
    return '\n|'+'|'.join(headers)+'|\n|'+'|'.join(['---']*len(headers))+'|\n'+''.join('|'+ '|'.join(cell(v) for v in row)+'|\n' for row in rows)+'\n'
def write(n,s): (OUT/(n+'.md')).write_text(s,encoding='utf-8')
def same(a,b):
    if a is None or b is None:return a is b
    try:return D(str(a))==D(str(b))
    except Exception:return a==b
def norm(s):
    return re.sub(r'\s+',' ',re.sub(r'\b(CREATE|ALTER)\s+(?:OR\s+ALTER\s+)?','',s, count=1,flags=re.I)).strip()

def main():
    rt=read('RT'); ro=read('RO'); key=lambda r:tuple(r[k] for k in ('fecha_operacional','turno','equipo_codigo'))
    ros={key(r):r for r in ro}
    rows=[]
    for r in rt:
        o=ros.get(key(r),{})
        rows.append([*key(r),o.get('contingencia_pi_activa','NO_APLICA_PRE_CORTE'),r['valor_pi_final'],r['valor_turno_tum'],r['estado_tecnico_pi'],r['fuente_resuelta'],r['valor_final_resuelto'],o.get('fuente_resuelta','NO_APLICA_PRE_CORTE'),o.get('valor_final_resuelto'),o.get('motivo_decision','FUERA_RO_PRE_CORTE')])
    write('01_trazabilidad','Evidencia extraída de DEV el 19-09-2026. 70 filas RT, 56 RO. RO no publica el 31-08; no se interpreta su ausencia como cero ni pendiente.\n'+table(['Fecha','Turno','Equipo','Contingencia','PI','TUM','Estado técnico PI','Fuente RT','RT','Fuente RO','RO','Estado/motivo RO'],rows))
    inventory='Inventario congelado: módulo completo untracked; no existe baseline Git interno que permita distinguir qué archivos del módulo fueron modificados en cada fase previa.\n\nPython tracked modificados: `layout.py`, `report_export/report_export.py`. Otros tracked: `.env.example`, `assets/theme.css`. Cambios Programa/Plan y sidebar preexistentes, preservados.\n'
    files=read('inventario_archivos')
    for title,predicate in [('Python del módulo',lambda p:p.endswith('.py') and 'test_' not in Path(p).name),('Tests del módulo',lambda p:Path(p).name.startswith('test_')),('SQL de implementación / evidencia previa',lambda p:p.endswith('.sql') and 'backup' not in p and 'rollback_' not in p),('Backups',lambda p:'backup' in p),('Rollback',lambda p:'rollback_' in p)]:
        inventory+='\n**'+title+'**\n\n'+''.join('- `'+p+'`\n' for p in files if predicate(p))
    inventory+='\nOtros tests/scripts untracked iniciales: `report_export/tests/test_programa_plan_cero_excel.py`, `scripts/validate_programa_plan_cero_dev.py`. Otros artefactos iniciales constan en `git_status.txt`.\n'
    objects=read('objetos_dev')
    inventory+='\n**Objetos TEST encontrados en DEV (existencia comprobada; no implica creados por esta fase)**\n'+table(['Objeto','Tipo','Creación','Modificación'],[[r['nombre'],r['type_desc'],r['create_date'],r['modify_date']] for r in objects if r['nombre'].endswith('_test')])
    inventory+='\n**Correspondencia de los ocho DDL de expansión con DEV y rollback**\n'
    checks=[]
    for f in sorted((ROOT/'ddl').glob('*.sql')):
        deployed=OUT/f.name; rollback=ROOT/('rollback_'+f.name)
        checks.append([f.stem, deployed.exists() and norm(f.read_text(encoding='utf-8'))==norm(deployed.read_text(encoding='utf-8')),str(rollback),rollback.exists()])
    inventory+=table(['Objeto','DDL coincide normalizado','Rollback','Existe'],checks)
    inventory+='\nLa cobertura de rollback es 8/8 para expansión_v1. No se puede certificar rollback integral del módulo: las tablas de acciones/estado, SP de registro y resolvedor operacional no tienen rollback dedicado en esta carpeta. `acciones_actual/` y `objetos_protegidos_antes.json` son evidencia de definiciones, no un rollback integral probado. No se ejecutó ningún rollback.\n'
    write('02_inventario_rollback',inventory)
    dates=['2026-08-31','2026-09-07','2026-09-08','2026-09-10','2026-09-13']
    matrix=[]; all_changes=[]; balances={}
    for day in dates:
        a=read('balance_'+day+'_oficial');b=read('balance_'+day+'_TEST')
        aa={r['Flujo']:r for r in a} if isinstance(a,list) else {}
        bb={r['Flujo']:r for r in b} if isinstance(b,list) else {}
        balances[day]=(aa,bb)
        for f in ['F4','F6','F7','F8','F9','F12','F13','F20','F25']:
            av=aa.get(f,{}).get('Tonelaje');bv=bb.get(f,{}).get('Tonelaje')
            cls='PENDIENTE_TUM' if not bb else ('SIN_CAMBIO' if aa[f]==bb[f] else ('CAMBIO_ESPERADO_NUEVA_GOBERNANZA' if day=='2026-09-13' else 'CAMBIO_ESPERADO_CONTINGENCIA'))
            matrix.append([day,f,av,bv if bb else 'SIN_RESULTADO: ERROR 51025',str(D(bv)-D(av)) if av is not None and bv is not None else None,cls])
        for f in aa.keys()&bb.keys():
            for col in aa[f]:
                if col!='Flujo' and aa[f][col]!=bb[f][col]:
                    all_changes.append([day,f,col,aa[f][col],bb[f][col]])
    write('03_balance_matriz','Baseline = SP oficial actual DEV, modelo_id=1. TEST = SP desplegado contingencia_test. Ambos ejecutados; no se usó un backup como sustituto del baseline. Valores decimales originales en JSON.\n'+table(['Fecha','Flujo','Oficial TMS','TEST TMS','Delta','Clasificación'],matrix)+'\nClasificaciones de cambios por fuente para los flujos solicitados; la diferencia estructural adicional entre SP oficial y TEST exige revisar su alineación antes de promover. El 08-09 se bloquea todo el resultado, no solo F20.\n\n**Todos los campos/ flujos que cambiaron**\n'+table(['Fecha','Flujo','Campo','Oficial','TEST'],sorted(all_changes)))
    a,b=balances['2026-09-13']; s='Impacto 13-09: NORMAL → PI oficial; PI=0 válido. RT→TUM y RO→PI=0 en CV002 A y CV003 A/B se clasifica CAMBIO_ESPERADO_NUEVA_GOBERNANZA, no regresión. CV002 B tiene PI=32768, por lo que no pertenece al caso PI=0.\n'
    s+=table(['Turno','Equipo','PI','Estado técnico','TUM','RT','RO'],[[r['turno'],r['equipo_codigo'],r['valor_pi_final'],r['estado_tecnico_pi'],r['valor_turno_tum'],r['valor_final_resuelto_legacy'],r['valor_final_resuelto']] for r in ro if r['fecha_operacional']=='2026-09-13' and r['equipo_codigo'] in ('SRR_CV002','SRR_CV003')])
    for f,g,h,bruto in [('F6','F8','F10','F12'),('F7','F9','F11','F13')]:
        s+=f'\n**{f} = TMS bruto {bruto} − {g} − {h}**\n\n'
        for label,bal in [('Baseline',a),('TEST',b)]:
            vals=[bal[x]['Tonelaje'] for x in (bruto,g,h,f)]
            s+=f'{label}: {vals[0]} − {vals[1]} − {vals[2]} = {vals[3]}.\n\n'
        delta=lambda x:D(b[x]['Tonelaje'])-D(a[x]['Tonelaje'])
        s+=f'Δ{f} = Δ{bruto} − Δ{g} − Δ{h} = {delta(bruto)} − ({delta(g)}) − ({delta(h)}) = {delta(f)}.\n\n'
    s+='FCu neto TM1 = FCu bruto TM1 − FCu F8; TM2 = FCu bruto TM2 − FCu F9. Ley neta = 100 × FCu neto/TMS neto (0 si TMS=0; NULL si falta masa o fino). Las sales F10/F11 no restan cobre. Valores de ley/FCu y otras dependencias: 03_balance_matriz.md.\n'
    write('04_impacto_13',s)
    diag=read('cv025_diagnostico_pi')
    s='**07-09 mixto**\n\nA NORMAL: PI=0, TUM=0, RO=PI=0. B CONTINGENCIA: PI=0, TUM=31387, RO=TUM=31387. Masa operacional = 0+31387=31387 TMH; F20 TEST = 31387×0,90 = 28248,300000 TMS, frente a oficial 0.\n\nF20 baseline prioriza `COALESCE(TRY_CONVERT(float,cv025_tot),TRY_CONVERT(float,cv025tot))`; un tag primario válido en cero no activa fallback al secundario. Calcula mínimo/máximo diario y mínimo del día siguiente, valida delta 0..100000; solo usa recorrido interno en las ramas de ausencia/reset/spike. Evidencia exacta:\n'
    s+=table(['Fecha','Mínimo','Máximo','Muestras'],[[r['fecha'],r['minimo'],r['maximo'],r['muestras']] for r in diag])
    s+='\nCausa numérica del baseline 07-09: mínimo 07=1759662,625; máximo 07=1759662,625; mínimo 08=1759662,625. Delta siguiente−mínimo=0, válido dentro de [0,100000]. La rama normal devuelve 0 y F20=0×0,90=0. Es señal congelada; no reset, no spike ni ausencia de señal.\n'
    s+='\n**08-09 pendiente**\n\nA: PI=0, TUM=4616, contingencia activa, RO=TUM=4616. B: PI=0, TUM=NULL, contingencia activa, RO=NULL, fuente/estado=PENDIENTE_TUM. No reaparece PI y no se fabrica cero. El guard del SP lanza 51025 antes de emitir su SELECT final: no existe una fila F20=NULL o F20=0; no se emite la matriz de Balance. Error original en balance_2026-09-08_TEST.json. No se ha verificado una pantalla de Balance que consuma esta variante; no se atribuye una representación visual no observada.\n'
    av=a['F20']['Tonelaje'];bv=b['F20']['Tonelaje']
    s+=f'\n**13-09 normal**\n\nF20 oficial={av}; TEST={bv}; delta={D(bv)-D(av)}. PI A+B de RO = 17675,625+29705,625=47381,25 TMH, ×0,90=42643,125 TMS. La metodología diaria vigente usa el otro recorrido/ventana y se conserva, según los mínimos de la tabla y las definiciones SQL; suma de turnos solo diagnóstica.\n'
    s+='\nMétodo diario actual: mínimo 14−mínimo 13 = 1988654,5−1941273,25=47381,25 TMH (delta válido). En este día coincide exactamente con PI A+B. No se cambió la metodología normal. Reclamo toma otra base/tag: 47381,5 TMH; esa diferencia de 0,25 TMH ya existe entre consumidores y no se homogeneizó.\n'
    write('05_cv025',s)
    s='Cadena TEST: `reclamo.cv25_diario` + RO → `v_cv25_diario_contingencia_test` → `v_preliminar_cv25_contingencia_test` → `v_preliminar_cv25_con_acumulado_contingencia_test` → `v_reclamo_diario_contingencia_test`; contraste en `v_diferencia_cv25_contingencia_test`. Dependencias exactas en dependencias.json.\n\nFórmula preservada de humedad: TMS = TMH × (1 − COALESCE(humedad_pct,0)/100). En NORMAL devuelve base.tms_dia; en contingencia aplica la misma humedad propia a SUM(RO A+B). No utiliza el 0,90 del Balance. En las cinco fechas la humedad almacenada es NULL: el factor efectivo es 1.\n'
    old=read('datos_reclamo.v_cv25_diario'); new=read('datos_reclamo.v_cv25_diario_contingencia_test')
    by={r['fecha']:r for r in old}
    s+=table(['Fecha','TMH oficial','TMH TEST','TMS oficial','TMS TEST','Flag TEST','Normal igualdad de valores'],[[r['fecha'],by[r['fecha']]['tmh_dia'],r['tmh_dia'],by[r['fecha']]['tms_dia'],r['tms_dia'],r['flag_preliminar'],all(same(v,r[k]) for k,v in by[r['fecha']].items()) if r['fecha'] in ('2026-08-31','2026-09-13') else 'No aplica'] for r in new])
    s+='\nIgualdad numérica exacta en controles normales; el tipo SQL de las masas pasa de decimal a float en TEST, por CONVERT(float) en la rama RO. No es identidad de tipos; riesgo de precisión para otros valores. Las cuatro vistas dependientes coinciden con las oficiales al normalizar espacios/CREATE y sustituir únicamente el sufijo _contingencia_test.\n'
    for n in ('v_preliminar_cv25','v_preliminar_cv25_con_acumulado','v_reclamo_diario'):
        x=read('extra_reclamo.'+n);y=read('extra_reclamo.'+n+'_contingencia_test')
        s+=f'\n{n}: filas oficial={len(x)}, TEST={len(y)}. '
        if isinstance(x,list) and isinstance(y,list):
            normrows=lambda z:sorted(json.dumps(r,sort_keys=True) for r in z if r.get('fecha_operacion')=='2026-09-13')
            s+=f'Igualdad filas del 13-09={normrows(x)==normrows(y)}. '
            if not x: s+='Sin filas en controles: no demuestra reparto con datos ni acumulados.'
    s+='\n\nSe preservan expresiones de humedad, topografía, rotopalas, densidad, campañas, módulos y avances en las vistas dependientes, salvo sustitución de nombres de la cadena. Los casos sin horas no son repartibles; no deben interpretarse como validación de tonelaje asignado a módulos.\n'
    write('06_reclamo',s)
    bases=read('datos_inventar_SpcHidr.v_bd_ton_t12_contingencia_test'); pts=read('datos_inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test'); actual=read('extra_inventar_SpcHidr.v_peso_real_torre_turno_excel')
    oldrep={r['Dia']:r for r in read('extra_inventar_SpcHidr.v_representatividad_diaria_calculada')};newrep={r['Dia']:r for r in read('extra_inventar_SpcHidr.v_representatividad_diaria_calculada_contingencia_test')}
    s='Representatividad mantiene ventanas propias (ts_ini/ts_fin y solape con turno TUM), sin imponer suma diaria PI operacional en NORMAL. Umbral de presentación 0,75 permanece en report_export/report_export.py y callbacks/reportabilidad_cb.py. El cociente SQL se limita a 1; denominador no positivo/faltante → NULL.\n'
    rr=[]
    for r in sorted(pts,key=lambda x:(x['Fecha'],x['Torre'],x['Turno'])):
        if r['Torre'] not in ('T1','T2'):continue
        day=r['Fecha'];tm='TM1' if r['Torre']=='T1' else 'TM2';t=r['Turno'];base=next(x for x in bases if x['Fecha']==day)
        pr=next((x for x in actual if x['Fecha']==day and x['Turno']==t and x['Torre']==r['Torre']),{})
        rr.append([day,tm,t,base['Ton_Intervalo_'+tm+'_T'+t],base['TMH_'+tm+'_T'+t+'_Resuelto'],r['Fuente_Calculo'],r['PesoTeo_Quimico_Actual'],r['PesoTeo_Quimico_Candidato'],r['PesoTeo_Fisico_Actual'],r['PesoTeo_Fisico_Candidato'],pr.get('PesoReal_Quimico'),pr.get('PesoReal_Fisico'),oldrep[day][tm+'_Turno'+t+'_Quimico'],newrep[day][tm+'_Turno'+t+'_Quimico'],oldrep[day][tm+'_Turno'+t+'_Fisico'],newrep[day][tm+'_Turno'+t+'_Fisico']])
    s+=table(['Fecha','TM','Turno','Base PI intervalo','Base TEST','Fuente TEST','Teórico Q PI','Teórico Q TEST','Teórico F PI','Teórico F TEST','Peso Q real','Peso F real','Rep Q oficial','Rep Q TEST','Rep F oficial','Rep F TEST'],rr)
    s+='\nPesos, bases, ventanas y fracciones exactas sin redondeo editorial en los JSON de peso_teorico y bd_ton. La fuente normal es PI_INTERVALO; en contingencia TUM_TURNO, ajustado por solape.\n'
    write('07_representatividad',s)

if __name__=='__main__':main()
