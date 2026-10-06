# Flujo real de botones y datos

```mermaid
flowchart TD
    A[Dato fuente o corrección] --> B{¿Falta o cambia base del módulo?}
    B -- Sí, existe --> C[Buscar y Actualizar registro]
    B -- Sí, no existe --> D[Insertar módulo]
    B -- No --> E[Elegir rango completo afectado]
    C --> E
    D --> E
    E --> F[Reprocesar período]
    F --> G[Preparar: congelar, secuencia, línea base; sin abrir/cerrar]
    G --> H[Sync ETL: topografía y camiones]
    H --> I[Mantener secuencia: cerrar, abrir, congelar y alertar]
    I --> J[Segundo sync de seguridad]
    J --> K[Cargar CV25 y horas]
    K --> L[Calcular Reclamo diario]
    L --> M[Paneles vuelven a consultar por mensaje-accion]
    M --> N[Validaciones y vista previa]
    N --> O{¿Bloqueo vigente o cifra errónea?}
    O -- Sí --> P[Corregir causa y reprocesar rango afectado]
    P --> E
    O -- No, publicación decidida --> Q[Publicar y confirmar]
    Q --> R[Factor camiones y reporte final; MERGE Datos_conciliados_of]
```

`Refrescar vista` es una rama de consulta manual desde cualquier estado: repite `SELECT` de paneles. No reemplaza ninguna etapa de `Reprocesar`.

`Actualizar secuencia de módulos` invoca solo la etapa de mantención, fuera del flujo habitual. Puede generar cambios y alertas, pero no sincroniza el rango ni recalcula `calculo_diario`.

El `MERGE` de Publicar consume `v_reclamo_para_conciliados`, derivada de `calculo_diario`. El SP final tiene lógica propia del reporte y factor de camiones; no repite la cadena de preparación de Reclamo.
