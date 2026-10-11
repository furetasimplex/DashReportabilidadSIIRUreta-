# Recomendador fuera de navegación — 06-10-2026

Único runtime modificado: `lixiviacion/panel.py`, lista de tabs en `layout()`. El constructor del placeholder se conserva literalmente dentro de una rama deshabilitada que aporta una lista vacía. No se monta tab ni contenido invisible, no reserva espacio y no altera `active_tab='lix-map-tab'`.

Se actualizó solo la expectativa de tabs visibles en `test_map.py` y se agregó la nota solicitada al README principal. `RECOMENDADOR_FASE0.md` y todo `recomendador_fase0/` mantienen sus hashes. Mapa, diagnóstico, callbacks, DB, CSS y shell intactos. [Diff exacto](runtime.diff), [integridad](integrity.json).

Validación:

- `python -m pytest lixiviacion -q`: 67 PASS.
- `smoke_current_dev`: PASS, evidencia `test_evidence/smoke_current_v2_20261006T031205943669Z_16125325.json`.
- Mapa: PASS, `smoke_current_map_20261006T031211172518Z_43a6bcc4.json`.
- Módulos: PASS, `smoke_current_modules_20261006T031255002714Z_0492255d.json`.
- Regresión Diagnóstico: PASS general + siete parcelas, `regression_diagnostic_20261006T031319300712Z_ad2b71bb.json`.
- Chrome headless: PASS desktop 1440×1100 y móvil 520×950. Dos tabs exactas, mapa inicial con 60 parcelas, diagnóstico con 6120 filas, regreso a mapa, cero errores JS/callback, sin placeholder/tab fantasma ni overflow del documento. [Resultado](visual/review.json), capturas desktop/mobile de ambas pantallas en `visual/`.
- Revisión de capturas: tabs sin espacio vacío reservado; el sidebar sigue reduciendo el ancho móvil y algunos textos químicos se recortan, limitación previa fuera del alcance.
- El primer harness usaba aria-selected, no expuesto por estas tabs; se corrigió exclusivamente el harness para verificar la clase Bootstrap active. No se cambió UI por ese fallo.
- `git diff --check`: PASS; aviso preexistente LF/CRLF en layout.py, que no se editó.

Los scripts visuales históricos que esperaban tres tabs se conservaron como evidencia de su versión. El nuevo harness está aquí. Ninguna evidencia histórica fue sobrescrita. Solo lecturas DEV para validación; sin SQL funcional, DDL/DML, PROD, commit o push.
