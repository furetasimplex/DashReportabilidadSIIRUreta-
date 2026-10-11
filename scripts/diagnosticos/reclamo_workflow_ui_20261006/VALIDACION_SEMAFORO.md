# Semáforo: ubicación, alcance y unidades

La consulta de `db.semaforo` no cambió. En DEV, para el período mostrado en la captura (01–06 octubre 2026), la presentación anterior mostraba **6 módulos sin secuencia**, **23 módulos sobre 100 % sin traspaso** y **274 eventos históricos** bajo BLOQUEOS. Ahora los primeros dos siguen como BLOQUEOS y los 274 eventos se muestran bajo INFORMACIÓN / TRAZABILIDAD con etiqueta `Últimos 30 días`. Las advertencias visibles (3 estimaciones CV25, 2 días de brecha y 2 eventos de sync) siguen como REVISAR.

| Orden SQL | Control | Alcance mostrado | Unidad |
|---:|---|---|---|
| 1 | Densidad incoherente | Estado global | módulos |
| 2 | Congelados sin secuencia | Estado global | módulos |
| 3 | Más de dos abiertos | Estado global | grupos rotopala/campaña |
| 4 | Cuadratura >100 sin traspaso | Estado global | módulos |
| 5 | Ajustes aprobados sin antecedente | Estado global | ajustes |
| 6 | Horas imposibles | Estado global | registros de horas |
| 7 | Preliminar CV25 | Período seleccionado | combinaciones módulo/día |
| 8 | Brecha CV25/topografía >10 % | Período seleccionado | días |
| 9 | Ajustes propuestos | Estado global | ajustes |
| 10 | Sync omitido sin congelar | Período seleccionado | combinaciones campaña/módulo |
| 11 | Cambios tras sync | Período seleccionado | eventos |
| 12 | Historial de automatización | Últimos 30 días | eventos registrados |
| 13 | Movimiento real sin congelar | Desde fecha de corte | combinaciones campaña/módulo |
| 14 | Congelado sin línea base histórica | Estado global respecto al corte | módulos |

El control 12 **sigue devolviendo severidad `BLOQUEANTE` desde SQL**, pero se trata exclusivamente como información en la UI. No se usa para deshabilitar Publicar. El backend sigue sin bloquear por semáforo. Los alcances y unidades proceden de los `COUNT` y `WHERE` de `reclamo/db.py:317-423`.
