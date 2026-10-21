# Auditorías locales

Todas las auditorías y evidencias de validación se guardan bajo `auditorias/`,
excluida de Git mediante `/auditorias/` en `.gitignore`.

- Auditorías recientes: sus carpetas existentes dentro de `auditorias/`.
- Entregables trasladados: `auditorias/archivo/<ruta anterior>`.
- Inventario del traslado y hashes: `auditorias/organizacion_20261016/`.

Se conservaron todos los archivos localmente. Los entregables previamente
versionados se retiraron del índice, sin reescribir el historial de Git.
Por ello, los commits anteriores todavía contienen sus versiones antiguas.

Los pequeños datos necesarios para pruebas automáticas quedan en
`test_fixtures/`, disponibles para versionar y sin dependencia de auditorías locales.
Pytest excluye `auditorias/` de la búsqueda de pruebas.

Las rutas dentro de los informes archivados describen su ubicación histórica;
el manifiesto del traslado permite localizar los archivos nuevos sin alterar
sus contenidos ni sus hashes. Las herramientas activas de validación se
actualizaron para producir evidencias en la carpeta central.
