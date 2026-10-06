# Validación funcional TEST V4 — evidencia aportada por el usuario

Actualización 04/10/2026. **VALIDADO LIVE: proyección funcional TEST V4**, según resultados comunicados por el usuario. No se ejecutó SQL desde el repositorio.

| Prueba | Resultado comunicado |
|---|---|
| Grano | pad_id + parcela_id + fecha |
| OX | 3264 claves, 0 duplicados, máximo 1 |
| SULF | 2856 claves, 0 duplicados, máximo 1 |
| Conservación flujo | EXCEPT ambas direcciones: 0 |
| Volumen OX fuente/V4 | 2908120.161887 |
| Volumen SULF fuente/V4 | 9260436.238434 |
| Campaña por clave | Máximo 1 |
| Drenaje fuente/V4 | EXCEPT ambas direcciones: 0 |
| Refino fuente/V4 | EXCEPT ambas direcciones: 0 |
| Transferencia kg/d y t/d recalculada | Diferencia 0 |
| Filas fuera de ventana | Conservadas |
| Ceros químicos del 10-09 | Provienen de la fuente; raw ya decimal(12,2), sin redondeo adicional de vistas |

No reinterpretar ceros como NULL ni agregar precisión inexistente para recuperarlos.

## Contrato y límite documental

El usuario informa un contrato LIVE V4 de **33 columnas** y autoriza registrar la validación de sus tipos. Sin embargo, el mensaje contiene literalmente `[pegas aquí el sys.columns que acabamos de obtener]`, no las filas de metadatos.

Por tanto se registra la validación reportada de V4, pero **queda pendiente recibir e incorporar sys.columns** (nombres, orden, tipos, precisión, escala y nullability) y, si difiere, el SELECT final validado. El candidato del repositorio tiene 25 columnas. No es correcto declarar que esas 25 columnas son el contrato LIVE de 33 ni inventar las ocho restantes o sus tipos. La equivalencia del candidato local con el objeto validado no ha sido demostrada.

## Pendientes operacionales que se mantienen

- Despliegue de inventar_SpcHidr.vw_tablero_lixiviacion_final_v2.
- Auditoría LIVE de consumidores.
- Promoción o reemplazo de cualquier objeto oficial.

La guarda del candidato permanece deshabilitada. Esta actualización no cambia fórmulas, DDL funcional ni datos; solo el estado documental de la evidencia. Sin PROD, ejecución SQL, commit ni push.
