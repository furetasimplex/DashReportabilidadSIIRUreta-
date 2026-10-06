# Riesgos y arquitectura futura

El riesgo de automatización NO es la prioridad de una parcela. La matriz clasifica BAJO para mostrar hechos; MEDIO para interpretar condiciones prolongadas con revisión; ALTO en R17 por ausencia de plan. Cualquier prescripción de variar riego/reclamo pasaría a riesgo ALTO aunque el hecho sea informativo.

Falsos positivos detallados por regla en matriz. Principales: pausas planificadas, residual normal, coexistencia de fases MIXTO, proxy Cu confundido con caudal, falta de cobertura confundida con cero, campaña hidráulica confundida con operacional, química negativa transitoria o sin flujo significativo, extremos futuros usados como «último hasta fecha», cambios tardíos reinterpretando el pasado.

## Arquitectura conceptual

```text
Función oficial / ruta temporal equivalente validada     V2 física
                         ↓                            ↓
       hechos diarios con claves y calidad separada (sin prescribir)
                         ↓
       ventanas/rachas, campaña explícita, censura/NULL
                         ↓
       reglas VERSIONADAS y aprobadas (futuro)
                         ↓
       prioridad aprobada y acción autorizada (futuro)
                         ↓
       presentación + explicación + revisión humana
```

No duplicar CASE de estados ni fórmulas de V2. El timeline actual de 12 columnas sirve para rachas de estados/flags/calidad; no contiene todos los hitos de la función de 24 campos. No prometer hitos históricos que no se consultan. Módulos únicamente bajo demanda.

| Alternativa | Evaluación |
|---|---|
| Query set-based de hechos/rachas | Preferida si consume ruta equivalente validada; verificar grano y planes. No asumir que un CTE materializa o elimina recálculo. |
| TVF nueva | Posible contrato reutilizable con parámetros, pero requeriría diseño/promoción y equivalencia futura. No crear ahora. |
| Vista | Útil para hechos físicos, menos apta para ventanas parametrizadas/as-of. Evitar cross join 60×fechas a función costosa. |
| Python | Adecuado para presentación/descriptivos/reglas versionadas; no reconstruir estados SQL. Fetch masivo por rango, no consultas por cada día/celda. |
| SQL + Python | Recomendable: hechos oficiales y V2 en SQL; políticas aprobadas/explicación y UI separadas. |

Esta auditoría ejecuta 60 consultas de rango con el SQL runtime ya validado, no 253 llamadas diarias que expanden todo el universo. Es un batch descriptivo, **no** recomendación de cargar 60 timelines síncronos al abrir la pestaña. El SQL tiene trabajo residual por expansión de CTE: el coste crece y debe medirse. La validación previa de 102 días de una parcela (~1 s) no equivale al coste de 60 parcelas y 253 días. No se optimizó de nuevo.

Fase 1 segura: primero acordar semántica, ventanas/calidad, canónicos y acciones permitidas; luego pantalla de hechos sin prioridades inventadas, con prueba de cobertura/NULL y benchmark de carga completa. Evaluar query de rango multiparcela solo en otra tarea, con comparación exacta respecto de oficial/timeline. No introducir caché ni materialización sin política de datos tardíos y vigencia.

La lectura histórica es retrospectiva con datos DEV actuales. No reproduce lo conocido en enero; no prueba causalidad ni rendimiento futuro. Definiciones comparadas al principio/final, pero no se impone snapshot transaccional a todas las tablas. Un cambio concurrente de datos puede afectar el conjunto; conservar timestamps, snapshots locales y limitación explícita.
