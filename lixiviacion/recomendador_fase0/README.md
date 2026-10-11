# Recomendador Fase 0 — auditoría y diseño, no implementación

[Informe principal](../RECOMENDADOR_FASE0.md). `arquitectura_actual.md`, `fuentes.md`, `matriz_reglas.csv`, `preguntas_negocio.md`, `propuesta_ux.md` y `riesgos.md` documentan hechos vs decisiones pendientes.

`audit.py` solo SELECT DEV: guarda definiciones, snapshot diario de 60 parcelas, timelines exactos existentes por parcela y V2. No crea motor de reglas ni objetos SQL. `design.py` genera una matriz documental. Los `.snapshot.sql` son texto capturado de OBJECT_DEFINITION, nunca ejecutado.

`hechos_historicos.csv`: conteos descriptivos no excluyentes por PAD y fuente, enero–10 septiembre 2026. `duraciones_descriptivas.csv`: estadísticas por RACHA (no ponderadas por parcela-día), percentiles con interpolación lineal, NULL si no hay rachas. `rachas_observadas.csv`: trazabilidad, campaña de cada fuente y banderas de censura en bordes del rango. Reset por cambio de campaña, hueco o predicado falso/NULL. V2 usa campaña hidráulica; OP usa operacional. Campañas NULL consecutivas se mantienen en el mismo segmento físico mientras no haya hueco.

Los percentiles NO son umbrales. Un estado observable no es una recomendación. Todos los campos de prioridad y acción de la matriz permanecen pendientes de definición de negocio. No sobrescribir esta evidencia para futuras corridas; usar carpeta fechada.
