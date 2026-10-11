# NULL y cero

| Uso | Clasificación | Decisión |
|---|---|---|
| `cb_resumen_general`: toneladas diarias de camiones/rotopala `fillna(0)` | A: suma | Se conserva para agregar masa; el conteo de «sin información» sigue separado. |
| `cb_resumen_general`: CV25/topografía `fillna(0).sum()` | A: suma acumulada | Se conserva para totalizar; no genera una medición diaria artificial. |
| `cb_matriz_mensual`: toneladas `fillna(0)` y pivot `fill_value=0` | A: suma de matriz | Se conserva. La matriz representa aportes por día, no una curva de medición. |
| `cb_preview_conciliados`: tonelajes `fillna(0)` | C: regla de presentación existente | Se conserva el total, pero la columna de origen distingue «Sin información». No se cambió el cálculo. |
| `cb_preview_conciliados`: `avance_roto_pct.fillna(0)` | B: priorizaba una fila sin avance medido como 0 % | Se eliminó; solo se elige protagonista entre filas con avance definido. |
| `cb_cv25`: `tms_preliminar.fillna(0).sum()>0` | A: prueba de existencia de masa | Se conserva; las series del gráfico mantienen sus NULL. |
| Rendimiento topográfico 04-10, rotopala 2 | B: la vista SQL entrega 0 por `SUM(CASE ... ELSE 0)` sin fila TOPOGRAFIA | Se añadió un campo read-only de existencia de fuente real y se dibuja gap si no hay medición. La cifra SQL no se cambió. |

Consulta DEV: el 04-10 la vista de rendimiento entrega `tms_topografia=0` y `rendimiento_topografia_tms_hr=0` para rotopala 2, pero no hay filas de `fuente_reclamo='TOPOGRAFIA'` para ninguna rotopala. Por eso el punto cero habría sugerido una medición inexistente.

La brecha CV25 extrema del 07/09 (`23,5` TMS CV25 frente a `29.015,894387` topografía) es `123.371,891008 %`; también hay `73.858,291568 %` el 10/09 y `9.757,790748 %` el 08/09. La vista aplica su cociente con denominadores positivos muy pequeños. Ocultar esos valores o reclasificarlos como «no evaluables» requiere definir un umbral de negocio: se documenta y no se altera la gráfica ni la regla.

Hay dos filas `PRELIMINAR_CV25` entre 01/09 y 06/10 con TMS y m³ de rotopala cero. La etiqueta proviene de la fuente calculada, pero la masa es cero. Se deja visible y se solicita revisión funcional para decidir si debe mostrarse como «Sin información»; no se cambia automáticamente.
