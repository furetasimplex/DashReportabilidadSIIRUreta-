# Clasificación de objetos detectados

La clasificación se basa en referencias del callback/exportador vigente y dependencias SQL DEV, no en nombres.

| Objeto | Tipo | Consumo actual demostrado | Estado | Motivo |
|---|---|---:|---|---|
| `reporte_turno_cache_emision_test` | Tabla | Sí | OFICIAL | Lectura directa del Excel TM; escrita por el SP invocado por el coordinador. |
| `sp_actualizar_reporte_turno_cache_emision_test`, `sp_reporte_turno_emision_test` | SP | Sí | OFICIAL | Cadena efectiva desde `preparar_paquete_reporte_turno_emision`. |
| `fn_generador_reporte_diario_emision_test` | Función | Sí | OFICIAL | Generador diario de emisión la referencia y lee la cache oficial. |
| `Datos_conciliados_of` | Tabla | Sí | OFICIAL | Consulta directa del exportador DC y del Reconst SRR de TM. |
| `sp_mantiene_datos_conciliados_emision_test` | SP | Sí | OFICIAL | Lo invoca el coordinador de DC y TM Excel. |
| `reporte_torre_oficial_cab`, `reporte_torre_oficial_snapshot`, `reporte_torre_oficial_detalle` | Tablas | Sí | OFICIAL | Descarga oficial de Representatividad lee el reporte activo. |
| `representatividad_torres_resultado` | Tabla de cálculo | Sí, antes de publicar | OFICIAL | Refresco y lectura por SP de Representatividad; no es el snapshot que lee la descarga. |
| `reporte_turno_cache` | Tabla | No en la ruta actual | LEGACY | El Excel vigente lee `reporte_turno_cache_emision_test`; se excluye de los checks de frescura. |
| `Datos_conciliados_of_emision_test` | Tabla | No en la ruta actual | LEGACY | El código vigente fija `TABLE_DATOS_CONCILIADOS_EMISION` a `Datos_conciliados_of`. |
| `sp_actualizar_reporte_turno_cache`, `sp_generador_reporte_diario`, `sp_mantiene_datos_conciliados_of` | SP | No en la ruta Excel vigente | LEGACY | Funciones standalone antiguas permanecen en Python, pero el callback actual usa sus variantes de emisión. |

Una dependencia SQL indirecta de un objeto de emisión puede mantener capas técnicas. Esta tabla no marca esas capas como legacy por el sufijo `_test`.
