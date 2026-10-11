# Reclamo CV25: cero confirmado por corriente

Cambio acotado a DEV, 07-10-2026. No se cambiaron datos crudos, procedimientos, topografía, camiones, secuencia ni reglas de publicación.

## Archivos solicitados

- `definicion_before.sql`: definiciones DEV previas de `v_cv25_diario`, `v_preliminar_cv25` y `v_reclamo_diario`, capturadas por `OBJECT_DEFINITION`.
- `alter_v_cv25_diario.sql`: único DDL aplicado a DEV. Mantiene las columnas de la vista; cambia la estimación por rotopala y el flag del día sin horas, con cobertura.
- `rollback.sql`: restaura exclusivamente la definición anterior de `v_cv25_diario` mediante `ALTER VIEW`. No se ejecutó.
- `validacion_04_06_oct.sql`: consultas SELECT reproducibles para los tres días, vista preliminar, vista final y estado de la tabla calculada.
- `before_after.csv`: valores antes/después, CV25 crudo y fuente preliminar.
- `resultado.md`: dictamen y límites de la validación.

Los auxiliares `audit_readonly.py`, `prepare_sql.py`, `deploy_dev.py`, `validate_dev.py`, `validate_dashboard.py`, `snapshot_before.json` y `snapshot_after.json` documentan cómo se obtuvo y comprobó la evidencia. `deploy_dev.py` compara la definición viva con la capturada antes de alterar la vista y verifica la nueva definición dentro de la transacción.

## Semántica

Para cada rotopala, si `cv.tms_dia IS NULL`, la estimación sigue `NULL`. Si CV25 vale cero, se conserva la regla vigente de estimación cero. Si CV25 es positivo y la rotopala tiene cero horas **con cobertura de corriente (`horas_con_dato_rX > 0`)**, su estimación es cero explícito. Si tiene cero horas **sin cobertura**, es `NULL`; no se deduce ausencia de operación de la actividad de la otra rotopala. En los demás casos se mantiene la distribución proporcional por horas.

El 05-10 el `flag_preliminar` pasa de `SIN_HORAS_NO_REPARTIBLE` a `CERO_OPERACION_CONFIRMADO`. La tabla `cv25_diario` conserva sus 18 TMS. La vista `v_preliminar_cv25` admite cero porque filtra por `IS NOT NULL`; la vista `v_reclamo_diario` sigue dando prioridad a topografía cuando existe.

El panel `reclamo/panel.py::cb_avance` cuenta fuentes sobre las filas del PAD y rango seleccionados. Muestra el texto de respaldo total únicamente cuando **todas** esas filas son `TOPOGRAFIA`. Muestra por separado preliminares, `SIN_DATO` y ajustes. El valor numérico cero de una fila `PRELIMINAR_CV25` no altera su clasificación.
