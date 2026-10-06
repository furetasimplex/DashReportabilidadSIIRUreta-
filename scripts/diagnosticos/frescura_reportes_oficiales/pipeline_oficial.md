# Pipeline vigente comprobado desde la aplicación

Observación de código: `main.py` importa `layout`; `layout.py:9` importa `report_export.callbacks.reportabilidad_cb`. Los callbacks Dash se definen en ese módulo. La BD DEV observada es `VPS-5347319-X / inventar_SpcHidr` (2026-10-06 13:16 hora del servidor). Se verificaron las dependencias en `sys.sql_expression_dependencies` y las definiciones en `sys.sql_modules`; ver `evidencia_dev.json`.

## Representatividad de Torres

- Vista previa: `reportabilidad_cb.py:7342` (`generar_reporte`, tipo `representatividad_torres`) → `preparar_paquete_editor_representatividad` → refresco RTO, `sp_calcular_resumen_intervalo_totTM`, `sp_refrescar_representatividad_torres`, `sp_sincronizar_bd_ton` → `representatividad_torres_resultado` y otras lecturas vivas.
- Publicación: `reportabilidad_cb.py:8457` → `armar_paquete_reporte_torre_oficial` → `sp_reporte_representatividad_torres` lee `representatividad_torres_resultado`; `write_reporte_torre_oficial` guarda cabecera, detalle y siete bloques JSON en `reporte_torre_oficial_snapshot`.
- Descarga Excel oficial: `reportabilidad_cb.py:7662`, tipo `representatividad_torres`, y descarga histórica `:8703` → selecciona `reporte_torre_oficial_cab.activo=1` → `fetch_reporte_torre_oficial_snapshot` + detalle → `_export_representatividad_desde_paquete` → Excel. **Esta descarga reutiliza el snapshot; no refresca fuentes.** Una nueva publicación reemplaza el activo.
- Fuente SQL inmediata de cálculo: `v_representatividad_diaria_calculada` → `sp_refrescar_representatividad_torres` → tabla `representatividad_torres_resultado`. Otras fuentes del paquete están en `_fetch_fuentes_mensuales_torres_oficial` (`report_export.py:3233`).

## Análisis TM

- Excel: `reportabilidad_cb.py:7662`, tipo `reporte_turno` → `preparar_paquete_reporte_turno_emision` (`report_export.py:2558`) → `refrescar_dependencias_reporte_turno_emision` → apilado TMH, histórico, factor, Clays/CuFe → `sp_actualizar_reporte_turno_cache_emision_test` → `sp_reporte_turno_emision_test` → **`reporte_turno_cache_emision_test`** → `fetch_reporte_turno_cache_emision` → `export_reporte_turno_estilo_leyes_finos`.
- La actualización oficial borra y reinserta el intervalo inclusivo solicitado hasta el corte operacional; fin SQL exclusivo. El coordinador usa siete días de reproceso para apilado; el SP de cache reconstruye todo el intervalo. La cache se valida por A/B y `Fecha_Actualizacion` dentro de la misma transacción.
- Generador Reporte: `fn_generador_reporte_diario_emision_test`, referenciada por `sp_generador_reporte_diario_emision_test`; lee la misma cache de emisión. Trazabilidad Analitos: `trazabilidad_analitos_tm_emision_test`, escrita por `sp_reporte_turno_emision_test`. Reconst Mod SRR: funciones `fn_reconstitucion_srr_turno_emision_test` y `fn_reconstitucion_srr_emision_test`, con `Datos_conciliados_of` actualizado dentro del paquete Excel. Clays, curva y malla: lecturas auxiliares del paquete.
- Dependencias SQL directas del SP de turno incluyen `v_conciliacion_chancado_v2` (MB/IMP), `v_datos_apilado_tmh_v2`, `v_reporte_turno_campania_modulo_test`, `v_reporte_turno_fuentes_info_test`, `v_leyes_resueltas_data_tm_reporte_test`, `v_apilado_base_mina_stock_srr`, planes, `Clays_CuFe` y representatividad. Sufijos `_test` aquí **sí pertenecen al pipeline actual**.
- Preview y PDF también invocan el coordinador de emisión (`reportabilidad_cb.py:7442,8125`).

## Datos Conciliados

- Excel: `reportabilidad_cb.py:7662`, tipo `prod` → `preparar_paquete_datos_conciliados_emision` (`report_export.py:2493`) → coordinador RTO con 15 días de reproceso de apilado → `sp_mantiene_datos_conciliados_emision_test` con `@DiasReproceso=0`, `@RefrescarFactor=0` → **`Datos_conciliados_of`** → `fetch_datos_conciliados_emision_report` + `v_ley_cu_srr_resuelta_emision_test` → exportador Excel. El mismo coordinador se llama desde preview.
- El SP mantiene el período calendario completo solicitado; RTO respeta el corte operacional. Ambos coordinadores comparten transacción. `Datos_conciliados_of` es la persistencia leída por el Excel; `reporte_turno_cache_emision_test` es un insumo previo, no la tabla Excel final de DC.
- Dependencias directas verificadas en SQL: `Historico_Apilado_Diario`, `fn_generador_reporte_diario_emision_test`, `reporte_turno_cache_emision_test`, `v_ajuste_camiones_emision_test`, `reclamo.v_reclamo_para_conciliados`, `mov_cam`, `hidro.imp_csv`, planes y producción catódica, entre otras.

La evidencia muestra el flujo en el checkout actual y las definiciones DEV. No se ejecutó ningún callback ni SP: la auditoría no puede garantizar que una instancia web desplegada use este checkout si no se dispone de su hash de versión o registro de ejecución.
