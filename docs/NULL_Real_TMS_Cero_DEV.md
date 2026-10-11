# NULL reales con TMS cero: presentación Excel

Regla vigente: TMS exactamente cero + NULL real se presenta como cero.
TMS positivo o nulo conserva NULL vacío; los valores existentes no cambian.
La transformación afecta solamente los dos preparadores de DataFrame en
report_export.py y sus listas explícitas de columnas reales. No incluye
planes/programas ni modifica los DataFrames fuente.

Validación con lecturas de DEV y exportación de septiembre 2026:

- 01/09 B, 02/09 A/B, 03/09 A y 11/09 A/B: TMS cero y analitos
  previamente NULL ahora cero. Las dosis existentes se conservan.
- Diario 02/09 y 11/09: TMS cero y NULL reales presentados como cero.
- 10/09: A=34092.869, B=34091.902, diario=68184.771;
  CuT A=0.531817, B=0.572627; fuentes IMP/IMP. Filas completas iguales.
- El resumen del último día también muestra los ceros preparados del 11/09.
  No cambian acumulados ni planes/programas.
- Las cinco hojas auxiliares conservan valores y propiedades de formato,
  incluida Reconst Mod SRR con su estética normalizada.

Pruebas: 50 aprobadas y 8 subtests aprobados, cero fallos, ejecutando
test_tms_cero_excel, test_analisis_tm_acumulados, test_reconst_mod_srr y
test_orquestacion_reporte_turno con pytest del entorno virtual.
Incluyen explícitamente NULL con TMS positivo en ambos preparadores,
TMS NULL, valores existentes, planes/programas y preservación del origen.

Artefactos: report_export/exports/validacion_null_real_tms_cero/
Analisis_Torres_de_Muestreo_20260901_20260930.xlsx y validacion.json.

No se modificaron SQL, PI, cálculos TMH/TMS, humedad, sal, factor,
representatividad, fórmulas de analitos ni orquestación. Sin promoción a PROD.
