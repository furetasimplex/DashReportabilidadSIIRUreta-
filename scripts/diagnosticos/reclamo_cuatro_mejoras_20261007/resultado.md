# Cuatro mejoras de Control de Reclamo — DEV

## Cambios

1. `reclamo.v_diferencia_cv25`: `tms_topografia` queda `NULL` si no existe
   ninguna fila `TOPOGRAFIA`; diferencia y porcentaje también quedan `NULL`.
   Se conserva el flag `SIN_TOPOGRAFIA_SOLO_PRELIMINAR`. Definición previa,
   ALTER y rollback están en esta carpeta. Los datos crudos no cambiaron.
2. `cb_resumen_general` reutiliza `_sin_dato_aplicable` y
   `db.ventanas_secuencia`, igual que Avance diario. La nota de brecha
   acumulada compara solo fechas con CV25 y topografía real.
3. `cb_preview_conciliados` conserva una fila `PRELIMINAR_CV25` de 0 TMS como
   contexto cuando no hay candidato con movimiento positivo. La selección
   existente por avance y el piso de secuencia siguen aplicando.
4. `_rango_inicial` ya estaba implementado: fecha Chile hasta D−1, con mes
   anterior completo el día 1. No hubo nuevo cambio para este punto.

## Verificación 01–06-10-2026

- 04-10: topografía real y brecha normal; Vista previa sigue con origen
  Topografía real.
- 05-10: CV25 crudo 18 TMS, preliminar 0 TMS, topografía y ambas diferencias
  `NULL`, flag `SIN_TOPOGRAFIA_SOLO_PRELIMINAR`.
- PAD2: 43 filas `SIN_DATO` del universo, 0 combinaciones módulo/día
  operacionalmente aplicables sin respaldo. PAD1: 0 y 0.
- Vista previa PAD2 05-10: Campaña 11, M16, Rotopala 0 TMS, avance 7,8 %,
  origen Estimación CV25.
- Rango predeterminado con hoy 07-10: 01-10 → 06-10; con 01-11:
  01-10 → 31-10.

`validate_readonly.py` consulta DEV y ejercita callbacks sin DML ni SP.
No hubo reproceso, publicación, PROD, commit ni push.
