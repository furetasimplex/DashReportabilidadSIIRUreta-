# Informe de comparación de reconstitución de módulos

Estado preparado para revisión: 28-10-2026. Comparativo simple de módulos del pad SU entre los XLSX oficiales publicados y las exportaciones del exportador activo `DashReportabilidadSIIR/reconstitucion/informe_modulos.py`.

## Alcance y fuentes

- Caso 10009, run 10082: campaña 11, ventana 01–07 septiembre de 2026; módulos SU con masa: 134 y 135.
- Caso 10013, run 10145: campaña 12, ventana 01–12 octubre de 2026; módulos SU con masa: 4, 5, 6, 7 y 8.
- Se comparan los módulos y los campos disponibles en `MODULOS`, conservando las filas de módulo y el resumen de parcela limitado a la ventana del caso. Un resumen parcial no se presenta como total oficial completo.
- Los XLSX oficiales Sulfuro(5) se usan como referencia publicada. La exportación actual se genera desde el exportador activo con snapshots y capturas offline. No se consulta la base, no se ejecuta SQL/SP y no se copia ni importa staging viejo.
- OX no se agrega: ninguno de estos snapshots tiene masa OX en el periodo.

## Campos y cálculos

El archivo compara más que masa: leyes, finos, consumo H+, clasificación contractual, orígenes, mallas, calidad Mina/Stock, SRR, ACF, CSR, sal y fechas de reposo donde existen datos. Se preservan faltantes como vacíos y los ceros explícitos como cero.

La calidad por turno se pondera por TMS asignada al módulo/turno. Los atributos ACF/control se derivan de las fuentes POND de `mov_cam` para Mina+Stock; CSR usa ponderación por TMS × CuT. SRR se pondera por la participación SRR y TMS de cada módulo/turno, y se mantiene separado de Mina/Stock. Sal se deriva del dato de turno y usa TMS. Las coberturas y límites de cada campo se muestran en el detalle del artefacto del exportador.

Las columnas `BE:BG` representan Calidad01–03 para SU; `BH` es su suma contractual, calculada por fórmula. Las columnas `AY:BC` son las fuentes ACF03–07, y `BD` su suma. Las celdas de salida y fórmulas del comparativo deben leerse desde la exportación corregida vigente y recalcularse con artifact-tool; una celda de fórmula con caché nula no se interpreta por sí sola como ausencia de dato.

En Sulfuros, `S` se deriva de `CuS/CuT`, `K` de `TMS×CuT/100` y `T` de la regla contractual sobre solubilidad. La salida usa los valores recalculados de `MODULOS` del artefacto actual, no el CSV de una captura anterior. Las fórmulas se validan con artifact-tool porque openpyxl conserva fórmulas pero no las evalúa.

## Limitaciones

Estas comparaciones reproducen snapshots identificados, no certifican cambios posteriores del run oficial. Los casos son ventanas; los módulos parciales se contrastan como ventanas contra los valores completos publicados y no como reconciliación de módulo completo. La cobertura de cada fuente adicional es desigual y está indicada en el comparativo; los resultados Mina/Stock no se atribuyen a SRR. No hay OX con masa en los intervalos.

## Flujo reproducible

1. Generar/actualizar los XLSX de cada caso mediante `reconstitucion/informe_modulos.py` sobre los snapshots offline en `outputs/reconstitucion_modulos_casos_20261027/`.
2. Ejecutar `extraer_exportaciones_activas.mjs`; recalcula las hojas `MODULOS` con artifact-tool y extrae valores y fórmulas.
3. Ejecutar `generar_informe_simple.py` y luego `actualizar_comparativo_core.py`; sincroniza el payload visible y `comparacion_modulos_numerica.csv` con los XLSX recalculados.
4. Verificar que los siete módulos y el bloque ACF/Calidad01–03/H se vean en el HTML.

No se incluyen los XLSX standalone de comparación en este entregable.

La interfaz conserva selector de Caso y boton Cargar datos; el control de fechas deshabilitado y el mensaje inicial de itinerario fueron retirados. Las fechas del Caso siguen controlando la carga.
