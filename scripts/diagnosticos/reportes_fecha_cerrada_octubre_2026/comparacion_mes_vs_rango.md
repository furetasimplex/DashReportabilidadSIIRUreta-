# Mes vs rango

| Caso | Input UI | Parámetros del SELECT de corte | Resultado DEV |
|---|---|---|---|
| Mes octubre | 01-10 a 31-10 | start=01-10/end=31-10 | NULL |
| Personalizado | 01-10 a 03-10 | start=01-10/end=03-10 | NULL |
| Hasta última cerrada de octubre | No existe fecha cerrada de octubre | No se fabrica rango 01-10 a 30-09 | No aplicable |
| Control septiembre | 01-09 a 30-09 | start=01-09/end=30-09 | 30-09 |
| Horizonte global | 1900-01-01 a 9999-12-31 | mismo SELECT | 30-09 |

Mismo helper y concepto de corte; cambia cota superior. No exige mes calendario completo. Para otros rangos personalizados, el editor recalcula desde el primer día del mes de fin, no necesariamente desde el ini visible; hecho de implementación relevante pero no causa de este caso, donde ambos inicios son 01-10.

El control de septiembre confirma únicamente resolución exitosa de fecha; no se afirma que exportación completa pasó, porque producirla refrescaría datos y violaría alcance de solo lectura.
