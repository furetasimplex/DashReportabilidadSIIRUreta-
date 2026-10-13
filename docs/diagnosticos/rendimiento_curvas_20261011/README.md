# Rendimiento de curvas — 2026-10-11

El botón Ejecutar cálculo muestra Calculando… y queda deshabilitado mientras
compute_recon está ejecutándose. Dash running restaura texto y habilitación
al terminar, incluido un error. No se recarga la sección completa.

Se midió Caso 8 de agosto con las entradas reales del perfil DEV y caché local
existente. Guard SELECT-only, save_run sustituido y escrituras de caché
desactivadas; no se guardaron runs ni se ejecutaron SPs.

La primera exploración: casos 2,46 s, preparación inicial 2,21 s,
entradas de ventana 4,40 s, motor y preparación de persistencia 15,95 s,
barras iniciales 3,78 s, gráficos de pila 3,35 s, motor repetido 0,26 s.
No sumar esas etapas como tiempo observado de la UI: sus callbacks pueden
ejecutarse en paralelo y faltan el transporte al navegador y la escritura SQL.

El perfil de funciones identificó sorted sobre fechas de Pandas y el bucle
que indexaba miles de Timestamp para buscar el último hueco de actividad.
Ahora se ordena con sort_values y se calcula el último hueco mediante una
diferencia vectorizada del DatetimeIndex. Se conserva > gap_days, el corte
a la fecha del Caso, el uso de riego+drenaje y el primer riego del bloque.

Comparación antes/después en un mismo proceso, limpiando las cachés de
actividad, campañas, curvas y rampa antes de cada motor, y manteniendo la
misma caché de entradas: 6,7519 s original frente a 1,5783 s vectorizado
(aprox. 77% menos tiempo). Resultados completos idénticos tras normalizar
NaN y serializar ambos resultados. Los tiempos varían con la carga de la
máquina; esto no es una medición del guardado real ni del tiempo total UI.

29 pruebas offline pasaron: actividad/campañas, ensamblado y callbacks HTTP,
incluido contrato running del botón. No se cambió metodología, límites de
drenaje, reparto de Cu, anclas ni esquema/persistencia de SQL.
