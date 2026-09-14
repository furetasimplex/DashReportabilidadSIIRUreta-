# Preservación de valores SQL en Excel (DEV)

> Registro histórico. La solicitud posterior introduce una excepción de
> presentación: los NULL del bloque REAL se muestran como cero únicamente
> cuando el TMS es cero. Véase NULL_Real_TMS_Cero_DEV.md.

Regla definitiva: cero permanece cero, NULL permanece vacío y los valores
se conservan, sin inferir ausencia de información desde el TMS.

En preparar_df_reporte_turno_excel y preparar_df_generador_reporte_excel
se eliminaron las limpiezas por TMS y los rellenos numéricos globales.
También se retiraron las limpiezas equivalentes de planes/programas
para conservar sus ceros y NULL. Se mantienen las conversiones visuales
existentes de Avance, material, campaña y fechas.

Validación con datos reales de DEV el 14/09/2026: 726 comparaciones entre
valores de los lectores SQL y XLSX, incluyendo 72 ceros y 102 NULL.
Se interpretaron las celdas combinadas mediante su celda superior.
Se contrastó con el archivo previo a la limpieza de analitos, ubicado en
exports/validacion_orquestacion: ningún cero de origen se perdió como vacío
en las columnas reales comparadas. Los NULL antes rellenados con cero
ahora permanecen vacíos conforme a la regla definitiva.

| Fecha/turno | TMS | Stock | Mina | SRR | CuT | FeS |
| --- | --- | --- | --- | --- | --- | --- |
| 01/09 B | 0 | 0 | 0 | 0 | NULL | NULL |
| 02/09 A y B | 0 | 0 | 0 | 0 | NULL | NULL |
| 03/09 A | 0 | 0 | 0 | 0 | NULL | NULL |
| 11/09 A y B | 0 | 0 | 0 | 0 | NULL | NULL |
| 10/09 A | 34092.869 | 75.63 | 0 | 24.37 | 0.531817 | 0.079342 |
| 10/09 B | 34091.902 | 53.81 | 0 | 46.19 | 0.572627 | 0.079341 |

TMS diario del 02/09 y 11/09: 0. TMS diario del 10/09: 68184.771.
Fuentes química/física del 10/09: IMP/IMP en ambos turnos.

Artefactos en report_export/exports/validacion_valores_sql:
Analisis_Torres_de_Muestreo_20260901_20260930.xlsx y validacion.json.

Pruebas ejecutadas con venv/Scripts/python.exe -B -m pytest:
test_tms_cero_excel.py, test_analisis_tm_acumulados.py,
test_orquestacion_reporte_turno.py. Resultado: 31 aprobadas,
8 subtests aprobados, cero fallos. Incluye int/float/Decimal cero, NULL,
valores positivos con TMS cero, planes/programas, día positivo y orquestación.
No se ejecutó la batería completa.

No se modificaron SQL ni la orquestación, PI, cálculos TMH/TMS,
humedad, sal, factor, representatividad ni fórmulas de analitos o
Stock/Mina/SRR. Solo presentación Python. Sin promoción a PROD.
