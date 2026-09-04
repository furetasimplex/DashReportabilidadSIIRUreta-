# Entrega de auditoría de Reclamo

Esta carpeta contiene la extracción read-only del catálogo SQL Server, definiciones completas, muestras de julio de 2026 y análisis técnico. No se ejecutaron procedimientos almacenados ni se modificó la base.

- CSV `01`–`15`: inventario, esquema, constraints, dependencias y controles.
- `sql_definitions/`: una definición completa por objeto activo/relevante.
- `raw/`: definiciones consolidadas, consultas ejecutadas y errores iniciales.
- `data_samples/`: evidencia operacional y comparación cálculo/preview/publicado.
- `analisis/`: arquitectura, flujos, hallazgos y preguntas abiertas.
- `sp_publicacion_bloque_reclamo.sql`: pasos 9–10b del SP de publicación.

La extracción puede repetirse con `scripts/audit_reclamo_readonly.py`. El script contiene una guardia que rechaza verbos de escritura.
