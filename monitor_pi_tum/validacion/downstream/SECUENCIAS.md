# Secuencias simuladas

A_original=Factor→Cache; B_original=Cache→Factor→Cache. Ambas omiten histórico. A_historico=Histórico→Factor→Cache; B_historico=Histórico→Cache→Factor→Cache. Control_Apilado ya tiene TUM vigente en todas.

Solo tablas temporales de sesión, sin UPDATE/DELETE/INSERT sobre tablas persistentes. Se reutilizan cuerpos SQL vigentes, con destinos y fuentes materializadas desviados a #hist/#factor/#cache/#traza/#srr/#ajuste. El motor ejecutó las mismas fórmulas; no se instalaron SP ni vistas. Se verificaron filas persistentes de histórico/factor/cache/trazabilidad idénticas antes/después y se hizo rollback final. Clays no se refrescó: sus fuentes se mantuvieron constantes para aislar el orden solicitado.

|Secuencia|Factor calculado|Factor reportes|TMH original|TMH ajustado|Persistentes intactos|
|---|---|---|---|---|---|
|A_original|1.0|1.0|71793.0|71793.0|True|
|B_original|1.0|1.0|71793.0|71793.0|True|
|A_historico|0.9983502509529375|0.9983502509529375|83630.0|83492.03148719417|True|
|B_historico|0.9983502509529375|0.9983502509529375|83630.0|83492.03148719417|True|


|Secuencia|Turno|Apilado TMS|STOCK %|MINA %|SRR %|FeS|Malla -1/2|
|---|---|---|---|---|---|---|---|
|A_original|A|39474.224000|78.960000|0.000000|21.040000|0.079497|75.746374|
|A_original|B|40156.926000|60.790000|0.000000|39.210000|0.079378|75.869861|
|B_original|A|39474.224000|78.960000|0.000000|21.040000|0.079497|75.746374|
|B_original|B|40156.926000|60.790000|0.000000|39.210000|0.079378|75.869861|
|A_historico|A|39408.079368|78.920000|0.000000|21.080000|0.079497|75.746374|
|A_historico|B|40089.655081|60.720000|0.000000|39.280000|0.079378|75.869861|
|B_historico|A|39408.079368|78.920000|0.000000|21.080000|0.079497|75.746374|
|B_historico|B|40089.655081|60.720000|0.000000|39.280000|0.079378|75.869861|

