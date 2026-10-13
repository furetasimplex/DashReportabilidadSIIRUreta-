# Prueba de techo diario por edad ? 11 de octubre de 2026

Prototipo aislado en curvas_recon/test_envolvente_edad_prototipo.py. No modifica
ramp_curve.py, recon_engine.py ni los callbacks productivos. Sin SQL.

Hip?tesis ilustrativa: techo lineal de factor de drenaje 0,10 el d?a 1 a 0,99
el d?a 30, estable despu?s. Edad absoluta desde primer riego real. Riego
sint?tico constante 100 unidades por d?a; objetivo PLS semanal 95% del riego.
El prototipo restringe el dial de la familia de curvas existente antes de
resolver el volumen. No corta a posteriori una curva ya reconciliada.

| D?as desde arranque | Factor final actual | Factor final con envolvente | Techo al ?ltimo d?a | Residuo de volumen sint?tico |
|---|---:|---:|---:|---:|
| 1–7 | 79.9% | 25.9% | 28.4% | 536.30 |
| 8–14 | 92.7% | 48.2% | 49.9% | 384.82 |
| 15–21 | 96.2% | 69.0% | 71.4% | 235.31 |
| 22–28 | 96.2% | 85.3% | 92.9% | 109.44 |
| 29–35 | 96.2% | 92.8% | 99.0% | 34.59 |

Resultado: 9 pruebas pasaron. Incluyen alta demanda inicial, cinco ventanas
consecutivas, borde compartido y repetibilidad, objetivo factible con cierre,
d?as sin riego, estado heredado incompatible, residuo negativo por piso,
coincidencia con la curva de continuaci?n sin restricci?n activa despu?s del
d?a 30 y objetivo positivo sin riego.

La envolvente evita la subida r?pida en el ejemplo, pero incrementa el
residuo que debe absorber el resto del pad. Aqu? se prueba su declaraci?n y
el balance local entregado + residuo = objetivo; no se simul? la capacidad
real de las pilas en r?gimen ni el cierre completo del flowsheet. Tampoco
se valida experimentalmente la curva 10%-99%: debe calibrarse con datos.

Si el estado anterior ya supera el nuevo techo, el prototipo exige recalcular
antecedentes; no baja artificialmente el factor heredado. La continuidad en
n=n0 es exacta y el alpha se hereda de la ventana previa.

Reproducir: python -B -m unittest curvas_recon.test_envolvente_edad_prototipo -v
