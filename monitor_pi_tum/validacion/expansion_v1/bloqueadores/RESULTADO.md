# Resolución de bloqueadores PI/TUM V1 — 19-09-2026

**Corregidos el filtro TUM y los tipos de Reclamo TEST. Suite: 74 tests, 73 PASS, 0 FAIL, 0 ERROR, 1 SKIP.** Rollback integral de los ocho objetos de expansión V1 preparado, sin ejecutarlo.

## Archivos

Modificados en esta intervención:

- `monitor_pi_tum/postprocesar_tum_contingencia.py`: parámetro de history tomado del batch.
- `monitor_pi_tum/test_cierre_expansion.py`: agrega comprobación equivalente para template seca; conserva los dos tests antes fallidos.
- `monitor_pi_tum/validacion/expansion_v1/ddl/reclamo.v_cv25_diario_contingencia_test.sql`: elimina promoción accidental a float.
- `monitor_pi_tum/validacion/expansion_v1/preparar_sql.py`: conserva la corrección al regenerar ese DDL.

Nuevos scripts de operación/validación:

- `monitor_pi_tum/validacion/expansion_v1/cerrar_bloqueadores.py`: inspección, dry-run y aplicación transaccional exclusivamente a las cinco vistas Reclamo TEST; captura y valida tipos, definiciones y regresión.
- `monitor_pi_tum/validacion/expansion_v1/construir_rollback_integral.py`: genera el manifiesto y script sin conexión SQL.
- Esta carpeta `bloqueadores/`: definiciones antes/después, metadata, dry-runs, regresión, resultado de suite, manifiesto y SQL de rollback. Inventario exacto en [archivos_evidencia.json](archivos_evidencia.json).

`cargar_informes_tum.py` no se modificó. Los cambios preexistentes del workspace se preservaron; no se editaron objetos oficiales, PROD, cache ni factor.

## Filtro y dry-run

La consulta ya tenía `template_code=:template`, pero Python enviaba la constante `TEMPLATE='informe_tum_seca'`. Ahora envía `template`, obtenido de `import_batch.template_code` y validado contra los tres templates permitidos. Así seca consulta seca, SRR consulta SRR y Ripios consulta Ripios. No cambia la consulta de equipos, dataset, contingencia ni el conjunto de equipos que puede reprocesar apilado.

Los dos tests fallidos pasaron inmediatamente tras la corrección (2/2). La suite final incluye también el mismo contrato para seca.

|Batch DEV|Template|Cambios detectados|Períodos|Cambios equipo-turno bajo contingencia|Fechas a reprocesar|
|---|---|---|---|---|---|
|20454|informe_tum_srr|30: 10 por cada CV001/CV002/CV003|11 al 15-09, A/B|6: tres equipos × 11-09 A/B|Ninguna|
|20455|informe_tum_ripios|10: CV025|11 al 15-09, A/B|2: CV025 × 11-09 A/B|Ninguna|

Evidencia: [batch 20454](dry_run_20454.json), [batch 20455](dry_run_20455.json). Ejecutados con `commit=False`: no se escribió ni reprocesó apilado. SRR y CV025 usan consumidores dinámicos; el único reproceso permanece reservado a CV008/CV108.

## Decimal y regresión Reclamo

La causa era `SUM(CONVERT(float,valor_final_resuelto))`: al participar en CASE, float propagaba su tipo a las ramas normales y a los consumidores. Se sustituyó por `SUM(CONVERT(decimal(28,6),valor_final_resuelto))` y se fijaron las dos salidas diarias al contrato oficial `decimal(30,12)`. Se conservó la expresión de humedad `1.0 - COALESCE(base.humedad_pct,0)/100.0` y la regla de NULL pendiente.

|Vista TEST / columna|Antes|Después = oficial|
|---|---|---|
|v_cv25_diario / tmh_dia, tms_dia|float(53)|decimal(30,12)|
|v_cv25_diario / tms_estimado_r1, tms_estimado_r2|float(53)|decimal(38,6)|
|v_diferencia_cv25 / tmh_cv25, tms_cv25|float(53)|decimal(30,12)|
|v_diferencia_cv25 / diferencia_topografia_cv25|float(53)|decimal(38,6)|
|v_diferencia_cv25 / diferencia_pct|float(53)|numeric(38,6)|

Las cinco vistas TEST se recompilaron en orden de dependencia dentro de una transacción. Se compararon tipo, precisión, escala y longitud de **todas** sus columnas numéricas contra las oficiales; igualdad completa. Las demás columnas float, si existen también en el objeto oficial, no se convierten arbitrariamente. Definiciones oficiales antes/después idénticas.

El primer intento se revirtió automáticamente por un error del script al sustituir CREATE VIEW con espacios variables; se corrigió la sustitución mediante expresión regular. El segundo intento confirmó las definiciones previas y completó correctamente. No se ejecutó ningún script de rollback de objetos.

Regresión NORMAL, 31-08 y 13-09, comparando todas las columnas y valores exactos:

|Cadena oficial vs TEST|Filas comparadas|Resultado|
|---|---|---|
|v_cv25_diario|2|Iguales|
|v_preliminar_cv25|0|Ambas vacías; no prueba reparto con datos|
|v_preliminar_cv25_con_acumulado|0|Ambas vacías; no prueba acumulado con datos|
|v_reclamo_diario|17|Iguales|
|v_diferencia_cv25|2|Iguales|

Evidencia: [tipos antes](tipos_antes.json), [tipos después](tipos_despues.json), [regresión NORMAL](regresion_normal.json).

## PENDIENTE_TUM y futura captura de 51025

Verificado nuevamente en DEV: CV025 08-09 B mantiene contingencia activa, PI=0, TUM=NULL, **RO=NULL y fuente PENDIENTE_TUM**. La fuente diaria Reclamo TEST conserva TMH/TMS=NULL y `flag_preliminar=PENDIENTE_TUM`. No se sustituyó por PI ni cero. Evidencia: [RO](pendiente_RO.json), [Reclamo](pendiente_reclamo.json).

No se modificó el SP de Balance ni su guard 51025; tampoco el tratamiento visual. La captura futura debe ubicarse en el adaptador que ejecute el SP TEST, al recibir la excepción DBAPI/SQLAlchemy (número nativo SQL Server 51025), antes de intentar construir el DataFrame o continuar la exportación. No basta filtrar SQLSTATE: la evidencia previa incluye avisos 8153 junto al error nativo.

En este repositorio, la llamada directa a ese SP está en `monitor_pi_tum/validacion/expansion_v1/auditar_balance.py`, dentro de `c.execute(...)`; su `except` ya guarda el error como evidencia, no constituye integración de producto. La exportación actual usa el servicio de casos oficiales `report_export/balance_service.py`. Si se incorpora TEST a ese flujo, el límite de presentación existente es el `except BalanceReportError` de `report_export/callbacks/reportabilidad_cb.py:8019`, que evita la descarga y muestra el motivo. La traducción 51025→error de dominio debe ocurrir en el adaptador SQL previo a ese handler. No se añadió esa traducción ni un consumidor nuevo.

## Rollback y pendientes

[Manifiesto y orden seguro](ROLLBACK.md) · [Script integral](rollback_integral_v1.sql) · [Manifiesto JSON y hashes](manifiesto_rollback_v1.json).

Cobertura exacta del directorio DDL expansión V1: cinco vistas creadas (estado previo AUSENTE) y tres objetos modificados (definición previa respaldada). El script retira primero consumidores y después la fuente Reclamo; restaura los tres objetos previos. Tiene guard DEV, transacción y rechazo de dependencias externas nuevas. No toca objetos oficiales ni tablas de datos. No fue ejecutado, conforme a la instrucción.

No quedan FAIL ni defectos conocidos abiertos de los dos bloqueadores corregidos. Permanecen documentadas estas limitaciones:

- CV025 08-09 B sigue sin TUM; es el estado de datos requerido, no se resolvió artificialmente.
- El test live de cambio horario sigue SKIP explícito; [suite completa](suite_completa.txt), [resumen](suite_resumen.json).
- Las vistas preliminares no tienen filas en los controles NORMAL; no certifican casos con reparto real.
- El tratamiento visual 51025 queda diferido por instrucción.
- El rollback integral cubre **expansión V1**, no desinstala fases históricas anteriores del módulo. Su orden y cobertura se verificaron contra DDL y dependencias capturadas; no se afirma haber ejecutado una prueba real de rollback.

No se realizó ni se propone aquí una promoción a PROD.
