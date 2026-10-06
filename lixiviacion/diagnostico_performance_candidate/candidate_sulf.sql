-- PROTOTIPO DEV READ ONLY. No desplegar ni integrar al runtime.
-- Parámetros enlazados SQLAlchemy: desde, hasta, pad_id, parcela_id.
-- CASE de estado y calidad copiados de la definición oficial capturada.
WITH fechas AS (
    SELECT CAST(:desde AS date) AS fecha
    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date)
), parcela AS (
    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela
    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad
    WHERE p.id_pad=:pad_id AND p.id_parcela=:parcela_id
      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))
), campanas AS (
    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,
           MIN(c.fecha_ini_carguio) AS fecha_ini_campana
    FROM inventar_SpcHidr.campana_parcela_control c
    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id
    WHERE c.fecha_ini_carguio IS NOT NULL
    GROUP BY c.pad_id,c.campana_id,c.parcela_id
), ventanas AS (
    SELECT c.*,LEAD(c.fecha_ini_campana) OVER
        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente
    FROM campanas c
), campanas_rango AS (
    -- LEAD ya calculado sobre todas las campañas de la parcela, antes del filtro de rango.
    SELECT * FROM ventanas
    WHERE fecha_ini_campana<=CAST(:hasta AS date)
      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(:desde AS date))
), riego_fuente AS (
    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot s
          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela
), drenaje_fuente AS (
    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor
        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional s
          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela
), riego_extremos AS (
    -- Ventana completa, nunca recortada a las fechas visibles.
    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,
           MAX(r.fecha) AS fecha_ultimo_riego_real
    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id
      AND r.fecha>=c.fecha_ini_campana
      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)
      AND r.valor>1
    GROUP BY c.pad_id,c.parcela_id,c.campana_id
), drenaje_extremos AS (
    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,
           MAX(d.fecha) AS fecha_ultimo_drenaje_real
    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id
      AND d.fecha>=c.fecha_ini_campana
      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)
      AND d.valor>0
    GROUP BY c.pad_id,c.parcela_id,c.campana_id
), contexto AS (
    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real
    FROM campanas_rango c
    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id
    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id
), riego_dia AS (
    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,
        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo
    FROM riego_fuente WHERE fecha BETWEEN CAST(:desde AS date) AND CAST(:hasta AS date)
    GROUP BY pad_id,parcela_id,fecha
), drenaje_dia AS (
    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_drenaje,
        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>0 THEN 1 ELSE 0 END) END AS drenaje_activo
    FROM drenaje_fuente WHERE fecha BETWEEN CAST(:desde AS date) AND CAST(:hasta AS date)
    GROUP BY pad_id,parcela_id,fecha
), dias AS (
    SELECT f.fecha,p.*,c.campana_id,c.numero_campana,
        c.fecha_primer_riego_real,c.fecha_ultimo_riego_real,c.fecha_primer_drenaje_real,c.fecha_ultimo_drenaje_real,
        r.tiene_dato_riego,r.riego_activo,d.tiene_dato_drenaje,d.drenaje_activo
    FROM fechas f CROSS JOIN parcela p
    LEFT JOIN contexto c ON c.pad_id=p.pad_id AND c.parcela_id=p.parcela_id
      AND f.fecha>=c.fecha_ini_campana AND (c.fecha_ini_campana_siguiente IS NULL OR f.fecha<c.fecha_ini_campana_siguiente)
    LEFT JOIN riego_dia r ON r.pad_id=p.pad_id AND r.parcela_id=p.parcela_id AND r.fecha=f.fecha
    LEFT JOIN drenaje_dia d ON d.pad_id=p.pad_id AND d.parcela_id=p.parcela_id AND d.fecha=f.fecha
), base_modulos AS (
    SELECT c.*,d.fecha,d.tiene_dato_riego,d.riego_activo,d.tiene_dato_drenaje,d.drenaje_activo,
        d.fecha_primer_riego_real,d.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real
    FROM dias d INNER JOIN inventar_SpcHidr.campana_parcela_control c
      ON c.pad_id=d.pad_id AND c.parcela_id=d.parcela_id AND c.campana_id=d.campana_id
    WHERE c.fecha_ini_carguio IS NOT NULL AND c.fecha_ini_carguio<=d.fecha
), estado_modulo AS (
    SELECT b.*,CASE

                WHEN b.fecha_fin_retiro IS NOT NULL
                 AND b.fecha > b.fecha_fin_retiro
                    THEN 'RECLAMADO'

                WHEN b.fecha_ini_retiro IS NOT NULL
                 AND b.fecha >= b.fecha_ini_retiro
                 AND
                 (
                     b.fecha_fin_retiro IS NULL
                     OR b.fecha <= b.fecha_fin_retiro
                 )
                    THEN 'RECLAMO'

                WHEN b.fecha >= b.fecha_ini_carguio
                 AND
                 (
                     b.fecha_fin_carguio IS NULL
                     OR b.fecha < b.fecha_fin_carguio
                 )
                    THEN 'APILADO'

                WHEN b.fecha_fin_carguio IS NOT NULL
                 AND b.fecha >= b.fecha_fin_carguio
                 AND
                 (
                     b.fecha_primer_riego_real IS NULL
                     OR b.fecha < b.fecha_primer_riego_real
                 )
                    THEN 'CONFORMADO_PRE_RIEGO'

                WHEN b.fecha_primer_riego_real IS NOT NULL
                 AND b.fecha >= b.fecha_primer_riego_real
                 AND
                 (
                     b.tiene_dato_riego IS NULL
                     OR b.riego_activo IS NULL
                     OR b.tiene_dato_drenaje IS NULL
                     OR b.drenaje_activo IS NULL
                 )
                    THEN 'SIN_COBERTURA_HIDRAULICA'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 1
                    THEN 'RIEGO_DRENAJE'

                WHEN b.riego_activo = 1
                 AND b.drenaje_activo = 0
                    THEN 'RIEGO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND b.fecha > b.fecha_ultimo_riego_real
                    THEN 'DRENAJE_RESIDUAL'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 1
                    THEN 'DRENAJE_CON_RIEGO_PAUSADO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0

                 AND b.fecha_ultimo_riego_real IS NOT NULL
                 AND b.fecha > b.fecha_ultimo_riego_real

                 AND
                 (
                     b.fecha_ultimo_drenaje_real IS NULL
                     OR b.fecha > b.fecha_ultimo_drenaje_real
                 )

                 AND
                 (
                     b.fecha_ini_retiro IS NULL
                     OR b.fecha < b.fecha_ini_retiro
                 )
                    THEN 'REPOSO_PRE_RECLAMO'

                WHEN b.riego_activo = 0
                 AND b.drenaje_activo = 0
                    THEN 'PAUSA_HIDRAULICA'

                ELSE 'SIN_CLASIFICAR'

            END AS estado_modulo FROM base_modulos b
), distribucion AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MAX(numero_campana) AS numero_campana,
        estado_modulo,COUNT(*) AS cantidad_modulos
    FROM estado_modulo GROUP BY fecha,pad_id,campana_id,parcela_id,estado_modulo
), resumen AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MAX(numero_campana) AS numero_campana,
        SUM(cantidad_modulos) AS modulos_total,COUNT(*) AS estados_distintos,
        CASE WHEN COUNT(*)=1 THEN MAX(estado_modulo) ELSE 'MIXTO' END AS estado_operacional,
        STRING_AGG(CAST(CONCAT(estado_modulo,' = ',cantidad_modulos) AS varchar(max)),' | ') AS composicion_modulos
    FROM distribucion GROUP BY fecha,pad_id,campana_id,parcela_id
), hitos AS (
    SELECT fecha,pad_id,campana_id,parcela_id,MIN(fecha_ini_carguio) AS fecha_ini_carguio,
        MAX(fecha_fin_carguio) AS fecha_conformado,MIN(fecha_ini_retiro) AS fecha_ini_reclamo,MAX(fecha_fin_retiro) AS fecha_fin_reclamo
    FROM estado_modulo GROUP BY fecha,pad_id,campana_id,parcela_id
)
SELECT d.fecha,d.pad_id,d.nombre_pad,d.parcela_id,d.numero_parcela,d.campana_id,d.numero_campana,
    r.modulos_total,r.estados_distintos,COALESCE(r.estado_operacional,'SIN_INFORMACION') AS estado_operacional,
    r.composicion_modulos,d.tiene_dato_riego,d.riego_activo,d.tiene_dato_drenaje,d.drenaje_activo,
    h.fecha_ini_carguio,h.fecha_conformado,d.fecha_primer_riego_real AS fecha_primer_riego,
    d.fecha_ultimo_riego_real AS fecha_ultima_actividad_riego,d.fecha_primer_drenaje_real AS fecha_ini_drenaje,
    d.fecha_ultimo_drenaje_real AS fecha_ultima_actividad_drenaje,h.fecha_ini_reclamo,h.fecha_fin_reclamo,
    CASE
            WHEN r.estado_operacional IS NULL
                THEN 'SIN_INFORMACION'

            WHEN r.estado_operacional =
                 'SIN_COBERTURA_HIDRAULICA'
                THEN 'NO_EVALUABLE'

            WHEN r.estado_operacional = 'MIXTO'
             AND r.composicion_modulos
                 LIKE '%SIN_COBERTURA_HIDRAULICA%'
                THEN 'PARCIAL'

            ELSE 'EVALUABLE'
        END AS calidad_estado
FROM dias d
LEFT JOIN resumen r ON r.fecha=d.fecha AND r.pad_id=d.pad_id AND r.parcela_id=d.parcela_id AND r.campana_id=d.campana_id
LEFT JOIN hitos h ON h.fecha=d.fecha AND h.pad_id=d.pad_id AND h.parcela_id=d.parcela_id AND h.campana_id=d.campana_id
ORDER BY d.fecha OPTION (MAXRECURSION 32767)
