# Entrega de auditoría de Reclamo

Esta carpeta contiene la extracción read-only del catálogo SQL Server, definiciones completas, muestras de julio de 2026 y análisis técnico. No se ejecutaron procedimientos almacenados ni se modificó la base.

Hay **dos fechas de extracción**. No mezclarlas:

| Qué | Fecha | Base | Servidor |
|---|---|---|---|
| CSV `01`–`15`, muestras, SP/funciones en `sql_definitions/`, `analisis/` original | 2026-09-02 | DEV `inventar_SpcHidr` | `VPS-5347319-X` |
| Vistas `reclamo.v_*`, CSV `16`/`16b`/`16c`, `analisis/vistas.md` | 2026-10-07 | PROD `inventar_SpcHidr_PROD` | `VPS-6191873-X` |

- CSV `01`–`15`: inventario, esquema, constraints, dependencias y controles (snapshot 2026-09-02).
- CSV `16`/`16b`/`16c` y `16_vistas_fuente.txt`: catálogo vivo de las 17 vistas `reclamo.*`.
- CSV `17`/`17b`–`17e`: cierre transitivo de objetos y tablas para migrar (`analisis/migracion.md`).
- `mapeo_reclamo_diario.html`: mapa filtrable (nombre, tipo, capa, dependencias, checklist local). Regenerar con `python scripts/gen_reclamo_mapeo_html.py`.
- `sql_definitions/reclamo.v_*.sql`: definición actual de cada vista (PROD, 2026-10-07). El resto de `sql_definitions/` (SP, funciones) sigue siendo el snapshot 2026-09-02.
- `raw/`: definiciones consolidadas, consultas ejecutadas y errores iniciales.
- `data_samples/`: evidencia operacional y comparación cálculo/preview/publicado.
- `analisis/`: arquitectura, flujos, hallazgos y preguntas abiertas. El catálogo de vistas actuales está en `analisis/vistas.md`.
- `sp_publicacion_bloque_reclamo.sql`: pasos 9–10b del SP de publicación.

La auditoría completa se puede repetir con `scripts/audit_reclamo_readonly.py`. El refresco de **solo vistas** es `scripts/dump_reclamo_views.py`. Ambos tienen guardia que rechaza verbos de escritura.
