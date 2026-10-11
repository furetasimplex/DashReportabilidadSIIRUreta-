CREATE   VIEW inventar_SpcHidr.v_informe_tm_lab_norm
AS
WITH B AS (
    SELECT
        l.ID_Registro,
        -- Estandarización de Nombres de Torre
        Torre = CASE 
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('T1', 'TM1', 'TORRE 1') THEN 'T1'
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('T2', 'TM2', 'TORRE 2') THEN 'T2'
            WHEN UPPER(LTRIM(RTRIM(l.Torre))) IN ('SRR', 'TM3', 'TORRE 3', 'CV-01') THEN 'SRR'
            ELSE UPPER(LTRIM(RTRIM(l.Torre)))
        END,
        fecha_rec = TRY_CONVERT(date, l.Fecha_Recepcion),
        hora_rec  = TRY_CONVERT(time(0), l.Hora),
        l.CuT_global,
        l.CuS_Global,
        l.Fe_Global,
        l.Humedad_Prom_Pct,
        l.RetParcial_2P, -- Asegúrate de incluir las columnas físicas
        l.RetParcial_1P
    FROM inventar_SpcHidr.informe_tm_lab l
)
SELECT
    ID_Registro,
    Torre,
    fecha_muestra_min =
        CASE
            WHEN fecha_rec IS NOT NULL AND hora_rec IS NOT NULL
            THEN DATEADD(MINUTE, DATEDIFF(MINUTE, 0,
                    DATEADD(SECOND, DATEDIFF(SECOND, 0, hora_rec), CAST(fecha_rec AS datetime2(0)))
                 ), 0)
            ELSE NULL
        END,
    CuT_global,
    CuS_Global,
    Fe_Global,
    Humedad_Prom_Pct,
    RetParcial_2P,
    RetParcial_1P
FROM B
WHERE Torre IN ('T1','T2','SRR'); -- Agregamos SRR al filtro