-- Fuente: definición vigente en PROD_SIIR (sys.sql_modules).
-- Extraída: 2026-08-06 21:49:46.930000
USE [PROD_SIIR];
GO

CREATE VIEW [hidro].[v_imp_chancado_normalizado] AS WITH tipado AS
(
    SELECT
        i.id,
        i.batch_id,
        i.imported_at,

        TRY_CONVERT(date, i.[date]) AS Fecha,
        TRY_CONVERT(datetime2(0), i.[datetime]) AS FechaHora,
        TRY_CONVERT(bigint, i.dumpid) AS dumpid,

        NULLIF(
            LTRIM(RTRIM(CONVERT(nvarchar(200), i.[from]))),
            ''
        ) AS Origen_Mineral,

        NULLIF(
            LTRIM(RTRIM(CONVERT(nvarchar(100), i.[to]))),
            ''
        ) AS Destino,

        NULLIF(
            LTRIM(RTRIM(CONVERT(nvarchar(100), i.shovel))),
            ''
        ) AS shovel,

        TRY_CONVERT(float, i.tonnage) AS Ton_Raw,
        TRY_CONVERT(float, i.cut) AS CuT_Raw,
        TRY_CONVERT(float, i.cus) AS CuS_Raw,
        TRY_CONVERT(float, i.cufe) AS CuFe_Raw,
        TRY_CONVERT(float, i.co3) AS CO3_Raw,
        TRY_CONVERT(float, i.fe) AS Fe_Raw,
        TRY_CONVERT(float, i.m100) AS Malla100_Raw,
        TRY_CONVERT(float, i.clay) AS Clay_Raw,
        TRY_CONVERT(float, i.recup) AS Recuperacion_Raw

    FROM hidro.imp_csv AS i

    WHERE LOWER(LTRIM(RTRIM(ISNULL(i.origen, '')))) = 'imp'

      AND UPPER(
            LTRIM(
                RTRIM(
                    ISNULL(CONVERT(varchar(100), i.[to]), '')
                )
            )
          ) = 'CH01'
),

base AS
(
    SELECT
        t.id,
        t.batch_id,
        t.imported_at,
        t.Fecha,
        t.FechaHora,

        CASE
            WHEN CONVERT(time, t.FechaHora) >= CONVERT(time, '08:00:00')
             AND CONVERT(time, t.FechaHora) <  CONVERT(time, '20:00:00')
                THEN 'A'
            ELSE 'B'
        END AS Turno,

        t.dumpid,
        t.Origen_Mineral,
        t.Destino,
        t.shovel,

        CASE
            WHEN UPPER(LTRIM(RTRIM(ISNULL(t.Origen_Mineral, '')))) = 'SRR-SRR'
              OR UPPER(LTRIM(RTRIM(ISNULL(t.shovel, '')))) = 'SRR'
                THEN 1
            ELSE 0
        END AS Es_SRR,

        CASE
    WHEN UPPER(LTRIM(RTRIM(ISNULL(t.Origen_Mineral, '')))) = 'SRR-SRR'
      OR UPPER(LTRIM(RTRIM(ISNULL(t.shovel, '')))) = 'SRR'
        THEN 'SRR'

    WHEN UPPER(LTRIM(RTRIM(ISNULL(t.Origen_Mineral, '')))) LIKE 'F%'
      OR UPPER(LTRIM(RTRIM(ISNULL(t.Origen_Mineral, '')))) LIKE 'H%'
        THEN 'MINA'

    ELSE 'CAMION'
		END AS Tipo_Registro,

        t.Ton_Raw AS Ton,

        CASE
            WHEN t.CuT_Raw BETWEEN 0 AND 100 THEN t.CuT_Raw
            ELSE NULL
        END AS CuT,

        CASE
            WHEN t.CuS_Raw BETWEEN 0 AND 100 THEN t.CuS_Raw
            ELSE NULL
        END AS CuS,

        CASE
            WHEN t.CuFe_Raw BETWEEN 0 AND 100 THEN t.CuFe_Raw
            ELSE NULL
        END AS CuFe,

        CASE
            WHEN t.CO3_Raw BETWEEN 0 AND 100 THEN t.CO3_Raw
            ELSE NULL
        END AS CO3,

        CASE
            WHEN t.Fe_Raw BETWEEN 0 AND 100 THEN t.Fe_Raw
            ELSE NULL
        END AS Fe,

        CASE
            WHEN t.Malla100_Raw BETWEEN 0 AND 100 THEN t.Malla100_Raw
            ELSE NULL
        END AS Malla100,

        CASE
            WHEN t.Clay_Raw BETWEEN 0 AND 100 THEN t.Clay_Raw
            ELSE NULL
        END AS Clay,

        CASE
            WHEN t.Recuperacion_Raw BETWEEN 0 AND 100
                THEN t.Recuperacion_Raw
            ELSE NULL
        END AS Recuperacion

    FROM tipado AS t

    WHERE t.Fecha IS NOT NULL
      AND t.FechaHora IS NOT NULL
      AND t.Ton_Raw > 0
),

lotes AS
(
    SELECT
        Fecha,
        batch_id,
        MAX(imported_at) AS imported_at_lote
    FROM base
    GROUP BY
        Fecha,
        batch_id
),

lote_vigente AS
(
    SELECT
        Fecha,
        batch_id,

        ROW_NUMBER() OVER
        (
            PARTITION BY Fecha
            ORDER BY
                imported_at_lote DESC,
                batch_id DESC
        ) AS rn_lote

    FROM lotes
),

vigente AS
(
    SELECT
        b.*
    FROM base AS b

    INNER JOIN lote_vigente AS l
        ON l.Fecha = b.Fecha
       AND l.batch_id = b.batch_id
       AND l.rn_lote = 1
),

deduplicado AS
(
    SELECT
        v.*,

        ROW_NUMBER() OVER
        (
            PARTITION BY
                v.Fecha,
                v.Es_SRR,

                CASE
                    WHEN v.Es_SRR = 0
                        THEN CONVERT(varchar(100), v.dumpid)
                    ELSE NULL
                END,

                CASE
                    WHEN v.Es_SRR = 1
                        THEN CONVERT(varchar(19), v.FechaHora, 120)
                    ELSE NULL
                END

            ORDER BY
                v.imported_at DESC,
                v.id DESC
        ) AS rn_registro

    FROM vigente AS v

    WHERE v.Es_SRR = 1
       OR v.dumpid IS NOT NULL
)

SELECT
    id,
    batch_id,
    imported_at,
    Fecha,
    FechaHora,
    Turno,
    dumpid,
    Origen_Mineral,
    Destino,
    shovel,
    Es_SRR,
    Tipo_Registro,
    Ton,
    CuT,
    CuS,
    CuFe,
    CO3,
    Fe,
    Malla100,
    Clay,
    Recuperacion,
    CAST('IMP' AS varchar(20)) AS Fuente_Dato

FROM deduplicado

WHERE rn_registro = 1;
GO
