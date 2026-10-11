Cadena TEST: `reclamo.cv25_diario` + RO → `v_cv25_diario_contingencia_test` → `v_preliminar_cv25_contingencia_test` → `v_preliminar_cv25_con_acumulado_contingencia_test` → `v_reclamo_diario_contingencia_test`; contraste en `v_diferencia_cv25_contingencia_test`. Dependencias exactas en dependencias.json.

Fórmula preservada de humedad: TMS = TMH × (1 − COALESCE(humedad_pct,0)/100). En NORMAL devuelve base.tms_dia; en contingencia aplica la misma humedad propia a SUM(RO A+B). No utiliza el 0,90 del Balance. En las cinco fechas la humedad almacenada es NULL: el factor efectivo es 1.

|Fecha|TMH oficial|TMH TEST|TMS oficial|TMS TEST|Flag TEST|Normal igualdad de valores|
|---|---|---|---|---|---|---|
|2026-08-31|35088.000000000000|35088.0|35088.000000000000|35088.0|OK|True|
|2026-09-07|23.500000000000|31387.0|23.500000000000|31387.0|SIN_HORAS_NO_REPARTIBLE|No aplica|
|2026-09-08|41.000000000000|NULL|41.000000000000|NULL|PENDIENTE_TUM|No aplica|
|2026-09-10|41.000000000000|41234.0|41.000000000000|41234.0|SIN_HORAS_NO_REPARTIBLE|No aplica|
|2026-09-13|47381.500000000000|47381.5|47381.500000000000|47381.5|OK|True|


Igualdad numérica exacta en controles normales; el tipo SQL de las masas pasa de decimal a float en TEST, por CONVERT(float) en la rama RO. No es identidad de tipos; riesgo de precisión para otros valores. Las cuatro vistas dependientes coinciden con las oficiales al normalizar espacios/CREATE y sustituir únicamente el sufijo _contingencia_test.

v_preliminar_cv25: filas oficial=0, TEST=0. Igualdad filas del 13-09=True. Sin filas en controles: no demuestra reparto con datos ni acumulados.
v_preliminar_cv25_con_acumulado: filas oficial=0, TEST=0. Igualdad filas del 13-09=True. Sin filas en controles: no demuestra reparto con datos ni acumulados.
v_reclamo_diario: filas oficial=46, TEST=46. Igualdad filas del 13-09=True. 

Se preservan expresiones de humedad, topografía, rotopalas, densidad, campañas, módulos y avances en las vistas dependientes, salvo sustitución de nombres de la cadena. Los casos sin horas no son repartibles; no deben interpretarse como validación de tonelaje asignado a módulos.
