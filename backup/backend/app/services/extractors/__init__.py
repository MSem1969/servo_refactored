"""
EXTRACTOR_TO - Estrattori Vendor v6.2
=====================================
Convertito da TO_EXTRACTOR_v6_0_DB_def.ipynb - Celle 6-10
v6.2: Aggiunto DOC_GENERICI per Transfer Order via grossisti
"""

from .angelini import extract_angelini
from .bayer import extract_bayer
from .chiesi import extract_chiesi
from .codifi import extract_codifi
from .opella import extract_opella
from .menarini import extract_menarini
from .doc_generici import extract_doc_generici  # v6.2
from .generic import extract_generic

# Mapping estrattori per vendor
EXTRACTORS = {
    'ANGELINI': extract_angelini,
    'BAYER': extract_bayer,
    'CHIESI': extract_chiesi,
    'CODIFI': extract_codifi,
    'OPELLA': extract_opella,
    'MENARINI': extract_menarini,
    'DOC_GENERICI': extract_doc_generici,  # v6.2
}

def get_extractor(vendor: str):
    """Ritorna l'estrattore appropriato per il vendor."""
    return EXTRACTORS.get(vendor.upper(), extract_generic)
