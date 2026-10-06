# Integración DEV del timeline genérico — contrato12

Finalizado 05-10-2026: 37 comparaciones exactas PASS, invariancia V2 en 8 escenarios PASS, 63 tests PASS, smoke y Chrome PASS. Medianas runtime12 de 102 días: OX P1 0,9464 s / SULF P7 1,3428 s; 53,75× / 37,67× frente al baseline12. `git diff --check` PASS. [Informe final](../DIAGNOSTICO_TIMELINE_RUNTIME.md), [benchmark completo](benchmark_tablas.md), [integridad](integrity_final.json). En móvil se documenta el ancho reducido y recorte de textos de química existente; no se tocó UI/CSS.

Solo `lixiviacion/db.py:OP_TIMELINE_SQL` cambia en runtime. Cabecera, helpers, callbacks, panel, mapa, CSS y V2 quedan intactos. No se publican objetos SQL ni se ejecutan DDL/DML. Sin PROD, commit ni push.

## Flujo y evidencia

1. `prepare.py prepare`: respalda db.py y su SHA256, guarda SQL/asignación anterior, extrae automáticamente proyección/nombres/orden y selecciona esos12 campos del candidato genérico24. No edita runtime.
2. `validate_dev.py functional`: captura invariancia V2 previa y ejecuta37 pares SQL anterior/nuevo (35 matriz +2 ampliados). Comparación exacta bidireccional, hashes, cardinalidad, NULL, estados canónicos, campañas y reversas. Aborta ante diferencias.
3. `prepare.py integrate`: exige37 PASS y hash de db.py intacto; sustituye únicamente la asignación. Guarda `runtime.diff`.
4. `validate_dev.py benchmark`: exige que el SQL importado de db.py sea idéntico al archivo candidato12. Tres repeticiones para cada rango/caso, planes reales102d aparte. No usa tiempos del candidato24.
5. `validate_dev.py post`: compara4 KPI, JSON de3 gráficos y todas las filas reales de DataTable para general +7 parcelas; perfila cabecera/timeline/resto del callback real sin logging permanente.
6. Suite completa de Lixiviación, smoke diagnóstico sin cambios funcionales y Chrome headless sobre aplicación DEV local, reutilizando el harness previo. Capturas y tiempos de clic→render en `visual/`.

`contract.json` contiene proyecciones y aliases, parámetros y hash previo. `comparacion.json` contiene37 comparaciones; no datasets masivos. `statistics_io_time/` conserva mensajes completos; `benchmark.json` incluye30 ejecuciones normales y2 capturas XML. Los hashes antes/después documentan los archivos preservados. `db_before.py` es respaldo de evidencia, no una segunda ruta runtime.

La detección visual usa clic DOM real, performance.now y requestAnimationFrame. Cabecera debe identificar la parcela nueva y fecha final; timeline debe estar visible y renderizado con102 puntos. No basta detectar el gráfico viejo. El tiempo incluye consultas V2 previas, callback operacional, red local y render; no es solo tiempo SQL. Se guarda una observación por caso, no un SLA.

## Restricciones y rollback

No se modifica CASE, umbrales, NULL, deduplicación ni selección de fuentes. No se introduce caché, índice o materialización. La única transformación del candidato es su proyección final a12 columnas (y comentario descriptivo). El recálculo residual por expansión de CTE se deja para una tarea futura.

[ROLLBACK.md](ROLLBACK.md) contiene el comando exacto para restaurar solo el SQL original. La instrucción exige que no haya cambios posteriores en esa constante.
