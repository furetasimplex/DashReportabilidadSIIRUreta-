# Flujo CV025

`sp_cargar_cv25_horas` lee `vista_resumen_datos_filtrados.fecha_turno`, `cv025tot`, `cv025_tot`, `rc_001` y `rc_002`. El parámetro predeterminado selecciona `cv025tot` como tag oficial.

La fuente ya entrega valores diarios rotulados como `DELTA_TOTALIZADOR_CV25_DIARIO`; el SP no aplica `LAG`. Por tanto, el comportamiento actual supone que la vista origen ya calculó el delta. En julio, `datos_filtrados` tiene 24 filas por día y dos turnos: la granularidad efectiva es horaria y `horas_por_muestra=1` es coherente.

Las horas usan `rc001corr > 45` para R1 y `rc002corr > 45` para R2. El umbral 45 está activo, aunque la propia tabla lo marca “pendiente de confirmar”.

Cuando Dash recalcula no pasa `@HumedadPct`. Para filas nuevas, `humedad_pct=NULL` y `tms_dia=tmh_dia`; para filas existentes conserva la humedad anterior con `COALESCE(@HumedadPct,tgt.humedad_pct)`. Esto significa que no hay una conversión seca efectiva en nuevas filas: TMH se trata numéricamente como TMS. Es un riesgo material.

Los negativos se conservan en tags crudos, pero `tmh_dia/tms_dia` quedan `NULL`. Si faltan horas totales, no se reparte. CV025 se compara solo con topografía de rotopalas porque la regla de proceso declara que la correa no recibe camiones.

La vista activa `v_preliminar_cv25` limita el preliminar a fechas posteriores a la última topografía de cada módulo abierto. Si hay dos abiertos, divide en partes iguales; no pondera por saldo ni evidencia física del módulo.

En PROD (definición 2026-09-07, catálogo `analisis/vistas.md`) el acumulado ya no vive solo ahí: `v_preliminar_cv25_con_acumulado` suma `m3_acum_ultima_topografia + SUM(m3_preliminar_dia)` y es esa vista la que consume `v_reclamo_diario`.

