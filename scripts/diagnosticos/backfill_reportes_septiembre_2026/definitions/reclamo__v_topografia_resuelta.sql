/* ============================================================================
   V3. reclamo.v_topografia_resuelta

   Deriva el incremento diario a partir del acumulado, comparando cada
   medicion contra la anterior del MISMO modulo. Nunca compara entre modulos.

   El incremento se acota en cero: un retroceso topografico no produce
   tonelaje negativo, pero queda marcado en flag_topografia para que alguien
   lo revise.

   CASO DE LA PRIMERA MEDICION DE CADA MODULO (sin fila anterior via LAG):
   el acumulado que llega desde la fuente (m3_reclamado_acum) NO se reinicia
   en la fecha de corte -- es el mismo acumulado corrido desde el inicio real
   del modulo. Si el modulo ya tenia extraccion previa capturada como linea
   base (modulo_congelado.m3_rotopala_previo, via sp_establecer_linea_base),
   esa porcion YA esta incluida dentro del primer acumulado sincronizado y
   debe descontarse antes de tratarlo como el incremento de ese dia. De lo
   contrario el modulo recibe de golpe todo lo que llevaba desde antes del
   corte como si fuera tonelaje de un solo dia (bug confirmado en modulo_id
   187, campaña 8, 2026-07-01: 100.439,216 m3 tratados como incremento del
   dia en vez de 10.325,714 m3, el incremento real).
   ============================================================================ */
CREATE   VIEW [reclamo].[v_topografia_resuelta]
AS
WITH sec AS
(
    SELECT
        ta.fecha_medicion,
        ta.[campaña_id],
        ta.pad_id,
        ta.modulo_id,
        ta.m3_reclamado_acum,
        ta.avance_total_pct,
        ta.medicion_valida,
        ta.motivo_no_medicion,
        ta.fuente,
        ta.metodo,
        mc.m3_rotopala_previo,

        LAG(ta.fecha_medicion) OVER
        (
            PARTITION BY ta.[campaña_id], ta.modulo_id
            ORDER BY ta.fecha_medicion
        ) AS fecha_medicion_anterior,

        LAG(ta.m3_reclamado_acum) OVER
        (
            PARTITION BY ta.[campaña_id], ta.modulo_id
            ORDER BY ta.fecha_medicion
        ) AS m3_acum_anterior
    FROM [reclamo].[topografia_avance] ta
    LEFT JOIN [reclamo].[modulo_congelado] mc
        ON mc.[campaña_id] = ta.[campaña_id] AND mc.modulo_id = ta.modulo_id
    WHERE ta.estado = 'VIGENTE'
)
SELECT
    s.fecha_medicion,
    s.[campaña_id],
    s.pad_id,
    s.modulo_id,

    s.m3_reclamado_acum,
    s.m3_acum_anterior,
    s.fecha_medicion_anterior,
    DATEDIFF(day, s.fecha_medicion_anterior, s.fecha_medicion) AS dias_entre_mediciones,

    CAST
    (
        CASE
            WHEN s.medicion_valida = 0 THEN 0
            WHEN s.m3_acum_anterior IS NULL
                 AND s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0) < 0 THEN 0
            WHEN s.m3_acum_anterior IS NULL
                 THEN s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0)
            WHEN s.m3_reclamado_acum - s.m3_acum_anterior < 0 THEN 0
            ELSE s.m3_reclamado_acum - s.m3_acum_anterior
        END AS decimal(30,12)
    )                                       AS m3_incremento,

    s.avance_total_pct,
    s.medicion_valida,
    s.motivo_no_medicion,
    s.fuente,
    s.metodo,

    CASE
        WHEN s.medicion_valida = 0
            THEN 'SIN_MEDICION'
        WHEN s.m3_acum_anterior IS NULL
             AND s.m3_reclamado_acum - COALESCE(s.m3_rotopala_previo, 0) < 0
            THEN 'PRIMERA_MEDICION_BAJO_LINEA_BASE_REVISAR'
        WHEN s.m3_acum_anterior IS NULL
            THEN 'PRIMERA_MEDICION_DEL_MODULO'
        WHEN s.m3_reclamado_acum < s.m3_acum_anterior
            THEN 'RETROCESO_ACUMULADO_REVISAR'
        WHEN DATEDIFF(day, s.fecha_medicion_anterior, s.fecha_medicion) > 1
            THEN 'INCREMENTO_ACUMULA_VARIOS_DIAS'
        ELSE 'OK'
    END                                     AS flag_topografia
FROM sec s;