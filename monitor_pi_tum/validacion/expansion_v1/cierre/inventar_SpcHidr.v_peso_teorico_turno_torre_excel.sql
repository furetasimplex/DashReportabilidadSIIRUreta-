CREATE VIEW inventar_SpcHidr.v_peso_teorico_turno_torre_excel
AS

WITH base AS
(
    SELECT
        r.Fecha,
        r.Turno,
        r.Torre,
        r.Horas_Reales,
        r.Factor_Masa,
        r.ts_ini,
        r.ts_fin,
        p.PesoBase_Quimico_12h,
        p.PesoBase_Fisico_12h,

        Fraccion_Muestreo =
            CASE
                WHEN r.ts_ini IS NULL
                  OR r.ts_fin IS NULL
                  OR r.ts_fin <= r.ts_ini
                    THEN 1.0

                ELSE
                    DATEDIFF(MINUTE, r.ts_ini, r.ts_fin)
                    / 720.0
            END,

        Factor_Comun =
            CASE
                WHEN r.Horas_Reales IS NULL
                  OR r.Horas_Reales <= 0
                    THEN NULL

                WHEN r.Factor_Masa IS NULL
                    THEN NULL

                ELSE
                    r.Factor_Masa
                    * (r.Horas_Reales / 12.0)
                    *
                    CASE
                        WHEN r.ts_ini IS NULL
                          OR r.ts_fin IS NULL
                          OR r.ts_fin <= r.ts_ini
                            THEN 1.0

                        ELSE
                            DATEDIFF(
                                MINUTE,
                                r.ts_ini,
                                r.ts_fin
                            ) / 720.0
                    END
            END

    FROM inventar_SpcHidr.v_reporte_diario_emulado_excel AS r

    INNER JOIN inventar_SpcHidr.param_peso_teorico_base AS p
        ON  p.Torre = r.Torre
        AND p.Activo = 1

    WHERE r.Torre IN ('T1', 'T2', 'SRR')
)

SELECT
    Fecha,
    Turno,
    Torre,
    Horas_Reales,
    Factor_Masa,
    ts_ini,
    ts_fin,
    PesoBase_Quimico_12h,
    PesoBase_Fisico_12h,
    Fraccion_Muestreo,

    PesoTeo_Quimico =
        CASE
            WHEN Horas_Reales IS NULL
              OR Horas_Reales <= 0
                THEN 0

            WHEN Factor_Comun IS NULL
                THEN NULL

            WHEN PesoBase_Quimico_12h IS NULL
                THEN NULL

            ELSE
                PesoBase_Quimico_12h
                * Factor_Comun
        END,

    PesoTeo_Fisico =
        CASE
            WHEN Horas_Reales IS NULL
              OR Horas_Reales <= 0
                THEN 0

            WHEN Factor_Comun IS NULL
                THEN NULL

            WHEN PesoBase_Fisico_12h IS NULL
                THEN NULL

            ELSE
                PesoBase_Fisico_12h
                * Factor_Comun
        END

FROM base;
