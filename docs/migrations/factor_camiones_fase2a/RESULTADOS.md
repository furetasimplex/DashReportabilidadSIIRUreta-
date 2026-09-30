# Entrega Fase 2A — desplegada en DEV, 28-09-2026

Ambiente confirmado antes de pruebas y despliegue: base `inventar_SpcHidr`, servidor SQL `VPS-5347319-X`, coincidente con la identidad DEV configurada. No se accedió a PROD.

## Resultado persistido

Solo quedan dos vigencias oficiales:

| Flota | Parámetro | Valor TMH/viaje | Desde inclusivo | Hasta exclusivo |
|---|---|---:|---|---|
| KOM | LIMITE_CARGA_AJUSTE | 380 | 01-07-2026 | NULL |
| CAT | LIMITE_CARGA_AJUSTE | 265 | 01-07-2026 | NULL |

El inicio proviene de MIN(Fecha) de Control V2, confirmado por el usuario. Seed probado dos veces sin alterar filas ni intervalos.

Objetos modificados: `sp_factor_ajuste_camiones_test`, `sp_mantiene_factor_ajuste_camiones_v2_test`, `v_ajuste_camiones_emision_test`.

Objetos nuevos: las tablas `factor_camiones_parametro_vigencia_test` y `factor_camiones_parametro_auditoria_test`, el procedimiento `sp_registrar_limite_factor_camiones_vigencia_test` y el trigger breve `tr_factor_camiones_vigencia_solapamiento_test`. Todos bajo `inventar_SpcHidr`.

La tabla V2 no cambia de esquema. La vista expone ahora `Limite_KOM_TMH_Viaje` y `Limite_CAT_TMH_Viaje` persistidos. El cálculo resuelve ambos por fecha y los devuelve al final de su contrato; el mantenedor amplía su captura INSERT EXEC y los guarda sin volver a consultar vigencias. No hay fallback numérico oculto.

## A. DERIVA PREEXISTENTE — H vs O

Se conserva la evidencia aprobada de **172 diferencias de celdas**, seis fechas que pasan de SIN_DATOS_CAMIONES a cálculo válido y el caso 22-09 (H calculado NULL/aplicado 1; O aproximadamente 0.9588138). No se corrigieron.

La última ejecución de diagnóstico registró 230 diferencias exactas de celdas H/O; el conteo incluye diferencias FLOAT de última precisión y no reemplaza el diagnóstico anterior. Cada diferencia queda identificada en `H_vs_O` del JSON final. No se usa para aceptar o rechazar parametrización.

## B. VALIDACIÓN DE PARAMETRIZACIÓN — O vs P_BASE

84 fechas, del 01-07-2026 al 22-09-2026. Misma transacción SERIALIZABLE para O y P, sobre las mismas entradas actuales. No se modifican las fuentes.

| Comparación | Diferencias funcionales | Diferencias exactas de representación |
|---|---:|---:|
| Cálculo O vs P_BASE | 0 | 33 |
| Control recalculado O vs P_BASE | 0 | 0 |
| Vista recalculada O vs P_BASE | 0 | 0 |
| Repetición del mantenedor parametrizado | 0 | 0 |
| Producción/viajes P_BASE vs P_PRUEBA | 0 | 0 |

Las 33 diferencias del cálculo son FLOAT, no se redondearon ni eliminaron de la evidencia. Dos ejecuciones del ORIGINAL en la misma transacción también produjeron 41 diferencias de representación. Esto evidencia la variación de acumulación FLOAT preexistente, compatible con orden de agregación/planes y operaciones posteriores, no cambios de entradas ni de metodología.

Máximos absolutos no nulos O/P del cálculo:

| Columnas | Diferencia máxima |
|---|---:|
| Produccion_KOM_TMH, Dato_Mina_TMH | 7.275957614183426e-12 |
| Chancado_KOM_TMH_Sin_Ajuste, KOM_TMH_Corregido, Chancado_TMH_Corregido_Total | 7.275957614183426e-12 |
| Chancado_CAT_TMH_Sin_Ajuste, CAT_TMH_Corregido | 9.094947017729282e-13 |
| Carga_KOM_Sin_Ajuste | 5.684341886080802e-14 |
| Carga_CAT_Sin_Ajuste | 2.842170943040401e-14 |
| Participacion_CAT | 5.551115123125783e-17 |
| Factor_Ajuste_Calculado | 2.220446049250313e-16 |

Las demás columnas numéricas comparadas tienen máximo cero. El JSON incluye valor O, valor P, diferencia absoluta y cota de representación por celda. Estados, flags y NULL coinciden exactamente. Los límites efectivos son 380/265 en todas las fechas.

## C. VALIDACIÓN DE VIGENCIA TEMPORAL — P_BASE vs P_PRUEBA

Candidato seleccionado automáticamente: **06-07-2026**, carga KOM 370.1761244432928 TMH/viaje, 146 vueltas.

| Fecha | KOM | CAT |
|---|---:|---:|
| D-1: 05-07-2026 | 380 | 265 |
| D: 06-07-2026 | 350 | 265 |
| D+1: 07-07-2026 | 350 | 265 |

Efecto real: KOM corregido y total corregido pasan de 54045.71416872075 a 51100 TMH. Factor calculado pasa de 1 a **0.9454958785533896**; la vista de prueba refleja el mismo factor aplicado y los límites efectivamente usados.

Segundo cambio provisional: 365 desde **09-07-2026**. Se verificó 380 antes de D, 350 desde D hasta 08-07 y 365 desde 09-07. También se insertó una vigencia intermedia y se comprobó que terminó en el inicio de la siguiente, sin eliminarla.

Reproceso 01-07 a 11-07 (D-5→D+5): cada fila persistió 380 antes de D y 350 desde D, con CAT=265. Las cinco fechas anteriores a D no presentaron diferencias.

Cambio futuro: inicio 28-10-2026; no aplica el día anterior y se mantiene al menos 180 días después si no hay otro cambio. Se verificó Es_Retroactivo=0.

Cambio retroactivo: inicio 06-07-2026, Es_Retroactivo=1, impacto 06-07→22-09. Auditoría comprobada: anterior 380, nuevo 350, fecha efectiva, registro actual, motivo de prueba y usuario VALIDACION_FASE2A. La evidencia de auditoría provisional está en el JSON; sus filas se revirtieron.

CAT también se probó reversiblemente con 250: resolución 265 el día anterior y 250 desde el día indicado.

## Integridad, concurrencia y restauración

12 rechazos verificados por código SQL: cero, negativo, flota inválida, motivo vacío, inicio duplicado, parámetro inválido, intervalo inválido, superposición, múltiples intervalos abiertos, configuración faltante, fecha anterior al seed y múltiples configuraciones simuladas.

Concurrencia real con dos conexiones: se observó la segunda sesión en espera APPLICATION por el applock específico. Tras ROLLBACK de la primera, la segunda resolvió valor anterior 380 y registró su prueba; también terminó en ROLLBACK. Seed, auditoría, control V2 y vista quedaron iguales al inicio. Evidencia: `concurrencia.json`.

Se ensayó el rollback técnico de definiciones y objetos dentro de la transacción reversible. Pasó. Se confirmó restauración exacta de H y sus timestamps, columnas previas de la vista y cadena antigua después de las pruebas. El despliegue definitivo solo creó objetos/seed y alteró las tres definiciones: **sin backfill**.

## Pruebas locales

`venv\Scripts\python.exe -m unittest scripts.test_factor_camiones_fase2a monitor_pi_tum.test_factor_camiones monitor_pi_tum.test_monitor`: **12 pruebas OK**. Incluyen integridad del bloque original de balance/producción/viajes, contratos, ausencia de constantes y regresión del panel.

`git diff --check`: correcto. No se modificó UI ni se necesitó validación visual en navegador.

## Archivos, respaldo y rollback

DDL y definiciones finales: `01_parametros.sql` a `05_v_ajuste_camiones_emision_test.sql` en este directorio. Diffs por objeto adjuntos.

Runner y pruebas nuevas:

- `scripts/factor_camiones_fase2a.py`.
- `scripts/test_factor_camiones_fase2a.py`.
- `scripts/validate_factor_camiones_fase2a_concurrency.py`.

Respaldo final y evidencia: `evidencia_20260928_102341/`: definiciones originales de los tres objetos, esquema de columnas V2, H, O, P_BASE, comparaciones completas, pruebas negativas y confirmación de restauración. Las carpetas de ensayos anteriores se conservan como trazabilidad; no son el resultado final.

Rollback: `rollback_dev.sql`, ensayado reversiblemente. Usar con guard de identidad DEV y transacción como documenta README. No debe ejecutarse como publicación ni contra PROD.

## Restricciones respetadas y pendientes

Cadena antigua: tabla y procedimiento intactos, comprobados. `mov_cam_powerbi` no recibió escrituras; su lógica de producción/viajes permanece idéntica. No se introdujeron 357/236. Sin overrides, formularios, publicación, cambios de fórmula, Reporte por Turno, Datos Conciliados o Balance.

El contrato del cálculo incorpora dos columnas finales: consumidores externos no inventariados que utilicen INSERT EXEC deberán adaptar su captura. El mantenedor V2 identificado ya está adaptado. No se asignaron permisos nuevos a un rol especialista ni se creó UI administrativa.

Se conserva el comportamiento previo de `@DiasReproceso` del mantenedor: puede ampliar el inicio hacia atrás. Si esa ampliación cruza antes del seed 01-07-2026, el cálculo ahora falla explícitamente por falta de configuración, como exige esta fase. Para procesar los primeros días del seed sin ampliación debe indicarse `@DiasReproceso=0`, tal como hacen las pruebas. No se inventa una vigencia anterior ni se recorta silenciosamente el rango.

El histórico sigue mostrando su deriva preexistente. Resolverla requiere una tarea separada. No quedó ningún límite provisional 350/365/360/250 ni fila de auditoría de pruebas. Los huecos IDENTITY generados por rollback de concurrencia son normales y no representan registros persistidos.
