# F4D1: comparación manual de Factor en Publicar Reclamo

Este script no llama a `reclamo.db.publicar()` ni modifica código funcional o SQL. No se ha ejecutado la prueba real. Requiere conexión DEV configurada y guard de identidad `SIIR_DEV_SQLSERVER_HOST` vigente.

Sin `--execute-rollback` aborta antes de importar los módulos de conexión o conectar a SQL.

Ejecución manual desde la raíz, en ventana DEV sin otros writers:

```powershell
.\venv\Scripts\python.exe scripts/validate_reclamo_publicar_factor_dev.py --execute-rollback
```

Opcionalmente indicar `--output ruta/nueva.json`. No sobrescribe evidencia. El archivo contiene fotografías completas; tratarlo como datos internos de DEV.

## Protocolo

- Fecha fija 2026-09-10 a 2026-09-10, `DiasReproceso=7`. A pasa `RefrescarFactor=1`; B pasa `0`.
- La lógica SQL vigente amplía el rango efectivo a **2026-09-03 a 2026-09-10 inclusivos**. Python no calcula ni sustituye ese rango: captura todas las filas de Factor, Cache y DC, incluidas fechas fuera de la ventana. La definición SQL y su hash quedan en la evidencia para revisar la lógica realmente ejecutada.
- Cada caso tiene una transacción nueva y lock global Exclusive/Transaction, timeout 10000 ms. Baseline e inspección se realizan dentro del lock, antes del EXEC.
- La salida normal y las excepciones pasan por rollback explícito en `finally`; no se depende de alcanzar un SENTINEL. No hay context manager de confirmación ni llamada a commit.
- Un listener bloquea commits desde SQLAlchemy y se retira al finalizar. La inspección previa rechaza COMMIT internos en los tres SP de esta cadena y triggers habilitados en las tablas capturadas. Esta inspección no es un analizador general de SQL dinámico: si cambia la cadena de SP/dependencias, debe revisarse el protocolo.
- Se drenan todos los resultsets del EXEC para propagar errores SQL tardíos. No se modifica SESSION_CONTEXT desde Python.
- Después de cada rollback, una nueva conexión adquiere el lock en otra transacción rollback-only, captura las tres tablas y verifica igualdad exacta, incluidos timestamps e identities. No hace reseed ni reparaciones automáticas.
- B no ejecuta su SP si su baseline difiere del original. Un fallo de restauración o de contrato detiene la prueba y deja clasificación REVISAR_MANUALMENTE.

## Evidencia y comparación

El JSON incluye `casos.A/B.antes`, `dentro`, `despues_rollback`, estados SPID/TRANCOUNT/XACT_STATE/lock, identities, definiciones, comparaciones y respuestas explícitas.

Las comparaciones completas conservan timestamps. Las funcionales excluyen **solo** columnas llamadas Fecha_Calculo o Fecha_Actualizacion cuyo tipo SQL sea de fecha/hora; la lista exacta se registra en `columnas_auditoria`. Ninguna otra columna se descarta. Decimal se serializa sin convertir a float. La comparación es exacta, sin tolerancias numéricas.

Cada comparación informa cantidad de filas, columnas diferentes, fechas, claves y valores A/B, incluidas altas y bajas. En `baseline_vs_A/B`, A significa baseline y B significa resultado del caso; en `A_vs_B_funcional` son los dos casos.

Clasificación automática, siempre condicionada a restauración exacta, mismo baseline, Factor B intacto y cache intacto en ambos casos:

| Factor A vs baseline funcional | DC A vs B funcional | Resultado |
|---|---|---|
| Igual | Igual | REFRESCO_FACTOR_REDUNDANTE |
| Distinto | Distinto | FACTOR_PREVIO_NO_EQUIVALENTE |
| Distinto | Igual | FACTOR_ESCRITURA_NO_NECESARIA_PARA_PUBLICAR |
| Otro o anomalía | — | REVISAR_MANUALMENTE |

FACTOR_PREVIO_NO_EQUIVALENTE significa que no es seguro omitir el refresco sin preparar la fotografía. Cualquier conclusión se limita al estado y rango probados; no autoriza cambiar `publicar()` de forma general.

## Límites

El lock excluye participantes F4, no writers externos que lo omitan. Entre transacciones se libera el lock; las comprobaciones detectan divergencias en las tres tablas, pero no congelan todas las fuentes upstream. Usar una ventana controlada. Los snapshots completos pueden consumir tiempo y memoria. Una pérdida de conexión puede impedir comprobar restauración: se informa como fallo, nunca como éxito. Las identities pueden avanzar aunque SQL revierta filas; se informa y no se corrige automáticamente. No hay afirmación de restauración de tablas fuera del alcance revisado.

## Verificaciones locales, sin SQL

```powershell
.\venv\Scripts\python.exe -m py_compile scripts/validate_reclamo_publicar_factor_dev.py scripts/test_validate_reclamo_publicar_factor_dev.py
.\venv\Scripts\python.exe -m unittest scripts.test_validate_reclamo_publicar_factor_dev -v
```
