# Prueba condicional de cap — sintética, no estado real DEV

Mismos orígenes IMP reales del 10-09 y mismo histórico actualizado; únicamente la copia temporal del cache arranca con 1000 TMS por turno. Ningún control real 04–10 tiene cap activo. Esta prueba ilustra el riesgo de alimentar el factor con una fotografía insuficiente de apilado.

|Paso|Acción|Factor aplicado|Cache A|Cache B|SRR A|SRR B|Cap A|Cap B|
|---|---|---|---|---|---|---|---|---|
|1|F|0.7147447899457886|1000.000000|1000.000000|1000.0000000000|1000.0000000000|True|True|
|2|C|0.7147447899457886|28037.271781|28525.229478|8307.0000000000|15746.0000000000|False|False|
|3|F|0.9983502509529375|28037.271781|28525.229478|8307.0000000000|15746.0000000000|False|False|
|4|C|0.9983502509529375|39408.079368|40089.655081|8307.0000000000|15746.0000000000|False|False|
|5|F|0.9983502509529375|39408.079368|40089.655081|8307.0000000000|15746.0000000000|False|False|
|6|C|0.9983502509529375|39408.079368|40089.655081|8307.0000000000|15746.0000000000|False|False|


Persistentes idénticos: True. No demuestra convergencia universal.
