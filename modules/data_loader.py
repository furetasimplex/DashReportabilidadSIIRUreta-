"""
data_loader.py
==============
Módulo para cargar datos desde SQL Server para el pipeline de
Reconciliación y Ajustes (reportabilidad post-balance).

IMPORTANTE - ARQUITECTURA REAL (descubierta en sesión de depuración 2026-09-09):

Existen DOS sistemas de "caso" completamente separados en la BD:

1. DEV_SIIR.hidro.recon_caso / recon_caso_oficial / recon_resultado_flujo
   -> el caso y las corridas del SOLVER (GEKKO/APMonitor) que hace la
      reconciliación de balance de masa. Tiene su propio id entero.

2. inventar_SpcHidr.casos_balance / Data_balance_rec / rep_prod_targets /
   rep_prod_reglas / rep_prod_ajustado_stg / rep_prod_ajustado /
   rep_prod_ajuste_log
   -> el caso y las corridas del PIPELINE DE AJUSTE/REPORTABILIDAD (este
      dashboard). Tiene su PROPIO caso_id, en un espacio de IDs DISTINTO
      al de recon_caso (un mismo número, ej. 70, puede existir en uno y
      no en el otro).

Esta pestaña (Reconciliación y Ajustes / Datos Reconciliados) pertenece al
sistema (2). El dropdown "Caso Balance" debe listar inventar_SpcHidr.casos_balance,
NO DEV_SIIR.hidro.recon_caso.

El cálculo real del reparto proporcional (chancado/sal/finos, motor de
reglas data-driven vía inventar_SpcHidr.rep_prod_reglas) vive en
ajuste_reporte/rep_prod_adjuster.py (motor recuperado y reinstalado el
2026-09-09 a partir del script original de Luis). Este módulo NO reimplementa
esa lógica: la reutiliza.

Usa el motor de conexión centralizado del proyecto (db_connection.get_engine()).
"""

import pandas as pd
import logging

from db_connection import get_engine

logger = logging.getLogger(__name__)

# Sentinel usado en el dropdown de Run ID para indicar "ejecutar un ajuste
# nuevo ahora" en vez de ver una corrida ya existente.
RUN_ID_NUEVO = "__NUEVO_AJUSTE__"


class DataLoader:
    """Cargador singleton de datos desde SQL Server"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataLoader, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            # Reutiliza el engine centralizado del proyecto (db_connection.py)
            self.engine = get_engine()

            if self.engine is not None:
                logger.info("✓ DataLoader inicializado - conexión a BD establecida (via db_connection.get_engine)")
                self._initialized = True
            else:
                logger.error("✗ get_engine() devolvió None - revisar variables SQLSERVER_* en .env")
                self._initialized = False
        except Exception as e:
            logger.error(f"✗ Error inicializando DataLoader: {e}")
            self.engine = None
            self._initialized = False

    # ========================================================================
    # CASOS DE BALANCE (pipeline de ajuste/reportabilidad)
    # ========================================================================

    def get_available_casos(self):
        """
        Obtiene los casos de balance desde DEV_SIIR.hidro.recon_caso
        (join con recon_caso_oficial). ESTE es el catalogo de casos que
        debe verse en el dropdown "Caso Balance" (confirmado por Luis
        2026-09-09 tras una regresion en la que se habia cambiado por
        error a inventar_SpcHidr.casos_balance).

        OJO - pendiente de resolver: inventar_SpcHidr.casos_balance (que
        usa el motor de ajuste rep_prod_* / sp_rep_get_periodo_caso) tiene
        su PROPIO caso_id, en un espacio de IDs que no siempre coincide
        con recon_caso.id (ver test_cruce_casos.py). Falta definir el
        puente entre ambos antes de que "Procesar" funcione para un caso
        elegido desde este dropdown.

        Returns:
            DataFrame con columnas: [id, nombre_caso, fecha_inicio, fecha_fin, estado]
        """
        try:
            if not self.engine:
                logger.warning("Sin conexión a BD")
                return pd.DataFrame()

            query = """
            SELECT DISTINCT
                rc.id,
                rc.nombre_caso,
                rc.fecha_inicio,
                rc.fecha_fin,
                rc.estado
            FROM [DEV_SIIR].[hidro].[recon_caso] rc
            INNER JOIN [DEV_SIIR].[hidro].[recon_caso_oficial] rco
                ON rc.id = rco.caso_id
            ORDER BY rc.nombre_caso
            """

            df = pd.read_sql(query, self.engine)
            logger.info(f"✓ Casos cargados: {len(df)} opciones desde DEV_SIIR.hidro.recon_caso")
            return df

        except Exception as e:
            logger.error(f"✗ Error obteniendo casos: {e}")
            logger.error("   Asegúrate que DEV_SIIR.hidro.recon_caso y recon_caso_oficial existen")
            return pd.DataFrame()

    def get_available_runs(self, caso_balance, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene el historial de corridas EXITOSAS del motor de ajuste
        (inventar_SpcHidr.rep_prod_ajuste_log) para un caso_id dado.

        Args:
            caso_balance: caso_id (de inventar_SpcHidr.casos_balance)

        Returns:
            DataFrame con columnas alineadas a los nombres que ya esperan
            los callbacks existentes: [solver_run_id, oficializado_en, comentario]
            (aquí solver_run_id es en realidad el run_id GUID del ajuste,
            y oficializado_en es ts_inicio de la corrida)
        """
        try:
            if not self.engine:
                logger.warning("Sin conexión a BD")
                return pd.DataFrame()

            query = """
            SELECT
                CAST(run_id AS VARCHAR(36)) AS solver_run_id,
                ts_inicio AS oficializado_en,
                mensaje AS comentario
            FROM inventar_SpcHidr.rep_prod_ajuste_log
            WHERE caso_id = ?
              AND ok = 1
            ORDER BY ts_inicio DESC
            """

            params = (caso_balance,)  # tupla: SQLAlchemy trata una lista como executemany
            df = pd.read_sql(query, self.engine, params=params)
            logger.info(f"✓ Runs cargados: {len(df)} corridas exitosas para caso_id={caso_balance}")
            return df

        except Exception as e:
            logger.error(f"✗ Error obteniendo runs: {e}")
            return pd.DataFrame()

    # ========================================================================
    # EJECUCIÓN DEL MOTOR DE AJUSTE (ajuste_reporte/rep_prod_adjuster.py)
    # ========================================================================

    def ejecutar_nuevo_ajuste(self, caso_id, version_reglas=1):
        """
        Ejecuta una corrida NUEVA del motor de reparto proporcional para un
        caso del SOLVER NUEVO (DEV_SIIR.hidro.recon_caso, el que aparece en
        el dropdown "Caso Balance"): toma el periodo y el solver_run_id
        oficial desde recon_caso_oficial, calcula los targets directo desde
        recon_resultado_flujo (puente agregado 2026-09-09 - ver docstring
        de ajuste_reporte.rep_prod_adjuster.run_ajuste_reporte_prod_solver_nuevo),
        carga Datos_conciliados_of del periodo, aplica rep_prod_reglas,
        escribe rep_prod_ajustado_stg y hace merge a rep_prod_ajustado.

        Returns:
            dict {ok, run_id, caso_id, totales}
        Raises:
            Exception si falla (el motor ya deja el detalle en
            rep_prod_ajuste_log.mensaje antes de relanzar)
        """
        from ajuste_reporte.rep_prod_adjuster import run_ajuste_reporte_prod_solver_nuevo
        return run_ajuste_reporte_prod_solver_nuevo(int(caso_id), version_reglas=version_reglas)

    def get_reconciliation_results(self, caso_balance, run_id, fecha_inicio=None, fecha_fin=None):
        """
        Obtiene los datos diarios AJUSTADOS (post reparto proporcional)
        para un run_id ya ejecutado, desde rep_prod_ajustado_stg (con
        fallback a rep_prod_ajustado).

        Returns:
            DataFrame ancho: Fecha + columnas de KPI (Chancado_TMS_Real,
            Sal_*, Apilado_*, Ley_CuT_Real, Cobre_fino_Apilado_Real, ...)
            + factor_chancado/factor_sal/factor_finos
        """
        try:
            if not self.engine:
                logger.warning("Sin conexión a BD")
                return pd.DataFrame()

            from ajuste_reporte.rep_prod_adjuster import read_ajustado_run_df
            df = read_ajustado_run_df(self.engine, int(caso_balance), str(run_id))
            logger.info(f"✓ Datos ajustados cargados: {len(df)} días para run_id={run_id}")
            return df

        except Exception as e:
            logger.error(f"✗ Error obteniendo datos de reconciliación: {e}")
            return pd.DataFrame()

    def get_daily_measured_data(self, fecha_inicio, fecha_fin):
        """
        Obtiene los datos diarios MEDIDOS/PLAN sin ajustar, desde
        inventar_SpcHidr.Datos_conciliados_of (tabla continua, sin caso_id,
        una fila por Fecha) - útil para comparar contra los ajustados.
        """
        try:
            if not self.engine:
                logger.warning("Sin conexión a BD")
                return pd.DataFrame()

            from ajuste_reporte.rep_prod_adjuster import load_query1_all_cols
            df = load_query1_all_cols(self.engine, fecha_inicio, fecha_fin)
            logger.info(f"✓ Datos medidos cargados: {len(df)} días")
            return df

        except Exception as e:
            logger.error(f"✗ Error obteniendo datos medidos: {e}")
            return pd.DataFrame()

    def get_resumen_comparativo(self, caso_id, run_id):
        """
        Resumen comparativo ajustado vs. target por métrica (chancado, sal,
        finos, reclamo, SRR), con estado OK/DESVIADO/SIN_TARGET por fila.
        Ver ajuste_reporte.rep_prod_adjuster.build_resumen_comparativo_run.
        """
        from ajuste_reporte.rep_prod_adjuster import build_resumen_comparativo_run
        return build_resumen_comparativo_run(int(caso_id), str(run_id))

    def marcar_run_oficial(self, caso_id, run_id, usuario, resumen=None):
        """
        Publica un run como la versión oficial vigente para su periodo
        (copia rep_prod_ajustado_stg -> Datos_conciliados_of_ver vía
        sp_rep_publish_oficial_validado). Sólo debe haber un oficial por
        periodo (el SP se encarga de eso).
        """
        from ajuste_reporte.rep_prod_adjuster import publicar_run_oficial
        return publicar_run_oficial(int(caso_id), str(run_id), usuario, resumen)

    def get_historial_ajustes(self, caso_id):
        """
        Historial COMPLETO (éxitos y fallos) de corridas del motor de ajuste
        para un caso, desde rep_prod_ajuste_log - sirve como trazabilidad
        de auditoría.
        """
        try:
            if not self.engine:
                return pd.DataFrame()
            query = """
            SELECT
                CAST(run_id AS VARCHAR(36)) AS run_id,
                caso_id,
                fecha_ini,
                fecha_fin,
                ts_inicio,
                ts_fin,
                ok,
                mensaje
            FROM inventar_SpcHidr.rep_prod_ajuste_log
            WHERE caso_id = ?
            ORDER BY ts_inicio DESC
            """
            df = pd.read_sql(query, self.engine, params=(caso_id,))
            return df
        except Exception as e:
            logger.error(f"✗ Error obteniendo historial de ajustes: {e}")
            return pd.DataFrame()


# Instancia singleton global
_data_loader = None


def get_data_loader():
    """Obtiene la instancia singleton del DataLoader"""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader
