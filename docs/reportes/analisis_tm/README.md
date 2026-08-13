# Análisis TM / Análisis Torres de Muestreo: dependencias SQL

> Extraccion de solo lectura: `2026-08-06 19:24:12.876465-03:00`  
> Servidor: `VPS-5347319-X`  
> Base de datos: `inventar_SpcHidr`

## Flujo ejecutado por la aplicacion

```text
Vista previa Análisis TM (tipo=reporte_turno)
├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)
├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe
├── EXEC sp_actualizar_reporte_turno_cache_emision_test
└── SELECT reporte_turno_cache_emision_test

Excel Análisis Torres de Muestreo (tipo=reporte_turno)
├── EXEC sp_mantiene_apilado_tmh_v2_test (@DiasReproceso=7)
├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)
├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe
├── EXEC sp_actualizar_reporte_turno_cache_emision_test
├── SELECT reporte_turno_cache_emision_test
└── EXEC sp_generador_reporte_diario_emision_test

PDF Análisis TM
├── EXEC sp_mantiene_factor_ajuste_camiones_v2_test (@DiasReproceso=0)
├── Si el período alcanza 2026-08-01: EXEC sp_refrescar_clays_cufe
├── EXEC sp_actualizar_reporte_turno_cache_emision_test
├── SELECT reporte_turno_cache_emision_test
└── EXEC sp_generador_reporte_diario_emision_test
```

## Árbol de dependencias de base de datos

Las aristas `[catalogo]` provienen de `sys.sql_expression_dependencies`;
las `[texto]` fueron encontradas en la definición y pueden incluir SQL dinámico.

```text
inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.Control_Apilado_TMH_v2_test [USER_TABLE]
├── [catalogo] inventar_SpcHidr.tot_TM [USER_TABLE]
└── [texto] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW]
        └── [catalogo] inventar_SpcHidr.Control_Apilado_TMH_v2_test [USER_TABLE]

inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test [USER_TABLE]
├── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
└── [catalogo] inventar_SpcHidr.sp_factor_ajuste_camiones_test [SQL_STORED_PROCEDURE]
        ├── [catalogo] inventar_SpcHidr.Historico_Apilado_Diario [USER_TABLE]
        ├── [texto] inventar_SpcHidr.mov_cam [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.mov_cam_powerbi [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.v_humedad_inventario_test [VIEW]
        │       └── [catalogo] inventar_SpcHidr.v_reporte_diario_humedad_test [VIEW]
        │               ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │               ├── [catalogo] inventar_SpcHidr.humedad_inicial_tm_periodo [USER_TABLE]
        │               ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW]
        │               │       ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │               │       ├── [catalogo] inventar_SpcHidr.factor_ajuste_camiones [USER_TABLE]
        │               │       ├── [catalogo] inventar_SpcHidr.humedad_inicial_tm_periodo [USER_TABLE]
        │               │       ├── [catalogo] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW] (dependencias ya mostradas)
        │               │       └── [catalogo] inventar_SpcHidr.v_representatividad_diaria_calculada [VIEW]
        │               │               ├── [catalogo] inventar_SpcHidr.v_peso_real_torre_turno_excel [VIEW]
        │               │               │       └── [catalogo] inventar_SpcHidr.peso_real_torre_turno [USER_TABLE]
        │               │               ├── [catalogo] inventar_SpcHidr.v_peso_teorico_turno_torre_excel [VIEW]
        │               │               │       ├── [catalogo] inventar_SpcHidr.param_peso_teorico_base [USER_TABLE]
        │               │               │       └── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW]
        │               │               │               ├── [catalogo] inventar_SpcHidr.v_bitacora_rangos [VIEW]
        │               │               │               │       └── [catalogo] inventar_SpcHidr.bitacora_turnos_consolidada [USER_TABLE]
        │               │               │               ├── [catalogo] inventar_SpcHidr.v_he_10s_por_intervalo_excel [VIEW]
        │               │               │               │       └── [catalogo] inventar_SpcHidr.Resumen_Intervalo_TotTM [USER_TABLE]
        │               │               │               ├── [catalogo] inventar_SpcHidr.v_informe_tm_lab_norm [VIEW]
        │               │               │               │       └── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │               │               │               └── [catalogo] inventar_SpcHidr.v_ton_por_intervalo_excel [VIEW]
        │               │               │                       └── [catalogo] inventar_SpcHidr.Resumen_Intervalo_TotTM [USER_TABLE]
        │               │               ├── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW] (dependencias ya mostradas)
        │               │               └── [catalogo] inventar_SpcHidr.v_representatividad_srr_turno_calculada [VIEW]
        │               │                       ├── [catalogo] inventar_SpcHidr.v_estado_apilado_turno_representatividad [VIEW]
        │               │                       │       └── [catalogo] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW] (dependencias ya mostradas)
        │               │                       ├── [catalogo] inventar_SpcHidr.v_peso_real_torre_turno_excel [VIEW] (dependencias ya mostradas)
        │               │                       ├── [catalogo] inventar_SpcHidr.v_peso_teorico_turno_torre_excel [VIEW] (dependencias ya mostradas)
        │               │                       └── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW] (dependencias ya mostradas)
        │               └── [catalogo] inventar_SpcHidr.v_representatividad_diaria_calculada [VIEW] (dependencias ya mostradas)
        └── [catalogo] inventar_SpcHidr.v_inventario_chancado_test [VIEW]
                └── [catalogo] inventar_SpcHidr.v_inventario_chancado_archive_test [VIEW]
                        ├── [catalogo] inventar_SpcHidr.datos_filtrados [USER_TABLE]
                        ├── [catalogo] inventar_SpcHidr.semilla_inventario_chancado [USER_TABLE]
                        └── [catalogo] inventar_SpcHidr.v_humedad_inventario_test [VIEW] (dependencias ya mostradas)

inventar_SpcHidr.sp_refrescar_clays_cufe [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.Clays_CuFe [USER_TABLE]
├── [catalogo] inventar_SpcHidr.Clays_CuFe_trazabilidad [USER_TABLE]
└── [catalogo] inventar_SpcHidr.v_clays_cufe_calculado_v2_test [VIEW]
        ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.NIR [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.representatividad_torres_resultado [USER_TABLE]
        └── [catalogo] inventar_SpcHidr.v_conciliacion_chancado_v2 [VIEW]
                └── [catalogo] inventar_SpcHidr.resumen_mina [VIEW]
                        └── [catalogo] inventar_SpcHidr.mov_cam [USER_TABLE]

inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
└── [catalogo] inventar_SpcHidr.sp_reporte_turno_emision_test [SQL_STORED_PROCEDURE]
        ├── [catalogo] inventar_SpcHidr.Clays_CuFe [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.humedad_inicial_tm_periodo [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.plan_mensual_reporte_turno [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.plan_semanal_reporte_turno [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.representatividad_torres_resultado [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.v_ajuste_camiones_emision_test [VIEW]
        │       └── [catalogo] inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.v_apilado_base_mina_stock_srr [VIEW]
        │       └── [catalogo] inventar_SpcHidr.mov_cam [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.v_conciliacion_chancado_v2 [VIEW] (dependencias ya mostradas)
        ├── [catalogo] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW] (dependencias ya mostradas)
        ├── [catalogo] inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test [VIEW]
        │       ├── [catalogo] inventar_SpcHidr.analitos_semilla_reporte_turno [USER_TABLE]
        │       └── [catalogo] inventar_SpcHidr.v_leyes_validadas_tm_turno [VIEW]
        │               ├── [catalogo] inventar_SpcHidr.v_validacion_leyes_tm1_v2 [VIEW]
        │               │       ├── [catalogo] inventar_SpcHidr.Clays_CuFe [USER_TABLE]
        │               │       ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │               │       ├── [catalogo] inventar_SpcHidr.representatividad_torres_resultado [USER_TABLE]
        │               │       └── [catalogo] inventar_SpcHidr.v_conciliacion_chancado_v2 [VIEW] (dependencias ya mostradas)
        │               └── [catalogo] inventar_SpcHidr.v_validacion_leyes_tm2_v2 [VIEW]
        │                       ├── [catalogo] inventar_SpcHidr.Clays_CuFe [USER_TABLE]
        │                       ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │                       ├── [catalogo] inventar_SpcHidr.representatividad_torres_resultado [USER_TABLE]
        │                       └── [catalogo] inventar_SpcHidr.v_conciliacion_chancado_v2 [VIEW] (dependencias ya mostradas)
        ├── [catalogo] inventar_SpcHidr.v_reporte_turno_campania_modulo_test [VIEW]
        │       ├── [catalogo] inventar_SpcHidr.control_apilado_diario [USER_TABLE]
        │       └── [catalogo] inventar_SpcHidr.v_reporte_turno_reales_test [VIEW]
        │               ├── [catalogo] inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test [VIEW]
        │               │       ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW] (dependencias ya mostradas)
        │               │       └── [catalogo] inventar_SpcHidr.v_sal_ajustada_operacional_test [VIEW]
        │               │               ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW] (dependencias ya mostradas)
        │               │               └── [catalogo] inventar_SpcHidr.v_sal_ajustada [VIEW]
        │               │                       ├── [catalogo] inventar_SpcHidr.datos_filtrados [USER_TABLE]
        │               │                       └── [catalogo] inventar_SpcHidr.topografia_sal [USER_TABLE]
        │               └── [catalogo] inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test_v2 [VIEW]
        │                       └── [catalogo] inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test [VIEW] (dependencias ya mostradas)
        ├── [catalogo] inventar_SpcHidr.v_reporte_turno_fuentes_info_test [VIEW]
        │       └── [catalogo] inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test [VIEW] (dependencias ya mostradas)
        └── [catalogo] inventar_SpcHidr.v_sal_ajustada [VIEW] (dependencias ya mostradas)

inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]

inventar_SpcHidr.sp_generador_reporte_diario_emision_test [SQL_STORED_PROCEDURE]
└── [catalogo] inventar_SpcHidr.fn_generador_reporte_diario_emision_test [SQL_INLINE_TABLE_VALUED_FUNCTION]
        ├── [catalogo] inventar_SpcHidr.plan_mensual_reporte_turno [USER_TABLE]
        ├── [catalogo] inventar_SpcHidr.plan_semanal_reporte_turno [USER_TABLE]
        └── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]

```

## Objetos incluidos

| Objeto | Tipo | Última modificación | Definición exportada |
|---|---|---:|---|
| `inventar_SpcHidr.Clays_CuFe` | USER_TABLE | 2025-10-02 15:43:08.017000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Clays_CuFe_trazabilidad` | USER_TABLE | 2026-08-03 02:43:07.160000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Control_Apilado_TMH_v2_test` | USER_TABLE | 2026-08-04 14:47:44.723000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test` | USER_TABLE | 2026-07-31 01:32:38.817000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Historico_Apilado_Diario` | USER_TABLE | 2026-07-07 15:56:18.137000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Informe_TM_lab` | USER_TABLE | 2026-02-12 12:13:55.607000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.NIR` | USER_TABLE | 2026-02-10 14:48:59.083000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Resumen_Intervalo_TotTM` | USER_TABLE | 2026-07-22 14:05:44.430000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.analitos_semilla_reporte_turno` | USER_TABLE | 2026-06-02 14:08:17.580000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.bitacora_turnos_consolidada` | USER_TABLE | 2026-05-19 17:07:34.240000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.control_apilado_diario` | USER_TABLE | 2025-10-07 09:21:00.063000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.datos_filtrados` | USER_TABLE | 2026-07-22 00:46:50.910000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.factor_ajuste_camiones` | USER_TABLE | 2026-05-28 18:57:18.897000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.fn_generador_reporte_diario_emision_test` | SQL_INLINE_TABLE_VALUED_FUNCTION | 2026-07-31 11:26:39.750000 | Sí |
| `inventar_SpcHidr.humedad_inicial_tm_periodo` | USER_TABLE | 2026-06-02 11:35:16.813000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.mov_cam` | USER_TABLE | 2026-08-04 16:03:13.620000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.mov_cam_powerbi` | USER_TABLE | 2026-08-03 21:43:58.913000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.param_peso_teorico_base` | USER_TABLE | 2026-05-07 12:16:09.310000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.peso_real_torre_turno` | USER_TABLE | 2026-05-19 17:07:23.280000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.plan_mensual_reporte_turno` | USER_TABLE | 2026-06-01 18:57:11.347000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.plan_semanal_reporte_turno` | USER_TABLE | 2026-06-01 18:57:11.413000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.reporte_turno_cache_emision_test` | USER_TABLE | 2026-07-31 11:14:35.217000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.representatividad_torres_resultado` | USER_TABLE | 2026-07-11 13:46:00.810000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.resumen_mina` | VIEW | 2026-02-11 13:13:03.167000 | Sí |
| `inventar_SpcHidr.semilla_inventario_chancado` | USER_TABLE | 2026-08-01 13:19:03.773000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.sp_actualizar_reporte_turno_cache_emision_test` | SQL_STORED_PROCEDURE | 2026-07-31 11:23:14.840000 | Sí |
| `inventar_SpcHidr.sp_factor_ajuste_camiones_test` | SQL_STORED_PROCEDURE | 2026-08-03 22:31:57.337000 | Sí |
| `inventar_SpcHidr.sp_generador_reporte_diario_emision_test` | SQL_STORED_PROCEDURE | 2026-07-31 11:39:34.093000 | Sí |
| `inventar_SpcHidr.sp_mantiene_apilado_tmh_v2_test` | SQL_STORED_PROCEDURE | 2026-08-04 14:48:06.393000 | Sí |
| `inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test` | SQL_STORED_PROCEDURE | 2026-08-02 20:56:20.490000 | Sí |
| `inventar_SpcHidr.sp_refrescar_clays_cufe` | SQL_STORED_PROCEDURE | 2026-08-03 02:46:39.750000 | Sí |
| `inventar_SpcHidr.sp_reporte_turno_emision_test` | SQL_STORED_PROCEDURE | 2026-08-04 11:46:16.413000 | Sí |
| `inventar_SpcHidr.topografia_sal` | USER_TABLE | 2026-05-28 10:01:37.457000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.tot_TM` | USER_TABLE | 2026-07-23 02:26:04.130000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.v_ajuste_camiones_emision_test` | VIEW | 2026-07-31 01:39:53.870000 | Sí |
| `inventar_SpcHidr.v_apilado_base_mina_stock_srr` | VIEW | 2026-06-01 10:12:33.767000 | Sí |
| `inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test` | VIEW | 2026-07-24 19:06:44.817000 | Sí |
| `inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test` | VIEW | 2026-07-29 13:31:05.657000 | Sí |
| `inventar_SpcHidr.v_bitacora_rangos` | VIEW | 2026-05-14 01:24:38.343000 | Sí |
| `inventar_SpcHidr.v_clays_cufe_calculado_v2_test` | VIEW | 2026-08-03 02:32:08.163000 | Sí |
| `inventar_SpcHidr.v_conciliacion_chancado_v2` | VIEW | 2026-07-24 08:01:00.463000 | Sí |
| `inventar_SpcHidr.v_datos_apilado_tmh_v2` | VIEW | 2026-08-04 14:50:41.020000 | Sí |
| `inventar_SpcHidr.v_estado_apilado_turno_representatividad` | VIEW | 2026-07-24 08:01:00.770000 | Sí |
| `inventar_SpcHidr.v_he_10s_por_intervalo_excel` | VIEW | 2026-07-22 14:05:44.800000 | Sí |
| `inventar_SpcHidr.v_humedad_inventario_test` | VIEW | 2026-07-30 22:08:14.490000 | Sí |
| `inventar_SpcHidr.v_informe_tm_lab_norm` | VIEW | 2026-02-16 11:44:09.443000 | Sí |
| `inventar_SpcHidr.v_inventario_chancado_archive_test` | VIEW | 2026-08-04 14:18:33.377000 | Sí |
| `inventar_SpcHidr.v_inventario_chancado_test` | VIEW | 2026-08-01 16:25:53.713000 | Sí |
| `inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test` | VIEW | 2026-06-02 14:14:35.280000 | Sí |
| `inventar_SpcHidr.v_leyes_resueltas_data_tm_reporte_test_v2` | VIEW | 2026-06-11 13:33:08.517000 | Sí |
| `inventar_SpcHidr.v_leyes_validadas_tm_turno` | VIEW | 2026-06-01 09:41:44.870000 | Sí |
| `inventar_SpcHidr.v_peso_real_torre_turno_excel` | VIEW | 2026-07-11 12:30:11.863000 | Sí |
| `inventar_SpcHidr.v_peso_teorico_turno_torre_excel` | VIEW | 2026-07-11 13:13:31.710000 | Sí |
| `inventar_SpcHidr.v_reporte_diario_emulado_excel` | VIEW | 2026-05-19 17:08:29.950000 | Sí |
| `inventar_SpcHidr.v_reporte_diario_humedad_test` | VIEW | 2026-08-04 14:24:53.767000 | Sí |
| `inventar_SpcHidr.v_reporte_turno_campania_modulo_test` | VIEW | 2026-07-24 08:01:00.663000 | Sí |
| `inventar_SpcHidr.v_reporte_turno_fuentes_info_test` | VIEW | 2026-07-22 21:08:03.533000 | Sí |
| `inventar_SpcHidr.v_reporte_turno_reales_test` | VIEW | 2026-06-03 11:04:41.810000 | Sí |
| `inventar_SpcHidr.v_representatividad_diaria_calculada` | VIEW | 2026-07-11 13:30:22.050000 | Sí |
| `inventar_SpcHidr.v_representatividad_srr_turno_calculada` | VIEW | 2026-07-11 13:19:23.893000 | Sí |
| `inventar_SpcHidr.v_sal_ajustada` | VIEW | 2026-05-28 19:21:46.190000 | Sí |
| `inventar_SpcHidr.v_sal_ajustada_operacional_test` | VIEW | 2026-07-29 13:20:09.397000 | Sí |
| `inventar_SpcHidr.v_ton_por_intervalo_excel` | VIEW | 2026-07-22 14:05:44.643000 | Sí |
| `inventar_SpcHidr.v_validacion_leyes_tm1_v2` | VIEW | 2026-07-22 20:31:37.703000 | Sí |
| `inventar_SpcHidr.v_validacion_leyes_tm2_v2` | VIEW | 2026-07-22 20:37:04.947000 | Sí |

## Archivos

- `definiciones_bd.sql`: definiciones textuales vigentes de procedimientos, vistas y funciones alcanzadas.
- `definiciones_hidro_imp_chancado.sql`: definiciones vigentes extraídas de
  `PROD_SIIR` para `hidro.v_imp_chancado_normalizado` y
  `hidro.v_imp_conciliacion_chancado`. Se mantienen aparte porque son
  dependencias entre bases y `sys.sql_expression_dependencies` no entrega su
  `object_id` desde `inventar_SpcHidr`.
- `inventario_dependencias.tsv`: aristas del catálogo y referencias textuales detectadas.

## Limitaciones

SQL Server puede no registrar dependencias resueltas mediante SQL dinámico, sinónimos o referencias entre bases. Por eso este documento combina el catálogo con una inspección textual y debe regenerarse después de cambios en BD.
