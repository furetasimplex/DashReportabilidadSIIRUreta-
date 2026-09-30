# Auditoría read-only: Ley CuT SRR, septiembre de 2026

## Resultado ejecutivo

La ruta de emisión vigente **publica el residual sin sustituir resultados cero o negativos**. La reconstrucción mediante SELECT del CASE y de los insumos del SP coincide con `Datos_conciliados_of.Ley_CuT_Real_srr` en las 30 fechas, incluidos los NULL. No se ejecutó ningún mantenedor.

El 16/09 el residual y SIIR son **−0,023021448774 %**. MOV_CAM contiene **0,293580790937 %**, igual al archivo mina y al oficial. La regla simulada escogería MOV_CAM y resolvería ese caso. IMP contiene una ley diferente: **0,497405531375 %**.

La regla todavía necesita una definición para **residual NULL con tonelaje positivo**: ocurre el 20/09, con SRR 603,12401226 TMS e IMP válido, pero sin ley mina+stock para calcular el residual. NULL no satisface `<= 0`. No se lo convirtió a cero ni se inventó una rama. Los días 28–30 tampoco pueden clasificarse como tonelaje cero: falta SRR evaluable.

La simulación literal produce 22 selecciones RESIDUAL, 1 MOV_CAM y 0 IMP. Hay 7 resultados NULL, de los cuales 3 corresponden a tonelaje cero, 3 a tonelaje desconocido y 1 al caso pendiente del 20/09. Ningún caso cumple la rama estricta «residual <= 0 sin MOV_CAM/IMP válidos».

## Alcance, fuentes y reproducibilidad

- Conexión verificada a DEV, base `inventar_SpcHidr`; la fuente IMP real es `DEV_SIIR.hidro`, en el mismo servidor. No se verificó otro ambiente.
- Período de registros analizado: exclusivamente 01–30/09/2026. El inventario anterior se utiliza únicamente como insumo ya disponible del balance de septiembre.
- Se leyeron las definiciones actuales mediante `sys.sql_modules`, datos por SELECT y los XML internos de los Excel. No se abrió Excel para recalcular, no se ejecutaron macros ni se guardaron los originales. Los valores del oficial son los valores almacenados en el archivo.
- Oficial elegido: `Datos Conciliados Septiembre 2026_RevPI SRR(3) (1).xlsm`, copia más reciente disponible en Downloads. SHA-256: `8f2e21719bf61988a1e7994178d3f921350028ff90dc5d82e76ae231cf4d336f`.
- Fuente mina contrastada: `BD_CIO_Spence_CH01_FY27_Septiembre(19).xlsx`, hojas Base_Datos, BD_Cubicación (no tocar) y Pegar_Cubicación.
- [Tabla completa de 30 días, CSV](diagnostico_septiembre_2026.csv): contiene todas las columnas solicitadas, más SRR físico, coordenadas, fórmulas del oficial y de la hoja auxiliar, cantidades de registros y observaciones.
- [Registros MOV_CAM](registros_MOV_CAM_SRR.csv), [registros IMP vigentes](registros_IMP_SRR_vigentes.csv), [insumos y residual SQL](residual_sql.json), [SELECT reproducible](reconstruccion_residual_select.sql).
- Las celdas vacías del CSV representan NULL. Ningún NULL se interpreta como cero. Las leyes se expresan en puntos porcentuales: 0,29358079 significa 0,29358079 %, no 29,358079 %.

## Linaje vigente de emisión

```text
Informe_TM_lab + representatividad_torres_resultado
     y v_conciliacion_chancado_v2 (resumen_mina / IMP)
  -> v_validacion_leyes_tm1_v2 / v_validacion_leyes_tm2_v2
  -> v_leyes_validadas_tm_turno
  -> v_leyes_resueltas_data_tm_reporte_test
  -> sp_reporte_turno_emision_test
  -> sp_actualizar_reporte_turno_cache_emision_test
  -> reporte_turno_cache_emision_test
     ├─ fn_generador_reporte_diario_emision_test.CuT_Real_Dia
     └─ SUM(Apilado_TMS_Real * SRR / 100) por día

mov_cam CH01, Fase <> SRR, deduplicado
  -> Ley_CuT_Mina_Stock ponderada por Tonelaje_seco_CIO
     └─ si no hay fila MOV_CAM: DEV_SIIR.hidro.imp_csv no SRR

Control_Factor_Ajuste_Camiones_v2_test + override vigente
  -> v_ajuste_camiones_emision_test
     -> masa bruta seleccionada, sal, delta inventario, chancado aplicado

Todos los insumos anteriores
  -> sp_mantiene_datos_conciliados_emision_test, CASE Ley_CuT_Real_srr
  -> MERGE Datos_conciliados_of.Ley_CuT_Real_srr
  -> fetch_datos_conciliados_emision_report()
  -> export_datos_conciliados_to_template()
  -> columna Ley CuT SRR de Generador Reporte Diario
```

El diagrama describe el código; **ninguno de los SP se ejecutó en esta auditoría**. Las definiciones íntegramente leídas están en los archivos SQL de esta carpeta.

Para CuT de torres, las vistas de validación usan laboratorio cuando la representatividad química es mayor que 0,75 y hay ley; de lo contrario usan CuT mina si existe; de lo contrario NULL. La vista de leyes resueltas proyecta CuT y Fuente_CuT de esa validación. No hay una semilla de Ley_CuT_Real_srr en el CASE residual. El cache contiene leyes con precisión decimal y la función diaria pondera por Apilado_TMS_Real; no es un promedio simple de A y B.

## Fórmula real y tratamientos

Definición vigente: [sp_mantiene_datos_conciliados_emision_test](inventar_SpcHidr.sp_mantiene_datos_conciliados_emision_test.sql), pasos 3, 5, 6 y 11. Extracto literal del CASE:

```sql
CASE
    WHEN ISNULL(s.Flag_SRR_TMS_Dia, '') <> 'OK'
      OR s.SRR_TMS_Dia IS NULL OR s.SRR_TMS_Dia <= 0 THEN NULL
    WHEN g.CuT_Real_Dia IS NULL THEN NULL
    WHEN lms.Ley_CuT_Mina_Stock IS NULL THEN NULL
    WHEN CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1
         THEN aj.Apilado_TMS_Bruto_Ajustado
         ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END IS NULL THEN NULL
    WHEN aj.Sal_TMH_Dia IS NULL THEN NULL
    WHEN aj.Delta_Inventario_Chancado_TMS IS NULL THEN NULL
    WHEN aj.Chancado_TMS_Reporte IS NULL THEN NULL
    ELSE
        (
            g.CuT_Real_Dia
            * (
                CASE WHEN COALESCE(aj.Flag_Usa_Ajuste, 0) = 1
                THEN aj.Apilado_TMS_Bruto_Ajustado
                ELSE aj.Apilado_TMS_Bruto_Sin_Ajuste END
                - aj.Sal_TMH_Dia
                + aj.Delta_Inventario_Chancado_TMS
              )
            - (lms.Ley_CuT_Mina_Stock * aj.Chancado_TMS_Reporte)
        ) / NULLIF(s.SRR_TMS_Dia, 0)
END AS Ley_CuT_Real_srr
```

Equivale a `[(LeyApilado × (TMSBrutoSeleccionado − Sal + ΔInventario)) − (LeyMinaStock × ChancadoAplicado)] / SRR_TMS_Cache`.

- La masa de apilado entra **bruta**, luego se descuenta sal una vez. No es TMH ni una masa obtenida de MOV_CAM.
- Δ inventario es TMS actual menos anterior, con el signo que entrega la vista. Se suma.
- Chancado es `aj.Chancado_TMS_Reporte`, de la ruta aplicada. Bajo FORZADO_1 la vista devuelve `Flag_Usa_Ajuste=0`, por lo que el residual usa masa sin ajuste automático.
- El denominador NO es `aj.SRR_TMS_Dia`. El paso 6 reconstruye por turno `Apilado_TMS_Real * SRR / 100.0` desde el cache RTO y suma. Exige ambos turnos y ningún producto NULL para Flag='OK'.
- Las masas son toneladas secas, salvo el campo Sal_TMH_Dia que el código resta directamente según la metodología existente. La auditoría no reinterpreta esa convención.
- Las leyes están en %. Los factores `/100` de cobre fino se cancelan en el cociente residual; el SQL trabaja en t·puntos porcentuales/t.
- SRR cero, negativo, NULL, flag no OK o cualquier insumo NULL → NULL. `NULLIF` protege división por cero.
- Si todos los insumos son evaluables, un numerador cero produce cero y uno negativo produce negativo. No hay clamp, sustitución por cero ni fallback de la ley residual a MOV_CAM/IMP.
- El fallback ya existente a IMP es de **Ley Mina+Stock**, no de **Ley SRR final**. MOV_CAM excluye Fase SRR y exige Destino CH01, tonelaje seco positivo y CuTG00 no NULL. IMP exige `to='CH01'`, `shovel<>'SRR'`, `origen='IMP'`, tonnage>0 y cut no NULL. La prioridad es existencia de fila MOV_CAM, no CuT>0. El SP lee imp_csv crudo para ese insumo, sin la selección de batch de la vista normalizada.

## Controles 02/09 y 16/09

| Magnitud | 02/09 | 16/09 |
|---|---:|---:|
| SRR TMS usado en residual, cache | 0 | 489,210795600 |
| SRR TMS físico, vista Factor/Balance | 0 | 489,214821763 |
| Ley apilado del generador SQL | NULL | 0,376750 |
| Ley mina+stock | NULL | 0,493644250874 |
| TMS bruto seleccionado | 0 | 2384,622 |
| Sal | 0 | 58,37 |
| Δ inventario TMS | 16,790950636 | −163,952112821 |
| Chancado aplicado | 16,790950636 | 1673,085065416 |
| Residual SQL / SIIR materializado | NULL | −0,023021448774 |
| Ley MOV_CAM | Sin registros | 0,293580790937 |
| Ley IMP vigente | Sin registros | 0,497405531375 |
| Ley publicada en oficial | 0 fijo | 0,293580790937 fijo |
| Simulación literal | NULL, sin tonelaje | 0,293580790937, MOV_CAM |

**02/09:** no hay registros SRR MOV_CAM ni IMP. `SRR!Z7` del oficial contiene:

```excel
IFERROR((('Generador Reporte diario'!Y22*('Generador Reporte diario'!T22+'Balance Chancado'!W5-'Balance Chancado'!W4))-(SRR!Y7*'Generador Reporte diario'!D22))/'Generador Reporte diario'!M22,0)
```

`M22=0`, por tanto es **ERROR/NO_EVALUABLE → IFERROR → 0**, no un cero residual matemático. `Generador Reporte diario!O22` almacena un 0 fijo; no contiene un vínculo de fórmula a Z7. El SIIR actual mantiene NULL correctamente. El residual de inventario de 16,790950636 TMS no crea tonelaje SRR ni vuelve evaluable la ley.

**16/09:**

```text
Masa para LeyApilado = 2384,622 − 58,37 − 163,952112820585 = 2162,299887179415
Término apilado       = 0,376750 × 2162,299887179415 = 814,646482494845
Término mina+stock    = 0,493644250873586 × 1673,085065416415 = 825,908823765270
Residual             = (814,646482494845 − 825,908823765270) / 489,2107956
                     = −0,0230214487736582 %
```

Trazabilidad numérica confirmada para la ley alternativa:

```text
Archivo mina septiembre(19), Pegar_Cubicación!D85 = 0,2935807909371006, fijo
  contexto B85 = SRR_10x_15jun26_final.bmf; C85 = 16-09-26-Ripio
-> BD_Cubicación (no tocar)!D85 = +Pegar_Cubicación!D85
-> Base_Datos!M142/M143 = IFERROR(VLOOKUP(F142/F143, BD_Cubicación..., D1+1, FALSE),0)
-> MOV_CAM mov_id 39294 / 39295, CuTG00 = 0,2935807909371006
   TA: Ton=489,2148217629661; TB: Ton=0
-> oficial SRR!Z21 y Generador Reporte diario!O36 = 0,2935807909371006, ambos fijos
```

Los 34 registros SRR del archivo mina coinciden con MOV_CAM en fecha, turno, tonelaje y CuTG00. El cargador documentado lee Base_Datos y conserva esas columnas. MOV_CAM no guarda nombre de archivo ni batch para estos registros; por eso se demuestra coincidencia registro a registro y linaje de código, no un log de importación individual. El salto al Excel oficial es **coincidencia exacta de valor fijo**, no un enlace de fórmula o una prueba de la acción humana de copiado. No se afirma un vínculo automático MOV_CAM → Excel que el archivo no contiene.

El oficial también tiene `D36=0` fijo para Chancado y sal 58, mientras SIIR tiene Chancado 1673,085065416 y sal 58,37. No son fotografías idénticas de todos los insumos. La coincidencia de ley no valida por sí sola la igualdad de los balances.

## MOV_CAM e IMP

MOV_CAM tiene **34 registros, 17 días**, dos turnos por día; los días son 01 y 04–19. No hay SRR el 02/09, ni duplicados exactos por fecha/turno/sólido/ton/ley en el conjunto. Los turnos de cada fecha tienen la misma CuTG00. Hay turnos de tonelaje cero, que no deben pesar en la ley diaria.

La ponderación no fue inventada: `resumen_mina` usa `SUM(Ton*CuTG00)/NULLIF(SUM(Ton),0)` por fecha/turno/origen/fase; la vista de publicación y el mantenedor alternativo agregan por día. `sp_calcular_balance_flujos` ya tiene una ley SRR diaria MOV_CAM con toneladas positivas y CuTG00 no NULL, seguida de IMP solo cuando falta MOV_CAM válido. Esa es una ruta distinta de la emisión residual. En los registros auditados, ambas agregaciones dan el mismo valor diario. **No se debe usar Tonelaje_seco_CIO para SRR MOV_CAM: en estas filas es NULL; el tonelaje fuente está en Ton. Tampoco usar PONDCuTG00 crudo como si fuera ley: el 16/09 vale 143,62407431132428 en TA, el producto Ton×CuTG00.**

IMP tiene **445 registros SRR vigentes, 24 días**: 01, 04–20 y 22–27. No contiene SRR el 02, 03, 21 ni 28–30. Todos tienen CuT válida y positiva; no se detectaron duplicados por fecha/hora. La normalización devuelve los mismos 445 registros de origen.

Fuente vigente: `DEV_SIIR.hidro.imp_csv`, batch **30520**, archivo `2026_09_01_leaching-2026_09_27_leaching.csv`, estado committed. `imported_at=2026-09-28 13:28:00.386562-03:00`. Hay un solo batch en los registros de septiembre consultados. `date` es fecha operacional; `datetime` define A entre 08:00 y antes de 20:00, B en otro horario. Hay varios registros intradiarios, no una única fila diaria.

La vista vigente [hidro.v_imp_chancado_normalizado](DEV_SIIR.hidro.v_imp_chancado_normalizado.sql):

1. Filtra origen IMP, destino CH01, fecha/hora válidas y Ton>0.
2. Identifica SRR por `from='SRR-SRR'` o `shovel='SRR'`.
3. Admite CuT entre 0 y 100; fuera de rango entrega NULL.
4. Escoge por fecha el lote con `MAX(imported_at)` más reciente, desempata por batch_id descendente.
5. Deduplica SRR por Fecha + FechaHora, conservando imported_at/id mayores.

Para la ley diaria diagnóstica se aplicó la ponderación por Ton con CuT válida de la metodología existente de conciliación/balance. No se promediaron promedios de turno. El 16/09 corresponde al registro **47888**, 08:00 turno A, `Ton=490,7325504213925`, `CuT=0,497405531375`, `from=SRR-SRR`, `shovel=SRR`, `to=CH01`.

IMP es un respaldo **técnicamente disponible y compatible en estructura**, pero no idéntico a MOV_CAM: difieren masas y leyes. Su adopción como ley final del residual requiere aprobación de negocio. Existe ya política SQL de lote/deduplicación; no se propone otra. En este mes ninguna residual evaluable no positiva llega a necesitar IMP porque el único caso negativo tiene MOV_CAM.

## Comparación con el oficial

La celda publicada seleccionada para `Ley_CuT_SRR_Oficial` es **Generador Reporte diario!O21:O50**. Hay 23 valores fijos, del 01 al 23, y 7 vacíos, del 24 al 30. Se clasifican como **VALOR_MANUAL_O_FIJO**, sin atribuirles error por el solo hecho de ser fijos.

La hoja auxiliar **SRR!Z6:Z35** tiene 28 fórmulas y 2 valores fijos: 16 y 20. Sus valores coinciden con la columna publicada del 01 al 23. Del 24 al 30 no deben presentarse los resultados auxiliares como ley oficial publicada: O está vacío. El CSV conserva ambas magnitudes y las fórmulas por día.

El patrón de la fórmula auxiliar es el conceptual solicitado: LeyApilado × (TMS apilado neto + Δ inventario), menos LeyMinaStock × Chancado, dividido por SRR; envuelto en IFERROR(...,0). La fórmula SIIR es conceptualmente comparable, pero los insumos y redondeos no son idénticos, y el oficial tiene sustituciones fijas.

Comparación de la simulación contra el valor publicado, con tolerancia absoluta **1e−9 puntos porcentuales**, sin redondeo visual: **1 SI, 18 NO, 11 NO_COMPARABLE**. La coincidencia es el 16/09. Un NULL no se considera igual a un cero del archivo. Los 18 NO no significan 18 errores de fallback: la regla conserva los residuales positivos y las fotografías de entrada difieren. Por ejemplo, el 01/09 SIIR publica 0,446589045205 frente a 0,412428613269 del archivo; el 22/09 son 0,453598016943 y 0,530934853985. No se atribuye cada diferencia a una causa única sin una conciliación adicional de insumos.

## Dependencias e impacto de cambiar solo Ley_CuT_Real_srr

| Consumidor | Dependencia real encontrada | Efecto de cambiar ese campo solamente |
|---|---|---|
| Datos Conciliados / Excel Generador Reporte Diario | `fetch_datos_conciliados_emision_report` selecciona la columna de Datos_conciliados_of; writer la presenta | Cambia la ley visible. No recalcula Chancado ni Apilado |
| `sp_reporte_datos_conciliados_test` | Proyecta `d.Ley_CuT_Real_srr` | Salida de reporte |
| `sp_rep_publish_oficial_validado` | Copia la columna a Datos_conciliados_of_ver | Cambia futuras versiones publicadas si se ejecuta ese proceso; no reescribe versiones por sí solo |
| `vw_Datos_conciliados_of_activo` | Proyecta versión activa o tabla base | Cambia lo visible según la rama seleccionada |
| `vw_datos_conciliados_reporte` | Su lista de columnas no incluye Ley_CuT_Real_srr | No hay consumo de esta ley por esa vista |
| Corte/fecha del exportador | Columna incluida en COLUMNAS_FECHA_ACTUALIZACION, excluida de COLUMNAS_CORTE_RESUMEN_DATOS_CONCILIADOS | Puede afectar detección de fecha si fuera el único dato real; no bloquea el corte MTD por faltar esta ley |
| RTO / función Generador SQL | Calcula CuT_Real desde torres/mina y masas; no lee Ley_CuT_Real_srr | No cambia la química RTO ni su ley global al cambiar solo el campo DC |
| Reconstitución SRR | `fn_reconstitucion_srr_emision_test` calcula CuT_SRR_Reconst con generador + resumen_mina; función de turno la proyecta | No consume Ley_CuT_Real_srr. El JOIN Python a DC toma masas TMH y sal, no esta ley |
| Cobre_fino_Apilado_Real | CASE: Apilado_TMS_Reporte × g.CuT_Real_Dia /100 | No depende de Ley_CuT_Real_srr |
| Balance Chancado / factor camiones | Balance de masas, sal, inventario y SRR; sin consumo de esta ley | Sin dependencia matemática de este campo |
| `sp_calcular_balance_flujos` y variantes | Ley SRR propia desde MOV_CAM/IMP; lecturas DC corresponden a toneladas de reclamo F21/F22 | Cambiar únicamente Ley_CuT_Real_srr no cambia sus leyes/finos. Cambiar MOV_CAM sería distinto y sí se propagaría |

Se revisaron referencias explícitas del campo, dependencias de objetos y las lecturas de DC; no se deduce una dependencia de ley por un simple JOIN a la tabla. No se demuestra aquí ausencia de consumidores externos que no estén en el repositorio o en los módulos SQL accesibles.

## Riesgos, discrepancias y recomendación

1. **Dos rutas con el mismo nombre de campo:** `sp_mantiene_datos_conciliados_emision_test` escribe residual; `sp_mantiene_datos_conciliados_of` y versiones antiguas calculan ley SRR directa de MOV_CAM. Ambos tienen código de escritura sobre Datos_conciliados_of. La ruta Python de emisión usa el primero y los valores actuales coinciden con él. Un consumidor alternativo podría sobrescribir con otra metodología; la auditoría no prueba su frecuencia de ejecución.
2. **Fallback existente mal interpretable:** el encabezado versión 1.16 menciona fallback IMP, pero es para Ley Mina+Stock; no resuelve residual SRR negativo. Otra ruta de balance sí prioriza MOV_CAM/IMP para su propia ley SRR. No trasladar esa conclusión automáticamente a emisión.
3. **SRR físico frente a reconstruido:** 489,214821763 frente a 489,2107956 el 16/09. El primero entra en Chancado, el segundo divide la ley residual. Se documenta sin corregir.
4. **Regla incompleta para NULL:** el 20/09 tiene tonelaje y una ley IMP 0,423387991, pero falta Ley Mina+Stock y residual NULL. A–E no autorizan fallback porque exigen residual<=0. Recomendar definir explícitamente si esa condición incluye no evaluables y qué flag conservar. No se simula que haya autorización.
5. **Datos faltantes no son cero:** los días 28–30 no tienen cache/generador/factor evaluables aunque DC conserva filas de calendario. No marcar «sin tonelaje».
6. **Coberturas diferentes:** MOV_CAM llega al 19; IMP al 27; la ley en la columna publicada oficial llega al 23. El auxiliar SRR no sustituye al reporte publicado.
7. **Trazabilidad de importación incompleta:** archivo mina y MOV_CAM coinciden, pero MOV_CAM no tiene batch/archivo; el oficial contiene valores fijos. No se puede demostrar la acción de copiado con una fórmula inexistente.
8. **Validación de dominio:** la propuesta considera >0. La normalización IMP también impone <=100, mientras MOV_CAM y la ley residual no necesariamente tienen ese límite. No inventar ahora un rango físico adicional, pero acordarlo antes de implementar.
9. **Insumo mina+stock IMP del residual:** el SP lee crudo, sin lote/deduplicación. Hay un solo lote en este conjunto, así que el riesgo de múltiples batches no se materializa aquí.

**Recomendación:** respaldo suficiente para conservar el residual diagnóstico, mantener NULL cuando SRR=0 y diseñar el fallback MOV_CAM del caso negativo del 16/09. IMP tiene infraestructura y datos utilizables como segundo respaldo. **No recomendar implementar todavía la regla completa como especificación cerrada**: primero decidir el residual NULL con tonelaje, tratamiento de SRR desconocido, validez de leyes y alcance del escritor de emisión frente al mantenedor alternativo. No se implementó ninguna de estas decisiones.

## Control read-only

Los 30 registros de Datos_conciliados_of y las 310 definiciones de módulos SQL son idénticos antes/después. Los hashes de todos los archivos versionados del repositorio no cambiaron. Los hashes de los originales oficial y mina tampoco cambiaron. Se conservaron las modificaciones preexistentes del workspace.

Los únicos archivos creados por esta auditoría están bajo `report_export/exports/auditoria_ley_srr_202609/`: scripts de análisis, snapshots SELECT, CSV y este informe. No se ejecutaron UPDATE/INSERT/DELETE/MERGE, mantenedores, DDL, commit ni push.

**Observación de concurrencia del workspace:** además de la carpeta diagnóstica, `git status` detectó durante la sesión un nuevo archivo no versionado `reporte/Datos Conciliados Septiembre 2026_RevPI SRR(3) (1).xlsm`, creado a las 15:33:12. Ningún comando de esta auditoría lo creó o modificó; su hash coincide exactamente con el original de Downloads. Se deja registrado y no se elimina. Por ello no se afirma que el estado global solo cambió por la carpeta de auditoría.

Evidencia: [control_read_only.json](control_read_only.json), [estado inicial](git_status_antes.txt), [estado final](git_status_despues.txt).

## Resumen cuantitativo y tabla diaria

| Indicador | D?as |
|---|---:|
| SRR TMS = 0 | 3 (02, 03, 21) |
| SRR TMS > 0 | 24 |
| SRR TMS NULL | 3 (28, 29, 30) |
| Residual positiva | 22 |
| Residual cero | 0 |
| Residual negativa | 1 (16) |
| Residual no evaluable | 7 |
| Selecci?n RESIDUAL | 22 |
| Selecci?n MOV_CAM | 1 |
| Selecci?n IMP | 0 |
| Rama E: sin MOV_CAM/IMP v?lidos y residual no positivo | 0 |
| Residual NULL con tonelaje; regla pendiente | 1 (20) |
| Coincide con oficial / No / No comparable | 1 / 18 / 11 |

Valores completos en CSV; aqu? se redondean ?nicamente para lectura. SRR es el denominador real del residual, no el f?sico. SIIR coincide con la columna residual en todos los casos.

| Fecha | SRR TMS c?lculo | Residual / SIIR | MOV_CAM | IMP | Oficial publicado |
|---|---:|---:|---:|---:|---:|
| 2026-09-01 | 266.9947924 | 0.446589045 | 0.415332578 | 0.41338495 | 0.412428613 |
| 2026-09-02 | 0 | NULL | NULL | NULL | 0 |
| 2026-09-03 | 0 | NULL | NULL | NULL | 0 |
| 2026-09-04 | 8941.06269669 | 0.352454828 | 0.352580951 | 0.382045905 | 0.352115129 |
| 2026-09-05 | 21355.123685723 | 0.412814602 | 0.411884859 | 0.378582897 | 0.412451391 |
| 2026-09-06 | 24253.780263699 | 0.407482005 | 0.414796461 | 0.446598679 | 0.407467685 |
| 2026-09-07 | 10010.697966557 | 0.389447112 | 0.407109438 | 0.476130453 | 0.399486001 |
| 2026-09-08 | 16147.366753213 | 0.508563409 | 0.510725172 | 0.518856898 | 0.510441168 |
| 2026-09-09 | 23184.145893907 | 0.407056672 | 0.412734405 | 0.509180511 | 0.404258118 |
| 2026-09-10 | 26574.458672 | 0.354103189 | 0.354646302 | 0.451965026 | 0.358435571 |
| 2026-09-11 | 34792.93950612 | 0.446147634 | 0.446812407 | 0.485795861 | 0.449055667 |
| 2026-09-12 | 31932.894168767 | 0.340420778 | 0.473650782 | 0.49760478 | 0.343108461 |
| 2026-09-13 | 20534.524120025 | 0.39788246 | 0.478178465 | 0.516394001 | 0.399355605 |
| 2026-09-14 | 17279.068098397 | 0.490331349 | 0.490763548 | 0.484481349 | 0.490263009 |
| 2026-09-15 | 27896.73594788 | 0.459077382 | 0.457805545 | 0.490579254 | 0.459072823 |
| 2026-09-16 | 489.2107956 | -0.023021449 | 0.293580791 | 0.497405531 | 0.293580791 |
| 2026-09-17 | 22626.145851124 | 0.37307437 | 0.383349851 | 0.387547559 | 0.374038589 |
| 2026-09-18 | 24052.92492334 | 0.321326082 | 0.383349851 | 0.450634362 | 0.319089317 |
| 2026-09-19 | 33050.735926418 | 0.37914405 | 0.379140955 | 0.449379142 | 0.381484344 |
| 2026-09-20 | 603.12401226 | NULL | NULL | 0.423387991 | 0.379140955 |
| 2026-09-21 | 0 | NULL | NULL | NULL | 0 |
| 2026-09-22 | 32073.777989892 | 0.453598017 | NULL | 0.452556306 | 0.530934854 |
| 2026-09-23 | 34133.651787256 | 0.470729763 | NULL | 0.467905792 | 0.492404225 |
| 2026-09-24 | 33331.549922994 | 0.518558884 | NULL | 0.517807543 | NULL |
| 2026-09-25 | 30209.32494365 | 0.626571504 | NULL | 0.622622601 | NULL |
| 2026-09-26 | 30905.502547218 | 0.678554132 | NULL | 0.678725757 | NULL |
| 2026-09-27 | 32334.938423541 | 0.766975141 | NULL | 0.764770148 | NULL |
| 2026-09-28 | NULL | NULL | NULL | NULL | NULL |
| 2026-09-29 | NULL | NULL | NULL | NULL | NULL |
| 2026-09-30 | NULL | NULL | NULL | NULL | NULL |

| Fecha | Estado residual | Tipo oficial | Final simulada | Fuente | Motivo | Coincide |
|---|---|---|---:|---|---|---|
| 2026-09-01 | POSITIVA | VALOR_FIJO | 0.446589045 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-02 | NO_EVALUABLE | VALOR_FIJO | NULL | NULL | SIN_TONELAJE_SRR | NO_COMPARABLE |
| 2026-09-03 | NO_EVALUABLE | VALOR_FIJO | NULL | NULL | SIN_TONELAJE_SRR | NO_COMPARABLE |
| 2026-09-04 | POSITIVA | VALOR_FIJO | 0.352454828 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-05 | POSITIVA | VALOR_FIJO | 0.412814602 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-06 | POSITIVA | VALOR_FIJO | 0.407482005 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-07 | POSITIVA | VALOR_FIJO | 0.389447112 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-08 | POSITIVA | VALOR_FIJO | 0.508563409 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-09 | POSITIVA | VALOR_FIJO | 0.407056672 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-10 | POSITIVA | VALOR_FIJO | 0.354103189 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-11 | POSITIVA | VALOR_FIJO | 0.446147634 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-12 | POSITIVA | VALOR_FIJO | 0.340420778 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-13 | POSITIVA | VALOR_FIJO | 0.39788246 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-14 | POSITIVA | VALOR_FIJO | 0.490331349 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-15 | POSITIVA | VALOR_FIJO | 0.459077382 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-16 | NEGATIVA | VALOR_FIJO | 0.293580791 | MOV_CAM | FALLBACK_MOV_CAM | SI |
| 2026-09-17 | POSITIVA | VALOR_FIJO | 0.37307437 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-18 | POSITIVA | VALOR_FIJO | 0.321326082 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-19 | POSITIVA | VALOR_FIJO | 0.37914405 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-20 | NO_EVALUABLE | VALOR_FIJO | NULL | NULL | RESIDUAL_NULL_REGLA_NO_DEFINIDA | NO_COMPARABLE |
| 2026-09-21 | NO_EVALUABLE | VALOR_FIJO | NULL | NULL | SIN_TONELAJE_SRR | NO_COMPARABLE |
| 2026-09-22 | POSITIVA | VALOR_FIJO | 0.453598017 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-23 | POSITIVA | VALOR_FIJO | 0.470729763 | RESIDUAL | RESIDUAL_VALIDA | NO |
| 2026-09-24 | POSITIVA | VACIO | 0.518558884 | RESIDUAL | RESIDUAL_VALIDA | NO_COMPARABLE |
| 2026-09-25 | POSITIVA | VACIO | 0.626571504 | RESIDUAL | RESIDUAL_VALIDA | NO_COMPARABLE |
| 2026-09-26 | POSITIVA | VACIO | 0.678554132 | RESIDUAL | RESIDUAL_VALIDA | NO_COMPARABLE |
| 2026-09-27 | POSITIVA | VACIO | 0.766975141 | RESIDUAL | RESIDUAL_VALIDA | NO_COMPARABLE |
| 2026-09-28 | NO_EVALUABLE | VACIO | NULL | NULL | SRR_TMS_NO_EVALUABLE | NO_COMPARABLE |
| 2026-09-29 | NO_EVALUABLE | VACIO | NULL | NULL | SRR_TMS_NO_EVALUABLE | NO_COMPARABLE |
| 2026-09-30 | NO_EVALUABLE | VACIO | NULL | NULL | SRR_TMS_NO_EVALUABLE | NO_COMPARABLE |
