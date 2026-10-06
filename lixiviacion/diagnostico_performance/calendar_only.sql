WITH fechas AS (SELECT CAST(:desde AS date) AS fecha UNION ALL
SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(:hasta AS date))
SELECT COUNT(*) AS dias FROM fechas OPTION (MAXRECURSION 32767)