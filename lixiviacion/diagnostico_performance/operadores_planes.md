# Operadores de los planes reales

Tiempos inclusivos: no sumar padres e hijos. Estimación y real/ejecución se comparan por ejecución, no contra el total acumulado.

## single_1_actualplan.sqlplan

```json
{
  "StatementText": "SELECT fecha,pad_id,parcela_id,numero_parcela,campana_id,numero_campana,estado_operacional,calidad_estado,tiene_dato_riego,riego_activo,tiene_dato_drenaje,drenaje_activo FROM inventar_SpcHidr.fn_estado_operacional_parcela_diario(@P1) WHERE pad_id=@P2 AND parcela_id=@P3",
  "StatementId": "1",
  "StatementCompId": "1",
  "StatementType": "SELECT",
  "RetrievedFromCache": "true",
  "StatementSubTreeCost": "8.25918",
  "StatementEstRows": "1.00009",
  "SecurityPolicyApplied": "false",
  "StatementOptmLevel": "FULL",
  "QueryHash": "0x25F4901A553A5224",
  "QueryPlanHash": "0x46475B5B6840321F",
  "StatementOptmEarlyAbortReason": "TimeOut",
  "CardinalityEstimationModelVersion": "140"
}
```

| Nodo | Padre | Operador | Est filas | Real total | Ejecuciones | Real/ejec | IO lógico | CPU ms | Elapsed ms | Objeto |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | — | Compute Scalar / Compute Scalar | 1.00009 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 1 | 0 | Nested Loops / Left Outer Join | 1.00009 | 1 | 1 | 1.000 | 0 | 15 | 15 |  |
| 2 | 1 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 2 | 2 |  |
| 3 | 2 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 4 | 3 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 5 | 4 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 6 | 4 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 7 | 3 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 8 | 7 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 9 | 8 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 10 | 8 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 11 | 10 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 12 | 10 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 13 | 12 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 14 | 13 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 15 | 14 | Window Spool / Window Spool | 406 | 500 | 1 | 500.000 | 0 | 0 | 0 |  |
| 16 | 15 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 17 | 16 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 18 | 17 | Sequence Project / Compute Scalar | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 19 | 18 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 20 | 19 | Sort / Sort | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 21 | 20 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 22 | 21 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 23 | 22 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 24 | 2 | Index Spool / Lazy Spool | 1 | 1 | 1 | 1.000 | 5 | 1 | 1 |  |
| 25 | 24 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 26 | 25 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 27 | 26 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 28 | 27 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 29 | 28 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 30 | 29 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 31 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 32 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 33 | 29 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 34 | 33 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 35 | 34 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 36 | 35 | Filter / Filter | 108.096 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 37 | 36 | Nested Loops / Left Outer Join | 1139.43 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 38 | 37 | Filter / Filter | 35.6073 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 40 | 38 | Clustered Index Scan / Clustered Index Scan | 35.6073 | 1 | 1 | 1.000 | 274 | 0 | 0 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 41 | 37 | Constant Scan / Constant Scan | 32 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 42 | 28 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 43 | 42 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 44 | 43 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 45 | 44 | Filter / Filter | 2.65631 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 46 | 45 | Nested Loops / Left Outer Join | 28 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 47 | 46 | Filter / Filter | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 49 | 47 | Clustered Index Scan / Clustered Index Scan | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 50 | 46 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 51 | 27 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 52 | 51 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 53 | 52 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 54 | 53 | Filter / Filter | 3.2 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 55 | 54 | Nested Loops / Left Outer Join | 32 | 32 | 1 | 32.000 | 0 | 1 | 1 |  |
| 56 | 55 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 58 | 56 | Clustered Index Scan / Clustered Index Scan | 1 | 1 | 1 | 1.000 | 1389 | 1 | 1 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 59 | 55 | Constant Scan / Constant Scan | 32 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 60 | 26 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 61 | 60 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 62 | 61 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 63 | 62 | Filter / Filter | 2.8 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 64 | 63 | Nested Loops / Left Outer Join | 28 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 65 | 64 | Filter / Filter | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 67 | 65 | Clustered Index Scan / Clustered Index Scan | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 68 | 64 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 69 | 1 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 70 | 69 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 71 | 70 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 12 | 12 |  |
| 72 | 71 | Compute Scalar / Compute Scalar | 10.2022 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 73 | 72 | Stream Aggregate / Aggregate | 10.2022 | 1 | 1 | 1.000 | 0 | 12 | 12 |  |
| 74 | 73 | Sort / Sort | 10.2022 | 2 | 1 | 2.000 | 0 | 12 | 12 |  |
| 75 | 74 | Compute Scalar / Compute Scalar | 10.2022 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 76 | 75 | Nested Loops / Left Outer Join | 10.2022 | 2 | 1 | 2.000 | 0 | 12 | 12 |  |
| 77 | 76 | Nested Loops / Left Outer Join | 9.75381 | 2 | 1 | 2.000 | 0 | 2 | 2 |  |
| 78 | 77 | Nested Loops / Inner Join | 4.80002 | 2 | 1 | 2.000 | 0 | 0 | 0 |  |
| 79 | 78 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 80 | 78 | Nested Loops / Inner Join | 5.18749 | 2 | 1 | 2.000 | 0 | 0 | 0 |  |
| 81 | 80 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 82 | 81 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 83 | 82 | Window Spool / Window Spool | 406 | 500 | 1 | 500.000 | 0 | 0 | 0 |  |
| 84 | 83 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 85 | 84 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 86 | 85 | Sequence Project / Compute Scalar | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 87 | 86 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 88 | 87 | Sort / Sort | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 89 | 88 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 90 | 89 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 91 | 90 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 92 | 80 | Nested Loops / Inner Join | 5.18749 | 2 | 1 | 2.000 | 0 | 0 | 0 |  |
| 93 | 92 | Index Seek / Index Seek | 5.18749 | 2 | 1 | 2.000 | 2 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 95 | 92 | Clustered Index Seek / Clustered Index Seek | 5.18749 | 2 | 2 | 1.000 | 4 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 96 | 77 | Index Spool / Lazy Spool | 1 | 2 | 2 | 1.000 | 7 | 1 | 1 |  |
| 97 | 96 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 98 | 97 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 99 | 98 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 100 | 99 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 101 | 100 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 102 | 101 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 103 | 101 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 104 | 103 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 105 | 104 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 106 | 105 | Filter / Filter | 34.183 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 107 | 106 | Nested Loops / Left Outer Join | 360.321 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 108 | 107 | Filter / Filter | 11.26 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 110 | 108 | Clustered Index Scan / Clustered Index Scan | 11.26 | 1 | 1 | 1.000 | 274 | 0 | 0 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 111 | 107 | Constant Scan / Constant Scan | 32 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 112 | 100 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 113 | 112 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 114 | 113 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 115 | 114 | Filter / Filter | 28.978 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 116 | 115 | Nested Loops / Left Outer Join | 305.455 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 117 | 116 | Filter / Filter | 10.9091 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 119 | 117 | Clustered Index Scan / Clustered Index Scan | 10.9091 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 120 | 116 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 121 | 99 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 122 | 121 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 123 | 122 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 124 | 123 | Filter / Filter | 3.2 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 125 | 124 | Nested Loops / Left Outer Join | 32 | 32 | 1 | 32.000 | 0 | 1 | 1 |  |
| 126 | 125 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 128 | 126 | Clustered Index Scan / Clustered Index Scan | 1 | 1 | 1 | 1.000 | 1389 | 0 | 0 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 129 | 125 | Constant Scan / Constant Scan | 32 | 32 | 1 | 32.000 | 0 | 0 | 0 |  |
| 130 | 98 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 131 | 130 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 132 | 131 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 133 | 132 | Filter / Filter | 2.8 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 134 | 133 | Nested Loops / Left Outer Join | 28 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 135 | 134 | Filter / Filter | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 137 | 135 | Clustered Index Scan / Clustered Index Scan | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 138 | 134 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 139 | 76 | Index Spool / Lazy Spool | 1 | 2 | 2 | 1.000 | 7 | 10 | 10 |  |
| 140 | 139 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 141 | 140 | Nested Loops / Left Outer Join | 1.00494 | 1 | 1 | 1.000 | 0 | 10 | 10 |  |
| 142 | 141 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 10 | 10 |  |
| 143 | 142 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 4 | 4 |  |
| 144 | 143 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 4 | 4 |  |
| 145 | 144 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 146 | 145 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 147 | 145 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 148 | 147 | Stream Aggregate / Aggregate | 203 | 5 | 1 | 5.000 | 0 | 0 | 0 |  |
| 149 | 148 | Window Spool / Window Spool | 406 | 10 | 1 | 10.000 | 0 | 0 | 0 |  |
| 150 | 149 | Segment / Segment | 203 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 151 | 150 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 152 | 151 | Sequence Project / Compute Scalar | 203 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 153 | 152 | Segment / Segment | 203 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 154 | 153 | Sort / Sort | 203 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 155 | 154 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 156 | 155 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 157 | 156 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 158 | 144 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 159 | 158 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 4 | 4 |  |
| 160 | 159 | Filter / Filter | 32.6343 | 296 | 1 | 296.000 | 0 | 4 | 4 |  |
| 161 | 160 | Nested Loops / Left Outer Join | 595.818 | 11040 | 1 | 11040.000 | 0 | 2 | 2 |  |
| 162 | 161 | Nested Loops / Inner Join | 18.6193 | 345 | 1 | 345.000 | 0 | 2 | 2 |  |
| 163 | 162 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 164 | 163 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 165 | 163 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 166 | 165 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 167 | 165 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 168 | 167 | Stream Aggregate / Aggregate | 165.7 | 5 | 1 | 5.000 | 0 | 0 | 0 |  |
| 169 | 168 | Window Spool / Window Spool | 331.399 | 10 | 1 | 10.000 | 0 | 0 | 0 |  |
| 170 | 169 | Segment / Segment | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 171 | 170 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 172 | 171 | Sequence Project / Compute Scalar | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 173 | 172 | Segment / Segment | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 174 | 173 | Sort / Sort | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 175 | 174 | Stream Aggregate / Aggregate | 165.7 | 140 | 1 | 140.000 | 0 | 0 | 0 |  |
| 176 | 175 | Sort / Sort | 289.489 | 279 | 1 | 279.000 | 0 | 0 | 0 |  |
| 178 | 176 | Hash Match / Inner Join | 149.726 | 279 | 1 | 279.000 | 0 | 0 | 0 |  |
| 179 | 178 | Index Seek / Index Seek | 289.489 | 279 | 1 | 279.000 | 5 | 0 | 0 | [campana_parcela_control] [IX_cpc_pad_parcela_fechas] |
| 180 | 178 | Index Scan / Index Scan | 289.785 | 281 | 1 | 281.000 | 6 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 181 | 162 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 182 | 181 | Clustered Index Scan / Clustered Index Scan | 3774 | 3774 | 1 | 3774.000 | 274 | 1 | 1 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 183 | 161 | Constant Scan / Constant Scan | 32 | 11040 | 345 | 32.000 | 0 | 0 | 0 |  |
| 184 | 143 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 185 | 184 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 186 | 185 | Filter / Filter | 28.5197 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 187 | 186 | Nested Loops / Left Outer Join | 520.697 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 188 | 187 | Nested Loops / Inner Join | 18.5963 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 189 | 188 | Nested Loops / Inner Join | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 190 | 189 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 1 | 0.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 191 | 189 | Nested Loops / Inner Join | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 192 | 191 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 193 | 191 | Filter / Filter | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 194 | 193 | Stream Aggregate / Aggregate | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 195 | 194 | Window Spool / Window Spool | 404.88 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 196 | 195 | Segment / Segment | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 197 | 196 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 198 | 197 | Sequence Project / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 199 | 198 | Segment / Segment | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 200 | 199 | Sort / Sort | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 201 | 200 | Stream Aggregate / Aggregate | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 202 | 201 | Sort / Sort | 689.51 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 203 | 202 | Clustered Index Scan / Clustered Index Scan | 689.51 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 204 | 188 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 205 | 204 | Clustered Index Scan / Clustered Index Scan | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 206 | 187 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 207 | 142 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 208 | 207 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 5 | 5 |  |
| 209 | 208 | Filter / Filter | 35.8078 | 290 | 1 | 290.000 | 0 | 5 | 5 |  |
| 210 | 209 | Nested Loops / Left Outer Join | 653.758 | 11072 | 1 | 11072.000 | 0 | 3 | 3 |  |
| 211 | 210 | Nested Loops / Inner Join | 20.4299 | 346 | 1 | 346.000 | 0 | 2 | 2 |  |
| 212 | 211 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 213 | 212 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 214 | 212 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 215 | 214 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 216 | 214 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 217 | 216 | Stream Aggregate / Aggregate | 165.7 | 5 | 1 | 5.000 | 0 | 0 | 0 |  |
| 218 | 217 | Window Spool / Window Spool | 331.399 | 10 | 1 | 10.000 | 0 | 0 | 0 |  |
| 219 | 218 | Segment / Segment | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 220 | 219 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 221 | 220 | Sequence Project / Compute Scalar | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 222 | 221 | Segment / Segment | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 223 | 222 | Sort / Sort | 165.7 | 8 | 1 | 8.000 | 0 | 0 | 0 |  |
| 224 | 223 | Stream Aggregate / Aggregate | 165.7 | 140 | 1 | 140.000 | 0 | 0 | 0 |  |
| 225 | 224 | Sort / Sort | 289.489 | 279 | 1 | 279.000 | 0 | 0 | 0 |  |
| 227 | 225 | Hash Match / Inner Join | 149.726 | 279 | 1 | 279.000 | 0 | 0 | 0 |  |
| 228 | 227 | Index Seek / Index Seek | 289.489 | 279 | 1 | 279.000 | 5 | 0 | 0 | [campana_parcela_control] [IX_cpc_pad_parcela_fechas] |
| 229 | 227 | Index Scan / Index Scan | 289.785 | 281 | 1 | 281.000 | 6 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 230 | 211 | Compute Scalar / Compute Scalar | 4141 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 231 | 230 | Clustered Index Scan / Clustered Index Scan | 4141 | 4141 | 1 | 4141.000 | 1389 | 1 | 1 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 232 | 210 | Constant Scan / Constant Scan | 32 | 11072 | 346 | 32.000 | 0 | 0 | 0 |  |
| 233 | 141 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 234 | 233 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 235 | 234 | Filter / Filter | 32.4267 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 236 | 235 | Nested Loops / Left Outer Join | 592.027 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 237 | 236 | Nested Loops / Inner Join | 21.1438 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 238 | 237 | Nested Loops / Inner Join | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 239 | 238 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 1 | 0.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 240 | 238 | Nested Loops / Inner Join | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 241 | 240 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 242 | 240 | Filter / Filter | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 243 | 242 | Stream Aggregate / Aggregate | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 244 | 243 | Window Spool / Window Spool | 404.88 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 245 | 244 | Segment / Segment | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 246 | 245 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 247 | 246 | Sequence Project / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 248 | 247 | Segment / Segment | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 249 | 248 | Sort / Sort | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 250 | 249 | Stream Aggregate / Aggregate | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 251 | 250 | Sort / Sort | 689.51 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 252 | 251 | Clustered Index Scan / Clustered Index Scan | 689.51 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 253 | 237 | Compute Scalar / Compute Scalar | 4291 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 254 | 253 | Clustered Index Scan / Clustered Index Scan | 4291 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 255 | 236 | Constant Scan / Constant Scan | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
## single_2_actualplan.sqlplan

```json
{
  "StatementText": "SELECT fecha,pad_id,parcela_id,numero_parcela,campana_id,numero_campana,estado_operacional,calidad_estado,tiene_dato_riego,riego_activo,tiene_dato_drenaje,drenaje_activo FROM inventar_SpcHidr.fn_estado_operacional_parcela_diario(@P1) WHERE pad_id=@P2 AND parcela_id=@P3",
  "StatementId": "1",
  "StatementCompId": "1",
  "StatementType": "SELECT",
  "RetrievedFromCache": "true",
  "StatementSubTreeCost": "8.25918",
  "StatementEstRows": "1.00009",
  "SecurityPolicyApplied": "false",
  "StatementOptmLevel": "FULL",
  "QueryHash": "0x25F4901A553A5224",
  "QueryPlanHash": "0x46475B5B6840321F",
  "StatementOptmEarlyAbortReason": "TimeOut",
  "CardinalityEstimationModelVersion": "140"
}
```

| Nodo | Padre | Operador | Est filas | Real total | Ejecuciones | Real/ejec | IO lógico | CPU ms | Elapsed ms | Objeto |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | — | Compute Scalar / Compute Scalar | 1.00009 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 1 | 0 | Nested Loops / Left Outer Join | 1.00009 | 1 | 1 | 1.000 | 0 | 25 | 25 |  |
| 2 | 1 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 3 | 3 |  |
| 3 | 2 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 4 | 3 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 5 | 4 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 6 | 4 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 7 | 3 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 8 | 7 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 9 | 8 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 10 | 8 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 11 | 10 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 12 | 10 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 13 | 12 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 14 | 13 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 1 | 1 |  |
| 15 | 14 | Window Spool / Window Spool | 406 | 500 | 1 | 500.000 | 0 | 1 | 1 |  |
| 16 | 15 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 1 | 1 |  |
| 17 | 16 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 18 | 17 | Sequence Project / Compute Scalar | 203 | 280 | 1 | 280.000 | 0 | 1 | 1 |  |
| 19 | 18 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 1 | 1 |  |
| 20 | 19 | Sort / Sort | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 21 | 20 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 22 | 21 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 23 | 22 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 24 | 2 | Index Spool / Lazy Spool | 1 | 1 | 1 | 1.000 | 5 | 2 | 2 |  |
| 25 | 24 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 26 | 25 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 2 | 2 |  |
| 27 | 26 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 28 | 27 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 29 | 28 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 30 | 29 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 31 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 32 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 33 | 29 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 34 | 33 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 35 | 34 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 36 | 35 | Filter / Filter | 108.096 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 37 | 36 | Nested Loops / Left Outer Join | 1139.43 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 38 | 37 | Filter / Filter | 35.6073 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 40 | 38 | Clustered Index Scan / Clustered Index Scan | 35.6073 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 41 | 37 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 42 | 28 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 43 | 42 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 44 | 43 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 45 | 44 | Filter / Filter | 2.65631 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 46 | 45 | Nested Loops / Left Outer Join | 28 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 47 | 46 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 49 | 47 | Clustered Index Scan / Clustered Index Scan | 1 | 1 | 1 | 1.000 | 240 | 0 | 0 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 50 | 46 | Constant Scan / Constant Scan | 28 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 51 | 27 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 52 | 51 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 53 | 52 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 54 | 53 | Filter / Filter | 3.2 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 55 | 54 | Nested Loops / Left Outer Join | 32 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 56 | 55 | Filter / Filter | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 58 | 56 | Clustered Index Scan / Clustered Index Scan | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 59 | 55 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 60 | 26 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 61 | 60 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 62 | 61 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 63 | 62 | Filter / Filter | 2.8 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 64 | 63 | Nested Loops / Left Outer Join | 28 | 28 | 1 | 28.000 | 0 | 1 | 1 |  |
| 65 | 64 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 67 | 65 | Clustered Index Scan / Clustered Index Scan | 1 | 1 | 1 | 1.000 | 1440 | 1 | 1 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 68 | 64 | Constant Scan / Constant Scan | 28 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 69 | 1 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 70 | 69 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 71 | 70 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 22 | 22 |  |
| 72 | 71 | Compute Scalar / Compute Scalar | 10.2022 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 73 | 72 | Stream Aggregate / Aggregate | 10.2022 | 1 | 1 | 1.000 | 0 | 22 | 22 |  |
| 74 | 73 | Sort / Sort | 10.2022 | 5 | 1 | 5.000 | 0 | 22 | 22 |  |
| 75 | 74 | Compute Scalar / Compute Scalar | 10.2022 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 76 | 75 | Nested Loops / Left Outer Join | 10.2022 | 5 | 1 | 5.000 | 0 | 22 | 22 |  |
| 77 | 76 | Nested Loops / Left Outer Join | 9.75381 | 5 | 1 | 5.000 | 0 | 3 | 3 |  |
| 78 | 77 | Nested Loops / Inner Join | 4.80002 | 5 | 1 | 5.000 | 0 | 1 | 1 |  |
| 79 | 78 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 80 | 78 | Nested Loops / Inner Join | 5.18749 | 5 | 1 | 5.000 | 0 | 1 | 1 |  |
| 81 | 80 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 82 | 81 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 1 | 1 |  |
| 83 | 82 | Window Spool / Window Spool | 406 | 500 | 1 | 500.000 | 0 | 1 | 1 |  |
| 84 | 83 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 85 | 84 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 86 | 85 | Sequence Project / Compute Scalar | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 87 | 86 | Segment / Segment | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 88 | 87 | Sort / Sort | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 89 | 88 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 90 | 89 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 91 | 90 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 92 | 80 | Nested Loops / Inner Join | 5.18749 | 5 | 1 | 5.000 | 0 | 0 | 0 |  |
| 93 | 92 | Index Seek / Index Seek | 5.18749 | 5 | 1 | 5.000 | 2 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 95 | 92 | Clustered Index Seek / Clustered Index Seek | 5.18749 | 5 | 5 | 1.000 | 10 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 96 | 77 | Index Spool / Lazy Spool | 1 | 5 | 5 | 1.000 | 13 | 1 | 1 |  |
| 97 | 96 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 98 | 97 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 99 | 98 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 100 | 99 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 101 | 100 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 102 | 101 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 103 | 101 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 104 | 103 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 105 | 104 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 106 | 105 | Filter / Filter | 34.183 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 107 | 106 | Nested Loops / Left Outer Join | 360.321 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 108 | 107 | Filter / Filter | 11.26 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 110 | 108 | Clustered Index Scan / Clustered Index Scan | 11.26 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 111 | 107 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 112 | 100 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 113 | 112 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 114 | 113 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 115 | 114 | Filter / Filter | 28.978 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 116 | 115 | Nested Loops / Left Outer Join | 305.455 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 117 | 116 | Filter / Filter | 10.9091 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 119 | 117 | Clustered Index Scan / Clustered Index Scan | 10.9091 | 1 | 1 | 1.000 | 240 | 0 | 0 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 120 | 116 | Constant Scan / Constant Scan | 28 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 121 | 99 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 122 | 121 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 123 | 122 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 124 | 123 | Filter / Filter | 3.2 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 125 | 124 | Nested Loops / Left Outer Join | 32 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 126 | 125 | Filter / Filter | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 128 | 126 | Clustered Index Scan / Clustered Index Scan | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 129 | 125 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 130 | 98 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 131 | 130 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 132 | 131 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 133 | 132 | Filter / Filter | 2.8 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 134 | 133 | Nested Loops / Left Outer Join | 28 | 28 | 1 | 28.000 | 0 | 1 | 1 |  |
| 135 | 134 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 137 | 135 | Clustered Index Scan / Clustered Index Scan | 1 | 1 | 1 | 1.000 | 1440 | 1 | 1 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 138 | 134 | Constant Scan / Constant Scan | 28 | 28 | 1 | 28.000 | 0 | 0 | 0 |  |
| 139 | 76 | Index Spool / Lazy Spool | 1 | 5 | 5 | 1.000 | 13 | 19 | 19 |  |
| 140 | 139 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 141 | 140 | Nested Loops / Left Outer Join | 1.00494 | 1 | 1 | 1.000 | 0 | 19 | 19 |  |
| 142 | 141 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 9 | 9 |  |
| 143 | 142 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 9 | 9 |  |
| 144 | 143 | Nested Loops / Left Outer Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 145 | 144 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 146 | 145 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 147 | 145 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 1 | 1 |  |
| 148 | 147 | Stream Aggregate / Aggregate | 203 | 175 | 1 | 175.000 | 0 | 1 | 1 |  |
| 149 | 148 | Window Spool / Window Spool | 406 | 312 | 1 | 312.000 | 0 | 1 | 1 |  |
| 150 | 149 | Segment / Segment | 203 | 178 | 1 | 178.000 | 0 | 1 | 1 |  |
| 151 | 150 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 152 | 151 | Sequence Project / Compute Scalar | 203 | 178 | 1 | 178.000 | 0 | 1 | 1 |  |
| 153 | 152 | Segment / Segment | 203 | 178 | 1 | 178.000 | 0 | 1 | 1 |  |
| 154 | 153 | Sort / Sort | 203 | 178 | 1 | 178.000 | 0 | 1 | 1 |  |
| 155 | 154 | Stream Aggregate / Aggregate | 203 | 280 | 1 | 280.000 | 0 | 0 | 0 |  |
| 156 | 155 | Sort / Sort | 978 | 978 | 1 | 978.000 | 0 | 0 | 0 |  |
| 157 | 156 | Clustered Index Scan / Clustered Index Scan | 978 | 978 | 1 | 978.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 158 | 144 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 159 | 158 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 160 | 159 | Filter / Filter | 32.6343 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 161 | 160 | Nested Loops / Left Outer Join | 595.818 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 162 | 161 | Nested Loops / Inner Join | 18.6193 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 163 | 162 | Nested Loops / Inner Join | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 164 | 163 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 1 | 0.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 165 | 163 | Nested Loops / Inner Join | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 166 | 165 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 167 | 165 | Filter / Filter | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 168 | 167 | Stream Aggregate / Aggregate | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 169 | 168 | Window Spool / Window Spool | 331.399 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 170 | 169 | Segment / Segment | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 171 | 170 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 172 | 171 | Sequence Project / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 173 | 172 | Segment / Segment | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 174 | 173 | Sort / Sort | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 175 | 174 | Stream Aggregate / Aggregate | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 176 | 175 | Sort / Sort | 289.489 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 178 | 176 | Hash Match / Inner Join | 149.726 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 179 | 178 | Index Seek / Index Seek | 289.489 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [IX_cpc_pad_parcela_fechas] |
| 180 | 178 | Index Scan / Index Scan | 289.785 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 181 | 162 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 182 | 181 | Clustered Index Scan / Clustered Index Scan | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 183 | 161 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 184 | 143 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 185 | 184 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 7 | 7 |  |
| 186 | 185 | Filter / Filter | 28.5197 | 350 | 1 | 350.000 | 0 | 7 | 7 |  |
| 187 | 186 | Nested Loops / Left Outer Join | 520.697 | 11676 | 1 | 11676.000 | 0 | 5 | 5 |  |
| 188 | 187 | Nested Loops / Inner Join | 18.5963 | 417 | 1 | 417.000 | 0 | 3 | 3 |  |
| 189 | 188 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 190 | 189 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 191 | 189 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 192 | 191 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 193 | 191 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 194 | 193 | Stream Aggregate / Aggregate | 202.44 | 35 | 1 | 35.000 | 0 | 0 | 0 |  |
| 195 | 194 | Window Spool / Window Spool | 404.88 | 64 | 1 | 64.000 | 0 | 0 | 0 |  |
| 196 | 195 | Segment / Segment | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 197 | 196 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 198 | 197 | Sequence Project / Compute Scalar | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 199 | 198 | Segment / Segment | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 200 | 199 | Sort / Sort | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 201 | 200 | Stream Aggregate / Aggregate | 202.44 | 140 | 1 | 140.000 | 0 | 0 | 0 |  |
| 202 | 201 | Sort / Sort | 689.51 | 699 | 1 | 699.000 | 0 | 0 | 0 |  |
| 203 | 202 | Clustered Index Scan / Clustered Index Scan | 689.51 | 699 | 1 | 699.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 204 | 188 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 205 | 204 | Clustered Index Scan / Clustered Index Scan | 3774 | 3774 | 1 | 3774.000 | 240 | 2 | 2 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 206 | 187 | Constant Scan / Constant Scan | 28 | 11676 | 417 | 28.000 | 0 | 0 | 0 |  |
| 207 | 142 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 208 | 207 | Stream Aggregate / Aggregate | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 209 | 208 | Filter / Filter | 35.8078 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 210 | 209 | Nested Loops / Left Outer Join | 653.758 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 211 | 210 | Nested Loops / Inner Join | 20.4299 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 212 | 211 | Nested Loops / Inner Join | 1 | 0 | 1 | 0.000 | 0 | 0 | 0 |  |
| 213 | 212 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 1 | 0.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 214 | 212 | Nested Loops / Inner Join | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 215 | 214 | Clustered Index Seek / Clustered Index Seek | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 216 | 214 | Filter / Filter | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 217 | 216 | Stream Aggregate / Aggregate | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 218 | 217 | Window Spool / Window Spool | 331.399 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 219 | 218 | Segment / Segment | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 220 | 219 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 221 | 220 | Sequence Project / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 222 | 221 | Segment / Segment | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 223 | 222 | Sort / Sort | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 224 | 223 | Stream Aggregate / Aggregate | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 225 | 224 | Sort / Sort | 289.489 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 227 | 225 | Hash Match / Inner Join | 149.726 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 228 | 227 | Index Seek / Index Seek | 289.489 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [IX_cpc_pad_parcela_fechas] |
| 229 | 227 | Index Scan / Index Scan | 289.785 | 0 | 0 | 0.000 | 0 | 0 | 0 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 230 | 211 | Compute Scalar / Compute Scalar | 4141 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 231 | 230 | Clustered Index Scan / Clustered Index Scan | 4141 | 0 | 0 | 0.000 | 0 | 0 | 0 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 232 | 210 | Constant Scan / Constant Scan | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 233 | 141 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 234 | 233 | Stream Aggregate / Aggregate | 1 | 1 | 1 | 1.000 | 0 | 9 | 9 |  |
| 235 | 234 | Filter / Filter | 32.4267 | 339 | 1 | 339.000 | 0 | 9 | 9 |  |
| 236 | 235 | Nested Loops / Left Outer Join | 592.027 | 11704 | 1 | 11704.000 | 0 | 5 | 5 |  |
| 237 | 236 | Nested Loops / Inner Join | 21.1438 | 418 | 1 | 418.000 | 0 | 4 | 4 |  |
| 238 | 237 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 239 | 238 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 240 | 238 | Nested Loops / Inner Join | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 241 | 240 | Clustered Index Seek / Clustered Index Seek | 1 | 1 | 1 | 1.000 | 2 | 0 | 0 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 242 | 240 | Filter / Filter | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 243 | 242 | Stream Aggregate / Aggregate | 202.44 | 35 | 1 | 35.000 | 0 | 0 | 0 |  |
| 244 | 243 | Window Spool / Window Spool | 404.88 | 64 | 1 | 64.000 | 0 | 0 | 0 |  |
| 245 | 244 | Segment / Segment | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 246 | 245 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 247 | 246 | Sequence Project / Compute Scalar | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 248 | 247 | Segment / Segment | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 249 | 248 | Sort / Sort | 202.44 | 38 | 1 | 38.000 | 0 | 0 | 0 |  |
| 250 | 249 | Stream Aggregate / Aggregate | 202.44 | 140 | 1 | 140.000 | 0 | 0 | 0 |  |
| 251 | 250 | Sort / Sort | 689.51 | 699 | 1 | 699.000 | 0 | 0 | 0 |  |
| 252 | 251 | Clustered Index Scan / Clustered Index Scan | 689.51 | 699 | 1 | 699.000 | 54 | 0 | 0 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 253 | 237 | Compute Scalar / Compute Scalar | 4291 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 254 | 253 | Clustered Index Scan / Clustered Index Scan | 4291 | 4291 | 1 | 4291.000 | 1440 | 3 | 3 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 255 | 236 | Constant Scan / Constant Scan | 28 | 11704 | 418 | 28.000 | 0 | 0 | 0 |  |
## timeline_102d_ox_p1_actualplan.sqlplan

```json
{
  "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n    ) SELECT e.fecha,e.pad_id,e.parcela_id,e.numero_parcela,e.campana_id,e.numero_campana,e.estado_operacional,e.calidad_estado,e.tiene_dato_riego,e.riego_activo,e.tiene_dato_drenaje,e.drenaje_activo\n    FROM fechas d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) e\n    WHERE e.pad_id=@P3 AND e.parcela_id=@P4\n    ORDER BY e.fecha OPTION (MAXRECURSION 32767)",
  "StatementId": "1",
  "StatementCompId": "1",
  "StatementType": "SELECT",
  "RetrievedFromCache": "true",
  "StatementSubTreeCost": "9.29993",
  "StatementEstRows": "11.5043",
  "SecurityPolicyApplied": "false",
  "StatementOptmLevel": "FULL",
  "QueryHash": "0xDC6F7FA1FB43E983",
  "QueryPlanHash": "0x75F647FB677DE496",
  "StatementOptmEarlyAbortReason": "TimeOut",
  "CardinalityEstimationModelVersion": "140"
}
```

| Nodo | Padre | Operador | Est filas | Real total | Ejecuciones | Real/ejec | IO lógico | CPU ms | Elapsed ms | Objeto |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | — | Compute Scalar / Compute Scalar | 11.5043 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 1 | 0 | Filter / Filter | 11.5043 | 102 | 1 | 102.000 | 0 | 69405 | 69409 |  |
| 2 | 1 | Nested Loops / Inner Join | 449.1 | 6120 | 1 | 6120.000 | 0 | 69404 | 69408 |  |
| 3 | 2 | Sort / Sort | 4 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 4 | 3 | Index Spool / Lazy Spool | 4 | 102 | 1 | 102.000 | 205 | 0 | 0 |  |
| 5 | 4 | Concatenation / Concatenation | 4 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 6 | 5 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 7 | 6 | Constant Scan / Constant Scan | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 8 | 5 | Assert / Assert | 4 | 101 | 1 | 101.000 | 0 | 0 | 0 |  |
| 9 | 8 | Nested Loops / Inner Join | 4 | 101 | 1 | 101.000 | 0 | 0 | 0 |  |
| 10 | 9 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 11 | 10 | Table Spool / Lazy Spool | 1 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 12 | 9 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 13 | 12 | Filter / Filter | 1 | 101 | 102 | 0.990 | 0 | 0 | 0 |  |
| 14 | 13 | Constant Scan / Constant Scan | 1 | 101 | 101 | 1.000 | 0 | 0 | 0 |  |
| 15 | 2 | Table Spool / Lazy Spool | 112.275 | 6120 | 102 | 60.000 | 12241 | 69397 | 69401 |  |
| 16 | 15 | Hash Match / Right Outer Join | 112.275 | 6120 | 102 | 60.000 | 0 | 69387 | 69391 |  |
| 17 | 16 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 18 | 17 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 19 | 18 | Stream Aggregate / Aggregate | 1 | 6120 | 102 | 60.000 | 0 | 68839 | 68843 |  |
| 20 | 19 | Sort / Sort | 12 | 6271 | 102 | 61.480 | 0 | 68834 | 68838 |  |
| 21 | 20 | Compute Scalar / Compute Scalar | 12 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 22 | 21 | Stream Aggregate / Aggregate | 12 | 6271 | 102 | 61.480 | 0 | 68830 | 68833 |  |
| 23 | 22 | Sort / Sort | 78.0066 | 20548 | 102 | 201.451 | 0 | 68826 | 68830 |  |
| 24 | 23 | Compute Scalar / Compute Scalar | 78.0066 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 25 | 24 | Nested Loops / Left Outer Join | 78.0066 | 20548 | 102 | 201.451 | 0 | 68777 | 68781 |  |
| 26 | 25 | Nested Loops / Left Outer Join | 76.3406 | 20548 | 102 | 201.451 | 0 | 8329 | 8330 |  |
| 27 | 26 | Nested Loops / Inner Join | 105.645 | 20548 | 102 | 201.451 | 0 | 362 | 362 |  |
| 29 | 27 | Nested Loops / Inner Join | 105.645 | 20855 | 102 | 204.461 | 0 | 281 | 281 |  |
| 30 | 29 | Nested Loops / Inner Join | 21.8836 | 6120 | 102 | 60.000 | 0 | 196 | 196 |  |
| 31 | 30 | Filter / Filter | 33.4521 | 6120 | 102 | 60.000 | 0 | 167 | 167 |  |
| 32 | 31 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 162 | 162 |  |
| 33 | 32 | Window Spool / Window Spool | 406 | 51000 | 102 | 500.000 | 0 | 129 | 129 |  |
| 34 | 33 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 88 | 88 |  |
| 35 | 34 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 36 | 35 | Sequence Project / Compute Scalar | 203 | 28560 | 102 | 280.000 | 0 | 83 | 83 |  |
| 37 | 36 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 75 | 75 |  |
| 38 | 37 | Sort / Sort | 203 | 28560 | 102 | 280.000 | 0 | 69 | 69 |  |
| 39 | 38 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 41 | 41 |  |
| 40 | 39 | Sort / Sort | 978 | 99756 | 102 | 978.000 | 0 | 32 | 32 |  |
| 41 | 40 | Clustered Index Scan / Clustered Index Scan | 978 | 99756 | 102 | 978.000 | 5508 | 11 | 11 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 42 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 20 | 20 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 43 | 29 | Index Seek / Index Seek | 4.82759 | 20855 | 6120 | 3.408 | 12240 | 80 | 80 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 45 | 27 | Clustered Index Seek / Clustered Index Seek | 31.7259 | 20548 | 20855 | 0.985 | 40398 | 49 | 49 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 46 | 26 | Index Spool / Lazy Spool | 1 | 20548 | 20548 | 1.000 | 77813 | 7897 | 7898 |  |
| 47 | 46 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 48 | 47 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 7734 | 7735 |  |
| 49 | 48 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 4778 | 4778 |  |
| 50 | 49 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 1730 | 1730 |  |
| 51 | 50 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 921 | 922 |  |
| 52 | 51 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 14 | 14 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 53 | 51 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 54 | 53 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 55 | 54 | Stream Aggregate / Aggregate | 1 | 3264 | 6120 | 0.533 | 0 | 897 | 897 |  |
| 56 | 55 | Filter / Filter | 3.03579 | 3264 | 6120 | 0.533 | 0 | 891 | 892 |  |
| 57 | 56 | Nested Loops / Left Outer Join | 32 | 104448 | 6120 | 17.067 | 0 | 875 | 875 |  |
| 58 | 57 | Filter / Filter | 1 | 3264 | 6120 | 0.533 | 0 | 862 | 862 |  |
| 60 | 58 | Clustered Index Scan / Clustered Index Scan | 1 | 3264 | 3264 | 1.000 | 894336 | 856 | 856 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 61 | 57 | Constant Scan / Constant Scan | 32 | 104448 | 3264 | 32.000 | 0 | 2 | 2 |  |
| 62 | 50 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 63 | 62 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 64 | 63 | Stream Aggregate / Aggregate | 1 | 2856 | 6120 | 0.467 | 0 | 796 | 796 |  |
| 65 | 64 | Filter / Filter | 2.65631 | 2856 | 6120 | 0.467 | 0 | 790 | 790 |  |
| 66 | 65 | Nested Loops / Left Outer Join | 28 | 79968 | 6120 | 13.067 | 0 | 777 | 777 |  |
| 67 | 66 | Filter / Filter | 1 | 2856 | 6120 | 0.467 | 0 | 766 | 766 |  |
| 69 | 67 | Clustered Index Scan / Clustered Index Scan | 1 | 2856 | 2856 | 1.000 | 685440 | 761 | 761 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 70 | 66 | Constant Scan / Constant Scan | 28 | 79968 | 2856 | 28.000 | 0 | 2 | 2 |  |
| 71 | 49 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 72 | 71 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 73 | 72 | Stream Aggregate / Aggregate | 1 | 3264 | 6120 | 0.533 | 0 | 3030 | 3031 |  |
| 74 | 73 | Filter / Filter | 3.2 | 3264 | 6120 | 0.533 | 0 | 3023 | 3023 |  |
| 75 | 74 | Nested Loops / Left Outer Join | 32 | 104448 | 6120 | 17.067 | 0 | 2983 | 2984 |  |
| 76 | 75 | Filter / Filter | 1 | 3264 | 6120 | 0.533 | 0 | 2970 | 2970 |  |
| 78 | 76 | Clustered Index Scan / Clustered Index Scan | 1 | 3264 | 3264 | 1.000 | 4.5337e+06 | 2965 | 2966 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 79 | 75 | Constant Scan / Constant Scan | 32 | 104448 | 3264 | 32.000 | 0 | 2 | 2 |  |
| 80 | 48 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 81 | 80 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 82 | 81 | Stream Aggregate / Aggregate | 1 | 2856 | 6120 | 0.467 | 0 | 2937 | 2938 |  |
| 83 | 82 | Filter / Filter | 2.8 | 2856 | 6120 | 0.467 | 0 | 2931 | 2931 |  |
| 84 | 83 | Nested Loops / Left Outer Join | 28 | 79968 | 6120 | 13.067 | 0 | 2898 | 2898 |  |
| 85 | 84 | Filter / Filter | 1 | 2856 | 6120 | 0.467 | 0 | 2886 | 2886 |  |
| 87 | 85 | Clustered Index Scan / Clustered Index Scan | 1 | 2856 | 2856 | 1.000 | 4.11264e+06 | 2881 | 2881 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 88 | 84 | Constant Scan / Constant Scan | 28 | 79968 | 2856 | 28.000 | 0 | 2 | 2 |  |
| 89 | 25 | Index Spool / Lazy Spool | 1 | 20548 | 20548 | 1.000 | 77813 | 60169 | 60173 |  |
| 90 | 89 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 91 | 90 | Nested Loops / Left Outer Join | 1.00494 | 6120 | 6120 | 1.000 | 0 | 59979 | 59982 |  |
| 92 | 91 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 44794 | 44796 |  |
| 93 | 92 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 26551 | 26552 |  |
| 94 | 93 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 16407 | 16408 |  |
| 95 | 94 | Nested Loops / Inner Join | 1 | 6120 | 6120 | 1.000 | 0 | 3871 | 3871 |  |
| 96 | 95 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 28 | 28 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 97 | 95 | Filter / Filter | 1 | 6120 | 6120 | 1.000 | 0 | 3836 | 3836 |  |
| 98 | 97 | Stream Aggregate / Aggregate | 203 | 862008 | 6120 | 140.851 | 0 | 3775 | 3775 |  |
| 99 | 98 | Window Spool / Window Spool | 406 | 1.54388e+06 | 6120 | 252.267 | 0 | 3542 | 3542 |  |
| 100 | 99 | Segment / Segment | 203 | 879860 | 6120 | 143.768 | 0 | 3184 | 3184 |  |
| 101 | 100 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 102 | 101 | Sequence Project / Compute Scalar | 203 | 879860 | 6120 | 143.768 | 0 | 3128 | 3128 |  |
| 103 | 102 | Segment / Segment | 203 | 879860 | 6120 | 143.768 | 0 | 3051 | 3052 |  |
| 104 | 103 | Sort / Sort | 203 | 879860 | 6120 | 143.768 | 0 | 2994 | 2994 |  |
| 105 | 104 | Stream Aggregate / Aggregate | 203 | 1.7136e+06 | 6120 | 280.000 | 0 | 2600 | 2601 |  |
| 106 | 105 | Sort / Sort | 978 | 5.98536e+06 | 6120 | 978.000 | 0 | 2071 | 2072 |  |
| 107 | 106 | Clustered Index Scan / Clustered Index Scan | 978 | 5.98536e+06 | 6120 | 978.000 | 330480 | 759 | 759 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 108 | 94 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 109 | 108 | Stream Aggregate / Aggregate | 1 | 3228 | 6120 | 0.527 | 0 | 12507 | 12508 |  |
| 110 | 109 | Filter / Filter | 32.5849 | 821352 | 6120 | 134.208 | 0 | 12413 | 12414 |  |
| 111 | 110 | Nested Loops / Left Outer Join | 594.916 | 3.59209e+07 | 6120 | 5869.427 | 0 | 8019 | 8020 |  |
| 112 | 111 | Nested Loops / Inner Join | 18.5911 | 1.12253e+06 | 6120 | 183.420 | 0 | 5328 | 5328 |  |
| 113 | 112 | Nested Loops / Inner Join | 1 | 3264 | 6120 | 0.533 | 0 | 996 | 996 |  |
| 114 | 113 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 6120 | 0.533 | 12240 | 45 | 45 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 115 | 113 | Nested Loops / Inner Join | 1 | 3264 | 3264 | 1.000 | 0 | 941 | 941 |  |
| 116 | 115 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 3264 | 1.000 | 6528 | 14 | 14 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 117 | 115 | Filter / Filter | 1 | 3264 | 3264 | 1.000 | 0 | 920 | 920 |  |
| 118 | 117 | Stream Aggregate / Aggregate | 165.7 | 255444 | 3264 | 78.261 | 0 | 901 | 901 |  |
| 119 | 118 | Window Spool / Window Spool | 331.399 | 460260 | 3264 | 141.011 | 0 | 818 | 818 |  |
| 120 | 119 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 707 | 707 |  |
| 121 | 120 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 122 | 121 | Sequence Project / Compute Scalar | 165.7 | 264864 | 3264 | 81.147 | 0 | 691 | 691 |  |
| 123 | 122 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 668 | 668 |  |
| 124 | 123 | Sort / Sort | 165.7 | 264864 | 3264 | 81.147 | 0 | 652 | 652 |  |
| 125 | 124 | Stream Aggregate / Aggregate | 165.7 | 456960 | 3264 | 140.000 | 0 | 505 | 505 |  |
| 126 | 125 | Sort / Sort | 289.489 | 910656 | 3264 | 279.000 | 0 | 407 | 407 |  |
| 127 | 126 | Clustered Index Scan / Clustered Index Scan | 289.489 | 910656 | 3264 | 279.000 | 176256 | 201 | 201 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 128 | 112 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 129 | 128 | Clustered Index Scan / Clustered Index Scan | 3774 | 1.23183e+07 | 3264 | 3774.000 | 894336 | 3706 | 3706 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 130 | 111 | Constant Scan / Constant Scan | 32 | 3.59209e+07 | 1.12253e+06 | 32.000 | 0 | 755 | 755 |  |
| 131 | 93 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 132 | 131 | Stream Aggregate / Aggregate | 1 | 2833 | 6120 | 0.463 | 0 | 10104 | 10105 |  |
| 133 | 132 | Filter / Filter | 28.5118 | 676948 | 6120 | 110.612 | 0 | 10029 | 10030 |  |
| 134 | 133 | Nested Loops / Left Outer Join | 520.552 | 2.51926e+07 | 6120 | 4116.444 | 0 | 7005 | 7006 |  |
| 135 | 134 | Nested Loops / Inner Join | 18.5911 | 899737 | 6120 | 147.016 | 0 | 5095 | 5095 |  |
| 136 | 135 | Nested Loops / Inner Join | 1 | 2856 | 6120 | 0.467 | 0 | 1258 | 1258 |  |
| 137 | 136 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 6120 | 0.467 | 12240 | 38 | 38 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 138 | 136 | Nested Loops / Inner Join | 1 | 2856 | 2856 | 1.000 | 0 | 1210 | 1211 |  |
| 139 | 138 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 2856 | 1.000 | 5712 | 13 | 13 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 140 | 138 | Filter / Filter | 1 | 2856 | 2856 | 1.000 | 0 | 1191 | 1191 |  |
| 141 | 140 | Stream Aggregate / Aggregate | 202.44 | 206724 | 2856 | 72.382 | 0 | 1176 | 1176 |  |
| 142 | 141 | Window Spool / Window Spool | 404.88 | 375226 | 2856 | 131.382 | 0 | 1109 | 1109 |  |
| 143 | 142 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1015 | 1015 |  |
| 144 | 143 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 145 | 144 | Sequence Project / Compute Scalar | 202.44 | 214850 | 2856 | 75.228 | 0 | 1002 | 1002 |  |
| 146 | 145 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 983 | 983 |  |
| 147 | 146 | Sort / Sort | 202.44 | 214850 | 2856 | 75.228 | 0 | 970 | 970 |  |
| 148 | 147 | Stream Aggregate / Aggregate | 202.44 | 399840 | 2856 | 140.000 | 0 | 837 | 838 |  |
| 149 | 148 | Sort / Sort | 689.51 | 1.99634e+06 | 2856 | 699.000 | 0 | 672 | 672 |  |
| 150 | 149 | Clustered Index Scan / Clustered Index Scan | 689.51 | 1.99634e+06 | 2856 | 699.000 | 154224 | 247 | 247 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 151 | 135 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 152 | 151 | Clustered Index Scan / Clustered Index Scan | 3774 | 1.07785e+07 | 2856 | 3774.000 | 685440 | 3304 | 3304 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 153 | 134 | Constant Scan / Constant Scan | 28 | 2.51926e+07 | 899737 | 28.000 | 0 | 537 | 537 |  |
| 154 | 92 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 155 | 154 | Stream Aggregate / Aggregate | 1 | 3228 | 6120 | 0.527 | 0 | 18205 | 18206 |  |
| 156 | 155 | Filter / Filter | 35.7536 | 800910 | 6120 | 130.868 | 0 | 18096 | 18097 |  |
| 157 | 156 | Nested Loops / Left Outer Join | 652.768 | 3.60232e+07 | 6120 | 5886.149 | 0 | 10963 | 10964 |  |
| 158 | 157 | Nested Loops / Inner Join | 20.399 | 1.12573e+06 | 6120 | 183.942 | 0 | 8258 | 8258 |  |
| 159 | 158 | Nested Loops / Inner Join | 1 | 3264 | 6120 | 0.533 | 0 | 1121 | 1121 |  |
| 160 | 159 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 6120 | 0.533 | 12240 | 37 | 37 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 161 | 159 | Nested Loops / Inner Join | 1 | 3264 | 3264 | 1.000 | 0 | 1074 | 1074 |  |
| 162 | 161 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 3264 | 1.000 | 6528 | 10 | 10 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 163 | 161 | Filter / Filter | 1 | 3264 | 3264 | 1.000 | 0 | 1056 | 1056 |  |
| 164 | 163 | Stream Aggregate / Aggregate | 165.7 | 255444 | 3264 | 78.261 | 0 | 1037 | 1037 |  |
| 165 | 164 | Window Spool / Window Spool | 331.399 | 460260 | 3264 | 141.011 | 0 | 954 | 954 |  |
| 166 | 165 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 832 | 832 |  |
| 167 | 166 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 168 | 167 | Sequence Project / Compute Scalar | 165.7 | 264864 | 3264 | 81.147 | 0 | 816 | 816 |  |
| 169 | 168 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 791 | 791 |  |
| 170 | 169 | Sort / Sort | 165.7 | 264864 | 3264 | 81.147 | 0 | 774 | 774 |  |
| 171 | 170 | Stream Aggregate / Aggregate | 165.7 | 456960 | 3264 | 140.000 | 0 | 611 | 611 |  |
| 172 | 171 | Sort / Sort | 289.489 | 910656 | 3264 | 279.000 | 0 | 513 | 513 |  |
| 173 | 172 | Clustered Index Scan / Clustered Index Scan | 289.489 | 910656 | 3264 | 279.000 | 176256 | 267 | 267 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 174 | 158 | Compute Scalar / Compute Scalar | 4141 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 175 | 174 | Clustered Index Scan / Clustered Index Scan | 4141 | 1.35162e+07 | 3264 | 4141.000 | 4.5337e+06 | 6177 | 6177 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 176 | 157 | Constant Scan / Constant Scan | 32 | 3.60232e+07 | 1.12573e+06 | 32.000 | 0 | 762 | 762 |  |
| 177 | 91 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 178 | 177 | Stream Aggregate / Aggregate | 1 | 2833 | 6120 | 0.463 | 0 | 15141 | 15142 |  |
| 179 | 178 | Filter / Filter | 32.4176 | 661015 | 6120 | 108.009 | 0 | 15049 | 15050 |  |
| 180 | 179 | Nested Loops / Left Outer Join | 591.862 | 2.52632e+07 | 6120 | 4127.973 | 0 | 9953 | 9954 |  |
| 181 | 180 | Nested Loops / Inner Join | 21.1379 | 902257 | 6120 | 147.428 | 0 | 8014 | 8015 |  |
| 182 | 181 | Nested Loops / Inner Join | 1 | 2856 | 6120 | 0.467 | 0 | 1350 | 1350 |  |
| 183 | 182 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 6120 | 0.467 | 12240 | 43 | 43 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 184 | 182 | Nested Loops / Inner Join | 1 | 2856 | 2856 | 1.000 | 0 | 1296 | 1296 |  |
| 185 | 184 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 2856 | 1.000 | 5712 | 9 | 9 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 186 | 184 | Filter / Filter | 1 | 2856 | 2856 | 1.000 | 0 | 1281 | 1281 |  |
| 187 | 186 | Stream Aggregate / Aggregate | 202.44 | 206724 | 2856 | 72.382 | 0 | 1263 | 1263 |  |
| 188 | 187 | Window Spool / Window Spool | 404.88 | 375226 | 2856 | 131.382 | 0 | 1193 | 1193 |  |
| 189 | 188 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1093 | 1093 |  |
| 190 | 189 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 191 | 190 | Sequence Project / Compute Scalar | 202.44 | 214850 | 2856 | 75.228 | 0 | 1078 | 1078 |  |
| 192 | 191 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1058 | 1058 |  |
| 193 | 192 | Sort / Sort | 202.44 | 214850 | 2856 | 75.228 | 0 | 1044 | 1044 |  |
| 194 | 193 | Stream Aggregate / Aggregate | 202.44 | 399840 | 2856 | 140.000 | 0 | 905 | 905 |  |
| 195 | 194 | Sort / Sort | 689.51 | 1.99634e+06 | 2856 | 699.000 | 0 | 736 | 736 |  |
| 196 | 195 | Clustered Index Scan / Clustered Index Scan | 689.51 | 1.99634e+06 | 2856 | 699.000 | 154224 | 283 | 283 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 197 | 181 | Compute Scalar / Compute Scalar | 4291 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 198 | 197 | Clustered Index Scan / Clustered Index Scan | 4291 | 1.22551e+07 | 2856 | 4291.000 | 4.11264e+06 | 5790 | 5791 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 199 | 180 | Constant Scan / Constant Scan | 28 | 2.52632e+07 | 902257 | 28.000 | 0 | 542 | 542 |  |
| 200 | 16 | Hash Match / Right Outer Join | 111.726 | 6120 | 102 | 60.000 | 0 | 529 | 529 |  |
| 201 | 200 | Compute Scalar / Compute Scalar | 101.173 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 202 | 201 | Hash Match / Right Outer Join | 101.173 | 6120 | 102 | 60.000 | 0 | 359 | 360 |  |
| 203 | 202 | Compute Scalar / Compute Scalar | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 204 | 203 | Compute Scalar / Compute Scalar | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 205 | 204 | Stream Aggregate / Aggregate | 28 | 2856 | 102 | 28.000 | 0 | 121 | 121 |  |
| 206 | 205 | Sort / Sort | 28.4846 | 2856 | 102 | 28.000 | 0 | 120 | 121 |  |
| 207 | 206 | Compute Scalar / Compute Scalar | 28.4846 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 208 | 207 | Filter / Filter | 28.4846 | 2856 | 102 | 28.000 | 0 | 115 | 115 |  |
| 209 | 208 | Nested Loops / Left Outer Join | 28.4846 | 2856 | 102 | 28.000 | 0 | 114 | 115 |  |
| 211 | 209 | Clustered Index Scan / Clustered Index Scan | 1.01731 | 102 | 102 | 1.000 | 146880 | 114 | 114 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 212 | 209 | Constant Scan / Constant Scan | 28 | 2856 | 102 | 28.000 | 0 | 0 | 0 |  |
| 213 | 202 | Hash Match / Right Outer Join | 72.3758 | 6120 | 102 | 60.000 | 0 | 224 | 224 |  |
| 214 | 213 | Compute Scalar / Compute Scalar | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 215 | 214 | Compute Scalar / Compute Scalar | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 216 | 215 | Stream Aggregate / Aggregate | 32 | 3264 | 102 | 32.000 | 0 | 117 | 117 |  |
| 217 | 216 | Sort / Sort | 32.6143 | 3264 | 102 | 32.000 | 0 | 116 | 116 |  |
| 218 | 217 | Compute Scalar / Compute Scalar | 32.6143 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 219 | 218 | Filter / Filter | 32.6143 | 3264 | 102 | 32.000 | 0 | 111 | 111 |  |
| 220 | 219 | Nested Loops / Left Outer Join | 32.6143 | 3264 | 102 | 32.000 | 0 | 110 | 110 |  |
| 222 | 220 | Clustered Index Scan / Clustered Index Scan | 1.0192 | 102 | 102 | 1.000 | 141678 | 110 | 110 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 223 | 220 | Constant Scan / Constant Scan | 32 | 3264 | 102 | 32.000 | 0 | 0 | 0 |  |
| 224 | 213 | Hash Match / Right Outer Join | 51.4991 | 6120 | 102 | 60.000 | 0 | 95 | 95 |  |
| 225 | 224 | Compute Scalar / Compute Scalar | 25.2 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 226 | 225 | Compute Scalar / Compute Scalar | 25.2 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 227 | 226 | Stream Aggregate / Aggregate | 25.2 | 2856 | 102 | 28.000 | 0 | 34 | 34 |  |
| 228 | 227 | Sort / Sort | 26.4621 | 2856 | 102 | 28.000 | 0 | 33 | 33 |  |
| 229 | 228 | Compute Scalar / Compute Scalar | 26.4621 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 230 | 229 | Filter / Filter | 26.4621 | 2856 | 102 | 28.000 | 0 | 30 | 30 |  |
| 231 | 230 | Nested Loops / Left Outer Join | 29.4023 | 2856 | 102 | 28.000 | 0 | 30 | 30 |  |
| 233 | 231 | Clustered Index Scan / Clustered Index Scan | 1.05008 | 102 | 102 | 1.000 | 24480 | 29 | 29 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 234 | 231 | Constant Scan / Constant Scan | 28 | 2856 | 102 | 28.000 | 0 | 0 | 0 |  |
| 235 | 224 | Hash Match / Right Outer Join | 42.7308 | 6120 | 102 | 60.000 | 0 | 48 | 48 |  |
| 236 | 235 | Compute Scalar / Compute Scalar | 28.8 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 237 | 236 | Compute Scalar / Compute Scalar | 28.8 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 238 | 237 | Stream Aggregate / Aggregate | 28.8 | 3264 | 102 | 32.000 | 0 | 34 | 34 |  |
| 239 | 238 | Sort / Sort | 30.3776 | 3264 | 102 | 32.000 | 0 | 33 | 33 |  |
| 240 | 239 | Compute Scalar / Compute Scalar | 30.3776 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 241 | 240 | Filter / Filter | 30.3776 | 3264 | 102 | 32.000 | 0 | 30 | 30 |  |
| 242 | 241 | Nested Loops / Left Outer Join | 33.7529 | 3264 | 102 | 32.000 | 0 | 30 | 30 |  |
| 244 | 242 | Clustered Index Scan / Clustered Index Scan | 1.05478 | 102 | 102 | 1.000 | 27948 | 30 | 30 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 245 | 242 | Constant Scan / Constant Scan | 32 | 3264 | 102 | 32.000 | 0 | 0 | 0 |  |
| 246 | 235 | Index Seek / Index Seek | 39.2506 | 6120 | 102 | 60.000 | 408 | 5 | 5 | [parcela] [UQ_parcela_material_numero] |
| 247 | 200 | Nested Loops / Left Outer Join | 46.4316 | 6120 | 102 | 60.000 | 0 | 154 | 154 |  |
| 248 | 247 | Index Seek / Index Seek | 39.2506 | 6120 | 102 | 60.000 | 408 | 3 | 3 | [parcela] [UQ_parcela_material_numero] |
| 250 | 247 | Table Spool / Lazy Spool | 21.8836 | 367200 | 6120 | 60.000 | 24277 | 136 | 136 |  |
| 251 | 250 | Compute Scalar / Compute Scalar | 21.8836 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 252 | 251 | Nested Loops / Inner Join | 21.8836 | 6120 | 102 | 60.000 | 0 | 98 | 98 |  |
| 253 | 252 | Filter / Filter | 33.4521 | 6120 | 102 | 60.000 | 0 | 92 | 92 |  |
| 254 | 253 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 255 | 254 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 89 | 89 |  |
| 256 | 255 | Window Spool / Window Spool | 406 | 51000 | 102 | 500.000 | 0 | 78 | 78 |  |
| 257 | 256 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 67 | 67 |  |
| 258 | 257 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 259 | 258 | Sequence Project / Compute Scalar | 203 | 28560 | 102 | 280.000 | 0 | 65 | 65 |  |
| 260 | 259 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 62 | 62 |  |
| 261 | 260 | Sort / Sort | 203 | 28560 | 102 | 280.000 | 0 | 60 | 60 |  |
| 262 | 261 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 50 | 50 |  |
| 263 | 262 | Sort / Sort | 978 | 99756 | 102 | 978.000 | 0 | 38 | 38 |  |
| 264 | 263 | Clustered Index Scan / Clustered Index Scan | 978 | 99756 | 102 | 978.000 | 5508 | 14 | 14 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 265 | 252 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 4 | 4 | [parcela] [PK__parcela__3213E83FD67044CB] |
## timeline_102d_sulf_p7_actualplan.sqlplan

```json
{
  "StatementText": "WITH fechas AS (\n    SELECT CAST(@P1 AS date) AS fecha\n    UNION ALL SELECT DATEADD(day,1,fecha) FROM fechas WHERE fecha<CAST(@P2 AS date)\n    ) SELECT e.fecha,e.pad_id,e.parcela_id,e.numero_parcela,e.campana_id,e.numero_campana,e.estado_operacional,e.calidad_estado,e.tiene_dato_riego,e.riego_activo,e.tiene_dato_drenaje,e.drenaje_activo\n    FROM fechas d CROSS APPLY inventar_SpcHidr.fn_estado_operacional_parcela_diario(d.fecha) e\n    WHERE e.pad_id=@P3 AND e.parcela_id=@P4\n    ORDER BY e.fecha OPTION (MAXRECURSION 32767)",
  "StatementId": "1",
  "StatementCompId": "1",
  "StatementType": "SELECT",
  "RetrievedFromCache": "true",
  "StatementSubTreeCost": "9.29993",
  "StatementEstRows": "11.5043",
  "SecurityPolicyApplied": "false",
  "StatementOptmLevel": "FULL",
  "QueryHash": "0xDC6F7FA1FB43E983",
  "QueryPlanHash": "0x75F647FB677DE496",
  "StatementOptmEarlyAbortReason": "TimeOut",
  "CardinalityEstimationModelVersion": "140"
}
```

| Nodo | Padre | Operador | Est filas | Real total | Ejecuciones | Real/ejec | IO lógico | CPU ms | Elapsed ms | Objeto |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | — | Compute Scalar / Compute Scalar | 11.5043 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 1 | 0 | Filter / Filter | 11.5043 | 102 | 1 | 102.000 | 0 | 70729 | 70733 |  |
| 2 | 1 | Nested Loops / Inner Join | 449.1 | 6120 | 1 | 6120.000 | 0 | 70728 | 70732 |  |
| 3 | 2 | Sort / Sort | 4 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 4 | 3 | Index Spool / Lazy Spool | 4 | 102 | 1 | 102.000 | 205 | 0 | 0 |  |
| 5 | 4 | Concatenation / Concatenation | 4 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 6 | 5 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 7 | 6 | Constant Scan / Constant Scan | 1 | 1 | 1 | 1.000 | 0 | 0 | 0 |  |
| 8 | 5 | Assert / Assert | 4 | 101 | 1 | 101.000 | 0 | 0 | 0 |  |
| 9 | 8 | Nested Loops / Inner Join | 4 | 101 | 1 | 101.000 | 0 | 0 | 0 |  |
| 10 | 9 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 11 | 10 | Table Spool / Lazy Spool | 1 | 102 | 1 | 102.000 | 0 | 0 | 0 |  |
| 12 | 9 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 13 | 12 | Filter / Filter | 1 | 101 | 102 | 0.990 | 0 | 0 | 0 |  |
| 14 | 13 | Constant Scan / Constant Scan | 1 | 101 | 101 | 1.000 | 0 | 0 | 0 |  |
| 15 | 2 | Table Spool / Lazy Spool | 112.275 | 6120 | 102 | 60.000 | 12241 | 70722 | 70726 |  |
| 16 | 15 | Hash Match / Right Outer Join | 112.275 | 6120 | 102 | 60.000 | 0 | 70712 | 70716 |  |
| 17 | 16 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 18 | 17 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 19 | 18 | Stream Aggregate / Aggregate | 1 | 6120 | 102 | 60.000 | 0 | 70179 | 70183 |  |
| 20 | 19 | Sort / Sort | 12 | 6271 | 102 | 61.480 | 0 | 70175 | 70178 |  |
| 21 | 20 | Compute Scalar / Compute Scalar | 12 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 22 | 21 | Stream Aggregate / Aggregate | 12 | 6271 | 102 | 61.480 | 0 | 70170 | 70174 |  |
| 23 | 22 | Sort / Sort | 78.0066 | 20548 | 102 | 201.451 | 0 | 70167 | 70170 |  |
| 24 | 23 | Compute Scalar / Compute Scalar | 78.0066 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 25 | 24 | Nested Loops / Left Outer Join | 78.0066 | 20548 | 102 | 201.451 | 0 | 70116 | 70120 |  |
| 26 | 25 | Nested Loops / Left Outer Join | 76.3406 | 20548 | 102 | 201.451 | 0 | 8498 | 8498 |  |
| 27 | 26 | Nested Loops / Inner Join | 105.645 | 20548 | 102 | 201.451 | 0 | 372 | 372 |  |
| 29 | 27 | Nested Loops / Inner Join | 105.645 | 20855 | 102 | 204.461 | 0 | 289 | 289 |  |
| 30 | 29 | Nested Loops / Inner Join | 21.8836 | 6120 | 102 | 60.000 | 0 | 199 | 199 |  |
| 31 | 30 | Filter / Filter | 33.4521 | 6120 | 102 | 60.000 | 0 | 170 | 170 |  |
| 32 | 31 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 164 | 164 |  |
| 33 | 32 | Window Spool / Window Spool | 406 | 51000 | 102 | 500.000 | 0 | 129 | 129 |  |
| 34 | 33 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 90 | 90 |  |
| 35 | 34 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 36 | 35 | Sequence Project / Compute Scalar | 203 | 28560 | 102 | 280.000 | 0 | 85 | 85 |  |
| 37 | 36 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 77 | 77 |  |
| 38 | 37 | Sort / Sort | 203 | 28560 | 102 | 280.000 | 0 | 70 | 70 |  |
| 39 | 38 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 40 | 40 |  |
| 40 | 39 | Sort / Sort | 978 | 99756 | 102 | 978.000 | 0 | 32 | 32 |  |
| 41 | 40 | Clustered Index Scan / Clustered Index Scan | 978 | 99756 | 102 | 978.000 | 5508 | 11 | 11 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 42 | 30 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 20 | 20 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 43 | 29 | Index Seek / Index Seek | 4.82759 | 20855 | 6120 | 3.408 | 12240 | 84 | 84 | [campana_parcela_control] [UQ_campana_parcela_control] |
| 45 | 27 | Clustered Index Seek / Clustered Index Seek | 31.7259 | 20548 | 20855 | 0.985 | 40398 | 50 | 50 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 46 | 26 | Index Spool / Lazy Spool | 1 | 20548 | 20548 | 1.000 | 77813 | 8054 | 8055 |  |
| 47 | 46 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 48 | 47 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 7887 | 7888 |  |
| 49 | 48 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 4878 | 4878 |  |
| 50 | 49 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 1763 | 1763 |  |
| 51 | 50 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 941 | 941 |  |
| 52 | 51 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 15 | 15 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 53 | 51 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 54 | 53 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 55 | 54 | Stream Aggregate / Aggregate | 1 | 3264 | 6120 | 0.533 | 0 | 916 | 916 |  |
| 56 | 55 | Filter / Filter | 3.03579 | 3264 | 6120 | 0.533 | 0 | 910 | 910 |  |
| 57 | 56 | Nested Loops / Left Outer Join | 32 | 104448 | 6120 | 17.067 | 0 | 893 | 893 |  |
| 58 | 57 | Filter / Filter | 1 | 3264 | 6120 | 0.533 | 0 | 880 | 880 |  |
| 60 | 58 | Clustered Index Scan / Clustered Index Scan | 1 | 3264 | 3264 | 1.000 | 894336 | 874 | 874 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 61 | 57 | Constant Scan / Constant Scan | 32 | 104448 | 3264 | 32.000 | 0 | 2 | 2 |  |
| 62 | 50 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 63 | 62 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 64 | 63 | Stream Aggregate / Aggregate | 1 | 2856 | 6120 | 0.467 | 0 | 810 | 810 |  |
| 65 | 64 | Filter / Filter | 2.65631 | 2856 | 6120 | 0.467 | 0 | 804 | 804 |  |
| 66 | 65 | Nested Loops / Left Outer Join | 28 | 79968 | 6120 | 13.067 | 0 | 790 | 790 |  |
| 67 | 66 | Filter / Filter | 1 | 2856 | 6120 | 0.467 | 0 | 779 | 779 |  |
| 69 | 67 | Clustered Index Scan / Clustered Index Scan | 1 | 2856 | 2856 | 1.000 | 685440 | 775 | 775 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 70 | 66 | Constant Scan / Constant Scan | 28 | 79968 | 2856 | 28.000 | 0 | 2 | 2 |  |
| 71 | 49 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 72 | 71 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 73 | 72 | Stream Aggregate / Aggregate | 1 | 3264 | 6120 | 0.533 | 0 | 3097 | 3097 |  |
| 74 | 73 | Filter / Filter | 3.2 | 3264 | 6120 | 0.533 | 0 | 3089 | 3089 |  |
| 75 | 74 | Nested Loops / Left Outer Join | 32 | 104448 | 6120 | 17.067 | 0 | 3049 | 3049 |  |
| 76 | 75 | Filter / Filter | 1 | 3264 | 6120 | 0.533 | 0 | 3035 | 3035 |  |
| 78 | 76 | Clustered Index Scan / Clustered Index Scan | 1 | 3264 | 3264 | 1.000 | 4.5337e+06 | 3030 | 3030 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 79 | 75 | Constant Scan / Constant Scan | 32 | 104448 | 3264 | 32.000 | 0 | 2 | 2 |  |
| 80 | 48 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 81 | 80 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 82 | 81 | Stream Aggregate / Aggregate | 1 | 2856 | 6120 | 0.467 | 0 | 2990 | 2990 |  |
| 83 | 82 | Filter / Filter | 2.8 | 2856 | 6120 | 0.467 | 0 | 2983 | 2983 |  |
| 84 | 83 | Nested Loops / Left Outer Join | 28 | 79968 | 6120 | 13.067 | 0 | 2950 | 2950 |  |
| 85 | 84 | Filter / Filter | 1 | 2856 | 6120 | 0.467 | 0 | 2937 | 2938 |  |
| 87 | 85 | Clustered Index Scan / Clustered Index Scan | 1 | 2856 | 2856 | 1.000 | 4.11264e+06 | 2933 | 2933 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 88 | 84 | Constant Scan / Constant Scan | 28 | 79968 | 2856 | 28.000 | 0 | 2 | 2 |  |
| 89 | 25 | Index Spool / Lazy Spool | 1 | 20548 | 20548 | 1.000 | 77813 | 61328 | 61332 |  |
| 90 | 89 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 91 | 90 | Nested Loops / Left Outer Join | 1.00494 | 6120 | 6120 | 1.000 | 0 | 61132 | 61136 |  |
| 92 | 91 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 45688 | 45691 |  |
| 93 | 92 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 27020 | 27021 |  |
| 94 | 93 | Nested Loops / Left Outer Join | 1 | 6120 | 6120 | 1.000 | 0 | 16739 | 16740 |  |
| 95 | 94 | Nested Loops / Inner Join | 1 | 6120 | 6120 | 1.000 | 0 | 3857 | 3858 |  |
| 96 | 95 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 29 | 29 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 97 | 95 | Filter / Filter | 1 | 6120 | 6120 | 1.000 | 0 | 3822 | 3822 |  |
| 98 | 97 | Stream Aggregate / Aggregate | 203 | 862008 | 6120 | 140.851 | 0 | 3760 | 3760 |  |
| 99 | 98 | Window Spool / Window Spool | 406 | 1.54388e+06 | 6120 | 252.267 | 0 | 3522 | 3523 |  |
| 100 | 99 | Segment / Segment | 203 | 879860 | 6120 | 143.768 | 0 | 3202 | 3202 |  |
| 101 | 100 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 102 | 101 | Sequence Project / Compute Scalar | 203 | 879860 | 6120 | 143.768 | 0 | 3145 | 3145 |  |
| 103 | 102 | Segment / Segment | 203 | 879860 | 6120 | 143.768 | 0 | 3067 | 3067 |  |
| 104 | 103 | Sort / Sort | 203 | 879860 | 6120 | 143.768 | 0 | 3008 | 3008 |  |
| 105 | 104 | Stream Aggregate / Aggregate | 203 | 1.7136e+06 | 6120 | 280.000 | 0 | 2606 | 2606 |  |
| 106 | 105 | Sort / Sort | 978 | 5.98536e+06 | 6120 | 978.000 | 0 | 2067 | 2067 |  |
| 107 | 106 | Clustered Index Scan / Clustered Index Scan | 978 | 5.98536e+06 | 6120 | 978.000 | 330480 | 747 | 747 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 108 | 94 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 109 | 108 | Stream Aggregate / Aggregate | 1 | 3228 | 6120 | 0.527 | 0 | 12853 | 12854 |  |
| 110 | 109 | Filter / Filter | 32.5849 | 821352 | 6120 | 134.208 | 0 | 12758 | 12758 |  |
| 111 | 110 | Nested Loops / Left Outer Join | 594.916 | 3.59209e+07 | 6120 | 5869.427 | 0 | 8213 | 8213 |  |
| 112 | 111 | Nested Loops / Inner Join | 18.5911 | 1.12253e+06 | 6120 | 183.420 | 0 | 5485 | 5485 |  |
| 113 | 112 | Nested Loops / Inner Join | 1 | 3264 | 6120 | 0.533 | 0 | 1023 | 1023 |  |
| 114 | 113 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 6120 | 0.533 | 12240 | 46 | 46 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 115 | 113 | Nested Loops / Inner Join | 1 | 3264 | 3264 | 1.000 | 0 | 967 | 967 |  |
| 116 | 115 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 3264 | 1.000 | 6528 | 14 | 14 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 117 | 115 | Filter / Filter | 1 | 3264 | 3264 | 1.000 | 0 | 945 | 945 |  |
| 118 | 117 | Stream Aggregate / Aggregate | 165.7 | 255444 | 3264 | 78.261 | 0 | 926 | 926 |  |
| 119 | 118 | Window Spool / Window Spool | 331.399 | 460260 | 3264 | 141.011 | 0 | 840 | 840 |  |
| 120 | 119 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 724 | 724 |  |
| 121 | 120 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 122 | 121 | Sequence Project / Compute Scalar | 165.7 | 264864 | 3264 | 81.147 | 0 | 708 | 708 |  |
| 123 | 122 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 685 | 685 |  |
| 124 | 123 | Sort / Sort | 165.7 | 264864 | 3264 | 81.147 | 0 | 668 | 668 |  |
| 125 | 124 | Stream Aggregate / Aggregate | 165.7 | 456960 | 3264 | 140.000 | 0 | 518 | 518 |  |
| 126 | 125 | Sort / Sort | 289.489 | 910656 | 3264 | 279.000 | 0 | 419 | 419 |  |
| 127 | 126 | Clustered Index Scan / Clustered Index Scan | 289.489 | 910656 | 3264 | 279.000 | 176256 | 207 | 207 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 128 | 112 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 129 | 128 | Clustered Index Scan / Clustered Index Scan | 3774 | 1.23183e+07 | 3264 | 3774.000 | 894336 | 3803 | 3804 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 130 | 111 | Constant Scan / Constant Scan | 32 | 3.59209e+07 | 1.12253e+06 | 32.000 | 0 | 760 | 760 |  |
| 131 | 93 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 132 | 131 | Stream Aggregate / Aggregate | 1 | 2833 | 6120 | 0.463 | 0 | 10240 | 10241 |  |
| 133 | 132 | Filter / Filter | 28.5118 | 676948 | 6120 | 110.612 | 0 | 10164 | 10165 |  |
| 134 | 133 | Nested Loops / Left Outer Join | 520.552 | 2.51926e+07 | 6120 | 4116.444 | 0 | 7108 | 7109 |  |
| 135 | 134 | Nested Loops / Inner Join | 18.5911 | 899737 | 6120 | 147.016 | 0 | 5182 | 5182 |  |
| 136 | 135 | Nested Loops / Inner Join | 1 | 2856 | 6120 | 0.467 | 0 | 1273 | 1273 |  |
| 137 | 136 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 6120 | 0.467 | 12240 | 40 | 40 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 138 | 136 | Nested Loops / Inner Join | 1 | 2856 | 2856 | 1.000 | 0 | 1223 | 1223 |  |
| 139 | 138 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 2856 | 1.000 | 5712 | 13 | 13 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 140 | 138 | Filter / Filter | 1 | 2856 | 2856 | 1.000 | 0 | 1204 | 1204 |  |
| 141 | 140 | Stream Aggregate / Aggregate | 202.44 | 206724 | 2856 | 72.382 | 0 | 1188 | 1188 |  |
| 142 | 141 | Window Spool / Window Spool | 404.88 | 375226 | 2856 | 131.382 | 0 | 1119 | 1119 |  |
| 143 | 142 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1025 | 1025 |  |
| 144 | 143 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 145 | 144 | Sequence Project / Compute Scalar | 202.44 | 214850 | 2856 | 75.228 | 0 | 1012 | 1012 |  |
| 146 | 145 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 993 | 993 |  |
| 147 | 146 | Sort / Sort | 202.44 | 214850 | 2856 | 75.228 | 0 | 980 | 980 |  |
| 148 | 147 | Stream Aggregate / Aggregate | 202.44 | 399840 | 2856 | 140.000 | 0 | 844 | 844 |  |
| 149 | 148 | Sort / Sort | 689.51 | 1.99634e+06 | 2856 | 699.000 | 0 | 677 | 677 |  |
| 150 | 149 | Clustered Index Scan / Clustered Index Scan | 689.51 | 1.99634e+06 | 2856 | 699.000 | 154224 | 250 | 250 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 151 | 135 | Compute Scalar / Compute Scalar | 3774 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 152 | 151 | Clustered Index Scan / Clustered Index Scan | 3774 | 1.07785e+07 | 2856 | 3774.000 | 685440 | 3361 | 3361 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 153 | 134 | Constant Scan / Constant Scan | 28 | 2.51926e+07 | 899737 | 28.000 | 0 | 539 | 539 |  |
| 154 | 92 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 155 | 154 | Stream Aggregate / Aggregate | 1 | 3228 | 6120 | 0.527 | 0 | 18626 | 18627 |  |
| 156 | 155 | Filter / Filter | 35.7536 | 800910 | 6120 | 130.868 | 0 | 18514 | 18515 |  |
| 157 | 156 | Nested Loops / Left Outer Join | 652.768 | 3.60232e+07 | 6120 | 5886.149 | 0 | 11216 | 11217 |  |
| 158 | 157 | Nested Loops / Inner Join | 20.399 | 1.12573e+06 | 6120 | 183.942 | 0 | 8478 | 8479 |  |
| 159 | 158 | Nested Loops / Inner Join | 1 | 3264 | 6120 | 0.533 | 0 | 1153 | 1153 |  |
| 160 | 159 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 6120 | 0.533 | 12240 | 38 | 38 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 161 | 159 | Nested Loops / Inner Join | 1 | 3264 | 3264 | 1.000 | 0 | 1104 | 1104 |  |
| 162 | 161 | Clustered Index Seek / Clustered Index Seek | 1 | 3264 | 3264 | 1.000 | 6528 | 11 | 11 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 163 | 161 | Filter / Filter | 1 | 3264 | 3264 | 1.000 | 0 | 1085 | 1085 |  |
| 164 | 163 | Stream Aggregate / Aggregate | 165.7 | 255444 | 3264 | 78.261 | 0 | 1065 | 1065 |  |
| 165 | 164 | Window Spool / Window Spool | 331.399 | 460260 | 3264 | 141.011 | 0 | 979 | 979 |  |
| 166 | 165 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 856 | 856 |  |
| 167 | 166 | Compute Scalar / Compute Scalar | 165.7 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 168 | 167 | Sequence Project / Compute Scalar | 165.7 | 264864 | 3264 | 81.147 | 0 | 839 | 839 |  |
| 169 | 168 | Segment / Segment | 165.7 | 264864 | 3264 | 81.147 | 0 | 814 | 814 |  |
| 170 | 169 | Sort / Sort | 165.7 | 264864 | 3264 | 81.147 | 0 | 796 | 796 |  |
| 171 | 170 | Stream Aggregate / Aggregate | 165.7 | 456960 | 3264 | 140.000 | 0 | 628 | 628 |  |
| 172 | 171 | Sort / Sort | 289.489 | 910656 | 3264 | 279.000 | 0 | 527 | 527 |  |
| 173 | 172 | Clustered Index Scan / Clustered Index Scan | 289.489 | 910656 | 3264 | 279.000 | 176256 | 274 | 274 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 174 | 158 | Compute Scalar / Compute Scalar | 4141 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 175 | 174 | Clustered Index Scan / Clustered Index Scan | 4141 | 1.35162e+07 | 3264 | 4141.000 | 4.5337e+06 | 6330 | 6330 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 176 | 157 | Constant Scan / Constant Scan | 32 | 3.60232e+07 | 1.12573e+06 | 32.000 | 0 | 769 | 769 |  |
| 177 | 91 | Compute Scalar / Compute Scalar | 1 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 178 | 177 | Stream Aggregate / Aggregate | 1 | 2833 | 6120 | 0.463 | 0 | 15397 | 15398 |  |
| 179 | 178 | Filter / Filter | 32.4176 | 661015 | 6120 | 108.009 | 0 | 15305 | 15305 |  |
| 180 | 179 | Nested Loops / Left Outer Join | 591.862 | 2.52632e+07 | 6120 | 4127.973 | 0 | 10110 | 10111 |  |
| 181 | 180 | Nested Loops / Inner Join | 21.1379 | 902257 | 6120 | 147.428 | 0 | 8160 | 8160 |  |
| 182 | 181 | Nested Loops / Inner Join | 1 | 2856 | 6120 | 0.467 | 0 | 1370 | 1370 |  |
| 183 | 182 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 6120 | 0.467 | 12240 | 45 | 45 | [parcela] [PK__parcela__3213E83FD67044CB] |
| 184 | 182 | Nested Loops / Inner Join | 1 | 2856 | 2856 | 1.000 | 0 | 1314 | 1315 |  |
| 185 | 184 | Clustered Index Seek / Clustered Index Seek | 1 | 2856 | 2856 | 1.000 | 5712 | 10 | 10 | [pad] [PK__pad__6FCA2A7CCF7F4CCC] |
| 186 | 184 | Filter / Filter | 1 | 2856 | 2856 | 1.000 | 0 | 1298 | 1298 |  |
| 187 | 186 | Stream Aggregate / Aggregate | 202.44 | 206724 | 2856 | 72.382 | 0 | 1282 | 1282 |  |
| 188 | 187 | Window Spool / Window Spool | 404.88 | 375226 | 2856 | 131.382 | 0 | 1211 | 1211 |  |
| 189 | 188 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1110 | 1110 |  |
| 190 | 189 | Compute Scalar / Compute Scalar | 202.44 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 191 | 190 | Sequence Project / Compute Scalar | 202.44 | 214850 | 2856 | 75.228 | 0 | 1096 | 1096 |  |
| 192 | 191 | Segment / Segment | 202.44 | 214850 | 2856 | 75.228 | 0 | 1075 | 1075 |  |
| 193 | 192 | Sort / Sort | 202.44 | 214850 | 2856 | 75.228 | 0 | 1060 | 1060 |  |
| 194 | 193 | Stream Aggregate / Aggregate | 202.44 | 399840 | 2856 | 140.000 | 0 | 919 | 919 |  |
| 195 | 194 | Sort / Sort | 689.51 | 1.99634e+06 | 2856 | 699.000 | 0 | 751 | 751 |  |
| 196 | 195 | Clustered Index Scan / Clustered Index Scan | 689.51 | 1.99634e+06 | 2856 | 699.000 | 154224 | 289 | 289 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 197 | 181 | Compute Scalar / Compute Scalar | 4291 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 198 | 197 | Clustered Index Scan / Clustered Index Scan | 4291 | 1.22551e+07 | 2856 | 4291.000 | 4.11264e+06 | 5905 | 5906 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 199 | 180 | Constant Scan / Constant Scan | 28 | 2.52632e+07 | 902257 | 28.000 | 0 | 546 | 546 |  |
| 200 | 16 | Hash Match / Right Outer Join | 111.726 | 6120 | 102 | 60.000 | 0 | 514 | 514 |  |
| 201 | 200 | Compute Scalar / Compute Scalar | 101.173 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 202 | 201 | Hash Match / Right Outer Join | 101.173 | 6120 | 102 | 60.000 | 0 | 348 | 348 |  |
| 203 | 202 | Compute Scalar / Compute Scalar | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 204 | 203 | Compute Scalar / Compute Scalar | 28 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 205 | 204 | Stream Aggregate / Aggregate | 28 | 2856 | 102 | 28.000 | 0 | 116 | 116 |  |
| 206 | 205 | Sort / Sort | 28.4846 | 2856 | 102 | 28.000 | 0 | 116 | 116 |  |
| 207 | 206 | Compute Scalar / Compute Scalar | 28.4846 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 208 | 207 | Filter / Filter | 28.4846 | 2856 | 102 | 28.000 | 0 | 110 | 110 |  |
| 209 | 208 | Nested Loops / Left Outer Join | 28.4846 | 2856 | 102 | 28.000 | 0 | 110 | 110 |  |
| 211 | 209 | Clustered Index Scan / Clustered Index Scan | 1.01731 | 102 | 102 | 1.000 | 146880 | 109 | 109 | [drena_concentrados_sulfuro] [PK_drena_concentrados_sulfuro] |
| 212 | 209 | Constant Scan / Constant Scan | 28 | 2856 | 102 | 28.000 | 0 | 0 | 0 |  |
| 213 | 202 | Hash Match / Right Outer Join | 72.3758 | 6120 | 102 | 60.000 | 0 | 217 | 217 |  |
| 214 | 213 | Compute Scalar / Compute Scalar | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 215 | 214 | Compute Scalar / Compute Scalar | 32 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 216 | 215 | Stream Aggregate / Aggregate | 32 | 3264 | 102 | 32.000 | 0 | 113 | 113 |  |
| 217 | 216 | Sort / Sort | 32.6143 | 3264 | 102 | 32.000 | 0 | 112 | 112 |  |
| 218 | 217 | Compute Scalar / Compute Scalar | 32.6143 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 219 | 218 | Filter / Filter | 32.6143 | 3264 | 102 | 32.000 | 0 | 107 | 107 |  |
| 220 | 219 | Nested Loops / Left Outer Join | 32.6143 | 3264 | 102 | 32.000 | 0 | 107 | 107 |  |
| 222 | 220 | Clustered Index Scan / Clustered Index Scan | 1.0192 | 102 | 102 | 1.000 | 141678 | 106 | 106 | [drena_concentrados_oxido] [PK_drena_concentrados_oxido] |
| 223 | 220 | Constant Scan / Constant Scan | 32 | 3264 | 102 | 32.000 | 0 | 0 | 0 |  |
| 224 | 213 | Hash Match / Right Outer Join | 51.4991 | 6120 | 102 | 60.000 | 0 | 91 | 91 |  |
| 225 | 224 | Compute Scalar / Compute Scalar | 25.2 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 226 | 225 | Compute Scalar / Compute Scalar | 25.2 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 227 | 226 | Stream Aggregate / Aggregate | 25.2 | 2856 | 102 | 28.000 | 0 | 33 | 33 |  |
| 228 | 227 | Sort / Sort | 26.4621 | 2856 | 102 | 28.000 | 0 | 32 | 32 |  |
| 229 | 228 | Compute Scalar / Compute Scalar | 26.4621 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 230 | 229 | Filter / Filter | 26.4621 | 2856 | 102 | 28.000 | 0 | 29 | 29 |  |
| 231 | 230 | Nested Loops / Left Outer Join | 29.4023 | 2856 | 102 | 28.000 | 0 | 29 | 29 |  |
| 233 | 231 | Clustered Index Scan / Clustered Index Scan | 1.05008 | 102 | 102 | 1.000 | 24480 | 28 | 28 | [flujos_reales_sulfuro] [PK_flujos_reales_sulfuro] |
| 234 | 231 | Constant Scan / Constant Scan | 28 | 2856 | 102 | 28.000 | 0 | 0 | 0 |  |
| 235 | 224 | Hash Match / Right Outer Join | 42.7308 | 6120 | 102 | 60.000 | 0 | 46 | 46 |  |
| 236 | 235 | Compute Scalar / Compute Scalar | 28.8 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 237 | 236 | Compute Scalar / Compute Scalar | 28.8 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 238 | 237 | Stream Aggregate / Aggregate | 28.8 | 3264 | 102 | 32.000 | 0 | 33 | 33 |  |
| 239 | 238 | Sort / Sort | 30.3776 | 3264 | 102 | 32.000 | 0 | 32 | 32 |  |
| 240 | 239 | Compute Scalar / Compute Scalar | 30.3776 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 241 | 240 | Filter / Filter | 30.3776 | 3264 | 102 | 32.000 | 0 | 29 | 29 |  |
| 242 | 241 | Nested Loops / Left Outer Join | 33.7529 | 3264 | 102 | 32.000 | 0 | 29 | 29 |  |
| 244 | 242 | Clustered Index Scan / Clustered Index Scan | 1.05478 | 102 | 102 | 1.000 | 27948 | 29 | 29 | [flujos_reales_oxido] [PK_flujos_reales_oxido] |
| 245 | 242 | Constant Scan / Constant Scan | 32 | 3264 | 102 | 32.000 | 0 | 0 | 0 |  |
| 246 | 235 | Index Seek / Index Seek | 39.2506 | 6120 | 102 | 60.000 | 408 | 3 | 3 | [parcela] [UQ_parcela_material_numero] |
| 247 | 200 | Nested Loops / Left Outer Join | 46.4316 | 6120 | 102 | 60.000 | 0 | 151 | 151 |  |
| 248 | 247 | Index Seek / Index Seek | 39.2506 | 6120 | 102 | 60.000 | 408 | 3 | 3 | [parcela] [UQ_parcela_material_numero] |
| 250 | 247 | Table Spool / Lazy Spool | 21.8836 | 367200 | 6120 | 60.000 | 24277 | 134 | 134 |  |
| 251 | 250 | Compute Scalar / Compute Scalar | 21.8836 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 252 | 251 | Nested Loops / Inner Join | 21.8836 | 6120 | 102 | 60.000 | 0 | 96 | 96 |  |
| 253 | 252 | Filter / Filter | 33.4521 | 6120 | 102 | 60.000 | 0 | 90 | 90 |  |
| 254 | 253 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 255 | 254 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 87 | 87 |  |
| 256 | 255 | Window Spool / Window Spool | 406 | 51000 | 102 | 500.000 | 0 | 76 | 76 |  |
| 257 | 256 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 65 | 65 |  |
| 258 | 257 | Compute Scalar / Compute Scalar | 203 | 0 | 0 | 0.000 | 0 | 0 | 0 |  |
| 259 | 258 | Sequence Project / Compute Scalar | 203 | 28560 | 102 | 280.000 | 0 | 63 | 63 |  |
| 260 | 259 | Segment / Segment | 203 | 28560 | 102 | 280.000 | 0 | 61 | 61 |  |
| 261 | 260 | Sort / Sort | 203 | 28560 | 102 | 280.000 | 0 | 59 | 59 |  |
| 262 | 261 | Stream Aggregate / Aggregate | 203 | 28560 | 102 | 280.000 | 0 | 50 | 50 |  |
| 263 | 262 | Sort / Sort | 978 | 99756 | 102 | 978.000 | 0 | 37 | 37 |  |
| 264 | 263 | Clustered Index Scan / Clustered Index Scan | 978 | 99756 | 102 | 978.000 | 5508 | 13 | 13 | [campana_parcela_control] [PK__campana___65F0BA0DEC5C4E31] |
| 265 | 252 | Clustered Index Seek / Clustered Index Seek | 1 | 6120 | 6120 | 1.000 | 12240 | 4 | 4 | [parcela] [PK__parcela__3213E83FD67044CB] |
