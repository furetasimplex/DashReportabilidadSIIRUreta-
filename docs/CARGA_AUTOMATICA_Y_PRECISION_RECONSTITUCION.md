# Reconstitución: carga automática y rendimiento — 27-10-2026

Los Casos oficiales se cargan automáticamente tras abrir la sección mediante un disparo único diferido. No hay botón Actualizar Casos ni consulta SQL dentro de build_layout. Si la selección ya existe en el catálogo se conserva. El cálculo sigue siendo explícito mediante Cargar datos.

Se conserva la hipótesis operativa autorizada de densidad uniforme dentro de cada pad/día. El volumen define la fracción de masa asignada; el pesómetro ubica temporalmente la fracción acumulada de masa húmeda. No se usa tasa de referencia ni se presupone caudal uniforme durante el día. La mayor heterogeneidad posible del stock afecta esa hipótesis de asignación, no se corrige aumentando la frecuencia del pesómetro. No se introdujeron umbrales de stock ni reglas geológicas nuevas.

## Cambio instalado sin reducir precisión

La consulta intraturno anterior transfería dos filas por tick y 16 columnas de diagnóstico. La nueva lee una fila con fecha y los dos contadores, y reconstruye vectorizadamente el mismo contrato y validaciones. Se conserva la resolución de 10 s, las pausas, las anclas, los nulos, duplicados, resets y saltos. La ruta SQL anterior permanece como referencia. LAG no determina el orden dentro de timestamps duplicados; sus diagnósticos secundarios pueden permutar, pero todos quedan invalidados por duplicate y no alimentan el reloj.

También se indexan los intervalos una sola vez por día/turno/correa y se memorizan las vistas por resultado, grupo y rango. Se evita recalcular resúmenes al abrir detalles. No se cachea el resultado completo entre cálculos: cada carga sigue validando su Caso/run y leyendo sus fuentes, evitando devolver una reconciliación anterior.

Mediciones SELECT sobre Caso 10013/run 10145, 01–12 octubre de 2026: lectura+cálculo 80,165 s antes y 16,833 s después; etapa intraturno 78,099 s antes y 3,234 s después. Son observaciones de dos ejecuciones, no una garantía de latencia. La consulta de perfil/ humedad quedó como principal costo (14,742 s en la segunda ejecución).

Una comparación SQL independiente del 06-10-2026 verificó los 17.280 registros y todos los valores del contrato: original 8,677 s y compacto 2,009 s. La mejora local de indexación produjo 16 DataFrames exactamente iguales a la referencia en 10009; mediana Python 0,638 a 0,532 s. El montaje, los gráficos, los informes y los guards de selección siguen funcionando sin SQL de QA.

## Alternativas comparadas, todavía experimentales

Se compararon seis cambios interiores con referencia válida en el Caso 10013. En el Caso 10009 el cambio interior disponible no pasa la validación de su perfil de referencia y no se usó para medir error horario.

| Lectura experimental | Error mediano | Error máximo |
|---|---:|---:|
| Horaria, interpolación local | 0,300 min | 6,032 min |
| Cada 15 min, interpolación local | 0,056 min | 2,342 min |
| Horaria + detalle 10 s solo en la ventana del cambio | 0,000 min | 0,000 min |

En esta muestra, seis ventanas deduplicadas necesitaron 4.320 intervalos detallados. Sumando los perfiles horarios y anclas, el costo estimado es 4.908 registros frente a 207.360 del perfil expandido completo (aproximadamente 2,37 %). Es una simulación offline de lecturas; no se implementó ni midió esta estrategia SQL. Una lectura horaria puede diluir pausas dentro de una hora con masa positiva; un bucket totalmente en cero permanece en cero. El refinamiento local es la alternativa recomendada para experimentar, sin alterar la asignación de masa.

Evidencia reproducible y comparación HTML: `../curvas_recon/auditorias/reconstitucion_auto_perf_20261027/`. La hipótesis de densidad no cambia por elegir otra frecuencia de lectura.
