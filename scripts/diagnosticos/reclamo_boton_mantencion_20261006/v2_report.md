# Reclamo backfill v2 — DEV — RESUELTO

Fecha: 2026-10-06. Servidor verificado: `VPS-5347319-X`, base `inventar_SpcHidr`.

## Causa raíz y cambio

`db.recalcular()` llamaba a `sp_auto_mantener_secuencia` antes del primer `sp_sincronizar_desde_etl`. Ese mantenimiento puede cerrar y avanzar usando `topografia_avance` todavía incompleta. En la segunda pasada no reconstruye fechas de filas que ya están `CERRADO`. Además, en `sp_auto_congelar_modulos_nuevos` el cálculo de apertura referenciaba `@Camp/@Pad/@Mod` del cursor de congelamiento en lugar del módulo elegido por el cursor de apertura.

Se agregó `@SoloPreparar bit=0` a `sp_auto_congelar_modulos_nuevos`. Con valor `1` ejecuta congelamiento, secuenciación y línea base, pero omite la apertura. Se corrigió el cálculo de fecha para usar `@CampAbrir/@PadAbrir/@ModAbrir`. Las llamadas existentes usan el valor predeterminado y mantienen sus reglas.

Orden anterior: **mantener → sync → mantener → sync → CV25 → cálculo**. Orden nuevo: **preparar sin abrir/cerrar → sync → mantener → sync → CV25 → cálculo**. Las reglas SQL de cierre, cupo y clasificación no se trasladaron a Python.

## Migración v2 y temporalidad

Se tomó el estado actual de DEV en `migration_v2_before.json`. `migrate_campaign10_sequence_dates_v2.sql` derivó fechas de `topografia_avance` `VIGENTE` y actualizó únicamente las cuatro filas con fechas distintas; no cambió estados ni topografía. `rollback_v2.sql` restaura ese snapshot solo si las cuatro filas siguen iguales a la propuesta v2. `migration_v2_after.json` registra el `OUTPUT` y `migration_persisted.json` confirma persistencia desde una conexión distinta.

| Módulo | Estado | Antes apertura/cierre | Después apertura/cierre |
|---|---|---|---|
| M12 / 76 | CERRADO | 23/09–23/09 | 14/09–17/09 |
| M13 / 77 | CERRADO | 23/09–06/10 | 17/09–26/09 |
| M14 / 78 | CERRADO | 06/10–06/10 | 26/09–29/09 |
| M15 / 79 | ABIERTO | 06/10–NULL | 29/09–NULL |
| M16 / 80 | PENDIENTE | NULL–NULL | NULL–NULL |

La convención LIVE permite actividad topográfica de M14 y apertura de M15 el mismo 29/09. `fecha_congelamiento` permanece como dato administrativo separado.

## Reproceso y verificaciones

Se ejecutó **una vez** `db.recalcular('2026-09-26','2026-10-04')` con el nuevo orden. La consulta posterior comparó las cinco filas con la lectura previa al reproceso: estados y fechas idénticos. `v2_acceptance.json` registra nueve comprobaciones PASS.

Del 26/09 al 03/10, M14/M15 conservan registros de topografía vigente y `v_reclamo_diario` marca `TOPOGRAFIA`. El 04/10 no hay topografía. `v_preliminar_cv25` devuelve M15/R2, 20 horas, 40.157,4375 TMS, `flag_preliminar=OK`. `v_reclamo_diario` devuelve `PRELIMINAR_CV25`. `v_diferencia_cv25` muestra 0 topografía, 40.157,4375 TMS preliminar y CV25 40.157,4375. La bandera `SIN_TOPOGRAFIA_SOLO_PRELIMINAR` sigue siendo coherente con ausencia de topografía.

La prueba aislada D1/D2/D5 ya estaba en `tests/backfill_date_regression.sql` y dio PASS. `tests/regression_full_pipeline.py` verificó dos pasadas con B presente en ETL pero ausente en `topografia_avance` al inicio; `regression_full_pipeline.json` guarda el PASS. Esta última es una prueba del orden Python con una conexión simulada; el reproceso DEV y su validación son la prueba integrada del caso real. La compilación DDL con rollback también pasó (`ddl_v2_compile_rollback.json`).

## Alcance y evidencia

El diff mínimo del SP está en `diff_v2_sp.patch`; el cambio de `db.recalcular` está en `reclamo/db.py`. Definiciones LIVE y hashes antes/después están en `flow_v2_live_audit.json` y `deploy_flow_v2.json`. La instrumentación temporal `DEBUG_RECLAMO_*` del trabajo anterior se conserva.

No se ejecutó publicación, no se modificó `Datos_conciliados_of`, no se tocó PROD y no se hizo commit ni push.

La corrida v1 anterior había registrado un `OUTPUT` de migración, pero el nuevo snapshot LIVE mostró las fechas antiguas y los logs 3607/3609 no mostraron acciones de campaña 10. Por eso v2 usó una transacción externa controlada por `engine.begin()` y comprobó la persistencia desde otra conexión. Esa evidencia no permite atribuir con certeza por qué desaparecieron las fechas del intento v1.
