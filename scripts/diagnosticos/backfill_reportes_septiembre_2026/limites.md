# Límites y bloques

No se encontró un máximo de días de rango en los coordinadores vigentes ni en los SP
LIVE de su cadena. Se validan fechas presentes y ordenadas. Los parámetros 7 y 15 no
son límites de exportación: seleccionan la ventana de recálculo de apilado existente.

| Reporte | Ventana runtime | Bloques elegidos |
|---|---:|---|
| Representatividad | 7 | 01–07, 08–14, 15–21, 22–28, 29–30 septiembre |
| Análisis TM | 7 | 01–07, 08–14, 15–21, 22–28, 29–30 septiembre |
| Datos Conciliados | 15 | 01–15, 16–30 septiembre |

Son 12 invocaciones de coordinadores (no 12 EXEC SQL: cada coordinador ejecuta su cadena).
Cada bloque está completamente dentro de la ventana runtime y por tanto refresca todas
sus fechas existentes. No se cambia ningún parámetro permanente.

Histórico y Factor reciben 0 como ya hace el runtime: evita extender hacia atrás el
rango. El fin del cache es exclusivo; `2026-10-01` delimita septiembre y no materializa
octubre. El resumen totalizador lee un colchón de ticks externos al rango pero su MERGE
usa solamente `fecha_turno BETWEEN @FechaInicio AND @FechaFin`.

La evidencia de cierre de Torres llega al 30-09; PI/TUM llega al 04-10. Se conserva
`min(fin solicitado, corte)` y nunca se extiende la solicitud a octubre.
