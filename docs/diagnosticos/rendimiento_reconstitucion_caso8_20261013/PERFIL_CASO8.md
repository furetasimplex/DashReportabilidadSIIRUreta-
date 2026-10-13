# Perfil de Reconstitución · Caso 8 · 13/10/2026

Caso 8 del catálogo oficial, run 47, ventana 22–31/08/2026. El catálogo confirma
la ventana, pero el `SELECT` parametrizado de masa validada no devuelve filas.
Por eso el cálculo de módulos y el gráfico no se alcanzan; estos tiempos miden
`engine.analyze_db`, no el click completo ni importación/montaje de la app.

En el código original, una ejecución fría de análisis tardó 8,546 s y la
repetición caliente 14,398 s. `load_masa` consumió 7,412/13,318 s. Por cada
análisis se ejecutaban cinco lecturas: dos agregados globales de cobertura,
una carga de apilado, una consulta de masa y una consulta a ticks de torre.
`pd.read_sql` midió 7,120/13,007 s para ticks, incluyendo fetch y DataFrame;
el evento SQL midió 6,873/12,731 s de ejecución. La carga de ticks no se usa
cuando la masa está vacía. La diferencia frío/caliente muestra variación del
servidor; el coste dominante queda identificado en ambos recorridos.

Con los cambios staged y la misma fuente, ambas ejecuciones tardaron 0,274 y
0,266 s. Cada una hizo un único SELECT de masa (execute 0,067/0,087 s; total
`pd.read_sql` 0,271/0,263 s). El motor ahora se detiene con
`MissingCaseMassError` antes de consultar cobertura o apilado. El acceso vacío
en `load_masa` también termina antes de pedir ticks. No hubo SQL de escritura,
consulta a SP, XLSX ni texto de SQL/parámetros en el reporte.

Los archivos propuestos para aplicar están en `cambios/reconstitucion/`:

- `engine.py`: masa Caso primero, error tipado y cobertura local derivada de los
  frames realmente cargados cuando sí hay masa.
- `db_source.py`: salida vacía con contrato de columnas y sin consulta de ticks.
- `panel.py`: mensaje estable para ausencia de masa, sin texto del driver.
- `test_casos.py`: tres regresiones para parada temprana, short-circuit de
  ticks y mensaje seguro.

Suite offline ejecutada sobre el paquete staged con el Python del destino:

```powershell
.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider `
  perfil_caso8_20261013\staging\reconstitucion\test_casos.py `
  perfil_caso8_20261013\staging\reconstitucion\test_metodologia.py
```

Resultado: 25 passed en 8,35 s. Los perfiles completos están en
`perfil_real_caso8.json` y `perfil_stage_caso8.json`; la repetición stage usó
el mismo host, fuente y ventana real. No se modificó el repositorio destino.

## Aplicación y validación en destino
El agente entregó la propuesta y el agente principal la aplicó a reconstitucion/engine.py, db_source.py, panel.py y test_casos.py el 13/10/2026. Los hashes de estos archivos coinciden con el staging medido online. 66 pruebas offline pasan en destino (34.17 s), git diff --check limpio y main.py preservado. La DB solo se leyó; no se ejecutaron SP ni publicaciones. El Caso8 sigue sin masa publicada: esta mejora acelera el diagnóstico, no demuestra tiempos de un cálculo completo con masa ni de interacción en navegador.