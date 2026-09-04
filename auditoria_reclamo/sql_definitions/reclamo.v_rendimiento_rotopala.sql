/* ============================================================================
   V9. reclamo.v_rendimiento_rotopala

   Replica la hoja Rendimiento del libro de ripios: tms/hr por pesometro y por
   topografia, y su diferencia.

   Es el control de rendimiento que el usuario pidio: permite ver si una
   rotopala esta rindiendo por debajo de su tasa horaria habitual.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_rendimiento_rotopala]
AS
WITH topo_dia AS
(
    SELECT
        rd.fecha_operacion                  AS fecha,
        rd.rotopala_id,
        SUM(CASE WHEN rd.fuente_reclamo = 'TOPOGRAFIA'
                 THEN rd.tms_rotopala_dia ELSE 0 END) AS tms_topografia,
        SUM(rd.tms_rotopala_dia)            AS tms_publicado,
        COUNT(*)                            AS modulos_con_movimiento
    FROM [reclamo].[v_reclamo_diario] rd
    WHERE rd.rotopala_id IS NOT NULL
    GROUP BY rd.fecha_operacion, rd.rotopala_id
)
SELECT
    d.fecha,
    r.rotopala_id,
    r.nombre                                AS rotopala,
    r.material,

    CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END AS horas_operacion,
    d.horas_total,
    d.tms_dia                               AS tms_cv25_dia_ambas,
    CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END
                                            AS tms_cv25_asignado,

    td.tms_topografia,
    td.tms_publicado,
    td.modulos_con_movimiento,

    /* Rendimiento en toneladas secas por hora. */
    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END,0) = 0
            THEN NULL
        ELSE (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
             / (CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END)
    END                                     AS rendimiento_pesometro_tms_hr,

    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END,0) = 0
            THEN NULL
        ELSE td.tms_topografia
             / (CASE WHEN r.rotopala_id = 1 THEN d.horas_r1 ELSE d.horas_r2 END)
    END                                     AS rendimiento_topografia_tms_hr,

    /* Diferencia entre lo que dice la correa y lo que dice la topografia. */
    td.tms_topografia
        - (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
                                            AS diferencia_tms,

    CASE
        WHEN COALESCE(CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1
                           ELSE d.tms_estimado_r2 END, 0) = 0 THEN NULL
        ELSE (td.tms_topografia
              - (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END))
             * 100.0
             / (CASE WHEN r.rotopala_id = 1 THEN d.tms_estimado_r1 ELSE d.tms_estimado_r2 END)
    END                                     AS diferencia_pct,

    d.flag_preliminar                       AS flag_cv25
FROM [reclamo].[v_cv25_diario] d
CROSS JOIN [reclamo].[rotopala] r
LEFT JOIN topo_dia td
    ON  td.fecha       = d.fecha
    AND td.rotopala_id = r.rotopala_id
WHERE r.activa = 1;