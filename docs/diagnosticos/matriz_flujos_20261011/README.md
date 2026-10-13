# Matriz, fuentes de flujos y SP vigente — 11/10/2026

Se revisó el XLSX indicado por el usuario sin modificarlo. Contiene tanto la
numeración legada (BALANCE y AUDITORIA_SP_120) como un bloque M6 en NUEVO FLOWSHET.
No tratar todas sus hojas como si correspondieran al mismo modelo.

La comparación completa de nombres, unidades y fuentes textuales abarca las 122
filas M6 de la hoja frente a 125 flujos del catálogo instalado. Faltan en la hoja
F123 (suma de aglomerado a PAD óxidos), F124 (suma de aglomerado a PAD sulfuros)
y F125 (inventario piscina refino óxidos). Se encontraron 3 diferencias literales
de nombre (F74, F117 y F122). Hay 21 filas sin fuente ni dependencia documentada;
esto es un vacío de la hoja, no prueba de ausencia de fuente en la BD.

## SP identificada y vigencia

La nueva SP es `inventar_SpcHidr.sp_calcular_balance_flujos_modelo6_v2`.
Se encontró un snapshot histórico en
`docs/diagnosticos/drenaje_operacional_20261002/sp_calcular_balance_flujos_modelo6_v2.snapshot.sql`.
Se contrastó con SELECT de metadatos de DEV: la definición instalada fue modificada
el 08/10/2026 09:54:35.737 (marca de sys.procedures, sin conversión de zona horaria).
Esta carpeta conserva la definición instalada consultada, no un script de despliegue.
No se ejecutó ninguna SP ni se realizaron DDL/DML.

## Versiones que no deben mezclarse

| Papel | Modelo 1, 120 flujos | Modelo 2, propuesta M6/125 |
|---|---|---|
| Riego óxidos por fuente | F39 + F41 + F46 | F70 + F60 + F81 |
| PLS óxidos | F48 | F44 |
| Riego sulfuros | F44 + F45 | F72 + F66 |
| PLS sulfuros y bleed | F50 + F49 | F47 + F48 |

El modelo nuevo se llama `hidrometalurgia_125_v2` y tiene ID 2 en esta BD;
el nombre M6 de la SP no significa modelo_id=6. F70 es el padre de los componentes
F70_PRINCIPAL y F70_ADICIONAL: sumar padre e hijos duplica el refino.
En la SP nueva el riego usa `v_riego_parcelas_origen` y `conc_cu`, integrando caudal
por duración real. Convierte g/L a % dividiendo por 10 y usa densidad 1 t/m³.
F44 se calcula restando evaporación F68, no aplicando de nuevo 0,95.

F44 cambia de refino hacia PAD sulfuros a PLS de PAD óxidos. F50 cambia de PLS
de sulfuros a inventario de solución. El lector `CASO_FLUJOS` del dashboard
solo corresponde al modelo 1; antes de usar runs del modelo 2 hay que seleccionar
el mapeo por modelo de los resultados y comprobar origen/destino, no solo código F.
Los retornos ILS son salidas distintas del PLS y se deben mostrar separados;
no sumarlos indiscriminadamente como PLS por parecer flujos de drenaje.

## Qué explica las curvas de agosto

Se consultaron los oficiales actuales: casos 5,6,7,8, runs 46,66,50,47,
todos del modelo 1 y con origen `sp_calcular_balance_flujos`.
No reinterpretar esas filas con los códigos nuevos. Septiembre tiene casos de
modelos 1 y 2, sin run oficial; sigue sin reconciliación en los gráficos.

Caso 6, sulfuros: respecto a lo medido, el ancla aplica factor 0,977769 al riego,
0,990495 al PLS, 2,545644 al Cu fino de riego y 1,369179 al Cu fino de PLS.
La elevación de ley puede venir del propio balance reconciliado. La separación
entre porcentajes medidos e integrados no demuestra por sí sola una mala
distribución por pila; además el cálculo hidráulico crudo ya diverge de la curva
medida. No se cambió el reparto para forzar parecido visual.

Criterio indicado por el usuario: si la diferencia viene de los cambios que
entrega el reconciliador de flujos, la metodología se mantiene. Validar la
aplicación de sus anclas y la conservación de balances, sin imponer que la
curva reconciliada coincida con la medida ni añadir cotas arbitrarias de ley.

Ver `anclas_oficiales_agosto.csv`, el cruce de Luna y el diagnóstico
`resultados_curvas/diagnostico_p23_p24_20261011`. Se preservaron el motor y el XLSX.
