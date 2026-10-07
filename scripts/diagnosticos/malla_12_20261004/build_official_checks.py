"""Verify cached official Excel formula arithmetic without recalculating the workbook."""
import json
from decimal import Decimal, getcontext
from pathlib import Path
getcontext().prec=28
BASE=Path(__file__).resolve().parent
snap=json.loads((BASE/'snapshot.json').read_text(encoding='utf-8'))
checks=json.loads((BASE/'checks.json').read_text(encoding='utf-8'))
trace=json.loads((BASE/'official_excel_trace.json').read_text(encoding='utf-8'))
snap['official_excel_trace']=trace
(BASE/'snapshot.json').write_text(json.dumps(snap,ensure_ascii=False,indent=2),encoding='utf-8')
cell=trace['sheets']; D=lambda x:Decimal(str(x))
official={}
for shift,weight_col,malla_col,report_row in [('A','I','AG',29),('B','J','AH',30)]:
    t1w=D(cell['Data TM1'][weight_col+'11']['cached'])
    t2w=D(cell['Data TM2'][weight_col+'11']['cached'])
    t1=D(cell['Data TM1'][malla_col+'11']['cached'])
    t2=D(cell['Data TM2'][malla_col+'11']['cached'])
    value=(t1w*t1+t2w*t2)/(t1w+t2w)
    excel=D(cell['Reporte por Turno']['AD'+str(report_row)]['cached'])
    assert abs(value-excel)<D('0.00000000001')
    official[shift]={'tm1_tms':str(t1w),'tm2_tms':str(t2w),
        'tm1_malla':str(t1),'tm2_malla':str(t2),
        'reconstruido':str(value),'excel_cache':str(excel),
        'delta_siir_menos_oficial_exacto':str(D(checks[shift]['malla_siir_cache'])-excel)}
checks['official_excel']={'available':True,'path':trace['path'],
    'reporte_por_turno_celdas':['AD29','AD30'],
    'generador_celdas':['X12','Y12','Z12','AF25'],
    'tm1_malla_origen':'Informe TORRE N°1!AL10; 04-10-2026 A',
    'tm2_malla_origen':'Informe TORRE N°2!AL9; 03-10-2026 B',
    'tm1_validacion':'Validacion de leyes TM1!T7=Informe TORRE N°1!AL10; U7=T7',
    'tm2_validacion':'Validacion de leyes TM2!U6 por C6=1; T7=U6; U7=U6',
    'tm2_rep_03_b_excel':'1','tm2_rep_03_b_siir':str(checks['03_B_TM2']['representatividad_fisica']),
    'tm2_rep_04_a_excel':'1','tm2_rep_04_b_excel':'0.76',
    'tm1_rep_04_a_excel':'0.76','tm1_rep_04_b_excel':'0.76',
    'weighted':official}
siir_a=D(checks['A']['malla_siir_cache']); siir_b=D(checks['B']['malla_siir_cache'])
tms_a=D(checks['A']['tms_total_neto']); tms_b=D(checks['B']['tms_total_neto'])
daily_siir=(tms_a*siir_a+tms_b*siir_b)/(tms_a+tms_b)
daily_official=D(cell['Generador Reporte']['Z12']['cached'])
checks['daily']={'siir_reconstructed':str(daily_siir),'official_excel_Z12':str(daily_official),
                 'delta_siir_menos_oficial':str(daily_siir-daily_official)}
(BASE/'checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(official,ensure_ascii=False,indent=2))
