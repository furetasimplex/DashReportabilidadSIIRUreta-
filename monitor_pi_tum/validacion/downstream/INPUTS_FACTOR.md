# Inputs y salidas del mantenedor del factor — 10-09

Izquierda: fila persistida. Derecha: mantenedor SQL simulado con histórico refrescado desde su vista vigente. Todas las columnas conservadas. El SP puro ejecutado con histórico real vuelve a leer 71793: evidencia en evidencia/calculo_factor_actual.json.

|Columna|Persistido|Con histórico actualizado|
|---|---|---|
|Fecha|2026-09-10|2026-09-10|
|Limite_KOM_TMH_Viaje|380.0|380.0|
|Limite_CAT_TMH_Viaje|265.0|265.0|
|Apilado_TMH_Bruto_Original|71793.0|83630.0|
|Apilado_TMH_Neto_Original|70553.94|82390.94|
|Sal_TMH_Dia|1239.06|1239.06|
|Humedad_Pct|3.3|3.3|
|Apilado_TMS_Bruto_Sin_Ajuste|69423.83099999999|80870.20999999999|
|Apilado_TMS_Neto_Sin_Ajuste|68184.771|79631.15|
|Inventario_Chancado_TMS_Actual|7858.983595340942|7858.983595340942|
|Inventario_Chancado_TMS_Anterior|7858.983595340942|7858.983595340942|
|Delta_Inventario_Chancado_TMS|0.0|0.0|
|Flag_Continuidad_Diaria|True|True|
|Flag_Inventario_Valido|True|True|
|Flag_Humedad_Valida|True|True|
|SRR_TMS_Turno_A|8307.0|8307.0|
|SRR_TMS_Turno_B|15746.0|15746.0|
|SRR_TMS_Dia|24053.0|24053.0|
|Mineral_Chancado_TMS_Sin_Ajuste|69423.83099999999|80870.20999999999|
|Chancado_TMS_Sin_Ajuste|44131.77099999999|55578.149999999994|
|Chancado_TMH_Sin_Ajuste|45637.8190279214|57474.8190279214|
|Produccion_KOM_TMH|53907.0|53907.0|
|Produccion_CAT_TMH|0.0|0.0|
|Dato_Mina_TMH|53907.0|53907.0|
|Vueltas_KOM|151.0|151.0|
|Vueltas_CAT|0.0|0.0|
|Participacion_KOM|1.0|1.0|
|Participacion_CAT|0.0|0.0|
|Chancado_KOM_TMH_Sin_Ajuste|45637.8190279214|57474.8190279214|
|Chancado_CAT_TMH_Sin_Ajuste|0.0|0.0|
|Carga_KOM_TMH_Viaje_Sin_Ajuste|302.23721210543977|380.627940582261|
|Carga_CAT_TMH_Viaje_Sin_Ajuste|NULL|NULL|
|KOM_TMH_Corregido|45637.8190279214|57380.0|
|CAT_TMH_Corregido|0.0|0.0|
|Chancado_TMH_Corregido_Total|45637.8190279214|57380.0|
|Factor_Ajuste|1.0|0.9983502509529375|
|Flag_Factor_Ajuste_Valido|True|True|
|Estado_Calculo|OK_SIN_AJUSTE|OK_AJUSTE_KOM|
|Apilado_TMH_Bruto_Ajustado|71793.0|83492.03148719417|
|Apilado_TMS_Bruto_Ajustado|69423.83099999999|80736.79444811675|
|Mineral_Chancado_TMS_Ajustado|69423.83099999999|80736.79444811675|
|Chancado_TMS_Ajustado|44131.77099999999|55444.73444811675|
|Apilado_TMH_Neto_Ajustado|70553.94|82252.97148719417|
|Apilado_TMS_Neto_Ajustado|68184.771|79497.73444811675|
|Cantidad_Registros_Originales|9|9|
|Cantidad_Registros_Validos|9|9|
|Cantidad_Duplicados_Eliminados|0|0|
|Check_TMH_Bruto|0.0|0.0|
|Check_Produccion_Flotas|0.0|0.0|
|Metodo|BALANCE_INVENTARIO_CAMIONES_V2|BALANCE_INVENTARIO_CAMIONES_V2|
|Fuente_Camiones|MOV_CAM_DEDUP_OPERACIONAL|MOV_CAM_DEDUP_OPERACIONAL|
|Fecha_Calculo|2026-09-14 10:20:18.481688|2026-09-19 17:34:42.914096|

