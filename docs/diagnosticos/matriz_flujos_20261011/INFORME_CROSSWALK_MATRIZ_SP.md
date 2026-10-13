# Auditoría de matriz y mapeo de flujos

## Resultado principal

La hoja `BALANCE` y las columnas de referencia antigua de `NUEVO FLOWSHET` documentan el catálogo `modelo_id=1` / `hidrometalurgia_120_completo`. El extracto live confirma que los casos oficiales de agosto (5–8; runs 46, 66, 50 y 47) usan ese modelo. `NUEVO FLOWSHET` también incluye un bloque nuevo M6 (columnas de flujo/nombre/fuente/dependencia) que corresponde al catálogo `modelo_id=2` / `hidrometalurgia_125_v2`, renumerando y cambiando el significado de F39–F58. No hay que interpretar los runs de agosto con el diccionario F nuevo.

El crosswalk detallado desde el bloque M6 de `NUEVO FLOWSHET` (F39–F58, F60, F66, F70, F72 y F81), con código/nombre previo, código/nombre del bloque antiguo y catálogo live, está en `matriz_modelo_crosswalk_F39_F58.csv`. Para resolver diferencias en series reconciliadas, valida siempre `modelo_id`/catálogo del run antes de traducir códigos. Un mismo `codigo_flujo` no es una identidad global.

La revisión completa de nomenclatura y fuentes del bloque M6 frente al catálogo live (122 filas de la hoja) está en `matriz_modelo_crosswalk_completo.csv`; el catálogo modelo 2 contiene 125 flujos y la hoja no muestra F123–F125. Los 122 comparados tienen unidad `Ton`; hay 3 diferencias literales de nombre (F74, F117, F122), 34 sin fuente textual (12 marcados explícitamente hardcode/fijo, 1 fórmula sin fuente externa y 21 sin fuente ni dependencia documentadas). La revisión se limita a correspondencia de código/modelo, nombre y fuente textual/unidad disponible; no juzga la magnitud reconciliada como error. Si una diferencia de curva proviene del reconciliador de flujos y el método aplicado es el aprobado, no se trata como una falla de distribución.

## Fuentes y estructura

La hoja `AUDITORIA_SP_120` de la matriz relaciona códigos antiguos con formulas, entradas de templates y trazabilidad. En modelo 1, el SP actual clasifica riego desde `v_riego_parcelas_origen` por `pila_codigo` OX/SULF y `origen_riego` REFINO/ILS/DPLS, usando concentraciones diarias de `conc_cu`; integra caudal por duración real del intervalo y filtra intervalos activos. Las correspondencias son OX: F39 (refino), F41 (ILS), F46 (DPLS); SULF: F44 (refino), F45 (ILS). F40/F42 son asignaciones a aglomerado desde `insumos_area_humeda_flujos`, no riego a PAD.

Los drenajes de modelo 1 son balances derivados: F48 para PLS óxidos; F50 para PLS sulfuros, al que se agrega F49 (bleed hacia la piscina PLS óxidos) para considerar todo el PLS de sulfuro. F47/F51 son retornos ILS, separados del alcance de drenaje PLS. En el SP de modelo 1 auditado, F43 se inserta como cero y los runs oficiales de agosto lo reportan cero; el SP base `sp_calcular_balance_flujos.sql` incluye F43 en la fórmula de F48. Esto no describe F43 del modelo nuevo, donde el nombre es inventario mineral PAD DUMP.

La definición live de `sp_calcular_balance_flujos_modelo6_v2` (perfil dev, modificada 2026-10-08) usa la nueva nomenclatura: por ejemplo F39–F43 describen entradas/compensación/inventario PAD DUMP; F44 es PLS de PAD óxidos a piscina, F47 PLS de PAD sulfuros, F48 bleed, F49 retorno ILS sulfuro y F50 inventario de solución sulfuros. Las fuentes de riego ahora se identifican como F70_PRINCIPAL/F70_ADICIONAL, F60 y F81 para OX; F72 y F66 para SULF. En la lista de flujos modelo2 la etiqueta F70 es el agregado; evitar sumar ese agregado otra vez con sus componentes.

El SP live `sp_flujo_riego_drenaje` produce un resumen operativo por campaña, pad y parcela: toma riegos desde `v_flujos_oxido_unpivot`/`v_flujos_sulfuro_unpivot` y drenajes desde `v_drena_oxido_operacional`/`v_drena_sulfuro_operacional`. No es el crosswalk del flujo reconciliado modelo 1 ni reemplaza su clasificación de origen por naturaleza de solución.

## Hallazgos y límites

- La clasificación OX/SULF más REFINO/ILS/DPLS es evidencia de origen directa en el SP, coherente con los templates de Parcelas y Balance Diario anotados en la matriz.
- La fórmula matriz de F48 usa F39+F41+F43+F46−F68; la nota técnica de la matriz documenta que en el SP modelo 1 F43=0. La revisión no concluye que un valor reconciliado alto venga de la asignación por parcela.
- La matriz y SP comparados son históricos/versionados: la matriz es Rev. B de marzo y los casos de agosto son modelo 1; la definición modelo6_v2 es la implementación nueva. No se validó una ejecución live nueva ni se escribió a DB.
- `BALANCE` contiene observaciones legadas que divergen del nuevo trazado operacional: F41 indica riego ILS óxidos en cero por estrategia; F46 dice PAD sulfuros pese a llamarse PAD óxidos; F53 dice flujo físicamente inexistente, mientras el SP modelo1 lo deriva. Deben resolverse contra la versión/modelo antes de tratar como errores de datos.
- Los diagramas embebidos muestran etiquetas generales como Tms, %CuT, cobre fino e inventarios, sin un crosswalk textual completo de nodos/códigos para estos F; no se dedujeron coeficientes de nodo no visibles en las tablas.
- Lectura enfocada: TAPA, filas F39–F58 de `BALANCE` y `AUDITORIA_SP_120`, bloque M6 F39–F58/F60/F66/F70/F72/F81 de `NUEVO FLOWSHET`, y `RESUMEN_CAMBIOS`; metadatos/modelos/casos desde `live_runs_flujos.json`; se inspeccionaron los bloques de origen/riego y flujo en los SP staged. No se procesaron todas las celdas ni todos los 120 flujos. No se modificó el XLSX, SQL, motor ni DB.
