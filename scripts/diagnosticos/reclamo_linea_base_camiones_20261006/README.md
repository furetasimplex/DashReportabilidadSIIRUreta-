# Auditoría de línea base de camiones — DEV

Captura de solo lectura tomada el 07-10-2026 en
`VPS-5347319-X / inventar_SpcHidr`. No se ejecutaron SP ni DML/DDL.

## Archivos

- `diagnostico_linea_base.sql`: consultas SELECT reproducibles.
- `def_sp_establecer_linea_base.sql`, `def_sp_auto_congelar_modulos_nuevos.sql`:
  definiciones vigentes de DEV.
- `detalle_m17_m23.csv`: deltas, acumulados fuente/sistema y desfase por fecha.
- `campania10_auditoria.csv`: 26 módulos, línea base real y esperada, totales
  y comparación con fuente alineada por fecha.
- `cronologia_congelamiento.csv`: logs de M17/M23 vinculados a ejecuciones.
- `snapshot.json`: evidencia cruda y metadatos de las consultas SELECT.
- `sql_verification.json`: confirmación independiente por SQL de los 26
  previos almacenados frente a la expresión del SP.
- `resultado.md`: conclusión, causas y límites de evidencia.
- `audit_readonly.py`, `analyze_snapshot.py`, `verify_sql_readonly.py`:
  generación y verificación de la evidencia.

El corte vigente es 01-07-2026. Las diferencias entre acumulados después de
ese corte no deben añadirse a `m3_camiones_previo`: esa columna representa
exclusivamente el período anterior al corte.
