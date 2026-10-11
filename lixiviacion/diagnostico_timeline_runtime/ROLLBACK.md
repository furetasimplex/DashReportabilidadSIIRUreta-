# Rollback local del timeline DEV

No ejecutar SQL, restaurar objetos ni borrar evidencias. No restaurar todo db.py sobre cambios posteriores.

Desde la raíz del repositorio, detener únicamente el proceso DEV propio si estuviera sirviendo la aplicación y ejecutar:

```powershell
.\venv\Scripts\python.exe -m lixiviacion.diagnostico_timeline_runtime.prepare rollback
```

El script comprueba que OP_TIMELINE_SQL coincide con candidate_runtime_12.sql y restaura únicamente la asignación original guardada en assignment_before.txt. Si otro cambio alteró el SQL, aborta para no sobrescribirlo. La consulta original también está en OP_TIMELINE_SQL_before.sql. db_before.py es respaldo íntegro de referencia; su SHA256 está en contract.json.

Reiniciar el proceso DEV para cargar la constante restaurada. Verificar que db.OP_TIMELINE_SQL coincide textualmente con OP_TIMELINE_SQL_before.sql; ejecutar los tests con las expectativas del SQL anterior si se revierte también el test de implementación. La suite funcional (cardinalidad, NULL, errores aislados) no cambia de criterio. El rollback recupera la latencia previa de unos51 s para102 días.

El script genera rollback.diff. No afecta OP_HEADER_SQL ni otras funciones. No hacer commit/push ni acciones sobre PROD.
