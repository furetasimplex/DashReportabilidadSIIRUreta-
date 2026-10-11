# Resultado de auditoría DEV: delta THM, PAD2 campaña 10

**Corte de evidencia:** 2026-10-07 00:18, hora del servidor SQL DEV `inventar_SpcHidr`. Consulta de solo lectura. Se observaron 26 módulos congelados; 18 tienen filas THM (474 filas fuente). Reclamo y su vista acumulada tienen 474 filas con las mismas claves. Las claves `(modulo_id, fecha)` son únicas en los tres conjuntos observados.

## Brecha final y sus componentes

| Componente | Módulos con hallazgo | Aporte neto a brecha (m³) |
|---|---:|---:|
| Arranque con acumulado | 10 | +6.990,283 |
| Delta interno inconsistente | 14 | +5.568,933 |
| Diario fuente menos `m3_thm` Reclamo | 4 | −60,675 |
| `m3_thm` Reclamo menos m³ oficial de la vista | 0 | 0,000 |
| **Brecha final fuente menos sistema** | | **+12.498,541** |

Los recuentos de módulos se solapan: por ejemplo M17 tiene arrastre y falta de sincronización; M23 tiene delta inconsistente y falta de sincronización. Los aportes netos se suman exactamente. No se atribuye el arrastre al primer día de movimiento.

## Casos ilustrativos

- **M17 / id 81:** primera fila 29-09, acumulado 1.423,533 frente a diario 135,623: arrastre +1.287,910. El 30-09 la fuente registra −5,377, Reclamo 0. Brecha final al 04-10: **+1.282,533**.
- **M23 / id 87:** arrastre inicial cero. El 22-09 el incremento acumulado es 5.233,797 frente a diario 2.643,358 (diferencia +2.590,439). Otras diferencias internas llevan el aporte neto a +2.590,420. El 30-09 la fuente registra −40,763 y Reclamo 0. Brecha final al 04-10: **+2.549,657**.
- **M8 / id 72:** no tiene arrastre; el neto de diferencias internas es **+3.513,641667**. Es la mayor contribución de delta interno por módulo.
- **M18 / id 82:** arrastre +1.091,170 e inconsistencia interna −1.091,136 se compensan casi por completo; brecha final +0,034. Por eso no se debe inferir ausencia de errores a partir de una brecha final pequeña.

## Comparación del 30-09

Hay once filas THM de ese día. Cuatro tienen un negativo correcto en la fuente y cero en `reclamo.camiones_reclamo.m3_thm` y en la vista acumulada:

| Módulo | Fuente m³ | Reclamo m³ | Diferencia fuente − Reclamo m³ |
|---|---:|---:|---:|
| M17 | −5,377 | 0 | −5,377 |
| M23 | −40,763 | 0 | −40,763 |
| M25 | −9,967 | 0 | −9,967 |
| M26 | −4,568 | 0 | −4,568 |
| **Total** | **−60,675** | **0** | **−60,675** |

En estos cuatro registros, `delta_acumulado` coincide con `volumen_diario_m3`. Las otras siete filas del 30-09 no presentan diferencia fuente−Reclamo superior a 0,001. La definición del SP de sincronización filtra la fuente por `@FechaInicio` y `@FechaFin` y carga `SUM(volumen_diario_m3)`.

La bitácora confirma que las últimas cuatro ejecuciones (`3631`, `3633`, `3636`, `3638`) comenzaron **01-10** y, por tanto, no podían actualizar el 30-09. También hubo ejecuciones anteriores `3623` y `3625` con rango **01-09 a 04-10** a las 16:42 del 06-10; ambas terminaron `OK`, sin filas afectadas registradas. `reclamo.log_sincronizacion` muestra que, durante las inserciones previas del 30-09, M23/M25/M26 tenían valor fuente **0** (ejecución `3576`) y M17 también tenía **0** al insertarse (ejecución `3603`). Actualmente la fuente registra los cuatro negativos. La secuencia es consistente con una actualización de la fuente posterior a las sincronizaciones amplias, seguida de reprocesos limitados desde el 01-10. Como la tabla fuente no contiene marca de carga, el instante exacto de ese cambio no se puede demostrar con esta evidencia.

## Regla observada y recomendación

El SP `reclamo.sp_sincronizar_desde_etl` sincroniza la suma de `volumen_diario_m3` por fecha/módulo. Por ello una discrepancia entre el diario y el incremento de `volumen_final_reclamado` puede pasar intacta a Reclamo. La vista acumulada observada coincide con `m3_thm` para las 474 filas; la divergencia se origina antes de ella.

1. Corregir y documentar el cálculo del delta en el **ETL que alimenta la tabla THM**, usando `volumen_final_reclamado_actual − volumen_final_reclamado_anterior` cuando existe una fila anterior validada. Conservar el diario original y el delta normalizado con su procedencia para auditar correcciones. Una vista de preparación de Reclamo también sería viable si se requiere no cambiar el ETL; evitar una sustitución silenciosa dentro del SP.
2. Recuperar primero las fechas y deltas posteriores al corte 2026-07-01 que faltan antes de la primera fila disponible, desde los archivos Volumen Pilas. Si no están disponibles, registrar un **arrastre inicial posterior al corte** con fecha/rango y evidencia explícitos, separado del diario de la primera fila. `m3_camiones_previo` permanece en cero: representa solo movimiento anterior al corte.
3. Investigar el rango real de la última sincronización y, tras acordar la corrección de fuente y continuidad, planificar un reproceso controlado que incluya el 30-09. No se ejecutó aquí.

**Estado:** auditoría terminada; sin DML, DDL, SP, reproceso ni publicación.
