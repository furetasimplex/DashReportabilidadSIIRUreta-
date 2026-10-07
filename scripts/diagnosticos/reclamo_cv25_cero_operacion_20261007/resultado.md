# Resultado DEV

**Estado: CV25_CERO_OPERACION_PASS.** Captura anterior: 07-10-2026 10:47, base `inventar_SpcHidr`. Validación posterior: 07-10-2026 10:54. Se alteró solo `reclamo.v_cv25_diario`; el código Python modificado es `reclamo/panel.py`, callback `cb_avance`.

## Resultado por día

| Día | Cobertura R2 | Horas R2 | CV25 crudo TMS | Estimación R2 antes | Estimación R2 después | Estado |
|---|---:|---:|---:|---:|---:|---|
| 04-10 | 24 | 20 | 40.157,4375 | 40.157,4375 | 40.157,4375 | Sin regresión |
| 05-10 | 24 | 0 | 18 | NULL | **0** | `CERO_OPERACION_CONFIRMADO` |
| 06-10 | 19 | 4 | NULL, `SIN_RESOLVER` | NULL | NULL | No se inventó cero |

El 05-10 `v_preliminar_cv25` devuelve exactamente una fila R2: campaña_id 10, PAD2, módulo 80 (M16), `fuente_reclamo=PRELIMINAR_CV25`, `tms_preliminar_dia=0` y `m3_preliminar_dia=0`. `v_preliminar_cv25_con_acumulado` y `v_reclamo_diario` también muestran esa fecha/módulo; esta última conserva fuente `PRELIMINAR_CV25` y tonelaje cero. No apareció fila preliminar R2 del 06-10.

La cobertura R1 es cero en estos días. En el 04-10, donde opera R2, el resultado R1 pasó de cero inferido a `NULL`: no hay evidencia de corriente R1 para confirmar ausencia de operación. Esta distinción implementa la regla solicitada de no fabricar un cero cuando falta cobertura. El CV25 crudo, sus flags y tags permanecieron idénticos entre las capturas.

## Mensaje del dashboard

Antes, `cb_avance` mostraba «Todo el período tiene respaldo topográfico» siempre que no hubiera `PRELIMINAR_CV25`. En la tabla `calculo_diario` observada para PAD2 el 04-10 hay **2 filas TOPOGRAFIA y 10 SIN_DATO**, ejemplo concreto del falso mensaje. Ahora el callback cuenta por fuente para el PAD/rango elegido. La validación aislada pasó cuatro casos: solo topografía, solo `SIN_DATO`, preliminar de **0 TMS** junto con `SIN_DATO`, y ajuste manual. En el caso mixto mostró ambas situaciones y omitió la afirmación de respaldo total.

**Límite operativo:** el panel lee `reclamo.calculo_diario`, una tabla materializada. Al cierre de esta validación solo tenía filas del 04-10 en el rango auditado; el preliminar cero del 05-10 ya existe en las vistas, pero aparecerá en el panel después del reproceso ordinario de `calculo_diario`. Ese reproceso no se ejecutó aquí. Si llega topografía real, `v_reclamo_diario` mantiene su prioridad sobre el preliminar según el `CASE` vigente; no se cambió esa vista.

Se verificaron `py_compile` de Python modificado y auxiliares, `git diff --check`, la definición DEV posterior al DDL y los resultados SELECT. No hubo publicación, commit ni push.
