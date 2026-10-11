"""Offline arithmetic and provenance checks; no database access."""
import json
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec=28
BASE=Path(__file__).resolve().parent
snap=json.loads((BASE/'snapshot.json').read_text(encoding='utf-8'))
extra=json.loads((BASE/'followup.json').read_text(encoding='utf-8'))
snap['focused_queries']=extra['queries']
(BASE/'snapshot.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
o=snap['objects']; q=extra['queries']
def D(x): return Decimal(str(x))
raw_real={(r['Turno'],r['Torre']):r for r in o['v_peso_real_torre_turno_excel']['rows']}
raw_teo={(r['Turno'],r['Torre']):r for r in o['v_peso_teorico_turno_torre_excel']['rows']}
lab={(r['Turno'],r['Torre']):r for r in o['Informe_TM_lab']['rows']}
tmh=o['v_datos_apilado_tmh_v2']['rows'][0]
sal=o['v_sal_ajustada']['rows'][0]
cache={r['Turno']:r for r in o['reporte_turno_cache_emision_test']['rows']}
rep=q['rep'][0]
results={}
for shift,official in [('A',D('73.3121')),('B',D('73.3035'))]:
    towers={}
    for num,tower in [(1,'T1'),(2,'T2')]:
        real=raw_real[(shift,tower)]; teo=raw_teo[(shift,tower)]
        ratio=D(real['PesoReal_Fisico'])/D(teo['PesoTeo_Fisico'])
        rep_db=D(rep[f'TM{num}_Turno{shift}_Fisico'])
        assert abs(ratio-rep_db)<D('0.00000001')
        lr=lab.get((shift,tower))
        towers[f'TM{num}']={
            'peso_real_fisico_kg':real['PesoReal_Fisico'],
            'peso_teorico_fisico_kg':teo['PesoTeo_Fisico'],
            'horas_reales':teo['Horas_Reales'],'factor_masa':teo['Factor_Masa'],
            'representatividad_fisica':str(rep_db),
            'valida_regla_vigente_mayor_0_75':rep_db>D('0.75'),
            'malla_cruda':lr['Pasante_1_2P'] if lr else None,
            'malla_fecha_carga':lr['Fecha_Carga'] if lr else None,
            'peso_fuente_archivo':real['nombre_archivo'],
            'peso_fecha_carga':real['fecha_carga'],
        }
    gross={1:D(tmh[f'TMH_CV008_{shift}']),2:D(tmh[f'TMH_CV108_{shift}'])}
    hum=D('4.26'); factor=D('1.0')
    wet={n:gross[n]*factor*(1-hum/D(100)) for n in (1,2)}
    total=sum(wet.values())
    sal_shift=D(sal[f'Sal_Ajustada_T{shift}'])
    net={n:wet[n]*(1-sal_shift/total) for n in (1,2)}
    net_total=sum(net.values())
    assert abs(net_total-D(cache[shift]['Apilado_TMS_Real']))<D('0.000001')
    siir=(net[1]*D('73.436')+net[2]*D('70.742'))/net_total
    assert abs(siir-D(cache[shift]['Malla_Menos_1_2_Real']))<D('0.000001')
    with_03=(net[1]*D('73.436')+net[2]*D('73.128'))/net_total
    implied_tm2=(official*net_total-net[1]*D('73.436'))/net[2]
    results[shift]={'torres':towers,'tms_tm1_neto':str(net[1]),'tms_tm2_neto':str(net[2]),
        'tms_total_neto':str(net_total),'malla_tm1_resuelta':'73.436',
        'tm1_origen':'2026-10-04 A TM1','malla_tm2_resuelta':'70.742',
        'tm2_origen':'2026-09-28 B TM2','tm2_regla':'ARRASTRE_ULTIMO_VALIDO',
        'malla_siir_reconstruida':str(siir),
        'malla_siir_cache':cache[shift]['Malla_Menos_1_2_Real'],
        'cache_actualizado':cache[shift]['Fecha_Actualizacion'],
        'malla_oficial_informada_por_usuario':str(official),
        'delta_siir_menos_oficial':str(D(cache[shift]['Malla_Menos_1_2_Real'])-official),
        'malla_si_tm2_usara_03_b_redondeado':str(with_03),
        'tm2_implicito_si_tm1_73_436_y_pesos_siir':str(implied_tm2)}
source_03=q['near_lab']
lab_03=next(r for r in source_03 if r['Fecha']=='2026-10-03' and r['Turno']=='B' and r['Torre']=='T2')
results['03_B_TM2']={'malla_cruda':lab_03['Pasante_1_2P'],'fecha_carga':lab_03['Fecha_Carga'],
    'representatividad_fisica':q['rep_03'][0]['TM2_TurnoB_Fisico'],
    'peso_real_fisico':q['real_03'][0]['PesoReal_Fisico'],
    'peso_teorico_fisico':q['teo_03'][0]['PesoTeo_Fisico'],
    'base_elegida':q['base_03'][1]}
results['official_excel']={'available':False,'source_provenance_verified':False,
    'note':'El valor oficial A/B fue suministrado en el pedido; el Excel fuente no aparece en el checkout ni en los adjuntos accesibles.'}
(BASE/'checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{z:v[z] for z in v if z in ('malla_siir_reconstruida','malla_siir_cache','malla_oficial_informada_por_usuario','delta_siir_menos_oficial','tm2_implicito_si_tm1_73_436_y_pesos_siir','malla_si_tm2_usara_03_b_redondeado')} for k,v in results.items() if k in ('A','B')},indent=2))
