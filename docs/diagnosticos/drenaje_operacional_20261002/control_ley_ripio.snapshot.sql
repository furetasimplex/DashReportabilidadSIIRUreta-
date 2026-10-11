-- SNAPSHOT HISTORICO, NO DESPLEGAR. Fuente: report_export/exports/auditoria_ley_srr_202609/catalogo.json
CREATE VIEW [inventar_SpcHidr].[control_ley_ripio] AS

SELECT

    R.Fecha_drenaje,

    R.Campana,

    R.PAD,

    R.Recuperacion_parcela,

    R.Parcela,

    A.fino_apilado_cu,

    A.tmh_apilado,

    A.tms_apilado,

    (A.fino_apilado_cu * R.Recuperacion_parcela) / 100 AS fino_producido,

    A.fino_apilado_cu - ((A.fino_apilado_cu * R.Recuperacion_parcela) / 100) AS fino_remanente,

    (

        (

            A.fino_apilado_cu - ((A.fino_apilado_cu * R.Recuperacion_parcela) / 100)

        )

        / NULLIF(

            (

                A.tms_apilado - ((A.fino_apilado_cu * R.Recuperacion_parcela) / 100)

            ), 0

        )

    ) * 100 AS ley_ripio,



    -- IDs Operativos añadidos

    C.id_campaña,

    P.id_parcela



FROM inventar_SpcHidr.Recuperaciones_pad AS R

INNER JOIN inventar_SpcHidr.res_parcelas_apilado AS A

    ON R.Parcela = A.Parcela

    AND R.Campana = A.Campana

    AND R.PAD = A.PAD



-- Join a Campaña

INNER JOIN inventar_SpcHidr.campaña AS C

    ON R.Campana = C.numero_campaña



-- ==========================================================

-- JOIN A PAD (CORREGIDO CON LIKE)

-- ==========================================================

INNER JOIN inventar_SpcHidr.pad AS PAD_DICT

    -- Compara si el inicio de R.PAD coincide con el nombre en pad (ignorando mayúsculas)

    ON UPPER(R.PAD) LIKE UPPER(PAD_DICT.nombre) + '%' -- El '%' permite que 'SULFUROS' coincida con 'Sulfuro'



-- ==========================================================

-- Join a Parcela

-- ==========================================================

INNER JOIN inventar_SpcHidr.parcela AS P

    ON PAD_DICT.id_pad = P.id_pad

    AND R.Parcela = P.numero;
