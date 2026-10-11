# Lixiviación — primera pantalla SIIR

Recomendador de Riegos y Drenajes permanece fuera de la navegación hasta contar con reglas de negocio aprobadas. La auditoría Fase 0 se conserva como referencia de desarrollo futuro.

**Pruebas actuales:** consultar [SMOKE_BASELINE_STRATEGY.md](SMOKE_BASELINE_STRATEGY.md). `smoke_dev.py` y `SMOKE_DEV.json` son **HISTORICAL_BASELINE**; no ejecutar ese script para salud LIVE porque escribe sobre evidencia histórica. Usar `python -m lixiviacion.smoke_current_dev` y el ejecutor `run_versioned_smoke` para nuevas verificaciones. La tabla histórica de este README permanece como evidencia, no como expected del LIVE.

## Pantalla principal actual: mapa operacional

**Fuente actual del mapa:** `fn_estado_operacional_parcela_diario(:fecha)`, 60 parcelas diarias. Detalle desde `fn_estado_operacional_modulo_diario`. Ambos oficiales fueron promovidos en DEV conservando literalmente los cuerpos TEST. La leyenda utiliza ocho fases visuales; el drawer conserva condición SQL exacta, composición, actividad, hitos y calidad. Implementación, SQL y pruebas: [ESTADO_OPERACIONAL.md](ESTADO_OPERACIONAL.md). Evidencia de promoción y rollback: [promoción DEV](promocion_estado_operacional_reanudada_20261005/README.md). Los informes anteriores quedan como evidencia histórica. Diagnóstico continúa con V2 sin cambios.

El módulo abre **Mapa operacional de pilas**; el dashboard descrito debajo se conserva en **Diagnóstico**. La tercera pestaña es **Recomendador de Riegos y Drenajes**, con mensaje «Funcionalidad en desarrollo». Auditoría de fuentes, SQL diario sin químicos, grano, colores, archivos y validaciones: [MAPA_OPERACIONAL.md](MAPA_OPERACIONAL.md). Captura: [mapa](visual_mapa/mapa.png). No se implementaron módulos, submódulos ni estados inferidos.

## Integración y archivos

Se inspeccionaron `main.py`, `layout.py`, `db_connection.py`, `env_loader.py`, `db_startup_check.py`, y patrones de `reclamo/` y `monitor_pi_tum/` antes de implementar.

La app tiene un único Dash (`main.py`) y navegación por visibilidad de secciones en `layout.py`, no Dash Pages. `dcc.Location` participa en sesión/usuario, no asigna una URL propia a cada dominio. El módulo sigue ese patrón: menú **Lixiviación**, IDs `nav-lixiviacion` y `subtabs-lixiviacion`, `href="#"`. Conserva las cuatro secciones anteriores y la autenticación global existente.

Archivos nuevos: `__init__.py`, `db.py`, `panel.py`, `callbacks.py`, `test_lixiviacion.py`, `smoke_dev.py`, este README y evidencia `SMOKE_DEV.json`. Único archivo existente modificado: `layout.py` (import, entrada sidebar, contenedor y salidas/entradas del callback de navegación).

Conexión: `db_connection.get_engine()` compartido, sin nuevas credenciales ni mecanismo de conexión. Sin conexiones en import/layout. Fuente única de negocio: `inventar_SpcHidr.vw_tablero_lixiviacion_final_v2`. No se modifican objetos SQL ni se consulta legacy. El smoke usa además `SELECT DB_NAME()` exclusivamente para verificar DEV antes de lecturas.

## Disposición visual

Título azul SIIR, subtítulo, card de filtros con fechas, PAD, campaña, parcela, estado y botón Consultar. Debajo: cuatro KPIs; flujo y química en dos columnas Bootstrap; transferencia diaria en una card de ancho completo; detalle al pie con 25 filas por página. Cards/loading/Plotly white/azul-verde y tipografía Segoe UI siguen las pantallas actuales. No se agregó CSS global ni arquitectura nueva.

Campañas y parcelas actualizan sus opciones filtrándose mutuamente y por fecha/PAD/estado, solo al estar visible la sección. Vacío significa Todos. Cambiar filtros no mezcla instantáneamente datos anteriores con detalle nuevo: Consultar aplica una selección que se guarda en Store; KPIs/gráficos y detalle usan esa selección aplicada. Un mensaje indica período y necesidad de pulsar Consultar.

Cuatro callbacks:

1. `options`: facetas, limpieza de selecciones no válidas y errores de opciones.
2. `load`: consulta aplicada, KPIs, tres gráficos, mensaje sin datos/error y Store de filtros (nunca Store de todo el detalle).
3. `table`: paginación, ordenación y filtrado backend; reinicia página al cambiar consulta aplicada/filtro de tabla y limita cada respuesta a 25 registros.
4. `delta_label`: distingue el promedio de parcelas del valor de una parcela seleccionada, sin cambiar AVG ni el tratamiento de NULL.

DataTable permite operadores =, !=, >=, <=, >, <, eq/ne/ge/le/gt/lt, contains y datestartswith, combinados con &&. No implementa OR ni una gramática arbitraria: un filtro no soportado produce aviso. Columnas/orden están en lista permitida; valores se parametrizan. Los filtros de tabla afectan solo al detalle, tal como indica la pantalla.

## Consultas

El SQL ejecutable completo está en `db.py`. No usa SELECT *. WHERE común:

```sql
WHERE fecha BETWEEN :desde AND :hasta
-- opcionales según selección:
AND pad_id = :pad
AND campana_id = :campana
AND parcela_id = :parcela
AND estado_asignacion = :estado
```

KPIs:

```sql
SELECT COUNT_BIG(*) AS registros,
       SUM(flujo_m3_d) AS flujo,
       SUM(transferencia_cu_t_d) AS transferencia,
       AVG(delta_cu_gl) AS delta,
       COUNT_BIG(CASE WHEN estado_asignacion='FUERA_VENTANA_RIEGO' THEN 1 END) AS fuera
FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
WHERE fecha BETWEEN :desde AND :hasta -- más filtros parametrizados
```

Series:

```sql
SELECT fecha,pad_id,SUM(flujo_m3_d) AS flujo,
       AVG(cu_drenaje_gl) AS drenaje,AVG(cu_refino_gl) AS refino,
       SUM(transferencia_cu_t_d) AS transferencia
FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
WHERE fecha BETWEEN :desde AND :hasta -- más filtros parametrizados
GROUP BY fecha,pad_id ORDER BY fecha,pad_id
```

Opciones: SELECT DISTINCT de identidades/descriptores de campaña o parcela sobre V2, con rango y facetas. DISTINCT solo genera opciones, no deduplica hechos. Tabla: proyección explícita de las diez columnas requeridas, COUNT_BIG para paginación y ORDER BY validado más `OFFSET :offset ROWS FETCH NEXT :size ROWS ONLY`.

No se calculan fecha operacional, ventana, campaña, delta, transferencias ni deduplicación en Python. La suma por fecha de transferencia agregada por PAD es únicamente presentación. AVG químico SQL ignora NULL; para una sola parcela se presenta su señal diaria (grano ya garantizado en el horizonte validado). No se corrige la anomalía de 2018: no se deduplican sus datos.

NULL nunca se rellena con cero. KPI all-NULL muestra Sin dato, gráficos conservan huecos y la tabla celdas vacías. Suma visual de un día completamente NULL permanece NULL. Cero real se presenta como cero. Los Decimal se convierten a float únicamente al serializar puntos/celdas, no para cambiar cálculos SQL.

## Pruebas y smoke DEV 01/06/2026–10/09/2026

Pruebas locales: `python -m pytest lixiviacion/test_lixiviacion.py -q`: **7 PASS** (NULL/cero, transferencia conservada, etiquetas químicas, fechas iniciales, parametrización/inyección, respuesta vacía/error, paginación backend, registro Dash y navegación anterior/nueva).

Revisión visual: `python -m lixiviacion.visual_review`, aplicación real en localhost con Chrome headless y sesión de prueba Flask en memoria. No modifica autenticación ni crea usuarios. Chequeo de bases peer desactivado solo en ese proceso; conexiones de lectura DEV. Capturas y resultados en `visual/`. El servidor de prueba se cierra al terminar.

Smoke: `python -m lixiviacion.smoke_dev`, lectura restringida a DEV `inventar_SpcHidr`, usando infraestructura existente. El primer intento dentro del sandbox falló por ODBC/TLS; reintento fuera del sandbox autorizado obtuvo los resultados guardados en `SMOKE_DEV.json`.

| Selección | Filas | Flujo SQL exacto m³ | Transferencia t Cu |
|---|---:|---:|---:|
| OX | 3264 | 2908120.161887395403000 | 6801.723817085 |
| SULF | 2856 | 9260436.238434241623000 | 23334.497994245 |
| Total | 6120 | 12168556.400321637026000 | 30136.221811330 |

**Smoke PASS exacto para OX, SULF y total.** La referencia fue actualizada con los valores exactos aprobados por el usuario; diferencias de filas, flujo y transferencia = 0. El total SQL redondeado a 6 decimales es **12168556.400322**. La discrepancia anterior correspondía exclusivamente al orden de redondeo. No se modificó SQL ni se suman subtotales previamente redondeados: la UI conserva SUM(flujo_m3_d) y AVG químico ignorando NULL.

Sin commit/push, cambios SQL, escrituras de datos, borrado de TEST ni cambios en otras pantallas fuera de integración del menú.
