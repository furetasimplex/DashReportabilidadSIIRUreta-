# Avance: reporte oficial, reconstitución recalibrada y curvas maduras/nuevas

Rama: `claude/great-hopper-63z6wb`. Este archivo se actualiza en cada hito.

## Decisiones acordadas (5-nov-2026)

- Reporte: replicar solo las **15 hojas visibles** del oficial
  (`Reporte_Recuperaciones_12_de_Octubre_2026.xlsx`); se excluyen
  `Budget FY16 y Q1`, `Rec Ox_gr`, `Rec Sulfuro_gr`. Las series de gráficos que
  dependen de hojas ocultas se **omiten**.
- Dump: factor de drenaje global F = Σ drenaje reconciliado / Σ riego
  reconciliado del dump (flujos); drenaje diario = F × riego reconciliado.
- Reconstitución: metodología `docs/METODOLOGIA_RECONSTITUCION_DENSIDAD_RECALIBRADA.md`
  (densidad húmeda recalibrada por PAD/campaña y asignación secuencial).
  Referencia M&R: `test_fixtures/referencias/Control_MR_septiembre.xlsx`.
- Método maduras/nuevas: resultado **local** (sin escribir en SQL).
- Orden: parte 3 → parte 1; parte 2 en paralelo.

## Validación previa del Control M&R (hoja Septiembre, campaña 11, parcela 28)

| Comprobación | Resultado |
|---|---|
| Suma TMH por turno = meta columna R por módulo | Cumple (131–135) |
| Traspaso de residual dentro del turno | Cumple (último + primero ≈ turno completo) |
| Columna S | Fracción del turno de traspaso que queda en el módulo (0,6437 = 26.741/41.543); último abierto = 1 |
| TMS no recalculada con humedad | Cumple (≈20 t/turno de diferencia con TMH·(1−3,3 %)) |
| Cu fino columna R = Σ TMS·CuT/100 | Cumple exacto |

Diferencias esperadas con la metodología: la meta M&R viene de `Volumen-Ton`
externo (densidad M&R) y humedad fija 3,3 %; la metodología usa densidad
recalibrada y humedad resuelta desde DB.

## Hitos

| # | Hito | Estado |
|---|---|---|
| 0 | Plan, decisiones y validación del Control | ✅ 5-nov |
| 3a | Método maduras/nuevas: cargador SELECT genérico (cualquier Caso) | ✅ 5-nov |
| 3b | Método maduras/nuevas en Óxidos + casos borde | ✅ 5-nov |
| 1a | Reporte: 15 hojas visibles, nombres y orden | ✅ 5-nov |
| 1b | Reporte: gráficos agrupados + RL + sumatorias Prod | ✅ 5-nov |
| 1c | Reporte: Dump reconciliado | ✅ 5-nov |
| 1d | Comparador de formato contra el oficial | ✅ 5-nov |
| 2a | Reconstitución: recalibración de densidad + asignación secuencial | ✅ 5-nov (opt-in «en validación») |
| 2b | Reconstitución: informe con fracción de traspaso y Cu fino | ✅ 5-nov |
| 4 | Integración: reporte consume recuperación directa del método | ✅ 5-nov |
| 5 | Unificación: reportes nuevos (formato oficial, reconstitución recalibrada) en el visor `dash-lixiviacion-curvas`, pestaña Reportes | ✅ 5-nov |

## Parte 2 — entrega (5-nov)

- `reconstitucion/recalibracion.py` (fórmulas §8–§10, ceros §13, invariantes §14),
  `recalibracion_caso.py` (suministro desde nacimiento de campaña, TMS
  reconciliada F18/F19 en la ventana, horas uniformes 12 h),
  `recalibracion_db.py` (solo SELECT).
- `analyze_db(..., metodo='recalibrada'|'volumen')`. **Por defecto sigue
  'volumen' (vigente)**; la recalibrada se elige en Reconstitución de Módulos →
  selector «Densidad recalibrada (en validación)», hasta validarla contra DB.
- Informe de módulos: DETALLE agrega `meta_tmh`, `densidad_recalibrada`,
  `fraccion_traspaso`; Cu fino = Σ TMS·CuT/100 por turno.
- Reproduce el Control M&R Septiembre: asignaciones por módulo, S = 0,6437 /
  0,5861 / 0,5978 / 0,4720 / 1 y Cu fino 865,41 / 810,21 / 845,65 / 764,63 / 460,63.
- Pruebas: 18 nuevas en `reconstitucion/test_recalibracion.py`.
- Supuestos a confirmar en servidor: `disponible_rotopalas.tmh_apilado` como TMH
  fijada directa; orden de módulos por primera fecha con volumen; tolerancia
  1 % contra `tms_conformado`; PAD con TMS reconciliada 0 y TMH positiva.

## Parte 3 — entrega (5-nov)

- `curvas_recon/maduras_nuevas.py`: núcleo genérico por PAD (`reconcile_pad`,
  `reconcile_chain`); maduras (>30 d) conservan la recuperación observada,
  nuevas se mueven con λ común para cerrar el Cu neto del run oficial
  (F25 Óxidos, F29 Sulfuros); 30 d conserva la oficial; historia intacta.
- `curvas_recon/maduras_inputs.py`: cargador SELECT-only para cualquier Caso
  (identidad Caso/run/modelo, objetivo F25/F29, perfil del run de asignación,
  recuperación primaria, riego y leyes); falla con causa explícita.
- Casos borde: pila que nace en la ventana, edad 29/30/31, infactibilidad con
  λ requerido y pila/día limitante, encadenamiento de Casos (vía API).
- Interfaz para el reporte: `direct_recovery_series(res)`.
- UI: «Ensayo neto local» funciona para Óxidos y Sulfuros de cualquier Caso,
  sin guardar en SQL. Regresión Caso 10009 intacta (λ = 0,72144; 1069,137 t).
- Pruebas: 88 pasan en las suites maduras/sulfide/cierre.
- Supuestos a confirmar en servidor: columnas `modulos_turnos.pad_id`,
  `reconciliacion_run.converged`, nombres `P%02d`; cotas de λ (0,2–5,0)
  provisionales; encadenamiento automático entre corridas de la UI pendiente.

## Parte 1 — entrega (5-nov)

- `escribir_libro` genera las 15 hojas visibles del oficial en su orden, con
  encabezados como fórmulas internas (`LOOKUP`, `MAX`, `SUM`, WIP), `Rec * 2`,
  `(Cu) dren`, `Flujo Riego` (reconciliado dentro del Caso, medido fuera).
- Gráficos de dispersión agrupados (Ox P1-8/9-16/17-24/25-32; Su P1-7/8-14/
  15-21/22-28) y 4 gráficos «Recuperación vs RL» por PAD; pilas virtuales
  siguen funcionando (5.º gráfico).
- Prod Cu: `Total Prod` diario (`=SUM`) y `Total Suma` del mes hasta el corte.
- Dump reconciliado (`report_dump.py`): F77 riego / F51 drenaje del run;
  riego diario reconciliado = medido × (Σ rec / Σ med); F por Caso;
  drenaje = F × riego; Aporte = (Qd·Cd − Qr·Cr)/1000; leyes medidas.
- `construir_doc(direct_recovery=...)` para el método maduras/nuevas.
- Comparador `tools/compare_report_format.py` + firma
  `test_fixtures/referencias/firma_reporte_oficial.json`: 0 ERROR; 5 AVISO
  (eje X ampliado a 420 días para no cortar curvas largas).
- Diferencia declarada: cada gráfico lleva una serie por pila del grupo
  (el oficial mezcla series de hojas ocultas/libros externos).
- A confirmar en servidor: F77/F51 en `recon_resultado_flujo` del modelo 125.
- Generación: ~13 s con 60 pilas × 1200 días (antes ~2 s) por las fórmulas.

## Hito 4 — integración (5-nov)

- Con «Ensayo neto local», el botón de reporte (Curvas y reconciliación y la
  sección Reportes de reconciliación) genera el **libro con formato oficial**
  usando `direct_recovery_series(res)`: maduras con recuperación observada,
  nuevas ajustadas. Antes descargaba un libro de ensayo aparte.
- La sección Reportes agrega al ZIP `Auditoria_Ensayo_Neto_Local_Caso<id>.xlsx`
  (fuentes, λ y cierre) cuando la corrida usa el método.

## Hito 5 — unificación en el visor (5-nov)

- La sección «Reportes de reconciliación» (SIIR) y la pestaña Reportes del
  visor `dash-lixiviacion-curvas` (con `LIX_CURVAS_SIIR=1`) entregan: reporte
  con formato oficial, auditoría del ensayo maduras/nuevas y los informes de
  módulos con selector «Reparto por volumen (vigente)» / «Densidad recalibrada
  (en validación)». El LEEME del ZIP registra el método.
- Verificado montando el visor dentro del SIIR con catálogo simulado: sin
  errores de consola.

## Pendientes conocidos

- Prototipo `auditorias/integracion_mr_dashboard_20261104/` no disponible en
  este entorno; la parte 2 se implementa desde el documento.
- Sin acceso SQL aquí: validación con fixtures/mocks. **Falta prueba en servidor**:
  F77/F51 en `recon_resultado_flujo`; cargador maduras/nuevas (reproducir 10009
  y un Caso con Óxidos); densidad recalibrada del Caso 10013 (ρ ≈ 1,8496).
- Cotas de λ (0,2–5,0) provisionales; encadenamiento de Casos desde la UI.
- Tiempo del reporte: ~13 s con 60 pilas × 1200 días.
- Semántica de `vol_total_est` y orden operacional de módulos (según documento).

## Bitácora

- 5-nov: plan cerrado; metodología y Control copiados al repo; agentes lanzados.
- 5-nov: parte 2 entregada y revisada; recalibrada queda opt-in hasta validar en DB.
- 5-nov: se agrega hito 5 (reportes en el visor de lixiviación, unificación).
- 5-nov: parte 3 entregada y revisada.
- 5-nov: parte 1 entregada y revisada (comparador 0 ERROR).
- 5-nov: hito 4 integrado (reporte oficial con recuperación directa).
- 5-nov: hito 5: reportes nuevos disponibles en el visor de lixiviación.
