# Checklist de promoción a PROD — Balance Hidrometalurgia

## 1. Template contractual

- Confirmar la existencia de `reporte/Template_Balance_Planta_Hidrometalurgia.xlsx`.
- Verificar SHA-256: `44E80514B74E3E99A9B723A2B3FE1150E3776CA559E440FB0BE20985FDD9F907`.
- No reemplazar ni modificar el template durante la promoción.

## 2. Configuración por ambiente

- Definir `BALANCE_RECON_DATABASE` con la base que contiene el reconciliador del ambiente.
- Definir `BALANCE_RECON_SCHEMA`; el valor esperado actualmente es `hidro`.
- Confirmar que host, base, usuario y driver provienen de la configuración segura del despliegue.
- No guardar passwords, tokens ni connection strings en código o documentación.

## 3. Dependencias existentes de BD

Confirmar acceso de sólo lectura a:

- `hidro.recon_caso`
- `hidro.recon_caso_oficial`
- `hidro.recon_solver_run`
- `hidro.recon_resultado_flujo`

El módulo de Balance sólo debe ejecutar `SELECT`. No autoriza DDL, DML, oficialización ni ejecución del solver.

## 4. Caso oficial de smoke test

- Elegir un Caso realmente oficial del ambiente PROD.
- No hardcodear Caso 24, Run 147, Run 149 ni Run 150.
- Confirmar la resolución `caso_id → recon_caso_oficial → solver_run_id`.
- Confirmar que el Run tiene estado `success` y exactamente F1–F120.

## 5. Selector y estado operacional

- Abrir Reportabilidad → Reportes Semanales → Balance.
- Confirmar que el selector muestra únicamente Casos oficializados.
- Seleccionar el Caso de smoke test y comprobar Caso, período, Run oficial y estado.
- Confirmar que el botón Excel sólo se habilita cuando el MTD está disponible.

## 6. Cobertura MTD

- Confirmar el período acumulado mostrado por el Dash.
- Si el Caso no comienza el día 1, verificar la cadena retrospectiva sin gaps ni solapamientos.
- Confirmar que una cobertura no disponible aparece como warning y bloquea la exportación.

## 7. Exportación e identidad

- Exportar el Excel desde el Caso seleccionado.
- Verificar el nombre `Balance_Planta_Hidrometalurgia_YYYYMMDD_YYYYMMDD_CasoXX_RunYY.xlsx`.
- Confirmar que `Resumen!F10:G10` muestra `Caso XX | Run oficial YY`.
- Confirmar que el cuadro DrawingML muestra el período contractual.
- Confirmar encabezados de período y acumulado.

## 8. Validaciones del workbook

- Abrir el archivo directamente con Excel Desktop: no debe solicitar reparación.
- Confirmar 120 flujos F1–F120.
- Confirmar las 480 fórmulas protegidas.
- Confirmar `Datos Reconciliados!L3` como días inclusivos del período.
- Confirmar `Datos Reconciliados!L4` como días inclusivos del MTD.
- Confirmar que masas cero mantienen ley acumulada vacía y fino cero numérico.
- Confirmar que signos negativos se conservan.
- Confirmar 66 partes OOXML, CRC válido, XML válido y cero partes/celdas duplicadas.
- Confirmar shapes, conectores, imágenes y relaciones DrawingML.

## 9. Logs

Revisar entradas `[BALANCE UI]` y `[BALANCE EXPORT]` para:

- Caso y Run oficial.
- Período y MTD.
- Cadena de Casos MTD.
- Hash del template.
- Filename final.
- `validacion_ooxml=OK`.

Los logs no deben incluir secretos ni DataFrames completos.

## 10. Rollback

- Revertir únicamente el despliegue de código a la versión previamente aprobada.
- No modificar datos, oficialidad, solver ni objetos SQL como mecanismo de rollback.
- Conservar el template contractual aprobado y registrar la versión desplegada.

## 11. Elementos prohibidos en PROD

- No usar IDs DEV hardcodeados.
- No usar Run 150 como smoke productivo.
- No inferir oficialidad mediante `MAX(run_id)`, último Run o fechas.
- No modificar template, fórmulas, MTD, OOXML o DrawingML sin nueva revisión formal.
- No habilitar escrituras en BD desde este módulo.
