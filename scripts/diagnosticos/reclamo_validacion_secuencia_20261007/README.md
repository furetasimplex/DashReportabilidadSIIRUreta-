# Validación de secuencia aplicable — DEV

El control 2 de `reclamo.db.semaforo` contaba antes todos los módulos
`CONGELADO` sin fila en `secuencia_rotopala`. El criterio vigente de
`sp_auto_mantener_secuencia` y `sp_definir_secuencia` requiere además
evidencia positiva en `inventar_SpcHidr.control_reclamo_diario` **o**
pertenecer a los cinco módulos posteriores al frente topográfico de la misma
campaña/PAD. Movimiento de camiones solo no satisface ese criterio.

- `definicion_before.sql`: control anterior y definiciones SP vigentes leídas
  de DEV.
- `auditoria_elegibilidad.sql`: clasificación por módulo, solo SELECT.
- `alter_validacion.sql`: predicado de reemplazo del control 2, solo SELECT.
- `rollback.sql`: predicado anterior; el cambio vive solo en Python, no hubo
  DDL.
- `before_after.csv`: detalle de los cinco módulos y su clasificación.
- `snapshot_before.json`: conteos y sumas de control para comparar invariantes.
- `resultado.md`: conclusión.

`audit_readonly.py` y `validate_readonly.py` solo ejecutan SELECT en DEV.
