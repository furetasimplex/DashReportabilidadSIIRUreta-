"""
validators.py
=============
Validaciones de integridad para datos reconciliados y ajustes
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import logging

logger = logging.getLogger(__name__)

class Validators:
    """Conjunto de validaciones para reportabilidad"""
    
    def __init__(self, tolerance: float = 0.0001):
        self.tolerance = tolerance
    
    def validate_sum_integrity(
        self,
        datos_ajustados: pd.DataFrame,
        valor_reconciliado_esperado: float,
        tolerance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Verifica que SUM(valor_final) ≈ valor_reconciliado
        
        Args:
            datos_ajustados: DataFrame con columna 'valor_final'
            valor_reconciliado_esperado: Valor esperado
            tolerance: Tolerancia permitida
        
        Returns:
            Dict con {es_valido, diferencia, porcentaje, mensaje}
        """
        
        if tolerance is None:
            tolerance = self.tolerance
        
        if datos_ajustados.empty:
            return {
                'es_valido': False,
                'suma_final': 0,
                'diferencia': valor_reconciliado_esperado,
                'porcentaje': 100,
                'mensaje': '✗ DataFrame vacío'
            }
        
        suma_final = datos_ajustados['valor_final'].sum()
        diferencia = abs(valor_reconciliado_esperado - suma_final)
        porcentaje = (diferencia / abs(valor_reconciliado_esperado) * 100) if valor_reconciliado_esperado != 0 else 0
        
        es_valido = diferencia <= abs(valor_reconciliado_esperado) * tolerance
        
        return {
            'es_valido': es_valido,
            'suma_final': round(suma_final, 4),
            'valor_esperado': round(valor_reconciliado_esperado, 4),
            'diferencia': round(diferencia, 4),
            'porcentaje': round(porcentaje, 4),
            'mensaje': (
                f'✓ Sum integrity OK: {suma_final:.4f} ≈ {valor_reconciliado_esperado:.4f}'
                if es_valido
                else f'✗ Sum mismatch: {suma_final:.4f} vs {valor_reconciliado_esperado:.4f} (Δ {diferencia:.4f})'
            )
        }
    
    def check_zero_day_adjustments(
        self,
        adjustment_detail: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """
        Detecta si se ajustaron días con valor_medido = 0
        
        Returns:
            Lista de anomalías (debería estar vacía)
        """
        
        anomalias = []
        
        if 'valor_medido' not in adjustment_detail.columns or 'ajuste' not in adjustment_detail.columns:
            return anomalias
        
        # Buscar ajustes con valor_medido = 0
        zero_adjusted = adjustment_detail[
            (adjustment_detail['valor_medido'] == 0) & 
            (adjustment_detail['ajuste'] != 0)
        ]
        
        for _, row in zero_adjusted.iterrows():
            anomalias.append({
                'tipo': 'Zero Day Adjusted',
                'fecha': row.get('fecha', 'Unknown'),
                'flujo_id': row.get('flujo_id', 'Unknown'),
                'valor_medido': 0,
                'ajuste': row.get('ajuste', 0),
                'severidad': 'ERROR'
            })
        
        if anomalias:
            logger.warning(f"⚠ Found {len(anomalias)} zero-day adjustments")
        else:
            logger.info("✓ No zero-day adjustments")
        
        return anomalias
    
    def detect_outliers(
        self,
        daily_data: pd.DataFrame,
        flujo_id: str,
        z_score_threshold: float = 3.0
    ) -> List[Dict[str, Any]]:
        """
        Detecta valores anómalos usando Z-score
        
        Args:
            daily_data: DataFrame con [fecha, flujo_id, valor_medido]
            flujo_id: ID del flujo a analizar
            z_score_threshold: Umbral de Z-score (default: 3.0)
        
        Returns:
            Lista de anomalías encontradas
        """
        
        anomalias = []
        
        flujo_data = daily_data[daily_data['flujo_id'] == flujo_id].copy()
        
        if len(flujo_data) < 3:
            return anomalias
        
        valores = flujo_data['valor_medido'].values
        media = np.mean(valores)
        std = np.std(valores)
        
        if std == 0:
            return anomalias
        
        z_scores = np.abs((valores - media) / std)
        
        for idx, (_, row) in enumerate(flujo_data.iterrows()):
            if z_scores[idx] > z_score_threshold:
                anomalias.append({
                    'tipo': 'Outlier',
                    'fecha': row.get('fecha', 'Unknown'),
                    'flujo_id': flujo_id,
                    'valor': row['valor_medido'],
                    'media': round(media, 2),
                    'z_score': round(z_scores[idx], 2),
                    'porcentaje_vs_media': round((row['valor_medido'] / media - 1) * 100, 1),
                    'severidad': 'WARNING'
                })
        
        if anomalias:
            logger.warning(f"⚠ Found {len(anomalias)} outliers in {flujo_id}")
        
        return anomalias
    
    def validate_all(
        self,
        daily_data: pd.DataFrame,
        adjustment_detail: pd.DataFrame,
        expected_total: float
    ) -> Dict[str, Any]:
        """
        Ejecuta todas las validaciones
        
        Returns:
            Dict con {es_valido, validaciones, errores, advertencias}
        """
        
        validaciones = {}
        errores = []
        advertencias = []
        
        # 1. Validación de suma
        val_suma = self.validate_sum_integrity(adjustment_detail, expected_total)
        validaciones['integridad_suma'] = val_suma
        if not val_suma['es_valido']:
            errores.append(val_suma['mensaje'])
        
        # 2. Detección de ajustes en días cero
        zero_adjusts = self.check_zero_day_adjustments(adjustment_detail)
        validaciones['ajustes_dias_cero'] = zero_adjusts
        if zero_adjusts:
            errores.extend([f"✗ Zero day adjusted on {a['fecha']}" for a in zero_adjusts])
        
        # 3. Detección de outliers
        flujos_unicos = daily_data['flujo_id'].unique() if not daily_data.empty else []
        all_outliers = []
        for flujo in flujos_unicos:
            outliers = self.detect_outliers(daily_data, flujo)
            all_outliers.extend(outliers)
        
        validaciones['outliers'] = all_outliers
        if all_outliers:
            advertencias.append(f"⚠ Found {len(all_outliers)} potential outliers")
        
        es_valido = len(errores) == 0
        
        return {
            'es_valido': es_valido,
            'validaciones': validaciones,
            'errores': errores,
            'advertencias': advertencias,
            'resumen': {
                'total_validaciones': 3,
                'validaciones_ok': sum(1 for v in validaciones.values() if not v),
                'errores': len(errores),
                'advertencias': len(advertencias)
            }
        }


# Instancia global
_validators = None

def get_validators(tolerance: float = 0.0001) -> Validators:
    """Obtiene instancia de validadores"""
    global _validators
    if _validators is None:
        _validators = Validators(tolerance=tolerance)
    return _validators
