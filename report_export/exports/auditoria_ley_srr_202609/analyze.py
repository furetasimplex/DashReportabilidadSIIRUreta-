from pathlib import Path
from collections import Counter
import csv,json,math
ROOT=Path(__file__).parent
def read(n): return json.loads((ROOT/(n+'.json')).read_text(encoding='utf-8'))
def num(v):
    try: return float(v) if v is not None and v!='' else None
    except (TypeError,ValueError): return None
def keyed(n): return {r['Fecha']:r for r in read(n)}
res=keyed('residual_sql'); mov=keyed('mov_daily'); imp=keyed('imp_normalizado_daily')
of=read('oficial_celdas'); gen=of['Generador Reporte diario']; srr=of['SRR']
out=[]
for day in range(1,31):
    date=f'2026-09-{day:02}'
    r=res[date]; t=num(r['SRR_TMS_Dia']); residual=num(r['Ley_CuT_Real_srr'])
    published=num(r['Ley_Publicada'])
    assert (residual is None and published is None) or (residual is not None and published is not None and abs(residual-published)<=1e-12)
    m=num(mov.get(date,{}).get('Ley_CuT_SRR_MOV_CAM')); i=num(imp.get(date,{}).get('Ley_CuT_SRR_IMP'))
    g=gen.get(f'O{day+20}',{}); z=srr.get(f'Z{day+5}',{})
    official=num(g.get('v')); aux=num(z.get('v'))
    kind='FORMULA' if g.get('formula_attrs') is not None else 'VALOR_FIJO' if g.get('v') is not None else 'VACIO'
    estado='NO_EVALUABLE' if residual is None else 'CERO' if residual==0 else 'NEGATIVA' if residual<0 else 'POSITIVA'
    final=None; source='NULL'; note=''; pending=False
    if t is None: reason='SRR_TMS_NO_EVALUABLE'; pending=True
    elif t==0: reason='SIN_TONELAJE_SRR'
    elif t<0: reason='SRR_TMS_NEGATIVO_NO_DEFINIDO'; pending=True
    elif residual is None:
        reason='RESIDUAL_NULL_REGLA_NO_DEFINIDA'; pending=True
        note='Existe IMP valido, pero NULL no cumple residual <= 0; requiere decision explicita.'
    elif residual>0: final=residual;source='RESIDUAL';reason='RESIDUAL_VALIDA'
    elif m is not None and m>0: final=m;source='MOV_CAM';reason='FALLBACK_MOV_CAM'
    elif i is not None and i>0: final=i;source='IMP';reason='FALLBACK_IMP'
    else: reason='SIN_LEY_VALIDA_CON_TONELAJE'
    comparable=final is not None and official is not None
    equal='NO_COMPARABLE' if not comparable else 'SI' if abs(final-official)<=1e-9 else 'NO'
    out.append(dict(Fecha=date,SRR_TMS=t,Ley_CuT_SRR_Calculada=residual,Estado_Ley_Calculada=estado,
        Ley_CuT_SRR_MOV_CAM=m,Ley_CuT_SRR_IMP=i,Ley_CuT_SRR_Actual_SIIR=published,
        Ley_CuT_SRR_Oficial=official,Tipo_Valor_Oficial=kind,Ley_CuT_SRR_Final_Simulada=final,
        Fuente_Final_Simulada=source,Motivo_Simulacion=reason,Coincide_Con_Oficial=equal,
        SRR_TMS_Fisico=num(r['SRR_TMS_Fisico']),Celda_Oficial=f'Generador Reporte diario!O{day+20}',
        Formula_Oficial=g.get('f'),Ley_SRR_Hoja_Auxiliar=aux,Celda_SRR=f'SRR!Z{day+5}',
        Tipo_Valor_SRR='FORMULA' if z.get('formula_attrs') is not None else 'VALOR_FIJO' if z.get('v') is not None else 'VACIO',
        Formula_SRR=z.get('f'),SRR_TMS_Oficial=num(gen.get(f'M{day+20}',{}).get('v')),
        Registros_MOV_CAM=mov.get(date,{}).get('Registros',0),Ton_MOV_CAM=mov.get(date,{}).get('Ton_SRR'),
        Registros_IMP=imp.get(date,{}).get('Registros',0),Ton_IMP=imp.get(date,{}).get('Ton_SRR'),
        Simulacion_Pendiente_Definicion=pending,Observacion=note))
def write_csv(name,rows):
    with (ROOT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';');w.writeheader();w.writerows(rows)
write_csv('diagnostico_septiembre_2026.csv',out)
(ROOT/'diagnostico_septiembre_2026.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
summary=dict(dias=30,tonelaje_cero=sum(r['SRR_TMS']==0 for r in out),tonelaje_positivo=sum(r['SRR_TMS'] is not None and r['SRR_TMS']>0 for r in out),tonelaje_null=sum(r['SRR_TMS'] is None for r in out),estados=dict(Counter(r['Estado_Ley_Calculada'] for r in out)),fuentes=dict(Counter(r['Fuente_Final_Simulada'] for r in out)),motivos=dict(Counter(r['Motivo_Simulacion'] for r in out)),coincidencia=dict(Counter(r['Coincide_Con_Oficial'] for r in out)),tipos_oficial=dict(Counter(r['Tipo_Valor_Oficial'] for r in out)),tipos_auxiliar=dict(Counter(r['Tipo_Valor_SRR'] for r in out)),dias_mov=len(mov),dias_imp=len(imp),residual_materializado_coincide=30,tolerancia_ley_puntos_porcentuales=1e-9)
(ROOT/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
write_csv('registros_MOV_CAM_SRR.csv',read('mov_srr'))
write_csv('registros_IMP_SRR_vigentes.csv',read('imp_normalizado'))
print(json.dumps(summary,ensure_ascii=False,indent=2))
for r in out: print(r['Fecha'],r['Estado_Ley_Calculada'],r['Fuente_Final_Simulada'],r['Coincide_Con_Oficial'])
