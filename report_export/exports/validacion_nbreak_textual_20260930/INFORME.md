# Corrección textual N_BREAK — DEV, 30/09/2026

**Persistida con COMMIT y verificada desde una conexión nueva.** Primero se ejecutó
la prueba reversible con ROLLBACK y se verificó la restitución de definiciones y datos.

## Alcance

Únicamente se alteraron `fn_resolver_vueltas_camiones_test` y
`v_vueltas_camiones_diarias_test`, en `inventar_SpcHidr` DEV.
La vista conserva por separado NULL real y fallo de conversión textual. Antes de
convertir PowerBI aplica `NULLIF(LTRIM(RTRIM(n_break)),N'')`; la ausencia de texto
numérico invalida la fuente con `NBREAK_NO_NUMERICO`, sin convertirse a cero.
El resolvedor recibe dos contadores adicionales de no numéricos. Su único consumidor
SQL de producción, la vista diaria, fue actualizado en la misma transacción.
La prueba anterior del resolvedor también pasa explícitamente esos dos contadores.

Clasificación: NULL real → NBREAK_NULL; vacío/espacios/texto no convertible →
NBREAK_NO_NUMERICO; negativo → NBREAK_NEGATIVO; cero individual permitido;
solo ceros → SOLO_CEROS; suma positiva sin defectos → OK.
Si coexisten defectos: NULL, no numérico, negativo, en ese orden. Todos invalidan.
Se conserva MOV_CAM → PowerBI → SIN_DATOS_CAMIONES, sin mezcla entre flotas.

No se alteraron parámetros, nominales, límites, vigencias, fórmulas, SPs de cálculo,
override, orquestación ni consumidores. No se ejecutó un reproceso materializador:
se ejecutaron ambos SPs de cálculo para comparar sus resultados, sin escribir V2.

## Validación

- 17 casos SQL sobre el cuerpo real de la vista instalada, sustituyendo únicamente
  las tablas fuente por fixtures CTE; ninguna inserción en fuentes.
- Individuales: NULL, '', '   ', 'abc', '-1', '0', ' 0 ', '1', '1.5'.
- Combinaciones: 10 con vacío, abc, NULL, -1 y 0; solo cero incluido arriba.
- Fallback: MOV inválido/PBI válido; MOV válido/PBI inválido; ambas inválidas.
- Ensayo ROLLBACK, despliegue y post-deploy: todos aprobados.
- Comparación exacta de ambas rutas de cálculo para 89 fechas, 01/07–27/09/2026.
- Delta factor = 0 en las 89 fechas. Fuentes, vueltas y producción sin cambios.
- Snapshot completo V2, vista de emisión, parámetros, auditoría, override,
  Datos Conciliados y cache: idéntico antes/después, incluidos valores NULL.
- 114 tests locales y 50 subtests aprobados. Advertencias preexistentes de openpyxl.
- `git diff --check`: aprobado (solo advertencias CRLF preexistentes).

## Archivos de la corrección

- `docs/migrations/factor_camiones_nominales_dev/04_resolver_vueltas.sql`
- `docs/migrations/factor_camiones_nominales_dev/05_vueltas_diarias.sql`
- `scripts/validate_factor_nominales_dev.py`: adaptación de invocación del test.
- `scripts/validate_nbreak_textual_dev.py`: pruebas integrales, regresión y despliegue.
- README de migración e informe anterior actualizados con esta corrección.

## Evidencia y respaldo

`before_definitions.json` conserva las dos definiciones inmediatamente anteriores;
`deployed_definitions.json`, las instaladas. `before.json`, `trial_after.json` y
`deploy_after.json` conservan las comparaciones completas.
`trial_OK.json` acredita ROLLBACK; `deploy_OK.json` acredita COMMIT y post-deploy.
`trial_cases.json`, `deploy_cases.json` y `postdeploy_cases.json` contienen los 17 casos.
`deploy_comparacion.csv` contiene las 89 fechas.

`rollback_textual.sql` revierte solo esta corrección, sin modificar datos. Ejecutar
con un cliente que se detenga ante errores de batch (por ejemplo sqlcmd -b), tras
verificar identidad DEV y ausencia de cambios posteriores. No se ejecutó un rollback
definitivo. El rollback global anterior detectará estas definiciones nuevas y se
bloqueará por seguridad; para utilizarlo debe restaurarse primero esta capa textual.

No PROD. No commit/push de Git.
