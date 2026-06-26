# =============================================================================
# SERV.O v11.2 - VENDORS PACKAGE
# =============================================================================
# Estrattori vendor-specifici unificati
# =============================================================================

from .angelini import extract_angelini
from .avas import extract_avas
from .bayer import extract_bayer
from .chiesi import extract_chiesi
from .dompe import extract_dompe
from .codifi import extract_codifi
from .cooper import extract_cooper
from .opella import extract_opella
from .menarini import extract_menarini
from .reckitt import extract_reckitt
from .doc_generici import extract_doc_generici
from .viatris import extract_viatris
from .perrigo import extract_perrigo
from .zentiva import extract_zentiva
from .generic import extract_generic

__all__ = [
    'extract_angelini',
    'extract_avas',
    'extract_bayer',
    'extract_chiesi',
    'extract_dompe',
    'extract_codifi',
    'extract_cooper',
    'extract_opella',
    'extract_menarini',
    'extract_perrigo',
    'extract_reckitt',
    'extract_doc_generici',
    'extract_viatris',
    'extract_zentiva',
    'extract_generic',
]
