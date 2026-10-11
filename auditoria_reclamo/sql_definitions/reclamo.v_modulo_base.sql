/* ============================================================================
   V1. reclamo.v_modulo_base

   Une el modulo congelado con su posicion en la secuencia de la rotopala.
   Es el punto de entrada de todas las demas vistas: si un modulo no esta
   congelado, no aparece aca y por lo tanto no puede reclamarse.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_modulo_base]
AS
SELECT
    mc.[campaña_id],
    mc.pad_id,
    mc.parcela_id,
    mc.modulo_id,
    COALESCE(mc.modulo_numero, md.numero)   AS modulo_numero,

    mc.fecha_conformacion,
    mc.fecha_congelamiento,

    mc.tms_conformado,
    mc.m3_totales,
    mc.densidad_oficial,
    mc.humedad_conformacion,

    /* Linea base: lo extraido antes de la fecha de corte del sistema. */
    mc.m3_camiones_previo,
    mc.m3_rotopala_previo,
    mc.fecha_linea_base,

    /* Topologia fija del PAD. */
    tp.nombre                               AS pad_nombre,
    tp.material,
    tp.parcelas,
    tp.modulos_por_parcela,
    tp.modulos_totales,
    tp.modulo_numero_max,

    sr.rotopala_id,
    sr.orden_secuencia,
    sr.estado                               AS estado_secuencia,
    sr.fecha_apertura,
    sr.fecha_cierre,

    mc.fuente                               AS fuente_base,
    mc.metodo                               AS metodo_base,
    mc.estado                               AS estado_congelamiento,

    /* Coherencia interna de la base congelada. La densidad declarada deberia
       reproducir el TMS al multiplicarla por el volumen. */
    CASE
        WHEN mc.m3_totales = 0 THEN NULL
        ELSE mc.tms_conformado / mc.m3_totales
    END                                     AS densidad_implicita,
    CASE
        WHEN mc.m3_totales = 0 THEN 'SIN_VOLUMEN'
        WHEN ABS(mc.tms_conformado / mc.m3_totales - mc.densidad_oficial)
             > 0.01 THEN 'DENSIDAD_DECLARADA_DIFIERE'
        ELSE 'OK'
    END                                     AS flag_densidad,

    /* El numero de modulo debe caer dentro del rango fisico de su PAD.
       Oxido 1 a 64, sulfuro 1 a 140. */
    CASE
        WHEN tp.pad_id IS NULL
            THEN 'PAD_SIN_TOPOLOGIA_DEFINIDA'
        WHEN COALESCE(mc.modulo_numero, md.numero) IS NULL
            THEN 'SIN_NUMERO_DE_MODULO'
        WHEN COALESCE(mc.modulo_numero, md.numero)
             NOT BETWEEN tp.modulo_numero_min AND tp.modulo_numero_max
            THEN 'MODULO_FUERA_DEL_RANGO_DEL_PAD'
        ELSE 'OK'
    END                                     AS flag_topologia
FROM [reclamo].[modulo_congelado] mc
LEFT JOIN [reclamo].[secuencia_rotopala] sr
    ON  sr.[campaña_id] = mc.[campaña_id]
    AND sr.modulo_id    = mc.modulo_id
LEFT JOIN [inventar_SpcHidr].[modulo] md
    ON md.id_modulo = mc.modulo_id
LEFT JOIN [reclamo].[topologia_pad] tp
    ON tp.pad_id = mc.pad_id
WHERE mc.estado = 'CONGELADO';