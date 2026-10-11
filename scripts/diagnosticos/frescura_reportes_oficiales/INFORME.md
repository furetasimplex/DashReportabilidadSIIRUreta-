# Auditoría de frescura de reportes oficiales — DEV

**Observado:** 2026-10-06 13:16–13:17 (hora SQL). **Servidor/BD:** `VPS-5347319-X / inventar_SpcHidr`. Solo se ejecutaron `SELECT` contra DEV y lectura local de dos Excel. No se ejecutó ningún SP, callback, regeneración ni publicación.

## Dictamen

| Reporte | Entry point oficial del checkout | SP/función oficial | Cache/emisión leída por Excel | Recalcula al solicitar | Fuente=emisión observada | Riesgo stale | Estado |
|---|---|---|---|---|---|---|---|
| Representatividad de Torres | `exportar_excel`, tipo `representatividad_torres` | Publicación: `armar_paquete_reporte_torre_oficial` → SP de refresco y lectura | `reporte_torre_oficial_snapshot`, id activo 135 | **Descarga: no**; publicación: sí | 30/30 días, 12 métricas: vista viva = resultado = snapshot | Nueva fuente posterior a publicación no invalida snapshot | **B** |
| Análisis TM | `exportar_excel`, tipo `reporte_turno` | `preparar_paquete_reporte_turno_emision` → `sp_actualizar_reporte_turno_cache_emision_test` | `reporte_turno_cache_emision_test` | Sí, intervalo solicitado hasta corte | Excel `(34)` = cache actual en 60/60 filas y 6 campos; `(35)` difiere en 33 valores | Diferencia entre emisiones sin atribución transaccional | **E** |
| Datos Conciliados | `exportar_excel`, tipo `prod` | `preparar_paquete_datos_conciliados_emision` → `sp_mantiene_datos_conciliados_emision_test` | `Datos_conciliados_of` + vista SRR | Sí, período solicitado | 30 filas presentes; equivalencia con cálculo vivo no demostrada sin ejecutar SP | Fuentes cambiadas fuera de ventana o concurrentes no verificadas | **E** |

**Lectura de estados:** B = valores actuales coinciden, invalidación posterior no demostrada; E = frescura completa no demostrable. La clasificación de TM como E se debe a la divergencia de dos archivos de la misma fecha y a que no se puede unir cada archivo con su transacción/DB exacta. No hay evidencia suficiente para declarar C o D. La ruta de Representatividad sí tiene mecanismo conocido de reutilización de snapshot y, por diseño, puede entregar una fotografía antigua si cambian fuentes antes de republicar.

## Evidencia de septiembre

### Representatividad

- Cabecera activa de septiembre: `id_reporte=135`, `fecha_generacion=2026-10-06 11:59:37`, corte operacional 2026-09-30. Hay 17 cabeceras anteriores inactivas.
- `v_representatividad_diaria_calculada`, `representatividad_torres_resultado` y bloque `rep_torres` del snapshot activo tienen 30 días y cero diferencias en los 12 indicadores TM1/TM2/SRR A/B químico/físico, con tolerancia numérica 1e-6. `fecha_calculo` de la tabla para 01-sep es 2026-10-06 11:59:02.
- El snapshot tiene otros seis bloques (`bd_ton_fy`, `bd_ton_mes`, `turno_mes`, `gestion_fy_quimico`, `gestion_fy_fisico`, `pesos_turno`) y el detalle 60 filas. No se compararon todos esos bloques con las consultas vivas, ni se emitió un Excel nuevo. Por tanto, la igualdad comprobada se limita a los 12 indicadores de `rep_torres`; no equivale a una certificación integral del libro.
- La descarga actual usa el snapshot activo. Una carga nueva no dispara automáticamente la publicación. La fecha de descarga tampoco es fecha de recálculo.

### Análisis TM

- `reporte_turno_cache_emision_test`: 60 claves únicas Fecha/Turno A/B del 01 al 30; todas las filas consultadas tienen `Fecha_Actualizacion=2026-10-06 12:03:21.334079`. El SP de actualización vigente ejecuta `DELETE` del intervalo y luego `INSERT ... EXEC sp_reporte_turno_emision_test` en transacción; no hace cache hit condicional.
- 20-sep A, únicamente ruta oficial: `v_conciliacion_chancado_v2.Fuente_Dato=IMP`, CuT `0.423387991`, Malla100 `26.253190515`; cache de emisión `Fuente_Info_Quimica=IMP`, `Fuente_Info_Fisica=IMP`, CuT `0.423388`, Malla #100 `26.253191`. El Excel `(35)` muestra 20-sep A con TMS `1958.4334` y módulo `140`, avance `100`; es coherente con la cache actual para ese registro. No se usó `reporte_turno_cache` legacy.
- Excel `(34)` creado 12:03:33 (138347 bytes); Excel `(35)` creado 12:04:00 (138183 bytes). Comparación de valores de celda: 33 diferencias en Reporte por Turno, 45 en Generador Reporte, 39 en Reconst Mod SRR; cero en las otras cuatro hojas. `checks.json` enumera las celdas. La comparación de 60 filas del Reporte por Turno con la cache actual en TMS, Stock, Mina, SRR y, para A, módulo/avance da **0 diferencias para `(34)`** y **33 para `(35)`**.
- Testigo 22-sep A: cache actual y `(34)` TMS `37083.435413`, módulo `1`, avance `47.2315%`; `(35)` TMS `36386.174227`, módulo `140`, avance `100%`. Testigo 23-sep A: cache actual/`(34)` TMS `43325.897058`; `(35)` `42359.366055`. La función oficial de Generador consultada hoy da 22-sep TMS diario `81100.988351` y 23-sep `88450.367040`, coincidentes con `(34)`; `(35)` da `79575.687292` y `86474.966889`.
- **Causa de la diferencia `(34)`/`(35)`: NO DEMOSTRABLE** con estos archivos y el estado persistido actual. No constan ID de ejecución, hash de versión, servidor/BD ni snapshot de la cache adjuntos a cada Excel. Que `(35)` sea posterior en el sistema de archivos y difiera de la cache observada no demuestra cuál transacción o ruta lo generó ni que fuese stale al momento de descarga.
- El SP de turno calcula desde varias vistas, no hay una vista única que reproduzca todas sus 40+ columnas sin ejecutarlo. Dado el veto de SP, no se hizo comparación completa cálculo vivo vs cache para 01–30. Los 60 registros de cache se contrastaron con los dos archivos y se hizo testigo fuente→cache para 20-sep A.

### Datos Conciliados

- `Datos_conciliados_of` tiene 30 filas del 01 al 30 en DEV. Es la tabla que el exportador vigente consulta, con `v_ley_cu_srr_resuelta_emision_test` para la columna `Ley_CuT_Real_srr`; el Excel también incorpora factor y balance.
- El callback hace un nuevo mantenimiento del período en transacción antes de leer. El SP de emisión fue identificado y su dependencia a esta tabla, cache de turno, histórico, función generador y fuentes base se verificó con metadatos SQL. La tabla no expone una marca inequívoca de emisión por fila en la muestra; `dc_id` no es un timestamp.
- Para establecer igualdad con el cálculo actual de las columnas críticas sería preciso ejecutar el SP o reconstruir su lógica de 42 KB en SELECT equivalentes y validar todas sus fuentes. Esa equivalencia no se afirma aquí. Tampoco se generó un Excel de DC bajo la restricción de solo lectura. Los archivos DC `(34)`/`(35)` se localizaron, pero la solicitud de comparación de emisiones se centraba en Análisis TM; no se usaron para atribuir frescura a DC.

## Mecanismo de frescura y límites

| Pregunta | Representatividad | Análisis TM | Datos Conciliados |
|---|---|---|---|
| ¿Solicitud de Excel recalcula? | No; lee publicación activa | Sí; prepara y reemplaza cache de intervalo | Sí; prepara RTO y mantiene tabla del período |
| ¿Fuente nueva invalida persistencia? | No automáticamente; requiere republicar | Nueva solicitud invoca reconstrucción del intervalo, con ventana de apilado de 7 días | Nueva solicitud invoca reconstrucción, con ventana de apilado de 15 días |
| ¿Reutiliza emisión anterior? | Sí, snapshot activo | Código actual no contiene rama de reutilización de cache | Código actual no contiene rama de reutilización de DC |
| ¿Timestamp fuente→cálculo→emisión→export? | Hay cálculo y publicación; no timestamp por fuente/bloque ni export | Hay `Fecha_Actualizacion` de cache y fecha de archivo; no ID de transacción por Excel ni todas las fechas fuente | No se estableció timestamp completo por fila/fuente/export |

La concordancia de un valor y un timestamp reciente no certifica toda la cadena. Tampoco es posible demostrar desde el checkout solamente qué versión exacta atendió las descargas `(34)` y `(35)`; faltan logs de solicitud/instancia y conexión de esos eventos. El cotejo 01–30 para Representatividad cubre los 12 indicadores diarios, para TM cubre la cache frente a los dos Excel en seis campos por turno, y para DC solo confirma presencia y la ruta de lectura. Se señalan estos alcances para no convertir una prueba parcial en conclusión total.

## Archivos de evidencia

- `pipeline_oficial.md`: linaje desde callbacks actuales.
- `objetos_legacy.md`: clasificación por uso real.
- `consultas_select.sql`: consultas realizadas (solo SELECT/metadatos).
- `evidencia_dev.json`: resultados completos, definiciones SQL y datos de septiembre.
- `checks.json`: comparaciones reproducibles y celdas diferentes de los Excel.
- `audit_readonly.py`, `build_checks.py`: extracción y cotejo offline. No contienen escritura SQL.
