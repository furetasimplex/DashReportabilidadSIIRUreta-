"""Pure, database-fed M&R density recalibration contract.

This module intentionally does not read files or connect to SQL. Callers must
provide campaign-scoped observations and DB-frozen module rows already joined
by PAD/campaign/module identity. In particular, dry TMS is never treated as wet
TMH and no humidity conversion is assumed.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Iterable, Optional


class RecalibrationError(ValueError):
    """Input cannot support an as-of density calibration."""


@dataclass(frozen=True)
class ModuleObservation:
    pad_id: int
    campana_id: int
    modulo_id: int
    volume_real_m3: float
    volume_objetivo_m3: Optional[float] = None
    frozen: bool = False
    fecha_congelamiento: Optional[date] = None
    fecha_cierre: Optional[date] = None
    tmh_fijada: Optional[float] = None
    abierto_al_corte: bool = False


@dataclass(frozen=True)
class Recalibration:
    pad_id: int
    campana_id: int
    fecha_corte: date
    density_tmh_per_m3: Optional[float]
    total_tmh: float
    fixed_tmh: float
    adjustable_volume_real_m3: float
    targets_tmh: dict[int, Optional[float]]


def calibrate_density(total_tmh: float, modules: Iterable[ModuleObservation], *,
                      pad_id: int, campana_id: int, cutoff: date) -> Recalibration:
    """Calibrate rho = (global TMH - frozen TMH) / remaining real volume.

    Frozen modules count as fixed only when both their DB freeze/close dates
    are known and no later than the case cutoff. A frozen row needs directly
    linked TMH; TMS and an undocumented humidity field are insufficient.
    The open final module is deliberately returned without a future target.
    """
    rows = list(modules)
    if not rows:
        raise RecalibrationError("No hay módulos observados para PAD/campaña al corte.")
    try:
        global_wet = float(total_tmh)
    except (TypeError, ValueError, OverflowError):
        global_wet = math.nan
    if not math.isfinite(global_wet) or global_wet < 0:
        raise RecalibrationError("TMH global debe ser finita y no negativa.")
    keys = [(r.pad_id, r.campana_id, r.modulo_id) for r in rows]
    if len(keys) != len(set(keys)):
        raise RecalibrationError("Identidad módulo duplicada en la calibración.")
    if any((r.pad_id, r.campana_id) != (pad_id, campana_id) for r in rows):
        raise RecalibrationError("La calibración mezcla PAD o campaña.")

    fixed = []
    adjustable = []
    open_rows = [r for r in rows if r.abierto_al_corte]
    if len(open_rows) > 1:
        raise RecalibrationError("Hay más de un módulo abierto al corte; la secuencia es ambigua.")
    for row in rows:
        v = float(row.volume_real_m3)
        if not math.isfinite(v) or v < 0:
            raise RecalibrationError(f"Módulo {row.modulo_id}: volumen real inválido.")
        if row.frozen and (row.fecha_congelamiento is None or row.fecha_cierre is None):
            raise RecalibrationError(
                f"Módulo congelado {row.modulo_id}: faltan fechas de congelamiento/cierre para el corte.")
        is_fixed = (row.frozen and row.fecha_congelamiento <= cutoff
                    and row.fecha_cierre <= cutoff)
        if is_fixed:
            if row.tmh_fijada is None:
                raise RecalibrationError(
                    f"Módulo congelado {row.modulo_id}: falta TMH fijada directa en DB; "
                    "no se convierte TMS a TMH sin humedad con unidad acreditada.")
            wet = float(row.tmh_fijada)
            if not math.isfinite(wet) or wet < 0:
                raise RecalibrationError(f"Módulo congelado {row.modulo_id}: TMH fijada inválida.")
            fixed.append((row, wet))
        else:
            adjustable.append(row)

    fixed_tmh = sum(wet for _, wet in fixed)
    volume = sum(float(row.volume_real_m3) for row in adjustable)
    if global_wet + 1e-9 < fixed_tmh:
        raise RecalibrationError("TMH fijada excede la TMH global observada al corte.")
    remaining_wet = max(0.0, global_wet - fixed_tmh)
    if not adjustable:
        if not math.isclose(remaining_wet, 0.0, rel_tol=0.0, abs_tol=1e-7):
            raise RecalibrationError("Toda la campaña está fijada, pero queda TMH global sin asignar.")
        return Recalibration(pad_id=pad_id, campana_id=campana_id, fecha_corte=cutoff,
            density_tmh_per_m3=None, total_tmh=global_wet, fixed_tmh=fixed_tmh,
            adjustable_volume_real_m3=0.0,
            targets_tmh={row.modulo_id: wet for row, wet in fixed})
    if not math.isfinite(volume) or volume <= 0:
        raise RecalibrationError("Volumen real ajustable debe ser positivo al corte.")
    density = remaining_wet / volume
    if not math.isfinite(density) or density < 0:
        raise RecalibrationError("La densidad recalibrada debe ser finita y no negativa.")

    targets = {}
    for row in adjustable:
        if row.abierto_al_corte:
            targets[row.modulo_id] = None
            continue
        if row.volume_objetivo_m3 is None:
            raise RecalibrationError(
                f"Módulo {row.modulo_id}: falta volumen objetivo DB para calcular su meta TMH.")
        goal_volume = float(row.volume_objetivo_m3)
        if not math.isfinite(goal_volume) or goal_volume < 0:
            raise RecalibrationError(f"Módulo {row.modulo_id}: volumen objetivo inválido.")
        targets[row.modulo_id] = density * goal_volume
    for row, wet in fixed:
        targets[row.modulo_id] = wet

    return Recalibration(pad_id=pad_id, campana_id=campana_id, fecha_corte=cutoff,
        density_tmh_per_m3=density, total_tmh=float(total_tmh), fixed_tmh=fixed_tmh,
        adjustable_volume_real_m3=volume, targets_tmh=targets)
