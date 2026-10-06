# Comparación de planes reales

XML íntegro en plans/. Contadores acumulados; no sumar tiempos inclusivos de padres e hijos.

## Referencia baseline runtime (auditoría previa)

PlanHash 0x75F647FB677DE496; DOP1; costo9,29993. Nested Loops2 produce6.120 filas y Filter1 devuelve102. Scans históricos OX ejecutan3.264 veces y SULF2.856 veces; Table Spool15 tiene102 rebinds,0 rewinds. A102 días:22.166.901 lecturas,42 Nested Loops,6 Hash Match,21 Sort,19 Clustered Index Scan. Grant11.600KB,usado1.936KB. Sin spills; advertencias optimizer TimeOut/PlanAffectingConvert. XML en ../diagnostico_performance/plans/. La referencia proyecta12 campos; candidatos24.

## candidate_generic_p1_1_102d_actualplan.sqlplan

```json
{
  "attributes": {
    "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n), parcela AS (\n    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela\n    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad\n    WHERE p.id_pad=@P3 AND p.id_parcela=@P4\n      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))\n), campanas AS (\n    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,\n           MIN(c.fecha_ini_carguio) AS fecha_ini_campana\n    FROM inventar_SpcHidr.campana_parcela_control c\n    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id\n    WHERE c.fecha_ini_carguio IS NOT NULL\n    GROUP BY c.pad_id,c.campana_id,c.parcela_id\n), ventanas AS (\n    SELECT c.*,LEAD(c.fecha_ini_campana) OVER\n        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente\n    FROM campanas c\n), campanas_rango AS (\n    -- LEAD ya calculado sobre todas las campa\u00f1as de la parcela, antes del filtro de rango.\n    SELECT * FROM ventanas\n    WHERE fecha_ini_campana<=CAST(@P5 AS date)\n      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(@P6 AS date))\n), riego_fuente AS (\n    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n        UNION ALL\n        SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), drenaje_fuente AS (\n    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_oxido_operacional s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n        UNION ALL\n        SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), riego_extremos AS (\n    -- Ventana completa, nunca recortada a las fechas visibles.\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,\n           MAX(r.fecha) AS fecha_ultimo_riego_real\n    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id\n      AND r.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)\n      AND r.valor>1\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), drenaje_extremos AS (\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,\n           MAX(d.fecha) AS fecha_ultimo_drenaje_real\n    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id\n      AND d.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)\n      AND d.valor>0\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), contexto AS (\n    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real\n    FROM campanas_rango c\n    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id\n    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id\n), riego_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo\n    FROM riego_fuente WHERE fecha BETWEEN CAST(@P7 AS date) AND CAST(",
    "StatementId": "1",
    "StatementCompId": "1",
    "StatementType": "SELECT",
    "RetrievedFromCache": "true",
    "StatementSubTreeCost": "11.8328",
    "StatementEstRows": "7.41779",
    "SecurityPolicyApplied": "false",
    "StatementOptmLevel": "FULL",
    "QueryHash": "0xA93DAD52C30711F9",
    "QueryPlanHash": "0x8135D440A8B32049",
    "StatementOptmEarlyAbortReason": "TimeOut",
    "CardinalityEstimationModelVersion": "140"
  },
  "query_plan": {
    "DegreeOfParallelism": "1",
    "MemoryGrant": "5472",
    "CachedPlanSize": "2232",
    "CompileTime": "216",
    "CompileCPU": "216",
    "CompileMemory": "61592"
  },
  "operator_counts": {
    "Compute Scalar": 44,
    "Nested Loops": 99,
    "Clustered Index Seek": 61,
    "Sort": 16,
    "Index Spool": 7,
    "Concatenation": 11,
    "Constant Scan": 22,
    "Assert": 3,
    "Table Spool": 5,
    "Filter": 44,
    "Stream Aggregate": 25,
    "Window Spool": 7,
    "Segment": 14,
    "Sequence Project": 7,
    "Index Seek": 9,
    "Clustered Index Scan": 16
  },
  "MemoryGrantInfo": [
    "<ns0:MemoryGrantInfo xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" SerialRequiredMemory=\"4992\" SerialDesiredMemory=\"5472\" RequiredMemory=\"4992\" DesiredMemory=\"5472\" RequestedMemory=\"5472\" GrantWaitTime=\"0\" GrantedMemory=\"5472\" MaxUsedMemory=\"40\" MaxQueryMemory=\"2260920\" />"
  ],
  "QueryTimeStats": [
    "<ns0:QueryTimeStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" ElapsedTime=\"1320\" CpuTime=\"1287\" />"
  ],
  "Warnings": [
    "<ns0:Warnings xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:PlanAffectingConvert ConvertIssue=\"Cardinality Estimate\" Expression=\"CONVERT_IMPLICIT(varchar(12),[Expr1797],0)\" /><ns0:MemoryGrantWarning GrantWarningKind=\"Excessive Grant\" RequestedMemory=\"5472\" GrantedMemory=\"5472\" MaxUsedMemory=\"40\" /></ns0:Warnings>"
  ],
  "WaitStats": [
    "<ns0:WaitStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:Wait WaitType=\"MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"1\" WaitCount=\"1185\" /><ns0:Wait WaitType=\"PAGELATCH_SH\" WaitTimeMs=\"40\" WaitCount=\"20705\" /></ns0:WaitStats>"
  ],
  "MissingIndexes": []
}
```

| Nodo | Operador | Est filas/ejec | Filas reales total | Ejecuciones | Real/ejec | Logical reads | Objeto |
|---:|---|---:|---:|---:|---:|---:|---|
| 0 | Compute Scalar | 7.41779 | 0 | 0 | None | 0 |  |
| 1 | Nested Loops | 7.41779 | 102 | 1 | 102.0 | 0 |  |
| 2 | Nested Loops | 2 | 102 | 1 | 102.0 | 0 |  |
| 3 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 4 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 5 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 6 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 7 | Nested Loops | 1 | 1 | 1 | 1.0 | 0 |  |
| 8 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 9 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 39 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 40 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 42 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 44 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 60 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 61 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 63 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 65 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 70 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 71 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 75 | Clustered Index Scan | 656.209 | 345 | 1 | 345.0 | 274 | [flujos_reales_oxido] |
| 80 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 81 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 85 | Clustered Index Scan | 656.209 | 0 | 0 | None | 0 | [flujos_reales_sulfuro] |
| 103 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 104 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 106 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 108 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 113 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 114 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 118 | Clustered Index Scan | 720.022 | 346 | 1 | 346.0 | 1389 | [drena_concentrados_oxido] |
| 123 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 124 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 128 | Clustered Index Scan | 746.103 | 0 | 0 | None | 0 | [drena_concentrados_sulfuro] |
| 137 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 139 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 143 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 27948 | [flujos_reales_oxido] |
| 147 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 149 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 153 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [flujos_reales_sulfuro] |
| 161 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 163 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 167 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 141678 | [drena_concentrados_oxido] |
| 171 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 173 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 177 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [drena_concentrados_sulfuro] |
| 193 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 195 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 209 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 210 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 212 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 214 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 242 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 243 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 245 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 247 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 252 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 253 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 257 | Clustered Index Scan | 656.209 | 35190 | 102 | 345.0 | 27948 | [flujos_reales_oxido] |
| 262 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 263 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 267 | Clustered Index Scan | 656.209 | 0 | 0 | None | 0 | [flujos_reales_sulfuro] |
| 285 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 286 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 288 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 290 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 295 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 296 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 300 | Clustered Index Scan | 720.022 | 35292 | 102 | 346.0 | 141678 | [drena_concentrados_oxido] |
| 305 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 306 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 310 | Clustered Index Scan | 746.103 | 0 | 0 | None | 0 | [drena_concentrados_sulfuro] |
| 312 | Index Seek | 1.29385 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 314 | Clustered Index Seek | 1.24535 | 204 | 1020 | 0.2 | 2040 | [campana_parcela_control] |
| 322 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 324 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 328 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 27948 | [flujos_reales_oxido] |
| 332 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 334 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 338 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [flujos_reales_sulfuro] |
| 346 | Clustered Index Seek | 1 | 204 | 204 | 1.0 | 408 | [pad] |
| 348 | Clustered Index Seek | 1 | 204 | 204 | 1.0 | 408 | [parcela] |
| 352 | Clustered Index Scan | 1 | 204 | 204 | 1.0 | 283356 | [drena_concentrados_oxido] |
| 356 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 358 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 362 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [drena_concentrados_sulfuro] |
| 370 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 372 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 386 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 387 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 389 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 391 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 404 | Index Seek | 1.29385 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 406 | Clustered Index Seek | 1 | 204 | 1020 | 0.2 | 2040 | [campana_parcela_control] |
## candidate_generic_p2_7_102d_actualplan.sqlplan

```json
{
  "attributes": {
    "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n), parcela AS (\n    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela\n    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad\n    WHERE p.id_pad=@P3 AND p.id_parcela=@P4\n      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))\n), campanas AS (\n    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,\n           MIN(c.fecha_ini_carguio) AS fecha_ini_campana\n    FROM inventar_SpcHidr.campana_parcela_control c\n    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id\n    WHERE c.fecha_ini_carguio IS NOT NULL\n    GROUP BY c.pad_id,c.campana_id,c.parcela_id\n), ventanas AS (\n    SELECT c.*,LEAD(c.fecha_ini_campana) OVER\n        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente\n    FROM campanas c\n), campanas_rango AS (\n    -- LEAD ya calculado sobre todas las campa\u00f1as de la parcela, antes del filtro de rango.\n    SELECT * FROM ventanas\n    WHERE fecha_ini_campana<=CAST(@P5 AS date)\n      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(@P6 AS date))\n), riego_fuente AS (\n    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n        UNION ALL\n        SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), drenaje_fuente AS (\n    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_oxido_operacional s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n        UNION ALL\n        SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), riego_extremos AS (\n    -- Ventana completa, nunca recortada a las fechas visibles.\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,\n           MAX(r.fecha) AS fecha_ultimo_riego_real\n    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id\n      AND r.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)\n      AND r.valor>1\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), drenaje_extremos AS (\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,\n           MAX(d.fecha) AS fecha_ultimo_drenaje_real\n    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id\n      AND d.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)\n      AND d.valor>0\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), contexto AS (\n    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real\n    FROM campanas_rango c\n    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id\n    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id\n), riego_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo\n    FROM riego_fuente WHERE fecha BETWEEN CAST(@P7 AS date) AND CAST(",
    "StatementId": "1",
    "StatementCompId": "1",
    "StatementType": "SELECT",
    "RetrievedFromCache": "true",
    "StatementSubTreeCost": "11.8328",
    "StatementEstRows": "7.41779",
    "SecurityPolicyApplied": "false",
    "StatementOptmLevel": "FULL",
    "QueryHash": "0xA93DAD52C30711F9",
    "QueryPlanHash": "0x8135D440A8B32049",
    "StatementOptmEarlyAbortReason": "TimeOut",
    "CardinalityEstimationModelVersion": "140"
  },
  "query_plan": {
    "DegreeOfParallelism": "1",
    "MemoryGrant": "5472",
    "CachedPlanSize": "2232",
    "CompileTime": "216",
    "CompileCPU": "216",
    "CompileMemory": "61592"
  },
  "operator_counts": {
    "Compute Scalar": 44,
    "Nested Loops": 99,
    "Clustered Index Seek": 61,
    "Sort": 16,
    "Index Spool": 7,
    "Concatenation": 11,
    "Constant Scan": 22,
    "Assert": 3,
    "Table Spool": 5,
    "Filter": 44,
    "Stream Aggregate": 25,
    "Window Spool": 7,
    "Segment": 14,
    "Sequence Project": 7,
    "Index Seek": 9,
    "Clustered Index Scan": 16
  },
  "MemoryGrantInfo": [
    "<ns0:MemoryGrantInfo xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" SerialRequiredMemory=\"4992\" SerialDesiredMemory=\"5472\" RequiredMemory=\"4992\" DesiredMemory=\"5472\" RequestedMemory=\"5472\" GrantWaitTime=\"0\" GrantedMemory=\"5472\" MaxUsedMemory=\"40\" MaxQueryMemory=\"2260920\" />"
  ],
  "QueryTimeStats": [
    "<ns0:QueryTimeStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" ElapsedTime=\"1797\" CpuTime=\"1759\" />"
  ],
  "Warnings": [
    "<ns0:Warnings xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:PlanAffectingConvert ConvertIssue=\"Cardinality Estimate\" Expression=\"CONVERT_IMPLICIT(varchar(12),[Expr1797],0)\" /><ns0:MemoryGrantWarning GrantWarningKind=\"Excessive Grant\" RequestedMemory=\"5472\" GrantedMemory=\"5472\" MaxUsedMemory=\"40\" /></ns0:Warnings>"
  ],
  "WaitStats": [
    "<ns0:WaitStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:Wait WaitType=\"SOS_SCHEDULER_YIELD\" WaitTimeMs=\"1\" WaitCount=\"325\" /><ns0:Wait WaitType=\"MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"1\" WaitCount=\"1185\" /><ns0:Wait WaitType=\"PAGELATCH_SH\" WaitTimeMs=\"47\" WaitCount=\"20705\" /></ns0:WaitStats>"
  ],
  "MissingIndexes": []
}
```

| Nodo | Operador | Est filas/ejec | Filas reales total | Ejecuciones | Real/ejec | Logical reads | Objeto |
|---:|---|---:|---:|---:|---:|---:|---|
| 0 | Compute Scalar | 7.41779 | 0 | 0 | None | 0 |  |
| 1 | Nested Loops | 7.41779 | 102 | 1 | 102.0 | 0 |  |
| 2 | Nested Loops | 2 | 102 | 1 | 102.0 | 0 |  |
| 3 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 4 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 5 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 6 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 7 | Nested Loops | 1 | 1 | 1 | 1.0 | 0 |  |
| 8 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 9 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 39 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 40 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 42 | Index Seek | 4.31283 | 25 | 1 | 25.0 | 2 | [campana_parcela_control] |
| 44 | Clustered Index Seek | 1 | 25 | 25 | 1.0 | 50 | [campana_parcela_control] |
| 60 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 61 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 63 | Index Seek | 4.31283 | 25 | 1 | 25.0 | 2 | [campana_parcela_control] |
| 65 | Clustered Index Seek | 1 | 25 | 25 | 1.0 | 50 | [campana_parcela_control] |
| 70 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 71 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 75 | Clustered Index Scan | 656.209 | 0 | 0 | None | 0 | [flujos_reales_oxido] |
| 80 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 81 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 85 | Clustered Index Scan | 656.209 | 417 | 1 | 417.0 | 240 | [flujos_reales_sulfuro] |
| 103 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 104 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 106 | Index Seek | 4.31283 | 25 | 1 | 25.0 | 2 | [campana_parcela_control] |
| 108 | Clustered Index Seek | 1 | 25 | 25 | 1.0 | 50 | [campana_parcela_control] |
| 113 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 114 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 118 | Clustered Index Scan | 720.022 | 0 | 0 | None | 0 | [drena_concentrados_oxido] |
| 123 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 124 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 128 | Clustered Index Scan | 746.103 | 418 | 1 | 418.0 | 1440 | [drena_concentrados_sulfuro] |
| 137 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 139 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 143 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [flujos_reales_oxido] |
| 147 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 149 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 153 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 24480 | [flujos_reales_sulfuro] |
| 161 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 163 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 167 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [drena_concentrados_oxido] |
| 171 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 173 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 177 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 146880 | [drena_concentrados_sulfuro] |
| 193 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 195 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 209 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 210 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 212 | Index Seek | 4.31283 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 214 | Clustered Index Seek | 1 | 2550 | 2550 | 1.0 | 5100 | [campana_parcela_control] |
| 242 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 243 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 245 | Index Seek | 4.31283 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 247 | Clustered Index Seek | 1 | 2550 | 2550 | 1.0 | 5100 | [campana_parcela_control] |
| 252 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 253 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 257 | Clustered Index Scan | 656.209 | 0 | 0 | None | 0 | [flujos_reales_oxido] |
| 262 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 263 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 267 | Clustered Index Scan | 656.209 | 42534 | 102 | 417.0 | 24480 | [flujos_reales_sulfuro] |
| 285 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 286 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 288 | Index Seek | 4.31283 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 290 | Clustered Index Seek | 1 | 2550 | 2550 | 1.0 | 5100 | [campana_parcela_control] |
| 295 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 296 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 300 | Clustered Index Scan | 720.022 | 0 | 0 | None | 0 | [drena_concentrados_oxido] |
| 305 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 306 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 310 | Clustered Index Scan | 746.103 | 42636 | 102 | 418.0 | 146880 | [drena_concentrados_sulfuro] |
| 312 | Index Seek | 1.29385 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 314 | Clustered Index Seek | 1.24535 | 510 | 2550 | 0.2 | 5100 | [campana_parcela_control] |
| 322 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 324 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 328 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [flujos_reales_oxido] |
| 332 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 334 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 338 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 24480 | [flujos_reales_sulfuro] |
| 346 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [pad] |
| 348 | Clustered Index Seek | 1 | 0 | 0 | None | 0 | [parcela] |
| 352 | Clustered Index Scan | 1 | 0 | 0 | None | 0 | [drena_concentrados_oxido] |
| 356 | Clustered Index Seek | 1 | 510 | 510 | 1.0 | 1020 | [pad] |
| 358 | Clustered Index Seek | 1 | 510 | 510 | 1.0 | 1020 | [parcela] |
| 362 | Clustered Index Scan | 1 | 510 | 510 | 1.0 | 734400 | [drena_concentrados_sulfuro] |
| 370 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 372 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 386 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 387 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 389 | Index Seek | 4.31283 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 391 | Clustered Index Seek | 1 | 2550 | 2550 | 1.0 | 5100 | [campana_parcela_control] |
| 404 | Index Seek | 1.29385 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 406 | Clustered Index Seek | 1 | 510 | 2550 | 0.2 | 5100 | [campana_parcela_control] |
## candidate_ox_p1_1_102d_actualplan.sqlplan

```json
{
  "attributes": {
    "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n), parcela AS (\n    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela\n    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad\n    WHERE p.id_pad=@P3 AND p.id_parcela=@P4\n      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))\n), campanas AS (\n    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,\n           MIN(c.fecha_ini_carguio) AS fecha_ini_campana\n    FROM inventar_SpcHidr.campana_parcela_control c\n    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id\n    WHERE c.fecha_ini_carguio IS NOT NULL\n    GROUP BY c.pad_id,c.campana_id,c.parcela_id\n), ventanas AS (\n    SELECT c.*,LEAD(c.fecha_ini_campana) OVER\n        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente\n    FROM campanas c\n), campanas_rango AS (\n    -- LEAD ya calculado sobre todas las campa\u00f1as de la parcela, antes del filtro de rango.\n    SELECT * FROM ventanas\n    WHERE fecha_ini_campana<=CAST(@P5 AS date)\n      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(@P6 AS date))\n), riego_fuente AS (\n    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_oxido_unpivot s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n), drenaje_fuente AS (\n    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_oxido_operacional s\n          ON p.pad_id=1 AND s.parcela_numero=p.numero_parcela\n), riego_extremos AS (\n    -- Ventana completa, nunca recortada a las fechas visibles.\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,\n           MAX(r.fecha) AS fecha_ultimo_riego_real\n    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id\n      AND r.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)\n      AND r.valor>1\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), drenaje_extremos AS (\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,\n           MAX(d.fecha) AS fecha_ultimo_drenaje_real\n    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id\n      AND d.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)\n      AND d.valor>0\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), contexto AS (\n    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real\n    FROM campanas_rango c\n    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id\n    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id\n), riego_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo\n    FROM riego_fuente WHERE fecha BETWEEN CAST(@P7 AS date) AND CAST(@P8 AS date)\n    GROUP BY pad_id,parcela_id,fecha\n), drenaje_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_drenaje,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>0 THEN 1 ELSE 0 END) END AS drenaje_activo\n    FROM drenaje_fuente WHERE fecha BETWEEN CAST(@P9 AS date) AND CAST(@P10 AS date)\n    GROUP BY pad_id,parcela_id,fecha\n), dias AS (\n    SELECT f.fecha,p.*,c.campana_id,c.numero_campana,\n        c.fecha_primer_riego_real,c.fecha_ultimo_riego_real,c.fecha",
    "StatementId": "1",
    "StatementCompId": "1",
    "StatementType": "SELECT",
    "RetrievedFromCache": "true",
    "StatementSubTreeCost": "6.049",
    "StatementEstRows": "7.41779",
    "SecurityPolicyApplied": "false",
    "StatementOptmLevel": "FULL",
    "QueryHash": "0x4CBFA087EB9A4BBC",
    "QueryPlanHash": "0x7F0C920F4F1A8FB4",
    "StatementOptmEarlyAbortReason": "TimeOut",
    "CardinalityEstimationModelVersion": "140"
  },
  "query_plan": {
    "DegreeOfParallelism": "1",
    "MemoryGrant": "6016",
    "CachedPlanSize": "1568",
    "CompileTime": "141",
    "CompileCPU": "141",
    "CompileMemory": "41664"
  },
  "operator_counts": {
    "Compute Scalar": 40,
    "Nested Loops": 75,
    "Clustered Index Seek": 45,
    "Sort": 17,
    "Index Spool": 7,
    "Concatenation": 3,
    "Constant Scan": 14,
    "Assert": 3,
    "Table Spool": 5,
    "Filter": 20,
    "Stream Aggregate": 25,
    "Window Spool": 7,
    "Segment": 14,
    "Sequence Project": 7,
    "Index Seek": 9,
    "Clustered Index Scan": 8
  },
  "MemoryGrantInfo": [
    "<ns0:MemoryGrantInfo xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" SerialRequiredMemory=\"5504\" SerialDesiredMemory=\"6016\" RequiredMemory=\"5504\" DesiredMemory=\"6016\" RequestedMemory=\"6016\" GrantWaitTime=\"0\" GrantedMemory=\"6016\" MaxUsedMemory=\"40\" MaxQueryMemory=\"2260912\" />"
  ],
  "QueryTimeStats": [
    "<ns0:QueryTimeStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" ElapsedTime=\"1401\" CpuTime=\"1365\" />"
  ],
  "Warnings": [
    "<ns0:Warnings xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:PlanAffectingConvert ConvertIssue=\"Cardinality Estimate\" Expression=\"CONVERT_IMPLICIT(varchar(12),[Expr1461],0)\" /><ns0:MemoryGrantWarning GrantWarningKind=\"Excessive Grant\" RequestedMemory=\"6016\" GrantedMemory=\"6016\" MaxUsedMemory=\"40\" /></ns0:Warnings>"
  ],
  "WaitStats": [
    "<ns0:WaitStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:Wait WaitType=\"MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"1\" WaitCount=\"1143\" /><ns0:Wait WaitType=\"RESERVED_MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"1\" WaitCount=\"1850\" /><ns0:Wait WaitType=\"PAGELATCH_SH\" WaitTimeMs=\"43\" WaitCount=\"20705\" /></ns0:WaitStats>"
  ],
  "MissingIndexes": []
}
```

| Nodo | Operador | Est filas/ejec | Filas reales total | Ejecuciones | Real/ejec | Logical reads | Objeto |
|---:|---|---:|---:|---:|---:|---:|---|
| 0 | Compute Scalar | 7.41779 | 0 | 0 | None | 0 |  |
| 1 | Nested Loops | 7.41779 | 102 | 1 | 102.0 | 0 |  |
| 2 | Nested Loops | 2 | 102 | 1 | 102.0 | 0 |  |
| 3 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 4 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 5 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 6 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 7 | Nested Loops | 1 | 1 | 1 | 1.0 | 0 |  |
| 8 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 9 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 39 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 40 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 42 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 44 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 50 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 53 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 66 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 67 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 69 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 71 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 73 | Clustered Index Scan | 3774 | 3774 | 1 | 3774.0 | 274 | [flujos_reales_oxido] |
| 81 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 85 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 98 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 99 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 101 | Index Seek | 4.31283 | 10 | 1 | 10.0 | 2 | [campana_parcela_control] |
| 103 | Clustered Index Seek | 1 | 10 | 10 | 1.0 | 20 | [campana_parcela_control] |
| 105 | Clustered Index Scan | 4141 | 4141 | 1 | 4141.0 | 1389 | [drena_concentrados_oxido] |
| 112 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 114 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 118 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 27948 | [flujos_reales_oxido] |
| 124 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 126 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 130 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 141678 | [drena_concentrados_oxido] |
| 146 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 148 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 162 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 163 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 165 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 167 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 185 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 188 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 201 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 202 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 204 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 206 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 208 | Clustered Index Scan | 3774 | 384948 | 102 | 3774.0 | 27948 | [flujos_reales_oxido] |
| 216 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 219 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 232 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 233 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 235 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 237 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 239 | Clustered Index Scan | 4141 | 422382 | 102 | 4141.0 | 141678 | [drena_concentrados_oxido] |
| 241 | Index Seek | 1.29385 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 243 | Clustered Index Seek | 1.40811 | 204 | 1020 | 0.2 | 2040 | [campana_parcela_control] |
| 249 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 251 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 255 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 27948 | [flujos_reales_oxido] |
| 261 | Clustered Index Seek | 1 | 204 | 204 | 1.0 | 408 | [pad] |
| 263 | Clustered Index Seek | 1 | 204 | 204 | 1.0 | 408 | [parcela] |
| 267 | Clustered Index Scan | 1 | 204 | 204 | 1.0 | 283356 | [drena_concentrados_oxido] |
| 275 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 277 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 291 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 292 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 294 | Index Seek | 4.31283 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 296 | Clustered Index Seek | 1 | 1020 | 1020 | 1.0 | 2040 | [campana_parcela_control] |
| 309 | Index Seek | 1.29385 | 1020 | 102 | 10.0 | 204 | [campana_parcela_control] |
| 311 | Clustered Index Seek | 1 | 204 | 1020 | 0.2 | 2040 | [campana_parcela_control] |
## candidate_sulf_p2_7_102d_actualplan.sqlplan

```json
{
  "attributes": {
    "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n), parcela AS (\n    SELECT p.id_pad AS pad_id,pa.nombre AS nombre_pad,p.id_parcela AS parcela_id,p.numero AS numero_parcela\n    FROM inventar_SpcHidr.parcela p INNER JOIN inventar_SpcHidr.pad pa ON pa.id_pad=p.id_pad\n    WHERE p.id_pad=@P3 AND p.id_parcela=@P4\n      AND ((p.id_pad=1 AND p.numero BETWEEN 1 AND 32) OR (p.id_pad=2 AND p.numero BETWEEN 1 AND 28))\n), campanas AS (\n    SELECT c.pad_id,c.campana_id,c.parcela_id,MAX(c.numero_campana) AS numero_campana,\n           MIN(c.fecha_ini_carguio) AS fecha_ini_campana\n    FROM inventar_SpcHidr.campana_parcela_control c\n    INNER JOIN parcela p ON p.pad_id=c.pad_id AND p.parcela_id=c.parcela_id\n    WHERE c.fecha_ini_carguio IS NOT NULL\n    GROUP BY c.pad_id,c.campana_id,c.parcela_id\n), ventanas AS (\n    SELECT c.*,LEAD(c.fecha_ini_campana) OVER\n        (PARTITION BY c.pad_id,c.parcela_id ORDER BY c.fecha_ini_campana,c.campana_id) AS fecha_ini_campana_siguiente\n    FROM campanas c\n), campanas_rango AS (\n    -- LEAD ya calculado sobre todas las campa\u00f1as de la parcela, antes del filtro de rango.\n    SELECT * FROM ventanas\n    WHERE fecha_ini_campana<=CAST(@P5 AS date)\n      AND (fecha_ini_campana_siguiente IS NULL OR fecha_ini_campana_siguiente>CAST(@P6 AS date))\n), riego_fuente AS (\n    SELECT p.pad_id,p.parcela_id,CAST(s.fecha_registro AS date) AS fecha,s.caudal AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_flujos_sulfuro_unpivot s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), drenaje_fuente AS (\n    SELECT p.pad_id,p.parcela_id,s.fecha_operacional AS fecha,s.cu_pp AS valor\n        FROM parcela p INNER JOIN inventar_SpcHidr.v_drena_sulfuro_operacional s\n          ON p.pad_id=2 AND s.parcela_numero=p.numero_parcela\n), riego_extremos AS (\n    -- Ventana completa, nunca recortada a las fechas visibles.\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(r.fecha) AS fecha_primer_riego_real,\n           MAX(r.fecha) AS fecha_ultimo_riego_real\n    FROM campanas_rango c INNER JOIN riego_fuente r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id\n      AND r.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR r.fecha<c.fecha_ini_campana_siguiente)\n      AND r.valor>1\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), drenaje_extremos AS (\n    SELECT c.pad_id,c.parcela_id,c.campana_id,MIN(d.fecha) AS fecha_primer_drenaje_real,\n           MAX(d.fecha) AS fecha_ultimo_drenaje_real\n    FROM campanas_rango c INNER JOIN drenaje_fuente d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id\n      AND d.fecha>=c.fecha_ini_campana\n      AND (c.fecha_ini_campana_siguiente IS NULL OR d.fecha<c.fecha_ini_campana_siguiente)\n      AND d.valor>0\n    GROUP BY c.pad_id,c.parcela_id,c.campana_id\n), contexto AS (\n    SELECT c.*,r.fecha_primer_riego_real,r.fecha_ultimo_riego_real,d.fecha_primer_drenaje_real,d.fecha_ultimo_drenaje_real\n    FROM campanas_rango c\n    LEFT JOIN riego_extremos r ON r.pad_id=c.pad_id AND r.parcela_id=c.parcela_id AND r.campana_id=c.campana_id\n    LEFT JOIN drenaje_extremos d ON d.pad_id=c.pad_id AND d.parcela_id=c.parcela_id AND d.campana_id=c.campana_id\n), riego_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_riego,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>1 THEN 1 ELSE 0 END) END AS riego_activo\n    FROM riego_fuente WHERE fecha BETWEEN CAST(@P7 AS date) AND CAST(@P8 AS date)\n    GROUP BY pad_id,parcela_id,fecha\n), drenaje_dia AS (\n    SELECT pad_id,parcela_id,fecha,1 AS tiene_dato_drenaje,\n        CASE WHEN COUNT(valor)=0 THEN NULL ELSE MAX(CASE WHEN valor>0 THEN 1 ELSE 0 END) END AS drenaje_activo\n    FROM drenaje_fuente WHERE fecha BETWEEN CAST(@P9 AS date) AND CAST(@P10 AS date)\n    GROUP BY pad_id,parcela_id,fecha\n), dias AS (\n    SELECT f.fecha,p.*,c.campana_id,c.numero_campana,\n        c.fecha_primer_riego_real,c.fecha_ultimo_riego_real,c.f",
    "StatementId": "1",
    "StatementCompId": "1",
    "StatementType": "SELECT",
    "RetrievedFromCache": "true",
    "StatementSubTreeCost": "6.57943",
    "StatementEstRows": "77.1473",
    "SecurityPolicyApplied": "false",
    "StatementOptmLevel": "FULL",
    "QueryHash": "0x8B7649F80570F07F",
    "QueryPlanHash": "0xA793AB706EE22B9C",
    "StatementOptmEarlyAbortReason": "TimeOut",
    "CardinalityEstimationModelVersion": "140"
  },
  "query_plan": {
    "DegreeOfParallelism": "1",
    "MemoryGrant": "12480",
    "CachedPlanSize": "1672",
    "CompileTime": "160",
    "CompileCPU": "160",
    "CompileMemory": "41384"
  },
  "operator_counts": {
    "Compute Scalar": 40,
    "Nested Loops": 68,
    "Clustered Index Seek": 38,
    "Sort": 18,
    "Index Spool": 7,
    "Concatenation": 3,
    "Constant Scan": 14,
    "Assert": 3,
    "Table Spool": 6,
    "Filter": 20,
    "Stream Aggregate": 25,
    "Window Spool": 7,
    "Segment": 14,
    "Sequence Project": 7,
    "Clustered Index Scan": 9,
    "Hash Match": 6,
    "Index Seek": 8,
    "Index Scan": 6
  },
  "MemoryGrantInfo": [
    "<ns0:MemoryGrantInfo xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" SerialRequiredMemory=\"11904\" SerialDesiredMemory=\"12480\" RequiredMemory=\"11904\" DesiredMemory=\"12480\" RequestedMemory=\"12480\" GrantWaitTime=\"0\" GrantedMemory=\"12480\" MaxUsedMemory=\"344\" MaxQueryMemory=\"2260920\" />"
  ],
  "QueryTimeStats": [
    "<ns0:QueryTimeStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\" ElapsedTime=\"1911\" CpuTime=\"1872\" />"
  ],
  "Warnings": [
    "<ns0:Warnings xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:PlanAffectingConvert ConvertIssue=\"Cardinality Estimate\" Expression=\"CONVERT_IMPLICIT(varchar(12),[Expr1429],0)\" /><ns0:MemoryGrantWarning GrantWarningKind=\"Excessive Grant\" RequestedMemory=\"12480\" GrantedMemory=\"12480\" MaxUsedMemory=\"344\" /></ns0:Warnings>"
  ],
  "WaitStats": [
    "<ns0:WaitStats xmlns:ns0=\"http://schemas.microsoft.com/sqlserver/2004/07/showplan\"><ns0:Wait WaitType=\"SOS_SCHEDULER_YIELD\" WaitTimeMs=\"1\" WaitCount=\"332\" /><ns0:Wait WaitType=\"MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"4\" WaitCount=\"6554\" /><ns0:Wait WaitType=\"RESERVED_MEMORY_ALLOCATION_EXT\" WaitTimeMs=\"8\" WaitCount=\"18250\" /><ns0:Wait WaitType=\"PAGELATCH_SH\" WaitTimeMs=\"47\" WaitCount=\"20705\" /></ns0:WaitStats>"
  ],
  "MissingIndexes": []
}
```

| Nodo | Operador | Est filas/ejec | Filas reales total | Ejecuciones | Real/ejec | Logical reads | Objeto |
|---:|---|---:|---:|---:|---:|---:|---|
| 0 | Compute Scalar | 77.1473 | 0 | 0 | None | 0 |  |
| 1 | Nested Loops | 77.1473 | 102 | 1 | 102.0 | 0 |  |
| 2 | Nested Loops | 8.78388 | 102 | 1 | 102.0 | 0 |  |
| 3 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 4 | Nested Loops | 1 | 102 | 1 | 102.0 | 0 |  |
| 5 | Nested Loops | 6.29849 | 102 | 1 | 102.0 | 0 |  |
| 6 | Nested Loops | 4 | 102 | 1 | 102.0 | 0 |  |
| 7 | Nested Loops | 1 | 1 | 1 | 1.0 | 0 |  |
| 8 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 9 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 39 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 40 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 41 | Clustered Index Scan | 22.1868 | 25 | 1 | 25.0 | 54 | [campana_parcela_control] |
| 48 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 52 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 65 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 66 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 69 | Index Seek | 22.1868 | 25 | 1 | 25.0 | 2 | [campana_parcela_control] |
| 70 | Index Scan | 22.1868 | 25 | 1 | 25.0 | 6 | [campana_parcela_control] |
| 72 | Clustered Index Scan | 3774 | 3774 | 1 | 3774.0 | 240 | [flujos_reales_sulfuro] |
| 80 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 84 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 97 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [pad] |
| 98 | Clustered Index Seek | 1 | 1 | 1 | 1.0 | 2 | [parcela] |
| 101 | Index Seek | 22.1868 | 25 | 1 | 25.0 | 2 | [campana_parcela_control] |
| 102 | Index Scan | 22.1868 | 25 | 1 | 25.0 | 6 | [campana_parcela_control] |
| 104 | Clustered Index Scan | 4291 | 4291 | 1 | 4291.0 | 1440 | [drena_concentrados_sulfuro] |
| 111 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 113 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 117 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 24480 | [flujos_reales_sulfuro] |
| 123 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 125 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 129 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 146880 | [drena_concentrados_sulfuro] |
| 145 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 147 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 161 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 162 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 165 | Index Seek | 22.1868 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 166 | Index Scan | 22.1868 | 2550 | 102 | 25.0 | 612 | [campana_parcela_control] |
| 184 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 187 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 200 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 201 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 204 | Index Seek | 22.1868 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 205 | Index Scan | 22.1868 | 2550 | 102 | 25.0 | 612 | [campana_parcela_control] |
| 207 | Clustered Index Scan | 3774 | 384948 | 102 | 3774.0 | 24480 | [flujos_reales_sulfuro] |
| 215 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 218 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 231 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 232 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 235 | Index Seek | 22.1868 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 236 | Index Scan | 22.1868 | 2550 | 102 | 25.0 | 612 | [campana_parcela_control] |
| 238 | Clustered Index Scan | 4291 | 437682 | 102 | 4291.0 | 146880 | [drena_concentrados_sulfuro] |
| 240 | Index Seek | 6.65605 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 242 | Clustered Index Seek | 3.88523 | 510 | 2550 | 0.2 | 5100 | [campana_parcela_control] |
| 248 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 250 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 254 | Clustered Index Scan | 1 | 102 | 102 | 1.0 | 24480 | [flujos_reales_sulfuro] |
| 260 | Clustered Index Seek | 1 | 510 | 510 | 1.0 | 1020 | [pad] |
| 262 | Clustered Index Seek | 1 | 510 | 510 | 1.0 | 1020 | [parcela] |
| 266 | Clustered Index Scan | 1 | 510 | 510 | 1.0 | 734400 | [drena_concentrados_sulfuro] |
| 274 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 276 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 290 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [pad] |
| 291 | Clustered Index Seek | 1 | 102 | 102 | 1.0 | 204 | [parcela] |
| 294 | Index Seek | 22.1868 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 295 | Index Scan | 22.1868 | 2550 | 102 | 25.0 | 612 | [campana_parcela_control] |
| 308 | Index Seek | 6.65605 | 2550 | 102 | 25.0 | 204 | [campana_parcela_control] |
| 310 | Clustered Index Seek | 2.74687 | 510 | 2550 | 0.2 | 5100 | [campana_parcela_control] |
