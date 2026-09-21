# Utilidad histórica de migración — agosto 2026

`refresh_and_validate_dev.py` pertenece a la migración de fuentes Clays/CuFe.
`refresh_resultset_1.csv` documenta una ejecución el **29-08-2026 21:14:29.937**,
con ocho actualizaciones de trazabilidad. Los snapshots y el resumen adjunto
son evidencia histórica, no prueba de operación periódica actual.

**No es una ruta operacional F4 y no debe usarse como mantenimiento periódico.**
Sus etapas Clays y cache usan commits independientes: no constituyen una única
transacción. Un error posterior no revierte una etapa ya confirmada.

Para revisión histórica, preferir `--validate-only`. Ese modo evita los EXEC
de escritura SQL, pero consulta la base configurada y genera archivos locales;
depende de snapshots/resultsets conservados de la migración. El resumen puede
incorporar cantidades de aquella corrida, no de una ejecución nueva.

El script histórico conserva su comportamiento: sin `--validate-only` escribe.
No tiene parser de ayuda; no asumir que `--help` evita la ejecución.

Si se pretende reutilizarlo operacionalmente, requiere revisión y rediseño bajo
el lock global `SIIR_CONTINGENCIA_PI_APILADO_DEV` y una transacción exterior única
para las escrituras relacionadas. Esta documentación no autoriza esa reutilización
ni modifica SQL, defaults, locks o commits del script.
