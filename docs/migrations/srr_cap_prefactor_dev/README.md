# SRR: cap físico pre-factor — exclusivamente DEV

## Cambio desplegado

Único objeto SQL modificado: `inventar_SpcHidr.v_srr_tms_origen_turno_emision_test`.
No se modificaron los SP de Factor, la vista de aplicación 2B, Python de la
aplicación, la orquestación RTO → DC → Reconst ni los objetos standalone.

El diagnóstico actual confirma **caso B**: ambos SP consumen
`Ton_SRR_Usado_Actual`; el cap y las claves Fecha/Turno de la vista anterior
dependían del cache ajustado. No hay reconstrucción desde porcentaje en los SP.

La nueva vista genera A/B desde
`v_apilado_tms_sin_sal_con_srr_reporte_test.TMS_Total_Sin_Sal_Con_SRR_A/B`.
El cap y la prioridad OFICIAL → IMP → SIN_ORIGEN conservan sus reglas.
Se preservan los nombres, orden y tipos de las 15 columnas originales.
`Apilado_TMS_Real` pasa a representar la referencia física **pre-factor**, como
en la standalone validada; `Apilado_TMS_Referencia_Cap` se agrega al final como
alias explícito. No es el tonelaje ajustado del cache RTO.

## Archivos de implementación y reversión

- `01_alter_vista.sql`: ALTER aplicado.
- `vista.diff`: diff exacto contra la definición respaldada.
- `v_srr_tms_origen_turno_emision_test.exact.sql`: bytes UTF-8 de la definición
  capturada mediante OBJECT_DEFINITION, antes del primer ALTER.
- `02_rollback.sql`: misma definición anterior, cambiando únicamente CREATE a
  ALTER para restaurar un objeto existente. Ejecutar solo en DEV.
- Los demás `*.exact.sql` respaldan los SP y la vista 2B protegidos.
- `scripts/deploy_srr_cap_prefactor_dev.py`: guard DEV, lock, respaldo,
  comparación y commit únicamente de la vista. Se niega a sobrescribir un
  respaldo distinto o a desplegar de nuevo sobre una vista ya cambiada.
- `scripts/validate_srr_cap_prefactor_dev.py`: pruebas reales reversibles,
  con comparación de hashes antes/después de los datos y definiciones protegidas.

## Comparación antes/después con las mismas fuentes

`impacto_srr.json` contiene un solo cambio operativo julio–septiembre:

| Fecha/turno | SRR anterior | SRR nuevo | Referencia pre-factor | Cap |
|---|---:|---:|---:|---|
| 2026-09-16 A | 455.773847 | 489.214821763 | 2326.252 | 1 → 0 |

La vista anterior estaba en `OK_CAP_APILADO`; la nueva queda en `OK`.
`antes_16.json` conserva los valores completos antes del cambio.

Los controles de agosto son exactamente iguales antes/después del ALTER:

| Fecha | SRR TMS día | Factor calculado actual |
|---|---:|---:|
| 06-08 | 16289.348630877499 | 0.999622091548018 |
| 09-08 | 29175.2560714605 | 0.9733574874959295 |
| 10-08 | 29750.894244100302 | 0.9964742557652089 |
| 13-08 | 30229.0643404688 | 1 |

El factor actual del 06-08 ya difería del antecedente histórico proporcionado;
esa diferencia estaba presente en el baseline y no la introduce este cambio.

La comparación con standalone detectó diferencias de 0.0000000001 TMS
exclusivamente en algunas sumas auxiliares FLOAT de IMP, al convertirlas a
decimal(38,10) con planes equivalentes. Se conservan en
`standalone_differences.json`. Las masas usadas, caps, estados y controles de
Factor se compararon exactamente; no se amplió su tolerancia para desplegar.

## Alcance de persistencia

El despliegue confirma únicamente el DDL de la vista. Las materializaciones
realizadas para validar se revierten: no se deja un reproceso histórico ni se
registra ningún evento de override. La siguiente generación normal de RTO
materializa los resultados corregidos usando la nueva vista.

Los objetos standalone se conservan. Su eventual eliminación queda fuera de
este cambio y requiere una tarea posterior.

## Validación final sobre los objetos vigentes

- `first_run_sin_cache.json`: 2 filas A/B pese a eliminar temporalmente el cache
  del 16-09. SRR A = 489.214821763; referencia = 2326.252; cap = 0.
- `estabilidad_3x.json`: tres ejecuciones completas del coordinador real RTO,
  con igualdad exacta desde la primera. Factor calculado/automático/aplicado =
  0.21963019549669024; SRR A/día = 489.214821763; SRR B = 0;
  RTO A = 465.364996; RTO B = 0; SRR % A/B = 100/0.
- Modo AUTOMATICO, Flag_Override_1 = false, Id_Control_Aplicacion = 7;
  límites KOM/CAT = 380/265 en todas las ejecuciones.
- `dia_vs_mes_16.json`: comparación exacta de todas las columnas de negocio
  para el 16-09 en Reporte por Turno, Generador y Reconst. Solo se excluyen
  timestamps de auditoría si existen; no se redondean resultados.
- `excel_checks.json`: los dos Excel contienen siete hojas. Las celdas Reconst
  del 16-09 coinciden exactamente. TMH total A = 483.2380620948381 con AUTOMATICO.
- `RTO_20260916_validado.xlsx` y `RTO_20260901_20260930_validado.xlsx`: archivos
  reales generados durante la transacción reversible, sin refrescos manuales
  de Datos Conciliados.
- `rollback_datos.json`: hashes completos idénticos antes/después para Control
  Factor V2, cache RTO, Datos Conciliados, historial de overrides y parámetros.
  Los dos SP Factor y la vista de aplicación 2B conservan sus definiciones exactas.
- `dependencias_finales.json`: las cuatro fuentes esperadas, sin cache RTO ni
  referencia a una vista standalone.

Tests Python ejecutados:

```text
python -m pytest report_export/tests/test_paquete_reporte_turno.py
  report_export/tests/test_orquestacion_reporte_turno.py
  report_export/tests/test_reconst_mod_srr.py
  report_export/tests/test_factor_ajuste_camiones_report.py
  monitor_pi_tum/test_factor_camiones.py
  monitor_pi_tum/test_limites_camiones.py
  monitor_pi_tum/test_override_camiones.py -q
```

Resultado: 106 passed, 45 subtests passed. `git diff --check` limpio.
Sin commit ni push; no se promovió ningún objeto a PROD.
