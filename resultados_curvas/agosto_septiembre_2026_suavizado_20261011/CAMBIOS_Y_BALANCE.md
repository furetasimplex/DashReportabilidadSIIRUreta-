# Empalme suave y balance de cobre

El salto de SULFUROS/P22 con techo por edad pasó de 14,51 a 0,52 puntos porcentuales.
En la rampa actual, la bajada pasó de 1,82 a 0,63 puntos porcentuales. La continuación
después de los 30 días conserva el factor heredado y limita cambios a 3 puntos
porcentuales por día calendario, como parámetro provisional.

La compensación del piso conserva masa de Cu por separado del volumen. Se corrigió
el exceso de 0,632 t Cu de Caso 8. Cierran los 64 balances de ambos escenarios,
incluyendo los términos pendientes: no equivale a demostrar stock disponible.

`balance_inventario.csv` separa volumen y Cu requerido por PAD y ventana. Positivo
es aporte desde inventario; negativo es retención. El stock inicial mínimo se
calcula como el máximo de aportes netos acumulados bajo esta hipótesis. No mide
la existencia física de ese stock, ni lo asigna a la recuperación de las pilas.
Para validar la explicación física faltan inventarios medidos al inicio y cierre.

El techo por edad sigue siendo experimental. Agosto usa Casos oficiales 5–8;
septiembre muestra riego observado y PLS proxy, sin reconciliación. El ensayo
usa el snapshot local, sin SQL ni guardado de runs.
