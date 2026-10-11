# Fuentes, variables y semántica

## Contratos

OP = `inventar_SpcHidr.fn_estado_operacional_parcela_diario(@fecha)`, 24 campos consumidos en `map_db.FIELDS`, 60 parcelas del catálogo. Estado derivado SQL, no observación directa de un sensor. Prioridad: PAD + parcela + fecha. `campana_id` es identificador, `numero_campana` es etiqueta; no intercambiarlos.

V2 = `inventar_SpcHidr.vw_tablero_lixiviacion_final_v2`, grano físico PAD + parcela + fecha, campaña hidráulica nullable. La campaña operacional puede ser distinta; unir fuentes por clave física tras verificar unicidad, conservar ambos IDs con nombres explícitos. No unir por número de campaña ni módulo. No descartar filas sin campaña hidráulica.

Módulos = `fn_estado_operacional_modulo_diario(fecha,pad_id,parcela_id)`: solo drill-down para explicar composición MIXTO. No hacer de módulos el hecho físico ni replicar medidas V2.

| Variables OP | Clase | Uso y límite |
|---|---|---|
| fecha,pad_id,nombre_pad,parcela_id,numero_parcela | Contexto | Clave e identidad; números locales vs IDs globales. |
| campana_id,numero_campana | Contexto operacional | Reinicio de rachas OP por ID; no confundir campaña hidráulica. |
| estado_operacional | Operacional | Clasificación oficial, incluida SIN_INFORMACION por ausencia de consolidación. |
| modulos_total,estados_distintos,composicion_modulos | Contexto | Explican MIXTO; no son cantidades físicas a multiplicar. |
| tiene_dato_riego,riego_activo | Hidráulica | Existencia de registro vs actividad evaluable son distintos. Actividad SQL: caudal > 1; todos NULL → flag NULL. Inactivo no implica caudal exactamente cero. |
| tiene_dato_drenaje,drenaje_activo | Hidráulica/proxy químico | Actividad SQL: cu_pp > 0; no mide caudal de drenaje. Todos NULL → flag NULL. |
| fecha_ini_carguio,fecha_conformado | Operacional | Hitos agregados de módulos de campaña; no calendario planificado. |
| fecha_primer_riego,fecha_ultima_actividad_riego | Hidráulica | Extremos de campaña completa, pueden ser futuros respecto de fecha seleccionada. |
| fecha_ini_drenaje,fecha_ultima_actividad_drenaje | Hidráulica/proxy | Extremos de señal Cu positiva; no comienzo/fin de drenaje físico certificado. |
| fecha_ini_reclamo,fecha_fin_reclamo | Operacional | Hitos de módulos; contexto, no plazo esperado de negocio. |
| calidad_estado | Calidad clasificación | EVALUABLE/PARCIAL/NO_EVALUABLE/SIN_INFORMACION. No certifica exactitud de químicos V2. |

| Variables V2 | Clase | Uso |
|---|---|---|
| fecha,pad_id,parcela_id,nro_parcela_pad | Contexto | Clave física. |
| campana_id,numero_campana,estado_asignacion y fechas de ventana | Hidráulica/contexto | Campaña hidráulica nullable, FUERA_VENTANA_RIEGO no equivale a inactividad. |
| flujo_m3_d | Hidráulica | m³/d; cero y NULL distintos. |
| cu_drenaje_gl,cu_refino_gl,delta_cu_gl | Química | g/L; delta consumido, no reconstruido por otro CASE. |
| transferencia_cu_t_d | Química/masa diaria | t Cu/d ya calculadas por V2. No duplicar fórmula en futuro motor. |

## Estados: todos son etiquetas observables en salida, no decisiones

El CASE de módulos tiene precedencia reclamo/carguío antes de fases hidráulicas; luego consolida parcela. Ningún estado solo autoriza acción ni prioridad. Todos pueden ser normales o tener explicación de calidad/contexto. Se transcribe semántica; no se crea otro CASE.

| Estado | Significado en fuente | ¿Atención automática? / contexto necesario |
|---|---|---|
| APILADO | Dentro del carguío antes del fin o fin NULL. | No; plan/cierre esperado ausente. |
| CONFORMADO_PRE_RIEGO | Carguío finalizado, primer riego ausente o posterior. | No; espera normal, plazo aprobado pendiente. |
| RIEGO | Flags riego 1 / drenaje 0 tras precedencias. | No; latencia de señal drenaje puede ser normal. |
| RIEGO_DRENAJE | Ambos flags 1. | No; operación clasificada, no desempeño óptimo demostrado. |
| DRENAJE_RESIDUAL | Riego 0/drenaje 1 después del último riego de campaña. | No; etapa normal, definición retrospectiva. |
| DRENAJE_CON_RIEGO_PAUSADO | Riego 0/drenaje 1 sin satisfacer residual. | No; intermitencia posible. |
| PAUSA_HIDRAULICA | Ambos flags 0 sin satisfacer reposo posterior. | No; estrategia de pausas/duración. |
| REPOSO_PRE_RECLAMO | Ambos 0 después de extremos activos y antes de reclamo/fecha ausente. | No; programación y duración. |
| RECLAMO | Desde inicio retiro hasta fin inclusivo o fin NULL. | No; plan y recursos. |
| RECLAMADO | Fecha posterior al fin retiro. | No; cierre normal. |
| MIXTO | Más de un estado de módulo en parcela. | No; coexistencia normal, composición y detalle a demanda. |
| SIN_COBERTURA_HIDRAULICA | Tras primer riego con alguna cobertura/actividad no evaluable. | Señal de datos; no concluir actividad cero. |
| SIN_CLASIFICAR | ELSE residual del CASE de módulo. | Revisar contexto/calidad; no inferir una fase. |
| SIN_INFORMACION | COALESCE sin consolidación de módulos. | Falta de información; no recomendación operativa. |

Calidad: `EVALUABLE` es ELSE (no garantía universal); `NO_EVALUABLE` si estado SIN_COBERTURA_HIDRAULICA; `PARCIAL` si MIXTO contiene ese componente; `SIN_INFORMACION` sin consolidación. Propuesta coherente: EVALUABLE permite describir hechos; PARCIAL advertencia y trazabilidad; NO_EVALUABLE/SIN_INFORMACION bloquean prescripción operativa. Aun EVALUABLE puede coexistir con flags NULL si una fase anterior resuelve el CASE: validar variables específicas, no solo calidad global.

## Hechos exactos

Predicados en matriz: estados/qualidad por igualdad literal; riego/drenaje activo `=1`; inactivo evaluable `tiene_dato=1 AND activo=0`; sin registro `tiene_dato IS NULL` (en contrato actual 1/NULL); actividad no evaluable `activo IS NULL`, incluso con registro existente; V2 delta/transferencia negativos requieren no NULL; flujo cero `=0`; fuera con flujo `>0 AND estado_asignacion='FUERA_VENTANA_RIEGO'`. Son observables como valores de fuente, no conclusiones físicas 100% independientes de calidad. Drenaje activo significa señal Cu positiva, no caudal positivo demostrado.

## Duraciones soportadas y límites

| Duración | Soporte/reconstrucción | Campaña y datos tardíos | Set-based posible |
|---|---|---|---|
| Rachas pausa/residual/pausado/MIXTO/reposo/reclamo | Calendario diario de estado oficial o ruta equivalente; no sale del snapshot de un día. | Reiniciar por campaña OP, hueco o interrupción; tardíos reclasifican historia. | Sí, gaps-and-islands sobre salida validada. |
| Calidad parcial/no evaluable; sin dato | Flags/calidad diarios, misma reconstrucción. | Reinicio OP elegido conservadoramente; no pegar huecos como ceros. | Sí. |
| Delta/transferencia negativa | V2 diaria; NULL corta observación, no cero. | Rachas físicas pueden cruzar campaña; aquí se separan por campaña hidráulica (NULL no se mezcla con ID). No unir con campaña OP. | Sí. |
| Desde conformado/inicio reclamo | DATEDIFF desde hito no NULL y <= fecha; describir hito agregado. | Reiniciar por campaña OP; puede cambiar por datos tardíos. | Sí. |
| Desde primer riego/inicio drenaje | Hito de campaña completa: computable solo si <= fecha. | Futuro → no transcurrido, no duración negativa. | Sí, con semántica explícita. |
| Desde último riego/drenaje hasta fecha | Último extremo expuesto puede estar en el FUTURO. No sirve directamente para «último hasta hoy». | Requiere máximo de fecha activa <= fecha y campaña OP, sobre diario; rango truncado produce duración mínima/censurada. | Sí; no implementado en runtime. |

Una condición del día no es una condición prolongada. Percentiles de rachas son descriptivos, no umbrales. Ventana «últimos N» y media móvil requieren N aprobado; desde campaña requiere historia previa suficiente. Fechas límites del rango y datos tardíos producen censura y sesgo retrospectivo.
