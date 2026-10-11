# Rollback preparado; no ejecutado

Exclusivamente DEV (`inventar_SpcHidr`). Ambos oficiales estaban ausentes antes de promover. Definiciones TEST exactas, contratos y dependencias están en esta carpeta; los TEST se conservan instalados.

1. Restituir únicamente los dos nombres de fuente de `map_db.py`: parcela a `fn_estado_operacional_parcela_diario_test_v2`, módulo a `fn_estado_operacional_modulo_diario_test`. Ver `map_db_before.py.txt`. No copiar el archivo entero si posteriormente tuvo otros cambios.
2. Reiniciar el proceso Dash que consume el módulo y ejecutar tests y ambos smokes.
3. Revisar consumidores nuevos y dependencias de ambos oficiales. No retirarlos mientras existan consumidores que deban conservarse.
4. Solo después de esa revisión, ejecutar manualmente `parcela_rollback.sql` y `modulo_rollback.sql` en DEV. Retiran únicamente los oficiales nuevos. Nunca eliminan TEST, datos ni backups.

Si falla la validación durante la promoción, el script hace ROLLBACK de ambos CREATE antes del COMMIT; Dash aún conserva las fuentes TEST. Después del COMMIT, este plan requiere ejecución manual deliberada.
