# Evidencia segunda pasada de nomenclatura Reclamo

`AUDITORIA_CAMPANAS.md`: fuente canónica y componentes. `AUDITORIA_IDS_VISIBLES.md`: columnas y controles técnicos. `AUDITORIA_FILLNA.md`: NULL/0, CV25 extremo y rendimiento. `CAMBIOS.md`: alcance. `INVARIANTES.md`: contrato y pendientes. `mapping.json`, `reads.json` y `tests.json`: resultados reproducibles. `before/` y `after/`: capturas a 1366 y 1920 px; `after/` también incluye móvil y editor expandido.

Los scripts `audit_mapping.py` y `validate_reads.py` solo ejecutan consultas SELECT en DEV. `test_ux.py` usa fixtures y mocks; no llama procedimientos.
