"""
data_loader.py
==============
Carga datos de reconciliación desde SQL Server.
Incluye datos de DEV_SIIR.hidro.recon_resultado_flujo y 
datos diarios de inventar_SpcHidr.Datos_conciliados_of
"""

import pandas as pd
from datetime import date
from typing import Tuple, Dict, List, Optional
from db_connection import get_engine
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    """Cargador de datos para reportabilidad post-balance"""
    
    def __init__(self):
        self.engine = get_engine()
    
    def get_reconciliation_results(
        self,
        caso_balance: str,
        run_id: int,
        fecha_inicio: date,
        fecha_fin: date
    ) -> pd.DataFrame:
        """
        Consulta DEV_SIIR.hidro.recon_resultado_flujo
        
        Retorna:
            DataFrame con columnas:
            - flujo_id: ID del flujo
            - valor_medido: Suma de valores medidos en el período
            - valor_reconciliado: Suma de valores reconciliados
            - diferencia: valor_reconciliado - valor_medido
            - error_%: Porcentaje de error
        """
        query = """
        SELECT 
            flujo_id,
            SUM(valor_medido) as valor_medido,
            SUM(valor_reconciliado) as valor_reconciliado,
            SUM(valor_reconciliado) - SUM(valor_medido) as diferencia,
            CASE 
                WHEN SUM(valor_medido) = 0 THEN 0
                ELSE (SUM(valor_reconciliado) - SUM(valor_medido)) / SUM(valor_medido) * 100
            END as error_pct
        FROM DEV_SIIR.hidro.recon_resultado_flujo
        WHERE 
            caso_balance = @caso_balance
            AND run_id = @run_id
            AND fecha >= @fecha_inicio
            AND fecha <= @fecha_fin
        GROUP BY flujo_id
        ORDER BY flujo_id
        """
        
        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={
                    'caso_balance': caso_balance,
                    'run_id': run_id,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            )
            logger.info(f"✓ Reconciliation results loaded: {len(df)} flujos")
            return df
        except Exception as e:
            logger.error(f"✗ Error loading reconciliation results: {e}")
            raise
    
    def get_daily_measured_data(
        self,
        caso_balance: str,
        fecha_inicio: date,
        fecha_fin: date
    ) -> pd.DataFrame:
        """
        Consulta inventar_SpcHidr.Datos_conciliados_of
        Obtiene datos diarios medidos por flujo
        
        Retorna:
            DataFrame con columnas:
            - fecha: Fecha del día
            - flujo_id: ID del flujo
            - valor_medido: Valor medido en ese día
        """
        query = """
        SELECT 
            CAST(fecha AS DATE) as fecha,
            flujo_id,
            SUM(valor) as valor_medido
        FROM inventar_SpcHidr.Datos_conciliados_of
        WHERE 
            caso_balance = @caso_balance
            AND fecha >= @fecha_inicio
            AND fecha <= @fecha_fin
            AND valor > 0  -- Excluir días con valor = 0
        GROUP BY 
            CAST(fecha AS DATE),
            flujo_id
        ORDER BY 
            CAST(fecha AS DATE),
            flujo_id
        """
        
        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={
                    'caso_balance': caso_balance,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            )
            logger.info(f"✓ Daily measured data loaded: {len(df)} registros")
            return df
        except Exception as e:
            logger.error(f"✗ Error loading daily measured data: {e}")
            raise
    
    def get_available_runs(
        self,
        caso_balance: str,
        fecha_inicio: date,
        fecha_fin: date
    ) -> pd.DataFrame:
        """
        Obtiene todos los run_id disponibles para un período
        Incluye información de cuál es oficial
        """
        query = """
        SELECT DISTINCT
            run_id,
            CASE WHEN is_official = 1 THEN 'OFICIAL' ELSE 'Archivado' END as estado,
            COUNT(*) as cantidad_registros,
            MAX(timestamp_ejecucion) as ultima_ejecucion
        FROM DEV_SIIR.hidro.recon_resultado_flujo
        WHERE 
            caso_balance = @caso_balance
            AND fecha >= @fecha_inicio
            AND fecha <= @fecha_fin
        GROUP BY run_id, is_official
        ORDER BY run_id DESC
        """
        
        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={
                    'caso_balance': caso_balance,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin
                }
            )
            logger.info(f"✓ Available runs loaded: {len(df)} versiones")
            return df
        except Exception as e:
            logger.error(f"✗ Error loading available runs: {e}")
            raise
    
    def get_audit_history(
        self,
        caso_balance: str,
        fecha_inicio: date,
        fecha_fin: date,
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Consulta Audit_Ajustes_Reportabilidad
        Retorna historial de ajustes aplicados
        """
        query = """
        SELECT TOP (@limit)
            audit_id,
            caso_balance,
            run_id,
            fecha_inicio,
            fecha_fin,
            flujo_id,
            fecha_dia,
            usuario_ajuste,
            timestamp_ajuste,
            metodo_distribucion,
            version_balance,
            is_active
        FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
        WHERE 
            caso_balance = @caso_balance
            AND fecha_inicio = @fecha_inicio
            AND fecha_fin = @fecha_fin
        ORDER BY timestamp_ajuste DESC
        """
        
        try:
            df = pd.read_sql(
                query,
                self.engine,
                params={
                    'caso_balance': caso_balance,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'limit': limit
                }
            )
            logger.info(f"✓ Audit history loaded: {len(df)} registros")
            return df
        except Exception as e:
            logger.error(f"✗ Error loading audit history: {e}")
            return pd.DataFrame()  # Retornar vacío si tabla no existe aún


# Instancia global para uso en callbacks
_data_loader = None

def get_data_loader() -> DataLoader:
    """Obtiene instancia del DataLoader (singleton)"""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoader()
    return _data_loader
