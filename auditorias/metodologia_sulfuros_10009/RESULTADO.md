# Ensayo de curvas Sulfuros — caso 10009, 1–7 septiembre 2026

**Cierre neto condicional: 1069.137402000 t Cu**, objetivo oficial F29 1069.137402000 t; residuo 0 t.

- Cohortes jóvenes: P24 (primer riego 15-ago, 23 días al cierre) y P25 (1-sep, 6 días).
- Las 16 pilas maduras conservan exactamente la recuperación observada.
- Se preservan 514 filas del mes anterior.
- Fuente congelada de agosto: serie primaria `Recuperaciones_pad`. Hay 377 filas que difieren de la observación consolidada `lectura_recuperacion`; el freeze no implica igualdad con ambas fuentes.
- Perfil de drenaje joven del run de asignación 2348, multiplicado por λ=0.721442719596; riego y concentraciones medidos sin cambios.
- Referencia de objetivo: caso oficial 10009, solver run 10082. No se escribió SQL ni se publicaron curvas.

## Jóvenes al cierre

- P24: observado 15.226614 %, ensayo 15.847805 % al 7-sep; neto 186.747149 t.
- P25: observado 2.235242 %, ensayo 5.480463 % al 7-sep; neto 283.834824 t.

## Alcance

- El objetivo es solo el Cu neto F29; no se imponen las cuatro igualdades antiguas de caudal y fino.
- Se reescala el perfil diario guardado de las jóvenes con un factor común, conservando su forma temporal relativa; no se calibra una nueva familia de rampa ni un alfa.
- El riego y ambas concentraciones conservan sus valores observados. El caudal de drenaje joven es modelado, no una medición independiente.
- Las curvas maduras conservan exactamente la recuperación observada. Su contribución no usa el proxy de drenaje 0,95 veces el riego.
- El tramo anterior conserva exactamente la serie primaria Recuperaciones_pad; no se afirma igualdad con lectura_recuperacion, que presenta diferencias en agosto.
- Es un ajuste local condicionado al perfil suministrado, no el solver completo ni una corrida oficial.
- La frontera de exactamente 30 días queda protegida; no hay pilas en ese límite en el caso 10009.

El diagnóstico separado `DIAGNOSTICO_CUATRO_COMPONENTES.md` corresponde a exigir además los cuatro objetivos antiguos de caudal/fino. Su incompatibilidad no invalida este ensayo cuyo objetivo es solo F29 neto.

Fuentes revisadas en `fuentes_claude.md`; extracciones SELECT-only y hashes en `resultado_neto_10009.json`. Gráficos: `curvas_ensayo_neto_10009.html`.
