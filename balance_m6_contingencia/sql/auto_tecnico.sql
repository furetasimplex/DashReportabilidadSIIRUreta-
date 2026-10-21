CREATE VIEW inventar_SpcHidr.v_balance_m6_totalizador_auto_turno

AS



/* ================================================================

   RESOLVEDOR FINAL PI / TUM POR TURNO



   Clave:

       fecha_operacional + turno + equipo_codigo



   Reglas principales:

     1. PI válido/con variación:

        -> PI



     2. PI no confiable / plano:

        -> TUM si existe



     3. PI completamente ausente:

        -> TUM si existe



     4. Sin PI confiable y sin TUM:

        -> SIN_RESOLVER



   IMPORTANTE:

   - TUM_DIRECTO, TUM_MIXTO y TUM_CALCULADO son utilizables.

   - NULL = falta información.

   - 0 TUM = cero operacional válido.

   - No aplicar factores de humedad 0.97 / 0.975 / 0.90 aquí.



   CAMBIO TUM:

   - CV008/CV108 dejan de leer v_datos_apilado_tmh_v2.

   - Su PI se obtiene directamente desde

     v_contingencia_pi_frontera_turno.

   - Regla productiva:

         NULL    -> NULL

         <=100 t -> 0

         >100 t  -> delta PI

================================================================ */



WITH pi_productivo AS

(



    /* ============================================================

       CV008 - PRINCIPAL TM1



       PI independiente de Control_Apilado_TMH_v2_test.



       v_contingencia_pi_frontera_turno ya entrega:

           turno A = 08:00 -> 20:00

           turno B = 20:00 -> 08:00 siguiente



       Regla productiva vigente:

           NULL    -> NULL

           <=100 t -> 0

           >100 t  -> delta

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('PRINCIPAL_CV008' AS varchar(40))

            AS equipo_codigo,



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ) AS valor_pi_bruto,



        CAST

        (

            CASE

                WHEN f.delta_frontera_pi IS NULL

                    THEN NULL



                WHEN f.delta_frontera_pi <= 100

                    THEN 0



                ELSE f.delta_frontera_pi

            END

            AS decimal(28,6)

        ) AS valor_pi_final



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'PRINCIPAL_CV008'





    UNION ALL





    /* ============================================================

       CV108 - PRINCIPAL TM2



       Misma metodología que CV008.

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('PRINCIPAL_CV108' AS varchar(40))

            AS equipo_codigo,



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ) AS valor_pi_bruto,



        CAST

        (

            CASE

                WHEN f.delta_frontera_pi IS NULL

                    THEN NULL



                WHEN f.delta_frontera_pi <= 100

                    THEN 0



                ELSE f.delta_frontera_pi

            END

            AS decimal(28,6)

        ) AS valor_pi_final



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'PRINCIPAL_CV108'





    UNION ALL





    /* ============================================================

       CV006 - CHANCADOR

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('CHANCADOR_CV006' AS varchar(40)),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        )



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'CHANCADOR_CV006'





    UNION ALL





    /* ============================================================

       CV025 - RIPIOS

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('RIPIOS_CV025' AS varchar(40)),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        )



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'RIPIOS_CV025'





    UNION ALL





    /* ============================================================

       SRR CV001



       Process Value integrado:

           SUM(tot_001 * 10 / 3600)



       delta_frontera_pi ya contiene esa integración.

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('SRR_CV001' AS varchar(40)),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        )



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'SRR_CV001'





    UNION ALL





    /* ============================================================

       SRR CV002

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('SRR_CV002' AS varchar(40)),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        )



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'SRR_CV002'





    UNION ALL





    /* ============================================================

       SRR CV003

       ============================================================ */



    SELECT

        f.fecha_operacional,

        f.turno,

        CAST('SRR_CV003' AS varchar(40)),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        ),



        CAST(

            f.delta_frontera_pi

            AS decimal(28,6)

        )



    FROM inventar_SpcHidr.v_contingencia_pi_frontera_turno AS f



    WHERE f.equipo_codigo = 'SRR_CV003'

),





base AS

(

    SELECT

        d.fecha_operacional,

        d.turno,

        d.equipo_codigo,



        /* ========================================================

           PI

           ======================================================== */



        d.estado_tecnico_pi,

        d.cobertura_pct,



        d.ultima_fecha_con_cambio,

        d.segundos_sin_cambio_al_cierre,



        d.lectura_inicio_pi,

        d.lectura_fin_pi,

        d.delta_frontera_pi,

        d.estado_fronteras,



        /*

           LEFT JOIN intencional.



           Si PI desapareció completamente:

               p.valor_pi_* = NULL



           pero la fila del diagnóstico sigue existiendo gracias

           al universo PI UNION TUM.

        */



        p.valor_pi_bruto,

        p.valor_pi_final,





        /* ========================================================

           APOYO OPERACIONAL

           ======================================================== */



        d.tonelaje_apoyo,

        d.fuente_apoyo,

        d.estado_apoyo,





        /* ========================================================

           TUM

           ======================================================== */



        d.tum_id,

        d.tum_disponible,



        d.lectura_inicio_tum,

        d.lectura_fin_tum,



        d.valor_turno_tum,

        d.total_excel_tum,



        d.lectura_inicial_calculada,

        d.lectura_final_calculada,



        d.diferencia_inicio_pi_tum,

        d.diferencia_fin_pi_tum,

        d.diferencia_tonelaje_pi_tum,



        d.archivo_batch,

        d.tum_batch_id,





        /* ========================================================

           TIPO DE TUM



           Sólo trazabilidad.

           Los tres tipos son utilizables como contingencia.

           ======================================================== */



        CAST

        (

            CASE



                WHEN d.tum_disponible = 0

                    THEN 'SIN_TUM'



                WHEN ISNULL(d.lectura_inicial_calculada,0) = 0

                 AND ISNULL(d.lectura_final_calculada,0) = 0

                    THEN 'TUM_DIRECTO'



                WHEN ISNULL(d.lectura_inicial_calculada,0) = 1

                 AND ISNULL(d.lectura_final_calculada,0) = 1

                    THEN 'TUM_CALCULADO'



                ELSE 'TUM_MIXTO'



            END

            AS varchar(30)

        ) AS tipo_tum



    FROM

        inventar_SpcHidr.v_contingencia_totalizador_diagnostico_turno

            AS d



    LEFT JOIN pi_productivo AS p

        ON  p.fecha_operacional = d.fecha_operacional

        AND p.turno             = d.turno

        AND p.equipo_codigo     = d.equipo_codigo



    WHERE d.equipo_codigo IN

    (

        'CHANCADOR_CV006',

        'PRINCIPAL_CV008',

        'PRINCIPAL_CV108',

        'RIPIOS_CV025',

        'SRR_CV001',

        'SRR_CV002',

        'SRR_CV003'

    )

),





decision AS

(

    SELECT

        *,



        CAST

        (

            CASE



                /* =================================================

                   CASO:

                   PI completamente ausente + TUM existente.



                   Un TUM = 0 es válido.

                   No confundir ausencia PI con PI=0.

                   ================================================= */



                WHEN estado_tecnico_pi = 'SIN_PI'

                 AND tum_disponible = 1

                 AND valor_turno_tum IS NOT NULL

                 AND valor_turno_tum >= 0



                    THEN 'TUM'





                /* =================================================

                   SRR CV001



                   Process Value integrado.



                   Para CV001 NO se exige frontera exacta 08/20,

                   porque F25 vigente integra todos los registros

                   disponibles del período.



                   Por eso:

                       CON_VARIACION

                       CON_VARIACION_COBERTURA_PARCIAL



                   continúan usando PI.

                   ================================================= */



                WHEN equipo_codigo = 'SRR_CV001'

                 AND estado_tecnico_pi IN

                 (

                     'CON_VARIACION',

                     'CON_VARIACION_COBERTURA_PARCIAL'

                 )

                 AND valor_pi_final IS NOT NULL

                 AND valor_pi_final >= 0



                    THEN 'PI'





                /* =================================================

                   RESTO DE TOTALIZADORES



                   Para señales acumulativas:

                   - fronteras completas

                   - existe variación

                   - delta >= 0

                   ================================================= */



                WHEN equipo_codigo <> 'SRR_CV001'

                 AND estado_fronteras = 'FRONTERAS_COMPLETAS'

                 AND delta_frontera_pi IS NOT NULL

                 AND delta_frontera_pi >= 0

                 AND estado_tecnico_pi IN

                 (

                     'CON_VARIACION',

                     'CON_VARIACION_COBERTURA_PARCIAL'

                 )



                    THEN 'PI'





                /* =================================================

                   PI plano / incompleto / no confiable + TUM



                   Se acepta:

                       TUM_DIRECTO

                       TUM_MIXTO

                       TUM_CALCULADO



                   Incluye TUM = 0.

                   ================================================= */



                WHEN tum_disponible = 1

                 AND valor_turno_tum IS NOT NULL

                 AND valor_turno_tum >= 0



                    THEN 'TUM'





                /* =================================================

                   No existe una fuente válida

                   ================================================= */



                ELSE 'SIN_RESOLVER'



            END

            AS varchar(30)

        ) AS fuente_resuelta



    FROM base

)





SELECT

    fecha_operacional,

    turno,

    equipo_codigo,





    /* ============================================================

       PI

       ============================================================ */



    estado_tecnico_pi,

    estado_fronteras,



    valor_pi_bruto,

    valor_pi_final,



    lectura_inicio_pi,

    lectura_fin_pi,

    delta_frontera_pi,



    ultima_fecha_con_cambio,

    segundos_sin_cambio_al_cierre,





    /* ============================================================

       APOYO OPERACIONAL

       ============================================================ */



    tonelaje_apoyo,

    fuente_apoyo,

    estado_apoyo,





    /* ============================================================

       TUM

       ============================================================ */



    tum_disponible,

    tipo_tum,



    lectura_inicio_tum,

    lectura_fin_tum,



    valor_turno_tum,

    total_excel_tum,



    diferencia_inicio_pi_tum,

    diferencia_fin_pi_tum,

    diferencia_tonelaje_pi_tum,





    /* ============================================================

       DECISIÓN

       ============================================================ */



    fuente_resuelta,





    /* ============================================================

       VALOR BRUTO RESUELTO

       ============================================================ */



    CAST

    (

        CASE



            WHEN fuente_resuelta = 'PI'

                THEN valor_pi_bruto



            WHEN fuente_resuelta = 'TUM'

                THEN valor_turno_tum



            ELSE NULL



        END

        AS decimal(28,6)

    ) AS valor_bruto_resuelto,





    /* ============================================================

       VALOR FINAL RESUELTO



       NO se aplican aquí:

           SRR   0.97

           CV006 0.975

           CV025 0.90



       Esos factores corresponden a consumidores finales.

       ============================================================ */



    CAST

    (

        CASE



            /* ----------------------------------------------------

               PI

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'PI'

                THEN valor_pi_final





            /* ----------------------------------------------------

               CV006

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND equipo_codigo = 'CHANCADOR_CV006'

             AND valor_turno_tum >= 0



                THEN valor_turno_tum





            /* ----------------------------------------------------

               CV025

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND equipo_codigo = 'RIPIOS_CV025'

             AND valor_turno_tum >= 0



                THEN valor_turno_tum





            /* ----------------------------------------------------

               SRR CV001 / CV002 / CV003



               TUM 0 también es cero válido.

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND equipo_codigo IN

             (

                 'SRR_CV001',

                 'SRR_CV002',

                 'SRR_CV003'

             )

             AND valor_turno_tum >= 0



                THEN valor_turno_tum





            /* ----------------------------------------------------

               CV008 / CV108



               Regla productiva vigente:

                   <= 100 t -> 0

                   >  100 t -> valor

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND equipo_codigo IN

             (

                 'PRINCIPAL_CV008',

                 'PRINCIPAL_CV108'

             )

             AND valor_turno_tum > 100



                THEN valor_turno_tum





            WHEN fuente_resuelta = 'TUM'

             AND equipo_codigo IN

             (

                 'PRINCIPAL_CV008',

                 'PRINCIPAL_CV108'

             )

             AND valor_turno_tum <= 100



                THEN 0





            ELSE NULL



        END

        AS decimal(28,6)

    ) AS valor_final_resuelto,





    /* ============================================================

       MOTIVO DE DECISIÓN

       ============================================================ */



    CAST

    (

        CASE



            /* ----------------------------------------------------

               PI ausente completamente

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND estado_tecnico_pi = 'SIN_PI'

             AND tipo_tum = 'TUM_DIRECTO'



                THEN 'SIN_PI_USA_TUM_DIRECTO'





            WHEN fuente_resuelta = 'TUM'

             AND estado_tecnico_pi = 'SIN_PI'

             AND tipo_tum = 'TUM_MIXTO'



                THEN 'SIN_PI_USA_TUM_MIXTO'





            WHEN fuente_resuelta = 'TUM'

             AND estado_tecnico_pi = 'SIN_PI'

             AND tipo_tum = 'TUM_CALCULADO'



                THEN 'SIN_PI_USA_TUM_CALCULADO'





            /* ----------------------------------------------------

               PI prioritario

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'PI'

             AND tum_disponible = 0



                THEN 'PI_DISPONIBLE'





            WHEN fuente_resuelta = 'PI'

             AND tum_disponible = 1



                THEN 'PI_PRIORITARIO_TUM_SOLO_CONTROL'





            /* ----------------------------------------------------

               PI existente pero en contingencia

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'TUM'

             AND tipo_tum = 'TUM_DIRECTO'



                THEN 'PI_EN_CONTINGENCIA_USA_TUM_DIRECTO'





            WHEN fuente_resuelta = 'TUM'

             AND tipo_tum = 'TUM_MIXTO'



                THEN 'PI_EN_CONTINGENCIA_USA_TUM_MIXTO'





            WHEN fuente_resuelta = 'TUM'

             AND tipo_tum = 'TUM_CALCULADO'



                THEN 'PI_EN_CONTINGENCIA_USA_TUM_CALCULADO'





            /* ----------------------------------------------------

               Sin resolver con movimiento externo

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'SIN_RESOLVER'

             AND estado_apoyo = 'MOVIMIENTO_CONFIRMADO'



                THEN 'MOVIMIENTO_CONFIRMADO_ESPERANDO_TUM'





            /* ----------------------------------------------------

               SRR sin fuente

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'SIN_RESOLVER'

             AND equipo_codigo IN

             (

                 'SRR_CV001',

                 'SRR_CV002',

                 'SRR_CV003'

             )



                THEN 'SRR_SIN_TUM'





            /* ----------------------------------------------------

               CV025 sin fuente

               ---------------------------------------------------- */



            WHEN fuente_resuelta = 'SIN_RESOLVER'

             AND equipo_codigo = 'RIPIOS_CV025'



                THEN 'CV025_SIN_TUM'





            ELSE 'SIN_EVIDENCIA_SUFICIENTE'



        END

        AS varchar(80)

    ) AS motivo_decision,





    /* ============================================================

       TRAZABILIDAD

       ============================================================ */



    tum_batch_id,

    archivo_batch



FROM decision
WHERE equipo_codigo <> 'RIPIOS_CV025';
