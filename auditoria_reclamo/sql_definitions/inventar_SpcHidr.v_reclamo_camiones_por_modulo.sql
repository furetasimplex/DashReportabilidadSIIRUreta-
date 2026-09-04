-- inventar_SpcHidr.v_reclamo_camiones_por_modulo source

CREATE   VIEW inventar_SpcHidr.v_reclamo_camiones_por_modulo AS
SELECT
    r.tonelaje_reclamado,
    r.campaña_id,
    r.id_modulo,
    c.numero_campaña  AS campana,
    m.numero          AS numero_modulo
FROM inventar_SpcHidr.reclamo_camiones_por_modulo AS r
JOIN inventar_SpcHidr.[campaña] AS c   ON c.[id_campaña] = r.campaña_id   -- usa campania/id_campania si no tienes tildes
JOIN inventar_SpcHidr.modulo    AS m   ON m.id_modulo    = r.id_modulo;