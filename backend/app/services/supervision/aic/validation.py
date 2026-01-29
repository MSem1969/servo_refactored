# =============================================================================
# SERV.O v11.4 - AIC VALIDATION
# =============================================================================
# Funzioni di validazione e normalizzazione per codici AIC
# =============================================================================

import re
import hashlib
from typing import Tuple


def valida_codice_aic(codice_aic: str) -> Tuple[bool, str]:
    """
    Valida formato codice AIC.

    Args:
        codice_aic: Codice da validare

    Returns:
        (valido, messaggio_o_codice_pulito)
        - Se valido: (True, codice_pulito)
        - Se non valido: (False, messaggio_errore)
    """
    if not codice_aic:
        return False, "Codice AIC mancante"

    codice = str(codice_aic).strip()

    if not codice.isdigit():
        return False, "Codice AIC deve contenere solo cifre"

    if len(codice) != 9:
        return False, f"Codice AIC deve essere di 9 cifre (ricevuto: {len(codice)})"

    return True, codice


def normalizza_descrizione(descrizione: str) -> str:
    """
    Normalizza descrizione per matching.
    - Uppercase
    - Rimuovi spazi multipli
    - Rimuovi caratteri speciali
    - Tronca a 50 caratteri
    """
    if not descrizione:
        return ''
    desc = ' '.join(str(descrizione).upper().split())
    desc = re.sub(r'[^\w\s]', '', desc)
    return desc[:50]


def calcola_pattern_signature(vendor: str, descrizione: str) -> str:
    """
    Calcola signature univoca per pattern AIC.
    Pattern: VENDOR|DESCRIZIONE_NORMALIZZATA

    Args:
        vendor: Codice vendor (es. MENARINI)
        descrizione: Descrizione prodotto

    Returns:
        Hash MD5 troncato a 16 caratteri
    """
    desc_norm = normalizza_descrizione(descrizione)
    raw = f"{vendor or 'UNKNOWN'}|{desc_norm}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]
