# Datos Conciliados: dependencias SQL

> Extraccion de solo lectura: `2026-08-21 14:14:23.707883-03:00`
> Servidor: `VPS-5347319-X`
> Base de datos: `inventar_SpcHidr`

## Flujo ejecutado por la aplicacion

```text
Vista previa / Excel / PDF
├── EXEC inventar_SpcHidr.sp_refrescar_historico_apilado_test
├── EXEC inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test
└── SELECT inventar_SpcHidr.Datos_conciliados_of
    └── Excel además consulta inventar_SpcHidr.v_ajuste_camiones_emision_test
```

## Árbol de dependencias de base de datos

Las aristas `[catalogo]` provienen de `sys.sql_expression_dependencies`;
las `[texto]` fueron encontradas en la definición y pueden incluir SQL dinámico.

```text
inventar_SpcHidr.sp_refrescar_historico_apilado_test [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.Historico_Apilado_Diario [USER_TABLE]
└── [catalogo] inventar_SpcHidr.v_reporte_diario_apilado_test [VIEW]
        ├── [catalogo] inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test [VIEW]
        │       ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW]
        │       │       ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │       │       ├── [catalogo] inventar_SpcHidr.factor_ajuste_camiones [USER_TABLE]
        │       │       ├── [catalogo] inventar_SpcHidr.humedad_inicial_tm_periodo [USER_TABLE]
        │       │       ├── [catalogo] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW]
        │       │       │       └── [catalogo] inventar_SpcHidr.Control_Apilado_TMH_v2_test [USER_TABLE]
        │       │       └── [catalogo] inventar_SpcHidr.v_representatividad_diaria_calculada [VIEW]
        │       │               ├── [catalogo] inventar_SpcHidr.v_peso_real_torre_turno_excel [VIEW]
        │       │               │       └── [catalogo] inventar_SpcHidr.peso_real_torre_turno [USER_TABLE]
        │       │               ├── [catalogo] inventar_SpcHidr.v_peso_teorico_turno_torre_excel [VIEW]
        │       │               │       ├── [catalogo] inventar_SpcHidr.param_peso_teorico_base [USER_TABLE]
        │       │               │       └── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW]
        │       │               │               ├── [catalogo] inventar_SpcHidr.v_bitacora_rangos [VIEW]
        │       │               │               │       └── [catalogo] inventar_SpcHidr.bitacora_turnos_consolidada [USER_TABLE]
        │       │               │               ├── [catalogo] inventar_SpcHidr.v_he_10s_por_intervalo_excel [VIEW]
        │       │               │               │       └── [catalogo] inventar_SpcHidr.Resumen_Intervalo_TotTM [USER_TABLE]
        │       │               │               ├── [catalogo] inventar_SpcHidr.v_informe_tm_lab_norm [VIEW]
        │       │               │               │       └── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
        │       │               │               └── [catalogo] inventar_SpcHidr.v_ton_por_intervalo_excel [VIEW]
        │       │               │                       └── [catalogo] inventar_SpcHidr.Resumen_Intervalo_TotTM [USER_TABLE]
        │       │               ├── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW] (dependencias ya mostradas)
        │       │               └── [catalogo] inventar_SpcHidr.v_representatividad_srr_turno_calculada [VIEW]
        │       │                       ├── [catalogo] inventar_SpcHidr.v_estado_apilado_turno_representatividad [VIEW]
        │       │                       │       └── [catalogo] inventar_SpcHidr.v_datos_apilado_tmh_v2 [VIEW] (dependencias ya mostradas)
        │       │                       ├── [catalogo] inventar_SpcHidr.v_peso_real_torre_turno_excel [VIEW] (dependencias ya mostradas)
        │       │                       ├── [catalogo] inventar_SpcHidr.v_peso_teorico_turno_torre_excel [VIEW] (dependencias ya mostradas)
        │       │                       └── [catalogo] inventar_SpcHidr.v_reporte_diario_emulado_excel [VIEW] (dependencias ya mostradas)
        │       └── [catalogo] inventar_SpcHidr.v_sal_ajustada_operacional_test [VIEW]
        │               ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW] (dependencias ya mostradas)
        │               └── [catalogo] inventar_SpcHidr.v_sal_ajustada [VIEW]
        │                       ├── [catalogo] inventar_SpcHidr.datos_filtrados [USER_TABLE]
        │                       └── [catalogo] inventar_SpcHidr.topografia_sal [USER_TABLE]
        └── [catalogo] inventar_SpcHidr.v_reporte_diario_humedad_test [VIEW]
                ├── [catalogo] inventar_SpcHidr.Informe_TM_lab [USER_TABLE]
                ├── [catalogo] inventar_SpcHidr.humedad_inicial_tm_periodo [USER_TABLE]
                ├── [catalogo] inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test [VIEW] (dependencias ya mostradas)
                └── [catalogo] inventar_SpcHidr.v_representatividad_diaria_calculada [VIEW] (dependencias ya mostradas)

inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test [SQL_STORED_PROCEDURE]
├── [catalogo] inventar_SpcHidr.Datos_conciliados_of [USER_TABLE]
├── [catalogo] inventar_SpcHidr.Historico_Apilado_Diario [USER_TABLE]
├── [catalogo] inventar_SpcHidr.campaña [USER_TABLE]
├── [catalogo] inventar_SpcHidr.configuracion_reclamo_rotopala_periodo [USER_TABLE]
├── [catalogo] inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario [USER_TABLE]
├── [catalogo] inventar_SpcHidr.fn_generador_reporte_diario_emision_test [SQL_INLINE_TABLE_VALUED_FUNCTION]
│       ├── [catalogo] inventar_SpcHidr.plan_mensual_reporte_turno [USER_TABLE]
│       ├── [catalogo] inventar_SpcHidr.plan_semanal_reporte_turno [USER_TABLE]
│       └── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
├── [catalogo] inventar_SpcHidr.mov_cam [USER_TABLE]
├── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
├── [catalogo] inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test [SQL_STORED_PROCEDURE]
│       ├── [catalogo] inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test [USER_TABLE]
│       ├── [catalogo] inventar_SpcHidr.sp_factor_ajuste_camiones_test [SQL_STORED_PROCEDURE]
│       │       ├── [catalogo] inventar_SpcHidr.Historico_Apilado_Diario [USER_TABLE]
│       │       ├── [texto] inventar_SpcHidr.mov_cam [USER_TABLE]
│       │       ├── [catalogo] inventar_SpcHidr.mov_cam_powerbi [USER_TABLE]
│       │       ├── [catalogo] inventar_SpcHidr.v_humedad_inventario_test [VIEW]
│       │       │       └── [catalogo] inventar_SpcHidr.v_reporte_diario_humedad_test [VIEW] (dependencias ya mostradas)
│       │       ├── [catalogo] inventar_SpcHidr.v_inventario_chancado_test [VIEW]
│       │       │       └── [catalogo] inventar_SpcHidr.v_inventario_chancado_archive_test [VIEW]
│       │       │               ├── [catalogo] inventar_SpcHidr.datos_filtrados [USER_TABLE]
│       │       │               ├── [catalogo] inventar_SpcHidr.semilla_inventario_chancado [USER_TABLE]
│       │       │               └── [catalogo] inventar_SpcHidr.v_humedad_inventario_test [VIEW] (dependencias ya mostradas)
│       │       └── [catalogo] inventar_SpcHidr.v_srr_tms_origen_turno_emision_test [VIEW]
│       │               ├── [catalogo] inventar_SpcHidr.reporte_turno_cache_emision_test [USER_TABLE]
│       │               ├── [catalogo] inventar_SpcHidr.v_apilado_base_mina_stock_srr [VIEW]
│       │               │       └── [catalogo] inventar_SpcHidr.mov_cam [USER_TABLE]
│       │               └── [catalogo] inventar_SpcHidr.v_conciliacion_chancado_v2 [VIEW]
│       │                       └── [catalogo] inventar_SpcHidr.resumen_mina [VIEW]
│       │                               └── [catalogo] inventar_SpcHidr.mov_cam [USER_TABLE]
│       └── [catalogo] inventar_SpcHidr.v_srr_tms_origen_turno_emision_test [VIEW] (dependencias ya mostradas)
├── [catalogo] inventar_SpcHidr.v_ajuste_camiones_emision_test [VIEW]
│       └── [catalogo] inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test [USER_TABLE]
├── [catalogo] inventar_SpcHidr.v_planes_mensuales_diarios_test [VIEW]
│       └── [catalogo] inventar_SpcHidr.planes_mensuales [USER_TABLE]
├── [catalogo] inventar_SpcHidr.v_produccion_catodica_diaria_test [VIEW]
│       └── [catalogo] inventar_SpcHidr.produccion_catodica [USER_TABLE]
└── [catalogo] reclamo.v_reclamo_para_conciliados [VIEW]
        ├── [texto] reclamo.calculo_diario [USER_TABLE]
        └── [catalogo] reclamo.v_reclamo_diario [VIEW]
                ├── [catalogo] reclamo.fn_fecha_corte [SQL_SCALAR_FUNCTION]
                │       └── [catalogo] reclamo.configuracion [USER_TABLE]
                ├── [catalogo] reclamo.v_ajustes_aplicables [VIEW]
                │       └── [catalogo] reclamo.ajuste_manual [USER_TABLE]
                ├── [catalogo] reclamo.v_camiones_acumulado [VIEW]
                │       └── [catalogo] reclamo.camiones_reclamo [USER_TABLE]
                ├── [catalogo] reclamo.v_modulo_base [VIEW]
                │       ├── [catalogo] inventar_SpcHidr.modulo [USER_TABLE]
                │       ├── [catalogo] reclamo.modulo_congelado [USER_TABLE]
                │       ├── [catalogo] reclamo.secuencia_rotopala [USER_TABLE]
                │       └── [catalogo] reclamo.topologia_pad [USER_TABLE]
                ├── [catalogo] reclamo.v_preliminar_cv25 [VIEW]
                │       ├── [catalogo] reclamo.v_cv25_diario [VIEW]
                │       │       ├── [catalogo] reclamo.cv25_diario [USER_TABLE]
                │       │       └── [catalogo] reclamo.rotopala_horas_turno [USER_TABLE]
                │       └── [catalogo] reclamo.v_modulo_base [VIEW] (dependencias ya mostradas)
                └── [catalogo] reclamo.v_topografia_resuelta [VIEW]
                        ├── [catalogo] reclamo.modulo_congelado [USER_TABLE]
                        └── [catalogo] reclamo.topografia_avance [USER_TABLE]

inventar_SpcHidr.Datos_conciliados_of [USER_TABLE]

inventar_SpcHidr.v_ajuste_camiones_emision_test [VIEW] (ver definición anterior)

reclamo.v_reclamo_para_conciliados [VIEW] (ver definición anterior)

```

## Objetos incluidos

| Objeto | Tipo | Última modificación | Definición exportada |
|---|---|---:|---|
| `inventar_SpcHidr.Control_Apilado_TMH_v2_test` | USER_TABLE | 2026-08-04 14:47:44.723000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Control_Factor_Ajuste_Camiones_v2_test` | USER_TABLE | 2026-07-31 01:32:38.817000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Datos_conciliados_of` | USER_TABLE | 2026-07-06 10:39:24.833000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Historico_Apilado_Diario` | USER_TABLE | 2026-07-07 15:56:18.137000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Informe_TM_lab` | USER_TABLE | 2026-08-17 13:51:26.377000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.Resumen_Intervalo_TotTM` | USER_TABLE | 2026-07-22 14:05:44.430000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.bitacora_turnos_consolidada` | USER_TABLE | 2026-05-19 17:07:34.240000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.campaña` | USER_TABLE | 2025-10-16 14:30:54.387000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.configuracion_reclamo_rotopala_periodo` | USER_TABLE | 2026-07-27 00:01:21.973000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.control_reclamo_sulfuro_camiones_thm_diario` | USER_TABLE | 2026-07-15 12:25:50.130000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.datos_filtrados` | USER_TABLE | 2026-07-22 00:46:50.910000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.factor_ajuste_camiones` | USER_TABLE | 2026-05-28 18:57:18.897000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.fn_generador_reporte_diario_emision_test` | SQL_INLINE_TABLE_VALUED_FUNCTION | 2026-07-31 11:26:39.750000 | Sí |
| `inventar_SpcHidr.humedad_inicial_tm_periodo` | USER_TABLE | 2026-06-02 11:35:16.813000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.modulo` | USER_TABLE | 2026-07-28 00:06:43.100000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.mov_cam` | USER_TABLE | 2026-08-04 16:03:13.620000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.mov_cam_powerbi` | USER_TABLE | 2026-08-03 21:43:58.913000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.param_peso_teorico_base` | USER_TABLE | 2026-05-07 12:16:09.310000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.peso_real_torre_turno` | USER_TABLE | 2026-05-19 17:07:23.280000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.plan_mensual_reporte_turno` | USER_TABLE | 2026-06-01 18:57:11.347000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.plan_semanal_reporte_turno` | USER_TABLE | 2026-06-01 18:57:11.413000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.planes_mensuales` | USER_TABLE | 2026-08-04 10:21:23.150000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.produccion_catodica` | USER_TABLE | 2026-07-22 14:11:46.437000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.reporte_turno_cache_emision_test` | USER_TABLE | 2026-07-31 11:14:35.217000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.resumen_mina` | VIEW | 2026-02-11 13:13:03.167000 | Sí |
| `inventar_SpcHidr.semilla_inventario_chancado` | USER_TABLE | 2026-08-01 13:19:03.773000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.sp_factor_ajuste_camiones_test` | SQL_STORED_PROCEDURE | 2026-08-21 13:33:37.403000 | Sí |
| `inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test` | SQL_STORED_PROCEDURE | 2026-08-04 21:35:44.210000 | Sí |
| `inventar_SpcHidr.sp_mantiene_factor_ajuste_camiones_v2_test` | SQL_STORED_PROCEDURE | 2026-08-21 13:33:37.463000 | Sí |
| `inventar_SpcHidr.sp_refrescar_historico_apilado_test` | SQL_STORED_PROCEDURE | 2026-07-23 16:03:32.820000 | Sí |
| `inventar_SpcHidr.topografia_sal` | USER_TABLE | 2026-05-28 10:01:37.457000 | No (tabla u objeto sin módulo SQL) |
| `inventar_SpcHidr.v_ajuste_camiones_emision_test` | VIEW | 2026-07-31 01:39:53.870000 | Sí |
| `inventar_SpcHidr.v_apilado_base_mina_stock_srr` | VIEW | 2026-06-01 10:12:33.767000 | Sí |
| `inventar_SpcHidr.v_apilado_tms_con_sal_srr_reporte_test` | VIEW | 2026-07-24 19:06:44.817000 | Sí |
| `inventar_SpcHidr.v_apilado_tms_sin_sal_con_srr_reporte_test` | VIEW | 2026-07-29 13:31:05.657000 | Sí |
| `inventar_SpcHidr.v_bitacora_rangos` | VIEW | 2026-05-14 01:24:38.343000 | Sí |
| `inventar_SpcHidr.v_conciliacion_chancado_v2` | VIEW | 2026-07-24 08:01:00.463000 | Sí |
| `inventar_SpcHidr.v_datos_apilado_tmh_v2` | VIEW | 2026-08-04 14:50:41.020000 | Sí |
| `inventar_SpcHidr.v_estado_apilado_turno_representatividad` | VIEW | 2026-07-24 08:01:00.770000 | Sí |
| `inventar_SpcHidr.v_he_10s_por_intervalo_excel` | VIEW | 2026-07-22 14:05:44.800000 | Sí |
| `inventar_SpcHidr.v_humedad_inventario_test` | VIEW | 2026-07-30 22:08:14.490000 | Sí |
| `inventar_SpcHidr.v_informe_tm_lab_norm` | VIEW | 2026-02-16 11:44:09.443000 | Sí |
| `inventar_SpcHidr.v_inventario_chancado_archive_test` | VIEW | 2026-08-04 14:18:33.377000 | Sí |
| `inventar_SpcHidr.v_inventario_chancado_test` | VIEW | 2026-08-01 16:25:53.713000 | Sí |
| `inventar_SpcHidr.v_peso_real_torre_turno_excel` | VIEW | 2026-07-11 12:30:11.863000 | Sí |
| `inventar_SpcHidr.v_peso_teorico_turno_torre_excel` | VIEW | 2026-07-11 13:13:31.710000 | Sí |
| `inventar_SpcHidr.v_planes_mensuales_diarios_test` | VIEW | 2026-06-17 15:52:47.310000 | Sí |
| `inventar_SpcHidr.v_produccion_catodica_diaria_test` | VIEW | 2026-06-17 10:54:09.003000 | Sí |
| `inventar_SpcHidr.v_reporte_diario_apilado_test` | VIEW | 2026-07-29 13:57:09.160000 | Sí |
| `inventar_SpcHidr.v_reporte_diario_emulado_excel` | VIEW | 2026-05-19 17:08:29.950000 | Sí |
| `inventar_SpcHidr.v_reporte_diario_humedad_test` | VIEW | 2026-08-04 14:24:53.767000 | Sí |
| `inventar_SpcHidr.v_representatividad_diaria_calculada` | VIEW | 2026-07-11 13:30:22.050000 | Sí |
| `inventar_SpcHidr.v_representatividad_srr_turno_calculada` | VIEW | 2026-07-11 13:19:23.893000 | Sí |
| `inventar_SpcHidr.v_sal_ajustada` | VIEW | 2026-05-28 19:21:46.190000 | Sí |
| `inventar_SpcHidr.v_sal_ajustada_operacional_test` | VIEW | 2026-07-29 13:20:09.397000 | Sí |
| `inventar_SpcHidr.v_srr_tms_origen_turno_emision_test` | VIEW | 2026-08-21 12:39:40.797000 | Sí |
| `inventar_SpcHidr.v_ton_por_intervalo_excel` | VIEW | 2026-07-22 14:05:44.643000 | Sí |
| `reclamo.ajuste_manual` | USER_TABLE | 2026-07-29 16:36:45.027000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.calculo_diario` | USER_TABLE | 2026-07-29 22:58:49.443000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.camiones_reclamo` | USER_TABLE | 2026-07-29 16:36:44.687000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.configuracion` | USER_TABLE | 2026-07-29 16:36:43.603000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.cv25_diario` | USER_TABLE | 2026-07-29 16:36:44.760000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.fn_fecha_corte` | SQL_SCALAR_FUNCTION | 2026-07-30 22:47:05.120000 | Sí |
| `reclamo.modulo_congelado` | USER_TABLE | 2026-07-29 16:36:44.160000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.rotopala_horas_turno` | USER_TABLE | 2026-07-29 16:36:44.877000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.secuencia_rotopala` | USER_TABLE | 2026-07-29 16:36:44.303000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.topografia_avance` | USER_TABLE | 2026-07-29 16:36:44.510000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.topologia_pad` | USER_TABLE | 2026-07-29 16:36:43.940000 | No (tabla u objeto sin módulo SQL) |
| `reclamo.v_ajustes_aplicables` | VIEW | 2026-07-30 10:03:49.203000 | Sí |
| `reclamo.v_camiones_acumulado` | VIEW | 2026-07-30 10:03:48.773000 | Sí |
| `reclamo.v_cv25_diario` | VIEW | 2026-07-30 10:03:48.977000 | Sí |
| `reclamo.v_modulo_base` | VIEW | 2026-07-30 10:03:48.680000 | Sí |
| `reclamo.v_preliminar_cv25` | VIEW | 2026-07-30 10:03:49.060000 | Sí |
| `reclamo.v_reclamo_diario` | VIEW | 2026-07-30 10:03:49.290000 | Sí |
| `reclamo.v_reclamo_para_conciliados` | VIEW | 2026-08-01 19:38:04.040000 | Sí |
| `reclamo.v_topografia_resuelta` | VIEW | 2026-07-30 10:03:48.890000 | Sí |

## Archivos

- `definiciones_bd.sql`: definiciones textuales vigentes de procedimientos, vistas y funciones alcanzadas.
- `inventario_dependencias.tsv`: aristas del catálogo y referencias textuales detectadas.

## Limitaciones

SQL Server puede no registrar dependencias resueltas mediante SQL dinámico, sinónimos o referencias entre bases. Por eso este documento combina el catálogo con una inspección textual y debe regenerarse después de cambios en BD.
