# Auditoría MB/IMP: 20-09-2026, turno A

## Conclusión

**Escenario A en DEV.** No existe registro oficial para la clave `2026-09-20/A` en `inventar_SpcHidr.mov_cam`, su vista `resumen_mina`, ni en `mov_cam_powerbi`. Sí existe IMP. La vista vigente `v_conciliacion_chancado_v2` selecciona IMP porque el lado oficial del `FULL OUTER JOIN` está ausente. El resultado no es una etiqueta de Excel: TM1 y TM2 utilizan CuT `0,423387991` y Malla -100 `26,253190515` de IMP; la trazabilidad registra `PROVISIONAL_IMP` y el cache de emisión contiene esos valores. No hay evidencia de un bug de precedencia, de una imagen antigua o de una versión SQL equivocada para esta clave. **No se modificó código ni base de datos.**

Las copias `(34)` y `(35)` citadas no estaban disponibles en el checkout ni en Downloads. Su contenido fue informado por el usuario; la auditoría contrasta la ruta DEV actual hasta las tablas que consume el exportador, sin atribuir a esas copias una verificación directa.

## Clave y vecinos

Datos capturados en `snapshot.json` mediante las consultas `SELECT` de `read_only_audit.py`. Conexión: `VPS-5347319-X / inventar_SpcHidr`; IMP se consulta en `DEV_SIIR.hidro` del mismo servidor.

| Fecha/turno | MOV_CAM oficial | IMP | Vista conciliada | Observación |
|---|---:|---:|---|---|
| 19/09 A | 6 filas, 37.656,305 TMS | 38.148,123 TMS | MINA | Hay ambas; gana oficial |
| 19/09 B | 4 filas, 34.030,504 TMS | 34.508,764 TMS | MINA | Hay ambas; gana oficial |
| 20/09 A | **0 filas** | **603,160 TMS** | **IMP** | Fallback esperado |
| 20/09 B | 0 filas | 0 filas | Sin fila | No inventa datos |
| 21/09 A | 0 filas | 0 filas | Sin fila | No inventa datos |
| 21/09 B | 1 fila, 1.392,3 TMS | 1.428 TMS | MINA | Hay ambas; gana oficial |

`mov_cam_powerbi` también carece de filas el 20/09 A. `resumen_mina` tiene 0 filas en esa clave. El 19/09 A/B y 21/09 B proporcionan una comprobación con ambas fuentes presentes: la vista usa MINA aun cuando IMP tiene valores distintos. En MOV_CAM el turno crudo es `TA/TB`; `v_conciliacion_chancado_v2` lo normaliza a `A/B` antes del `JOIN` por `Fecha` y `Turno`.

### Analitos de 20/09 A

| Campo | MB | IMP | TM1/TM2 resuelto | Cache RTO |
|---|---|---:|---:|---:|
| Tonelaje de fuente | Ausente | 603,160304119 TMS | La vista usa IMP | Apilado del turno es otra masa |
| CuT | Ausente | 0,423387991 | 0,423387991 / IMP | 0,423388 |
| CuS | Ausente | NULL | NULL / SIN_DATO | NULL |
| CuFe | Ausente | NULL | NULL / SIN_DATO | NULL |
| CO3 | Ausente | NULL | NULL / SIN_DATO | NULL |
| Malla -100 | Ausente | 26,253190515 | 26,253190515 / IMP | 26,253191 |
| ClayBeta | Ausente | NULL | NULL / SIN_DATO | NULL |
| Caolinita | Ausente | NULL | NULL / SIN_DATO | No hay campo equivalente en cache |

`trazabilidad_analitos_tm_emision_test` tiene CuT y Malla -100 con `Fuente_Tecnica=IMP`, `Resolucion=PROVISIONAL_IMP` en ambas torres; el resto de esos analitos queda `SIN_DATO`. `Fecha_Proceso=2026-10-06 12:03:14.111`, y el cache tiene `Fecha_Actualizacion=2026-10-06 12:03:21.334079`: fueron reconstruidos hoy y todavía dan IMP. La función diaria vigente devuelve CuT `0,423388`, Malla -100 `26,253191` para el día 20, coherentes con el redondeo del cache. El Generador Diario es por **día**, así que esa fila no representa por sí sola la fuente de un turno; el cache y la trazabilidad sí fijan el turno A.

## Linaje efectivo

1. `mov_cam` contiene fecha, turno `TA/TB`, tonelaje y leyes. `resumen_mina` pondera por `Ton` y agrupa por fecha, turno, origen y fase. `mov_cam_powerbi` participa en otros cálculos de masa, pero no alimenta la rama oficial de `v_conciliacion_chancado_v2`.
2. `DEV_SIIR.hidro.v_imp_conciliacion_chancado` aporta el fallback IMP por fecha/turno con tonelaje y analitos. La vista no persiste el resultado.
3. `v_conciliacion_chancado_v2` agrega `resumen_mina`, normaliza `TA/TB`, hace `FULL OUTER JOIN` con IMP por fecha y turno. `Usar_IMP=1` solo si IMP tiene `Ton>0` y el oficial falta o suma `Ton=0`. Todas las columnas de analitos y `Fuente_Dato` salen de la misma rama. Precedencia efectiva: **oficial con tonelaje no nulo y distinto de cero > IMP válido**. Una fila oficial de tonelaje cero activa fallback IMP según la regla vigente.
4. `v_validacion_leyes_tm1_v2` y `v_validacion_leyes_tm2_v2` hacen `LEFT JOIN` a la conciliación por fecha/turno, aplican primero las reglas de representatividad de laboratorio y, donde corresponde fallback de mina, conservan `Fuente_Dato` de la vista. `v_leyes_validadas_tm_turno` unifica TM1/TM2 y A/B; `v_leyes_resueltas_data_tm_reporte_test` resuelve arrastres por analito. Son vistas en línea, no cache.
5. `sp_reporte_turno_emision_test` lee la vista resuelta, `v_conciliacion_chancado_v2` y otros insumos; produce las filas de turno y escribe `trazabilidad_analitos_tm_emision_test`. Mapea `Fuente_Tecnica=MINA` a `MB` y `IMP` a `PROVISIONAL_IMP` en la trazabilidad. No se ejecutó el SP durante esta auditoría.
6. `sp_actualizar_reporte_turno_cache_emision_test` borra **solo el rango** `[inicio,fin)` y hace `INSERT ... EXEC sp_reporte_turno_emision_test` dentro de una transacción. El cache persistente tiene clave operacional fecha/turno. `fn_generador_reporte_diario_emision_test` lee ese cache y consolida A/B en una fila diaria.
7. El callback de Excel en `reportabilidad_cb.py` llama `preparar_paquete_reporte_turno_emision`. Esta función refresca dependencias y cache, luego lee el cache, el Generador Diario y la trazabilidad en la misma conexión/transacción. `export_reporte_turno_estilo_leyes_finos` escribe `Reporte por Turno` y `Trazabilidad Analitos` desde ese paquete. Las consultas sueltas al cache sí pueden leer una imagen histórica si no se ejecuta antes el coordinador, pero el flujo de exportación auditado sí lo ejecuta.

Las definiciones LIVE de los nueve objetos principales se guardaron en `snapshot.json`. Frente a las capturas SQL de `backfill_reportes_septiembre_2026/definitions`, coinciden línea por línea al ignorar líneas vacías y espacios extremos. La diferencia de SHA bruto se debe al formato de saltos/líneas en los snapshots, no a una regla distinta. Los objetos efectivos son los sufijados `_emision_test` y `_v2` indicados arriba; las versiones antiguas `sp_reporte_turno_test`, `reporte_turno_cache` y `fn_generador_reporte_diario` existen en el repositorio, pero el exportador actual usa la ruta de emisión.

## Decisión y acciones

Para `20/09 A`: MB **No**; IMP **Sí**; fuente actual **IMP**; fuente correcta con los datos actuales **IMP provisional**. La decisión ocurre en `v_conciliacion_chancado_v2`, no en Excel. El cache fue renovado el 06/10 y sigue alineado con la vista; no hay indicio de invalidación fallida para esta clave.

No hay archivo funcional ni objeto SQL a modificar con la evidencia actual. Cambiar la prioridad, invalidar cache o sustituir la etiqueta fabricaría MB donde no hay datos oficiales. Si llega MB posteriormente para la misma clave, el siguiente flujo de exportación debe volver a leer la vista y reconstruir selectivamente el rango del cache; el 19/09 y 21/09 con ambas fuentes muestran que MB gana en la vista. La incorporación real de MB para el 20/09 y una validación posterior de su cambio de valores siguen siendo condiciones futuras, no pruebas ejecutadas.

Consultas reproducibles: `consultas_select.sql`. No se ejecutó `UPDATE`, `DELETE`, `DROP`, SP, exportación nueva, publicación, commit ni push. El único cambio de archivos de esta auditoría es evidencia y un script de lectura en esta carpeta.
