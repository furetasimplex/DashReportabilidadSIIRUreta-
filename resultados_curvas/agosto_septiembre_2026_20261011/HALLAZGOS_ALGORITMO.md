# Hallazgos del algoritmo completo

Agosto de 2026: casos oficiales 5?8. Septiembre: medido sin ajustes,
por elecci?n expl?cita del usuario; no hay Casos oficiales de septiembre.
La recuperaci?n medida llega al 31/08; el riego/qu?mica llega al 30/09.

## Error de conservaci?n de Cu del algoritmo actual

Caso 8, SULFUROS: exceso de 0,63225388376 t Cu al final de paso 7e.
Terra confirm? la causa con lectura del snapshot, sin SQL ni modificaciones:
_absorber_piso_rampa calcula falta_f, pero luego s?lo descuenta agua y escala
el Cu de cada receptora preservando su propia ley. As? no retira la misma
masa que agreg? a la pila en piso. En la operaci?n que genera la diferencia,
P23 recibe 0,80834751696 t Cu extra; las 15 receptoras retiran 0,17609363320 t.
La resta coincide con el exceso medido. El agua s? cierra.

Corregir requiere descontar falta_f expl?citamente con reparto acotado de
fino en receptoras (sin masas negativas), recalcular concentraciones y
reportar infactibilidad si no hay fino suficiente. No se modific? producci?n
para ocultar esta falla en la prueba o los plots.

## Residuo de caudal sin colocar

En SULFUROS, Caso 5:
- Actual: 6.324,50768 m? sin colocar, 153,24360 t Cu asociadas.
- Envolvente: 30.882,23839 m? sin colocar, 671,36608 t Cu asociadas.
Envolvente, Caso 6: 6.605,03319 m? sin colocar, 185,99637 t Cu asociadas.
Estos residuos no prueban inventario f?sico: son magnitudes de balance que
el motor etiqueta inventario y que necesitan explicaci?n/validaci?n externa.

## Transici?n rampa?r?gimen

SULFUROS P22 pasa a r?gimen en Caso 6. Actual: factor final anterior 98,578%
a factor inicial 96,761% (descenso 1,817 puntos). Envolvente: 84,489% a 99%
(salto 14,511 puntos). El techo por edad no garantiza un empalme suave con
el m?todo de r?gimen. Ajustar esa transici?n es una condici?n adicional.

## Resultado de los chequeos

2.420 filas diarias, 64 cierres (8 partes material/Caso ?4 magnitudes ?2
escenarios). 57 cierres directos, 63 contando el residuo expl?cito. El cierre
restante falla por el exceso Cu descrito. Sin caudales negativos, sin superar
0,99 diario, sin superar el techo por edad en el escenario experimental,
sin fechas reconciliadas fuera de agosto y sin diferencias entre sumas
diarias y totales por pila.

El l?mite 10% d?a 1 ?99% d?a30 es ilustrativo. Se empieza con historial de
rampa limpio al 1/08; no se hered? un cierre reconciliado de julio. WIP
reconstruido por fecha final de cada caso, para evitar campa?as futuras.

## Calidad adicional de las curvas

Hay recuperaciones medidas/calculadas por encima de100% en algunas pilas
de ?xidos, visibles sin recorte. El techo por edad no corrige esa calidad
de datos/base acumulada. ?xidos P17 entra como joven por riegos de escala
0,001m?/h aproximadamente: revisar umbral de actividad para no confundir
ruido/caudales residuales con una campa?a nueva. No se alteraron los datos.

Septiembre: 1800 filas medidas; caudal de riego positivo en 1087 filas. Recuperaci?n fuente termina el31/08; no se extrapola a septiembre.
Valores calculados de recuperaci?n >100%: 124 puntos, no pilas distintas.
