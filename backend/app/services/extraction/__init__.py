# =============================================================================
# SERV.O v7.0 - EXTRACTION PACKAGE
# =============================================================================
# Factory pattern unificato per estrattori PDF
# Sostituisce e unifica:
#   - app/extractors/          (deprecato)
#   - app/services/extractors/ (deprecato)
# =============================================================================

from typing import Callable, Dict, List

from .detector import detect_vendor, get_supported_vendors
from .vendors import (
    extract_angelini,
    extract_bayer,
    extract_chiesi,
    extract_codifi,
    extract_cooper,
    extract_opella,
    extract_menarini,
    extract_doc_generici,
    extract_generic,
)


# =============================================================================
# REGISTRY ESTRATTORI
# =============================================================================

EXTRACTORS: Dict[str, Callable] = {
    'ANGELINI': extract_angelini,
    'BAYER': extract_bayer,
    'CHIESI': extract_chiesi,
    'CODIFI': extract_codifi,
    'COOPER': extract_cooper,
    'DOC_GENERICI': extract_doc_generici,
    'MENARINI': extract_menarini,
    'OPELLA': extract_opella,
    'GENERIC': extract_generic,
    'UNKNOWN': extract_generic,
}


def get_extractor(vendor: str) -> Callable:
    """
    Factory: ritorna funzione estrattore per il vendor specificato.

    Args:
        vendor: Codice vendor (es: 'ANGELINI', 'CHIESI')

    Returns:
        Funzione estrattore: (text, lines, pdf_path) -> List[Dict]
    """
    vendor = vendor.upper() if vendor else 'GENERIC'
    return EXTRACTORS.get(vendor, extract_generic)


def extract_pdf(vendor: str, text: str, lines: List[str], pdf_path: str = None) -> List[Dict]:
    """
    Estrae ordini da PDF usando l'estrattore appropriato.

    Args:
        vendor: Codice vendor
        text: Testo completo estratto dal PDF
        lines: Lista di righe del testo
        pdf_path: Percorso al file PDF (opzionale)

    Returns:
        Lista di ordini estratti
    """
    extractor = get_extractor(vendor)
    return extractor(text, lines, pdf_path)


__all__ = [
    # Factory
    'get_extractor',
    'extract_pdf',
    'EXTRACTORS',

    # Detection
    'detect_vendor',
    'get_supported_vendors',

    # Estrattori (per import diretto se necessario)
    'extract_angelini',
    'extract_bayer',
    'extract_chiesi',
    'extract_codifi',
    'extract_cooper',
    'extract_opella',
    'extract_menarini',
    'extract_doc_generici',
    'extract_generic',
]
