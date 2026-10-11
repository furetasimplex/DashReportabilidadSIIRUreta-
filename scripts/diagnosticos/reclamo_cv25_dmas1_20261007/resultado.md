# Resultado DEV

- Base: `inventar_SpcHidr` (DEV).
- `v_cv25_diario`: conservó la regla previamente aplicada de cobertura con cero
  operación. El 05-10 R2 da 0 TMS y `CERO_OPERACION_CONFIRMADO`; el 06-10
  permanece `NULL` por CV25 sin resolver.
- Última topografía vigente de módulo 80, PAD2/R2: 04-10-2026.
- `v_preliminar_cv25`: 05-10 contiene una fila de módulo 80 por 0 TMS; 06-10
  y 07-10 no contienen preliminar.
- `v_reclamo_diario`: módulo 80 tiene TOPOGRAFIA el 04-10 y PRELIMINAR_CV25
  el 05-10; ninguna fila preliminar el 06-10.
- Simulación SELECT con última topografía 05-10: solo 06-10 satisface el
  filtro D+1. El CV25 del 06-10 sigue en `NULL`, por lo que la fecha sería
  elegible, pero no se generaría tonelaje mientras siga sin resolverse.
- `calculo_diario` ya tiene una fila PRELIMINAR_CV25 el 05-10 para PAD2 al
  momento de validar. No se ejecutó ningún reproceso en esta tarea.
- El callback de Avance diario ahora consulta la fecha de topografía y la
  proyección vigente en las vistas para mostrar el límite y el cero de manera
  explícita, incluso si el rango no contiene filas materializadas.

**Estado: CV25_DMAS1_PASS**, con la salvedad del valor CV25 aún no resuelto
para 06-10. No se tocó PROD, ni hubo publicación, commit o push.
