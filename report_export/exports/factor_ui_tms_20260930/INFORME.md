# Factor camiones — presentación automático / publicado

Implementación de presentación realizada. Validación de datos y componentes aprobada;
validación visual en navegador y capturas pendientes: el acceso a Microsoft Edge
mediante Computer Use agotó dos veces el tiempo de autorización. No se simulan capturas.

## Cambio

Tres barras TMH: Chancado TMH sin ajuste, Producción de referencia, Chancado TMH
corregido automático. Dos líneas: Factor calculado y Factor aplicado. Eje de factores
0–1,05, referencia 1,0000. Marcadores discretos derivados de los datos para
MOV_CAM_POWERBI, SIN_DATOS_CAMIONES y FORZADO_1. Se conserva el indicador de respaldo.

Detalle: producción de referencia, estado cálculo automático, ajuste por límite
KOM/CAT, chancado corregido automático. Se conserva toda la trazabilidad técnica.
El campo existente Chancado_TMS_Reporte se presenta como Chancado TMS publicado [TMS]
solo en detalle y tooltip. No aparece como barra ni se crea un TMH efectivo.
El tooltip incluye fuente, evaluaciones, vueltas, nominales, producción por flota,
cargas, límites, factores, modo y regla. Los NULL se muestran como —.

No se cambiaron derivaciones existentes ni factores. La única extensión de lectura
es agregar Chancado_TMS_Reporte a la proyección SELECT de FACTOR_CAMIONES_SQL en db.py.
No cambian FROM, filtros, joins, cálculos ni objetos SQL. El valor representa la capa
de emisión; no se añadió una consulta nueva a Datos_conciliados_of.

Se actualizó el subtítulo de Parámetros para aclarar que registrar vigencias no
modifica resultados históricos hasta un reproceso.

## Casos DEV comprobados mediante lectura y componentes

| Día | Resultado |
|---|---|
| 16/09 | 1.730,18 TMH sin ajuste; 380,00 TMH automático; factor calculado 0,2196; aplicado 1,0000; FORZADO_1; 1.673,09 TMS publicado |
| 21/09 | MOV_CAM_POWERBI; 4 vueltas KOM; 1.428 TMH de referencia KOM |
| 22/09 | MOV_CAM_POWERBI; 137 vueltas KOM; 48.909 TMH de referencia KOM; factor ≈0,95881375587 |
| 02/09 | SIN_DATOS_CAMIONES; factor calculado NULL; aplicado 1 con FALLBACK explícito |
| 20/09 | SIN_DATOS_CAMIONES; factor calculado NULL; aplicado 1 con FALLBACK explícito |

Evidencia: datos.json, grafico.json y los cinco archivos de detalle diarios.
El script valida los datos, las tres barras y el contrato del componente.

## Pruebas

- Focalizadas: 35 tests y 23 subtests aprobados, tests_focalizados.txt.
- Suite unitaria ampliada: 506 aprobados, 174 subtests aprobados, 1 omitido,
  9 fallos, tests_generales.txt. Incluye monitor_pi_tum, report_export/tests,
  tests de migración factor y configuración de arranque.
- Fallos: campaña del Generador (1), calendario Excel RTO (2), PDF Torres (6,
  incluidos subcasos), estos últimos por dependencia reportlab ausente.
  Esas implementaciones no se editaron en esta tarea.
- No se ejecutaron los scripts de integración de la raíz que escriben en bases,
  publican o reprocesan: serían incompatibles con el alcance exclusivamente visual.
- git diff --check aprobado; advertencias CRLF preexistentes.
- Preview local: /_dash-layout responde HTTP 200 y contiene el nuevo campo TMS.

## Archivos

- monitor_pi_tum/db.py: un campo existente adicional en SELECT de lectura.
- monitor_pi_tum/factor_camiones_panel.py: etiquetas, tooltip, eventos, eje y detalle.
- monitor_pi_tum/limites_camiones_panel.py: subtítulo.
- monitor_pi_tum/test_factor_camiones.py: expectativas visuales.
- monitor_pi_tum/test_override_camiones.py: marcador y posiciones del tooltip.
- monitor_pi_tum/test_factor_presentacion.py: nuevo contrato visual.
- scripts/validate_factor_presentacion_dev.py: captura read-only y preview aislado.

## Revisión visual pendiente

Preview en http://127.0.0.1:8067/ con dropdown de los cinco días, los componentes
reales de detalle y el gráfico generado. No contiene registro ni publicación;
utiliza la captura local y no consulta SQL al interactuar.
Reiniciar con `venv\Scripts\python.exe -B scripts/validate_factor_presentacion_dev.py --serve`.

Propuesta opcional no implementada: una sola línea de cuatro contadores del rango
(MOV_CAM, PowerBI, sin datos y override) calculados desde Fuente_Camiones y
Modo_Aplicacion. Se omite por ahora para no sumar ruido a la leyenda de eventos.

Objetos SQL, datos, parámetros, fórmulas, consumidores y PROD sin cambios.
No reprocesos. No commit/push. No preparación de release PROD.
El ajuste previo de rendimiento de CV008 en panel.py es una tarea separada.
