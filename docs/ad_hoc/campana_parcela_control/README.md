# Mapa de dependencias: campaña parcela control

> Servidor: `VPS-5347319-X`  
> Base: `inventar_SpcHidr`  
> Extracción: `2026-08-14 13:43:09.052001-03:00`

## Objetos raíz

- `inventar_SpcHidr.campana_parcela_control` — USER_TABLE (modificado 2026-06-02 11:29:35.003000)
- `inventar_SpcHidr.sp_actualizar_campana_parcela_control` — SQL_STORED_PROCEDURE (modificado 2026-06-02 12:39:20.733000)

## Dependencias directas y transitivas

```text
inventar_SpcHidr.campana_parcela_control [USER_TABLE]

inventar_SpcHidr.sp_actualizar_campana_parcela_control [SQL_STORED_PROCEDURE]
├── [catálogo] inventar_SpcHidr.aux_parcela_columna [USER_TABLE]
├── [catálogo] inventar_SpcHidr.campana_parcela_control [USER_TABLE]
├── [catálogo] inventar_SpcHidr.campaña [USER_TABLE]
├── [catálogo] inventar_SpcHidr.mapa_campana_modulo_parcela [USER_TABLE]
├── [catálogo] inventar_SpcHidr.modulo [USER_TABLE]
├── [catálogo] inventar_SpcHidr.modulos_turnos [USER_TABLE]
├── [catálogo] inventar_SpcHidr.pad [USER_TABLE]
├── [catálogo] inventar_SpcHidr.parcela [USER_TABLE]
├── [catálogo] inventar_SpcHidr.v_drena_oxido_unpivot [VIEW]
│       └── [catálogo] inventar_SpcHidr.drena_concentrados_oxido [USER_TABLE]
├── [catálogo] inventar_SpcHidr.v_drena_sulfuro_unpivot [VIEW]
│       └── [catálogo] inventar_SpcHidr.drena_concentrados_sulfuro [USER_TABLE]
├── [catálogo] inventar_SpcHidr.v_flujos_oxido_unpivot [VIEW]
│       └── [catálogo] inventar_SpcHidr.flujos_reales_oxido [USER_TABLE]
└── [catálogo] inventar_SpcHidr.v_flujos_sulfuro_unpivot [VIEW]
        └── [catálogo] inventar_SpcHidr.flujos_reales_sulfuro [USER_TABLE]

```

## Dependencias inversas: quién los usa

- `[catálogo]` `inventar_SpcHidr.sp_actualizar_campana_parcela_control` — SQL_STORED_PROCEDURE
- `[catálogo]` `inventar_SpcHidr.sp_calcular_balance_flujos_v2` — SQL_STORED_PROCEDURE
- `[texto]` `inventar_SpcHidr.sp_curvas_recuperacion` — SQL_STORED_PROCEDURE
- `[catálogo]` `inventar_SpcHidr.sp_flujo_riego_drenaje` — SQL_STORED_PROCEDURE
- `[catálogo]` `inventar_SpcHidr.sp_razon_lixiviacion` — SQL_STORED_PROCEDURE
- `[catálogo]` `inventar_SpcHidr.sp_resumen_campana` — SQL_STORED_PROCEDURE
- `[catálogo]` `inventar_SpcHidr.vw_estado_operacional_campana_parcela` — VIEW
- `[catálogo]` `inventar_SpcHidr.vw_tablero_lixiviacion_final` — VIEW

## Triggers

- No se encontraron triggers asociados ni triggers que referencien literalmente los objetos.

## Ejecuciones programadas (SQL Server Agent)

- No se encontraron pasos de jobs que contengan literalmente estos nombres.

## Ejecución desde el código de la aplicación

La búsqueda en el repositorio no encontró llamadas ni referencias a estos nombres.

## Limitaciones

Las dependencias por sinónimos, otras bases, jobs de SQL Server Agent, triggers deshabilitados o SQL dinámico construido sin el nombre literal pueden no aparecer.
