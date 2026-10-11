"""
versioning.py
=============
Control de versiones de balances.
Asegura que solo existe un balance oficial por período.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from db_connection import get_connection

logger = logging.getLogger(__name__)

class VersionControl:
    """Gestor de versiones de balances"""
    
    def __init__(self):
        self.conn = get_connection()
    
    def get_active_version(
        self,
        caso_balance: str,
        fecha_inicio,
        fecha_fin
    ) -> Optional[int]:
        """
        Retorna run_id del balance oficial activo
        
        Returns:
            run_id del balance oficial, o None si no existe
        """
        
        if not self.conn:
            logger.error("✗ Cannot get active version: invalid connection")
            return None
        
        try:
            sql = """
            SELECT DISTINCT run_id
            FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            WHERE 
                caso_balance = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
                AND is_active = 1
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql, (caso_balance, fecha_inicio, fecha_fin))
            result = cursor.fetchone()
            
            if result:
                logger.info(f"✓ Active version found: run_id={result[0]}")
                return int(result[0])
            else:
                logger.info(f"⚠ No active version for {caso_balance}")
                return None
                
        except Exception as e:
            logger.error(f"✗ Error getting active version: {e}")
            return None
    
    def list_all_versions(
        self,
        caso_balance: str,
        fecha_inicio,
        fecha_fin
    ) -> pd.DataFrame:
        """
        Retorna todas las versiones del balance (oficial y archivadas)
        """
        
        if not self.conn:
            logger.error("✗ Cannot list versions: invalid connection")
            return pd.DataFrame()
        
        try:
            sql = """
            SELECT 
                run_id,
                MIN(timestamp_ajuste) as fecha_creacion,
                COUNT(*) as cantidad_registros,
                SUM(ABS(ajuste_aplicado)) as suma_ajustes,
                CASE WHEN MAX(CAST(is_active AS INT)) = 1 THEN 'OFICIAL' ELSE 'ARCHIVADO' END as estado,
                MAX(usuario_ajuste) as usuario
            FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            WHERE 
                caso_balance = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
            GROUP BY run_id
            ORDER BY run_id DESC
            """
            
            df = pd.read_sql(sql, self.conn, 
                           params=(caso_balance, fecha_inicio, fecha_fin))
            
            logger.info(f"✓ Listed {len(df)} versions")
            return df
            
        except Exception as e:
            logger.warning(f"⚠ Error listing versions (tabla puede no existir): {e}")
            return pd.DataFrame()
    
    def compare_versions(
        self,
        caso_balance: str,
        fecha_inicio,
        fecha_fin,
        run_id_1: int,
        run_id_2: int
    ) -> Dict[str, any]:
        """
        Compara dos versiones de balance
        
        Returns:
            Dict con diferencias día a día, impacto en reportes
        """
        
        if not self.conn:
            return {}
        
        try:
            # Obtener datos de ambas versiones
            sql = """
            SELECT 
                fecha_dia, flujo_id, valor_final
            FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            WHERE 
                caso_balance = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
                AND run_id = ?
            ORDER BY fecha_dia, flujo_id
            """
            
            df1 = pd.read_sql(sql, self.conn, 
                            params=(caso_balance, fecha_inicio, fecha_fin, run_id_1))
            df2 = pd.read_sql(sql, self.conn, 
                            params=(caso_balance, fecha_inicio, fecha_fin, run_id_2))
            
            if df1.empty or df2.empty:
                return {
                    'mensaje': 'Una o ambas versiones están vacías',
                    'es_comparable': False
                }
            
            # Merge y comparación
            df_compare = df1.merge(df2, on=['fecha_dia', 'flujo_id'], 
                                  how='outer', suffixes=('_v1', '_v2'))
            df_compare['diferencia'] = df_compare['valor_final_v2'] - df_compare['valor_final_v1']
            df_compare['porcentaje'] = (
                df_compare['diferencia'] / df_compare['valor_final_v1'] * 100
            ).where(df_compare['valor_final_v1'] != 0, 0)
            
            # Resumen
            dias_diferentes = len(df_compare[df_compare['diferencia'] != 0])
            suma_diferencias = df_compare['diferencia'].sum()
            max_diferencia = df_compare['diferencia'].abs().max()
            
            reporte = {
                'run_id_1': run_id_1,
                'run_id_2': run_id_2,
                'es_comparable': True,
                'resumen': {
                    'dias_diferentes': dias_diferentes,
                    'dias_totales': len(df_compare),
                    'suma_diferencias': round(suma_diferencias, 4),
                    'max_diferencia': round(max_diferencia, 4),
                    'porcentaje_cambio': round(abs(suma_diferencias) / df1['valor_final'].sum() * 100, 4)
                },
                'diferencias_dia_a_dia': df_compare[df_compare['diferencia'] != 0][
                    ['fecha_dia', 'flujo_id', 'valor_final_v1', 'valor_final_v2', 'diferencia']
                ].to_dict('records') if dias_diferentes > 0 else []
            }
            
            logger.info(f"✓ Compared versions: {dias_diferentes} days different")
            return reporte
            
        except Exception as e:
            logger.error(f"✗ Error comparing versions: {e}")
            return {'error': str(e)}
    
    def archive_version(
        self,
        caso_balance: str,
        run_id: int,
        fecha_inicio,
        fecha_fin
    ) -> bool:
        """
        Archiva una versión (marca como no oficial)
        """
        
        if not self.conn:
            return False
        
        try:
            sql = """
            UPDATE inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            SET is_active = 0
            WHERE 
                caso_balance = ?
                AND run_id = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
            """
            
            cursor = self.conn.cursor()
            cursor.execute(sql, (caso_balance, run_id, fecha_inicio, fecha_fin))
            self.conn.commit()
            
            logger.info(f"✓ Archived version: run_id={run_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error archiving version: {e}")
            self.conn.rollback()
            return False


# Instancia global
_version_control = None

def get_version_control() -> VersionControl:
    """Obtiene instancia del control de versiones"""
    global _version_control
    if _version_control is None:
        _version_control = VersionControl()
    return _version_control
