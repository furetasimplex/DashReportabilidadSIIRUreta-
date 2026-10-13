# Diagnóstico de recuperación P23 y P24 — agosto 2026

La desviación persiste en el snapshot suavizado. No es la falla de conservación
de 0,632 t Cu que se corrigió en el piso de rampa.

La serie naranja integra el Cu neto diario reconciliado desde una lectura base,
dividido por CuTf. La gris viene directamente de Recuperaciones_pad. La reconstrucción
hidráulica sin ajuste ya queda por encima de la gris: las dos fuentes no constituyen
una base equivalente demostrada. El PLS crudo por pila es proxy 0,95 × riego, no sensor.
No es correcto atribuir toda esta separación a la reconciliación.

pila,medida_pct,sin_ajuste_hidraulico_pct,reconciliada_pct,proporcion_reconciliada_medida,CuTf_t
P23,28.76790858310629,46.42678909340182,43.337961601852165,1.5064689696386901,5026.454539774864
P24,11.745198072025302,24.366833033684774,19.02207499841615,1.619561873862554,4551.913709795878

Además, Caso 6 P23 recibe 1,2746 veces su fino PLS de referencia con 0,9118 veces su
Q PLS de referencia: ley media de 20,15 a 28,16 g/L. El reparto por fino de referencia
no acota las concentraciones resultantes después de la rampa.

Acciones metodológicas necesarias:
- Verificar que Recuperaciones_pad, CuTf y el balance diario usan la misma campaña,
  intervalo, unidades y convención de extracción neta.
- Mostrar la reconstrucción hidráulica cruda como diagnóstico separado de la curva
  medida; una identidad de ancla no garantiza igualdad entre esas fuentes.
- Acotar el reparto de Cu según caudal drenado y concentración o extracción admisible
  validada; el Cu no asignable queda como balance de inventario independiente.
- No ajustar un techo arbitrario para lograr parecido visual ni recortar a 100%.

La primera lectura se usa como base y también se integra el primer día; ese posible
solapamiento requiere resolver la convención del acumulado, pero su tamaño (0,03 pp
en P23 y 0,15 pp en P24) no explica diferencias de 14,57 y 7,28 pp al cierre.

No se modificó el algoritmo de Cu para forzar concordancia. Un cambio a “medido más
delta de Cu” exige decidir qué fuente es referencia y validar la reconstrucción;
aplicarlo al techo por edad actual puede producir recuperación negativa en P24.
