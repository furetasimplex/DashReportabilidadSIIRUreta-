"""Busqueda estatica local; no importa la app ni conecta a SQL."""
import csv
import json
from pathlib import Path
import re
import subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
targets = ['vw_tablero_lixiviacion_final', 'vw_drena_concentrados_oxido_long',
 'vw_drena_concentrados_sulfuro_long', 'vw_riego_oxido_refino_base', 'vw_riego_sulfuro_refino_base']
columns = ['id_campana_parcela_control','campana_id','pad_id','parcela_id','modulo_id',
 'numero_campana','nombre_pad','nombre_parcela','nombre_modulo','fecha','flujo_m3_h',
 'flujo_m3_d','cu_drenaje_ppm','cu_refino_ppm','delta_cu_ppm','transferencia_cu_kg_d']
contract = [r for r in json.loads((ROOT/'report_export/exports/auditoria_ley_srr_202609/columnas.json').read_text(encoding='utf-8-sig'))
 if r.get('TABLE_NAME') == targets[0]]
columns = sorted(set(columns + [r['COLUMN_NAME'].lower() for r in contract]))
(OUT/'contrato_historico.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
paths = subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','!.git/**',
 '-g','!venv/**','-g','!.venv/**','-g','!**/node_modules/**','-g','!**/__pycache__/**','.'],
 cwd=ROOT,encoding='utf-8').splitlines()
pat = re.compile(r'\b('+'|'.join(targets+columns)+r')\b',re.I)
refs, uses = [], []
for name in paths:
 p = ROOT / name
 if OUT in p.resolve().parents or p.suffix.lower() not in {
 '.sql','.py','.json','.csv','.md','.txt','.js','.ts','.html','.m','.pq','.dax','.ipynb','.yaml','.yml'}:
  continue
 raw=p.read_bytes()
 try: text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
 except UnicodeError: text=raw.decode('cp1252',errors='replace')
 for n,line in enumerate(text.splitlines(),1):
  found=sorted({m.group(0).lower() for m in pat.finditer(line)})
  for term in found:
   row=[p.relative_to(ROOT).as_posix(),n,term]
   (refs if term in targets else uses).append(row)
for name,rows in [('referencias_objetos.csv',refs),('coincidencias_columnas.csv',uses)]:
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f); w.writerow(['archivo','linea','identificador']); w.writerows(rows)

catalogs=['report_export/exports/auditoria_ley_srr_202609/catalogo.json',
 'report_export/exports/diagnostico_fase4/catalogo_dev.json']
object_refs=[]
for catalog in catalogs:
 for o in json.loads((ROOT/catalog).read_text(encoding='utf-8-sig')):
  definition=o.get('definition') or ''
  name=o.get('name',o.get('nombre'))
  for n,line in enumerate(definition.splitlines(),1):
   for target in targets:
    if re.search(r'\b'+target+r'\b',line,re.I):
     object_refs.append([catalog,o['esquema'],name,n,target,line.strip()])
  if catalog==catalogs[0] and (name in targets or any(t in definition.lower() for t in targets)):
   (OUT/(name+'.snapshot.sql')).write_text(
    '-- EVIDENCIA HISTORICA; NO DESPLEGAR. Origen: '+catalog+'\n'+
    '\n'.join(x.rstrip() for x in definition.splitlines()).strip()+'\n',encoding='utf-8')
with (OUT/'referencias_en_definiciones.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f); w.writerow(['catalogo','esquema','objeto','linea_definicion','referencia','texto']); w.writerows(object_refs)

# Buscar aristas relevantes dentro de todos los JSON de dependencias encontrados.
deprefs=[]
for name in paths:
 p=ROOT/name
 if OUT in p.resolve().parents or p.suffix.lower()!='.json' or not re.search('depend',p.name,re.I): continue
 try: data=json.loads(p.read_text(encoding='utf-8-sig'))
 except (ValueError,UnicodeError): continue
 def walk(obj):
  if isinstance(obj,dict):
   if any(isinstance(v,str) and v.lower().split('.')[-1] in targets for v in obj.values()):
    deprefs.append({'archivo':p.relative_to(ROOT).as_posix(),'registro':obj})
   for v in obj.values(): walk(v)
  elif isinstance(obj,list):
   for v in obj: walk(v)
 walk(data)
(OUT/'dependencias_encontradas.json').write_text(json.dumps(deprefs,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Archivos con referencias a los cinco objetos','',
 'Inventario literal; una referencia puede ser una definición, comentario o metadato, no necesariamente un consumidor.','']
for file in sorted({r[0] for r in refs}):
 rows=[r for r in refs if r[0]==file]
 lines.append('- `'+file+'`: '+ '; '.join(t+': líneas '+','.join(str(r[1]) for r in rows if r[2]==t) for t in targets if any(r[2]==t for r in rows)))
(OUT/'ARCHIVOS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(f'Objetos: {len(refs)} coincidencias / {len(set(r[0] for r in refs))} archivos; columnas: {len(uses)}; metadatos dependencias: {len(deprefs)}.')
print('Definiciones:',sorted({r[2] for r in object_refs}))
