from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
import json,hashlib
ROOT=Path(__file__).parent
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def read(path,selected=None):
    with ZipFile(path) as z:
        wb=ET.fromstring(z.read('xl/workbook.xml'))
        rm={r.attrib['Id']:r.attrib['Target'] for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(t.text or '' for t in n.findall('.//s:t',NS)) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
        out={}
        for sh in wb.find('s:sheets',NS):
            name=sh.attrib['name']
            if selected and name not in selected: continue
            rid=sh.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']
            target=rm[rid]; loc=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            cells={}
            for c in ET.fromstring(z.read(loc)).findall('.//s:sheetData/s:row/s:c',NS):
                v=c.find('s:v',NS); f=c.find('s:f',NS)
                value=v.text if v is not None else None
                if c.attrib.get('t')=='s' and value is not None: value=strings[int(value)]
                if c.attrib.get('t')=='inlineStr': value=''.join(t.text or '' for t in c.findall('.//s:t',NS))
                cells[c.attrib['r']]={'v':value,'f':f.text if f is not None else None,'type':c.attrib.get('t'),'formula_attrs':f.attrib if f is not None else None}
            out[name]=cells
        return out
if __name__=='__main__':
    files=list(Path('C:/Users/nimun/Downloads').glob('BD_CIO*Septiembre*.xlsx'))
    files+=list(Path('C:/Users/nimun/OneDrive/Escritorio/Simplex').rglob('BD_CIO*Septiembre*.xlsx'))
    for i,p in enumerate(files):
        d=read(p,{'Base_Datos'})
        (ROOT/f'mina_archivo_{i}.json').write_text(json.dumps({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'sheets':d},ensure_ascii=False),encoding='utf-8')
        print(i,p)
        for name,cells in d.items():
            print(name,len(cells))
            print([(r,c['v']) for r,c in cells.items() if int(''.join(filter(str.isdigit,r)))<=2][:160])
