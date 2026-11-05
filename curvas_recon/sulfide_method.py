"""Compatibilidad: ajuste neto local de Sulfuros.

La implementacion vive en :mod:`curvas_recon.maduras_nuevas`, que sirve a
Oxidos y Sulfuros. Esta funcion conserva la firma historica (solo Sulfuros).
"""
from .maduras_nuevas import (  # noqa: F401  (reexport)
    CoverageError, InfeasibleError, MadurasError, LAMBDA_BOUNDS, reconcile_pad,
)


def reconcile_sulfides(rows, case_start, case_end, target_net_t, *, lambda_bounds=LAMBDA_BOUNDS):
    """Fit one common drainage-profile multiplier to the Sulfides net target.

    Mature (> 30 d) piles keep the observed recovery, exactly-30 piles keep the
    official one, and younger piles scale their modelled drainage profile by a
    common lambda. See ``maduras_nuevas.reconcile_pad`` for the contract.
    """
    return reconcile_pad(rows, case_start, case_end, target_net_t,
                         pad='SULFUROS', lambda_bounds=lambda_bounds)
