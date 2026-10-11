"""
Carga y ETL del Export de PowerBI camiones hacia
inventar_SpcHidr.mov_cam_powerbi.

Integrado directamente en el sitio SIIR (DashReportabilidadSIIR), mismo
patron que el modulo reclamo: panel.py se cuelga en layout.py bajo un
nuevo item del sidebar, y sus callbacks quedan registrados en la app Dash
del sitio via el decorador global @callback al importarse este paquete.
"""
