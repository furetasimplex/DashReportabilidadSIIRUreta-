# Evidencia de auditoría de Transferencia Cu

Solo lectura DEV, período 2026-06-01 a 2026-09-10. [Informe](../TRANSFERENCIA_CU_AUDITORIA.md).

`audit.py` captura V2, agregados SQL, definiciones y hashes; detiene la comparación si el total deja de ser 30395.260628596. `report.py` inventaría referencias históricas, separa evidencia posterior y comprueba los hashes previos. No cambiar ni ejecutar el smoke histórico para esta auditoría.

JSON conserva Decimal como string exacto y NULL como null; CSV agregado usa vacío para NULL. Las series y resúmenes son LIVE, no históricos. La granularidad antigua disponible es total/PAD sin fechas. Por eso no hay row_comparison.csv ni top_contributors.csv. `cause_breakdown.json` distingue 100% localizado por PAD de 0% causalmente demostrado.

`queries_readonly.sql` registra SELECT con parámetros SQLAlchemy: no es un script de despliegue. Las definiciones CREATE guardadas en definitions_diff son texto de evidencia de OBJECT_DEFINITION, nunca ejecutadas. Los snapshots de referencia son del 05-10, no del baseline original. No reejecutar los scripts sobre esta misma carpeta si se desea preservar esta captura: usar otro destino de evidencia.
