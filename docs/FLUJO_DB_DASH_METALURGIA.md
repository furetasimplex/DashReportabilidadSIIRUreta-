# Flujo DB + Dash + metodologia metalurgica
Propuesta operativa revisable - 26-10-2026. No modifica la aplicacion ni la configuracion global.
Base activa: `DashReportabilidadSIIR`; `curvas_recon/integracion_siir` es antecedente historico.
Fuentes leidas: AGENTS de ambos repositorios, NOTAS_CONTINUIDAD, INTEGRACION_CURVAS e INTEGRACION_RECONSTITUCION del activo.

## 1. Abrir una tarea con un contrato corto
Registrar objetivo observable, clase de cambio, archivos permitidos, invariantes, evidencia disponible y condicion de terminado.
Ejemplo: "Cambiar el nombre de tasa diaria en UI y Excel; no alterar numeros ni RL acumulada; revisar strings/diff y un artefacto representativo".
Clasificar por el mayor riesgo afectado:
- Visual/texto: etiquetas, colores, geometria; comparacion de estructura y muestra visual relevante.
- Datos/consulta/cache: identidad, cobertura, fechas, procedencia, invalidacion; contrato de datos y regresion dirigida.
- Metodologia: Cu, recuperacion, rampa, tasa/RL; balance numerico y revision fisica independiente de la implementacion.
Cerrar solo con diff revisado, evidencia verificable y limitaciones explicitas; un acuse de recibo del agente no es una entrega.

## 2. Usar agentes con alcance acotado
El principal conserva integracion, revision y cierre. Cada agente recibe contexto minimo, archivos permitidos, entrada, salida y comprobaciones.
Un entregable debe incluir archivos producidos, diff o ubicacion, pruebas realmente ejecutadas, resultados y pendientes.
Evitar encargar "optimizar todo"; separar diagnostico de una consulta, modificacion de un modulo y revision del balance.
Paralelizar unicamente tareas independientes; un solo responsable por archivo. Revisores pueden trabajar en lectura.
Antes de aplicar un parche, comparar con el archivo activo actual y sus cambios locales; nunca copiar un archivo completo antiguo desde staging.
Despues, comprobar que etiquetas, ejes y cambios recientes ajenos al encargo siguen presentes.
No pedir confirmacion para crear carpetas o ejecutar lecturas y cambios reversibles ya autorizados dentro del alcance.

## 3. Seleccion de modelo propuesta
La preferencia persistente vigente es Luna; la peticion actual permite este encargo en GPT-6.1 Sol.
La tabla siguiente es una propuesta flexible para futuras tareas, pendiente de adopcion explicita; no sustituye sola esa preferencia.
| Modelo | Uso funcional propuesto | Senal para cambiar |
|---|---|---|
| gpt-6-luna | Edicion acotada, extraccion, pruebas dirigidas con contrato conocido | Dos intentos sin avance o ambiguedad de varias capas: pasar contexto minimo a Sol |
| gpt-6.1-sol | Integracion DB/Dash, depuracion transversal, revision de diffs y diseno de contratos | Incertidumbre fisica o contradiccion no resuelta: revision Astra |
| gpt-6-astra | Revision puntual de metodologia y problemas dificiles de identificar | Devolver decision e invariantes; implementacion acotada vuelve a Luna/Sol |
| gpt-6-sol / gpt-5.6-sol | Alternativa disponible cuando la tarea concreta esta verificada con ese modelo | No rotar modelos sin una razon observable |
No se afirman tarifas ni velocidades: evaluar costo operativo por tarea aceptada, no por nombre de modelo.

## 4. Presupuesto orientativo de investigacion
No es un limite global ni autoriza omitir verificaciones necesarias. Revisarlo si aparece evidencia nueva.
| Clase | Primera lectura | Primera salida de herramientas | Rondas de implementacion |
|---|---|---|---|
| Visual | 3-5 archivos/secciones | 2-4 mil tokens | 1 + correccion si falla revision |
| Datos | 5-8 archivos/secciones | 4-8 mil tokens | Diagnostico + cambio + validacion |
| Metodologia | Contrato y fuentes precisas | 6-12 mil tokens | Hipotesis + contraste + revision |
Buscar con `rg` por simbolo/rango; leer secciones actuales y ultimas notas pertinentes, no documentos historicos completos.
Limitar salidas a resumenes y primeras diferencias. Nunca imprimir DataFrames, payloads, AST/repr o JSON completos para inspeccion rutinaria.
Si el arnes falla, registrar excepcion y resumen de entradas; corregir el arnes antes de atribuir un fallo al producto.

## 5. Una base de QA reproducible
Reutilizar primero evidencia existente valida: referencia Caso 10013/run 10145, 01-12 octubre 2026; confirmar que corresponde al cambio.
No repetir por rutina las auditorias ya correctas de 36 pilas activas y 12 grupos.
Crear o localizar un manifiesto: Caso/run/modelo125/ventana, fecha de extraccion, fuentes, cobertura por campana, unidades, hash del snapshot y version del codigo.
Snapshot interno reutilizable fuera de Git; fixtures versionadas pequenas y sin payloads internos ni secretos. No deserializar pickle de origen desconocido.
Conservar fechas anteriores al Caso necesarias para historia y primer riego; un margen de quimica no es un recorte de campana.
Una lectura de QA por fuente/rango/PAD debe alimentar todas las pilas/grupos que la comparten.
Claves de cache incluyen identidad de datos, PAD, inicio y corte; invalidar al cambiar run, ventana o fuente.
Probar offline sobre ese snapshot. Para cambios de datos/metodologia, hacer una confirmacion DB fresca SELECT-only, agrupada por fuentes necesarias, tras estabilizar el cambio.
No significa una unica sentencia SQL: es una pasada de confirmacion, sin repetirla por cada pila o ensayo UI.
Si cambia el run oficial o la cobertura entre snapshot y confirmacion, invalidar esa comparacion y justificar una nueva captura.
Un cambio puramente textual no necesita DB fresca. No presentar resultados offline como validacion de planta actual.
El manifiesto es un objetivo del arnes de QA: el exportador actual aun puede leer historia al exportar; no afirmar que produccion ya congela todas las fuentes.

## 6. Invariantes metalurgicos que no se negocian por rapidez
Pilas dinamicas: OX/SU son nombres de pads con el mismo mineral; no deducir cineticas distintas de esos nombres.
Modelo de referencia con 125 flujos; no sustituirlo por 115/120 sin contrato explicito de version.
Cu recuperado neto = Cu en drenaje - Cu entrante en riego, con unidades y conversiones visibles.
Contrastar objetivos F25 OX/F29 SU; entradas OX 70+60+81 y SU 72+66; drenajes OX 44+45 y SU 47+48+49 segun contrato validado del modelo.
Recuperacion agrupada = sum(Cu recuperado) / sum(Cu apilado); no promedio simple de porcentajes.
Tasa de lixiviacion diaria = 24 * sum(Q_riego(m3/h)) / sum(TMS); RL acumulada = sum(volumen) / TMS desde primer riego, sin reinicio por Caso.
Usar la historia aceptada y Q del Caso en modo reconciliado; conservar procedencia medida/reconciliada. No inventar historia reconciliada previa.
Cero explicito es cero; NaN/ausencia conserva ausencia. No interpolar ni descartar fechas silenciosamente para conseguir una curva continua.
Mascaras de comparacion visual no modifican la fuente ni el balance; conservar calendario y huecos.
Rampa y continuidad se anclan a campana; documentar el limite de estado en memoria por worker cuando corresponda.
Inventario/remanente Cu requiere stock inicial + Cu apilado + Cu de refino - drenaje - Cu retirado; declarar terminos no observados.
Refino predominante es hipotesis autorizada, no quimica medida. No exigir ley residual para obtener el saldo de balance.
En campanas activas separar remanente presente de Cu retirado; no duplicar Cu acuoso ya incluido en el saldo total.
Residuos firmados objetivo-entregado son terminos de cierre; no certifican un inventario fisico disponible.

## 7. Validacion en orden y con criterio de parada
1. Revisar diff y ejecutar import/sintaxis o prueba minima pertinente; comprobar que no entro codigo antiguo.
2. Cambio visual: buscar etiquetas afectadas y verificar una figura/exportacion representativa. No lanzar 62 pruebas por un renombre aislado.
3. Cambio de datos: comprobar claves, bounds, run, cobertura, valores diarios, fechas, ceros/huecos y cache fria/caliente.
4. Cambio metodologico: contrastar Cu diario/acumulado por pila y pad, recuperacion ponderada, TMS, tasa/RL y continuidad entre Casos.
5. Comparar con baseline indicando tolerancias/unidades antes de evaluar; reportar maximo error y primera discrepancia, no volcados completos.
6. Ampliar pruebas solo si cambio otra capa, fallo una prueba o queda una incertidumbre concreta. Repetir una suite ya verde exige una causa.
7. Hacer UI al final con codigo y tests ya estables, una sesion autenticada, selectores por identidad real y espera por estado observable.
8. Reutilizar stores autorizados en memoria; no pulsar Calcular para preparar una prueba visual. Mantener credenciales/sesion fuera de archivos.
9. Si hot reload reinicia el servidor, invalidar ese intento y estabilizar proceso/arnes antes de reintentar; no encadenar tres sesiones a ciegas.
Terminado: comportamiento requerido demostrado, pruebas pertinentes verdes, diff revisado por principal, incertidumbre fisica declarada.
No se exige navegador a un cambio sin comportamiento visual ni una suite completa a toda modificacion reversible.

## 8. Seguridad y autorizacion concretas
DB de auditoria: SELECT-only. Calcular persiste y Actualizar datos puede sincronizar: tratarlos como acciones reales, nunca como lectura de pantalla.
No ejecutar SP, escrituras, publicacion, push o despliegue sin autorizacion aplicable a esa accion. Preparar primero el resultado revisable.
No leer/imprimir `.env`, credenciales o cadenas de conexion. No guardar sesiones. No ocultar un bloqueo real bajo un resultado parcial.
Los cambios fuera de la raiz permitida requieren el mecanismo de permisos de la sesion; autorizacion funcional no elimina el sandbox.

## 9. Adoptar hoy y medir durante cinco tareas
- Usar ficha de tarea + contrato + diff actual antes de delegar; principal revisa y cierra sin esperar un recordatorio del usuario.
- Reutilizar snapshot/manifest valido y agrupar lecturas por PAD/rango; reservar confirmacion fresca para la fase final cuando corresponda.
- Sustituir volcados por resumen y primera diferencia; ejecutar pruebas por riesgo y navegador solo con fuente estable.
- Registrar por tarea: clase/modelo, minutos hasta aceptacion, tokens observados si estan disponibles, lecturas DB por fuente/rango, repeticiones SQL, rondas y sesiones UI.
- Registrar tambien errores escapados, reversion de cambios previos, discrepancia maxima Cu/fechas y fallos de identidad/cobertura.
- Comparar mediana por clase con las primeras cinco tareas equivalentes; no inventar ahorros porcentuales sin una linea base.
Menos tiempo/tokens solo cuenta como mejora si se conserva el contrato metalurgico y no aumentan defectos ni accesos inseguros.

Estado local: las reglas operativas de contrato, revision, reutilizacion de datos, validacion por riesgo y UI estable se adoptaron mediante AGENTS.md. La seleccion flexible de modelos de la seccion3 sigue siendo recomendacion y respeta las preferencias/autorizaciones explicitas del usuario. No se altero configuracion global ni se atribuyen ahorros de tokens sin medicion.
