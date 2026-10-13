# Evaluación del algoritmo completo: agosto–septiembre 2026

Agosto reconciliado con Casos 5–8, ventanas 1–7, 8–14, 15–21, 22–31. Septiembre medido sin ajustes, elegido por el usuario al confirmar que no hay Casos oficiales. Sin reconciliación de julio; estado inicial limpio, con edad desde primer riego real. Sin escrituras SQL.

WIP reconstruido AS OF cada Caso; no usa una campaña posterior. Se ejecuta reconcile_flowsheet real incluyendo caudal, Cu fino, distribución diaria, rampa, reparto de residuos e inventario declarado. La envolvente sustituye solo el ajuste de rampa en el proceso de prueba. Motor productivo corregido: conservación de Cu y continuación suave después de los 30 días; el techo por edad sigue siendo experimental.

## Diagnóstico

```json
{
  "fecha_evaluacion": "2026-10-11T16:14:25.139819",
  "perfil": "dev_snapshot",
  "sql_selects": 0,
  "filas_diarias": 2420,
  "violaciones_techo_general": 0,
  "violaciones_techo_edad": 0,
  "caudales_negativos": 0,
  "fechas_fuera_agosto": 0,
  "errores_suma_diaria_pila": 0,
  "fallos_continuidad": 0,
  "cierres_sin_inventario": 56,
  "cierres_totales": 64,
  "cierres_con_inventario": 64,
  "transiciones_regimen": 2,
  "salto_max_transicion_regimen": 0.006272140955645544
}
```

43 pilas reconciliadas; 4 jóvenes; 0 con CuTf de campaña anterior. No recortar recuperación a 100% para ocultar anomalías.

## Cierres no directos

escenario,caso_id,material,magnitud,objetivo,entregado,residuo,inventario_declarado,objetivo_pls_sin_recorte,ancla_pls_recortada,cierre_sin_inventario,cierre_con_inventario
actual,5,SULFUROS,q_pls_final,627221.5484002368,620897.0407193374,6324.50768089926,6324.507680899218,627221.5484002368,False,False,True
actual,5,SULFUROS,fino_pls_final,2615.982055922956,2462.738455637375,153.2436002855811,153.24360028558087,,False,False,True
envolvente,5,SULFUROS,q_pls_final,627221.5484002368,596339.3100152233,30882.238385013363,30882.238385013283,627221.5484002368,False,False,True
envolvente,5,SULFUROS,fino_pls_final,2615.982055922956,1944.615971194509,671.3660847284472,671.3660847284468,,False,False,True
envolvente,6,SULFUROS,q_pls_final,636211.4729108824,620881.1725190636,15330.30039181898,15330.300391818952,636211.4729108824,False,False,True
envolvente,6,SULFUROS,fino_pls_final,2885.258516378043,2520.8384269923995,364.4200893856434,364.4200893856431,,False,False,True
envolvente,7,SULFUROS,q_pls_final,551377.5013416386,549644.4318812016,1733.06946043708,1733.06946043708,551377.5013416386,False,False,True
envolvente,7,SULFUROS,fino_pls_final,1483.625762412447,1458.776279690592,24.849482721855345,24.849482721855424,,False,False,True


Los objetivos PLS usados pueden tener recorte por el techo del PAD; también se conserva objetivo_pls_sin_recorte. Los objetivos son ratios oficiales aplicados al universo de pilas del motor, no igualdad automática a todos los flujos del Caso. El residuo declarado no prueba existencia de inventario físico. No se reconcilia producción de planta.

Curvas desde último ciclo medido por pila hasta 31/08. Las series calculadas usan fino diario del run de prueba (0,024 × suma(q·C) en t Cu) y CuTf de WIP AS OF agosto; no se mezclan otros runs del historial SQL. Si no existe lectura previa se usa primera lectura del tramo como base provisional. La edad hidráulica usa primer riego real y puede diferir del inicio del ciclo medido.

Caudales diarios m³/h; cierres de caudal m³ (=24 × suma diaria), fino t Cu (=0,024 × suma q·C). Ver detalle_diario.csv, cierres_por_caso_pad.csv, continuidad_rampas.csv, medido_agosto_septiembre.csv, campanas_y_calidad.csv y curvas_recuperacion.csv. Septiembre no tiene curvas reconciliadas ni recuperación medida disponible.

Las diferencias en transición a régimen se registran sin interpretar un descenso entre semanas como error de una pila madura. La comprobación de continuidad de rampa considera edad y omite reinicios de campaña. Revisar transición_regimen y delta_factor en continuidad_rampas.csv.
