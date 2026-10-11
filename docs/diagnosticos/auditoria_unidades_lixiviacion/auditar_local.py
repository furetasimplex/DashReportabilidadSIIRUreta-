"""Inventario estatico de unidades; no importa app ni conecta a SQL Server."""
import csv
import json
from pathlib import Path
import re
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
pattern=re.compile(r'\b(?:cu_pp|cu_g_l|[a-z_]\w*_(?:cu_pp|ppm|gl|kg_d|t_d))\b',re.I)
paths=subprocess.check_output(['rg','--files','--hidden','--no-ignore','-g','!.git/**',
 '-g','!venv/**','-g','!.venv/**','-g','!**/node_modules/**','-g','!**/__pycache__/**','.'],
 cwd=ROOT,encoding='utf-8').splitlines()
rows=[]
formulas=[]
for name in paths:
 p=ROOT/name
 if OUT in p.resolve().parents or 'tablero_lixiviacion_v2_package' in p.parts:
  continue
 if p.suffix.lower() not in {'.py','.sql','.md','.txt','.csv','.json','.js','.ts','.m','.pq','.dax','.ipynb','.yml','.yaml'}:
  continue
 raw=p.read_bytes()
 try: content=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
 except UnicodeError: content=raw.decode('cp1252',errors='replace')
 rel=p.relative_to(ROOT).as_posix()
 blocks=[('',content)]
 if p.suffix.lower()=='.json':
  try:
   data=json.loads(content)
   if isinstance(data,list) and any(isinstance(x,dict) and 'definition' in x for x in data):
    blocks=[(str(x.get('esquema',''))+'.'+str(x.get('name',x.get('nombre',''))),x.get('definition') or '')
            for x in data if isinstance(x,dict)]
  except ValueError: pass
 for obj,block in blocks:
  lines=block.splitlines()
  for n,line in enumerate(lines,1):
   nearby=' '.join(lines[max(0,n-4):min(len(lines),n+3)])
   if '*' in line and re.search(r'flujo|caudal|volumen|m3',nearby,re.I) and re.search(r'cu_|ley|concentr',nearby,re.I):
    formulas.append([rel,obj,n,'no determinable con evidencia disponible',
     'Candidato textual; confirmar linaje y unidades, no prueba automatica de error',nearby[:1600]])
   for token in sorted({m.group(0) for m in pattern.finditer(line)}):
    low=token.lower()
    unit=('ppm' if low.endswith('_ppm') else 'g/L sugerido' if low.endswith('_gl') or low=='cu_g_l'
          else 'kg/d' if low.endswith('_kg_d') else 't/d' if low.endswith('_t_d') else 'No declarada por cu_pp')
    context=' '.join(lines[max(0,n-4):min(len(lines),n+3)])
    conv='; '.join(sorted(set(re.findall(r'(?:/|\*)\s*1000(?:\.0)?',context))))
    classification='no determinable con evidencia disponible'
    source='Linaje no resuelto por coincidencia nominal; revisar objeto/contexto'
    actual='No demostrada para esta ocurrencia'
    consumer='No demostrado por esta coincidencia'
    risk='Revisar contrato y consumidores antes de renombrar o convertir'
    identity=(obj+' '+p.name).lower()
    if 'vw_tablero_lixiviacion_final' in identity:
     source='vw_drena_concentrados_*_long / vw_riego_*_refino_base; flujo de vw_flujos_reales_*_long'
     consumer='No downstream ejecutable encontrado en auditoria estatica previa'
     if low in {'cu_drenaje_ppm','cu_refino_ppm','delta_cu_ppm'}:
      classification='alias engañoso'; actual='g/L (contexto validado por usuario)'
      risk='Cambio de alias rompe SELECT/bindings; no convertir valor solo por renombrar'
     elif low=='transferencia_cu_kg_d':
      classification='inconsistencia dimensional'; actual='t Cu/d: m3/d * g/L /1000'
      risk='Critico: quitar /1000 bajo mismo nombre cambia valor x1000 por observacion'
     elif low=='cu_pp':
      classification='alias engañoso'; actual='g/L para Cu drenaje/refino validado, no ppm'
    elif 'sp_razon_lixiviacion' in identity and low=='cu_drenaje_gl':
     classification='correcto'; source='v_drena_oxido_unpivot / v_drena_sulfuro_unpivot'
     actual='g/L, proyecta s.cu_pp; conversion a t Cu/d en cu_diario_ton con /1000'
     consumer='Salida SP; no consumidor de aplicacion identificado'
    elif 'sp_flujo_riego_drenaje' in identity and low in {'cu_drenaje_prom_gl','cu_drenaje_max_gl','cu_drenaje_min_gl'}:
     classification='correcto'; source='v_drena_oxido_unpivot / v_drena_sulfuro_unpivot'
     actual='g/L; AVG/MAX/MIN conservan dimension de cu_pp validado'
     consumer='Salida SP, consumidor externo no acreditado'
     risk='Alias coherente; multiplicidad puede alterar ponderacion, riesgo distinto de unidad'
    elif any(x in identity for x in ['vw_drena_concentrados_','v_drena_oxido_unpivot','v_drena_sulfuro_unpivot']) and (low=='cu_pp' or low.endswith('_cu_pp')):
     source='drena_concentrados_oxido/sulfuro'; actual='g/L para Cu drenaje validado por usuario'
     classification='no determinable con evidencia disponible'
     consumer='Tablero / vistas parcela para long; SP flujo/razon/control para unpivot'
     risk='cu_pp es ambiguo pero no demuestra ppm; renombrar requiere coordinar dependencias'
    elif 'vw_riego_' in identity and 'refino_base' in identity and (low=='cu_pp' or low=='refino_cu_pp'):
     source='riego_concentrados_oxido/sulfuro.refino_cu_pp'
     actual='g/L para Cu refino validado por usuario'; consumer='vw_tablero_lixiviacion_final'
     risk='Alias ambiguo sin conversion; no extender unidad a otros campos de riego'
    elif 'vw_drena_quimica_ingest' in identity and low=='cu_gl':
     classification='correcto'; source='drena_concentrados_oxido/sulfuro via CROSS APPLY'
     actual='g/L; CAST a FLOAT y NULLIF(valor,0), sin escala'
     risk='Renombrar rompe contrato; NULLIF existente altera cero, no se modifica'
    rows.append([rel,obj,n,token,source,unit,actual,conv,consumer,classification,risk,line.strip()[:900]])

with (OUT/'OCURRENCIAS.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f); w.writerow(['archivo','objeto_si_catalogo','linea_archivo_o_definicion','alias',
  'fuente','unidad_nombre','unidad_evidencia','conversion_cercana_no_prueba_de_linaje','consumidor',
  'clasificacion','riesgo','texto']); w.writerows(rows)
with (OUT/'FORMULAS_CANDIDATAS.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f); w.writerow(['archivo','objeto_si_catalogo','linea_archivo_o_definicion',
  'clasificacion','limite_evidencia','contexto']); w.writerows(formulas)

# Extraer evidencia de formulas seleccionadas, sin modificar fuentes.
catalog='report_export/exports/auditoria_ley_srr_202609/catalogo.json'
data=json.loads((ROOT/catalog).read_text(encoding='utf-8-sig'))
names={'vw_tablero_lixiviacion_final','sp_razon_lixiviacion','vw_drena_quimica_ingest',
 'vw_drena_concentrados_oxido_long','vw_drena_concentrados_sulfuro_long',
 'vw_riego_oxido_refino_base','vw_riego_sulfuro_refino_base',
 'sp_flujo_riego_drenaje','sp_calcular_balance_flujos_modelo6_v2',
 'vw_siir_drena_concentrado_parcela_long'}
evidence=[]
for obj in data:
 if obj['name'] not in names: continue
 lines=(obj.get('definition') or '').splitlines()
 hits=set()
 for i,line in enumerate(lines):
  if pattern.search(line) or (re.search(r'/\s*1000|\*\s*1000',line) and re.search('cu|caudal|flujo',line,re.I)):
   hits.update(range(max(0,i-2),min(len(lines),i+3)))
 evidence += ['\n## '+obj['esquema']+'.'+obj['name'], 'Fuente histórica: `'+catalog+'`; líneas de definition.','', '```sql']
 evidence += [f'{i+1}: {lines[i]}'.rstrip() for i in sorted(hits)]
 evidence += ['```','']
(OUT/'EVIDENCIA_FORMULAS.md').write_text('\n'.join(evidence)+'\n',encoding='utf-8')
files=sorted({r[0] for r in rows})
(OUT/'ARCHIVOS.md').write_text('# Archivos con coincidencias químicas\n\n'+
 '\n'.join('- `'+p+'`' for p in files)+'\n',encoding='utf-8')
print(f'{len(rows)} ocurrencias (alias por linea), {len(files)} archivos. Clasificacion conservadora: no inferir unidades desconocidas.')
