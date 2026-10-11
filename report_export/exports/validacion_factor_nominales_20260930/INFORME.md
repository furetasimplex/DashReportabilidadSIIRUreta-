> Actualizacion posterior: correccion textual N_BREAK persistida en DEV.
> [Informe y evidencia](../validacion_nbreak_textual_20260930/INFORME.md).
> NBREAK_NO_NUMERICO distingue vacios/espacios/texto invalido de NULL real.
> 17 casos aprobados y 89 fechas sin diferencias; no se reprocesaron datos.

# Implementación DEV — Factor camiones V2: vueltas y cargas nominales

**Estado final: COMMIT aplicado y verificado.** Migración y reproceso persistidos el 30-09-2026. Rango: 01-07–27-09-2026, última fecha materializada al ejecutar. 89 fechas; 178 filas de cache RTO. Las pruebas con ROLLBACK se completaron primero. No PROD, no commit/push de Git.

## Lógica y trazabilidad

Cada fuente se filtra por CH01, fase distinta de SRR y KOM/CAT. Se agregan sus vueltas diarias. Se exigen registros, ausencia de NULL/negativos y suma positiva. Solo ceros no da cobertura. Se selecciona MOV_CAM, en su defecto MOV_CAM_POWERBI, o SIN_DATOS_CAMIONES. No se mezclan fuentes entre flotas; una flota ausente en la fuente válida aporta cero. Los motivos OK/SIN_REGISTROS/SOLO_CEROS/NBREAK_NULL/NBREAK_NEGATIVO se conservan en V2. Si ambos defectos coexisten se informa NULL primero, sin considerar válido el día.

Producción KOM/CAT = vueltas seleccionadas × nominal vigente. Dato Mina es su suma. No intervienen ton_descarga ni Tonelaje_Hum_CIO. Se mantienen las fórmulas posteriores de participación, distribución, carga por viaje, límite, toneladas corregidas y factor. Se suman los registros filtrados sin introducir deduplicación adicional.

Se resuelven cuatro configuraciones únicas por fecha; la falta o multiplicidad aborta. Nominales utilizados y estados se guardan físicamente en V2 y la vista los expone desde V2. La ruta standalone comparte la resolución de camiones y conserva su fuente de SRR anterior. La vista mantiene sin cambios la lógica AUTOMÁTICO/APLICADO/override.

Registrar parámetros solo cambia vigencias y auditoría; no reprocesa ni publica. El panel existente permite seleccionar categoría y revisar vigencia, historial, próximos cambios, motivo/usuario, confirmación retroactiva y pendiente contra el valor materializado. El detalle diario muestra nominales usados y evaluación de fuentes.

## Seeds persistidos

| Categoría | Flota | Valor | Desde | Hasta | Usuario |
|---|---|---:|---|---|---|
| CARGA_NOMINAL_TMH_VIAJE | CAT | 236.000000 | 2026-07-01 | Abierta | MIGRACION_NOMINALES_V2_DEV |
| CARGA_NOMINAL_TMH_VIAJE | KOM | 357.000000 | 2026-07-01 | Abierta | MIGRACION_NOMINALES_V2_DEV |
| LIMITE_CARGA_AJUSTE | CAT | 265.000000 | 2026-07-01 | Abierta | MIGRACION_FASE2A |
| LIMITE_CARGA_AJUSTE | KOM | 380.000000 | 2026-07-01 | Abierta | MIGRACION_FASE2A |

Motivo nominal: Seed aprobado: carga nominal por viaje para reconstrucción de producción V2; vigencia 2026-07-01. Los registros originales de límites se conservaron; no se crearon tablas paralelas.

## Casos obligatorios

| Fecha | Fuente | Vueltas KOM/CAT | Producción KOM/CAT | Calculado | Aplicado | Modo |
|---|---|---|---|---:|---:|---|
| 2026-08-06 | MOV_CAM | 66 / 17 | 23562 / 4012 | 0.998314380308 | 0.998314380308 | AUTOMATICO |
| 2026-09-14 | MOV_CAM | 139 / 0 | 49623 / 0 | 1.000000000000 | 1.000000000000 | AUTOMATICO |
| 2026-09-16 | MOV_CAM | 1 / 0 | 357 / 0 | 0.219630195497 | 1.000000000000 | FORZADO_1 |
| 2026-09-21 | MOV_CAM_POWERBI | 4 / 0 | 1428 / 0 | 1.000000000000 | 1.000000000000 | AUTOMATICO |
| 2026-09-22 | MOV_CAM_POWERBI | 137 / 0 | 48909 / 0 | 0.958813755870 | 0.958813755870 | AUTOMATICO |

06/08: Dato Mina=27.574 TMH. 14/09: MOV_CAM=139 vueltas KOM frente a 138 en PowerBI; producción=49.623, chancado sin ajuste≈52.601,453190 y carga≈378,427721<380. 16/09: automático≈0,21963019549669 y aplicado=1 exclusivamente por FORZADO_1. La tabla de override quedó idéntica antes/después.

## Comparación masiva

[Comparación completa de 89 fechas](comparacion.csv). [Fuentes y vueltas](fuentes_vueltas.csv). [Snapshot anterior CSV](antes.csv). [Snapshot posterior CSV](despues.csv).

Fuentes finales: MOV_CAM=80, SIN_DATOS_CAMIONES=2, MOV_CAM_POWERBI=7.

Clasificación: SIN_CAMBIO=7, CAMBIO_POR_NOMINAL=0, CAMBIO_POR_FUENTE_VUELTAS=32, CAMBIO_AMBOS=48, SIN_DATOS=2.

La clasificación considera cambios de fuente y reconstrucción nominal, incluso cuando el factor numérico no cambia. Fuente anterior significa la fuente efectiva del código anterior (PowerBI); se conserva también la etiqueta antigua incorrecta MOV_CAM_DEDUP_OPERACIONAL en otra columna.

| Fecha con cambio numérico | Antes | Después | Explicación |
|---|---:|---:|---|
| 2026-07-10 | 0.982843094318 | 1.000000000000 | MOV_CAM suma 50 vueltas KOM; PowerBI 25. |
| 2026-07-30 | 0.941204678690 | 1.000000000000 | MOV_CAM agrega 17 vueltas CAT; PowerBI no tenía CAT (KOM=88 en ambos). |
| 2026-08-06 | 0.999622091548 | 0.998314380308 | Mismas vueltas 66/17; nueva proporción por nominales 357/236. |
| 2026-09-14 | 0.996930632509 | 1.000000000000 | Se eligen 139 vueltas KOM de MOV_CAM frente a 138 de PowerBI. |

Los días 02/09 y 20/09 quedan SIN_DATOS_CAMIONES y factor calculado NULL; la aplicación efectiva conserva el fallback existente. No se convierten datos inválidos en un factor válido.

## Alcance e invariantes

Las 89 fechas conservan exactamente las entradas de apilado bruto, humedad, sal, SRR, delta de inventario y chancado TMH sin ajuste. Solo cambia la reconstrucción de camiones y sus efectos posteriores. Los valores derivados de los cuatro factores modificados se propagaron mediante la cadena existente. No se cambiaron reglas de masa, SRR, PI/TUM, inventario ni fórmulas downstream.

Se utilizó refrescar_dependencias_datos_conciliados_emision: Apilado → Histórico → Factor → Clays/CuFe → Cache → Datos Conciliados. Su ventana incremental preexistente de apilado es de 15 días (13–27/09); Factor, Cache y DC se procesaron desde 01/07. Clays conserva su inicio vigente 01/08. No se creó otra cadena ni se amplió el rango de DC/cache fuera del autorizado.

Consumidores leídos y validados: factor=89 filas, balance=89 filas, dc=89 filas, generador=89 filas, reconstitucion=178 filas, rto=178 filas. Balance aplicado coincide con DC dentro de 1e-6. Los archivos de exportación/Excel no se editaron en esta tarea.

## Objetos SQL exactos

**Modificados** (esquema inventar_SpcHidr):

- factor_camiones_parametro_vigencia_test (CHECK y seeds)
- Control_Factor_Ajuste_Camiones_v2_test (dos nominales y dos estados)
- sp_registrar_limite_factor_camiones_vigencia_test
- sp_factor_ajuste_camiones_test
- sp_factor_ajuste_camiones_standalone_test
- sp_mantiene_factor_ajuste_camiones_v2_test
- sp_mantiene_factor_ajuste_camiones_v2_standalone_test
- v_ajuste_camiones_emision_test

**Creados**:

- sp_registrar_parametro_factor_camiones_vigencia_test
- fn_resolver_vueltas_camiones_test
- v_vueltas_camiones_diarias_test

Trigger, índices, PK/UQ, semántica de vigencias y tabla de auditoría permanecen conservados.

## Archivos de esta implementación

**Python** (los tres primeros son existentes; los demás nuevos):

- monitor_pi_tum/db.py
- monitor_pi_tum/limites_camiones_panel.py
- monitor_pi_tum/factor_camiones_panel.py
- monitor_pi_tum/test_parametros_camiones.py
- scripts/factor_camiones_nominales_dev.py
- scripts/validate_factor_nominales_dev.py
- scripts/test_factor_nominales_sql.py

**SQL nuevos** en docs/migrations/factor_camiones_nominales_dev:

- 01_esquema.sql
- 01b_trazabilidad_fuentes.sql
- 02_administrador_generico.sql
- 03_wrapper_limites.sql
- 04_resolver_vueltas.sql
- 05_vueltas_diarias.sql
- 06_sp_factor_ajuste_camiones_test.sql
- 07_sp_factor_ajuste_camiones_standalone_test.sql
- 08_sp_mantiene_factor_ajuste_camiones_v2_test.sql
- 09_sp_mantiene_factor_ajuste_camiones_v2_standalone_test.sql
- 10_v_ajuste_camiones_emision_test.sql
- rollback_dev.sql
- rollback_preparacion.sql

Además: README.md y backup/ (7 SQL, 3 copias Python y manifest SHA-256). Los .diff locales de este directorio comparan únicamente los tres archivos productivos con sus backups previos, separando los cambios preexistentes. Los snapshots y este informe son artefactos locales sin staging.

## Pruebas y rollback

114 tests locales y 50 subtests pasaron; comando exacto en [tests.txt](tests.txt). Las advertencias de openpyxl copy son preexistentes. Pasaron los 10 casos del resolutor SQL, 8 rechazos por configuración/vigencia inválida, temporalidad, independencia entre categorías/flotas, seis decimales, registro sin reproceso, pendiente antes/después, persistencia, contratos INSERT EXEC y ambas rutas. Concurrencia comprobada antes y después del despliegue con dos sesiones y espera APPLICATION.

La UI se validó con tests y callbacks sobre lecturas reales DEV: ambas categorías, historial, pendientes vacíos, modal retroactivo y detalle 16/09. No se realizó verificación visual en navegador.

Dos pruebas integrales con ROLLBACK restauraron datos y definiciones. Posteriormente la migración y el reproceso hicieron COMMIT, comprobado con nueva conexión. El rollback de objetos y resultados también fue probado dentro de una transacción revertida: **la implementación nueva sigue persistida**.

Rollback operativo: scripts/validate_factor_nominales_dev.py rollback; usa rollback_dev.sql, restaura V2/DC/cache del snapshot fresco y los archivos Python originales. Aborta ante cambios posteriores en vez de destruirlos. No ejecutar el componente rollback_preparacion.sql aisladamente. Los timestamps/bitácoras auxiliares del reproceso no se rebobinan con ese rollback.

## Riesgos y límites conocidos

- La prioridad aprobada usa SUM sobre los registros filtrados de MOV_CAM; 10/07 suma 50 frente a 25 en PowerBI. No se añadió una deduplicación no solicitada.
- La UI conserva su control optimista por valor; no hay compare-and-swap de versión nuevo. La integridad temporal se protege mediante locks y constraints SQL.
- El rango potencial del administrador sigue siendo inicio solicitado a MAX(Fecha), sin recorte por futuras vigencias; el pendiente real se calcula por valores.
- Nominales/estados se añadieron nullable para no inventar uso histórico. Todas las 89 fechas reprocesadas ya guardan sus valores efectivos.
- Los ROLLBACK de pruebas pueden dejar saltos de identity, sin registros residuales.

## Control Git

git diff --check: **exit 0**. Avisos LF/CRLF preexistentes. Ningún commit/push. El diff global incluye trabajo anterior; no representa solo esta tarea. Los demás archivos tracked ya modificados al iniciar (report_export, reclamo, panel general y diagnósticos) no se editaron aquí.

```text
 M definiciones_pipeline.txt
 M monitor_pi_tum/db.py
 M monitor_pi_tum/panel.py
 M pipeline_completo.txt
 M rastreo_escritor.txt
 M reclamo/db.py
 M report_export/export_to_excel.py
 M report_export/report_export.py
 M report_export/tests/test_datos_conciliados_excel.py
 M report_export/tests/test_orquestacion_reporte_turno.py
 M report_export/tests/test_paquete_reporte_turno.py
 M report_export/tests/test_reconst_mod_srr.py
 M test_definiciones_pipeline.py
 M test_pipeline_completo.py
 M validar_pipeline.txt
?? docs/diagnosticos/
?? docs/migrations/factor_camiones_fase2a/
?? docs/migrations/factor_camiones_nominales_dev/
?? docs/migrations/srr_cap_prefactor_dev/
?? monitor_pi_tum/ENTREGA_FACTOR_CAMIONES_FASE1.md
?? monitor_pi_tum/factor_camiones_panel.py
?? monitor_pi_tum/limites_camiones_panel.py
?? monitor_pi_tum/override_camiones_panel.py
?? monitor_pi_tum/test_factor_camiones.py
?? monitor_pi_tum/test_limites_camiones.py
?? monitor_pi_tum/test_override_camiones.py
?? monitor_pi_tum/test_override_dev_reversible.py
?? monitor_pi_tum/test_parametros_camiones.py
?? release/
?? report_export/exports/auditoria_ley_srr_202609/
?? report_export/exports/auditoria_parametros_camiones_20260930/
?? report_export/exports/auditoria_rutas_factor_20260929/
?? report_export/exports/balance_presentacion_20260929/
?? report_export/exports/factor_encabezado_20260929/
?? report_export/exports/factor_grupos_20260929/
?? report_export/exports/factor_presentacion_20260929/
?? report_export/exports/validacion_factor_nominales_20260930/
?? report_export/tests/test_rutas_factor_balance.py
?? "reporte/Datos Conciliados Septiembre 2026_RevPI SRR(3) (1).xlsm"
?? scripts/deploy_srr_cap_prefactor_dev.py
?? scripts/diagnosticos/calendario_rto_dev/evidencia_final/
?? scripts/factor_camiones_fase2a.py
?? scripts/factor_camiones_nominales_dev.py
?? scripts/inspect_factor_camiones_fase2a.py
?? scripts/test_factor_camiones_fase2a.py
?? scripts/test_factor_nominales_sql.py
?? scripts/validate_factor_camiones_fase2a_baseline.py
?? scripts/validate_factor_camiones_fase2a_concurrency.py
?? scripts/validate_factor_nominales_dev.py
?? scripts/validate_limites_camiones_ui_dev.py
?? scripts/validate_srr_cap_prefactor_dev.py
?? test_factor_limites_dev_reversible.py

 definiciones_pipeline.txt                          | 147 ++++-----
 monitor_pi_tum/db.py                               | 224 ++++++++++++++
 monitor_pi_tum/panel.py                            |   2 +
 pipeline_completo.txt                              | 341 +--------------------
 rastreo_escritor.txt                               |  34 +-
 reclamo/db.py                                      |  30 +-
 report_export/export_to_excel.py                   | 187 +++++++----
 report_export/report_export.py                     | 154 ++++++----
 .../tests/test_datos_conciliados_excel.py          |  65 ++--
 .../tests/test_orquestacion_reporte_turno.py       |  24 +-
 report_export/tests/test_paquete_reporte_turno.py  |  75 ++++-
 report_export/tests/test_reconst_mod_srr.py        |  36 ++-
 test_definiciones_pipeline.py                      |  18 +-
 test_pipeline_completo.py                          |   6 +-
 validar_pipeline.txt                               | 199 +-----------
 15 files changed, 736 insertions(+), 806 deletions(-)

```
