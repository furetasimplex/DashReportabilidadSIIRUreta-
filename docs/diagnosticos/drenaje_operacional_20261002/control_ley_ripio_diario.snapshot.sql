-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE VIEW inventar_SpcHidr.control_ley_ripio_diario

AS

WITH base AS (

   SELECT

       r.Fecha_drenaje,

       r.Campana,

       r.PAD,

       r.Parcela,

       r.fino_apilado_cu,

       r.tms_apilado,

       r.fino_producido,

       LAG(r.fino_producido) OVER (

           PARTITION BY r.PAD, r.Campana, r.Parcela

           ORDER BY r.Fecha_drenaje

       ) AS fino_prev

   FROM inventar_SpcHidr.control_ley_ripio r

)

SELECT

   base.Fecha_drenaje,

   base.Campana,

   base.PAD,

   base.Parcela,

   base.fino_apilado_cu,

   base.tms_apilado,

   base.fino_producido,

   CASE

       WHEN (base.fino_producido - COALESCE(base.fino_prev, 0)) > 0

       THEN (base.fino_producido - COALESCE(base.fino_prev, 0))

       ELSE 0

   END AS fino_dia,

   CASE

       WHEN base.fino_apilado_cu > 0 THEN

           (100 *

               CASE

                   WHEN (base.fino_producido - COALESCE(base.fino_prev, 0)) > 0

                   THEN (base.fino_producido - COALESCE(base.fino_prev, 0))

                   ELSE 0

               END

           ) / base.fino_apilado_cu

       ELSE NULL

   END AS rec_dia_pct

FROM base;
