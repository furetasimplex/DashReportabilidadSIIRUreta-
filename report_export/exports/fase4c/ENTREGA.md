# FASE 4C — implementación preparada, pendiente de validación manual DEV

No se da la fase por cerrada. No se ejecutó un refresco real de Representatividad durante esta implementación. Las consultas reales fueron de lectura en DEV; no se tocó PROD, no se promovieron objetos y no hubo commit/push de Git.

## Cortes comprobados antes de editar

Para septiembre completo (2026-09-01 a 2026-09-30), ambas funciones devolvieron **2026-09-15**: corte operacional de Representatividad y corte RTO/Apilado. Ninguno fue más restrictivo. Se conserva el corte de Representatividad para preservar su semántica y se limita la invocación del coordinador RTO a ese corte. Si RTO devuelve un corte distinto, se aborta toda la transacción; no se recorta silenciosamente Representatividad.

## Cambio y contrato transaccional

Antes: corte → lock mensual Session → Apilado, Resumen, Representatividad y BD Ton, con transacciones individuales.

Ahora: lock mensual Session → una transacción exterior → lock global Transaction → lectura del corte → coordinador RTO (Apilado → Histórico → Factor → Clays → Cache) → Resumen → Representatividad → BD Ton → validación de transacción/lock → commit exterior → liberación mensual.

Todos los pasos de datos reciben la misma conexión. El lock mensual conserva recurso `rep_torres_refresco:YYYY-MM` y timeout 180000 ms. El global conserva `SIIR_CONTINGENCIA_PI_APILADO_DEV`, Exclusive, Transaction y timeout 10000 ms. Se adquiere antes de leer el corte y el coordinador RTO vuelve a adquirir el mismo recurso de forma reentrante dentro de la misma transacción. No existe un tercer lock; el global se libera al finalizar la transacción.

Los dos commits de control asociados a adquirir/liberar el lock Session están fuera de la transacción de datos. No hay commits intermedios del refresco desde Python. Los COMMIT anidados de los SP existentes no deben confirmar la transacción exterior; su comportamiento real queda pendiente de la prueba manual.

El orden es siempre mensual → global. Los flujos existentes PI/TUM/RTO/DC usan el global; cualquier caller futuro que necesite ambos debe respetar este orden. Si falla la liberación del lock Session, se invalida la conexión para evitar devolver una sesión bloqueada al pool y se conserva el error primario del refresco.

## Archivos y funciones

- `report_export/report_export.py`: `fetch_fecha_corte_operacional_representatividad` acepta `conn` opcional sin cambiar su consulta; `refrescar_representatividad_para_exportacion` reutiliza RTO y una transacción exterior; nuevo `_validar_refresco_representatividad` comprueba TRANCOUNT=1, XACT_STATE=1 y lock global Exclusive.
- `report_export/tests/test_refresco_representatividad.py`: simulaciones de orden, conexión compartida, locks, fallos, rollback, cortes y SENTINEL tras validación real del helper.
- `report_export/tests/test_orquestacion_reporte_turno.py`: corrección de una expectativa AST desactualizada de FASE 4B2: tres llamadas directas a RTO y delegación del helper DC a su coordinador. No cambia el callback.
- `scripts/validate_representatividad_atomicity_dev.py`: prueba manual DEV rollback-only.

`FASE4C.diff` contiene el diff exacto contra las copias tomadas al iniciar esta tarea, excluyendo cambios previos del usuario. `integridad.json` registra las comprobaciones de funciones y archivos que debían permanecer intactos. Los backups `.antes` permiten revisar ese punto de partida.

## Validación automatizada

`py_compile` pasó para el módulo de reportes y el script manual.

```powershell
.\venv\Scripts\python.exe -m py_compile report_export/report_export.py scripts/validate_representatividad_atomicity_dev.py
.\venv\Scripts\python.exe -m pytest report_export/tests/test_refresco_representatividad.py report_export/tests/test_orquestacion_reporte_turno.py report_export/tests/test_factor_ajuste_camiones_report.py monitor_pi_tum -q --disable-warnings
```

Resultado: **110 PASS, 1 SKIP, 0 FAIL; 142 subtests PASS**. El SKIP corresponde a una prueba SQL DEV que requiere habilitación explícita. Se verificaron fallos en RTO, cada uno de los tres SP posteriores y validación final, liberación mensual, conservación del lock global hasta BD Ton y ausencia de commits de datos intermedios. El `--help` del script manual también pasó.

`git diff --check` señala un espacio final preexistente en la sección de Datos Conciliados de `report_export.py` (línea 836 al verificar). Se dejó intacto por estar fuera de alcance; no se declara este chequeo limpio.

## Prueba manual pendiente

Desde la raíz, en una ventana DEV sin otros writers:

```powershell
.\venv\Scripts\python.exe scripts/validate_representatividad_atomicity_dev.py --execute-rollback --date 2026-09-10 --output report_export/exports/fase4c/manual_dev.json
```

El script valida identidad DEV, exige activación explícita y rechaza sobrescribir evidencia. Captura SPID, conexión DBAPI, TRANCOUNT, XACT_STATE y ambos locks. Toma hashes y conteos de todas las filas de las nueve tablas solicitadas más `trazabilidad_analitos_tm_emision_test`. Captura una fotografía dentro de la transacción, inyecta SENTINEL después de la validación final y compara la fotografía posterior al rollback contra la inicial. Una barrera adicional en el evento commit impide confirmar una conexión marcada con operaciones de refresco si no se alcanzara el SENTINEL final.

La instrumentación es temporal en memoria. No altera objetos SQL. El código de salida es distinto de cero ante errores o checks fallidos. La evidencia interna permite comprobar qué cambios temporales ocurrieron; todavía no hay resultados empíricos de esta prueba.

## Riesgos y límites pendientes

- SQL Server puede avanzar contadores IDENTITY aun con rollback. Existe identidad en `Clays_CuFe_trazabilidad`; el script compara también esos contadores y reportará fallo si cambian, sin reseed automático. Restaurar filas no implica restaurar identidad.
- Los snapshots abarcan tablas completas: pueden ser costosos y detectar cambios de writers concurrentes ajenos. Ejecutar la prueba en una ventana controlada DEV.
- Los writers legacy/manuales que no adquieren el global no quedan excluidos por este cambio. Deben estudiarse antes de integrarlos.
- El lock protege la cadena de refresco. No se extendió a lecturas/exportaciones posteriores a su finalización ni se cambió su aislamiento; otra actualización posterior puede preceder a esas lecturas.
- La comprobación final asegura estado transaccional y lock, no demuestra por sí sola atomicidad real de los SP ni igualdad funcional de los datos. Eso corresponde a la validación manual pendiente.

No se modificaron callbacks, monitor PI/TUM, coordinadores RTO/DC, fórmulas, SP/objetos SQL, reglas SRR/tag, umbral 0.75, templates Excel ni reglas de Representatividad/BD Ton/FY/Pad/comentarios. PROD permanece intacto respecto de esta intervención.
