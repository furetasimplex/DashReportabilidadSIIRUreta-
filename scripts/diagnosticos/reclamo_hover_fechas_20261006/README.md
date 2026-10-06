# Hover de fechas de Cuadratura — DEV, 2026-10-06

Resultado: `HOVER_FECHAS_CUADRATURA_PASS`.

`reclamo/panel.py::cb_cuadratura` conserva tres series (`Camiones`, `Rotopala`, `Volumen congelado`) y sus valores. El tooltip unificado añade `Fecha inicio` y `Fecha fin` en la serie de volumen, con formato `DD-MM-YYYY` o `—` si no hay movimiento disponible. No añade trazas, cifras ni campos a la tabla.

`reclamo/db.py::cuadratura` mantiene las columnas y la vista original `reclamo.v_cuadratura_modulo`; añade dos fechas mediante `OUTER APPLY` de solo lectura:

- Movimiento posterior al corte: `reclamo.v_topografia_resuelta.fecha_medicion` cuando `m3_incremento > 0`, y `reclamo.v_camiones_acumulado.fecha` cuando `m3_camiones_dia > 0`.
- Movimiento de línea base anterior al corte: `inventar_SpcHidr.control_reclamo_diario.fecha` y `inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario.fecha` cuando `volumen_diario_m3 > 0` y la línea base correspondiente del módulo es positiva. Son las fuentes que usa `reclamo.sp_establecer_linea_base` para `m3_rotopala_previo` y `m3_camiones_previo`.

Las fechas son `MIN` y `MAX` de esos movimientos por `campaña_id, modulo_id`. No se usa fecha de secuencia ni fecha de congelamiento. El caso histórico C10 · M111 del PAD 2 tenía volumen de línea base sin movimientos posteriores y ahora muestra `15-01-2026` a `26-05-2026`.

Evidencia de navegador, viewport 1366 × 768: `before/hover_oxidos_1366x768.png`, `after/hover_oxidos_1366x768.png`, `before/hover_sulfuros_1366x768.png`, `after/hover_sulfuros_1366x768.png`. `validation.json` compara 85 filas y 13 columnas de cifras contra la consulta anterior, sin diferencias; verifica además los tres valores `y` del gráfico en ambos PAD y la presencia de las fechas.

`py_compile` y `git diff --check`: PASS. No se ejecutaron SP ni acciones de escritura. PROD, publicación, commit y push intactos.
