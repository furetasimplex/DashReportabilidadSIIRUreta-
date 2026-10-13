# Prueba real de dos Casos — 12/10/2026

Se usó el catálogo oficial compartido con Curvas y la conexión anfitriona, con un guard SQLAlchemy que solo permite SELECT/WITH. No se ejecutó main.py ni ningún SP, ajuste o publicación.

| Caso | Run oficial solver | Período | Días con masa publicada elegible | Resultado |
|---|---:|---|---:|---|
| 8 — Caso hidrometalurgia | 47 | 22–31/08/2026 | 0 | Sin masa publicada |
| 7 — Semana 3 agosto | 50 | 15–21/08/2026 | 0 | Sin masa publicada |

La verificación de publicaciones usa `Datos_conciliados_of_ver`, el ID del Caso seleccionado, su período, `origen = AJUSTE_REPORTE` y el estado validado según la política histórica del módulo. Ambos Casos existen y tienen corrida oficial del solver, pero no cuentan con filas de masa elegibles para la reconstitución. El motor real lanza ValueError y el callback de carga entrega token vacío y mensaje de fallo, sin reutilizar masa de otro Caso.

No se pudieron comprobar balances, renderizar gráficos ni contrastar el aislamiento de dos resultados reales. No debe interpretarse este resultado como dos cálculos completos aprobados. Las pruebas offline de aislamiento con dos Casos sintéticos pasaron en la validación anterior de 63 tests.

Para completar la prueba hace falta revisar o generar mediante el flujo autorizado de reportabilidad la publicación de masa de esos Casos, o definir un vínculo documentado con publicaciones existentes. Esta prueba no crea ese vínculo por coincidencia de fechas o IDs de catálogos distintos y no publica datos automáticamente.

Evidencia: `resultado.json`. El número de consultas incluye lecturas de catálogo, preflight, motor y callback real repetido para verificar el manejo del error; no es una medición de una sola carga en la interfaz.
