/* ============================================================================
   V8. reclamo.v_cuadratura_modulo

   Regla R9. Es el control que detecta los casos que el Excel mostraba a mano:
   modulos 115 y 118 al 104 % y 107 % de extraccion.

   Cuando el porcentaje supera 100 mas la tolerancia configurada, la vista
   calcula el excedente y propone el modulo siguiente de la secuencia como
   destino del traspaso. La propuesta NO se aplica sola: hay que registrarla
   como ajuste manual APROBADO.

   INCLUYE LA LINEA BASE. El acumulado suma lo extraido antes de la fecha de
   corte del sistema (m3_camiones_previo y m3_rotopala_previo, fijados una vez
   con sp_establecer_linea_base) mas lo registrado desde el corte. Sin eso, un
   modulo que venia reclamandose desde antes apareceria como intacto.
   ============================================================================ */
CREATE   VIEW [reclamo].[v_cuadratura_modulo]
AS
WITH ult AS
(
    SELECT
        mb.[campaña_id],
        mb.pad_id,
        mb.modulo_id,
        mb.modulo_numero,
        mb.rotopala_id,
        mb.orden_secuencia,
        mb.estado_secuencia,
        mb.m3_totales,
        mb.tms_conformado,
        mb.densidad_oficial,
        mb.m3_camiones_previo,
        mb.m3_rotopala_previo,
        (
            SELECT MAX(c.m3_camiones_acum)
            FROM [reclamo].[v_camiones_acumulado] c
            WHERE c.[campaña_id] = mb.[campaña_id] AND c.modulo_id = mb.modulo_id
        ) AS m3_camiones_sistema,
        (
            SELECT MAX(t.m3_reclamado_acum)
            FROM [reclamo].[v_topografia_resuelta] t
            WHERE t.[campaña_id] = mb.[campaña_id] AND t.modulo_id = mb.modulo_id
        ) AS m3_rotopala_sistema,
        (
            SELECT SUM(COALESCE(a.delta_m3,0))
            FROM [reclamo].[v_ajustes_aplicables] a
            WHERE a.[campaña_id] = mb.[campaña_id] AND a.modulo_id = mb.modulo_id
        ) AS m3_ajustes
    FROM [reclamo].[v_modulo_base] mb
)
SELECT
    u.[campaña_id],
    u.pad_id,
    u.modulo_id,
    u.modulo_numero,
    u.rotopala_id,
    u.orden_secuencia,
    u.estado_secuencia,

    u.m3_totales,

    /* Extraido antes de la fecha de corte del sistema. No se recalcula. */
    u.m3_camiones_previo,
    u.m3_rotopala_previo,

    /* Extraido registrado por el sistema, desde la fecha de corte. */
    COALESCE(u.m3_camiones_sistema, 0)      AS m3_camiones_sistema,
    COALESCE(u.m3_rotopala_sistema, 0)      AS m3_rotopala_sistema,

    /* Totales del modulo.
       Camiones: la linea base SI se suma al acumulado propio del sistema,
       porque camiones_reclamo solo tiene filas desde el corte y su
       acumulado se recalcula desde cero dentro del esquema (no duplica).
       Rotopala/topografia: la linea base NO se suma cuando ya existe una
       lectura de topografia, porque m3_reclamado_acum llega desde la fuente
       como acumulado corrido desde el inicio real del modulo (nunca se
       reinicia en el corte) y ya incluye lo previo. Sumar previo encima
       duplicaba el tonelaje (bug confirmado en modulo_id 187, campaña 8:
       90.113,502 + 101.363,707 = 191.477 m3 contra 102.709,9 m3 de
       capacidad, 186% del modulo). La linea base solo se usa como
       reemplazo cuando el modulo aun no tiene ninguna lectura de
       topografia sincronizada. */
    u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema, 0)
                                            AS m3_camiones_total,
    COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
                                            AS m3_rotopala_total,
    COALESCE(u.m3_ajustes, 0)               AS m3_ajustes,
    u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
        + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
        + COALESCE(u.m3_ajustes,0)          AS m3_extraido_total,

    CASE
        WHEN u.m3_totales = 0 THEN NULL
        ELSE (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
              + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
              + COALESCE(u.m3_ajustes,0)) * 100.0 / u.m3_totales
    END                                     AS porcentaje_extraido,

    /* Excedente por sobre el volumen del modulo. */
    CASE
        WHEN u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
             + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
             + COALESCE(u.m3_ajustes,0) > u.m3_totales
        THEN u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
             + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
             + COALESCE(u.m3_ajustes,0) - u.m3_totales
        ELSE 0
    END                                     AS m3_excedente,

    CASE
        WHEN u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
             + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
             + COALESCE(u.m3_ajustes,0) > u.m3_totales
        THEN (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
              + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
              + COALESCE(u.m3_ajustes,0) - u.m3_totales) * u.densidad_oficial
        ELSE 0
    END                                     AS tms_excedente,

    /* Modulo siguiente de la secuencia, propuesto como destino del traspaso. */
    (
        SELECT TOP (1) s.modulo_id
        FROM [reclamo].[secuencia_rotopala] s
        WHERE s.rotopala_id     = u.rotopala_id
          AND s.[campaña_id]    = u.[campaña_id]
          AND s.orden_secuencia > u.orden_secuencia
        ORDER BY s.orden_secuencia
    )                                       AS modulo_siguiente_propuesto,

    CASE
        WHEN u.m3_totales = 0
            THEN 'SIN_VOLUMEN_TOTAL'
        WHEN (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
              + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
              + COALESCE(u.m3_ajustes,0)) * 100.0 / u.m3_totales
             > 100 + (SELECT TRY_CONVERT(decimal(9,4), valor)
                      FROM [reclamo].[configuracion]
                      WHERE clave = 'TOLERANCIA_CUADRATURA_PCT')
            THEN 'SOBRE_100_PROPONER_TRASPASO'
        WHEN (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
              + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
              + COALESCE(u.m3_ajustes,0)) * 100.0 / u.m3_totales > 99
            THEN 'MODULO_PRACTICAMENTE_AGOTADO'
        ELSE 'OK'
    END                                     AS flag_cuadratura,

    /* Saldo disponible para seguir reclamando. */
    u.m3_totales
        - (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
           + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
           + COALESCE(u.m3_ajustes,0))      AS m3_saldo_disponible,

    /* Los mismos totales en TMS, para el resumen por modulo del dashboard.
       La densidad es la oficial del modulo, constante desde el congelamiento
       (supuesto S8), por lo que convertir m3 a TMS aca es directo. */
    u.densidad_oficial,
    u.tms_conformado,

    (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)) * u.densidad_oficial
                                            AS tms_camiones_total,
    (COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)) * u.densidad_oficial
                                            AS tms_rotopala_total,
    (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
        + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
        + COALESCE(u.m3_ajustes,0)) * u.densidad_oficial
                                            AS tms_extraido_total,

    (u.m3_totales
        - (u.m3_camiones_previo + COALESCE(u.m3_camiones_sistema,0)
           + COALESCE(u.m3_rotopala_sistema, u.m3_rotopala_previo, 0)
           + COALESCE(u.m3_ajustes,0))) * u.densidad_oficial
                                            AS tms_saldo_disponible
FROM ult u;