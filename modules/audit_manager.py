"""
audit_manager.py
===============
Gestión de auditoría, trazabilidad y versionamiento de balances
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from db_connection import get_connection

logger = logging.getLogger(__name__)

class AuditManager:
    """Gestor de auditoría y trazabilidad"""
    
    def __init__(self):
        self.conn = get_connection()
    
    def record_adjustment(
        self,
        caso_balance: str,
        run_id: int,
        fecha_inicio,
        fecha_fin,
        adjustment_detail: pd.DataFrame,
        usuario: str,
        metodo_distribucion: str = 'Proporcional_Aporte_Diario',
        version_balance: int = 1
    ) -> Optional[int]:
        """
        Guarda ajustes en Audit_Ajustes_Reportabilidad
        
        Args:
            caso_balance: Identificador del caso
            run_id: ID de la ejecución de reconciliación
            fecha_inicio: Fecha de inicio del período
            fecha_fin: Fecha de fin del período
            adjustment_detail: DataFrame con detalles de ajustes
            usuario: Usuario que realiza el ajuste
            metodo_distribucion: Método usado
            version_balance: Número de versión
        
        Returns:
            audit_id del registro insertado, o None si falla
        """
        
        if not self.conn or adjustment_detail.empty:
            logger.error("✗ Cannot record adjustment: invalid connection or empty data")
            return None
        
        try:
            cursor = self.conn.cursor()
            
            for _, row in adjustment_detail.iterrows():
                sql = """
                INSERT INTO inventar_SpcHidr.Audit_Ajustes_Reportabilidad (
                    caso_balance, run_id, fecha_inicio, fecha_fin, planta,
                    flujo_id, fecha_dia, valor_medido, diferencia_reconciliada, 
                    ajuste_aplicado, porcentaje_aporte, valor_final,
                    usuario_ajuste, timestamp_ajuste, metodo_distribucion,
                    version_balance, is_active
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?
                )
                """
                
                # Extraer datos del row
                flujo_id = row.get('flujo_id', 'Unknown')
                fecha_dia = row.get('fecha')
                valor_medido = row.get('valor_medido', 0)
                ajuste = row.get('ajuste', 0)
                valor_final = row.get('valor_final', 0)
                pct_aporte = row.get('porcentaje_aporte', 0)
                
                # Obtener planta del caso_balance (si aplica)
                planta = caso_balance.split('_')[0] if '_' in caso_balance else caso_balance
                
                cursor.execute(sql, (
                    caso_balance, run_id, fecha_inicio, fecha_fin, planta,
                    flujo_id, fecha_dia, valor_medido, ajuste,
                    ajuste, pct_aporte, valor_final,
                    usuario, datetime.now(), metodo_distribucion,
                    version_balance, 1
                ))
            
            self.conn.commit()
            logger.info(f"✓ Recorded {len(adjustment_detail)} adjustment records")
            
            # Obtener el último audit_id insertado
            cursor.execute("SELECT IDENT_CURRENT('inventar_SpcHidr.Audit_Ajustes_Reportabilidad')")
            audit_id = cursor.fetchone()[0]
            return int(audit_id) if audit_id else None
            
        except Exception as e:
            logger.error(f"✗ Error recording adjustment: {e}")
            self.conn.rollback()
            return None
    
    def mark_balance_official(
        self,
        caso_balance: str,
        run_id: int,
        fecha_inicio,
        fecha_fin,
        usuario: str
    ) -> bool:
        """
        Marca un balance como oficial
        Desmarca el anterior si existe
        
        Returns:
            True si tuvo éxito, False en caso contrario
        """
        
        if not self.conn:
            logger.error("✗ Cannot mark balance official: invalid connection")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # 1. Desmarcar anterior oficial
            sql_unmark = """
            UPDATE inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            SET is_active = 0
            WHERE 
                caso_balance = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
                AND is_active = 1
            """
            cursor.execute(sql_unmark, (caso_balance, fecha_inicio, fecha_fin))
            
            # 2. Marcar nuevo como oficial
            sql_mark = """
            UPDATE inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            SET is_active = 1
            WHERE 
                caso_balance = ?
                AND run_id = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
            """
            cursor.execute(sql_mark, (caso_balance, run_id, fecha_inicio, fecha_fin))
            
            self.conn.commit()
            logger.info(f"✓ Marked balance official: run_id={run_id}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error marking balance official: {e}")
            self.conn.rollback()
            return False
    
    def get_audit_trail(
        self,
        caso_balance: str,
        run_id: int
    ) -> pd.DataFrame:
        """
        Retorna log completo de ajustes para un balance
        """
        
        if not self.conn:
            logger.error("✗ Cannot get audit trail: invalid connection")
            return pd.DataFrame()
        
        try:
            sql = """
            SELECT 
                audit_id, flujo_id, fecha_dia, valor_medido, ajuste_aplicado,
                porcentaje_aporte, valor_final, usuario_ajuste, timestamp_ajuste,
                metodo_distribucion
            FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            WHERE 
                caso_balance = ?
                AND run_id = ?
            ORDER BY fecha_dia, flujo_id
            """
            
            df = pd.read_sql(sql, self.conn, params=(caso_balance, run_id))
            logger.info(f"✓ Retrieved audit trail: {len(df)} records")
            return df
            
        except Exception as e:
            logger.warning(f"⚠ Error retrieving audit trail: {e}")
            return pd.DataFrame()
    
    def generate_trazabilidad_report(
        self,
        caso_balance: str,
        fecha_inicio,
        fecha_fin
    ) -> Dict[str, any]:
        """
        Genera reporte de auditoría para visualización
        """
        
        if not self.conn:
            return {}
        
        try:
            # Obtener todos los registros del período
            sql = """
            SELECT 
                audit_id, run_id, usuario_ajuste, timestamp_ajuste,
                COUNT(*) as cantidad_ajustes,
                SUM(ABS(ajuste_aplicado)) as suma_ajustes_abs,
                is_active
            FROM inventar_SpcHidr.Audit_Ajustes_Reportabilidad
            WHERE 
                caso_balance = ?
                AND fecha_inicio = ?
                AND fecha_fin = ?
            GROUP BY run_id, usuario_ajuste, timestamp_ajuste, is_active
            ORDER BY timestamp_ajuste DESC
            """
            
            df = pd.read_sql(sql, self.conn, 
                           params=(caso_balance, fecha_inicio, fecha_fin))
            
            if df.empty:
                return {}
            
            # Construir reporte
            reporte = {
                'caso_balance': caso_balance,
                'fecha_inicio': str(fecha_inicio),
                'fecha_fin': str(fecha_fin),
                'versiones': [],
                'resumen': {
                    'total_versiones': len(df),
                    'versiones_oficiales': int(df['is_active'].sum()),
                    'usuarios': df['usuario_ajuste'].nunique()
                }
            }
            
            for _, row in df.iterrows():
                reporte['versiones'].append({
                    'run_id': int(row['run_id']),
                    'usuario': row['usuario_ajuste'],
                    'timestamp': str(row['timestamp_ajuste']),
                    'cantidad_ajustes': int(row['cantidad_ajustes']),
                    'suma_ajustes': float(row['suma_ajustes_abs']),
                    'es_oficial': bool(row['is_active'])
                })
            
            logger.info(f"✓ Generated trazabilidad report for {caso_balance}")
            return reporte
            
        except Exception as e:
            logger.error(f"✗ Error generating trazabilidad report: {e}")
            return {}


# Instancia global
_audit_manager = None

def get_audit_manager() -> AuditManager:
    """Obtiene instancia del gestor de auditoría"""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = AuditManager()
    return _audit_manager
