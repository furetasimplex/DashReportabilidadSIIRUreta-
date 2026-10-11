CREATE OR ALTER PROCEDURE
    [inventar_SpcHidr].[sp_gestion_representatividad_fy]
    @anio_fiscal int,
    @tipo varchar(10) = 'QUIMICO',
    @alcance varchar(10) = 'COMBINADO',
    @objetivo decimal(10,6) = 0.85,
    @fecha_corte date = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SET @tipo = UPPER(LTRIM(RTRIM(@tipo)));
    SET @alcance = UPPER(LTRIM(RTRIM(@alcance)));

    IF @tipo NOT IN ('QUIMICO', 'FISICO')
        THROW 50001, 'El parámetro @tipo debe ser QUIMICO o FISICO.', 1;

    IF @alcance NOT IN ('TM1', 'TM2', 'COMBINADO')
        THROW 50002, 'El parámetro @alcance debe ser TM1, TM2 o COMBINADO.', 1;

    DECLARE @fecha_inicio date = DATEFROMPARTS(@anio_fiscal - 1, 7, 1);
    DECLARE @fecha_fin_exclusiva date = DATEFROMPARTS(@anio_fiscal, 7, 1);

    IF @fecha_corte IS NULL
    BEGIN
        SELECT @fecha_corte = MAX(Fecha)
        FROM inventar_SpcHidr.v_bd_ton_reportabilidad
        WHERE Fecha >= @fecha_inicio
          AND Fecha < @fecha_fin_exclusiva;
    END;

    IF @fecha_corte >= @fecha_fin_exclusiva
        SET @fecha_corte = DATEADD(DAY, -1, @fecha_fin_exclusiva);

    IF @fecha_corte < @fecha_inicio
        SET @fecha_corte = NULL;

    DECLARE @fecha_mes_corte date =
        CASE
            WHEN @fecha_corte IS NULL THEN NULL
            ELSE DATEFROMPARTS(YEAR(@fecha_corte), MONTH(@fecha_corte), 1)
        END;

    ;WITH meses AS
    (
        SELECT
            Orden = n + 1,
            Fecha_Mes = DATEADD(MONTH, n, @fecha_inicio)
        FROM
        (
            VALUES
                (0), (1), (2), (3), (4), (5),
                (6), (7), (8), (9), (10), (11)
        ) AS x(n)
        WHERE @fecha_mes_corte IS NOT NULL
          AND DATEADD(MONTH, n, @fecha_inicio) <= @fecha_mes_corte
    ),
    turnos AS
    (
        SELECT
            b.Fecha,
            t.Turno,
            Evaluable_TM1 =
                CASE
                    WHEN b.Fecha >= CONVERT(date, '20260101')
                    THEN COALESCE(CONVERT(int, e.Turno_Evaluable), 0)
                    WHEN t.Turno = 'A' THEN COALESCE(b.Evaluable_TM1_TA, 0)
                    ELSE COALESCE(b.Evaluable_TM1_TB, 0)
                END,
            Evaluable_TM2 =
                CASE
                    WHEN b.Fecha >= CONVERT(date, '20260101')
                    THEN COALESCE(CONVERT(int, e.Turno_Evaluable), 0)
                    WHEN t.Turno = 'A' THEN COALESCE(b.Evaluable_TM2_TA, 0)
                    ELSE COALESCE(b.Evaluable_TM2_TB, 0)
                END,
            Flag_TM1 =
                CASE
                    WHEN @tipo = 'FISICO'
                    THEN CASE WHEN t.Turno = 'A' THEN b.FISICO_TM1_TA ELSE b.FISICO_TM1_TB END
                    ELSE CASE WHEN t.Turno = 'A' THEN b.Muestra_representativa_TM1_TA ELSE b.Muestra_representativa_TM1_TB END
                END,
            Flag_TM2 =
                CASE
                    WHEN @tipo = 'FISICO'
                    THEN CASE WHEN t.Turno = 'A' THEN b.FISICO_TM2_TA ELSE b.FISICO_TM2_TB END
                    ELSE CASE WHEN t.Turno = 'A' THEN b.Muestra_representativa_TM2_TA ELSE b.Muestra_representativa_TM2_TB END
                END
        FROM inventar_SpcHidr.v_bd_ton_reportabilidad AS b
        CROSS JOIN (VALUES ('A'), ('B')) AS t(Turno)
        LEFT JOIN inventar_SpcHidr.v_estado_apilado_turno_representatividad AS e
            ON e.Fecha = b.Fecha
           AND e.Turno = t.Turno
        WHERE @fecha_corte IS NOT NULL
          AND b.Fecha >= @fecha_inicio
          AND b.Fecha <= @fecha_corte
          AND b.Fecha < @fecha_fin_exclusiva
    ),
    indicadores AS
    (
        -- La unidad oficial es Fecha + Turno + Torre. COMBINADO conserva
        -- ambas oportunidades mediante UNION ALL; no consolida por OR.
        SELECT
            Fecha,
            Turno,
            Torre = CAST('TM1' AS varchar(3)),
            Indicador =
                CASE
                    WHEN Evaluable_TM1 <> 1 THEN NULL
                    ELSE COALESCE(Flag_TM1, 0)
                END
        FROM turnos
        WHERE @alcance IN ('TM1', 'COMBINADO')

        UNION ALL

        SELECT
            Fecha,
            Turno,
            Torre = CAST('TM2' AS varchar(3)),
            Indicador =
                CASE
                    WHEN Evaluable_TM2 <> 1 THEN NULL
                    ELSE COALESCE(Flag_TM2, 0)
                END
        FROM turnos
        WHERE @alcance IN ('TM2', 'COMBINADO')
    ),
    mensual AS
    (
        SELECT
            Fecha_Mes = DATEFROMPARTS(YEAR(Fecha), MONTH(Fecha), 1),
            Turnos_Evaluables = COUNT(Indicador),
            Turnos_Representativos = SUM(Indicador)
        FROM indicadores
        GROUP BY DATEFROMPARTS(YEAR(Fecha), MONTH(Fecha), 1)
    ),
    salida_mensual AS
    (
        SELECT
            m.Orden,
            m.Fecha_Mes,
            Etiqueta =
                LOWER(LEFT(CHOOSE(
                    MONTH(m.Fecha_Mes),
                    'ene', 'feb', 'mar', 'abr', 'may', 'jun',
                    'jul', 'ago', 'sep', 'oct', 'nov', 'dic'
                ), 3))
                + '-'
                + RIGHT(CAST(YEAR(m.Fecha_Mes) AS varchar(4)), 2),
            Tipo_Registro = 'MES',
            Turnos_Evaluables = mn.Turnos_Evaluables,
            Turnos_Representativos = mn.Turnos_Representativos,
            Representatividad =
                CAST(mn.Turnos_Representativos AS decimal(18,10))
                / NULLIF(mn.Turnos_Evaluables, 0),
            Objetivo = @objetivo
        FROM meses AS m
        LEFT JOIN mensual AS mn
            ON mn.Fecha_Mes = m.Fecha_Mes
    ),
    ytd AS
    (
        SELECT
            Turnos_Evaluables = COUNT(Indicador),
            Turnos_Representativos = SUM(Indicador)
        FROM indicadores
    )
    SELECT
        Orden,
        Fecha_Mes,
        Etiqueta,
        Tipo_Registro,
        Turnos_Evaluables,
        Turnos_Representativos,
        Representatividad,
        Objetivo,
        Tipo = @tipo,
        Alcance = @alcance,
        Año_Fiscal = @anio_fiscal,
        Fecha_Corte = @fecha_corte
    FROM salida_mensual

    UNION ALL

    SELECT
        Orden = 13,
        Fecha_Mes = NULL,
        Etiqueta = 'YTD',
        Tipo_Registro = 'YTD',
        Turnos_Evaluables,
        Turnos_Representativos,
        Representatividad =
            CAST(Turnos_Representativos AS decimal(18,10))
            / NULLIF(Turnos_Evaluables, 0),
        Objetivo = @objetivo,
        Tipo = @tipo,
        Alcance = @alcance,
        Año_Fiscal = @anio_fiscal,
        Fecha_Corte = @fecha_corte
    FROM ytd
    ORDER BY Orden;
END;
