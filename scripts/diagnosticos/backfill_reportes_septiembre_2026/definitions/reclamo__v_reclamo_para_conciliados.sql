/* ================================================================
   FIX: reclamo.v_reclamo_para_conciliados descarta camiones de
   modulos que ese dia solo tuvieron camiones y ninguna medicion de
   rotopala (topografia, preliminar o ajuste).

   Causa raiz: el filtro WHERE rd.fuente_reclamo <> 'SIN_DATO' usa
   fuente_reclamo (que solo describe el origen del dato de ROTOPALA)
   como filtro de fila completa. Cuando fuente_reclamo = SIN_DATO
   por falta de rotopala ese dia, se pierde tambien el
   tms_camiones_dia de esa fila aunque sea distinto de cero.

   Evidencia 2026-07-01 PAD 2: modulos 192, 193, 194, 199, 200, 201
   tienen tms_camiones_dia > 0 y fuente_reclamo = SIN_DATO. Suma de
   esos seis modulos = 17995.070451, exactamente la diferencia que
   se observaba ese dia entre el dashboard (reclamo.calculo_diario)
   y la fuente del SP (reclamo.v_reclamo_para_conciliados).

   Fix: conservar la fila si hay fuente de rotopala valida O si hay
   camiones distintos de cero ese dia. Los modulos realmente vacios
   (sin rotopala y sin camiones) se siguen excluyendo igual que
   antes.

   No se toca reclamo.v_reclamo_diario (esa vista ya calcula bien
   tms_camiones_dia; el problema es solo el filtro de esta vista).
================================================================ */

CREATE VIEW [reclamo].[v_reclamo_para_conciliados]
AS
SELECT
    rd.fecha_operacion,
    rd.pad_id,
    rd.[campaña_id],
    rd.modulo_id,
    rd.modulo_numero,
    rd.rotopala_id,
    CAST(rd.avance_roto_pct AS float)              AS avance_porcentaje,
    CAST(rd.avance_total_pct_calculado AS float)   AS avance_total_porcentaje,
    CAST(rd.avance_camiones_pct AS float)          AS avance_camiones_porcentaje,
    CAST(rd.tms_rotopala_dia AS float)             AS tonelaje_reclamado_diario,
    CAST(rd.m3_rotopala_dia AS float)              AS volumen_diario_m3,
    CAST(rd.tms_camiones_dia AS float)             AS tonelaje_camiones_diario,
    CAST(rd.tms_disponible_roto AS float)          AS tms_disponible_roto,
    CAST(rd.tms_conformado AS float)               AS tms_conformado,
    CAST(rd.densidad_oficial AS float)             AS densidad_oficial,
    rd.fuente_reclamo,
    rd.metodo_calculo,
    rd.flag_calculo,
    rd.ajustes_aplicados
FROM [reclamo].[v_reclamo_diario] rd
WHERE rd.fuente_reclamo <> 'SIN_DATO'
   OR COALESCE(rd.tms_camiones_dia, 0) <> 0;