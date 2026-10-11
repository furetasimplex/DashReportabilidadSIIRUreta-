# Análisis TM DEV: calendario y faltantes visibles

## Diagnóstico y call graph actual

`callbacks/reportabilidad_cb.py::exportar_excel`, rama `tipo="reporte_turno"`:

1. Conserva `ini_d` y `fin_d` solicitados por UI.
2. Invoca `preparar_paquete_reporte_turno_emision(ini_d, fin_d, salida="excel")`.
3. El paquete abre una transacción y llama a `refrescar_dependencias_reporte_turno_emision` con la misma conexión.
4. El coordinador adquiere el lock global transaccional, calcula `fin_efectiva=min(end_date,corte)` y `fin_sql_exclusivo=fin_efectiva+1 día`. Refresca Apilado hasta corte, Histórico según fechas materializadas/ventana, Factor hasta corte y Clays/cache hasta el fin exclusivo. Valida frescura y A/B del corte.
5. `fetch_reporte_turno_cache_emision` lee exclusivamente ese cache con `Fecha >= inicio AND Fecha < refresco["fin_sql_exclusivo"]`.
6. Los auxiliares y `fetch_generador_reporte_diario_emision` reciben el fin solicitado+1. Este último ejecuta `sp_generador_reporte_diario_emision_test`; la definición SQL local de su función parte del cache de emisión agrupado por fecha y añade planes. Pedir hasta octubre no genera por sí solo fechas ausentes del cache.
7. Tras finalizar la transacción, el callback llama a `export_reporte_turno_estilo_leyes_finos`, pasando `periodo_inicio=ini_d, periodo_fin=fin_d`.

**Punto de truncamiento:** el paquete asignaba directamente a `df_turno` la lectura hasta corte+1. No se sobrescribe `fin_d` en el callback. Sí: para corte 15/09, prepare+read materializaba el DataFrame sólo hasta el 15 inclusive. El exportador escribe las filas recibidas; no completaba un calendario por recibir `periodo_fin`.

Preview y PDF también usan este paquete; conservan la misma conexión y el constructor permanece fuera de la transacción.

## Cambio acotado

- Se mantiene la lectura del cache hasta el corte validado: ampliar solamente el SELECT no garantiza calendario y puede exponer filas antiguas no refrescadas.
- `_completar_calendario_rto` completa en memoria las fechas posteriores al cierre hasta el fin solicitado, A/B para RTO y una fila diaria para Generador/resumen. No rellena huecos operacionales anteriores al corte.
- Los datos reales posteriores al cierre se dejan ausentes. Se conservan los planes/programas diarios efectivamente devueltos por la fuente. No se inventan planes ausentes del cache.
- Un indicador interno distingue calendario futuro de TMS operacional desconocido. La validación de trazabilidad sigue exigiéndose para turnos operacionales; no se exige trazabilidad para filas calendario futuras.
- Reconst Mod SRR recibe el período solicitado para su encabezado; sus filas siguen siendo los insumos disponibles.
- Cache vacío conserva el comportamiento anterior de “sin datos”; no se disfraza como un reporte operacional válido.

## Causa exacta de NAN

`preparar_df_reporte_turno_excel`, bloque Material, hacía `.astype(str).str.upper().str.strip()`: `np.nan` pasaba a `"nan"` y luego `"NAN"`. El escritor usa `pd.isna`, que devuelve falso para ese texto, por lo que lo imprimía.

`_texto_excel_nullable` utiliza el tipo nullable `string` antes de transformar y elimina los literales nan/none/nat/<na> completos, sin cambiar valores numéricos. Se aplica a Material, Turno, fuentes textuales y objetivos textuales de RTO, y a los campos equivalentes del Generador. Campania/Modulo/Avance siguen siendo numéricos; se conserva su máscara de faltantes para que NaT no se convierta al entero interno de datetime.

El escritor existente convierte los faltantes en celdas vacías, también en merges A/B. No se añade `fillna(0)`. Datos Conciliados no se modifica; se sigue la misma semántica solicitada de faltante → celda vacía.

## Hojas auxiliares: contrato

| Hoja | Clase | Calendario / disponibilidad |
| --- | --- | --- |
| Reporte por Turno | A | Calendario solicitado, A/B; reales futuros vacíos. |
| Generador Reporte | A | Calendario diario solicitado; planes disponibles conservados. |
| Malla -100 (derivada del Generador) | A | Recibe el calendario diario completo; valores sólo disponibles. |
| Clays-CuFe | B | Filas de la fuente Clays; no inventar análisis futuros. Su refresh depende del corte RTO. |
| Trazabilidad Analitos | B | Trazabilidad persistida y cobertura operacional validada; no inventar fuentes/analitos post-corte. |
| Reconst Mod SRR | B (filas), A (encabezado) | Insumos de reconstrucción disponibles; encabezado del período solicitado. |
| Curva Granulométrica | B (filas), A (encabezado) | Consulta independiente a `v_curva_granulometrica_torres_test` por el período solicitado, sin predicado de corte RTO. |

**Curva hasta el 17 vs. RTO hasta el 15:** ambos caminos ya recibían horizontes distintos para sus datos. Curva consulta la vista independiente hasta 01/10 exclusivo y usa el período UI en el encabezado; RTO leía cache hasta 16/09 exclusivo. Datos disponibles en Curva el 16/17 no demuestran cierre operacional de esos días. Esta explicación está comprobada en el código; no se verificó la existencia ni el origen concreto de esas filas en BD o en el archivo descargado, porque no se proporcionó ese XLSX y se prohibió SQL real.

## Validación

- Suite focalizada: 124 tests PASS y 25 subtests PASS, con guardas de conexiones SQL del conftest.
- Casos de integración: callback Excel real, prepare+reads simulados, exportador real y lectura openpyxl. Mes 01–30/09 con corte 15/09 y rango personalizado 04–23/09 con el mismo corte.
- XLSX mensual: fechas 01–30/09, 15 días post-corte con ambos turnos, Material vacío y reales vacíos post-corte; cero literales NAN/nan/None/NaT/<na> en todas las hojas. Material válido anterior al cierre preservado. Plan diario del 17/09 = 300 en el XLSX.
- XLSX personalizado: fechas 04–23/09, 8 días post-corte, mismas garantías.
- Pruebas de None, NaN, NaT, pd.NA y sus literales; encabezado SRR del mes sin inventar reconstrucciones; conservación de ceros existentes y detección de anomalías operacionales de trazabilidad.
- `py_compile` de archivos Python modificados. No se ejecuta SQL real.

Locks/transacciones F4B3A, refresh, Histórico, Factor, materialización del cache y Datos Conciliados intactos. Cambios locales DEV: no despliegue PROD, no actualización de `release/f6_candidate`. Queda pendiente la validación manual del nuevo Excel con datos DEV reales por el usuario.
