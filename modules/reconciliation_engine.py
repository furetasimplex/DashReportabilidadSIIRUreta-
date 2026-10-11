"""
reconciliation_engine.py
=======================
Implementa la lógica de distribución proporcional de diferencias
según aporte diario de cada flujo.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)

class ReconciliationEngine:
    """Motor de reconciliación y distribución de ajustes"""
    
    def __init__(self, tolerance: float = 0.0001):
        """
        Args:
            tolerance: Tolerancia de redondeo (default: 0.01%)
        """
        self.tolerance = tolerance
    
    def calculate_daily_contributions(
        self,
        daily_data: pd.DataFrame,
        flujo_id: str
    ) -> pd.DataFrame:
        """
        Calcula el % aporte diario para un flujo específico
        
        Args:
            daily_data: DataFrame con [fecha, flujo_id, valor_medido]
            flujo_id: ID del flujo a analizar
        
        Returns:
            DataFrame con [fecha, flujo_id, valor_medido, porcentaje_aporte]
        """
        
        # Filtrar datos del flujo
        flujo_data = daily_data[daily_data['flujo_id'] == flujo_id].copy()
        
        if flujo_data.empty:
            logger.warning(f"⚠ No data found for flujo_id: {flujo_id}")
            return pd.DataFrame()
        
        # Total del flujo en el período
        total_flujo = flujo_data['valor_medido'].sum()
        
        if total_flujo == 0:
            logger.warning(f"⚠ Total flujo is zero for {flujo_id}")
            return flujo_data.assign(porcentaje_aporte=0)
        
        # Calcular % aporte
        flujo_data['porcentaje_aporte'] = (
            (flujo_data['valor_medido'] / total_flujo) * 100
        ).round(4)
        
        # Validar que suma = 100%
        suma_pct = flujo_data['porcentaje_aporte'].sum()
        if abs(suma_pct - 100) > 0.01:
            logger.warning(f"⚠ Contribution sum for {flujo_id}: {suma_pct:.4f}% (expected 100%)")
        
        logger.info(f"✓ Daily contributions calculated for {flujo_id}")
        return flujo_data
    
    def apply_proportional_adjustment(
        self,
        daily_data: pd.DataFrame,
        total_difference: float,
        flujo_id: str,
        tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Distribuye la diferencia proporcionalmente según aporte diario
        
        Args:
            daily_data: DataFrame con [fecha, flujo_id, valor_medido, porcentaje_aporte]
            total_difference: valor_reconciliado - valor_medido (diferencia total)
            flujo_id: ID del flujo a ajustar
            tolerance: Tolerancia de redondeo (usa self.tolerance si None)
        
        Returns:
            Dict con:
            {
                'datos_ajustados': DataFrame con columnas [fecha, flujo_id, valor_medido, ajuste, valor_final],
                'ajustes_detalle': DataFrame con detalles de cada ajuste,
                'validacion': {
                    'sum_ajustes': float,
                    'diferencia_residual': float,
                    'es_valido': bool,
                    'mensaje': str
                }
            }
        """
        
        if tolerance is None:
            tolerance = self.tolerance
        
        # Filtrar datos del flujo
        flujo_data = daily_data[daily_data['flujo_id'] == flujo_id].copy()
        
        if flujo_data.empty:
            return {
                'datos_ajustados': pd.DataFrame(),
                'ajustes_detalle': pd.DataFrame(),
                'validacion': {
                    'sum_ajustes': 0,
                    'diferencia_residual': total_difference,
                    'es_valido': False,
                    'mensaje': f'No data found for flujo_id: {flujo_id}'
                }
            }
        
        # Asegurar que tiene porcentajes (calcularlos si no)
        if 'porcentaje_aporte' not in flujo_data.columns:
            flujo_data = self.calculate_daily_contributions(daily_data, flujo_id)
        
        # Calcular ajuste para cada día
        ajustes = []
        for idx, row in flujo_data.iterrows():
            pct_aporte = row['porcentaje_aporte']
            ajuste_dia = (total_difference * pct_aporte) / 100
            ajustes.append(ajuste_dia)
        
        flujo_data['ajuste'] = ajustes
        flujo_data['valor_final'] = flujo_data['valor_medido'] + flujo_data['ajuste']
        
        # Validación: suma de ajustes ≈ diferencia total
        suma_ajustes = flujo_data['ajuste'].sum()
        diferencia_residual = abs(total_difference - suma_ajustes)
        
        es_valido = diferencia_residual <= abs(total_difference) * tolerance
        
        validacion = {
            'sum_ajustes': round(suma_ajustes, 4),
            'diferencia_residual': round(diferencia_residual, 4),
            'es_valido': es_valido,
            'mensaje': (
                f'✓ Distribución válida' if es_valido
                else f'✗ Distribución fuera de tolerancia: residual {diferencia_residual:.4f}'
            )
        }
        
        if es_valido:
            logger.info(f"✓ Adjustment distribution valid for {flujo_id}")
        else:
            logger.warning(f"⚠ {validacion['mensaje']}")
        
        return {
            'datos_ajustados': flujo_data[['fecha', 'flujo_id', 'valor_medido', 'ajuste', 'valor_final']],
            'ajustes_detalle': flujo_data[['fecha', 'flujo_id', 'valor_medido', 'porcentaje_aporte', 'ajuste', 'valor_final']],
            'validacion': validacion
        }
    
    def process_all_flujos(
        self,
        daily_data: pd.DataFrame,
        recon_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Procesa todos los flujos de una vez
        
        Args:
            daily_data: DataFrame con datos diarios [fecha, flujo_id, valor_medido]
            recon_data: DataFrame con reconciliación [flujo_id, diferencia]
        
        Returns:
            Dict con:
            {
                'ajustes_por_flujo': {flujo_id: resultado},
                'resumen': {
                    'total_flujos': int,
                    'flujos_validos': int,
                    'flujos_invalidos': int,
                    'suma_total_ajustes': float
                },
                'datos_consolidados': DataFrame
            }
        """
        
        ajustes_por_flujo = {}
        datos_consolidados = []
        suma_total = 0
        flujos_validos = 0
        flujos_invalidos = 0
        
        for _, row in recon_data.iterrows():
            flujo_id = row['flujo_id']
            diferencia = row['diferencia']
            
            resultado = self.apply_proportional_adjustment(
                daily_data,
                diferencia,
                flujo_id
            )
            
            ajustes_por_flujo[flujo_id] = resultado
            
            if not resultado['datos_ajustados'].empty:
                datos_consolidados.append(resultado['datos_ajustados'])
            
            if resultado['validacion']['es_valido']:
                flujos_validos += 1
                suma_total += resultado['validacion']['sum_ajustes']
            else:
                flujos_invalidos += 1
        
        # Consolidar datos
        if datos_consolidados:
            df_consolidado = pd.concat(datos_consolidados, ignore_index=True)
        else:
            df_consolidado = pd.DataFrame()
        
        resumen = {
            'total_flujos': len(recon_data),
            'flujos_validos': flujos_validos,
            'flujos_invalidos': flujos_invalidos,
            'suma_total_ajustes': round(suma_total, 4)
        }
        
        logger.info(f"✓ Processed {resumen['total_flujos']} flujos: {flujos_validos} valid, {flujos_invalidos} invalid")
        
        return {
            'ajustes_por_flujo': ajustes_por_flujo,
            'resumen': resumen,
            'datos_consolidados': df_consolidado
        }


# Instancia global
_engine = None

def get_reconciliation_engine(tolerance: float = 0.0001) -> ReconciliationEngine:
    """Obtiene instancia del motor de reconciliación"""
    global _engine
    if _engine is None:
        _engine = ReconciliationEngine(tolerance=tolerance)
    return _engine
