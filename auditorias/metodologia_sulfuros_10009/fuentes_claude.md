# Fuentes halladas en logs de Claude

Revisión de metadatos y fragmentos pertinentes de la sesión Claude más reciente para `curvas_recon`, con fecha 2026-11-03. Sesión principal: `C:\Users\5330\.claude\projects\C--Users-5330-Desktop-HidroNueva-curvas-recon\b1433e7a-3542-4aa5-b7d0-e83a3ecf72a9.jsonl` (último evento 13:07 UTC). Resúmenes/hallazgos de subagentes en la carpeta homónima `subagents\`; los más directos son `agent-a553a9419e4b77208.jsonl` (mapa de fuentes, 03-nov) y `agent-acbf8df58304fde2f.jsonl` (regla de ancla del primer riego). La carpeta de proyecto `DashReportabilidadSIIR` tiene sesiones de junio/julio; son antecedentes más antiguos.

## Fuentes de datos documentadas

| Fuente | Papel que los logs le atribuyen | Alcance / evidencia |
|---|---|---|
| `riego_diario` | Caudal de riego por pila (`caudal_m3h`) | Loader `load_riego`; diario, pivot fecha × pila. El sync registrado toma `parcela_id`, `fecha`, `caudal_m3h` desde `vw_riego_diario_ingest`. |
| `cu_riego_diario` | Cu del refino de riego por material | Loader `load_cu_riego`; serie por material. |
| `drena_cu_diario` | Cu del drenaje / PLS por pila | Loader `load_drena_cu`; diario, pivot fecha × pila. |
| `lectura_recuperacion` | Curva observada por pila | Columna `valor_pct`, vía `pad_data.load_oxido/_sulfuro`. El loader SQL limita la ventana solicitada. |
| `campana_parcela_control` | Fechas, edad y Cu apilado por pila; filas/granularidad por módulo | Nota de metodología del propio proyecto: Cu fino agregado desde módulos como `tms * ley / 100`; `cu_tf` es ley, no tonelaje. Los logs revisados no dan un nombre confirmado de columna de primer riego ni prueban el esquema físico completo. |
| `recon_caso`, `recon_caso_oficial`, `recon_solver_run`, `recon_resultado_flujo` | Definición/corrida oficial y objetivos del PAD | En `db_pipeline.py` se registra unión `recon_caso` → `recon_caso_oficial` por `caso_id`, y esta a `recon_solver_run` por `solver_run_id`; flujos oficiales salen de `recon_resultado_flujo`. |
| `reconciliacion_run`, `reconciliacion_detalle`, `reconciliacion_detalle_dia` | Resultados guardados (salida) | Enumerados como destinos/resultados guardados, no fuentes primarias. |

El material offline del motor ancla el día de ciclo al primer día con riego real; especifica que no se usa la fecha de la curva de `lectura_recuperacion` como inicio de rampa. Es evidencia de lógica del motor registrada en un agente, no de que exista una columna SQL específica para `primer_riego`.

## Artefactos y límites

Los logs citan el código `curvas_recon/db_pipeline.py`, `pad_data.py`, `recon_engine.py` y el caché local `datos_reconciliados.sqlite` usado en una exploración anterior/offline. También registran harnesses y resultados de trabajo anteriores bajo `curvas_recon/auditorias/ppt_curvas_simplex_20261028/` (incluyendo carpetas `build/datos_v30` y `build/datos_v31`, y artefactos CSV/JSON para casos 10009/10013). Son rastros de exploraciones previas, no prueba de que representen la ingesta actual de 1–7 sep 2026.

El resumen de fuentes del 03-nov indica que `load_rec_curves` era un stub sin datos y que ese método no usaba su consumidor; por ello no asumir que toda recuperación sale de ese loader. Los logs revisados no contienen una consulta de catálogo que confirme columnas físicas de `campana_parcela_control`, ni una extracción actual completa que certifique disponibilidad de todas las series de 1–7 sep. Ningún secreto, cadena de conexión, `.env` ni dato ajeno se copió a este apunte.

Esta auditoría solo identifica fuentes y evidencia documental de logs. No adopta las metodologías alternativas, edades de corte, anclas ni objetivos de aquellas exploraciones. Para este trabajo rigen las instrucciones vigentes del usuario: jóvenes SU <30 días desde primer riego, cohorte independiente diaria de curva y requisitos de drenaje/concentraciones; pilas >30 días solo medición; mes anterior oficial congelado; PAD neto como objetivo. El intervalo objetivo es caso 10009, 1–7 septiembre 2026.
