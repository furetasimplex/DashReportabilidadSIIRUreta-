# Malla -1/2, 04-10-2026 A/B: auditoría DEV de solo lectura

**Resultado principal — A. DIFERENCIA DE REPRESENTATIVIDAD.** La emisión SIIR y el Excel Oficial usan el mismo tipo de dato (pasante de Malla -1/2 de torre), pero discrepan sobre qué muestra histórica de TM2 queda habilitada para el arrastre. SIIR calcula para TM2 del 03-10 B representatividad física **0,6879107545** y la rechaza con la regla `> 0,75`. El Excel Oficial guarda **1** en `Validacion de leyes TM2!C6`, acepta esa muestra y arrastra su **73,1283159756 %** a ambos turnos del 04-10. SIIR arrastra el último evento válido anterior de TM2: **70,742 %**, del 28-09 B.

Además, el Excel deja `T7=U6` y `U7=U6` para TM2 el 04-10 incluso cuando su propia celda de representatividad de 04-10 A guarda `1`. Es una fórmula explícita de arrastre del Oficial; no se debe interpretar su marca de validez del 04-10 A como selección de la muestra cruda de ese turno. Las cifras del Excel se reproducen con sus propias fórmulas y tonelajes.

## Alcance, fuentes y ruta ejecutada

- **Excel Oficial leído:** `C:\Users\nimun\Downloads\Actual Reporte Leyes y Finos_Octubre_2026 con SRR(1).xlsx`, modificado 07-10-2026 09:18. Sus celdas `Reporte por Turno!AD29:AD30` son 73,3121308679 y 73,3035313961. `Generador Reporte!X12:Y12` las copia y `Z12` muestra el diario 73,3074451730. La variante sin `(1)` no contiene esas cifras.
- **Ruta SIIR OFICIAL según el código vigente:** `report_export/callbacks/reportabilidad_cb.py::exportar_excel` (`tipo="reporte_turno"`) → `preparar_paquete_reporte_turno_emision` → `sp_actualizar_reporte_turno_cache_emision_test` → `sp_reporte_turno_emision_test` → `v_leyes_resueltas_data_tm_reporte_test` → `v_leyes_validadas_tm_turno` → `v_validacion_leyes_tm1_v2` / `v_validacion_leyes_tm2_v2` → `v_representatividad_diaria_calculada`, `Informe_TM_lab`, vistas de pesos real/teórico. El callback exporta el cache `reporte_turno_cache_emision_test`; aquí **solo se leyó** su estado, sin ejecutar la preparación ni los SP.
- **Objetos OFICIAL:** todos los de la ruta anterior; el sufijo `_test` forma parte de la ruta actualmente llamada. `v_datos_apilado_tmh_v2`, `v_sal_ajustada`, `v_ajuste_camiones_emision_test` y `v_reporte_diario_humedad_test` alimentan o corroboran la ponderación del SP.
- **LEGACY / no consumidos por esta emisión:** `reporte_turno_cache`, `v_reporte_turno_reales_test`, `v_leyes_resueltas_data_tm_reporte_test_v2`, `Historico_Reporte_Turno`. **TEST / DESCONOCIDO:** ninguna de esas rutas se usó como evidencia del valor emitido. La clasificación se basa en llamadas y referencias efectivas, no solo en nombres.

Las consultas DEV se observaron el 07-10-2026 a las 10:22 (hora SQL). El cache A/B tiene `Fecha_Actualizacion=2026-10-07 09:43:45.561020`, posterior a la carga de laboratorio del 06-10. La fórmula vigente y las fuentes reconstruyen el cache a menos de 0,000001 pp: **no hay evidencia de desfase de cache**.

## Representatividad física SIIR

La definición actual de ambas vistas de validación aplica **`> 0.75`**, no `>= 0.75`; los cuatro casos están alejados de la igualdad exacta. `Representatividad_TM` expuesta por la vista de leyes validadas es química; para Malla se utiliza la columna **física**.

| Turno | TM | Peso real físico kg | Peso teórico físico kg | Horas reales | Factor masa | Rep. física | Válida `>0,75` |
|---|---|---:|---:|---:|---:|---:|---|
| A | TM1 | 30,180 | 40,216599 | 9,572222 | 1,000000 | 0,750436 | Sí |
| A | TM2 | 19,460 | 30,749663 | 8,758333 | 0,835654 | 0,632852 | No |
| B | TM1 | 0 | 64,548591 | 13,000000 | 1,000000 | 0 | No |
| B | TM2 | 22,500 | 58,863019 | 12,783333 | 0,927374 | 0,382243 | No |

Los pesos reales vienen de `v_peso_real_torre_turno_excel`, archivo `10_Peso Torre Octubre 2026 (1).xlsx`, cargado 06-10-2026 11:43:35. Horas, factor y pesos teóricos vienen de `v_peso_teorico_turno_torre_excel`. Comprobación adicional del evento disputado: **03-10 B TM2**, real 17,100 kg, teórico 24,857876 kg, rep. física **0,6879107545**, inválida para SIIR.

## Datos crudos y selección

| Fecha/turno | Torre | Malla cruda SIIR (`Informe_TM_lab.Pasante_1_2P`) | Carga en DEV | Uso en SIIR |
|---|---|---:|---|---|
| 04-10 A | TM1 | 73,436 % | 06-10 18:40:04 | Válida; se usa en A y B |
| 04-10 A | TM2 | 73,659 % | 06-10 18:39:54 | Inválida; no crea evento |
| 04-10 B | TM1 | NULL | 06-10 18:40:04 | Sin muestra |
| 04-10 B | TM2 | 72,858 % | 06-10 18:39:54 | Inválida; no crea evento |
| 03-10 B | TM2 | 73,128 % | 06-10 18:39:54 | Inválida (rep. 0,687911) |
| 28-09 B | TM2 | 70,742 % | 05-10 13:35:55 | Último evento válido; se arrastra |

Para Malla -1/2, `v_validacion_leyes_tm1_v2` y `v_validacion_leyes_tm2_v2` fijan el campo Mina/MB en `NULL`; no hay rama de fallback MB ni IMP elegible en la cadena oficial. `Muestra_Fisica=MIXTA` y `Fuente_Info_Fisica=T1; MB` del cache describen el conjunto de información física, **no** la procedencia específica de Malla. No se encontró una semilla de Malla para el 04-10.

El SP actual forma candidatos solo si el valor es no nulo/no cero y su fuente es `TORRE_MISMO_TURNO` o `SEMILLA_INICIO_PERIODO`. Selecciona el evento cronológico más reciente sin mirar al futuro. Permite la propia TM y, si el objetivo es TM1, también TM2; **no permite TM1 → TM2**. Permite A → B dentro de la misma TM. Si el candidato procede de fecha anterior, etiqueta `ARRASTRE_ULTIMO_VALIDO`. Así, en A TM1 usa 04-10 A y TM2 usa 28-09 B; en B TM1 usa 04-10 A y TM2 conserva 28-09 B. No existe promedio simple ni fallback MB/IMP: el valor final es media ponderada por TMS de TM1 y TM2.

## Excel Oficial: fuente y fórmula comprobadas

| Objeto/celda | 04-10 A/B en el Excel |
|---|---|
| `Informe TORRE N°1!AL10` | 04-10 A, **73,4360834089 %** |
| `Informe TORRE N°2!AL9` | 03-10 B, **73,1283159756 %** |
| `Validacion de leyes TM2!C6` | 03-10 B, **1** (referencia externa `[1]Reporte Diario!BJ22`) |
| `Validacion de leyes TM2!U6` | `IF(C6>0.75, VLOOKUP(03-10 B, Informe TORRE N°2, columna 38), 0)` → 73,1283159756 |
| `Validacion de leyes TM2!T7/U7` | Ambos `=U6`: arrastre a 04-10 A/B |
| `Validacion de leyes TM1!T7/U7` | T7 toma 04-10 A si `B7>0.75`; U7=`T7` |
| `Reporte por Turno!AD29/AD30` | Ponderación de `Data TM1/Data TM2` por TMS, 73,3121308679 / 73,3035313961 |

En el Excel Oficial, `Validacion de leyes TM1!B7/C7=0,76/0,76`; `Validacion de leyes TM2!B7/C7=1/0,76`. Son valores guardados o enlazados en ese archivo; no equivalen a la representatividad física calculada hoy por SIIR. En particular, la fuente externa de `TM2!C6=1` no está incorporada en el archivo como cálculo auditable, pero el valor cached y su uso en la fórmula sí están comprobados. El Excel también conserva más decimales de Malla que `Informe_TM_lab` (tres decimales); ese redondeo explica solo décimas de milésima de punto, no la brecha principal.

## Reconstrucción A/B

Los TMS de SIIR proceden del bloque de apilado del SP: TMH por torre × factor de ajuste × (1 − humedad/100); la Sal se resta proporcionalmente, sin cambiar la razón de ponderación. Factor de ajuste del 04-10: **1**; humedad usada: **4,26 %**. El cálculo reproduce el valor guardado en el cache.

| 04-10 | TM1 después de regla | TM2 después de regla | TMS TM1/TM2 SIIR | Malla SIIR | TMS TM1/TM2 Excel | Malla Oficial | Δ SIIR−Oficial |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 73,436 (04 A) | 70,742 (28-09 B) | 21.687,677 / 14.624,727 | **72,350998** | 21.673,198 / 14.614,964 | **73,312131** | **−0,961133 pp** |
| B | 73,436 (04 A) | 70,742 (28-09 B) | 24.718,652 / 18.699,878 | **72,275724** | 24.733,898 / 18.711,412 | **73,303531** | **−1,027807 pp** |

En el Excel Oficial, TM1=73,4360834089 y TM2=73,1283159756 en ambos turnos. Las ponderaciones con sus TMS reproducen `AD29` y `AD30` hasta precisión numérica. En SIIR, la ponderación de 73,436 y 70,742 reproduce el cache a menos de 0,000001 pp. El diario SIIR ponderado desde A/B es **72,310007 %**; el diario Oficial en `Generador Reporte!Z12` es **73,307445 %**; Δ diario ≈ **−0,997439 pp**.

## Dictamen

- **Fuente Oficial:** TM1 de 04-10 A + TM2 de 03-10 B arrastrada, con ponderación por TMS. **Fuente SIIR:** TM1 de 04-10 A + TM2 de 28-09 B arrastrada. Es una **selección de eventos distinta** provocada principalmente por la discrepancia de representatividad física del 03-10 B TM2 (`1` en el Excel; `0,687911` en SIIR). No es el mismo registro con una diferencia cercana a 1 pp en su valor cargado.
- **Compartir torres:** para estos turnos no se aplica cruce TM1 ↔ TM2; cada salida por TM conserva su propio origen. SIIR sí comparte el evento TM1 A hacia B y arrastra el último TM2 válido. El Excel también copia TM1 A hacia B y TM2 03 B hacia A/B mediante fórmulas directas. La regla SIIR vigente permite TM2 → TM1 cuando hace falta, pero no TM1 → TM2.
- **¿SIIR aplica correctamente su regla vigente? Sí.** Los ratios físicos, filtro `>0,75`, selección cronológica y ponderación explican exactamente el cache emitido. **¿Se recomienda modificar código SIIR? No con esta evidencia.** Primero debe conciliarse el criterio/celda de representatividad externa del Excel Oficial y su arrastre explícito. Si se decide cambiar formalmente la metodología, habría que especificar los criterios físicos y la prioridad del evento antes de proponer un cambio al SP/vistas; esta auditoría no los modifica.

**Categoría principal: A. DIFERENCIA DE REPRESENTATIVIDAD.** El arrastre fijado en el Excel es una diferencia metodológica secundaria visible; la marca de representatividad del 03-10 B es la primera divergencia que introduce el 73,1283159756 % en vez del 70,742 %. **Estado: auditoría resuelta, solo lectura.** No DML, DDL, ejecución de SP, publicación, commit ni push.
