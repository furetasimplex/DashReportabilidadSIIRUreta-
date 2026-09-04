/* ============================================================================
   V6. reclamo.v_ajustes_aplicables

   Regla R10. Solo los ajustes APROBADOS afectan el calculo. Los PROPUESTOS
   quedan visibles en el dashboard pero con delta cero.

   TRASPASO_MODULO genera DOS efectos: descuenta del modulo origen y abona al
   modulo destino. Por eso la vista devuelve dos filas por ajuste de ese tipo.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_ajustes_aplicables]
AS
SELECT
    a.fecha_operacion,
    a.[campaña_id],
    a.pad_id,
    a.modulo_id,
    a.tipo_ajuste,
    a.delta_m3,
    a.delta_tms,
    a.motivo,
    a.antecedente_tipo,
    a.antecedente_ref,
    a.usuario_solicita,
    a.usuario_aprueba,
    a.fecha_aprobacion,
    a.ajuste_id,
    CAST('ORIGEN' AS varchar(10))           AS rol_en_ajuste
FROM [reclamo].[ajuste_manual] a
WHERE a.estado = 'APROBADO'

UNION ALL

/* Contrapartida del traspaso: lo que sale del origen entra al destino. */
SELECT
    a.fecha_operacion,
    a.[campaña_id],
    a.pad_id,
    a.modulo_destino_id                     AS modulo_id,
    a.tipo_ajuste,
    -a.delta_m3                             AS delta_m3,
    -a.delta_tms                            AS delta_tms,
    a.motivo,
    a.antecedente_tipo,
    a.antecedente_ref,
    a.usuario_solicita,
    a.usuario_aprueba,
    a.fecha_aprobacion,
    a.ajuste_id,
    CAST('DESTINO' AS varchar(10))          AS rol_en_ajuste
FROM [reclamo].[ajuste_manual] a
WHERE a.estado = 'APROBADO'
  AND a.tipo_ajuste = 'TRASPASO_MODULO'
  AND a.modulo_destino_id IS NOT NULL;