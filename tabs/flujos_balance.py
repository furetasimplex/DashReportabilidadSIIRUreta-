import pandas as pd
from sqlalchemy import create_engine, text#create_engine, text
from db_connection import get_connection,get_engine
from datetime import datetime

import os

# --- 1. TODA LA LÓGICA ESTÁ DENTRO DE ESTA FUNCIÓN ---
def ejecutar_balance_flujos(fecha_inicio, fecha_fin):
    """
    Se conecta a la base de datos, ejecuta las queries de flujos
    para un rango de fechas específico y devuelve un DataFrame con los resultados.
    """
    
    print(f"Iniciando balance para el rango: {fecha_inicio} a {fecha_fin}")

    # --- Conexión a MySQL ---
    """ 
    user = "inventar_simplex"
    password = "PLexyz31416"
    host = "149.50.133.195"
    port = 3306
    database = "inventar_SpcHidr"
     """
    try:
        engine = create_engine(f"mssql+pytds://sa:24gegepeNA@149.50.136.234/inventar_SpcHidr")
    except Exception as e:
        print(f"Error de conexión a la base de datos: {e}")
        return pd.DataFrame()

    # --- Diccionario de queries estándar (excepto F18) ---
    queries = {
        "F1": f"""SELECT SUM(Ton) AS Tonelaje, (SUM(Ton * CuTG00 / 100) / SUM(Ton)) * 100 AS Ley_Cu FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}' AND Origen = 'Stock' and (Fase <> 'SRR') AND Destino = 'CH01';""",
        "F2": f"""SELECT SUM(Ton) AS Tonelaje, (SUM(Ton * CuTG00 / 100) / SUM(Ton)) * 100 AS Ley_Cu FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}' AND Origen = 'Mina' AND (Fase <> 'SRR') AND Destino = 'CH01';""",
        "F3": f"""SELECT SUM(Ton) AS Tonelaje, (SUM(Ton * CuTG00 / 100) / SUM(Ton)) * 100 AS Ley_Cu FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}' AND Fase <> 'SRR' AND Destino = 'CH01';""",
        "F4": f"""
        SELECT
            ROUND(
                COALESCE((
                    SELECT SUM(CV006_tot)
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                ), 0) * (1 - 2.5/100.0),
                2
            ) AS Tonelaje,
            (
                SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0
                FROM inventar_SpcHidr.mov_cam
                WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                AND Fase <> 'SRR'
                AND Destino = 'CH01'
            ) AS Ley_Cu;
        """,
        "F5": f"""
                WITH
        tms_i AS (
            SELECT
                AVG(31.1017672705390 * ((v.niv_silo_a + v.niv_silo_b) / 2.0) * (1 - 2.5/100.0)) AS total_tms
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados v
            WHERE CAST(v.Fecha_turno AS DATE) = '{fecha_inicio}'
        ),
        tms_f AS (
            SELECT
                AVG(31.1017672705390 * ((v.niv_silo_a + v.niv_silo_b) / 2.0) * (1 - 2.5/100.0)) AS total_tms
            FROM inventar_SpcHidr.vista_resumen_datos_filtrados v
            WHERE CAST(v.Fecha_turno AS DATE) = '{fecha_fin}'
        ),
        ley_i AS (
            SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0 AS ley_cu
            FROM inventar_SpcHidr.mov_cam
            WHERE fecha = '{fecha_inicio}' AND Fase <> 'SRR' AND Destino = 'CH01'
        ),
        ley_f AS (
            SELECT (SUM(Ton * CuTG00 / 100.0) / NULLIF(SUM(Ton), 0)) * 100.0 AS ley_cu
            FROM inventar_SpcHidr.mov_cam
            WHERE fecha = '{fecha_fin}' AND Fase <> 'SRR' AND Destino = 'CH01'
        )
        SELECT
            COALESCE(tms_i.total_tms, 0) AS TMS_Inicial,
            COALESCE(tms_f.total_tms, 0) AS TMS_Final,
            COALESCE(tms_f.total_tms, 0) - COALESCE(tms_i.total_tms, 0) AS Tonelaje,
            ley_i.ley_cu AS Ley_Cu_1,
            ley_f.ley_cu AS Ley_Cu_2,
            COALESCE(
                (
                    (COALESCE(tms_f.total_tms, 0) * ley_f.ley_cu / 100.0) -
                    (COALESCE(tms_i.total_tms, 0) * ley_i.ley_cu / 100.0)
                ) / NULLIF(COALESCE(tms_f.total_tms, 0) - COALESCE(tms_i.total_tms, 0), 0) * 100.0,
                0
            ) AS Ley_Cu
        FROM tms_i
        CROSS JOIN tms_f
        CROSS JOIN ley_i
        CROSS JOIN ley_f;""",
        "F6": f"""SELECT
        /* ================================================================= */
        /* PRIMERA COLUMNA: Cálculo del Tonelaje Neto (F6)                    */
        /* ================================================================= */
        (
            ISNULL(
                (
                    -- Tonelaje de entrada (seco) desde la torre 1
                    SELECT ROUND(SUM(D.tsd), 2)
                    FROM (
                        SELECT sum(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd
                        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                        WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        AND i.id_torre = 1
                        GROUP BY CAST(vrdf.fecha_turno AS DATE)

                    ) AS D
                ), 0
            ) - ISNULL(
                (
                    -- Tonelaje de salida 1 (cv002)
                    SELECT sum(cv002_tot) * 0.93
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                ), 0
            ) - ISNULL(
                (
                    -- Tonelaje de salida 2 (cv201)
                    SELECT SUM(cv201_tot)
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                ), 0
            )
        ) AS Tonelaje,

        /* ================================================================= */
        /* SEGUNDA COLUMNA: Cálculo de la Ley de Cobre (F6)                   */
        /* ================================================================= */
        (
            -- INICIO DEL NUMERADOR: (Finos F12 - Finos F8)
            (
                ISNULL(
                    (
                        -- Finos de entrada (F12)
                        SELECT SUM(D.Finos)
                        FROM (
                            SELECT (sum(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100)) * AVG(i.CuT_Dia) / 100 AS Finos
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                            WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                            AND i.id_torre = 1
                            GROUP BY CAST(vrdf.fecha_turno AS DATE)

                        ) AS D
                    ), 0
                ) - ISNULL(
                    (
                        -- Finos de salida (F8) con la nueva lógica corregida
                        SELECT
                            (
                                SELECT SUM(cv002_tot) * 0.93
                                FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                                WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                            ) * (
                                SELECT (SUM(Ton * CuTG00 / 100) / NULLIF(SUM(Ton), 0))
                                FROM inventar_SpcHidr.mov_cam
                                WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                                AND Fase = 'SRR'
                                AND Destino = 'prueba'
                            )
                    ), 0
                )
            ) 
            -- FIN DEL NUMERADOR
            / 
            -- INICIO DEL DENOMINADOR: Tonelaje Neto (F6)
            NULLIF(
                (
                    ISNULL(
                        (
                            SELECT ROUND(SUM(D.tsd), 2)
                            FROM (
                                SELECT sum(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd
                                FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                                JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                                WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                                AND i.id_torre = 1
                                GROUP BY CAST(vrdf.fecha_turno AS DATE)

                            ) AS D
                        ), 0
                    ) - ISNULL(
                        (
                            SELECT sum(cv002_tot) * 0.93
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                            WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        ), 0
                    ) - ISNULL(
                        (
                            SELECT SUM(cv201_tot)
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                            WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        ), 0
                    )
                ), 0
            )
            -- FIN DEL DENOMINADOR
        ) * 100 AS Ley_Cu;
    """,
        "F7": f"""SELECT
        /* ================================================================= */
        /* PRIMERA COLUMNA: Cálculo del Tonelaje Neto (F7)                    */
        /* ================================================================= */
        (
            ISNULL(
                (
                    -- Tonelaje de entrada (seco) desde la torre 2
                    SELECT ROUND(SUM(D.tsd), 2)
                    FROM (
                        SELECT sum(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd
                        FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                        JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                        WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        AND i.id_torre = 2
                        GROUP BY CAST(vrdf.fecha_turno AS DATE)

                    ) AS D
                ), 0
            ) - ISNULL(
                (
                    -- Tonelaje de salida 1 (cv003)
                    SELECT sum(cv003_tot) * 0.93
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                ), 0
            ) - ISNULL(
                (
                    -- Tonelaje de salida 2 (cv202)
                    SELECT SUM(cv202_tot)
                    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                ), 0
            )
        ) AS Tonelaje,

        /* ================================================================= */
        /* SEGUNDA COLUMNA: Cálculo de la Ley de Cobre (F7)                   */
        /* ================================================================= */
        (
            -- INICIO DEL NUMERADOR: (Finos de Entrada - Finos de Salida)
            (
                ISNULL(
                    (
                        -- Finos de entrada (basado en cv108)
                        SELECT SUM(D.Finos)
                        FROM (
                            SELECT (sum(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100)) * AVG(i.CuT_Dia) / 100 AS Finos
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                            JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                            WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                            AND i.id_torre = 2
                            GROUP BY CAST(vrdf.fecha_turno AS DATE)

                        ) AS D
                    ), 0
                ) - ISNULL(
                    (
                        -- Finos de salida con la lógica corregida (basado en cv003)
                        SELECT
                            (
                                SELECT SUM(cv003_tot) * 0.93
                                FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                                WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                            ) * (
                                SELECT (SUM(Ton * CuTG00 / 100) / NULLIF(SUM(Ton), 0))
                                FROM inventar_SpcHidr.mov_cam
                                WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                                AND Fase = 'SRR'
                                AND Destino = 'prueba'
                            )
                    ), 0
                )
            ) 
            -- FIN DEL NUMERADOR
            / 
            -- INICIO DEL DENOMINADOR: Tonelaje Neto (F7)
            NULLIF(
                (
                    ISNULL(
                        (
                            SELECT ROUND(SUM(D.tsd), 2)
                            FROM (
                                SELECT sum(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd
                                FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
                                JOIN inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
                                WHERE vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                                AND i.id_torre = 2
                                GROUP BY CAST(vrdf.fecha_turno AS DATE)

                            ) AS D
                        ), 0
                    ) - ISNULL(
                        (
                            SELECT sum(cv003_tot) * 0.93
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                            WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        ), 0
                    ) - ISNULL(
                        (
                            SELECT SUM(cv202_tot)
                            FROM inventar_SpcHidr.vista_resumen_datos_filtrados
                            WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                        ), 0
                    )
                ), 0
            )
            -- FIN DEL DENOMINADOR
        ) * 100 AS Ley_Cu;
    """,
        "F8": f"""SELECT
    (
        SELECT sum(cv002_tot) * 0.93
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados
        WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    ) AS Tonelaje,

    (
        SELECT (SUM(Ton * CuTG00 / 100) / NULLIF(SUM(Ton), 0)) * 100
        FROM inventar_SpcHidr.mov_cam
        -- CORRECCIÓN: Se ajustó el rango de fechas para que coincida con el tonelaje
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND Fase = 'SRR'
        AND Destino = 'prueba'
    ) AS Ley_Cu;
    """,
        "F9": f"""SELECT
    (
        SELECT sum(cv003_tot) * 0.93
        FROM inventar_SpcHidr.vista_resumen_datos_filtrados
        WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    ) AS Tonelaje,

    (
        SELECT (SUM(Ton * CuTG00 / 100) / NULLIF(SUM(Ton), 0)) * 100
        FROM inventar_SpcHidr.mov_cam
        -- CORRECCIÓN: Se ajustó el rango de fechas para que coincida con el tonelaje
        WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND Fase = 'SRR'
        AND Destino = 'prueba'
    ) AS Ley_Cu;
    """,
        "F10": f"""SELECT 
        sum(cv201_tot) AS "Tonelaje",
        0 AS "Ley_Cu"
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}';""",
        "F11": f"""SELECT 
        sum(cv202_tot) AS "Tonelaje",
        0 AS "Ley_Cu"
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados
    WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}';""",
        "F12": f"""WITH D AS (
    SELECT
        sum(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
        AVG(i.CuT_Dia) AS ld
    FROM
        inventar_SpcHidr.vista_resumen_datos_filtrados vrdf -- Alias 'vrdf'
    JOIN
        inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
    WHERE
        vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND i.id_torre = 1
    GROUP BY
        CAST(vrdf.fecha_turno AS DATE)

    )
    SELECT
    ROUND(SUM(tsd), 2) AS "Tonelaje",
    ROUND(SUM(ld * tsd) / NULLIF(SUM(tsd), 0), 4) AS "Ley_Cu"
    FROM D;""",
        "F13": f"""WITH D AS (
    SELECT
        sum(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
        AVG(i.CuT_Dia) AS ld
    FROM
        inventar_SpcHidr.vista_resumen_datos_filtrados vrdf -- Alias 'vrdf'
    JOIN
        inventar_SpcHidr.import_leyes_torres i ON CAST(vrdf.fecha_turno AS DATE)
 = i.fecha
    WHERE
        vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        AND i.id_torre = 2
    GROUP BY
        CAST(vrdf.fecha_turno AS DATE)

    )
    SELECT
    ROUND(SUM(tsd), 2) AS "Tonelaje",
    ROUND(SUM(ld * tsd) / NULLIF(SUM(tsd), 0), 4) AS "Ley_Cu"
    FROM D;""",
        "F14": f"""WITH
  dias_de_conflicto AS (
    SELECT
      fecha
    FROM inventar_SpcHidr.control_apilado_diario
    WHERE
      fecha BETWEEN '{fecha_inicio}' AND DATEADD(DAY, 1, '{fecha_fin}')
      AND volumen_diario_m3 > 0
      AND pad_id IN (1, 2)
    GROUP BY fecha
    HAVING COUNT(DISTINCT pad_id) > 1
  ),
  datos_diarios_por_torre AS (
    SELECT
      CAST(vrdf.fecha_turno AS DATE) AS fecha_operacion,
      SUM(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
      AVG(i.CuT_Dia) AS ld
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
    JOIN inventar_SpcHidr.import_leyes_torres i
      ON CAST(vrdf.fecha_turno AS DATE) = i.fecha
    WHERE
      vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
      AND i.id_torre = 1
    GROUP BY CAST(vrdf.fecha_turno AS DATE)

    UNION ALL

    SELECT
      CAST(vrdf.fecha_turno AS DATE) AS fecha_operacion,
      SUM(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
      AVG(i.CuT_Dia) AS ld
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
    JOIN inventar_SpcHidr.import_leyes_torres i
      ON CAST(vrdf.fecha_turno AS DATE) = i.fecha
    WHERE
      vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
      AND i.id_torre = 2
    GROUP BY CAST(vrdf.fecha_turno AS DATE)
  )
  SELECT
  ISNULL(ROUND(SUM(dd.tsd), 2), 0) AS Tonelaje,
  ISNULL(ROUND(SUM(dd.tsd * dd.ld) / NULLIF(SUM(dd.tsd), 0), 4), 0) AS Ley_Cu
FROM datos_diarios_por_torre dd
WHERE
  -- Se mantiene la lógica de asignar la producción del día anterior al reporte de apilado
  dd.fecha_operacion IN (
    SELECT DISTINCT DATEADD(DAY, -1, cad.fecha)
    FROM inventar_SpcHidr.control_apilado_diario cad
    WHERE
      cad.fecha BETWEEN '{fecha_inicio}' AND DATEADD(DAY, 1, '{fecha_fin}')
      AND cad.pad_id = 2 -- Filtro para Pad 2
      AND cad.volumen_diario_m3 > 0
  );
""",
        "F15": f"""WITH
  dias_de_conflicto AS (
    SELECT
      fecha
    FROM inventar_SpcHidr.control_apilado_diario
    WHERE
      fecha BETWEEN '{fecha_inicio}' AND DATEADD(DAY, 1, '{fecha_fin}')
      AND volumen_diario_m3 > 0
      AND pad_id IN (1, 2)
    GROUP BY fecha
    HAVING COUNT(DISTINCT pad_id) > 1
  ),
  datos_diarios_por_torre AS (
    SELECT
      CAST(vrdf.fecha_turno AS DATE) AS fecha_operacion,
      SUM(vrdf.cv008_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
      AVG(i.CuT_Dia) AS ld
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
    JOIN inventar_SpcHidr.import_leyes_torres i
      ON CAST(vrdf.fecha_turno AS DATE) = i.fecha
    WHERE
      vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
      AND i.id_torre = 1
    GROUP BY CAST(vrdf.fecha_turno AS DATE)

    UNION ALL

    SELECT
      CAST(vrdf.fecha_turno AS DATE) AS fecha_operacion,
      SUM(vrdf.cv108_tot) * (1 - AVG(i.Humedades_Dia) / 100) AS tsd,
      AVG(i.CuT_Dia) AS ld
    FROM inventar_SpcHidr.vista_resumen_datos_filtrados vrdf
    JOIN inventar_SpcHidr.import_leyes_torres i
      ON CAST(vrdf.fecha_turno AS DATE) = i.fecha
    WHERE
      vrdf.fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
      AND i.id_torre = 2
    GROUP BY CAST(vrdf.fecha_turno AS DATE)
  )
  -- Paso 2: Sumar la producción de los días que corresponden a apilamiento en Pad 1 (lógica corregida)
SELECT
  ISNULL(ROUND(SUM(dd.tsd), 2), 0) AS Tonelaje,
  ISNULL(ROUND(SUM(dd.tsd * dd.ld) / NULLIF(SUM(dd.tsd), 0), 4), 0) AS Ley_Cu
FROM datos_diarios_por_torre dd
WHERE
  -- Se mantiene la lógica de asignar la producción del día anterior al reporte de apilado
  dd.fecha_operacion IN (
    SELECT DISTINCT DATEADD(DAY, -1, cad.fecha)
    FROM inventar_SpcHidr.control_apilado_diario cad
    WHERE
      cad.fecha BETWEEN '{fecha_inicio}' AND DATEADD(DAY, 1, '{fecha_fin}')
      AND cad.pad_id = 1 -- Filtro para Pad 1
      AND cad.volumen_diario_m3 > 0
  );
""",
    "F20": f"""SELECT ISNULL(SUM(cv025_tot * 0.89), 0) AS Tonelaje, '0' AS Ley_Cu FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}';""",
        "F21": f"""SELECT ISNULL(SUM(ton_reclamo_camiones), 0) AS Tonelaje, 0 AS Ley_Cu FROM inventar_SpcHidr.reclamos_tonelaje WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}';""",
        "F22": f"""SELECT ISNULL(SUM(Camiones_TMS_Reclamo_Oxidos), 0) AS Tonelaje, 0 AS Ley_Cu FROM inventar_SpcHidr.Datos_conciliados_of WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}';""",
        "F23": f"""SELECT
            COALESCE(
                (
                    (SELECT SUM(fino_producido) FROM inventar_SpcHidr.control_ley_ripio WHERE fecha_drenaje = '{fecha_fin}' AND PAD = 'OXIDOS') -
                    (SELECT SUM(fino_producido) FROM inventar_SpcHidr.control_ley_ripio WHERE fecha_drenaje = '{fecha_inicio}' AND PAD = 'OXIDOS')
                ), 0
            ) AS Tonelaje,
            100 AS Ley_Cu;""",
        "F24": f"""SELECT
            COALESCE(
                (
                    (SELECT SUM(fino_producido) FROM inventar_SpcHidr.control_ley_ripio WHERE fecha_drenaje = '{fecha_fin}' AND PAD = 'SULFUROS') -
                    (SELECT SUM(fino_producido) FROM inventar_SpcHidr.control_ley_ripio WHERE fecha_drenaje = '{fecha_inicio}' AND PAD = 'SULFUROS')
                ), 0
            ) AS Tonelaje,
            100 AS Ley_Cu;""",
        "F25": f"""SELECT
            (SELECT sum(cv001_tot) * 0.93 FROM inventar_SpcHidr.vista_resumen_datos_filtrados WHERE fecha_turno BETWEEN '{fecha_inicio}' AND '{fecha_fin}') AS Tonelaje,
            (SELECT (SUM(Ton * CuTG00 / 100) / NULLIF(SUM(Ton), 0)) * 100 FROM inventar_SpcHidr.mov_cam WHERE fecha BETWEEN '{fecha_inicio}' AND '{fecha_fin}' AND Fase = 'SRR' AND Destino = 'prueba') AS Ley_Cu;"""
    }

    # --- 4. Función Auxiliar (Requerida para cálculos de inventario inicial) ---
    def _run_flow_for_day(flow_key: str, fecha_un_dia: str):
        q = queries[flow_key].format(fecha_inicio=fecha_un_dia, fecha_fin=fecha_un_dia)
        d = pd.read_sql(q, engine)
        if d.empty:
            return 0.0, 0.0
        ton = pd.to_numeric(d.get("Tonelaje", pd.Series([0])).iloc[0], errors="coerce")
        ley = pd.to_numeric(d.get("Ley_Cu",   pd.Series([0])).iloc[0], errors="coerce")
        return float(0 if pd.isna(ton) else ton), float(0 if pd.isna(ley) else ley)

    # --- 5. Ejecución de Flujos ---
    todos_los_resultados = []

    # --- 5.1 Flujos estándar (del diccionario) ---
    print("Ejecutando flujos estándar...")
    for flujo, query in queries.items():
        try:
            df = pd.read_sql(query, engine)
            df.insert(0, "Flujo", flujo)
            todos_los_resultados.append(df)
            print(f" -> Flujo {flujo} calculado.")
        except Exception as e:
            print(f"ERROR en Flujo {flujo}: {e}")
            # Crear un DataFrame vacío con las columnas esperadas en caso de error
            df_error = pd.DataFrame([{"Flujo": flujo, "Tonelaje": 0, "Ley_Cu": 0}])
            todos_los_resultados.append(df_error)

    # --- 5.2 FLUJO F18 (Rotopala 2) - VERSIÓN OPTIMIZADA ---
    sql_f18 = text("""
    WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.campaña_id,
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos AS mt
        GROUP BY mt.campaña_id, mt.modulo_id
    ),
    Pct_Diario AS (
        SELECT
            CAST(crd.fecha AS date) AS fecha,
            crd.pad_id,
            crd.campaña_id,
            crd.modulo_id,
            CASE
                WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
                WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
                ELSE MAX(crd.avance_porcentaje)
            END AS pct_clip
        FROM inventar_SpcHidr.control_reclamo_diario AS crd
        WHERE CAST(crd.fecha AS date) BETWEEN :fi AND DATEADD(DAY, 1, :ff)
        GROUP BY CAST(crd.fecha AS date), crd.pad_id, crd.campaña_id, crd.modulo_id
    ),
    Pct_Segmentado AS (
        SELECT p.*, CASE WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id ORDER BY p.fecha) THEN 1 ELSE 0 END AS reset_flag
        FROM Pct_Diario AS p
    ),
    Pct_Seg_Id AS (
        SELECT ps.*, SUM(ps.reset_flag) OVER (PARTITION BY ps.campaña_id, ps.modulo_id, ps.pad_id ORDER BY ps.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS seg_id
        FROM Pct_Segmentado AS ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha, p.pad_id, p.campaña_id, p.modulo_id, p.pct_clip AS avance_porcentaje,
            CASE WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id, p.seg_id ORDER BY p.fecha)) < 0 THEN 0 ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id, p.seg_id ORDER BY p.fecha)) END AS avance_incremental
        FROM Pct_Seg_Id AS p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha, pad_id, campaña_id, modulo_id, MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date) BETWEEN :fi AND DATEADD(DAY, 1, :ff)
        GROUP BY CAST(fecha AS date), pad_id, campaña_id, modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            DATEADD(DAY, -1, a.fecha) AS fecha_operacion,
            a.campaña_id,
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario AS a
        JOIN Tms_Apilado_Por_Modulo  AS tm
        ON tm.campaña_id = a.campaña_id AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario AS vd
        ON vd.fecha = a.fecha AND vd.pad_id = a.pad_id
        AND vd.campaña_id = a.campaña_id AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 2 -- Filtro para F18 (Sulfuros)
        AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario AS r
        WHERE r.fecha_operacion BETWEEN :fi AND :ff
    ),
    -- CTE para agrupar toneladas por módulo activo
    ModulosActivos AS (
        SELECT
            r.campaña_id,
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario AS r
        WHERE r.fecha_operacion BETWEEN :fi AND :ff
        GROUP BY r.campaña_id, r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    -- 3. Calcular la ley ponderada (CORREGIDO JOIN PAD)
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                / NULLIF(SUM(ma.tms_reclamado_modulo), 0)) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos AS ma
        INNER JOIN inventar_SpcHidr.campaña AS c ON ma.campaña_id = c.id_campaña
        INNER JOIN inventar_SpcHidr.modulo AS m ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela AS p ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad AS pd ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio AS clr
            ON clr.Campana = c.numero_campaña
            AND clr.Parcela = p.numero
            -- Cruce PAD CORREGIDO con LIKE (ignora 'S' y mayúsculas)
            AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        -- Filtro por ID (más seguro)
        WHERE pd.id_pad = 2 -- Filtro para F18 (Sulfuros)
    )
    SELECT t.Tonelaje, l.Ley_Cu
    FROM Calculo_Tonelaje AS t
    CROSS JOIN Calculo_Ley AS l;
""")

    df_f18 = pd.read_sql(sql_f18, engine, params={"fi": fecha_inicio, "ff": fecha_fin})
    df_f18.insert(0, "Flujo", "F18")
    todos_los_resultados.append(df_f18)
    print(" -> Flujo F18 calculado.")

    print("Ejecutando flujo F19")
    sql_f19 = text("""
    WITH
    Tms_Apilado_Por_Modulo AS (
        SELECT
            mt.campaña_id,
            mt.modulo_id,
            SUM(mt.TMS) AS tms_total_apilado
        FROM inventar_SpcHidr.modulos_turnos AS mt
        GROUP BY mt.campaña_id, mt.modulo_id
    ),
    Pct_Diario AS (
        SELECT
            CAST(crd.fecha AS date) AS fecha,
            crd.pad_id,
            crd.campaña_id,
            crd.modulo_id,
            CASE
                WHEN MAX(crd.avance_porcentaje) < 0 THEN 0
                WHEN MAX(crd.avance_porcentaje) > 1 THEN 1
                ELSE MAX(crd.avance_porcentaje)
            END AS pct_clip
        FROM inventar_SpcHidr.control_reclamo_diario AS crd
        WHERE CAST(crd.fecha AS date) BETWEEN :fi AND DATEADD(DAY, 1, :ff)
        GROUP BY CAST(crd.fecha AS date), crd.pad_id, crd.campaña_id, crd.modulo_id
    ),
    Pct_Segmentado AS (
        SELECT p.*, CASE WHEN p.pct_clip < LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id ORDER BY p.fecha) THEN 1 ELSE 0 END AS reset_flag
        FROM Pct_Diario AS p
    ),
    Pct_Seg_Id AS (
        SELECT ps.*, SUM(ps.reset_flag) OVER (PARTITION BY ps.campaña_id, ps.modulo_id, ps.pad_id ORDER BY ps.fecha ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS seg_id
        FROM Pct_Segmentado AS ps
    ),
    Avance_Incremental_Diario AS (
        SELECT
            p.fecha, p.pad_id, p.campaña_id, p.modulo_id, p.pct_clip AS avance_porcentaje,
            CASE WHEN (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id, p.seg_id ORDER BY p.fecha)) < 0 THEN 0 ELSE (p.pct_clip - LAG(p.pct_clip, 1, 0) OVER (PARTITION BY p.campaña_id, p.modulo_id, p.pad_id, p.seg_id ORDER BY p.fecha)) END AS avance_incremental
        FROM Pct_Seg_Id AS p
    ),
    Volumen_Diario AS (
        SELECT
            CAST(fecha AS date) AS fecha, pad_id, campaña_id, modulo_id, MAX(volumen_diario_m3) AS vol_m3
        FROM inventar_SpcHidr.control_reclamo_diario
        WHERE CAST(fecha AS date) BETWEEN :fi AND DATEADD(DAY, 1, :ff)
        GROUP BY CAST(fecha AS date), pad_id, campaña_id, modulo_id
    ),
    Reclamo_Diario AS (
        SELECT
            DATEADD(DAY, -1, a.fecha) AS fecha_operacion,
            a.campaña_id,
            a.modulo_id,
            (tm.tms_total_apilado * a.avance_incremental) AS tonelaje_reclamado_diario
        FROM Avance_Incremental_Diario AS a
        JOIN Tms_Apilado_Por_Modulo  AS tm
        ON tm.campaña_id = a.campaña_id AND tm.modulo_id = a.modulo_id
        JOIN Volumen_Diario AS vd
        ON vd.fecha = a.fecha AND vd.pad_id = a.pad_id
        AND vd.campaña_id = a.campaña_id AND vd.modulo_id = a.modulo_id
        WHERE a.pad_id = 1 -- Filtro para F19 (Óxidos)
        AND vd.vol_m3 > 0
    ),
    Calculo_Tonelaje AS (
        SELECT COALESCE(SUM(r.tonelaje_reclamado_diario), 0) AS Tonelaje
        FROM Reclamo_Diario AS r
        WHERE r.fecha_operacion BETWEEN :fi AND :ff
    ),
    -- CTE para agrupar toneladas por módulo activo
    ModulosActivos AS (
        SELECT
            r.campaña_id,
            r.modulo_id,
            SUM(r.tonelaje_reclamado_diario) AS tms_reclamado_modulo
        FROM Reclamo_Diario AS r
        WHERE r.fecha_operacion BETWEEN :fi AND :ff
        GROUP BY r.campaña_id, r.modulo_id
        HAVING SUM(r.tonelaje_reclamado_diario) > 0
    ),
    -- 3. Calcular la ley ponderada (CORREGIDO JOIN PAD)
    Calculo_Ley AS (
        SELECT
            COALESCE(
                (SUM(ma.tms_reclamado_modulo * clr.ley_ripio / 100.0)
                / NULLIF(SUM(ma.tms_reclamado_modulo), 0)) * 100.0,
                0
            ) AS Ley_Cu
        FROM ModulosActivos AS ma
        INNER JOIN inventar_SpcHidr.campaña AS c ON ma.campaña_id = c.id_campaña
        INNER JOIN inventar_SpcHidr.modulo AS m ON ma.modulo_id = m.id_modulo
        INNER JOIN inventar_SpcHidr.parcela AS p ON m.id_parcela = p.id_parcela
        INNER JOIN inventar_SpcHidr.pad AS pd ON p.id_pad = pd.id_pad
        INNER JOIN inventar_SpcHidr.control_ley_ripio AS clr
            ON clr.Campana = c.numero_campaña
            AND clr.Parcela = p.numero
            -- Cruce PAD CORREGIDO con LIKE (ignora 'S' y mayúsculas)
            AND UPPER(clr.PAD) LIKE UPPER(pd.nombre) + '%'
        -- Filtro por ID (más seguro)
        WHERE pd.id_pad = 1 -- Filtro para F19 (Óxidos)
    )
    SELECT t.Tonelaje, l.Ley_Cu
    FROM Calculo_Tonelaje AS t
    CROSS JOIN Calculo_Ley AS l;
""")

    df_f19 = pd.read_sql(sql_f19, engine, params={"fi": fecha_inicio, "ff": fecha_fin})
    df_f19.insert(0, "Flujo", "F19")
    todos_los_resultados.append(df_f19)
    print(" -> Flujo F19 calculado.")

    # --- 6. Consolidación y Cálculos Posteriores ---
    df_final = pd.concat(todos_los_resultados, ignore_index=True)

    # --- 6.1 FLUJO F16 y F17 (Cálculo por diferencia) ---
    print("Calculando flujos F16 y F17 por diferencia...")
    def _get_single(df, flujo, col, how="first"):
        s = df.loc[df["Flujo"] == flujo, col]
        if s.empty: return 0.0
        v = pd.to_numeric(s.iloc[0], errors="coerce") if how == "first" else pd.to_numeric(s, errors="coerce").sum()
        return 0.0 if pd.isna(v) else float(v)

    # Cálculo F16
    ton_f14 = _get_single(df_final, "F14", "Tonelaje")
    ley_f14 = _get_single(df_final, "F14", "Ley_Cu")
    ton_f18 = _get_single(df_final, "F18", "Tonelaje")
    ley_f18 = _get_single(df_final, "F18", "Ley_Cu")
    ton_f21 = _get_single(df_final, "F21", "Tonelaje")
    ley_f21 = _get_single(df_final, "F21", "Ley_Cu")
    ton_f24 = _get_single(df_final, "F24", "Tonelaje")
    ton_f16 = ton_f14 - ton_f18 - ton_f21 - ton_f24
    finos_in_16 = ton_f14 * ley_f14
    finos_out_16 = (ton_f18 * ley_f18) + (ton_f21 * ley_f21)
    ley_f16 = ((finos_in_16 - finos_out_16) / ton_f16) if ton_f16 != 0 else 0.0
    df_f16 = pd.DataFrame({"Flujo": ["F16"], "Tonelaje": [ton_f16], "Ley_Cu": [ley_f16]})
    todos_los_resultados.append(df_f16)

    # Cálculo F17
    ton_f15 = _get_single(df_final, "F15", "Tonelaje")
    ley_f15 = _get_single(df_final, "F15", "Ley_Cu")
    ton_f19 = _get_single(df_final, "F19", "Tonelaje")
    ley_f19 = _get_single(df_final, "F19", "Ley_Cu")
    ton_f22 = _get_single(df_final, "F22", "Tonelaje")
    ley_f22 = _get_single(df_final, "F22", "Ley_Cu")
    ton_f23 = _get_single(df_final, "F23", "Tonelaje")
    
    ton_f17 = ton_f15 - ton_f19 - ton_f22 - ton_f23
    finos_in_17 = ton_f15 * ley_f15
    finos_out_17 = (ton_f19 * ley_f19) + (ton_f22 * ley_f22)
    ley_f17 = ((finos_in_17 - finos_out_17) / ton_f17) if ton_f17 != 0 else 0.0
    df_f17 = pd.DataFrame({"Flujo": ["F17"], "Tonelaje": [ton_f17], "Ley_Cu": [ley_f17]})
    todos_los_resultados.append(df_f17)

    # --- 6.2 Inventarios Iniciales para F16 y F17 (CORREGIDO) ---
    print("Calculando inventarios iniciales...")

    # F14 y F15 iniciales se pueden calcular con la función auxiliar
    ton14_i, ley14_i = _run_flow_for_day("F14", fecha_inicio)
    ton15_i, ley15_i = _run_flow_for_day("F15", fecha_inicio)

    # Para F18 (inventario inicial con la misma query parametrizada)
    print(" -> Calculando inventario inicial para F18...")
    d18 = pd.read_sql(sql_f18, engine, params={"fi": fecha_inicio, "ff": fecha_inicio})
    ton18_i = float(d18["Tonelaje"].iloc[0]) if not d18.empty else 0.0
    ley18_i = float(d18["Ley_Cu"].iloc[0])   if not d18.empty else 0.0

    # Para F19 (inventario inicial con la misma query parametrizada)
    print(" -> Calculando inventario inicial para F19...")
    d19 = pd.read_sql(sql_f19, engine, params={"fi": fecha_inicio, "ff": fecha_inicio})
    ton19_i = float(d19["Tonelaje"].iloc[0]) if not d19.empty else 0.0
    ley19_i = float(d19["Ley_Cu"].iloc[0])   if not d19.empty else 0.0

    # Ahora calculamos los inventarios iniciales de F16 y F17 con los valores obtenidos
    tms_ini_f16 = ton14_i - ton18_i
    ley_ini_f16 = ((ton14_i * ley14_i) - (ton18_i * ley18_i)) / tms_ini_f16 if tms_ini_f16 != 0 else 0.0

    tms_ini_f17 = ton15_i - ton19_i
    ley_ini_f17 = ((ton15_i * ley15_i) - (ton19_i * ley19_i)) / tms_ini_f17 if tms_ini_f17 != 0 else 0.0

    # Inyectar inventarios en los dataframes correspondientes
    df_f16["TMS_Inicial"] = tms_ini_f16
    df_f16["Ley_Cu_1"]    = ley_ini_f16
    df_f17["TMS_Inicial"] = tms_ini_f17
    df_f17["Ley_Cu_1"]    = ley_ini_f17

    # --- 6.3 Ajustes finales de Leyes ---
    print("Realizando ajustes finales de leyes...")
    df_final = pd.concat(todos_los_resultados, ignore_index=True)

    # Asignar leyes a F21 y F22 desde F18 y F19
    df_final.loc[df_final["Flujo"] == "F21", "Ley_Cu"] = ley_f18
    df_final.loc[df_final["Flujo"] == "F22", "Ley_Cu"] = ley_f19

    # Calcular Ley_Cu para F20
    diferencia_ton = ton_f18 + ton_f19
    ley_f20 = ((ton_f18 * ley_f18) + (ton_f19 * ley_f19)) / diferencia_ton if diferencia_ton != 0 else 0.0
    df_final.loc[df_final["Flujo"] == "F20", "Ley_Cu"] = ley_f20


    # --- 7. Formateo y Exportación Final ---
    print("Formateando y exportando resultados a Excel...")
    # Ordenar de F1 a F25
    orden_flujos = [f"F{i}" for i in range(1, 26)]
    df_final["Flujo"] = pd.Categorical(df_final["Flujo"], categories=orden_flujos, ordered=True)
    df_final = df_final.sort_values("Flujo").reset_index(drop=True)

    # Asegurar que todas las columnas existan antes de seleccionarlas
    columnas_finales = ["Flujo", "TMS_Inicial", "Ley_Cu_1", "TMS_Final", "Ley_Cu_2", "Tonelaje", "Ley_Cu"]
    for col in columnas_finales:
        if col not in df_final.columns:
            df_final[col] = pd.NA

    df_final = df_final[columnas_finales]

    print("Balance completado. Devolviendo resultados.")
    return df_final
def guardar_balance_en_bd(df_final, caso_id, fecha_inicio, fecha_fin, engine, truncate=False):
    """
    Persiste en BD los resultados del balance de flujos.

    Parámetros
    ----------
    df_final : pd.DataFrame
        Debe incluir (al menos) las columnas:
        ['Flujo','Tonelaje','Ley_Cu','TMS_Inicial','Ley_Cu_1','TMS_Final','Ley_Cu_2'].
        - 'Flujo' se interpreta como 'codigo_flujo' (F1..F25).
        - 'Ley_Cu' se interpreta como %Cu (no fracción).
    caso_id : int
        Identificador del caso.
    fecha_inicio : str | date-like
        Fecha de inicio del período (YYYY-MM-DD).
    fecha_fin : str | date-like
        Fecha de fin del período (YYYY-MM-DD).
    engine : sqlalchemy.Engine
        Conexión SQLAlchemy a MySQL/MariaDB.
    truncate : bool, opcional (False)
        Si True, se vacía la tabla completa antes de insertar.
        Si False, solo se borra el período (caso_id, fecha_inicio, fecha_fin).

    Efectos
    -------
    Inserta en inventar_SpcHidr.balances_flujos_resultados las columnas:
    ['caso_id','fecha_inicio','fecha_fin','codigo_flujo','Tonelaje','Cu','FCu',
     'TMS_Inicial','Ley_Cu_1','TMS_Final','Ley_Cu_2']
    """
    # Copia de trabajo
    df = df_final.copy()

    # 1) Normalización de nombres y columnas mínimas
    df.rename(columns={'Flujo': 'codigo_flujo', 'Ley_Cu': 'Cu'}, inplace=True)
    for col in ['Tonelaje', 'Cu', 'TMS_Inicial', 'Ley_Cu_1', 'TMS_Final', 'Ley_Cu_2']:
        if col not in df.columns:
            df[col] = 0.0

    # 2) Tipos numéricos seguros
    df[['Tonelaje', 'Cu', 'TMS_Inicial', 'Ley_Cu_1', 'TMS_Final', 'Ley_Cu_2']] = (
        df[['Tonelaje', 'Cu', 'TMS_Inicial', 'Ley_Cu_1', 'TMS_Final', 'Ley_Cu_2']]
        .apply(pd.to_numeric, errors='coerce').fillna(0.0)
    )

    # 3) Cálculo de fino (FCu = Tonelaje * Cu[%] / 100)
    df['FCu'] = df['Tonelaje'] * (df['Cu'] / 100.0)

    # 4) Fechas ordenadas y claves
    fi = pd.to_datetime(fecha_inicio).date()
    ff = pd.to_datetime(fecha_fin).date()
    if fi > ff:
        fi, ff = ff, fi

    df['caso_id'] = int(caso_id)
    df['fecha_inicio'] = fi
    df['fecha_fin'] = ff

    # 5) Redondeos acordes a definición DECIMAL de la tabla
    df['Tonelaje'] = df['Tonelaje'].round(3)   # DECIMAL(12,3) recomendado
    df['Cu']       = df['Cu'].round(4)         # DECIMAL(10,4)
    df['FCu']      = df['FCu'].round(3)        # DECIMAL(12,3)

    # 6) Columnas de salida (orden estable)
    cols_out = [
        'caso_id','fecha_inicio','fecha_fin','codigo_flujo',
        'Tonelaje','Cu','FCu','TMS_Inicial','Ley_Cu_1','TMS_Final','Ley_Cu_2'
    ]

    # 7) Persistencia idempotente
    with engine.begin() as conn:
        if truncate:
            # Vacía toda la tabla (requiere privilegios adecuados)
            conn.execute(text("TRUNCATE TABLE inventar_SpcHidr.balances_flujos_resultados"))
        else:
            # Borra solo el período del caso actual
            conn.execute(
                text("""
                    DELETE FROM inventar_SpcHidr.balances_flujos_resultados
                    WHERE caso_id = :c AND fecha_inicio = :fi AND fecha_fin = :ff
                """),
                {"c": int(caso_id), "fi": fi, "ff": ff}
            )

        # Inserción por lotes
        if 'generado_en' not in df.columns:
            df['generado_en'] = datetime.now()
        df[cols_out].to_sql(
            'balances_flujos_resultados',
            con=conn,
            schema='inventar_SpcHidr',
            if_exists='append',
            index=False
        )


def ejecutar_y_guardar_balance(caso_id, fecha_inicio, fecha_fin, engine, truncate=False):
    df_final = ejecutar_balance_flujos(fecha_inicio, fecha_fin)
    guardar_balance_en_bd(df_final, caso_id, fecha_inicio, fecha_fin, engine, truncate=truncate)
    return df_final
