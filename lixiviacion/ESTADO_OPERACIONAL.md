# Integración de estado operacional diario — DEV

El mapa conserva sus dos cards, 60 bloques físicos, geometría serpenteante, fecha, filtro PAD, selección y drawer de 400 px. Se sustituyó únicamente su fuente de datos y la presentación de estados. Diagnóstico sigue consumiendo V2 sin cambios; Recomendador conserva «Funcionalidad en desarrollo».

## Consulta final

```sql
SELECT fecha,pad_id,nombre_pad,parcela_id,numero_parcela,campana_id,
       numero_campana,modulos_total,estados_distintos,estado_operacional,
       composicion_modulos,tiene_dato_riego,riego_activo,tiene_dato_drenaje,
       drenaje_activo,fecha_ini_carguio,fecha_conformado,fecha_primer_riego,
       fecha_ultima_actividad_riego,fecha_ini_drenaje,fecha_ultima_actividad_drenaje,
       fecha_ini_reclamo,fecha_fin_reclamo,calidad_estado
FROM inventar_SpcHidr.fn_estado_operacional_parcela_diario(:fecha)
```

Proyección explícita de las 24 columnas del contrato; única fuente. SQLAlchemy `text`, parámetro `fecha` como `datetime.date`, `_connection()`/`get_engine()` existentes. Una ejecución por callback de carga. Ya no se consulta el catálogo `parcela` ni V2 desde el mapa. Se validan fecha, contrato, identidades, 60 filas y numeración física 32/28. Duplicados, ausencia de filas o códigos no soportados producen un aviso, nunca una clasificación o un relleno artificial.

`lix-map-data` conserva las 60 filas y el estado SQL sin cambiar. `fase_visual` se añade a la copia serializada. Filtro PAD y leyenda operan sobre este Store y no disparan consultas. Cambiar fecha/selección PAD limpia el detalle y resaltado anterior.

## Mapeo de presentación

`map_states.fase_visual(estado_operacional)` aplica solamente:

| Estado SQL | Fase visual | Etiqueta | Color |
|---|---|---|---|
| APILADO | APILADO | Apilado | `#c78542` |
| CONFORMADO_PRE_RIEGO | CONFORMADO_PRE_RIEGO | Conformado / espera de riego | `#bda663` |
| RIEGO, RIEGO_DRENAJE, DRENAJE_CON_RIEGO_PAUSADO, PAUSA_HIDRAULICA, DRENAJE_RESIDUAL | CICLO_HIDRAULICO | Ciclo hidráulico | `#5485a1` |
| REPOSO_PRE_RECLAMO | ESPERA_RECLAMO | Espera de reclamo | `#638d72` |
| RECLAMO | RECLAMO | Reclamo | `#b65c55` |
| RECLAMADO | RECLAMADO | Reclamado | `#929da4` |
| MIXTO | MIXTO | Mixto | `#9173ad` |
| SIN_INFORMACION, SIN_COBERTURA_HIDRAULICA, SIN_CLASIFICAR | NO_EVALUABLE | Sin información / no evaluable | `#303638` |

Leyenda de ocho categorías con conteos del PAD visible. No se calculan estados desde fechas, módulos o actividad. Tooltip muestra fase y condición exacta amigable; el código SQL original permanece en Store.

## Drawer

Identificación desde la función: nombre PAD, número parcela, campaña y fecha. Estado: fase macro, condición exacta, módulos considerados. Cuando `estados_distintos > 1`, se muestra Mixto y `composicion_modulos` sin modificar ni fabricar nombres de módulos.

Actividad: dato=1/activo=1 → Sí; dato=1/activo=0 → No; dato ausente/0 o activo NULL → Sin dato. No convierte NULL a falso.

Ocho hitos con etiquetas aprobadas, DD-MM-YYYY; NULL → «—». Calidad discreta: Evaluado, Información parcial, No evaluable o Sin información. No colorea el mapa. Se retiraron campos de flujo y fechas de ventana del drawer porque no forman parte del nuevo contrato; no se realizan joins para recuperarlos.

## Validación

`python -m pytest lixiviacion -q`: **27 PASS**. Mocks, sin dependencia obligatoria de SQL Server. Cubre los 14 estados, ocho fases, actividad NULL/0/1, contrato y duplicados, consulta parametrizada única, filtro PAD local, Store y composición, fechas, drawer, limpieza por error, navegación y regresión de Diagnóstico.

`python -m lixiviacion.smoke_map_dev`: **PASS DEV**, seis casos exactos y 60 filas únicas. También se consultó 11/09 y se confirmó contrato 60 filas. Evidencia: `SMOKE_MAP_DEV.json`.

| Estado 10-09-2026 | OX | SULF |
|---|---:|---:|
| APILADO | 0 | 1 |
| CONFORMADO_PRE_RIEGO | 0 | 2 |
| MIXTO | 1 | 2 |
| REPOSO_PRE_RECLAMO | 12 | 5 |
| RIEGO_DRENAJE | 19 | 18 |
| Total | 32 | 28 |

Canónico actualizado el 05-10-2026 por confirmación directa del usuario sobre las fuentes DEV actuales: OX y SULF tienen simultáneamente riego y drenaje activos en 19/18 parcelas. El criterio anterior `RIEGO` quedó desactualizado; no se cambió la función para obtener este resultado. La evidencia del precheck anterior permanece en `promocion_estado_operacional_20261005/`.

Casos confirmados: OX P17 `APILADO = 1 | CONFORMADO_PRE_RIEGO = 1`; SULF P1 `RECLAMADO = 4 | RECLAMO = 1`; SULF P2 `RECLAMO = 1 | REPOSO_PRE_RECLAMO = 4`; SULF P26/P27 conformado y P28 apilado.

Smoke navegador: `python -m lixiviacion.visual_review`, aplicación real en localhost con sesión Flask de prueba en memoria y lecturas DEV. Resultados y capturas actuales en `visual_estado_operacional/`; las carpetas visuales anteriores documentan versiones previas.

Resultado navegador: **PASS**. Sin errores JavaScript ni respuestas de callback fallidas; sin errores de callbacks duplicados observados. Ambos=60, OX=32, SULF=28. OX P17 y cinco casos SULF comprobados en drawer. Fecha 11/09 comprobada en detalle. Diagnóstico consultado y navegación por las cinco secciones conservada. A 520 px, scroll interno del mapa activo y documento sin overflow horizontal. Servidor temporal detenido al finalizar. Capturas `mapa_desktop.png` y `detalle_lateral.png` inspeccionadas.

`git diff --check`: sin errores. Hashes de `db.py`, `callbacks.py` y `panel.py` idénticos a la pasada anterior; Diagnóstico no fue modificado.

## Archivos

Modificados: `map_db.py`, `map_panel.py`, `test_map.py`, `smoke_map_dev.py`, `SMOKE_MAP_DEV.json`, `visual_review.py`, `README.md`, `assets/lixiviacion_map.css`.

Creados: `map_states.py`, este informe y `visual_estado_operacional/`.

Intactos: `db.py`, `callbacks.py`, `panel.py` (Diagnóstico), `layout.py`, V2, CPC, SP de CPC, Model6, recomendador y shell. No DDL, escrituras de datos, PROD, commit ni push.
