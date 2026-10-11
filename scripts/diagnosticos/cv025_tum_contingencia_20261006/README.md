# CV025 PI/TUM — DEV — 2026-10-06

**Estado: `CV025_TUM_PASS_CON_OBSERVACIONES`.** Cambio aplicado en `VPS-5347319-X / inventar_SpcHidr`, sin PROD, publicación, commit ni push. No se ejecutó mantenimiento de Datos Conciliados ni recalculo general de Reclamo.

## Causa y corrección

`reclamo.sp_cargar_cv25_horas` tomaba `cv025tot` diario de `inventar_SpcHidr.vista_resumen_datos_filtrados` tanto para PI crudo como para `tmh_dia/tms_dia`. La contingencia TUM por turno en `v_contingencia_totalizador_resuelto_turno` no llegaba a `reclamo.cv25_diario`. Elegir TUM solo durante el PI plano y PI en la recuperación habría duplicado el catch-up.

La nueva vista `inventar_SpcHidr.v_contingencia_cv025_diario_resuelto` detecta el primer día con PI técnicamente plano y TUM_DIRECTO positivo, sigue hasta el primer día de recuperación PI, exige dos turnos TUM_DIRECTO completos por día y compara la masa PI **diaria** cruda de toda la ventana con TUM. Solo una igualdad exacta reconcilia y distribuye todo el episodio con TUM, incluido el día de recuperación. No fija las fechas canónicas en la vista. La vista conserva PI, TUM, estado, episodio, residual, razón y batch/archivo A/B.

`sp_cargar_cv25_horas` mantiene `tmh_cv025tot`/`tmh_cv025_tot` como PI crudo y usa el valor resuelto en `tmh_dia/tms_dia`. `tag_utilizado='TUM_CV025'` identifica la procedencia; se amplió `CK_cv_tag` con `TUM_CV025` y `SIN_RESOLVER`. La humedad vigente se aplica exactamente como antes y las horas mantienen su MERGE original. Se ajustaron `v_cv25_diario` y `v_diferencia_cv25` para señalar valores sin resolver como NULL, sin tratarlos como cero medido. Las otras vistas de contingencia y las reglas de módulo/topografía no se modificaron.

## Evidencia

| Control | Resultado |
|---|---|
| Simulación read-only 01–15 | Detecta 07-B→11-A automáticamente; 01–05 y 12–15 sin cambio; 06 sigue 0. |
| Vista ejecutada como SELECT antes del DDL | 15 días correctos; 07–11 reconciliado; 06-oct sin TUM devuelve `SIN_TUM_NO_RESOLUBLE`/NULL. |
| DDL dry-run | Cinco lotes compilaron en transacción revertida. |
| PI crudo 07–11 | 23,5; 41; 41,125; 41; 140.342,375 TMS, intacto. |
| CV25 resuelto 07–11 | 31.387; 4.616; 0; 41.234; 63.252 TMS. |
| Masa 07–11 | PI **140.489** = TUM/resuelto **140.489** TMS; residual **0**. |
| Idempotencia | Dos reprocesos en una transacción; hash de filas de negocio CV25 idéntico. |
| Regresión 01–05 / 12–15 | 0 diferencias. |
| Topografía | 15 valores diarios idénticos antes/después; ninguna tabla topográfica escrita. |
| Horas | 60 filas de valores de negocio idénticas. |
| CV006/008/108 y SRR 001/002/003 | 180 filas de resolución idénticas. |
| Lectura independiente post-commit | 15 filas CV25 y del gráfico verificadas desde otra conexión. |

El gráfico `v_diferencia_cv25` ahora muestra 07=31.387, 08=4.616, 09=0, 10=41.234 y 11=63.252 TMS. El pico de ~140 mil TMS del 11 desaparece. Topografía sigue 07=29.015,894387, 08=4.041,694207, 10=30.322,899543 y 11=67.667,839155 TMS; es contraste independiente, no entrada del cálculo CV025.

`v_rendimiento_rotopala` consume el CV25 nuevo y registró 24 diferencias de campos derivados en los 30 registros del 01–15, concentradas en días afectados. El 11 su masa asignada pasa de 93.561,583333/46.780,791666 a 42.168/21.084 TMS para R1/R2. En 07/08/10 no hay horas suficientes para asignar rendimiento por rotopala; la vista mantiene NULL. Las vistas preliminares tienen 0 filas de septiembre 01–15 con la secuencia abierta actual; no se alteraron sus reglas.

## Observaciones y límites

- No hay tolerancia de reconciliación configurada en los objetos PI/TUM auditados. Se usó igualdad exacta, que pasa para el episodio canónico; cualquier residual no cero requiere revisión.
- La suma PI por turnos el 11 difiere del PI diario usado por Reclamo. La reconciliación usa el contrato diario real de `cv25_diario`, no suma PI por turno.
- El gráfico y las vistas derivadas quedaron actualizados; `reclamo.calculo_diario` y `Datos_conciliados_of` no se recalcularon. Véase `downstream_impact.md` para el orden y alcance de un reproceso posterior.
- `rotopala_horas_turno.fecha_registro` puede cambiar por el MERGE de horas existente al reprocesar; los valores de operación, muestras, factor y bandera quedaron idénticos.

## Artefactos

- `live_objects_before.sql` y `live_before.json`: definiciones LIVE, hashes, restricciones y datos previos.
- `cv025_view_select.sql`, `simulation_20260901_15.csv/json`, `view_select_result.json`: simulación y consulta read-only previas al DDL.
- `episodio_0709_1109.md`, `mass_balance_before_after.json`: episodio y balance.
- `ddl_deploy.sql`, `rollback_cv025_contingencia.sql`, `diff.patch`: cambio y reversión preparados. El rollback no se ejecutó.
- `post_deploy_validation.json`, `post_commit_readonly.json`, `idempotencia.json`, `regression_normal_days.json`: verificaciones transaccionales e independientes.
- `downstream_impact.md`: materializados y orden de reproceso.
