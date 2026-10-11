# Recuperación — no ejecutada automáticamente

`before.json` contiene conteos y hashes por fecha; `backup_logico/*.json` conserva todas
las filas de septiembre de los once destinos, con NULL explícito y decimales como
texto exacto. `columns.json` identifica tipos, identities y columnas calculadas;
`definitions/` conserva las definiciones revisadas. `outside_before.json` firma los
resultados fuera de septiembre, incluido octubre, sin respaldos masivos de fuentes.

Ante error: detener la cadena, conservar `ejecucion.json` y no ejecutar downstream.
Los coordinadores gestionan su rollback transaccional. Los bloques COMMIT anteriores
permanecen materializados. Un error de conexión durante commit podría requerir
reconciliación read-only antes de determinar su estado; no reintentar automáticamente.

No restaurar parcialmente tablas relacionadas ni ejecutar DELETE manual improvisado.
Si se decide una restauración, preparar una operación revisada bajo los mismos locks,
verificar ausencia de escritores concurrentes y restaurar coherentemente los once
destinos del período exacto. Respetar identities (BD_Ton/DC/auditoría), claves y tipos;
no convertir NULL a cero. Preservar trazabilidad de ejecuciones posteriores legítimas.
Comparar contra firmas previas y confirmar integridad fuera del período.

Alternativa preferible si el problema es una fuente corregible: reproceso oficial del
bloque fallido y downstream, tras diagnóstico y aprobación del plan concreto.
Este documento no ejecuta ninguna restauración ni altera octubre/PROD.
