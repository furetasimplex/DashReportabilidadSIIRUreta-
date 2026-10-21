# Optimizaci?n de Ejecutar c?lculo ? 21 octubre 2026

Validaci?n real con Playwright, login habitual, Caso 10013 / run oficial 10104, 1?12 octubre 2026. Se realizaron una corrida instrumentada previa y una posterior al cambio, por el bot?n normal (incluido su guardado habitual).

| Medici?n | Antes | Despu?s |
|---|---:|---:|
| Callback de c?lculo | 44,259 s | 5,387 s |
| Guardado completo | 42,148 s | 3,563 s |
| Inserci?n 432 filas diarias | 37,448 s | 1,548 s |
| Inserci?n 36 filas resumen | 2,977 s | 0,316 s |
| Resoluci?n matem?tica | 0,792 s | 0,569 s |
| Bot?n habilitado desde click | 44,400 s | 5,491 s |
| Indicador C?lculo listo desde click | 45,188 s | 6,197 s |

El cuello era el executemany del driver en el motor compartido sin fast_executemany: generaba numerosos viajes a SQL Server. Se reemplazaron solamente los dos INSERT de detalle de save_run por multi-VALUES parametrizado, m?ximo 2000 par?metros / 1000 filas. Para esta corrida: un bloque resumen y tres diarios (200+200+32). La cabecera OUTPUT INSERTED.id, reemplazo por caso/ventana/m?todo, commit y valores se conservan. Otros motores conservan executemany. La estrategia se aplica a todos los casos, sin ID codificado.

La metodolog?a, restricciones, rampa y resultados matem?ticos no cambiaron. Hash de KPIs, mensajes y grilla visible id?ntico antes/despu?s; no hubo modal de error. No es una comparaci?n num?rica exhaustiva de todas las curvas de todos los casos. La prueba us? datos cacheados del caso en ambos recorridos; una carga fr?a o distinta latencia de SQL puede variar los tiempos.

Validaci?n: 131 pruebas existentes aprobadas, m?s 6 nuevas en curvas_recon/test_write_batching.py. Pruebas aisladas de l?mites, valores nulos/Unicode/fechas, rollback y propagaci?n de fallo. Registro local de tiempos en auditorias/curvas_recon_performance.jsonl (ignorado por git); solo metadatos de fases, sin SQL, credenciales ni valores de filas. Instrumentaci?n en perf_trace.py, callback y engine.

Archivos activos: curvas_recon/db_pipeline.py (helper _insert_rows_batched, save_run), pad_dashboard.py, recon_engine.py, perf_trace.py, test_write_batching.py. No se hicieron commit ni push. Artefactos de medici?n baseline.json y after.json en el workspace de curvas_recon/optimizacion_calcular_20261021.
