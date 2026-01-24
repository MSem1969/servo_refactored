# =============================================================================
# TO_EXTRACTOR v6.2 - ESTRATTORE ANGELINI (WRAPPER)
# =============================================================================
# Vendor: ACRAF S.p.A. (Angelini Pharma)
#
# ARCHITETTURA:
# - La logica di estrazione è in: app/services/extractors/angelini.py
# - Questo file è un wrapper che espone la classe per il factory pattern
# =============================================================================

from typing import List, Dict, Any
from .base import BaseExtractor

# Import diretto dal file per evitare circular import
# (services/__init__.py importa pdf_processor che importa extractors)
import importlib.util
import os

def _get_extract_angelini():
    """Lazy load per evitare circular import."""
    from ..services.extractors.angelini import extract_angelini
    return extract_angelini


class AngeliniExtractor(BaseExtractor):
    """
    Wrapper per estrattore ANGELINI.

    La logica completa è implementata in:
        app/services/extractors/angelini.py

    Questo wrapper permette l'integrazione con il factory pattern
    usato da get_extractor().

    Gestisce:
    - PARENT_ESPOSITORE: codice 6 cifre + BANCO/DBOX/FSTAND/EXPO/XXPZ
    - CHILD: righe successive al parent fino a raggiungere pezzi attesi
    - SC.MERCE: righe sconto merce
    - P.O.P.: materiale promozionale
    - PRODOTTO_STANDARD: vendita normale
    - PROMO_AUTONOMA: codice 6 cifre senza pattern espositore
    """

    vendor = "ANGELINI"

    def extract(self, text: str, lines: List[str], pdf_path: str = None) -> List[Dict[str, Any]]:
        """
        Estrae ordini da PDF ANGELINI.

        Delega l'elaborazione alla funzione extract_angelini() in services.

        Args:
            text: Testo completo del PDF
            lines: Lista delle righe del PDF
            pdf_path: Percorso del file PDF (opzionale)

        Returns:
            Lista di dizionari con i dati degli ordini estratti
        """
        extract_angelini = _get_extract_angelini()
        return extract_angelini(text, lines, pdf_path)
