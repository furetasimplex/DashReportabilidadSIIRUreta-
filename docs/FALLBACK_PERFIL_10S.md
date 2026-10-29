# Fallback del perfil de 10 segundos — 27-10-2026

Instalado en `reconstitucion/engine.py` mediante `_optional_intraday`, usado en las rutas del Caso y de la fuente histórica.

1. Con bloques de 10 s completos y válidos, el reloj usa el acumulado validado.
2. Si la lectura opcional falla, devuelve None o queda vacía, el cálculo continúa desde TMH por turnos A/B. Un aviso seguro queda disponible en Consideraciones; no se incorpora el texto de la excepción SQL o de conexión.
3. Si faltan días o bloques, hay gaps, resets, duplicados, nulos o discrepancia con TMH, el validador existente selecciona A/B para la fecha afectada. Cada fila conserva origen, resolución y motivo; no se presenta como hora observada de 10 s.
4. El respaldo interpola masa acumulada uniformemente dentro del turno de 12 h. No usa tasa de referencia y no modifica las masas seca/húmeda asignadas por volumen.
5. Un turno A/B medido en cero se conserva en cero. Sin perfil A/B válido no se inventa un horario. Los fallos de fuentes obligatorias no se capturan como si fueran una ausencia opcional.

Pruebas offline instaladas en `reconstitucion/test_fallback.py`: error del lector 10 s, None, vacío, fecha ausente, gap, reset, null, duplicate, total incompatible, turno explícito cero, fuente A/B inválida y propagación del error de la fuente obligatoria. Junto con las regresiones de timeline y envoltura de Caso pasaron 18 pruebas. No se consultó SQL para esta verificación.

Este respaldo ya está activo en el código. Las alternativas de leer por hora y refinar solo la ventana del cambio siguen siendo experimentales y no sustituyeron el algoritmo de producción.
