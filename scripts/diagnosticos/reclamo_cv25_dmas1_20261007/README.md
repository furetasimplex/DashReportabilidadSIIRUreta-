# CV25 D+1 en DEV

`definiciones_before.sql` conserva las tres vistas auditadas antes del cambio.
`alter_v_preliminar_cv25.sql` contiene la única modificación SQL aplicada: la
fecha preliminar debe ser exactamente la última topografía vigente + 1 día.
`alter_v_cv25_diario.sql` documenta la definición que ya estaba desplegada al
iniciar esta tarea; no se volvió a ejecutar. `rollback.sql` restaura solo la
vista preliminar al estado inicial de esta tarea. `validacion_dmas1.sql` es de
solo lectura. `before_after.csv` y `resultado.md` resumen la verificación.

`apply_dev.py` comprueba base, definición inicial y regla de cero confirmado
antes del `ALTER VIEW`. `validate_dev.py` ejecuta únicamente SELECT.

No se ejecutó SP ni se reprocesaron datos crudos.
