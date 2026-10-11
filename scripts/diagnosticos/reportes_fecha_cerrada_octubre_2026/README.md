# Auditoría fecha cerrada — Reportabilidad, DEV

Informe: REPORTES_FECHA_CERRADA_OCTUBRE_2026.md. Solo SELECT, sin ejecutar callbacks de editor/exportación porque refrescan/materializan datos. `audit.py` extrae el SQL literal desde AST, consulta DEV, guarda definiciones y cobertura. `document.py` calcula metadata/documentación local y ejecuta aislado el selector puro de fechas.

consulta_fecha_cerrada.sql usa parámetros SQLAlchemy :start/:end, instancias reales en parametros.json. queries.json conserva todas las consultas. Cobertura septiembre describe solo las fuentes de cierre; no certifica química/física/apilado. Ceros de rangos futuros no se consideran días operacionales cerrados. No se ejecutó SQL de archivos snapshot; son evidencia.
