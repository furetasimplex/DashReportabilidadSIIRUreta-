# Diff semántico exacto de la promoción SRR en DEV

## `sp_factor_ajuste_camiones_test`

Antes, el CTE diario leía `reporte_turno_cache_emision_test` y calculaba cada
turno mediante:

```sql
COALESCE(TRY_CONVERT(float, r.Apilado_TMS_Real), 0.0)
* COALESCE(TRY_CONVERT(float, r.SRR), 0.0)
/ 100.0
```

Después, conserva los mismos alias y tipos `float`, pero suma directamente:

```sql
COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)
```

desde:

```sql
[inventar_SpcHidr].[v_srr_tms_origen_turno_emision_test] AS s
```

El rango continúa siendo inclusivo:

```sql
s.Fecha BETWEEN @FechaInicio AND @FechaFin
```

## `sp_mantiene_factor_ajuste_camiones_v2_test`

Antes, `#SRRTurnos` reconstruía A/B con la misma multiplicación del porcentaje
del cache.

Después, `#SRRTurnos` conserva nombres y tipos, y suma por turno:

```sql
SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'A'
         THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)
         ELSE 0.0 END) AS SRR_TMS_Turno_A,
SUM(CASE WHEN UPPER(LTRIM(RTRIM(s.Turno))) = 'B'
         THEN COALESCE(TRY_CONVERT(float, s.Ton_SRR_Usado_Actual), 0.0)
         ELSE 0.0 END) AS SRR_TMS_Turno_B
```

El rango continúa siendo inclusivo:

```sql
s.Fecha BETWEEN @FechaInicioProceso AND @FechaFin
```

No se modificó ninguna fórmula, flag, estado ni bloque restante.
