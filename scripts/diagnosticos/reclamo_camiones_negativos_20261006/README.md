# Reclamo: acumulado vigente de camiones en cuadratura

Alcance: DEV `VPS-5347319-X / inventar_SpcHidr`, 06-10-2026. Se cambió solo
`reclamo.v_cuadratura_modulo`: `MAX(c.m3_camiones_acum)` pasó a
`TOP (1) c.m3_camiones_acum ... ORDER BY c.fecha DESC`.

## Artefactos

- `definicion_before.sql`: definición completa leída con `sys.sql_modules` antes del cambio.
- `alter_v_cuadratura_modulo.sql`: ALTER aplicado en DEV.
- `rollback.sql`: misma definición anterior completa, con encabezado `ALTER VIEW`.
- `before.json`, `after.json`, `post_validation.json`: capturas de consultas SELECT y definición.
- `before_after.csv`: comparación de los 85 módulos para cinco indicadores.
- `validacion_negativos.sql`, `validacion_regresion.sql`: consultas para repetir validación.
- `audit_dev.py`, `prepare.py`, `apply_dev.py`, `validate_post.py`: captura, preparación,
  aplicación protegida por identidad/definición previa y validación.

## Resultado

Ver `resultado.md`. La nueva definición compila y la regresión sin negativos pasa.
La prueba funcional con correcciones negativas reales queda pendiente porque la
tabla fuente del ETL y `reclamo.camiones_reclamo` no concuerdan para los casos
del 01-02 de octubre. No se ejecutó sincronización ni reproceso.
