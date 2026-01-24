# =============================================================================
# SERV.O v7.0 - UTILS/VENDOR
# =============================================================================
# Funzioni helper per vendor
# =============================================================================

from ..config import VENDOR_PIVA_EXCLUDE
from .codes import normalize_piva


def is_vendor_piva(vendor: str, piva: str) -> bool:
    """
    Verifica se una P.IVA appartiene al vendor (da escludere).

    Args:
        vendor: Codice vendor
        piva: P.IVA da verificare

    Returns:
        True se è P.IVA del vendor (non del cliente)
    """
    vendor_piva = VENDOR_PIVA_EXCLUDE.get(vendor.upper())
    if not vendor_piva:
        return False

    # Confronta normalizzate
    piva_norm = normalize_piva(piva)
    vendor_piva_norm = normalize_piva(vendor_piva)

    return piva_norm == vendor_piva_norm
