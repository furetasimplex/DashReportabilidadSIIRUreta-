# UX propuesta — no implementada

Mantener la pestaña existente por navegación; título conceptual recomendado: **Situaciones a revisar**. Es más neutral que «Alertas operacionales», que puede sugerir que el hecho ya es anómalo. No cambiar el nombre runtime en Fase 0.

Tabla propuesta: Fecha | PAD/Parcela | Situación observada | Duración observada | Campaña operacional | Campaña hidráulica | Motivo/fuente | Calidad/cobertura | Prioridad | Acción sugerida.

- Prioridad sin regla aprobada: **Pendiente de regla**.
- Acción sin regla aprobada: **Requiere validación operacional**. Es un estado de revisión humana, no una prescripción de modificar la parcela.
- Mostrar racha «al menos X días observados» si empieza al borde de ventana; no inventar inicio real.
- NULL: Sin dato, nunca cero. Sin coincidencia V2: sin cobertura V2, no transferencia cero.
- Separar falta de información, contexto de asignación y condición operacional. No semáforo rojo por MIXTO/FUERA_VENTANA_RIEGO/negativo automáticamente.
- Mostrar fuente, fecha consultada, definición/regla/versionado cuando exista. Drill-down a detalle diario y, solo para explicar MIXTO, módulos reales; no repetir medidas físicas por módulo.
- Orden inicial por PAD/parcela/fecha o filtro elegido, no ranking económico/operativo inventado. Filtros conceptuales por hecho, calidad, PAD/parcela y período. N temporal pendiente de acuerdo.

Opciones de prioridad futura:

| Opción | Ventaja | Riesgo / requisito |
|---|---|---|
| Flags independientes | Preserva varios hechos, transparente; adecuada primera fase informativa. | No determina qué atender primero. |
| Prioridad categórica por regla | Explicable y auditable. | Negocio debe aprobar severidad, excepciones y conflicto de reglas. |
| Jerarquía de severidad | Orden determinista y simple. | Puede ocultar calidad o situaciones simultáneas; requiere precedencia aprobada. |
| Scoring ponderado | Combina duración, magnitud, calidad y etapa. | Pesos/normalización inventados crean falsa precisión; no recomendable antes de casos etiquetados y aprobación. |

Duración, calidad, delta/transferencia, actividad, estado, campaña y tiempo desde hito son candidatos a contexto de prioridad, no pesos aprobados. No interpretar transferencia negativa como pérdida recuperable cuantificada para ordenar económicamente.
