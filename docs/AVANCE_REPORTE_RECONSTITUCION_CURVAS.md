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
| 3a | Método maduras/nuevas: cargador SELECT genérico (cualquier Caso) | ⏳ en curso |
| 3b | Método maduras/nuevas en Óxidos + casos borde | ⏳ en curso |
| 1a | Reporte: 15 hojas visibles, nombres y orden | ⏳ en curso |
| 1b | Reporte: gráficos agrupados + RL + sumatorias Prod | ⏳ en curso |
| 1c | Reporte: Dump reconciliado | ⏳ en curso |
| 1d | Comparador de formato contra el oficial | ⏳ en curso |
| 2a | Reconstitución: recalibración de densidad + asignación secuencial | ✅ 5-nov (opt-in «en validación») |
| 2b | Reconstitución: informe con fracción de traspaso y Cu fino | ✅ 5-nov |
| 4 | Integración: reporte consume recuperación directa del método | pendiente |
| 5 | Unificación: reportes nuevos (formato oficial, reconstitución recalibrada) en el visor `dash-lixiviacion-curvas`, pestaña Reportes | pendiente |

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

## Pendientes conocidos

- Prototipo `auditorias/integracion_mr_dashboard_20261104/` no disponible en
  este entorno; la parte 2 se implementa desde el documento.
- Sin acceso SQL aquí: validación con fixtures/mocks; falta prueba en servidor.
- Semántica de `vol_total_est` y orden operacional de módulos (según documento).

## Bitácora

- 5-nov: plan cerrado; metodología y Control copiados al repo; agentes lanzados.
- 5-nov: parte 2 entregada y revisada; recalibrada queda opt-in hasta validar en DB.
- 5-nov: se agrega hito 5 (reportes en el visor de lixiviación, unificación).
