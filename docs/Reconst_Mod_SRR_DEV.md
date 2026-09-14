# Reconst Mod SRR — implementación DEV

Se agrega una hoja independiente al final de Análisis TM. Los bloques M:AL
contienen los orígenes existentes y los valores SRR/MB leídos de SQL.
D:I contienen el TMH neto por turno según la metodología definitiva validada:
total publicado por Datos Conciliados, TM2 con factor y descuento proporcional
de sal, y TM1 por diferencia. BD Ton no se consulta para esta hoja.

## Archivos y funciones

| Archivo | Cambio |
|---|---|
| `report_export/report_export.py` | Nuevas `_normalizar_claves_reconst_srr`, `fetch_reconstitucion_srr_report`, `_calcular_tmh_reconst_srr` y `_agregar_hoja_reconst_mod_srr`. Se amplía `export_reporte_turno_estilo_leyes_finos` con un argumento opcional al final y una llamada condicional. |
| `report_export/callbacks/reportabilidad_cb.py` | `exportar_excel`: import, fetch independiente con fin exclusivo, tiempo/filas y keyword SRR. |
| `report_export/tests/test_reconst_mod_srr.py` | Pruebas de integridad, NULL, turnos parciales, copias y compatibilidad. |
| `scripts/validate_reconst_mod_srr_dev.py` | Exportación y regresión reproducible en DEV contra el baseline del usuario. |
| `scripts/inspect_reconst_srr_tmh_dev.py` | Inspección de fuentes operacionales y cuadratura con Datos Conciliados; solo SELECT. |
| `report_export/exports/Analisis_Torres_de_Muestreo_20260801_20260831.xlsx` | Entregable generado. |

El motor real del exportador es XlsxWriter. Se mantiene este motor para agregar
la hoja antes del cierre del workbook y evitar reserializar con openpyxl las
hojas, gráficos y valores cacheados existentes. Openpyxl se usa para verificar
el resultado. Esta es la adaptación del ejemplo `create_sheet` a la arquitectura
existente: el exportador siempre crea un workbook nuevo y agrega SRR una sola vez.
No se cambia su hoja activa, selección ni visibilidad.

No se modificaron funciones SQL, tablas, conexiones, SPs, mantenimiento ni rutas PDF.
El parámetro `df_reconst_srr=None` se añade después de `periodo_fin`; todas las
posiciones de argumentos anteriores conservan su significado.

## Fuente SQL de cada campo

Todos los objetos pertenecen al esquema `inventar_SpcHidr`.

| Campo / columnas Excel | Objeto SQL y columna |
|---|---|
| Fecha / C; Día / L | `fn_reconstitucion_srr_turno_emision_test.Fecha`; día calendario derivado de Fecha |
| STOCK A/B / M:N | `reporte_turno_cache_emision_test.STOCK`, mediante `fetch_reporte_turno_cache_emision` y copia local de `df_turno` |
| MINA A/B / O:P | `reporte_turno_cache_emision_test.MINA`, misma copia |
| SRR A/B / Q:R | `reporte_turno_cache_emision_test.SRR`, misma copia |
| SRR TMS A/B / S:T | `fn_reconstitucion_srr_turno_emision_test.SRR_TMS_Turno` |
| CuT SRR / U:V | `fn_reconstitucion_srr_turno_emision_test.CuT_SRR` |
| CuS SRR / W:X | `fn_reconstitucion_srr_turno_emision_test.CuS_SRR` |
| ClayBeta SRR / Y:Z | `fn_reconstitucion_srr_turno_emision_test.ClayBeta_SRR` — MB directo |
| Malla100 SRR / AA:AB | `fn_reconstitucion_srr_turno_emision_test.Malla100_SRR` |
| CO3 SRR / AC:AD | `fn_reconstitucion_srr_turno_emision_test.CO3_SRR` |
| Recuperación SRR / AE:AF | `fn_reconstitucion_srr_turno_emision_test.Recuperacion_SRR` — MB directo |
| CuT MinaStock / AH | `fn_reconstitucion_srr_emision_test.CuT_MinaStock` |
| CuS MinaStock / AI | `fn_reconstitucion_srr_emision_test.CuS_MinaStock` |
| ClayBeta MinaStock / AJ | `fn_reconstitucion_srr_emision_test.ClayBeta_MinaStock` |
| Malla100 MinaStock / AK | `fn_reconstitucion_srr_emision_test.Malla100_MinaStock` |
| CO3 MinaStock / AL | `fn_reconstitucion_srr_emision_test.CO3_MinaStock` |
| Total TMH A/B / D:E | `Datos_conciliados_of.Apilado_TMH_turno_A/B`, sin recalcular ni ajustar |
| Sal por turno (insumo interno) | `Datos_conciliados_of.Sal_turno_A`, `Sal_Turno_B` |
| TMH bruto por correa (insumo interno) | `v_datos_apilado_tmh_v2.TMH_CV008_A/B` y `TMH_CV108_A/B` |
| Factor (insumo interno) | `v_ajuste_camiones_emision_test.Factor_Aplicacion_Reportes` |
| Tambor 2 TMH A/B / H:I | `CV108 * Factor_Aplicacion_Reportes - Sal_Turno * CV108 / (CV008 + CV108)`, calculado únicamente en `_calcular_tmh_reconst_srr` |
| Tambor 1 TMH A/B / F:G | Total publicado por Datos Conciliados − Tambor 2 final |

El fetch nuevo une las TVF y los tres objetos TMH con `LEFT JOIN` por Fecha, usando `_get_engine`,
context manager, `pd.read_sql`, `_sa_text` y parámetros `:start/:end`, igual que
los fetches de emisión. Agosto usa `[2026-08-01, 2026-09-01)`.
Participación, factor de sensibilidad y flags se conservan en el DataFrame interno;
no anulan leyes ni alteran el bloque principal.

## Integridad

- Normaliza Fecha y A/B sobre copias; acepta TA/TB con la utilidad existente.
- Rechaza duplicados Fecha/Turno y claves inválidas; admite rangos parciales.
- Rechaza columnas SQL requeridas ausentes y discrepancias A/B en los cinco
  campos diarios MB y `SRR_TMS_Dia`, incluyendo discrepancias NULL/valor.
- Rechaza insumos TMH ausentes/no finitos. Con bruto, sal y total todos cero,
  produce TM1=TM2=0; con bruto cero y sal o total distinto de cero, lanza error
  explícito. No inventa factor o sal cuando falta el dato.
- Valida `abs(TM1 + TM2 - Total) <= 0.001 TMH` sin redondear los insumos.
- Escribe valores sin recalcular leyes ni aplicar `fillna(0)` al dataset SRR.
- Conserva las leyes diarias cuando un turno tiene cero TMS; deja celdas vacías
  cuando SQL devuelve NULL. Los orígenes conservan escala 0–100 sin recalcularse.
- Sin DataFrame SRR, o con uno vacío, omite la hoja y conserva el comportamiento
  anterior. El callback registra el rango y número de registros, también si son cero.

## TMH: metodología definitiva

La fuente final autoritativa es Datos Conciliados, según la metodología
confirmada por el usuario para agosto de 2026. Los brutos operacionales incluyen
sal; no se escriben directamente en D:I.

Se trazó la fuente operacional:
`tot_TM` → `sp_mantiene_apilado_tmh_v2_test` → `Control_Apilado_TMH_v2_test`
→ `v_datos_apilado_tmh_v2` → consumidor `sp_reporte_turno_emision_test`.
La definición viva en DEV toma totalizadores a las 08:00, 20:00 y 08:00 del día
siguiente, calcula diferencias y aplica la validación existente de actividad.
CV008 corresponde a TM1 y CV108 a TM2. Para cada turno:

```text
TotalBruto = CV008 + CV108
Sal_TM2 = Sal_Turno * CV108 / TotalBruto
TM2_Final = CV108 * Factor_Aplicacion_Reportes - Sal_TM2
TM1_Final = Total_Datos_Conciliados - TM2_Final
```

La sal no se multiplica nuevamente por el factor. El total publicado no se
sustituye por la suma bruta ni por `TMH_Total_Con_Factor_A/B` de
`v_apilado_tms_con_sal_srr_reporte_test`. La regla residual de TM1 garantiza
la cuadratura con el total autoritativo incluso cuando difiere de un cálculo
paralelo del total. No se cambian métodos de representatividad, objetos SQL
ni valores almacenados en Datos Conciliados.

Se revisan los 31 días y ambos turnos, incluidos los 12 días con factor distinto
de 1. El detalle de fuentes queda en `tmh_metodologia_definitiva.csv` y el
resultado máximo de cuadratura en `resultado.json`, dentro de las evidencias.

## Pruebas y regresión

Baseline confirmado por el usuario:
`C:/Users/nimun/Downloads/Analisis_Torres_de_Muestreo_20260801_20260831 (1).xlsx`.
SHA-256: `7dfc456e64a9bd711084fff58d7bc011d23238210815b66da58a48269e7e8c7d`.
El archivo se abre solo para lectura y su hash se comprueba al terminar.

```powershell
.\venv\Scripts\python.exe -m pytest report_export/tests/test_reconst_mod_srr.py report_export/tests/test_curva_granulometrica_excel.py report_export/tests/test_trazabilidad_analitos_excel.py report_export/tests/test_clays_cufe_excel.py report_export/tests/test_analisis_tm_acumulados.py -q
python -m scripts.validate_reconst_mod_srr_dev verify
python -m scripts.inspect_reconst_srr_tmh_dev
git diff --check
```

Resultado: 35 pruebas aprobadas; regresión DEV aprobada con y sin SRR.
Cuadratura máxima TMH en los 62 turnos: `1.4551915228366852e-11 TMH`, inferior
a `0.001 TMH`. Los totales D/E coinciden con Datos Conciliados; se cubren los
12 días con factor distinto de 1. Tiempo del fetch completo: 0,29 s.
Se comparan nombres, orden, dimensiones, valores, fórmulas, valores cacheados,
merges, estilos resueltos, anchos/altos, filas/columnas ocultas, paneles congelados,
visibilidad, selección, configuración de impresión y los gráficos/dibujos/imágenes
originales. Las seis hojas existentes permanecen iguales. Se excluye únicamente
la nueva hoja de las comparaciones; no se usan timestamps ZIP como criterio.

| Hoja existente | Filas × columnas | Resultado |
|---|---:|---|
| Reporte por Turno | 86 × 42 | Sin cambios |
| Generador Reporte | 54 × 42 | Sin cambios |
| Malla #100 | 1 × 1, hoja de gráfico | Sin cambios |
| Curva Granulométrica | 70 × 21 | Sin cambios |
| Clays-CuFe | 126 × 11 | Sin cambios |
| Trazabilidad Analitos | 131 × 31 | Sin cambios |

SRR: 62 registros únicos, 31 fechas. Verificados los valores
solicitados del 01-08, el MB diario, turnos de masa cero del 08/21, NULL del 22,
alta sensibilidad del 21/23 y presencia del 31. Se comparan las masas/leyes SRR
y los orígenes contra sus DataFrames, y se verifica que estos no se mutan.
La regresión también contrasta D/E directamente con Datos Conciliados, calcula
TM2 independientemente desde sus insumos y comprueba F+H=D / G+I=E con tolerancia
máxima 0.001. Se comparan C y L:AL contra el Excel previo a completar TMH.
La hoja se revisó visualmente en Excel. No contiene fórmulas ni vínculos externos.
Las evidencias locales quedan en `report_export/exports/reconst_mod_srr_validation`.

No se ejecutó una conversión PDF completa: se comprobó la firma compatible y la
generación histórica sin SRR, que es la ruta usada por PDF. D:I están implementadas.
Una regeneración futura puede reflejar cambios
posteriores en los datos de DEV; la regresión corresponde a los datos verificados.

## Todas las llamadas encontradas

La búsqueda global incluye scripts, tests, respaldos y versiones antiguas
(excluye el entorno virtual y `.git`). Había 18 llamadas previas; se agregan
dos en la validación nueva y una en su prueba. No se modifica ninguna llamada
legacy/PDF.

| Archivo | Ubicación de llamadas |
|---|---|
| `report_export/callbacks/reportabilidad_cb.py` | `exportar_excel` y ruta PDF |
| `report_export/callbacks/reportabilidad_cb_backup.py` | línea 1521 |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v6.py` | línea 2849 |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v7.py` | línea 2858 |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v8.py` | línea 2990 |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v9.py` | línea 3039 |
| `versiones_prueba/reportabilidad_cb_hojas_mensuales_v10.py` | línea 3054 |
| `docs/migrations/dev_clays_cufe_fuente_conciliacion/export_and_verify_excel_dev.py` | línea 47 |
| `scripts/validate_analisis_tm_acumulados.py` | línea 32 |
| `scripts/validate_curva_granulometrica_dev.py` | líneas 46 y 115 |
| `report_export/tests/test_analisis_tm_acumulados.py` | línea 64 |
| `report_export/tests/test_clays_cufe_excel.py` | líneas 67 y 95 |
| `report_export/tests/test_curva_granulometrica_excel.py` | líneas 30 y 66 |
| `report_export/tests/test_trazabilidad_analitos_excel.py` | línea 85 |
| `scripts/validate_reconst_mod_srr_dev.py` | `main`: exportación con SRR y exportación histórica sin SRR |
| `report_export/tests/test_reconst_mod_srr.py` | helper `export`, línea 39 |

El diff de los dos archivos productivos se adjunta como `Reconst_Mod_SRR_DEV.diff`.
