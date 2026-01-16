# =============================================================================
# SERV.O v7.0 - UTILS/CODES
# =============================================================================
# Funzioni per normalizzazione codici (AIC, P.IVA)
# =============================================================================

import re
from typing import Tuple


def normalize_aic_simple(codice: str) -> str:
    """
    Normalizza codice AIC a 9 cifre (versione semplice).

    Args:
        codice: Codice AIC originale

    Returns:
        AIC normalizzato a 9 cifre
    """
    codice = str(codice).strip() if codice else ''
    codice_num = re.sub(r'[^\d]', '', codice)

    if not codice_num:
        return ''

    # Normalizza a 9 cifre
    if len(codice_num) < 9:
        return codice_num.zfill(9)
    else:
        return codice_num[:9]


def normalize_aic(codice: str, descrizione: str = '') -> Tuple[str, str, bool, bool]:
    """
    Normalizza codice AIC a 9 cifre con rilevamento espositore.

    Args:
        codice: Codice AIC originale
        descrizione: Descrizione prodotto (per rilevare espositore)

    Returns:
        Tuple (aic_normalizzato, aic_originale, is_espositore, is_child)
    """
    codice = str(codice).strip() if codice else ''
    aic_orig = codice
    is_espositore = False
    is_child = False

    # Rileva espositore da codice o descrizione
    esp_pattern = r'(ESP|EXP|BANCO|EXPO)'
    if re.search(esp_pattern, codice.upper()) or \
       re.search(esp_pattern, descrizione.upper()):
        is_espositore = True

    # Usa normalize_aic_simple per la normalizzazione
    aic_norm = normalize_aic_simple(codice)

    return aic_norm, aic_orig, is_espositore, is_child


def normalize_piva(piva: str) -> str:
    """
    Normalizza P.IVA rimuovendo zeri iniziali per confronto robusto.

    Args:
        piva: P.IVA originale

    Returns:
        P.IVA senza zeri iniziali (o '0' se solo zeri)
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Rimuovi zeri iniziali per confronto robusto
    return piva_clean.lstrip('0') or '0'


def format_piva(piva: str) -> str:
    """
    Formatta P.IVA come stringa di 11 caratteri con zeri iniziali.

    Se la P.IVA è più corta di 11 cifre, aggiunge zeri iniziali.
    Se più lunga, tronca a 11 cifre.
    Preserva gli zeri iniziali presenti nel documento.

    Args:
        piva: P.IVA originale (può essere con o senza zeri iniziali)

    Returns:
        P.IVA formattata a 11 cifre con padding di zeri iniziali
    """
    if not piva:
        return ''

    # Rimuovi caratteri non numerici
    piva_clean = re.sub(r'[^\d]', '', str(piva).strip())

    if not piva_clean:
        return ''

    # Normalizza a 11 cifre con padding di zeri iniziali
    if len(piva_clean) < 11:
        return piva_clean.zfill(11)
    elif len(piva_clean) > 11:
        return piva_clean[:11]

    return piva_clean


def is_valid_piva(piva: str) -> bool:
    """Verifica se P.IVA ha formato valido (11 cifre)."""
    if not piva:
        return False
    piva_clean = re.sub(r'[^\d]', '', str(piva))
    return len(piva_clean) == 11


def is_valid_aic(aic: str) -> bool:
    """Verifica se codice AIC ha formato valido (9 cifre)."""
    if not aic:
        return False
    aic_clean = re.sub(r'[^\d]', '', str(aic))
    return len(aic_clean) == 9
