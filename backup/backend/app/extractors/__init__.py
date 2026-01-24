# =============================================================================
# TO_EXTRACTOR v6.0 - ESTRATTORI PACKAGE
# =============================================================================
# Factory pattern per estrattori vendor-specifici
# =============================================================================

from typing import Dict, Type

from .base import BaseExtractor, GenericExtractor
from .angelini import AngeliniExtractor
from .bayer import BayerExtractor
from .chiesi import ChiesiExtractor
from .codifi import CodifiExtractor
from .menarini import MenariniExtractor
from .opella import OpellaExtractor


# =============================================================================
# REGISTRY ESTRATTORI
# =============================================================================

EXTRACTORS: Dict[str, Type[BaseExtractor]] = {
    'ANGELINI': AngeliniExtractor,
    'BAYER': BayerExtractor,
    'CHIESI': ChiesiExtractor,
    'CODIFI': CodifiExtractor,
    'MENARINI': MenariniExtractor,
    'OPELLA': OpellaExtractor,
    'GENERIC': GenericExtractor,
    'UNKNOWN': GenericExtractor,
}


def get_extractor(vendor: str) -> BaseExtractor:
    """
    Factory: ritorna istanza dell'estrattore per il vendor specificato.
    
    Args:
        vendor: Codice vendor (es: 'ANGELINI', 'CHIESI')
        
    Returns:
        Istanza dell'estrattore appropriato
    """
    vendor = vendor.upper() if vendor else 'GENERIC'
    extractor_class = EXTRACTORS.get(vendor, GenericExtractor)
    return extractor_class()


def get_supported_vendors() -> list:
    """Ritorna lista vendor supportati (escluso GENERIC/UNKNOWN)."""
    return [v for v in EXTRACTORS.keys() if v not in ('GENERIC', 'UNKNOWN')]


__all__ = [
    'BaseExtractor',
    'GenericExtractor',
    'AngeliniExtractor',
    'BayerExtractor',
    'ChiesiExtractor',
    'CodifiExtractor',
    'MenariniExtractor',
    'OpellaExtractor',
    'EXTRACTORS',
    'get_extractor',
    'get_supported_vendors',
]
