"""Read-only formula/value lineage from the located official workbook."""
import json
from pathlib import Path
from openpyxl import load_workbook
BASE=Path(__file__).resolve().parent
p=Path(r'C:\Users\nimun\Downloads\Actual Reporte Leyes y Finos_Octubre_2026 con SRR(1).xlsx')
wf=load_workbook(p,read_only=True,data_only=False)
wv=load_workbook(p,read_only=True,data_only=True)
spec={
 'Reporte por Turno':['C29','H29','I29','AD29','AN29','AO29','C30','H30','I30','AD30','AN30','AO30'],
 'Generador Reporte':['V4','X12','Y12','Z12','AF25'],
 'Data TM1':[f'{c}{r}' for r in (7,8,9,10,11,12) for c in ('B','I','J','K','AF','AG','AH','AI','AJ','AK')],
 'Data TM2':[f'{c}{r}' for r in (7,8,9,10,11,12) for c in ('B','I','J','K','AF','AG','AH','AI','AJ','AK')],
 'Validacion de leyes TM1':[f'{c}{r}' for r in (1,2,3,4,5,6,7) for c in ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W')],
 'Validacion de leyes TM2':[f'{c}{r}' for r in (1,2,3,4,5,6,7) for c in ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W')],
}
out={'path':str(p),'size':p.stat().st_size,'sheets':{}}
for name,addrs in spec.items():
    sf=wf[name]; sv=wv[name]
    out['sheets'][name]={a:{'formula':sf[a].value,'cached':str(sv[a].value) if sv[a].value is not None else None} for a in addrs}
out['raw_malla_hits']=[]
for name,target in [('Informe TORRE N°1',73.43608340888485),('Informe TORRE N°2',73.12831597563371)]:
    actual=next((s for s in wv.worksheets if s.title.startswith(name[:13]) and ('1' if '1' in name else '2') in s.title),None)
    if actual is None: continue
    sf=wf[actual.title]
    for row in actual.iter_rows():
        for cell in row:
            if isinstance(cell.value,(float,int)) and abs(cell.value-target)<0.000001:
                out['raw_malla_hits'].append({'sheet':actual.title,'cell':cell.coordinate,
                    'cached':cell.value,'formula':sf[cell.coordinate].value,
                    'row_key':actual.cell(cell.row,1).value})
(BASE/'official_excel_trace.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for name,cells in out['sheets'].items():
    if name.startswith('Validacion'): continue
    print('\n',name)
    for a,v in cells.items():
        if v['cached'] is not None or v['formula'] is not None: print(a,str(v['cached'])[:32],str(v['formula'])[:120])
