# Refresco de Reporte por Turno en DEV

## Cambio

El mantenedor de apilado recibía el fin calendario solicitado, por lo que
septiembre completo situaba sus siete días de reproceso desde el 24/09.
Ahora recibe la última fecha operacional resoluble dentro del rango.
Preview, Excel y PDF comparten `refrescar_dependencias_reporte_turno_emision`.

`fetch_fecha_corte_apilado_tmh_report` consulta
`inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno`, anterior al
resolver y a Control_Apilado. Exige las cuatro claves CV008/CV108, A/B.
Antes del 01/09/2026 exige fronteras PI completas; desde esa fecha exige
PI utilizable (fronteras completas, delta no negativo y estado CON_VARIACION
o CON_VARIACION_COBERTURA_PARCIAL) o TUM disponible no negativo, incluido cero.
No utiliza el corte SRR ni Control_Apilado como fuente del corte.

Secuencia: corte, apilado, factor, Clays, cache, validación. Apilado usa
fin efectivo inclusivo; factor conserva fin solicitado inclusivo; cache
conserva fin solicitado más un día, exclusivo. Clays recibe fin inclusivo.
El periodo visual y los rangos del generador y lectores no se recortan.

La validación exige claves válidas y únicas, ambos turnos del corte y
Fecha_Actualizacion posterior o igual al reloj SQL capturado antes del
refresco. También verifica presencia del corte y Fecha_Calculo del apilado
en la ventana. No compara numéricamente cada ejecución contra el SP vivo:
eso duplicaría su costo. Se apoya en el reemplazo transaccional del cache
y su DEFAULT SYSDATETIME() existente. Sin corte se aborta antes de escribir.

## Evidencia real

Validación ejecutada el 14/09/2026 en DEV, servidor VPS-5347319-X,
base inventar_SpcHidr. No se promovió a PROD ni se alteraron objetos SQL.

| Dato | Resultado |
| --- | --- |
| Periodo solicitado | 2026-09-01 a 2026-09-30 |
| Corte operacional / fin efectivo | 2026-09-10 |
| Ventana de reproceso | 2026-09-04 a 2026-09-10 |
| Fin exclusivo del cache | 2026-10-01 |
| Filas cache regeneradas | 22 |
| Fecha_Calculo apilado del 10/09 | 2026-09-14 00:30:35.886831 |
| Fecha_Actualizacion cache del 10/09 | 2026-09-14 00:31:00.505366 |
| TMS A del 10/09 | 34092.869 |
| TMS B del 10/09 | 34091.902 |
| Total TMS | 68184.771 |
| Datos_conciliados_of, antes y después | 68184.771 |

Se compararon todas las columnas de ambas filas del 10/09 antes y después:
ningún cambio salvo Fecha_Actualizacion. CuT A/B: 0.531817 / 0.572627;
Stock: 75.63 / 53.81; Mina: 0 / 0; SRR: 24.37 / 46.19; fuentes: IMP.
No se modificaron fórmulas PI, TMH/TMS, humedad, sal, factor, analitos,
representatividad ni sp_reporte_turno_emision_test.

Se generó con los lectores y exportador reales el archivo
`report_export/exports/validacion_orquestacion/Analisis_Torres_de_Muestreo_20260901_20260930.xlsx`.
Comprobaciones numéricas aprobadas: Reporte por Turno I41=34092.869,
I42=34091.902; Generador Reporte H31=68184.771 (fecha C31=10/09/2026).

## Pruebas

Las cinco pruebas nuevas cubren mes en curso, histórico, personalizado,
fin posterior a cobertura, ausencia de corte, orden/contratos de fechas,
cache incompleto/obsoleto/duplicado y uso común por los tres consumidores.

Ejecución ampliada con `venv/Scripts/python.exe -B -m pytest` sobre
test_orquestacion_reporte_turno, test_factor_ajuste_camiones_report,
test_clays_cufe_excel, test_analisis_tm_acumulados,
test_refresco_representatividad y test_datos_conciliados_excel:
49 passed, 1 failed, 8 subtests passed.

El fallo preexistente es
`test_fecha_corte_informa_columnas_estructurales_faltantes`: espera que
el error incluya Camiones_TMS_plan, pero export_to_excel.py emite
"Faltan columnas requeridas para construir el resumen MTD.".
Ambos archivos coinciden con HEAD y no se modificaron en esta tarea.
La ejecución inicial con Python global no tenía pytest; la batería se
ejecutó posteriormente con el entorno virtual del proyecto.
