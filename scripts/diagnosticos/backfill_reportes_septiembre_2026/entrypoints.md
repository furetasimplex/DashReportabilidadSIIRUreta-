# Entrypoints vigentes — inspección 06-10-2026 DEV

Código: `report_export/report_export.py` y `report_export/callbacks/reportabilidad_cb.py`.
Definiciones LIVE conservadas en `definitions/`; inventario y dependencias en JSON.

| Reporte | UI / paquete | Coordinador de escritura |
|---|---|---|
| Representatividad Torres | `generar_reporte` → `_cargar_detalle_representatividad_periodo` → `preparar_paquete_editor_representatividad` | `refrescar_representatividad_para_exportacion` |
| Análisis Torres de Muestreo | tipo `reporte_turno` → `preparar_paquete_reporte_turno_emision` | `refrescar_dependencias_reporte_turno_emision` |
| Datos Conciliados | `preparar_paquete_datos_conciliados_emision` | `refrescar_dependencias_datos_conciliados_emision` |

Representatividad llama primero al coordinador RTO con ventana 7 dentro de su transacción;
después ejecuta `sp_calcular_resumen_intervalo_totTM`,
`sp_refrescar_representatividad_torres` y `sp_sincronizar_bd_ton`.
No es una dependencia lineal simple de los tres reportes: se conserva la preparación
upstream del runtime y se vuelve a refrescar TM después de validar Representatividad.

RTO: `sp_mantiene_apilado_tmh_v2_test` → `sp_refrescar_historico_apilado_test`
(solo fechas recalculadas, parámetro 0) → `sp_mantiene_factor_ajuste_camiones_v2_test`
(parámetro 0) → `sp_refrescar_clays_cufe` → `sp_actualizar_reporte_turno_cache_emision_test`
→ `sp_reporte_turno_emision_test`. Este último también reconstruye la trazabilidad de analitos.

DC: coordinador RTO con ventana 15 → `sp_mantiene_datos_conciliados_emision_test`
con `DiasReproceso=0, RefrescarFactor=0`.

El paquete Excel RTO además refresca DC para su hoja de reconstitución SRR.
El editor de Representatividad expande el inicio al primer día del mes.
El botón de descarga de Representatividad consume el snapshot oficial activo;
refrescar tablas no equivale a publicar una versión oficial nueva.

## Destinos e idempotencia

| Tabla | Escritura |
|---|---|
| Control_Apilado_TMH_v2_test | MERGE por Fecha |
| Historico_Apilado_Diario | DELETE+INSERT del rango |
| Control_Factor_Ajuste_Camiones_v2_test | MERGE por Fecha |
| Clays_CuFe | UPDATE / INSERT para claves ausentes Fecha/Torre/Turno |
| Clays_CuFe_trazabilidad | Auditoría de INSERTAR/ACTUALIZAR/TRAZABILIDAD; SIN_CAMBIO no inserta |
| reporte_turno_cache_emision_test | DELETE+INSERT, fin exclusivo |
| trazabilidad_analitos_tm_emision_test | DELETE+INSERT, fin exclusivo |
| Resumen_Intervalo_TotTM | MERGE torre_id/fecha_turno/turno_op |
| representatividad_torres_resultado | DELETE+INSERT por Dia |
| BD_Ton | UPDATE + INSERT NOT EXISTS por Fecha |
| Datos_conciliados_of | MERGE por Fecha |

No hay triggers activos en estos destinos. No se encontraron escrituras append sin
control sobre claves de resultados. La auditoría de cambios y las fechas de cálculo
no son invariantes byte a byte al repetir un refresco.
Las referencias cross-database encontradas son DEV_SIIR y la propia base DEV.

Se mantienen locks globales PI/TUM, mensual de Representatividad y Clays, así como las
transacciones originales. Cada bloque retorna después de su commit; no hay transacción
global mensual. Se detiene en el primer error, incluso si corresponde a liberar un lock.
