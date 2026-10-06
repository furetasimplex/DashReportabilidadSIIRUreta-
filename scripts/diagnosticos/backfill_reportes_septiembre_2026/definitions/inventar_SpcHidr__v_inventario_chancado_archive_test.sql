CREATE VIEW [inventar_SpcHidr].[v_inventario_chancado_archive_test]
AS

WITH Parametros AS
(
    SELECT
        CAST(5.0 AS float) AS Cantidad_Bins,
        CAST(1.6 AS float) AS Densidad_Ton_M3,
        CAST(1200.0 AS float) AS Tolva_Compensacion_TMH,

        /* Cambio confirmado de metodología de descarga:
           antes: niveles horarios;
           desde 30-06-2026: Archive Value diario replicado. */
        CAST('2026-06-30' AS date) AS Fecha_Inicio_Archive_Value
),

/*==============================================================
  1. Base cruda
==============================================================*/
BaseBloqueArchive AS
(
    SELECT
        CAST(
            DATEADD(HOUR, -8, df.fecha_inicial)
            AS date
        ) AS Fecha_Operacional,

        df.fecha_inicial,

        TRY_CONVERT(float, df.nivel_silo_a) AS nivel_silo_a,
        TRY_CONVERT(float, df.nivel_silo_b) AS nivel_silo_b,

        TRY_CONVERT(float, df.nivel_harnero_a) AS nivel_harnero_a,
        TRY_CONVERT(float, df.nivel_harnero_b) AS nivel_harnero_b,
        TRY_CONVERT(float, df.nivel_harnero_c) AS nivel_harnero_c,
        TRY_CONVERT(float, df.nivel_harnero_d) AS nivel_harnero_d,
        TRY_CONVERT(float, df.nivel_harnero_e) AS nivel_harnero_e,

        TRY_CONVERT(float, df.nivel_chancado_a) AS nivel_chancado_a,
        TRY_CONVERT(float, df.nivel_chancado_b) AS nivel_chancado_b,
        TRY_CONVERT(float, df.nivel_chancado_c) AS nivel_chancado_c,
        TRY_CONVERT(float, df.nivel_chancado_d) AS nivel_chancado_d,
        TRY_CONVERT(float, df.nivel_chancado_e) AS nivel_chancado_e

    FROM inventar_SpcHidr.datos_filtrados AS df

    WHERE df.fecha_inicial >=
          DATEADD(DAY, -400, CAST(GETDATE() AS date))
),

/*==============================================================
  2. Horas físicas esperadas por día operacional

  Chile continental:
      Pacific SA Standard Time

  Posibles duraciones físicas:
      23 h = adelanto horario
      24 h = día normal
      25 h = atraso horario
==============================================================*/
HorasEsperadasArchive AS
(
    SELECT
        f.Fecha_Operacional,

        DATEADD(
            HOUR,
            8,
            CAST(f.Fecha_Operacional AS datetime2)
        ) AS Inicio_Local,

        DATEADD(
            HOUR,
            8,
            CAST(
                DATEADD(DAY, 1, f.Fecha_Operacional)
                AS datetime2
            )
        ) AS Fin_Local,

        CAST
        (
            DATEDIFF
            (
                MINUTE,

                SWITCHOFFSET
                (
                    DATEADD(
                        HOUR,
                        8,
                        CAST(f.Fecha_Operacional AS datetime2)
                    )
                    AT TIME ZONE 'Pacific SA Standard Time',
                    '+00:00'
                ),

                SWITCHOFFSET
                (
                    DATEADD(
                        HOUR,
                        8,
                        CAST(
                            DATEADD(DAY, 1, f.Fecha_Operacional)
                            AS datetime2
                        )
                    )
                    AT TIME ZONE 'Pacific SA Standard Time',
                    '+00:00'
                )
            ) / 60.0

            AS decimal(10,2)
        ) AS Horas_Fisicas_Esperadas

    FROM
    (
        SELECT DISTINCT
            Fecha_Operacional
        FROM BaseBloqueArchive
    ) AS f
),

/*==============================================================
  3. Registros esperados en datos_filtrados

  Comportamiento observado:
      23 horas físicas -> 23 registros
      24 horas físicas -> 24 registros
      25 horas físicas -> 24 registros

  La hora repetida del cambio a horario de invierno no queda
  almacenada como una fila local adicional.
==============================================================*/
RegistrosEsperadosArchive AS
(
    SELECT
        h.Fecha_Operacional,
        h.Inicio_Local,
        h.Fin_Local,
        h.Horas_Fisicas_Esperadas,

        CASE
            WHEN h.Horas_Fisicas_Esperadas < 24
                THEN CAST(h.Horas_Fisicas_Esperadas AS int)
            ELSE 24
        END AS Registros_Horarios_Esperados

    FROM HorasEsperadasArchive AS h
),

/*==============================================================
  4. Validación del bloque de niveles

  REGLAS COMUNES
  - Cantidad de filas correcta según DST y almacenamiento.
  - Primera fila 08:00.
  - Última fila 07:00 del día siguiente.

  METODOLOGÍA HISTÓRICA (< 30-06-2026)
  - Datos horarios.
  - Para inventario se utiliza snapshot 08:00.
  - Se exige que los 12 sensores estén presentes a las 08:00.
  - NO se exige que todos estén presentes durante las 24 h.
  - NO se exige constancia diaria.

  METODOLOGÍA ARCHIVE VALUE (>= 30-06-2026)
  - Un valor diario replicado.
  - Todos los sensores deben estar presentes en todas las filas.
  - Cada sensor debe tener exactamente un valor distinto.
==============================================================*/
ValidacionBloqueArchive AS
(
    SELECT
        b.Fecha_Operacional,

        MIN(b.fecha_inicial) AS Primera_Fila_Bloque,
        MAX(b.fecha_inicial) AS Ultima_Fila_Bloque,
        COUNT(*) AS Cantidad_Filas_Bloque,

        CASE
            WHEN
                COUNT(*) = h.Registros_Horarios_Esperados

                AND MIN(b.fecha_inicial) =
                    DATEADD(
                        HOUR,
                        8,
                        CAST(b.Fecha_Operacional AS datetime2)
                    )

                AND MAX(b.fecha_inicial) =
                    DATEADD(
                        HOUR,
                        7,
                        DATEADD(
                            DAY,
                            1,
                            CAST(b.Fecha_Operacional AS datetime2)
                        )
                    )

                AND
                (
                    /*==================================================
                      METODOLOGÍA HISTÓRICA
                    ==================================================*/
                    (
                        b.Fecha_Operacional
                            < p.Fecha_Inicio_Archive_Value

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_silo_a IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_silo_b IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_harnero_a IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_harnero_b IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_harnero_c IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_harnero_d IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_harnero_e IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_chancado_a IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_chancado_b IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_chancado_c IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_chancado_d IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1

                        AND SUM(
                            CASE
                                WHEN DATEPART(HOUR, b.fecha_inicial) = 8
                                 AND DATEPART(MINUTE, b.fecha_inicial) = 0
                                 AND b.nivel_chancado_e IS NOT NULL
                                THEN 1 ELSE 0
                            END
                        ) = 1
                    )

                    OR

                    /*==================================================
                      METODOLOGÍA ARCHIVE VALUE
                    ==================================================*/
                    (
                        b.Fecha_Operacional
                            >= p.Fecha_Inicio_Archive_Value

                        AND COUNT(b.nivel_silo_a) = COUNT(*)
                        AND COUNT(b.nivel_silo_b) = COUNT(*)

                        AND COUNT(b.nivel_harnero_a) = COUNT(*)
                        AND COUNT(b.nivel_harnero_b) = COUNT(*)
                        AND COUNT(b.nivel_harnero_c) = COUNT(*)
                        AND COUNT(b.nivel_harnero_d) = COUNT(*)
                        AND COUNT(b.nivel_harnero_e) = COUNT(*)

                        AND COUNT(b.nivel_chancado_a) = COUNT(*)
                        AND COUNT(b.nivel_chancado_b) = COUNT(*)
                        AND COUNT(b.nivel_chancado_c) = COUNT(*)
                        AND COUNT(b.nivel_chancado_d) = COUNT(*)
                        AND COUNT(b.nivel_chancado_e) = COUNT(*)

                        AND COUNT(DISTINCT b.nivel_silo_a) = 1
                        AND COUNT(DISTINCT b.nivel_silo_b) = 1

                        AND COUNT(DISTINCT b.nivel_harnero_a) = 1
                        AND COUNT(DISTINCT b.nivel_harnero_b) = 1
                        AND COUNT(DISTINCT b.nivel_harnero_c) = 1
                        AND COUNT(DISTINCT b.nivel_harnero_d) = 1
                        AND COUNT(DISTINCT b.nivel_harnero_e) = 1

                        AND COUNT(DISTINCT b.nivel_chancado_a) = 1
                        AND COUNT(DISTINCT b.nivel_chancado_b) = 1
                        AND COUNT(DISTINCT b.nivel_chancado_c) = 1
                        AND COUNT(DISTINCT b.nivel_chancado_d) = 1
                        AND COUNT(DISTINCT b.nivel_chancado_e) = 1
                    )
                )

            THEN 1
            ELSE 0
        END AS Flag_Bloque_Archive_Valido

    FROM BaseBloqueArchive AS b

    INNER JOIN RegistrosEsperadosArchive AS h
        ON h.Fecha_Operacional = b.Fecha_Operacional

    CROSS JOIN Parametros AS p

    GROUP BY
        b.Fecha_Operacional,
        h.Registros_Horarios_Esperados,
        p.Fecha_Inicio_Archive_Value
),

/*==============================================================
  5. Selección de la fila de las 08:00
==============================================================*/
RegistrosHora8 AS
(
    SELECT
        CAST(df.fecha_inicial AS date) AS Fecha_Lectura_D1,
        df.fecha_inicial,

        TRY_CONVERT(float, df.nivel_silo_a) AS nivel_silo_a,
        TRY_CONVERT(float, df.nivel_silo_b) AS nivel_silo_b,

        TRY_CONVERT(float, df.nivel_harnero_a) AS nivel_harnero_a,
        TRY_CONVERT(float, df.nivel_harnero_b) AS nivel_harnero_b,
        TRY_CONVERT(float, df.nivel_harnero_c) AS nivel_harnero_c,
        TRY_CONVERT(float, df.nivel_harnero_d) AS nivel_harnero_d,
        TRY_CONVERT(float, df.nivel_harnero_e) AS nivel_harnero_e,

        TRY_CONVERT(float, df.nivel_chancado_a) AS nivel_chancado_a,
        TRY_CONVERT(float, df.nivel_chancado_b) AS nivel_chancado_b,
        TRY_CONVERT(float, df.nivel_chancado_c) AS nivel_chancado_c,
        TRY_CONVERT(float, df.nivel_chancado_d) AS nivel_chancado_d,
        TRY_CONVERT(float, df.nivel_chancado_e) AS nivel_chancado_e

    FROM inventar_SpcHidr.datos_filtrados AS df

    WHERE DATEPART(HOUR, df.fecha_inicial) = 8
      AND DATEPART(MINUTE, df.fecha_inicial) = 0
      AND df.fecha_inicial >=
          DATEADD(DAY, -400, CAST(GETDATE() AS date))
),

/*==============================================================
  6. Consolidación de registros encontrados a las 08:00
==============================================================*/
PromedioHora8 AS
(
    SELECT
        Fecha_Lectura_D1,

        MIN(fecha_inicial) AS Primera_Lectura_Hora_8,
        MAX(fecha_inicial) AS Ultima_Lectura_Hora_8,
        COUNT(*) AS Cantidad_Registros_Hora_8,

        AVG(nivel_silo_a) AS nivel_silo_a,
        AVG(nivel_silo_b) AS nivel_silo_b,

        AVG(nivel_harnero_a) AS nivel_harnero_a,
        AVG(nivel_harnero_b) AS nivel_harnero_b,
        AVG(nivel_harnero_c) AS nivel_harnero_c,
        AVG(nivel_harnero_d) AS nivel_harnero_d,
        AVG(nivel_harnero_e) AS nivel_harnero_e,

        AVG(nivel_chancado_a) AS nivel_chancado_a,
        AVG(nivel_chancado_b) AS nivel_chancado_b,
        AVG(nivel_chancado_c) AS nivel_chancado_c,
        AVG(nivel_chancado_d) AS nivel_chancado_d,
        AVG(nivel_chancado_e) AS nivel_chancado_e

    FROM RegistrosHora8

    GROUP BY Fecha_Lectura_D1
),

/*==============================================================
  7. Fecha operacional
==============================================================*/
FechaOperacional AS
(
    SELECT
        CAST(p.Fecha_Lectura_D1 AS date) AS Fecha,

        p.Fecha_Lectura_D1,
        p.Primera_Lectura_Hora_8,
        p.Ultima_Lectura_Hora_8,
        p.Cantidad_Registros_Hora_8,

        p.nivel_silo_a,
        p.nivel_silo_b,

        p.nivel_harnero_a,
        p.nivel_harnero_b,
        p.nivel_harnero_c,
        p.nivel_harnero_d,
        p.nivel_harnero_e,

        p.nivel_chancado_a,
        p.nivel_chancado_b,
        p.nivel_chancado_c,
        p.nivel_chancado_d,
        p.nivel_chancado_e

    FROM PromedioHora8 AS p
),

/*==============================================================
  8. Promedio de sensores por instalación
==============================================================*/
NivelesPromedio AS
(
    SELECT
        f.*,

        silo.Nivel_Inventario_Silo,
        silo.Sensores_Silo_Validos,

        harnero.Nivel_Inventario_Harnero,
        harnero.Sensores_Harnero_Validos,

        chancado.Nivel_Inventario_Chancado,
        chancado.Sensores_Chancado_Validos

    FROM FechaOperacional AS f

    CROSS APPLY
    (
        SELECT
            AVG(v.Valor) AS Nivel_Inventario_Silo,
            COUNT(v.Valor) AS Sensores_Silo_Validos
        FROM
        (
            VALUES
                (f.nivel_silo_a),
                (f.nivel_silo_b)
        ) AS v(Valor)
    ) AS silo

    CROSS APPLY
    (
        SELECT
            AVG(v.Valor) AS Nivel_Inventario_Harnero,
            COUNT(v.Valor) AS Sensores_Harnero_Validos
        FROM
        (
            VALUES
                (f.nivel_harnero_a),
                (f.nivel_harnero_b),
                (f.nivel_harnero_c),
                (f.nivel_harnero_d),
                (f.nivel_harnero_e)
        ) AS v(Valor)
    ) AS harnero

    CROSS APPLY
    (
        SELECT
            AVG(v.Valor) AS Nivel_Inventario_Chancado,
            COUNT(v.Valor) AS Sensores_Chancado_Validos
        FROM
        (
            VALUES
                (f.nivel_chancado_a),
                (f.nivel_chancado_b),
                (f.nivel_chancado_c),
                (f.nivel_chancado_d),
                (f.nivel_chancado_e)
        ) AS v(Valor)
    ) AS chancado
),

/*==============================================================
  9. Humedad, parámetros y validación del bloque
==============================================================*/
BaseConHumedad AS
(
    SELECT
        n.*,

        va.Primera_Fila_Bloque,
        va.Ultima_Fila_Bloque,
        va.Cantidad_Filas_Bloque,

        ISNULL(
            va.Flag_Bloque_Archive_Valido,
            0
        ) AS Flag_Bloque_Archive_Valido,

        h.Humedad_Inventario,
        h.Regla_Humedad_Inventario,
        h.Flag_Humedad_Inventario_Valida,

        h.Fecha_Humedad_TM1,
        h.Torre_Humedad_TM1,
        h.Turno_Humedad_TM1,
        h.Fuente_Humedad_TM1,

        h.Fecha_Humedad_TM2,
        h.Torre_Humedad_TM2,
        h.Turno_Humedad_TM2,
        h.Fuente_Humedad_TM2,

        p.Cantidad_Bins,
        p.Densidad_Ton_M3,
        p.Tolva_Compensacion_TMH,

        0.0957 * n.Nivel_Inventario_Harnero
            + 0.43 AS Y_Harnero,

        0.0957 * n.Nivel_Inventario_Chancado
            + 0.43 AS Y_Chancado

    FROM NivelesPromedio AS n

    CROSS JOIN Parametros AS p

    LEFT JOIN inventar_SpcHidr.v_humedad_inventario_test AS h
        ON h.Fecha = n.Fecha

    LEFT JOIN ValidacionBloqueArchive AS va
        ON va.Fecha_Operacional = n.Fecha
),

/*==============================================================
  10. Cálculo de inventarios húmedos TMH
==============================================================*/
InventariosTMH AS
(
    SELECT
        b.*,

        CASE
            WHEN b.Nivel_Inventario_Silo IS NULL
                THEN NULL
            ELSE
                PI()
                * POWER(CAST(7.5 AS float), 2)
                * CAST(11.0 AS float)
                * b.Nivel_Inventario_Silo
                * CAST(b.Densidad_Ton_M3 AS float)
                / CAST(100.0 AS float)
        END AS TMH_Silo,

        CASE
            WHEN b.Nivel_Inventario_Harnero IS NULL
                THEN NULL

            WHEN b.Y_Harnero > 0
             AND b.Y_Harnero <= 2.268
                THEN
                    (
                        31.6468254 * POWER(b.Y_Harnero, 2)
                        + 63.8 * b.Y_Harnero
                    )
                    * (
                        b.Cantidad_Bins
                        * b.Densidad_Ton_M3
                        / 5.0
                    )

            WHEN b.Y_Harnero > 2.268
             AND b.Y_Harnero <= 2.52
                THEN
                    (
                        25.3173746 * POWER(b.Y_Harnero, 2)
                        + 92.51 * b.Y_Harnero
                        - 32.55714
                    )
                    * (
                        b.Cantidad_Bins
                        * b.Densidad_Ton_M3
                        / 5.0
                    )

            ELSE
                (
                    220.11 * b.Y_Harnero
                    - 193.33314
                )
                * (
                    b.Cantidad_Bins
                    * b.Densidad_Ton_M3
                    / 5.0
                )
        END AS TMH_Harnero,

        CASE
            WHEN b.Nivel_Inventario_Chancado IS NULL
                THEN NULL

            WHEN b.Y_Chancado > 0
             AND b.Y_Chancado <= 2.268
                THEN
                    (
                        31.6468254 * POWER(b.Y_Chancado, 2)
                        + 63.8 * b.Y_Chancado
                    )
                    * (
                        b.Cantidad_Bins
                        * b.Densidad_Ton_M3
                        / 5.0
                    )

            WHEN b.Y_Chancado > 2.268
             AND b.Y_Chancado <= 2.52
                THEN
                    (
                        25.3173746 * POWER(b.Y_Chancado, 2)
                        + 92.51 * b.Y_Chancado
                        - 32.55714
                    )
                    * (
                        b.Cantidad_Bins
                        * b.Densidad_Ton_M3
                        / 5.0
                    )

            ELSE
                (
                    220.11 * b.Y_Chancado
                    - 193.33314
                )
                * (
                    b.Cantidad_Bins
                    * b.Densidad_Ton_M3
                    / 5.0
                )
        END AS TMH_Chancado

    FROM BaseConHumedad AS b
),

/*==============================================================
  11. Inventario total húmedo
==============================================================*/
Totales AS
(
    SELECT
        i.*,

        CASE
            WHEN i.TMH_Silo IS NOT NULL
             AND i.TMH_Harnero IS NOT NULL
             AND i.TMH_Chancado IS NOT NULL
                THEN
                    i.TMH_Silo
                    + i.TMH_Harnero
                    + i.TMH_Chancado
                    + i.Tolva_Compensacion_TMH
            ELSE NULL
        END AS Total_Inventario_Chancado_TMH

    FROM InventariosTMH AS i
),

/*==============================================================
  12. Conversión a toneladas secas
==============================================================*/
TotalesSecos AS
(
    SELECT
        t.*,

        CASE
            WHEN t.Flag_Bloque_Archive_Valido = 1
             AND t.Flag_Humedad_Inventario_Valida = 1
             AND t.Total_Inventario_Chancado_TMH IS NOT NULL
                THEN
                    t.Total_Inventario_Chancado_TMH
                    * (1.0 - t.Humedad_Inventario / 100.0)

            ELSE NULL
        END AS Total_Inventario_Chancado_TMS

    FROM Totales AS t
),

/*==============================================================
  13. Inventario inmediatamente anterior mediante LAG
==============================================================*/
ConLagInventario AS
(
    SELECT
        t.*,

        LAG(t.Fecha)
            OVER (ORDER BY t.Fecha)
            AS Fecha_Inventario_Anterior_Lag,

        LAG(t.Total_Inventario_Chancado_TMS)
            OVER (ORDER BY t.Fecha)
            AS Inventario_Chancado_TMS_Anterior_Lag

    FROM TotalesSecos AS t
),

/*==============================================================
  14. Resolución entre semilla oficial y LAG
==============================================================*/
ConInventarioAnterior AS
(
    SELECT
        l.*,

        CASE
            WHEN s.Inventario_Chancado_TMS IS NOT NULL
                THEN s.Fecha

            WHEN l.Inventario_Chancado_TMS_Anterior_Lag IS NOT NULL
                THEN l.Fecha_Inventario_Anterior_Lag

            ELSE NULL
        END AS Fecha_Inventario_Anterior,

        COALESCE
        (
            TRY_CONVERT(float, s.Inventario_Chancado_TMS),
            l.Inventario_Chancado_TMS_Anterior_Lag
        ) AS Inventario_Chancado_TMS_Anterior,

        CASE
            WHEN s.Inventario_Chancado_TMS IS NOT NULL
                THEN 'SEMILLA_OFICIAL'

            WHEN l.Inventario_Chancado_TMS_Anterior_Lag IS NOT NULL
                THEN 'LAG_VISTA'

            ELSE 'SIN_INVENTARIO_ANTERIOR'
        END AS Fuente_Inventario_Anterior

    FROM ConLagInventario AS l

    LEFT JOIN inventar_SpcHidr.semilla_inventario_chancado AS s
        ON s.Fecha = DATEADD(DAY, -1, l.Fecha)
       AND s.Activo = 1
),

/*==============================================================
  15. Delta diario de inventario
==============================================================*/
Resultado AS
(
    SELECT
        c.*,

        CASE
            WHEN DATEDIFF(
                    DAY,
                    c.Fecha_Inventario_Anterior,
                    c.Fecha
                 ) = 1
             AND c.Total_Inventario_Chancado_TMS IS NOT NULL
             AND c.Inventario_Chancado_TMS_Anterior IS NOT NULL
                THEN 1
            ELSE 0
        END AS Flag_Continuidad_Diaria,

        CASE
            WHEN DATEDIFF(
                    DAY,
                    c.Fecha_Inventario_Anterior,
                    c.Fecha
                 ) = 1
             AND c.Total_Inventario_Chancado_TMS IS NOT NULL
             AND c.Inventario_Chancado_TMS_Anterior IS NOT NULL
                THEN
                    c.Total_Inventario_Chancado_TMS
                    - c.Inventario_Chancado_TMS_Anterior
            ELSE NULL
        END AS Delta_Inventario_Chancado_TMS

    FROM ConInventarioAnterior AS c
)

/*==============================================================
  16. Salida final
==============================================================*/
SELECT
    Fecha,

    Fecha_Lectura_D1,
    Primera_Lectura_Hora_8,
    Ultima_Lectura_Hora_8,
    Cantidad_Registros_Hora_8,

    Primera_Fila_Bloque,
    Ultima_Fila_Bloque,
    Cantidad_Filas_Bloque,
    Flag_Bloque_Archive_Valido,

    Nivel_Inventario_Silo,
    Sensores_Silo_Validos,

    Nivel_Inventario_Harnero,
    Sensores_Harnero_Validos,

    Nivel_Inventario_Chancado,
    Sensores_Chancado_Validos,

    TMH_Silo,
    TMH_Harnero,
    TMH_Chancado,

    Tolva_Compensacion_TMH,
    Total_Inventario_Chancado_TMH,

    Humedad_Inventario,
    Regla_Humedad_Inventario,
    Flag_Humedad_Inventario_Valida,

    Total_Inventario_Chancado_TMS,

    Fecha_Inventario_Anterior,
    Inventario_Chancado_TMS_Anterior,
    Fuente_Inventario_Anterior,

    Flag_Continuidad_Diaria,
    Delta_Inventario_Chancado_TMS,

    Fecha_Humedad_TM1,
    Torre_Humedad_TM1,
    Turno_Humedad_TM1,
    Fuente_Humedad_TM1,

    Fecha_Humedad_TM2,
    Torre_Humedad_TM2,
    Turno_Humedad_TM2,
    Fuente_Humedad_TM2,

    CASE
        WHEN Cantidad_Registros_Hora_8 = 1
         AND Flag_Bloque_Archive_Valido = 1
         AND Sensores_Silo_Validos = 2
         AND Sensores_Harnero_Validos = 5
         AND Sensores_Chancado_Validos = 5
         AND Flag_Humedad_Inventario_Valida = 1
         AND Flag_Continuidad_Diaria = 1
            THEN 1

        ELSE 0
    END AS Flag_Inventario_Valido

FROM Resultado;