USE [inventar_SpcHidr];
GO

IF OBJECT_ID('tempdb..#factor_actual') IS NOT NULL DROP TABLE #factor_actual;
IF OBJECT_ID('tempdb..#factor_nuevo') IS NOT NULL DROP TABLE #factor_nuevo;

/* Los esquemas de ambas tablas corresponden a las salidas diagnósticas. */
CREATE TABLE #factor_actual
(
    Fecha date, Apilado_TMH_Bruto float, Apilado_TMH_Neto float,
    Sal_Dia float, Humedad_Inventario float, Apilado_TMS_Sin_Ajuste float,
    Total_Inventario_Chancado_TMS float, Inventario_Chancado_TMS_Anterior float,
    Delta_Inventario_Chancado_TMS float, SRR_TMS_Dia float,
    Mineral_Chancado_TMS_Sin_Ajuste float, Chancado_TMS_Sin_Ajuste float,
    Chancado_TMH_Sin_Ajuste float, Produccion_KOM_TMH float,
    Produccion_CAT_TMH float, Dato_Mina_TMH float, Vueltas_KOM float,
    Vueltas_CAT float, Participacion_KOM float, Participacion_CAT float,
    Chancado_KOM_TMH_Sin_Ajuste float, Chancado_CAT_TMH_Sin_Ajuste float,
    Carga_KOM_Sin_Ajuste float, Carga_CAT_Sin_Ajuste float,
    KOM_TMH_Corregido float, CAT_TMH_Corregido float,
    Chancado_TMH_Corregido_Total float, Factor_Ajuste_Calculado float,
    Flag_Factor_Ajuste_Valido int, Estado_Calculo varchar(80),
    Cantidad_Registros_Originales bigint, Cantidad_Registros_Validos bigint,
    Cantidad_Duplicados_Eliminados bigint, Check_TMH_Bruto float,
    Check_Produccion_Flotas float, Flag_Continuidad_Diaria int,
    Flag_Inventario_Valido int, Flag_Humedad_Inventario_Valida int
);

CREATE TABLE #factor_nuevo
(
    Fecha date, SRR_TMS_Turno_A_Origen decimal(38,10),
    SRR_TMS_Turno_B_Origen decimal(38,10), SRR_TMS_Dia_Origen decimal(38,10),
    Fuente_SRR_Turno_A varchar(20), Fuente_SRR_Turno_B varchar(20),
    Flag_SRR_Capeado_A bit, Flag_SRR_Capeado_B bit,
    Chancado_TMS_Sin_Ajuste float, Chancado_TMH_Sin_Ajuste float,
    Produccion_KOM_TMH float, Produccion_CAT_TMH float, Vueltas_KOM float,
    Vueltas_CAT float, Carga_KOM_Sin_Ajuste float, Carga_CAT_Sin_Ajuste float,
    KOM_TMH_Corregido float, CAT_TMH_Corregido float,
    Factor_Ajuste_Calculado float, Flag_Factor_Ajuste_Valido int,
    Estado_Calculo varchar(80)
);

INSERT #factor_actual EXEC [inventar_SpcHidr].[sp_factor_ajuste_camiones_test]
    @FechaInicio='20260801', @FechaFin='20260831';
INSERT #factor_nuevo EXEC [inventar_SpcHidr].[sp_factor_ajuste_camiones_srr_origen_test]
    @FechaInicio='20260801', @FechaFin='20260831';

SELECT
    a.Fecha,
    a.SRR_TMS_Dia AS SRR_TMS_Actual_Cache,
    n.SRR_TMS_Dia_Origen AS SRR_TMS_Origen,
    n.SRR_TMS_Dia_Origen - a.SRR_TMS_Dia AS Delta_SRR_TMS,
    a.Chancado_TMS_Sin_Ajuste AS Chancado_TMS_Actual,
    n.Chancado_TMS_Sin_Ajuste AS Chancado_TMS_Nuevo,
    n.Chancado_TMS_Sin_Ajuste - a.Chancado_TMS_Sin_Ajuste AS Delta_Chancado_TMS,
    a.Chancado_TMH_Sin_Ajuste AS Chancado_TMH_Actual,
    n.Chancado_TMH_Sin_Ajuste AS Chancado_TMH_Nuevo,
    n.Chancado_TMH_Sin_Ajuste - a.Chancado_TMH_Sin_Ajuste AS Delta_Chancado_TMH,
    a.Factor_Ajuste_Calculado AS Factor_Actual,
    n.Factor_Ajuste_Calculado AS Factor_Nuevo,
    n.Factor_Ajuste_Calculado - a.Factor_Ajuste_Calculado AS Delta_Factor,
    n.Fuente_SRR_Turno_A, n.Fuente_SRR_Turno_B,
    n.Flag_SRR_Capeado_A, n.Flag_SRR_Capeado_B,
    a.Estado_Calculo AS Estado_Actual, n.Estado_Calculo AS Estado_Nuevo
FROM #factor_actual AS a
FULL JOIN #factor_nuevo AS n ON n.Fecha = a.Fecha
ORDER BY COALESCE(a.Fecha, n.Fecha);
GO
