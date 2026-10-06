"""Genera documentacion del contrato historico; no accede a SQL Server."""
import json
from pathlib import Path
out=Path(__file__).resolve().parent
root=out.parents[2]
rows=json.loads((root/'report_export/exports/auditoria_ley_srr_202609/columnas.json').read_text(encoding='utf-8-sig'))
rows=sorted((r for r in rows if r.get('TABLE_NAME')=='vw_tablero_lixiviacion_final'),key=lambda r:r['ORDINAL_POSITION'])
lines=['# Matriz del contrato legacy frente a V2 candidato','',
 'Las 51 columnas legacy proceden del catálogo histórico. TEST V4 funcional VALIDADO LIVE según VALIDACION_LIVE_V4.md. Esta matriz conserva el candidato local de 25 columnas: pendiente conciliar con sys.columns LIVE33, no recibido. No acredita el detalle de tipos LIVE ni inventa las ocho columnas restantes.','',
 '| Columna legacy | Columna V2 | Unidad legacy | Unidad V2 | Mismo significado sí/no | Compatibilidad | Observaciones |',
 '|---|---|---|---|---|---|---|']
for r in rows:
 c=r['COLUMN_NAME']; v='—'; ul='No demostrada / contexto CPC'; uv='—'; same='No (no expuesta)'; comp='Ruptura de esquema si cliente migra sin adaptación'; note='Contexto separado; no inventar agregación.'
 if c in {'pad_id','parcela_id','fecha'}:
  v=c; ul=uv='Fecha' if c=='fecha' else 'Identificador'; same='Sí (identidad física)'; comp='Nombre preservado'; note='Validar IDs reales, tipo y cobertura; ahora una sola fila física.'
 elif c in {'campana_id','numero_campana'}:
  v=c; ul=uv='Identificador / número de campaña'; same='No (criterio de asociación cambia)'; comp='Nombre preservado, semántica distinta'; note='VALIDADO LIVE: asociación por ventana hidráulica; ambos NULL fuera. JOIN de V2 pendiente de prueba; no oculta conflictos.'
 elif c in {'flujo_m3_h','flujo_m3_d'}:
  v=c; ul=uv='m³/h' if c.endswith('_h') else 'm³/d'; same='Sí (medida por observación)'; comp='Nombre/unidad preservados, cardinalidad distinta'; note='Conservación exacta contra fuente física; no igualdad de sumas legacy duplicadas.'
 elif c in {'cu_drenaje_ppm','cu_refino_ppm','delta_cu_ppm'}:
  v=c.replace('_ppm','_gl'); ul='Nombre ppm; valor g/L validado'; uv='g/L'; same='Sí (magnitud), fecha puede cambiar'; comp='Renombrado explícito'; note='No multiplicar por 1000 al cambiar alias; nueva fecha operacional modifica emparejamientos.'
 elif c=='transferencia_cu_kg_d':
  v='transferencia_cu_kg_d / transferencia_cu_t_d'; ul='Nombre kg/d; fórmula entrega t Cu/d'; uv='kg Cu/d / t Cu/d'; same='No para kg; sí dimensionalmente para t'; comp='Crítica bajo mismo nombre'; note='V2 kg=flujo×delta_gl; t=kg/1000. No mezclar contratos ni asumir totales ×1000 con distinto grano.'
 elif c in {'modulo_id','id_campana_parcela_control','nombre_modulo'}:
  ul='Identificador / descriptor de módulo'; note='No existe identidad singular al grano físico. No MIN/MAX/TOP 1 representativo.'
 elif c in {'nombre_pad','nombre_parcela'}:
  ul='Descriptor'; note='No imprescindible en contrato mínimo; incorporar solo con dimensión live única, sin multiplicar filas.'
 elif c.startswith('fecha_'):
  ul='Fecha de contexto CPC'; note='No se expone. MIN primer riego/MAX último riego sí fueron validados exclusivamente para resolver ventana hidráulica, no estas fechas.'
 elif c in {'dia_relativo_campana','fase_operacional','secuencia_carguio','secuencia_retiro'}:
  ul='Días / categoría / secuencia según columna'; note='Requiere nuevo contrato contextual; no conservar el CASE legacy por inercia.'
 elif c in {'tmh_cargado','tms_cargado'}:
  ul='TMH' if c=='tmh_cargado' else 'TMS'; note='Material CPC separado; no replicarlo por día ni sumarlo como producción diaria.'
 elif c=='altura_modulo_max':
  ul='Longitud, unidad no acreditada en snapshot'; note='No asumir metros ni tomar MAX entre módulos sin regla aprobada.'
 elif c in {'h_drenaje','ph_drenaje','cl_drenaje','fet_drenaje','fe2_drenaje','eh_drenaje',
            'h_refino','ph_refino','cl_refino','fet_refino','fe2_refino','eh_refino'}:
  v=c; ul=uv='Propia del analito; no inferir g/L'; same='Sí, señal química; fecha cambia'; comp='Alias conservado'; note='VALIDADO LIVE: siete analitos preservados. Proyección final y metadatos pendientes; sin nuevos casts.'
 elif c=='delta_h':
  ul='No acreditada'; note='No se incorpora nueva fórmula de acidez: evidencia explícita confirma delta Cu, no contrato delta_h.'
 lines.append('| '+' | '.join([c,v,ul,uv,same,comp,note])+' |')
for c,u,n in [('estado_asignacion','Categoría','FUERA_VENTANA_RIEGO aprobado; CAMPANA_HIDRAULICA del diseño candidato aportado. Proyección final pendiente. Sin contador público ni estado de conflicto inventados.')]:
 lines.append('| — | '+c+' | — | '+u+' | No (nueva) | Columna nueva | '+n+' |')
lines += ['', 'No hay garantía de compatibilidad por ordinal, cantidad de filas o nullability. Confirmar tipos y precisión con 04. La matriz no autoriza eliminar campos de la vista oficial.','']
(out/'MATRIZ_CONTRATO.md').write_text('\n'.join(lines),encoding='utf-8')
print(f'Matriz: {len(rows)} columnas legacy; estado_asignacion del diseño aportado.')
