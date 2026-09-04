# Flujo de topografía

1. `control_reclamo_diario` contiene una fotografía acumulada por fecha/campaña/módulo. El campo usado es `volumen_final_reclamado`; `volumen_diario_m3` se usa para detectar actividad y para construir la línea base histórica, no como fuente del incremento postcorte.
2. `sp_sincronizar_desde_etl` deduplica por fecha, PAD, campaña y módulo conservando el ID mayor. Cruza excepciones aprobadas de `control_medicion_topografia_diaria` y omite módulos no congelados.
3. `topografia_avance.m3_reclamado_acum` conserva el acumulado.
4. `v_topografia_resuelta` obtiene el incremento con `LAG` dentro de la misma campaña/módulo. Un acumulado repetido genera cero; una disminución genera cero y flag de revisión; una medición inválida genera cero; un salto de varios días queda íntegro en la fecha de la siguiente medición.
5. La primera medición descuenta `m3_rotopala_previo`, evitando duplicar el histórico anterior al corte.
6. En ausencia de fila topográfica puede aparecer CV025 preliminar, sujeto a las reglas de apertura y última medición.

