"""Read-only workbook locator for 04-10-2026 Malla -1/2."""
import json
from datetime import date,datetime
from pathlib import Path
from openpyxl import load_workbook
BASE=Path(__file__).resolve().parent
paths=[Path(r'C:\Users\nimun\Downloads\Actual Reporte Leyes y Finos_Octubre_2026 con SRR.xlsx'),
       Path(r'C:\Users\nimun\Downloads\Actual Reporte Leyes y Finos_Octubre_2026 con SRR(1).xlsx')]
out=[]
for p in paths:
    wb=load_workbook(p,read_only=True,data_only=True)
    item={'path':str(p),'size':p.stat().st_size,'mtime':datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
          'sheets':[(s.title,s.max_row,s.max_column) for s in wb.worksheets], 'matches':[],'report_turno_rows':[]}
    for s in wb.worksheets:
        for rownum,row in enumerate(s.iter_rows(),1):
            if s.title=='Reporte por Turno' and rownum<=8:
                item['report_turno_rows'].append({'row':rownum,'cells':{c.coordinate:str(c.value) for c in row if c.value is not None}})
            if s.title=='Reporte por Turno' and any(
                (isinstance(c.value,datetime) and c.value.date()==date(2026,10,4)) or
                (isinstance(c.value,date) and c.value==date(2026,10,4)) or
                (isinstance(c.value,str) and c.value.strip() in ('04-10-2026','04/10/2026','2026-10-04'))
                for c in row):
                item['report_turno_rows'].append({'row':rownum,'cells':{c.coordinate:str(c.value) for c in row if c.value is not None}})
            for c in row:
                v=c.value
                if isinstance(v,(float,int)) and not isinstance(v,bool):
                    if any(abs(v-t)<0.0003 for t in (73.3121,73.3035,73.3074,0.733121,0.733035,0.733074,72.3510,72.2757)):
                        item['matches'].append({'sheet':s.title,'cell':c.coordinate,'value':v})
    out.append(item)
(BASE/'official_excel_probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
for a in out:
    print(a['path'],'matches',len(a['matches']),'report rows',len(a['report_turno_rows']))
    print(a['matches'][:30])
    for r in a['report_turno_rows']:
        if r['row']<=8 or any('2026-10-04' in x for x in r['cells'].values()):
            print('row',r['row'],r['cells'])
