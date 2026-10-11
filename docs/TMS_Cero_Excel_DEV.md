# Ceros válidos en Análisis TM

> Registro histórico: la regla de vaciar analitos sin masa fue reemplazada
> por la regla definitiva documentada en Valores_SQL_Excel_DEV.md.

Cambio limitado a `preparar_df_reporte_turno_excel` y
`preparar_df_generador_reporte_excel` en report_export/report_export.py.
El TMS real se excluye de las listas que vacían variables dependientes
del apilado. Los rellenos numéricos existentes respetan ahora los NULL
del TMS. El relleno final por turno respeta además los analitos vaciados
por ausencia de apilado. No se cambian planes ni fórmulas de negocio.

Validación del 14/09/2026 mediante lectura de DEV y generación con los
lectores y exportador reales, sin ejecutar refrescos ni modificar SQL.

| Fecha septiembre 2026 | TMS A | TMS B | TMS diario |
| --- | --- | --- | --- |
| 02 | 0 | 0 | 0 |
| 10 | 34092.869 | 34091.902 | 68184.771 |
| 11 | 0 | 0 | 0 |

XLSX: report_export/exports/validacion_tms_cero/Analisis_Torres_de_Muestreo_20260901_20260930.xlsx.
Reporte por Turno: I25/I26=0, I43/I44=0; I41/I42 conservan los positivos.
Generador Reporte: H23=0, H32=0, H31=68184.771.
El formato numérico #,##0 muestra el cero; no se modificó el formato.
Se verificaron celdas vacías de analitos, Stock/Mina/SRR y dosis ideal
en ambas hojas para los días 02 y 11. CuT del 10: 0.531817 y 0.572627.
Datos_conciliados_of devuelve respectivamente 0, 68184.771 y 0.

Pruebas: `venv/Scripts/python.exe -B -m pytest` con
test_tms_cero_excel.py, test_analisis_tm_acumulados.py y
test_orquestacion_reporte_turno.py: 21 aprobadas, 8 subtests aprobados,
cero fallos finales. Incluye cero, NULL, ambos turnos, días 02/11,
producción del 10, fuentes IMP y preservación del DataFrame original.
No se ejecutó la batería completa; el fallo preexistente de mensaje
de Datos Conciliados documentado en la tarea anterior no fue reevaluado.

No se modificaron SQL, PI, cálculos TMH/TMS, humedad, sal, factor,
representatividad, fórmulas de analitos ni la orquestación corregida.
No se promovió a PROD.
