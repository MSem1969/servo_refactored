# =============================================================================
# SERV.O v7.0 - UTILS/TEXT
# =============================================================================
# Funzioni per pulizia e estrazione testo
# =============================================================================

import re
from typing import Optional


def clean_text(text: str, max_length: int = None) -> str:
    """
    Pulisce e normalizza testo.

    - Rimuove spazi multipli
    - Rimuove caratteri di controllo
    - Tronca se necessario
    """
    if not text:
        return ''

    # Rimuovi caratteri di controllo
    text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(text))

    # Normalizza spazi
    text = re.sub(r'\s+', ' ', text).strip()

    # Tronca se necessario
    if max_length and len(text) > max_length:
        text = text[:max_length]

    return text


def extract_cap(text: str) -> Optional[str]:
    """Estrae CAP (5 cifre) da una stringa."""
    m = re.search(r'\b(\d{5})\b', str(text))
    return m.group(1) if m else None


def extract_piva(text: str) -> Optional[str]:
    """Estrae P.IVA (11 cifre) da una stringa."""
    m = re.search(r'\b(\d{11})\b', str(text))
    return m.group(1) if m else None
