CREATE   PROCEDURE inventar_SpcHidr.sp_rep_merge_ajustado
    @run_id UNIQUEIDENTIFIER
AS
BEGIN

SET NOCOUNT ON;

MERGE inventar_SpcHidr.rep_prod_ajustado AS tgt
USING
(
    SELECT *
    FROM inventar_SpcHidr.rep_prod_ajustado_stg
    WHERE run_id = @run_id
) AS src

ON tgt.Fecha = src.Fecha

WHEN MATCHED THEN
UPDATE SET

    tgt.Chancado_TMS_Real                    = src.Chancado_TMS_Real,
    tgt.Humedad_Turno_A                      = src.Humedad_Turno_A,
    tgt.Humedad_Turno_B                      = src.Humedad_Turno_B,
    tgt.Humedad_promedio_dia                 = src.Humedad_promedio_dia,
    tgt.Sal_turno_A                          = src.Sal_turno_A,
    tgt.Sal_Turno_B                          = src.Sal_Turno_B,
    tgt.Sal_promedio_dia                     = src.Sal_promedio_dia,
    tgt.Apilado_TMH_turno_A                  = src.Apilado_TMH_turno_A,
    tgt.Apilado_TMH_turno_B                  = src.Apilado_TMH_turno_B,
    tgt.Apilado_TMH_promedio_dia             = src.Apilado_TMH_promedio_dia,
    tgt.Apilado_TMS_Real                     = src.Apilado_TMS_Real,
    tgt.Apilado_TMS_Plan                     = src.Apilado_TMS_Plan,
    tgt.Ley_CuT_Real                         = src.Ley_CuT_Real,
    tgt.Cobre_fino_Apilado_Real              = src.Cobre_fino_Apilado_Real,

    tgt.TMS_Rotopala_1_Real                  = src.TMS_Rotopala_1_Real,
    tgt.TMS_Rotopala_2_Real                  = src.TMS_Rotopala_2_Real,
    tgt.Camiones_TMS_Reclamo_Oxidos          = src.Camiones_TMS_Reclamo_Oxidos,
    tgt.Camiones_TMS_Reclamo_Sulfuros        = src.Camiones_TMS_Reclamo_Sulfuros,

    tgt.Total_Ripios_Incluye_Camiones_Real   = src.Total_Ripios_Incluye_Camiones_Real,

    tgt.estado                               = 1,

    tgt.run_id                               = src.run_id,
    tgt.caso_id                              = src.caso_id,
    tgt.version_reglas                       = src.version_reglas,
    tgt.ts_ajuste                            = src.ts_ajuste,
    tgt.factor_chancado                      = src.factor_chancado,
    tgt.factor_sal                           = src.factor_sal,
    tgt.factor_finos                         = src.factor_finos


WHEN NOT MATCHED THEN
INSERT
(
    Fecha,

    Chancado_TMS_Real,
    Humedad_Turno_A,
    Humedad_Turno_B,
    Humedad_promedio_dia,
    Sal_turno_A,
    Sal_Turno_B,
    Sal_promedio_dia,
    Apilado_TMH_turno_A,
    Apilado_TMH_turno_B,
    Apilado_TMH_promedio_dia,
    Apilado_TMS_Real,
    Apilado_TMS_Plan,
    Ley_CuT_Real,
    Cobre_fino_Apilado_Real,

    TMS_Rotopala_1_Real,
    TMS_Rotopala_2_Real,
    Camiones_TMS_Reclamo_Oxidos,
    Camiones_TMS_Reclamo_Sulfuros,

    Total_Ripios_Incluye_Camiones_Real,

    estado,
    run_id,
    caso_id,
    version_reglas,
    ts_ajuste,
    factor_chancado,
    factor_sal,
    factor_finos
)

VALUES
(
    src.Fecha,

    src.Chancado_TMS_Real,
    src.Humedad_Turno_A,
    src.Humedad_Turno_B,
    src.Humedad_promedio_dia,
    src.Sal_turno_A,
    src.Sal_Turno_B,
    src.Sal_promedio_dia,
    src.Apilado_TMH_turno_A,
    src.Apilado_TMH_turno_B,
    src.Apilado_TMH_promedio_dia,
    src.Apilado_TMS_Real,
    src.Apilado_TMS_Plan,
    src.Ley_CuT_Real,
    src.Cobre_fino_Apilado_Real,

    src.TMS_Rotopala_1_Real,
    src.TMS_Rotopala_2_Real,
    src.Camiones_TMS_Reclamo_Oxidos,
    src.Camiones_TMS_Reclamo_Sulfuros,

    src.Total_Ripios_Incluye_Camiones_Real,

    1,
    src.run_id,
    src.caso_id,
    src.version_reglas,
    src.ts_ajuste,
    src.factor_chancado,
    src.factor_sal,
    src.factor_finos
);

END