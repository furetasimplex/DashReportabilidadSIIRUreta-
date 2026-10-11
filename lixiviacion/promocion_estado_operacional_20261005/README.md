# Promoción DEV detenida en precheck — 05-10-2026

No se ejecutó DDL ni se cambió la dependencia de Dash.

## Estado previo verificado

- Base DEV: `inventar_SpcHidr`.
- TEST V2 existe: object_id 974730625, tipo IF (función tabular inline), ANSI_NULLS y QUOTED_IDENTIFIER activos.
- Oficial `inventar_SpcHidr.fn_estado_operacional_parcela_diario`: no existe.
- Definición exacta TEST guardada en `01_test_v2_original.sql`; ausencia del oficial registrada en `02_oficial_previo.sql`.
- Dependencias TEST registradas por SQL Server: CPC, pad, parcela, v_drena_oxido_operacional, v_drena_sulfuro_operacional, v_flujos_oxido_unpivot y v_flujos_sulfuro_unpivot. No existen consumidores enlazados del oficial inexistente encontrados en sys.sql_expression_dependencies. Referencias textuales adicionales se conservan en `precheck.json`; esto no acredita ausencia de consumidores externos a SQL Server.

## Bloqueo canónico

| PAD / estado | Requerido en sección 8 | TEST V2 instalado |
|---|---:|---:|
| OX RIEGO | 19 | 0 |
| OX RIEGO_DRENAJE | 0 | 19 |
| SULF RIEGO | 18 | 0 |
| SULF RIEGO_DRENAJE | 0 | 18 |

10-09-2026: 60 filas, 60 claves PAD/número únicas, OX32/SULF28. Los restantes conteos coinciden. Los seis casos específicos coinciden con los valores requeridos y están guardados en precheck.json.

La instrucción exige simultáneamente cuerpo idéntico al TEST instalado y distribución exacta con RIEGO. Con la fuente actual no se pueden cumplir ambos criterios sin cambiar el requerimiento o la lógica. No se modifica ninguna regla para acomodar el resultado. La salida RIEGO_DRENAJE es además coherente con el pulido UX anterior aprobado para OX P1/SULF P7.

Se requiere resolver la referencia canónica antes de promover. Esto es una diferencia TEST instalado vs criterio documental; NO una diferencia demostrada TEST vs oficial, ya que el oficial no existe.

## Trabajo pendiente

No se creó oficial, no hay hash de un objeto oficial instalado ni validación post-deploy. No se ejecutaron auditoría histórica, comparación 15.180 filas, reversas, regresión Dash ni smoke de promoción. `map_db.py` continúa apuntando a TEST V2. TEST V2 y todos los demás objetos permanecen intactos.

## Rollback preparado, no ejecutado

Caso A (oficial inexistente al precheck): tras una futura promoción, restituir primero en map_db.py el nombre TEST V2, ejecutar smoke y luego retirar únicamente el nuevo objeto oficial según `04_rollback.sql`, verificando dependencias y conexión DEV. Hoy no corresponde ejecutar rollback porque no hubo promoción. No borrar TEST, backups ni otros objetos.

Archivos de esta tarea: script read-only `lixiviacion/precheck_promocion_estado.py` y esta carpeta de evidencias. `git diff --check` sin errores. Sin cambios de código runtime, escrituras de datos, DDL, PROD, commit ni push.
