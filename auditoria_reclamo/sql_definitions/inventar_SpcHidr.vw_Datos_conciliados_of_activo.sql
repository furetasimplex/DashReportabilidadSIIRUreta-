
CREATE   VIEW [inventar_SpcHidr].[vw_Datos_conciliados_of_activo]
AS
WITH ActiveRun AS (
    SELECT TOP (1) ar.run_id
    FROM [inventar_SpcHidr].Datos_conciliados_of_active_run ar
    ORDER BY ar.ts_set DESC
)
SELECT v.[Fecha], v.[Chancado_TMS_Real], v.[Humedad_Turno_A], v.[Humedad_Turno_B], v.[Humedad_promedio_dia], v.[Sal_turno_A], v.[Sal_Turno_B], v.[Sal_promedio_dia], v.[Apilado_TMH_turno_A], v.[Apilado_TMH_turno_B], v.[Apilado_TMH_promedio_dia], v.[Apilado_TMS_Real], v.[Apilado_TMS_Plan], v.[Campana_apilado], v.[Modulo_apilado], v.[Avance_apilado], v.[Ley_CuT_Real], v.[Ley_CuT_Plan], v.[Cobre_fino_Apilado_Real], v.[Cobre_fino_Apilado_Plan], v.[TMS_Rotopala_1_Real], v.[TMS_Rotopala_1_Plan], v.[Campana_reclamo_oxidos], v.[Modulo_reclamo_oxidos], v.[Avance_reclamo_oxidos], v.[TMS_Rotopala_2_Real], v.[TMS_Rotopala_2_Plan], v.[Campana_reclamo_sulfuros], v.[modulo_reclamo_sulfuros], v.[Avance_reclamo_sulfuros], v.[Camiones_TMS_Reclamo_Oxidos], v.[Camiones_TMS_Reclamo_Sulfuros], v.[Movido], v.[Extraido], v.[Camiones_TMS_total], v.[Camiones_TMS_plan], v.[Campana_reclamo_camiones], v.[Modulo_reclamo_camiones], v.[Total_Ripios_Incluye_Camiones_Real], v.[Total_Ripios_Incluye_Camiones_Plan], v.[Produccion_Catodos_Real], v.[Produccion_Catodos_Plan], v.[SRR_TMS_Turno_A], v.[SRR_TMS_Turno_B], v.[SRR_TMS_promedio_dia], v.[SRR_TMS_Plan], v.[Ley_CuT_Real_srr], v.[Ley_CuT_Plan_srr], v.[estado]
FROM [inventar_SpcHidr].[Datos_conciliados_of_ver] v
CROSS JOIN ActiveRun a
WHERE v.run_id = a.run_id
  AND v.es_activa = 1

UNION ALL

SELECT b.[Fecha], b.[Chancado_TMS_Real], b.[Humedad_Turno_A], b.[Humedad_Turno_B], b.[Humedad_promedio_dia], b.[Sal_turno_A], b.[Sal_Turno_B], b.[Sal_promedio_dia], b.[Apilado_TMH_turno_A], b.[Apilado_TMH_turno_B], b.[Apilado_TMH_promedio_dia], b.[Apilado_TMS_Real], b.[Apilado_TMS_Plan], b.[Campana_apilado], b.[Modulo_apilado], b.[Avance_apilado], b.[Ley_CuT_Real], b.[Ley_CuT_Plan], b.[Cobre_fino_Apilado_Real], b.[Cobre_fino_Apilado_Plan], b.[TMS_Rotopala_1_Real], b.[TMS_Rotopala_1_Plan], b.[Campana_reclamo_oxidos], b.[Modulo_reclamo_oxidos], b.[Avance_reclamo_oxidos], b.[TMS_Rotopala_2_Real], b.[TMS_Rotopala_2_Plan], b.[Campana_reclamo_sulfuros], b.[modulo_reclamo_sulfuros], b.[Avance_reclamo_sulfuros], b.[Camiones_TMS_Reclamo_Oxidos], b.[Camiones_TMS_Reclamo_Sulfuros], b.[Movido], b.[Extraido], b.[Camiones_TMS_total], b.[Camiones_TMS_plan], b.[Campana_reclamo_camiones], b.[Modulo_reclamo_camiones], b.[Total_Ripios_Incluye_Camiones_Real], b.[Total_Ripios_Incluye_Camiones_Plan], b.[Produccion_Catodos_Real], b.[Produccion_Catodos_Plan], b.[SRR_TMS_Turno_A], b.[SRR_TMS_Turno_B], b.[SRR_TMS_promedio_dia], b.[SRR_TMS_Plan], b.[Ley_CuT_Real_srr], b.[Ley_CuT_Plan_srr], b.[estado]
FROM [inventar_SpcHidr].[Datos_conciliados_of] b
WHERE NOT EXISTS (
    SELECT 1
    FROM [inventar_SpcHidr].[Datos_conciliados_of_ver] v
    CROSS JOIN ActiveRun a
    WHERE v.run_id = a.run_id
      AND v.es_activa = 1
      AND v.[Fecha] = b.[Fecha]
);
