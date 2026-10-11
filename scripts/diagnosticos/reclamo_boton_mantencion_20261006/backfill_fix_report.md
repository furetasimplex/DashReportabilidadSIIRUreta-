# Diagnóstico del backfill de secuencia Reclamo en DEV

> **Actualización v2 (2026-10-06):** el flujo fue corregido y el caso terminó `RESUELTO`. Ver `v2_report.md` y `v2_acceptance.json`. Este informe documenta el intento v1 y su estado antes de la corrección. El snapshot v2 mostró que la migración v1 no había persistido; los logs nuevos 3607/3609 tampoco registraron cambios en campaña 10. Por ello, la atribución que sigue sobre una supuesta sobrescritura por el recálculo v1 no quedó demostrada.

Fecha: 2026-10-06  
Destino verificado: `VPS-5347319-X` / `inventar_SpcHidr` (DEV)  
Alcance: PAD 2, campaña 10, módulos 76–80. No se tocó PROD, no se publicó y no se editaron tablas/vistas CV25 ni topografía.

## Hallazgo y resultado

La auditoría previa confirmó que las definiciones antiguas de tres SP usaban fecha de ejecución para crear aperturas y cierres. Se desplegaron en DEV variantes que buscan evidencia topográfica vigente y se corrigieron fechas de secuencia para 76–79. La regresión aislada de D1/D2 frente a D5 pasó.

Sin embargo, el recálculo posterior invalida el resultado de la migración histórica: el cierre ocurre en el primer paso de `recalcular()` **antes** de `sp_sincronizar_desde_etl`. Para `SOBRE_100_TOLERANCIA`, la definición desplegada toma la primera fecha del módulo siguiente si la encuentra; en ese momento el sucesor puede no tener sus registros sincronizados. Si no encuentra evidencia, usa `MAX(fecha_medicion)` del módulo actual. Eso produjo cierres en fechas ya existentes/recientes y no conservó el límite histórico previsto. Después se ejecuta sync y el segundo mantenimiento; una secuencia ya marcada `CERRADO` ya no participa en el cierre de `sp_auto_cerrar_y_avanzar_secuencia`.

El resultado final leído en DEV a las 14:38:24 UTC fue:

| Módulo | Estado | Apertura | Cierre |
|---|---|---|---|
| 76 / M12 | CERRADO | 2026-09-23 | 2026-09-23 |
| 77 / M13 | CERRADO | 2026-09-23 | 2026-10-06 |
| 78 / M14 | CERRADO | 2026-10-06 | 2026-10-06 |
| 79 / M15 | ABIERTO | 2026-10-06 | NULL |
| 80 / M16 | PENDIENTE | NULL | NULL |

Topografía existente confirma M14 desde 2026-09-26 hasta 2026-10-03 y M15 desde 2026-09-29 hasta 2026-10-03. En la vista `v_preliminar_cv25` y en `v_reclamo_diario` no hubo filas para 2026-10-04, PAD 2/campaña 10. `v_diferencia_cv25` mostró CV25 TMS 40,157.4375, 20 horas R2, 0 topografía, 0 preliminar y bandera `SIN_TOPOGRAFIA_SOLO_PRELIMINAR`.

Por lo tanto, **no está verificada la recuperación funcional del 04/10**. El fix desplegado y la migración no deben considerarse cerrados. No se aplicó rollback porque su guarda exige que las cuatro filas sigan con las fechas propuestas, condición que ya no se cumple; el rollback se detendría sin escribir.

## Causa de los cambios observados

La SP `sp_auto_mantener_secuencia` llama a `sp_auto_cerrar_y_avanzar_secuencia` antes de `sp_auto_congelar_modulos_nuevos`. La secuencia del recálculo llama a mantenimiento antes del primer sync, luego sync, y luego mantenimiento otra vez. La fecha de transición del cierre no está coordinada con esa secuencia de sync: su evidencia de sucesor puede estar ausente en el primer mantenimiento. La fecha de apertura calculada durante el congelamiento solo sirve para módulos `PENDIENTE`, por lo que no repara el cierre de filas ya cerradas.

Los logs guardados antes de esta ejecución muestran IDs 3601 y 3604; no se obtuvo una lectura de los logs nuevos tras el recálculo por error TLS intermitente. No atribuyo a esos logs anteriores los cambios del recálculo.

## Artefactos y diff

- Comparación de SP antes/después, regresión, DDL validado, hashes y scripts reversibles: esta carpeta, especialmente `live_backfill_sql_audit.json`, `deploy_result.json`, `regression_result.json`, `migration_result.json` y `fixes/`.
- Consulta final de secuencia/vistas/topografía: `post_reprocess_validation.json`.
- La migración inicial cambió únicamente campos de fecha de IDs 1199, 1200, 1259 y 1260; el reprocess posterior volvió a cambiar las fechas operacionales vía SP.
- No se cambió regla de clasificación CV25, datos fuente de CV25, topografía ni estado de módulos de forma manual.

## Siguiente acción requerida

El ajuste debe tratar cierres/aperturas de secuencia después de que el sync incorpore la topografía, o hacer que toda rama de transición calcule y preserve la misma fecha histórica con evidencia fuente verificable antes del primer sync. Preparar una prueba de secuencia completa (mantenimiento → sync → mantenimiento → CV25 → cálculo) sin escrituras productivas antes de reintentar la migración histórica. No ejecutar otra recalculación en DEV hasta preparar y validar ese cambio, porque el flujo actual volvió a sobrescribir el backfill.
