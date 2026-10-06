# Segunda pasada UX/UI de Reclamo

Archivos funcionales: `reclamo/panel.py` y únicamente consultas `SELECT` de `reclamo/db.py`. No se tocaron SP, reglas, backfill, publicación ni datos.

- Campaña operacional obtenida de `disponible_rotopalas` en cuadratura, cálculo diario, preview, ajustes, módulos y alertas. El `campana_id` sigue en el backend.
- Selectores de campaña, módulo, editor y ajustes con números operacionales; sin IDs visibles.
- Matriz por `(campana_id, campana, modulo_id, modulo_numero)`, con Campaña y Módulo visibles; rango que cruza mes usa día-mes en las columnas.
- Cuadratura y remanente identifican campaña+módulo; encabezados de cliente y estados traducidos.
- Historial de automatización con campaña operacional y fecha local; el contador histórico queda claramente separado de problemas activos.
- Tabla de datos base reducida a ocho campos principales; el Store y los formularios avanzados conservan los datos técnicos.
- Tablas sin controles nativos de filtro/selección de columnas en inglés. Números con separadores chilenos y fechas `DD-MM-AAAA`; densidad con cuatro decimales.
- Gráfico de rendimiento con gap cuando no existe una fila de topografía real. La consulta de existencia es read-only y no modifica la tasa SQL.
- Fecha de ajuste explicada como independiente del período consultado; publicación intacta.

Las reglas de semáforo, CV25, secuencia y publicación permanecen vigentes. La observación de brechas porcentuales extremas queda en `AUDITORIA_FILLNA.md`.
