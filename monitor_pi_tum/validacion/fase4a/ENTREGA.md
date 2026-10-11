# FASE 4A — concurrencia PI/TUM

Implementada únicamente FASE 4A. No se ejecutaron eventos, batches reales con `--commit`, conexiones SQL ni pruebas concurrentes contra DEV. No se continuó a FASE 4B.

## Diff funcional

- `monitor_pi_tum/db.py:159`: helper privado `_adquirir_lock_contingencia(conn)`, extraído del SQL ya repetido en PI. Conserva exactamente Resource `SIIR_CONTINGENCIA_PI_APILADO_DEV`, Mode `Exclusive`, Owner `Transaction`, Timeout `10000` ms y el mensaje de error existente. Acepta resultados 0/1; rechaza negativos y ausencia de resultado. No abre conexión, no hace commit/rollback y no libera el lock.
- `monitor_pi_tum/db.py:179,472`: rango y alta/cierre reutilizan el helper en el mismo punto de sus transacciones, sin cambiar el flujo funcional. El caso anómalo sin resultado se normaliza al error controlado que ya usaba rango; previamente el caller puntual habría producido TypeError al comparar None.
- `monitor_pi_tum/postprocesar_tum_contingencia.py:124`: `commit=True` llama al helper inmediatamente después del guard DEV y antes de `planificar`. Misma conexión/transacción hasta verificación y salida. Dry-run permanece sin lock. Sin retry automático.
- `monitor_pi_tum/test_postprocesar_tum_contingencia.py`: actualiza conexión simulada y agrega cinco tests de orden, contrato del lock, resultados 0/1, fallas SQL/códigos negativos/None y dry-run sin escritura.

[FASE4A.diff](FASE4A.diff) contiene el diff exacto frente al inicio de esta fase; archivos anteriores preservados como `*.antes`. No confundir con cambios previos presentes en Git.

## Validación

Ejecutados con `venv/Scripts/python.exe`:

1. `-m py_compile monitor_pi_tum/db.py`: OK.
2. `-m py_compile monitor_pi_tum/postprocesar_tum_contingencia.py`: OK.
3. `-m pytest monitor_pi_tum -q --disable-warnings`: **79 PASS, 1 SKIP, 0 FAIL; 113 subtests PASS**.

Baseline anterior a esta fase: **74 PASS, 1 SKIP, 0 FAIL; 106 subtests PASS**. No se encontraron fallos preexistentes en esta suite. Incluye `test_gestion.py`, `test_rango.py` y `test_postprocesar_tum_contingencia.py`.

Los tests demuestran `begin → guard → lock → planificar → reprocesar → verificar → salida`, identidad de conexión y ausencia de commit/liberación prematuros. Un lock fallido impide planificar/reprocesar/verificar, se intenta una sola vez y la excepción alcanza `__exit__`. El test existente de fallo del reproceso sigue propagando el error al contexto. Dry-run devuelve el mismo plan y solo ejecuta SELECT. Son pruebas simuladas, no certificación de concurrencia real de SQL Server.

## Integridad y alcance

[integridad.json](integridad.json) confirma comparación textual idéntica de `reprocesar_apilado` antes/después y hashes SHA-256 iguales de `report_export/report_export.py` y `report_export/callbacks/reportabilidad_cb.py`.

**Report_export, callbacks de reportabilidad, Representatividad, definiciones SQL, reglas de negocio/SRR y PROD quedaron intactos en esta fase.** No se modificaron firma, orden, parámetros, rangos, Clays ni Cache de FASE 3. No hubo commit ni push.

La protección agregada cubre TUM frente a los callers PI que usan el mismo lock. No cierra concurrencia con reportes ni writers secundarios: pertenecen a FASES 4B/4C, no implementadas aquí.
