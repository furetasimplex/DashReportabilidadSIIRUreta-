Inventario congelado: módulo completo untracked; no existe baseline Git interno que permita distinguir qué archivos del módulo fueron modificados en cada fase previa.

Python tracked modificados: `layout.py`, `report_export/report_export.py`. Otros tracked: `.env.example`, `assets/theme.css`. Cambios Programa/Plan y sidebar preexistentes, preservados.

**Python del módulo**

- `monitor_pi_tum\db.py`
- `monitor_pi_tum\deploy_dev.py`
- `monitor_pi_tum\gestion.py`
- `monitor_pi_tum\inspect_acciones_dev.py`
- `monitor_pi_tum\inspect_dev.py`
- `monitor_pi_tum\inspect_tum_postproceso_dev.py`
- `monitor_pi_tum\operational_sql.py`
- `monitor_pi_tum\panel.py`
- `monitor_pi_tum\postprocesar_tum_contingencia.py`
- `monitor_pi_tum\validate_atomicity_dev.py`
- `monitor_pi_tum\validate_operational_dev.py`
- `monitor_pi_tum\validate_postprocesar_tum_dev.py`
- `monitor_pi_tum\__init__.py`
- `monitor_pi_tum\validacion\expansion_v1\auditar_cierre.py`
- `monitor_pi_tum\validacion\expansion_v1\desplegar_dev.py`
- `monitor_pi_tum\validacion\expansion_v1\desplegar_reclamo_dev.py`
- `monitor_pi_tum\validacion\expansion_v1\preparar_sql.py`

**Tests del módulo**

- `monitor_pi_tum\test_cambio_horario.py`
- `monitor_pi_tum\test_gestion.py`
- `monitor_pi_tum\test_guard_dev.py`
- `monitor_pi_tum\test_modalidades.py`
- `monitor_pi_tum\test_monitor.py`
- `monitor_pi_tum\test_postprocesar_tum_contingencia.py`
- `monitor_pi_tum\test_rango.py`

**SQL de implementación / evidencia previa**

- `monitor_pi_tum\operacional_dev.sql`
- `monitor_pi_tum\validacion\ddl_ejecutado.sql`
- `monitor_pi_tum\validacion\acciones_actual\sp_mantiene_apilado_tmh_v2_test.sql`
- `monitor_pi_tum\validacion\acciones_actual\sp_registrar_contingencia_pi_test.sql`
- `monitor_pi_tum\validacion\acciones_actual\v_contingencia_pi_estado_turno_test.sql`
- `monitor_pi_tum\validacion\acciones_actual\v_contingencia_totalizador_resuelto_operacional_test.sql`
- `monitor_pi_tum\validacion\acciones_actual\v_contingencia_totalizador_resuelto_turno.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\inventar_SpcHidr.v_bd_ton_t12_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\reclamo.v_cv25_diario_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\reclamo.v_diferencia_cv25_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\reclamo.v_preliminar_cv25_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\reclamo.v_preliminar_cv25_con_acumulado_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\ddl\reclamo.v_reclamo_diario_contingencia_test.sql`

**Backups**

- `monitor_pi_tum\validacion\expansion_v1\backup\inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\inventar_SpcHidr.v_bd_ton_t12_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\inventar_SpcHidr.v_representatividad_diaria_calculada_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\reclamo.v_cv25_diario.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\reclamo.v_diferencia_cv25.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\reclamo.v_preliminar_cv25.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\reclamo.v_preliminar_cv25_con_acumulado.sql`
- `monitor_pi_tum\validacion\expansion_v1\backup\reclamo.v_reclamo_diario.sql`

**Rollback**

- `monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.v_bd_ton_t12_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_cv25_diario_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_diferencia_cv25_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_preliminar_cv25_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_preliminar_cv25_con_acumulado_contingencia_test.sql`
- `monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_reclamo_diario_contingencia_test.sql`

Otros tests/scripts untracked iniciales: `report_export/tests/test_programa_plan_cero_excel.py`, `scripts/validate_programa_plan_cero_dev.py`. Otros artefactos iniciales constan en `git_status.txt`.

**Objetos TEST encontrados en DEV (existencia comprobada; no implica creados por esta fase)**

|Objeto|Tipo|Creación|Modificación|
|---|---|---|---|
|inventar_SpcHidr.contingencia_estado_operacional_test|USER_TABLE|2026-09-15 14:24:18.257000|2026-09-15 15:35:50.660000|
|inventar_SpcHidr.contingencia_pi_accion_test|USER_TABLE|2026-09-15 16:33:54.503000|2026-09-15 16:38:07.967000|
|inventar_SpcHidr.PK_contingencia_estado_operacional_test|PRIMARY_KEY_CONSTRAINT|2026-09-15 14:24:18.260000|2026-09-15 14:24:18.260000|
|inventar_SpcHidr.PK_contingencia_pi_accion_test|PRIMARY_KEY_CONSTRAINT|2026-09-15 16:33:54.507000|2026-09-15 16:33:54.507000|
|inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test|SQL_STORED_PROCEDURE|2026-09-10 18:19:36.373000|2026-09-17 12:05:38.210000|
|inventar_SpcHidr.sp_guardar_contingencia_estado_operacional_test|SQL_STORED_PROCEDURE|2026-09-15 14:24:18.307000|2026-09-15 15:35:57.293000|
|inventar_SpcHidr.sp_registrar_contingencia_pi_test|SQL_STORED_PROCEDURE|2026-09-15 16:34:04.693000|2026-09-15 16:34:04.693000|
|inventar_SpcHidr.v_bd_ton_t12_contingencia_opt_test|VIEW|2026-09-13 00:20:33.747000|2026-09-13 00:20:33.747000|
|inventar_SpcHidr.v_bd_ton_t12_contingencia_test|VIEW|2026-09-11 12:44:33.013000|2026-09-17 12:05:35.780000|
|inventar_SpcHidr.v_contingencia_estado_operacional_actual_test|VIEW|2026-09-15 14:24:18.347000|2026-09-15 15:36:09.520000|
|inventar_SpcHidr.v_contingencia_pi_estado_turno_test|VIEW|2026-09-15 16:34:12.617000|2026-09-15 16:38:20.697000|
|inventar_SpcHidr.v_contingencia_pi_frontera_turno_opt_test|VIEW|2026-09-12 23:58:29.797000|2026-09-12 23:58:29.797000|
|inventar_SpcHidr.v_contingencia_pi_frontera_turno_opt2_test|VIEW|2026-09-13 00:03:07.370000|2026-09-13 00:03:07.370000|
|inventar_SpcHidr.v_contingencia_pi_serie_opt_test|VIEW|2026-09-12 23:28:44.743000|2026-09-12 23:28:44.743000|
|inventar_SpcHidr.v_contingencia_pi_totalizador_turno_opt_test|VIEW|2026-09-12 23:31:17.147000|2026-09-12 23:31:17.147000|
|inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno_opt_test|VIEW|2026-09-13 00:08:47.193000|2026-09-13 00:08:47.193000|
|inventar_SpcHidr.v_contingencia_totalizador_resuelto_operacional_test|VIEW|2026-09-15 14:24:18.393000|2026-09-15 16:42:47.390000|
|inventar_SpcHidr.v_contingencia_totalizador_resuelto_turno_opt_test|VIEW|2026-09-13 00:14:55.970000|2026-09-13 00:14:55.970000|
|inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test|VIEW|2026-09-11 10:19:22.040000|2026-09-17 12:05:35.673000|
|inventar_SpcHidr.v_representatividad_diaria_calculada_contingencia_test|VIEW|2026-09-11 10:21:04.510000|2026-09-11 10:21:04.510000|
|reclamo.v_cv25_diario_contingencia_test|VIEW|2026-09-17 12:07:02.717000|2026-09-17 12:09:43.980000|
|reclamo.v_diferencia_cv25_contingencia_test|VIEW|2026-09-17 12:07:03.213000|2026-09-17 12:07:03.213000|
|reclamo.v_preliminar_cv25_con_acumulado_contingencia_test|VIEW|2026-09-17 12:07:03.023000|2026-09-17 12:07:03.023000|
|reclamo.v_preliminar_cv25_contingencia_test|VIEW|2026-09-17 12:07:02.927000|2026-09-17 12:07:02.927000|
|reclamo.v_reclamo_diario_contingencia_test|VIEW|2026-09-17 12:07:03.107000|2026-09-17 12:07:03.107000|


**Correspondencia de los ocho DDL de expansión con DEV y rollback**

|Objeto|DDL coincide normalizado|Rollback|Existe|
|---|---|---|---|
|inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.sp_calcular_balance_flujos_contingencia_test.sql|True|
|inventar_SpcHidr.v_bd_ton_t12_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.v_bd_ton_t12_contingencia_test.sql|True|
|inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_inventar_SpcHidr.v_peso_teorico_turno_torre_contingencia_test.sql|True|
|reclamo.v_cv25_diario_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_cv25_diario_contingencia_test.sql|True|
|reclamo.v_diferencia_cv25_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_diferencia_cv25_contingencia_test.sql|True|
|reclamo.v_preliminar_cv25_con_acumulado_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_preliminar_cv25_con_acumulado_contingencia_test.sql|True|
|reclamo.v_preliminar_cv25_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_preliminar_cv25_contingencia_test.sql|True|
|reclamo.v_reclamo_diario_contingencia_test|True|C:\Users\nimun\OneDrive\Documentos\GitHub\DashReportabilidadSIIR\monitor_pi_tum\validacion\expansion_v1\rollback_reclamo.v_reclamo_diario_contingencia_test.sql|True|


La cobertura de rollback es 8/8 para expansión_v1. No se puede certificar rollback integral del módulo: las tablas de acciones/estado, SP de registro y resolvedor operacional no tienen rollback dedicado en esta carpeta. `acciones_actual/` y `objetos_protegidos_antes.json` son evidencia de definiciones, no un rollback integral probado. No se ejecutó ningún rollback.
