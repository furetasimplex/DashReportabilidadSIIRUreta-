/*==============================================================
  REFINO OXIDO - FECHA OPERACIONAL
==============================================================*/

CREATE   VIEW
inventar_SpcHidr.vw_riego_oxido_refino_operacional
AS
SELECT
    id_registro,

    /* fecha que consumen los procesos aguas abajo */
    CASE
        WHEN fecha_registro >= '2026-06-01T21:00:00'
         AND DATEPART(HOUR, fecha_registro) >= 20
        THEN DATEADD(DAY, 1, CAST(fecha_registro AS date))
        ELSE CAST(fecha_registro AS date)
    END AS fecha,

    /* trazabilidad */
    fecha_registro AS fecha_registro_raw,

    CASE
        WHEN fecha_registro >= '2026-06-01T21:00:00'
         AND DATEPART(HOUR, fecha_registro) >= 20
        THEN DATEADD(DAY, 1, CAST(fecha_registro AS date))
        ELSE CAST(fecha_registro AS date)
    END AS fecha_operacional,

    cu_pp,
    h_p,
    ph,
    cl,
    fet,
    fe2,
    eh

FROM inventar_SpcHidr.vw_riego_oxido_refino_base;
