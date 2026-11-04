# Prueba local: caso 10009, 1–7 septiembre 2026

Estado: **infeasible_irrigation_copper_target**. Sin escrituras SQL ni cambios en curvas oficiales.

Edad: días calendario transcurridos desde el primer riego al 7 de septiembre; una edad por pila para toda la ventana.

- Pilas menores de 30 días: P24, P25.
- Pilas mayores de 30 días: 16; deben conservar solo medición durante septiembre.
- Referencia guardada de asignación: run(s) [2348]; objetivo oficial: solver run 10082.
- Filas oficiales de agosto recuperadas como referencia protegida: 1285.

## Primera incompatibilidad

El Cu de riego medido de las pilas maduras suma **267.721995 t**.
El objetivo del motor, normalizado por la razón reconciliado/medido del ancla, es **41.748814 t** para todo Sulfuros.
Las jóvenes tendrían que aportar **-225.973182 t**, un valor negativo inadmisible.
El objetivo componente bruto (41.232979 t) también es inferior a la contribución madura.
Por tanto, no se pueden mantener simultáneamente las mediciones maduras y los cuatro objetivos actuales; no se amplió el grupo a pilas mayores para ocultar el saldo.

## Datos y límites

- No independently measured drainage flow was found in the inspected drainage-source schema. Saved Qdrain is reconciled, not measured. The old 0.95*Qirrig proxy was not substituted for a measurement.
- Young-pile drainage concentrations and saved reconciled drainage are available, but do not certify a measured drainage-flow prerequisite.
- Infeasibility concerns preservation of the four existing official flow/copper constraints. It does not prove infeasibility for a net-copper-only model with different constraints.
- No new curves are published. No full nonlinear solver was run after the necessary feasibility bound failed.
- Allocation tables do not record their originating solver_run_id. The saved case reference and official solver anchor are identified separately.
- Exactly 30 elapsed days is protected from adjustment; the case has no pile on that boundary.
