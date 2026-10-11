


/*==============================================================
  SULFURO
==============================================================*/
CREATE   VIEW inventar_SpcHidr.v_drena_sulfuro_operacional
AS
SELECT
    d.id_registro,

    /* trazabilidad original */
    d.fecha_registro AS fecha_registro_raw,

    /* fecha usada por lógica operacional */
    CASE
        WHEN d.fecha_registro >= '2026-06-01T21:00:00'
         AND DATEPART(HOUR, d.fecha_registro) >= 20
        THEN DATEADD(
                 DAY,
                 1,
                 CAST(d.fecha_registro AS date)
             )
        ELSE CAST(d.fecha_registro AS date)
    END AS fecha_operacional,

    d.parcela_numero,
    d.cu_pp

FROM inventar_SpcHidr.v_drena_sulfuro_unpivot d;
