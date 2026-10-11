# Publicación en Datos Conciliados

`v_reclamo_para_conciliados` expone por fecha/módulo los TMS de rotopala, TMS de camiones y contexto. Conserva una fila si `fuente_reclamo <> 'SIN_DATO'` o si `tms_camiones_dia <> 0`.

`sp_mantiene_datos_conciliados_emision_test` crea `#ReclamoBase`, agrega TMS por PAD en `#ReclamoOxidosTMS` y `#ReclamoSulfurosTMS`, selecciona un módulo ganador diario para mostrar campaña/módulo/avance, y agrega camiones por PAD. Luego hace MERGE en `Datos_conciliados_of`.

Correspondencia:

- `TMS_Rotopala_1_Real`: suma diaria de `tonelaje_reclamado_diario`, PAD 1.
- `TMS_Rotopala_2_Real`: suma diaria, PAD 2.
- campaña/módulo/avance: contexto del ganador diario, no suma ni último módulo necesariamente.
- `Camiones_TMS_Reclamo_Oxidos`: suma diaria de camiones PAD 1.
- `Camiones_TMS_Reclamo_Sulfuros`: suma diaria de camiones PAD 2.
- `Total_Ripios_Incluye_Camiones_Real`: rotopalas más camiones según el bloque final del SP.

La comparación de julio está en `data_samples/comparacion_calculo_preview_publicado_julio.csv`. Las diferencias históricas no implican por sí solas error actual: `calculo_diario`, las vistas activas y la tabla publicada pueden representar momentos de ejecución distintos.

