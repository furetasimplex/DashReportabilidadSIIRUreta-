# Mapa operacional de pilas — auditoría e implementación DEV

Fecha: 2026-10-05. Se leyó el requerimiento adjunto y se trataron las cinco imágenes solo como referencia de geometría. Auditoría comunicada antes de implementar. Consultas DEV exclusivamente SELECT; no se modificaron objetos ni datos SQL. Los snapshots locales citados no se presentan como estado actual de PROD.

## A–H. Fuentes, grano y riesgo

| Uso | Fuente / evidencia | Grano / columnas relevantes | Decisión y riesgo |
|---|---|---|---|
| A. PAD/parcela | `inventar_SpcHidr.parcela`, metadatos y catálogo DEV; uso existente en `reclamo/db.py:catalogo_modulos` | `id_parcela`, `id_pad`, `numero`, `nombre`; 32 OX (1–32), 28 SULF (1–28). Cero duplicados PAD/número en DEV | Catálogo completo separado de medidas; preserva parcelas sin registro diario |
| B. Campaña | `vw_tablero_lixiviacion_final_v2`, contrato y metadatos DEV | PAD + parcela + fecha; campaña nullable, fechas hidráulicas/operación/drenaje | Usar sin recalcular ventanas ni unir CPC |
| C. Módulo | `modulo` usado por `reclamo/db.py:catalogo_modulos`; `campana_parcela_control` y `mapa_campana_modulo_parcela` | CPC incluye campaña/PAD/parcela/módulo, fechas y `estado_ciclo`; mapa incluye `id_mapa`, campaña/PAD/parcela/módulo, fechas carguío/reclamo/ciclo y `estado_modulo` | Hay identidades reales de módulo; no se validó composición ni estado diario único para esta pantalla. No incorporar todavía |
| D. Submódulo | Sin fuente validada hallada en búsquedas de SQL/Python | No se acreditó identidad, vigencia ni relación con parcela | Omitir selector y subdivisiones artificiales |
| E. Estado diario | V2 `estado_asignacion` | `CAMPANA_HIDRAULICA`, `FUERA_VENTANA_RIEGO` | Representar asignación; no inferir riego, reposo, humectación, detención ni abandono |
| F. Otras fuentes examinadas | `modulos_turnos` en `tabs/tab3.py`; `control_apilado_diario` en `tabs/tab_import_apilado.py` y snapshots de SP | Turnos: fecha/turno/PAD/campaña/parcela/módulo; apilado: id, fecha, PAD/campaña/módulo y volúmenes. Unicidad no acreditada para el mapa | No son un catálogo validado de estados hidráulicos diarios; no se consultan sus analitos ni se incorporan |
| G. Unión propuesta/implementada | Catálogo y V2, dos SELECT separados | En memoria por `(pad_id, parcela_id)`, V2 restringido a una sola fecha | Relación 1:0/1. Validación de identidad, número y fecha. No hay join de módulos |
| H. Multiplicación | CPC/mapa pueden contener varios módulos/campañas por parcela | Join por parcela contra todos sus módulos/historia sería 1:N | No se ejecuta. Duplicados V2 provocan error y limpieza del mapa, nunca SUM/DISTINCT/selección arbitraria |

La definición DEV de `vw_flujos_reales_sulfuro_long` enumera parcelas 01–28 y resuelve identidades con `parcela` por PAD/número, consistente con catálogo. No se extrae histórico de flujo para construir catálogo.

### Estados de otros objetos: existen, pero no son equivalencias aprobadas

Consulta DEV de valores existentes en CPC: `operacion` (15), `sin_dato` (1), `carguio` (1), `reclamo` (115), `drenaje` (799), `reposo` (49).

Mapa campaña/módulo: `APILADO_SIN_RECLAMO` (160), `historico_apilado` (686), `en_ciclo` (18), `SIN_CLASIFICAR` (2), `CICLO_CERRADO` (12), `reclamado` (100).

Esto demuestra existencia, no vigencia diaria ni equivalencia con la maqueta. El snapshot histórico `docs/ad_hoc/campana_parcela_control/definiciones_bd.sql`, alrededor de líneas 311–324, calcula `estado_ciclo` por presencia de fechas con un CASE, sin fecha de consulta del mapa. Se requiere validar la regla temporal antes de reutilizarlo para una fotografía histórica. No se reprodujo ese CASE en Python.

Referencias inspeccionadas adicionales: `docs/diagnosticos/tablero_lixiviacion_v2_package/01_create_v2_candidate.sql` (candidato histórico, no verdad live), `lixiviacion/db.py` (consumo V2), `auditoria_reclamo/sql_definitions/inventar_SpcHidr.sp_calcular_datos_conciliados.sql` (snapshot), `layout.py` (navegación).

## I–J. Referencia visual y límites

Implementado: dos superficies gris oscuro, una celda por parcela, OX P1–P16 arriba/P32–P17 abajo; SULF P1–P14 arriba/P28–P15 abajo, ordenadas desde el catálogo. La geometría es esquemática, no coordenadas georreferenciadas. Fecha única y filtro PAD, leyenda inferior, detalle al clic, scroll horizontal cuando el ancho disponible es insuficiente.

Omitido: analitos, escalas continuas, módulos/submódulos, marcadores P/R y símbolos sin definición, estados operacionales no validados y algoritmos de recomendación.

## Navegación

1. **Mapa operacional de pilas**, seleccionado inicialmente, fecha inicial 10-09-2026 (horizonte ya validado, no una afirmación de dato actual).
2. **Recomendador de Riegos y Drenajes**: únicamente «Funcionalidad en desarrollo».
3. **Diagnóstico**: dashboard anterior conservado. Sus consultas AVG/SUM y resultados no se cambian. Sus opciones solo se consultan con esta pestaña activa; el mapa no consulta columnas químicas.

## SQL utilizado por el mapa

```sql
SELECT id_pad AS pad_id, id_parcela AS parcela_id, numero AS nro_parcela_pad
FROM inventar_SpcHidr.parcela
WHERE id_pad IN (1,2)
ORDER BY id_pad,numero;

SELECT pad_id,parcela_id,nro_parcela_pad,fecha,campana_id,numero_campana,
       fecha_primer_riego,fecha_ultimo_riego,fecha_limite_hidraulica,
       fecha_ini_operacion,fecha_fin_operacion,fecha_ini_drenaje,fecha_fin_drenaje,
       estado_asignacion,flujo_m3_h,flujo_m3_d
FROM inventar_SpcHidr.vw_tablero_lixiviacion_final_v2
WHERE fecha = :fecha
-- AND pad_id = :pad  (solo si se selecciona PAD)
```

SQLAlchemy `text`, parámetros enlazados y `db_connection.get_engine()` mediante `_connection` existente. Sin SELECT *, consultas del histórico, nuevas conexiones configuradas, DDL ni DML. El catálogo se filtra por PAD en memoria. Las consultas de auditoría fueron `sys.objects/sys.columns/sys.types`, `OBJECT_DEFINITION` de flujo SULF, conteo/duplicados de catálogo y conteos por estado de CPC/mapa. No se leyeron valores químicos para construir el mapa.

## Renderizado, detalle y colores

1. Obtener catálogo y fotografía.
2. Rechazar duplicados, fecha distinta, parcela ajena al catálogo, numeración contradictoria o código de estado no soportado.
3. Conservar cada parcela una vez; ausencia diaria deja campos NULL y `con_registro=False`.
4. Ordenar por PAD/número, dividir en dos mitades y revertir la fila inferior. Una celda representa toda la parcela, sin repartir flujo.
5. Clic resuelve la misma fila del Store diario. Cambio de fecha/PAD/pestaña o actualización de fotografía cierra el detalle anterior.

| Código | Etiqueta | Color |
|---|---|---|
| CAMPANA_HIDRAULICA | Campaña hidráulica | Azul sobrio `#5485a1` |
| FUERA_VENTANA_RIEGO | Fuera ventana de riego | Ocre `#c78542` |
| NULL / sin registro | Sin información | Gris oscuro `#303638` |

Campaña hidráulica no equivale a «En riego». Flujo NULL muestra «Sin dato» y cero muestra `0,000`. Código original y fechas se conservan en detalle. No se muestran químicos en mapa, tooltip ni modal.

## Validación

- `python -m pytest lixiviacion -q`: 12 PASS. Cobertura de cardinalidad, orden físico, duplicados, fecha, ausencia/0, proyección diaria sin químicos, callbacks inactivos y regresión de Diagnóstico.
- `python -m lixiviacion.smoke_map_dev`: PASS. 10 y 11/09/2026: 60 parcelas únicas, 37 con campaña hidráulica y 23 fuera de ventana. PAD filtrado: 32/28. 01/01/2099: cero registros, 60 parcelas conservadas con NULL, sin escribir datos.
- `python -m lixiviacion.visual_review`: servidor local temporal conectado solo a DEV, sesión de pruebas en memoria; mapa, clic, filtro SULF, cambio de fecha, recomendador y Diagnóstico. Evidencia en `visual_mapa/`.
- `git diff --check`: sin errores. El mapa y scripts son archivos nuevos no versionados; no se realizó staging ni commit.

## Archivos y diff resumido

Nuevos: `lixiviacion/map_db.py`, `map_panel.py`, `test_map.py`, `smoke_map_dev.py`, `SMOKE_MAP_DEV.json`, este informe, `assets/lixiviacion_map.css`, evidencia `lixiviacion/visual_mapa/`.

Modificados en esta tarea: `lixiviacion/panel.py` (layout anterior renombrado y tres pestañas), `callbacks.py` (consulta de opciones condicionada a Diagnóstico), `visual_review.py` (casos del mapa), `README.md` (entrada al mapa). No se modificó `layout.py` en esta tarea; su cambio de integración es anterior. `db.py`, fórmulas y consultas de Diagnóstico permanecen intactos.

Pendiente: fuente/contrato temporal validado para módulos, submódulos y estados detallados; semántica de marcadores; recomendador. La dimensión `parcela` no tiene vigencias, por lo que la geometría representa el catálogo actual incluso al consultar fechas históricas. El shell global móvil conserva sus limitaciones previas; el mapa permite scroll interno sin inventar celdas.

Sin cambios PROD, objetos SQL, datos, legacy ni TEST. Sin commit/push.
