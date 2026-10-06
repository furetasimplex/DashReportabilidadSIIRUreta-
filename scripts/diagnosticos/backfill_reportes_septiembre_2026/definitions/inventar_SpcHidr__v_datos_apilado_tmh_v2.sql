/* ================================================================
   ALTER inventar_SpcHidr.v_datos_apilado_tmh_v2
   ----------------------------------------------------------------
   Reemplaza el calculo en vivo (3 JOINs contra tot_TM por fecha,
   sin materializar) por una simple lectura de la tabla congelada
   inventar_SpcHidr.Control_Apilado_TMH_v2_test, poblada por
   sp_mantiene_apilado_tmh_v2_test.

   IMPORTANTE -- aplicar SOLO despues de:
   - correr crear_tabla_control_apilado_tmh_v2_test.sql
   - correr crear_sp_mantiene_apilado_tmh_v2_test.sql
   - confirmar que la consulta de comparacion fila a fila de ese
     script no devolvio ninguna diferencia

   Las columnas expuestas quedan exactamente iguales a las que ya
   entrega la vista hoy -- ningun consumidor (incluida
   v_apilado_tms_con_sal_srr_reporte_test, la metodologia de
   Apilado ya validada) necesita cambios.

   Consecuencia operativa: de ahora en adelante, alguien tiene que
   llamar a sp_mantiene_apilado_tmh_v2_test para que la vista vea
   dias nuevos. Mientras no se agregue esa llamada a un proceso
   automatico (job de SQL Agent o al inicio del pipeline de
   exportacion, igual que ya se hace con
   sp_mantiene_factor_ajuste_camiones_v2_test), los dias que no se
   hayan procesado explicitamente NO apareceran en esta vista.
   Recomendacion: agregar la misma llamada en
   report_export/report_export.py, junto al EXEC de
   sp_mantiene_factor_ajuste_camiones_v2_test que ya existe ahi,
   antes de dar esto por completamente integrado al flujo de
   exportacion. Esto queda pendiente de tu confirmacion -- no se
   modifico el Dash todavia.
================================================================ */
CREATE   VIEW
    [inventar_SpcHidr].[v_datos_apilado_tmh_v2]
AS
SELECT
    Fecha,
    ts_08_dia,
    ts_20_dia,
    ts_08_dia_siguiente,
    CV008_Totalizador_08,
    CV008_Totalizador_20,
    CV008_Totalizador_08_Dia_Siguiente,
    CV108_Totalizador_08,
    CV108_Totalizador_20,
    CV108_Totalizador_08_Dia_Siguiente,
    TMH_CV008_A_Bruto,
    TMH_CV008_B_Bruto,
    TMH_CV108_A_Bruto,
    TMH_CV108_B_Bruto,
    Flag_Apilado_Valido,
    TMH_CV008_A,
    TMH_CV008_B,
    TMH_CV108_A,
    TMH_CV108_B,
    TMH_Apilado_Total_A,
    TMH_Apilado_Total_B,
    TMH_Apilado_Total_Dia,
    Flag_Apilado_Valido_A,
    Flag_Apilado_Valido_B
FROM inventar_SpcHidr.Control_Apilado_TMH_v2_test;